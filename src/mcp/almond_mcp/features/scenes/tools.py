"""Scene MCP tools registered against a per-server feature context."""
import json


def register(mcp, context):
    @mcp.tool()
    def create_design_scene(name: str, units: str = "mm") -> str:
        """
        Creates a persistent scene handle for a house or interior generation.
        Scene metadata remains local and is retrieved by ID instead of being
        repeated in the model context.
        """
        try:
            return json.dumps({
                "status": "success",
                "scene": context.retrieval_store.create_scene(name=name, units=units),
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def get_design_scene(scene_id: str) -> str:
        """Returns a token-efficient scene summary by stable handle."""
        scene = context.retrieval_store.get_scene(scene_id)
        if not scene:
            return json.dumps({"status": "error", "message": f"Unknown scene_id: {scene_id}"})
        return json.dumps({"status": "success", "scene": scene})


    @mcp.tool(annotations={"destructiveHint": False})
    def register_scene_objects(
        scene_id: str, expected_model_path: str, object_ids: list[str], mode: str = "add",
    ) -> str:
        """Link top-level objects directly to a Scene without an asset instance or Component.

        mode is add, remove or replace for this document's direct links. Other model
        links and Component membership are retained. Observe current GUIDs/bounds live;
        this updates the local ledger and does not edit Rhino geometry or object names.
        """
        try:
            result = context.retrieval_store.register_scene_objects(
                scene_id=scene_id, model_path=expected_model_path, object_ids=object_ids,
                mode=mode, native_observe=context._component_bridge,
            )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def get_scene_objects(scene_id: str) -> str:
        """Read cached direct Scene objects and all descendant Component members as one set."""
        try:
            objects = context.retrieval_store.scene_objects(scene_id)
            return json.dumps({"status": "success", "scene_id": scene_id, "objects": objects,
                               "total": len(objects), "live_verified": False}, ensure_ascii=False)
        except Exception as exc:
            return context._component_error(exc)


    return {
        "create_design_scene": create_design_scene,
        "get_design_scene": get_design_scene,
        "register_scene_objects": register_scene_objects,
        "get_scene_objects": get_scene_objects,
    }
