"""MCP tools for cached legacy asset placement, registered per server."""
import json


def register(mcp, context):
    @mcp.tool()
    def upsert_design_room(
        scene_id: str,
        name: str,
        bounds_mm: list[float],
        room_id: str = "",
    ) -> str:
        """
        Creates or updates a legacy room envelope for asset-placement containment checks.
        Use upsert_design_component for physical architectural assemblies.
        bounds_mm is [min_x, min_y, min_z, max_x, max_y, max_z]. When room_id is
        omitted, an existing room with the same name in the scene is updated
        instead of creating a duplicate.
        """
        try:
            result = context.retrieval_store.upsert_room(
                scene_id=scene_id,
                name=name,
                bounds_mm=bounds_mm,
                room_id=room_id,
            )
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
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
        """
        Registers or moves an asset instance in millimetres without retransmitting
        its full metadata. Returns a stable instance handle and scene revision.
        When z_mm is omitted the instance stands on its room's floor (the room's
        min_z), so rooms at storey elevation validate correctly.
        """
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
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def remove_scene_instance(scene_id: str, instance_id: str) -> str:
        """
        Removes an instance from the scene ledger (recorded as a revision delta).
        The Rhino geometry, if any, is not touched.
        """
        try:
            result = context.retrieval_store.remove_instance(scene_id, instance_id)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def remove_design_room(scene_id: str, room_id: str) -> str:
        """
        Removes a room from the scene ledger. Instances that referenced it stay
        in the scene, orphaned (re-home them with register_scene_instance).
        """
        try:
            result = context.retrieval_store.remove_room(scene_id, room_id)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def validate_scene_layout(scene_id: str, detail_limit: int = 50) -> str:
        """
        Runs cached legacy asset-instance AABB collisions and room-containment checks.
        Component/raw-object geometry is reported as unvalidated; inspect it with native probes.
        """
        try:
            return json.dumps({
                "status": "success",
                **context.retrieval_store.validate_scene(scene_id, limit=detail_limit),
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    return {
        "upsert_design_room": upsert_design_room,
        "register_scene_instance": register_scene_instance,
        "remove_scene_instance": remove_scene_instance,
        "remove_design_room": remove_design_room,
        "validate_scene_layout": validate_scene_layout,
    }
