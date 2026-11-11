"""Public names are callable identifiers, independent of Python/native names."""
import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


def test_categorized_name_executes_and_old_name_is_not_an_alias(tmp_path):
    server = FastMCP("public-names")
    register(server, SimpleNamespace(retrieval_store=AlmondStore(tmp_path / "scene.sqlite3")))

    async def run():
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert "plan_02-create" in names
            assert {"create_phase", "plan_01-create_phase"}.isdisjoint(names)
            created = await client.call_tool("plan_02-create", {"request": {"target": "phase", "name": "Entrance"}})
            phase_id = json.loads(created.content[0].text)["phase"]["phase_id"]
            detail = await client.call_tool("plan_05-get", {"request": {"target": "phase", "phase_id": phase_id}})
            assert json.loads(detail.content[0].text)["name"] == "Entrance"
            for name in ("create_phase", "plan_01-create_phase"):
                rejected = await client.call_tool(name, {"name": "Must not create"}, raise_on_error=False)
                assert rejected.is_error
            listing = await client.call_tool("plan_08-list", {"request": {"target": "phase"}})
            assert len(json.loads(listing.content[0].text)["phases"]) == 1

    asyncio.run(run())
