"""Scene MCP tools registered against a per-server feature context."""
from almond_mcp.tool_response import error_payload, mcp_error_result
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.query_output import compact_ack, query_output, select_fields, validate_field_groups
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.instruction_text import tool_instruction
import json
from pydantic import StrictBool, StrictInt
from almond_mcp.features.scenes.observation import observe_objects


ACK_FIELDS = {"scene_id", "revision", "scene_revisions"}
SCENE_GROUPS = {
    "scope": {"file_name", "project_file_id", "units", "model_path"},
    "state": {"revision"},
    "geometry": {"bounds_mm", "component_id"},
    "audit": {"created_at", "updated_at", "observed_at"},
}


def register(mcp, context):
    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('list_design_scenes', wrapped=True))
    @tool_instruction(__file__, 'list_design_scenes')
    @query_output
    @holon_output
    def list_design_scenes(name: str = "", file_name: str = "", limit: StrictInt = 50,
                           offset: StrictInt = 0, include_ids: StrictBool = False,
                           field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, SCENE_GROUPS)
        try:
            result = context.retrieval_store.list_scenes(name, file_name, limit, offset)
            result["scenes"] = [select_fields(scene, field_groups, {"scene_id", "name"}, SCENE_GROUPS)
                                for scene in result["scenes"]]
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))

    @mcp.tool(output_schema=public_output_schema('create_design_scene', wrapped=True))
    @tool_instruction(__file__, 'create_design_scene')
    @holon_output
    def create_design_scene(name: str, units: str = "mm", file_name: str = "", project_file_id: str | None = None) -> str:
        try:
            return json.dumps({
                "status": "success",
                "scene": compact_ack(context.retrieval_store.create_scene(name=name, units=units, file_name=file_name, project_file_id=project_file_id), ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(output_schema=public_output_schema('get_design_scene', wrapped=True))
    @tool_instruction(__file__, 'get_design_scene')
    @query_output
    @holon_output
    def get_design_scene(scene_id: str, include_ids: StrictBool = False,
                         field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, SCENE_GROUPS)
        scene = context.retrieval_store.get_scene(scene_id)
        if not scene:
            return json.dumps(error_payload(f"Unknown scene_id: {scene_id}"))
        return json.dumps({"status": "success", "scene": select_fields(scene, field_groups,
            {"scene_id", "name", "units", "revision", "components", "objects", "direct_objects"}, SCENE_GROUPS)})

    @mcp.tool(output_schema=public_output_schema('update_design_scene', wrapped=True))
    @tool_instruction(__file__, 'update_design_scene')
    @holon_output
    def update_design_scene(scene_id: str, file_name: str | None = None, project_file_id: str | None = None) -> str:
        try:
            return json.dumps({"status": "success", "scene": compact_ack(context.retrieval_store.update_scene(scene_id, file_name, project_file_id), ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    def _observe(model_path, ids):
        return observe_objects(context._send_and_receive, model_path, ids)

    @mcp.tool(output_schema=public_output_schema('add_scene_objects', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'add_scene_objects')
    def add_scene_objects(scene_id: str, object_ids: list[str], expected_model_path: str = "") -> str:
        try:
            result = context.retrieval_store.change_scene_objects(scene_id, bound_model_path(expected_model_path),
                object_ids, True, context._component_bridge, _observe)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return context._component_error(exc)

    @mcp.tool(output_schema=public_output_schema('remove_scene_objects', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'remove_scene_objects')
    def remove_scene_objects(scene_id: str, object_ids: list[str], expected_model_path: str = "") -> str:
        try:
            result = context.retrieval_store.change_scene_objects(scene_id, bound_model_path(expected_model_path),
                object_ids, False, context._component_bridge, _observe)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return context._component_error(exc)

    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_scene_objects', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'get_scene_objects')
    @query_output
    @holon_output
    def get_scene_objects(scene_id: str, include_ids: StrictBool = False,
                          field_groups: list[str] | None = None, limit: StrictInt = 50,
                          offset: StrictInt = 0, expected_model_path: str = "") -> str:
        validate_field_groups(field_groups, SCENE_GROUPS)
        try:
            if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or offset < 0:
                return json.dumps(error_payload("limit must be 1–200 and offset non-negative.", error_code="invalid_arguments"))
            model_path = bound_model_path(expected_model_path)
            objects = context.retrieval_store.scene_objects(scene_id, model_path, context._component_bridge, _observe)
            selected = [select_fields(obj, field_groups,
                {"rhino_guid", "name", "object_type"}, SCENE_GROUPS) for obj in objects[offset:offset + limit]]
            return json.dumps({"status": "success", "scene_id": scene_id, "objects": selected,
                               "total": len(objects), "limit": limit, "offset": offset,
                               "truncated": offset + len(selected) < len(objects), "live_verified": True, "model_path": model_path}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    return {
        "list_design_scenes": list_design_scenes,
        "create_design_scene": create_design_scene,
        "get_design_scene": get_design_scene,
        "update_design_scene": update_design_scene,
        "get_scene_objects": get_scene_objects,
        "add_scene_objects": add_scene_objects,
        "remove_scene_objects": remove_scene_objects,
    }
