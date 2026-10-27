"""COS catalog agrees with the live MCP schema, using an isolated module fixture."""
import asyncio
from fastmcp import Client
from test_rhino_observation import server


def test_catalog_matches_live_schema_and_retains_camera_examples(server):
    from runtime import load_catalog, schema_identity
    catalog = {tool["name"]: tool for tool in load_catalog()["tools"]}

    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert len(tools) == 76
            assert {"save_rhino_document", "list_design_scenes", "get_selection_references", "update_design_scene", "list_phases", "list_plans"} <= set(tools)
            for name in ("list_design_scenes", "list_plans", "get_plan", "get_design_component",
                         "list_drawing_assets", "validate_scene_layout", "get_selection_references"):
                assert tools[name]["inputSchema"]["properties"]["field_groups"] == {
                    "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": None}
            assert not {"upsert_drawing_sheet", "get_drawing_sheet", "list_drawing_sheets",
                        "sync_drawing_sheet", "remove_drawing_sheet"} & set(tools)
            for name in tools:
                assert schema_identity(tools[name]) == schema_identity(catalog[name])
                assert tools[name]["description"] == catalog[name]["description"]
            description = tools["capture_conditioning_pass"]["description"]
            for retained in ('"type":"orbit"', '"type":"track"', '"type":"keyframes"', "camera.json"):
                assert retained in description
                assert retained in catalog["capture_conditioning_pass"]["description"]
            assert "result_error" in tools["execute_rhino_script"]["description"]
            from almond_mcp.modeling_guidance import startup_instructions
            assert client.instructions == startup_instructions()
            assert 'get_modeling_guide(topic="blocks")' in tools["execute_rhino_script"]["description"]
    asyncio.run(verify())
