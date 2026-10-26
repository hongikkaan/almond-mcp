"""MCP tools for cached legacy asset placement, registered per server."""
from almond_mcp.tool_response import error_payload
from almond_mcp.instruction_text import tool_instruction
import json


def register(mcp, context):
    @mcp.tool()
    @tool_instruction(__file__, 'upsert_design_room')
    def upsert_design_room(
        scene_id: str,
        name: str,
        bounds_mm: list[float],
        room_id: str = "",
    ) -> str:
        try:
            result = context.retrieval_store.upsert_room(
                scene_id=scene_id,
                name=name,
                bounds_mm=bounds_mm,
                room_id=room_id,
            )
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'register_scene_instance')
    def register_scene_instance(
        scene_id: str,
        asset_id: str,
        x_mm: float,
        y_mm: float,
        z_mm: float | None = None,
        rotation_degrees: float = 0,
        scale: float = 1,
        room_id: str = "",
        instance_id: str = "",
        locked: bool = False,
        rhino_guid: str = "",
    ) -> str:
        try:
            result = context.retrieval_store.upsert_instance(
                scene_id=scene_id,
                asset_id=asset_id,
                x_mm=x_mm,
                y_mm=y_mm,
                z_mm=z_mm,
                rotation_degrees=rotation_degrees,
                scale=scale,
                room_id=room_id,
                instance_id=instance_id,
                locked=locked,
                rhino_guid=rhino_guid,
            )
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'remove_scene_instance')
    def remove_scene_instance(scene_id: str, instance_id: str) -> str:
        try:
            result = context.retrieval_store.remove_instance(scene_id, instance_id)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'remove_design_room')
    def remove_design_room(scene_id: str, room_id: str) -> str:
        try:
            result = context.retrieval_store.remove_room(scene_id, room_id)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'validate_scene_layout')
    def validate_scene_layout(scene_id: str, detail_limit: int = 50) -> str:
        try:
            return json.dumps({
                "status": "success",
                **context.retrieval_store.validate_scene(scene_id, limit=detail_limit),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    return {
        "upsert_design_room": upsert_design_room,
        "register_scene_instance": register_scene_instance,
        "remove_scene_instance": remove_scene_instance,
        "remove_design_room": remove_design_room,
        "validate_scene_layout": validate_scene_layout,
    }
