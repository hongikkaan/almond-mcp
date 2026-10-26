"""Scene MCP tools registered against a per-server feature context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.instruction_text import tool_instruction
import json
from pydantic import StrictBool


def register(mcp, context):
    @mcp.tool()
    @tool_instruction(__file__, 'create_design_scene')
    def create_design_scene(name: str, units: str = "mm", file_name: str = "") -> str:
        try:
            return json.dumps({
                "status": "success",
                "scene": context.retrieval_store.create_scene(name=name, units=units, file_name=file_name),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'get_design_scene')
    @query_output
    def get_design_scene(scene_id: str, include_ids: StrictBool = False) -> str:
        scene = context.retrieval_store.get_scene(scene_id)
        if not scene:
            return json.dumps(error_payload(f"Unknown scene_id: {scene_id}"))
        return json.dumps({"status": "success", "scene": scene})

    @mcp.tool()
    @tool_instruction(__file__, 'update_design_scene')
    def update_design_scene(scene_id: str, file_name: str) -> str:
        try:
            return json.dumps({"status": "success", "scene": context.retrieval_store.update_scene(scene_id, file_name)})
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
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_scene_objects')
    @query_output
    def get_scene_objects(scene_id: str, include_ids: StrictBool = False) -> str:
        try:
            objects = context.retrieval_store.scene_objects(scene_id)
            return json.dumps({"status": "success", "scene_id": scene_id, "objects": objects,
                               "total": len(objects), "live_verified": False}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    return {
        "create_design_scene": create_design_scene,
        "get_design_scene": get_design_scene,
        "update_design_scene": update_design_scene,
        "register_scene_objects": register_scene_objects,
        "get_scene_objects": get_scene_objects,
    }
