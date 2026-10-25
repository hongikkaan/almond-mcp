"""Component MCP tools; register explicitly with the current server context."""
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
                raise ValueError("Load a Bridge with design_components=1 before registering Components.")
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
        result = {"status": "error", "message": str(exc)}
        if isinstance(exc, ComponentReconciliationError):
            result.update(error_code="component_reconciliation_required", requires_reconciliation=True,
                          component_id=exc.component_id, expected_model_path=exc.model_path)
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    def upsert_design_component(
        expected_model_path: str,
        name: str,
        object_ids: list[str],
        scene_ids: list[str] | None = None,
        component_id: str = "",
        rhino_group_id: str = "",
        child_component_ids: list[str] | None = None,
    ) -> str:
        """Register direct objects and optional nested child Components in an explicit Rhino group.

        object_ids names DIRECT top-level owners (possibly [] when child_component_ids
        contains existing children). child_component_ids=None preserves existing children;
        [] explicitly detaches them. Each object has exactly one direct Component owner,
        and each child at most one parent in the same document without cycles. Parent
        group selection includes descendants without rewriting their direct owner IDs.
        Every Component needs at least one existing Scene; omitting scene_ids preserves
        an existing association. Geometry is not copied or duplicated.
        expected_model_path must match the active saved document. After an uncertain
        native result, inspect and sync_design_component; do not replay the mutation.
        """
        try:
            component = context.retrieval_store.upsert_component(
                model_path=expected_model_path, name=name, object_ids=object_ids,
                scene_ids=scene_ids, component_id=component_id, rhino_group_id=rhino_group_id,
                native_apply=_component_bridge, child_component_ids=child_component_ids,
            )
            return json.dumps({"status": "success", "component": component}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def get_design_component(component_id: str, live: bool = False) -> str:
        """Read cached direct/nested Component members or inspect live Rhino group membership.

        live=True reads the actual group, including unowned group-added TextDots as
        pending_objects requiring explicit sync; it never changes Rhino or the ledger.
        """
        try:
            component = context.retrieval_store.get_component(
                component_id, live=live, native_inspect=_component_bridge if live else None,
            )
            if component is None:
                raise KeyError(f"Unknown component_id: {component_id}")
            return json.dumps({"status": "success", "component": component}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def list_design_components(expected_model_path: str = "") -> str:
        """List compact cached Components, optionally restricted to one saved model path."""
        try:
            components = context.retrieval_store.list_components(expected_model_path)
            return json.dumps({"status": "success", "components": components, "total": len(components),
                               "live_verified": False}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool()
    def sync_design_component(expected_model_path: str, component_id: str, rhino_group_id: str = "") -> str:
        """Reconcile a Component after inspecting live Rhino group membership.

        When group editing adds unowned TextDots/objects, one explicit native sync may
        adopt their direct ownership under Undo and normalize ancestor memberships.
        Unchanged components stay read-only. Conflicting ownership requires explicit
        repair. A timed-out mutation is never automatically replayed.
        A complete live proof of a previously registered but now unregistered group
        also releases its cached registration, after checking Plan/Step/Sheet references.
        """
        try:
            component = context.retrieval_store.sync_component(
                model_path=expected_model_path, component_id=component_id,
                rhino_group_id=rhino_group_id, native_inspect=_component_bridge,
            )
            return json.dumps({"status": "success", "component": component}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    @mcp.tool(annotations={"destructiveHint": False})
    def remove_design_component(component_id: str) -> str:
        """Unregister Component ownership while preserving Rhino geometry and the ordinary group.

        A root Component may have children; they become roots and keep their object
        ownership, registered Rhino groups and Scene links. A Component that still has
        its own parent must first be detached. Plan/Step/Sheet references to the
        removed Component must be cleared first. No geometry is deleted or copied.
        """
        try:
            component = context.retrieval_store.unregister_component(component_id, native_apply=_component_bridge)
            return json.dumps({"status": "success", "component": component}, ensure_ascii=False)
        except Exception as exc:
            return _component_error(exc)

    def _component_operation_bridge(action: str, expected_model_path: str,
                                    component_ids: list[str], max_pairs: int = 64) -> str:
        """Verify the advertised native helper before dispatching one bounded request."""
        try:
            model_path = context.retrieval_store._component_model_path(expected_model_path)
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
                raise ValueError("Load a Bridge with component_operations=1 before using Component helpers.")
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
    def get_component_intersections(expected_model_path: str, component_ids: list[str],
                                    max_pairs: StrictInt = 64) -> str:
        """Inspect actual solid overlaps among the current recursive members of 1-32 Components.

        The native helper resolves current group members inside the same callback,
        tests bounded candidate pairs, and reports unsupported/truncated/unknown work.
        A successful call is not proof of no collision unless complete is true.
        This helper does not modify Rhino objects or the local Scene ledger.
        """
        return _component_operation_bridge("intersections", expected_model_path, component_ids, max_pairs)

    @mcp.tool(annotations={"destructiveHint": False})
    def focus_components(expected_model_path: str, component_ids: list[str]) -> str:
        """Select, isolate and zoom to current recursive members of 1-32 Components.

        Uses Rhino's existing Isolate/Unisolate history; other hidden/locked context
        and any existing document state are subject to the native helper's guards.
        The operation changes the live selection/visibility/view. An uncertain native
        result must be inspected; it is never automatically retried.
        """
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
