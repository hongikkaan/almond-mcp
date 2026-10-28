"""Scene MCP tools registered against a per-server feature context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import compact_ack, query_output, select_fields, validate_field_groups
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.instruction_text import tool_instruction
import json
from pydantic import StrictBool, StrictInt


ACK_FIELDS = {"scene_id", "revision", "direct_objects", "scene_revisions"}
SCENE_GROUPS = {
    "scope": {"file_name", "units", "model_path"},
    "state": {"revision"},
    "geometry": {"bounds_mm", "component_id"},
    "audit": {"created_at", "updated_at", "observed_at"},
}


def register(mcp, context):
    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_design_scenes')
    @query_output
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

    @mcp.tool()
    @tool_instruction(__file__, 'create_design_scene')
    def create_design_scene(name: str, units: str = "mm", file_name: str = "") -> str:
        try:
            return json.dumps({
                "status": "success",
                "scene": compact_ack(context.retrieval_store.create_scene(name=name, units=units, file_name=file_name), ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'get_design_scene')
    @query_output
    def get_design_scene(scene_id: str, include_ids: StrictBool = False,
                         field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, SCENE_GROUPS)
        scene = context.retrieval_store.get_scene(scene_id)
        if not scene:
            return json.dumps(error_payload(f"Unknown scene_id: {scene_id}"))
        return json.dumps({"status": "success", "scene": select_fields(scene, field_groups,
            {"scene_id", "name", "units", "revision", "components", "direct_objects", "objects"}, SCENE_GROUPS)})

    @mcp.tool()
    @tool_instruction(__file__, 'update_design_scene')
    def update_design_scene(scene_id: str, file_name: str) -> str:
        try:
            return json.dumps({"status": "success", "scene": compact_ack(context.retrieval_store.update_scene(scene_id, file_name), ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"destructiveHint": False})
    @tool_instruction(__file__, 'register_scene_objects')
    def register_scene_objects(
        scene_id: str, object_ids: list[str], expected_model_path: str = "", mode: str = "add",
    ) -> str:
        try:
            result = context.retrieval_store.register_scene_objects(
                scene_id=scene_id, model_path=bound_model_path(expected_model_path), object_ids=object_ids,
                mode=mode, native_observe=context._component_bridge,
            )
            return json.dumps({"status": "success", **compact_ack(result, ACK_FIELDS)}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_scene_objects')
    @query_output
    def get_scene_objects(scene_id: str, include_ids: StrictBool = False,
                          field_groups: list[str] | None = None, limit: StrictInt = 50,
                          offset: StrictInt = 0) -> str:
        validate_field_groups(field_groups, SCENE_GROUPS)
        try:
            if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or offset < 0:
                return json.dumps(error_payload("limit must be 1–200 and offset non-negative.", error_code="invalid_arguments"))
            objects = context.retrieval_store.scene_objects(scene_id)
            selected = [select_fields(obj, field_groups,
                {"rhino_guid", "name", "object_type", "direct"}, SCENE_GROUPS) for obj in objects[offset:offset + limit]]
            return json.dumps({"status": "success", "scene_id": scene_id, "objects": selected,
                               "total": len(objects), "limit": limit, "offset": offset,
                               "truncated": offset + len(selected) < len(objects), "live_verified": False}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    return {
        "list_design_scenes": list_design_scenes,
        "create_design_scene": create_design_scene,
        "get_design_scene": get_design_scene,
        "update_design_scene": update_design_scene,
        "register_scene_objects": register_scene_objects,
        "get_scene_objects": get_scene_objects,
    }
