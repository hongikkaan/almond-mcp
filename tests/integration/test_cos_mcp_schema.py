"""COS catalog agrees with the live MCP schema, using an isolated module fixture."""
import asyncio
from fastmcp import Client
from test_rhino_observation import server


def test_catalog_matches_live_schema_and_keeps_camera_examples_in_explanation(server):
    from runtime import load_catalog, schema_identity
    catalog = {tool["name"]: tool for tool in load_catalog()["tools"]}

    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert len(tools) == 76
            assert {"save_rhino_document", "list_design_scenes", "get_selection_references", "update_design_scene", "list_phases", "list_plans"} <= set(tools)
            for name in ("list_design_scenes", "list_plans", "get_plan", "get_ontological_component",
                         "list_drawing_assets", "get_selection_references"):
                assert tools[name]["inputSchema"]["properties"]["field_groups"] == {
                    "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": None}
            assert not {"upsert_drawing_sheet", "get_drawing_sheet", "list_drawing_sheets",
                        "sync_drawing_sheet", "remove_drawing_sheet"} & set(tools)
            for name in tools:
                assert schema_identity(tools[name]) == schema_identity(catalog[name])
                assert tools[name]["description"] == catalog[name]["description"]
            description = tools["capture_conditioning_pass"]["description"]
            from almond_mcp.instruction_text import read_instruction
            from almond_mcp.features.capture import tools as capture_tools
            full = read_instruction(capture_tools.__file__, 'capture_conditioning_pass')
            for retained in ('"type":"orbit"', '"type":"track"', '"type":"keyframes"', "camera.json"):
                assert retained not in description
                assert retained in full
            from almond_mcp.features.modeling import tools as modeling_tools
            assert "result_error" in read_instruction(modeling_tools.__file__, 'execute_rhino_script')
            from almond_mcp.modeling_guidance import startup_instructions
            assert client.instructions == startup_instructions()
            assert 'get_modeling_guide(topic="blocks")' not in tools["execute_rhino_script"]["description"]
    asyncio.run(verify())
