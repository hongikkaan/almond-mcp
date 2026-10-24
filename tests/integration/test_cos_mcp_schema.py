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
            for name in ("get_rhino_context", "get_rhino_viewport_image", "execute_rhino_script",
                         "get_rhino_probe", "capture_conditioning_pass", "setup_modeling"):
                assert schema_identity(tools[name]) == schema_identity(catalog[name])
            description = tools["capture_conditioning_pass"]["description"]
            for retained in ('"type":"orbit"', '"type":"track"', '"type":"keyframes"', "camera.json"):
                assert retained in description
                assert retained in catalog["capture_conditioning_pass"]["description"]
            assert "result_error" in tools["execute_rhino_script"]["description"]
    asyncio.run(verify())
