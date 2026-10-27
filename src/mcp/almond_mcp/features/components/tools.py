"""Component MCP tools; register explicitly with the current server context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.instruction_text import tool_instruction, read_instruction
from pydantic import StrictBool
import json

from pydantic import StrictInt

from almond_mcp.store_common import ComponentReconciliationError


def register(mcp, context):
    def _component_bridge(request: dict) -> dict:
        """Capability-check before one native operation; never retry an uncertain mutation."""
        payload = json.dumps(request, allow_nan=False).encode("utf-8")
        if len(payload) > 2_097_152:
            return {"status": "error", "mutation_applied": False, "message": "Component request exceeds 2 MiB."}
        try:
            rhino_context = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
            if not isinstance(rhino_context, dict) or rhino_context.get("status") != "success":
                raise ValueError("Could not inspect the bound Rhino document.")
            if rhino_context.get("capabilities", {}).get("design_components") != 1:
                raise ValueError(read_instruction(__file__, 'response-566'))
            if rhino_context.get("capabilities", {}).get("component_registry") != 2:
                raise ValueError("Load a Bridge with component_registry=2 before using object-free Component registration.")
        except Exception as exc:
            return {"status": "error", "mutation_applied": False, "message": str(exc)}
        response = context._send_and_receive(payload)
        if len(response.encode("utf-8")) > 2_097_152:
            raise ValueError("Component response exceeds 2 MiB.")
        result = json.loads(response)
        if not isinstance(result, dict):
            raise ValueError("Invalid native Component response.")
        return result

    def _component_error(exc: Exception) -> str:
        result = error_payload(str(exc))
        result.update(getattr(exc, "native_result", {}))
        if isinstance(exc, ComponentReconciliationError):
            result.update(error_code="component_reconciliation_required", requires_reconciliation=True,
                          component_id=exc.component_id, expected_model_path=exc.model_path)
        return json.dumps(result, ensure_ascii=False)

    def _component_ack(component: dict) -> dict:
        return {key: component[key] for key in (
            "component_id", "rhino_group_id", "status", "availability", "object_count", "live_verified",
        ) if key in component}

    @mcp.tool()
    @tool_instruction(__file__, 'upsert_design_component')
    def upsert_design_component(
        name: str,
        object_ids: list[str],
        expected_model_path: str = "",
        scene_ids: list[str] | None = None,
        component_id: str = "",
        rhino_group_id: str = "",
        child_component_ids: list[str] | None = None,
    ) -> str:
        try:
            component = context.retrieval_store.upsert_component(
                model_path=bound_model_path(expected_model_path), name=name, object_ids=object_ids,
                scene_ids=scene_ids, component_id=component_id, rhino_group_id=rhino_group_id,
                native_apply=_component_bridge, child_component_ids=child_component_ids,
            )
            return json.dumps({"status": "success", "component": _component_ack(component)}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_design_component')
    @query_output
    def get_design_component(component_id: str, live: bool = False, include_ids: StrictBool = False,
                             recursive: StrictBool = False) -> str:
        try:
            component = context.retrieval_store.get_component(
                component_id, live=live, native_inspect=_component_bridge if live else None,
            )
            if component is None:
                raise KeyError(f"Unknown component_id: {component_id}")
            if not recursive:
                component = {key: value for key, value in component.items()
                             if key not in {"effective_objects", "effective_object_ids"}}
            return json.dumps({"status": "success", "component": component}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_design_components')
    @query_output
    def list_design_components(expected_model_path: str = "", include_ids: StrictBool = False,
                               scene_id: str = "", recursive: StrictBool = False) -> str:
        try:
            components = context.retrieval_store.list_components(expected_model_path, scene_id=scene_id, recursive=recursive)
            return json.dumps({"status": "success", "components": components, "total": len(components),
                               "live_verified": False}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool()
    @tool_instruction(__file__, 'sync_design_component')
    def sync_design_component(component_id: str = "", expected_model_path: str = "", rhino_group_id: str = "",
                              component_ids: list[str] | None = None, scene_id: str = "") -> str:
        try:
            if component_id and component_ids is not None:
                raise ValueError("Use component_id or component_ids, not both.")
            if scene_id and (component_id or component_ids is not None):
                raise ValueError("Use a Component target or a Scene scope, not both.")
            if rhino_group_id:
                rhino_group_id = context.retrieval_store._component_guid(rhino_group_id)
                existing = context.retrieval_store.get_component(component_id)
                if not component_id or (existing and existing["rhino_group_id"] != rhino_group_id):
                    raise ValueError("The supplied group GUID does not match the existing Component binding.")
            result = context.retrieval_store.align_components(
                model_path=bound_model_path(expected_model_path),
                component_ids=[component_id] if component_id else component_ids,
                scene_id=scene_id, native_inspect=_component_bridge,
                expected_groups={component_id: rhino_group_id} if rhino_group_id else None)
            if component_id:
                component = context.retrieval_store.get_component(component_id)
                failed = any(isinstance(problem, dict) and problem.get("component_id") == component_id
                             for problem in result["problems"])
                if component and not failed:
                    result["component"] = _component_ack(dict(component, live_verified=True))
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool(annotations={"destructiveHint": False})
    @tool_instruction(__file__, 'remove_design_component')
    def remove_design_component(component_id: str) -> str:
        try:
            component = context.retrieval_store.unregister_component(component_id, native_apply=_component_bridge)
            return json.dumps({"status": "success", "component": _component_ack(component)}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    def _component_operation_bridge(action: str, expected_model_path: str,
                                    component_ids: list[str], max_pairs: int = 64) -> str:
        """Verify the advertised native helper before dispatching one bounded request."""
        try:
            model_path = context.retrieval_store._component_model_path(bound_model_path(expected_model_path))
            if (not isinstance(component_ids, list) or not 1 <= len(component_ids) <= 32
                    or any(not isinstance(value, str) or not value.strip() for value in component_ids)
                    or len(set(component_ids)) != len(component_ids)):
                raise ValueError("component_ids must contain 1 to 32 distinct Component handles.")
            if type(max_pairs) is not int or not 1 <= max_pairs <= 64:
                raise ValueError("max_pairs must be an integer between 1 and 64.")
            request = {"type": "component_operation", "action": action,
                       "expected_model_path": model_path, "component_ids": component_ids}
            if action == "intersections":
                request["max_pairs"] = max_pairs
            payload = json.dumps(request, allow_nan=False).encode("utf-8")
            if len(payload) > 262144:
                raise ValueError("Component operation request exceeds 256 KiB.")
        except (ValueError, TypeError, KeyError) as exc:
            return json.dumps({"status": "error", "error_code": "invalid_arguments",
                               "mutation_applied": False, "message": str(exc)})
        try:
            rhino_context = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
            if not isinstance(rhino_context, dict) or rhino_context.get("status") != "success":
                raise ValueError("Could not inspect the bound Rhino document.")
            if rhino_context.get("capabilities", {}).get("component_operations") != 1:
                raise ValueError(read_instruction(__file__, 'response-571'))
        except Exception as exc:
            return json.dumps({"status": "error", "error_code": "unsupported_component_operations",
                               "mutation_applied": False, "message": str(exc)})
        # After this point a focus timeout cannot certify that Rhino was not changed.
        try:
            response = context._send_and_receive(payload)
            if len(response.encode("utf-8")) > 262144:
                raise ValueError("Component operation response exceeds 256 KiB.")
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError("Native Component helper returned a non-object response.")
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            uncertainty = action == "focus"
            return json.dumps({"status": "error", "error_code": "component_operation_bridge_error",
                               "message": str(exc), "requires_reconciliation": uncertainty,
                               "mutation_applied": None if uncertainty else False})

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_component_intersections')
    @query_output
    def get_component_intersections(component_ids: list[str], expected_model_path: str = "",
                                    max_pairs: StrictInt = 64, include_ids: StrictBool = False) -> str:
        return _component_operation_bridge("intersections", expected_model_path, component_ids, max_pairs)

    @mcp.tool(annotations={"destructiveHint": False})
    @tool_instruction(__file__, 'focus_components')
    def focus_components(component_ids: list[str], expected_model_path: str = "") -> str:
        return _component_operation_bridge("focus", expected_model_path, component_ids)

    return {
        "_component_bridge": _component_bridge,
        "_component_error": _component_error,
        "upsert_design_component": upsert_design_component,
        "get_design_component": get_design_component,
        "list_design_components": list_design_components,
        "sync_design_component": sync_design_component,
        "remove_design_component": remove_design_component,
        "_component_operation_bridge": _component_operation_bridge,
        "get_component_intersections": get_component_intersections,
        "focus_components": focus_components,
    }
