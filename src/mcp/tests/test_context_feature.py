"""Run the established observation contracts against the extracted factory directly."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.context.tools import register


@pytest.fixture
def server():
    def unexpected_send(*_):
        pytest.fail("Unexpected bridge call")

    context = SimpleNamespace(mcp=FastMCP("context-feature"), _send_and_receive=unexpected_send)
    exports = register(context.mcp, context)
    assert set(exports) == {
        "get_retrieval_status", "get_rhino_context", "get_rhino_probe",
        "get_rhino_viewport_image", "_viewport_result",
    }
    context.__dict__.update(exports)
    return context


def test_registration_keeps_tools_and_runtime_sender_scoped(server):
    other = SimpleNamespace(mcp=FastMCP("other-context"))
    other.__dict__.update(register(other.mcp, other))
    other._send_and_receive = lambda _: '{"status":"success","connection":"other"}'
    server._send_and_receive = lambda _: '{"status":"success","connection":"first"}'
    assert json.loads(server.get_rhino_context())["connection"] == "first"
    assert json.loads(other.get_rhino_context())["connection"] == "other"
    server._send_and_receive = lambda _: '{"status":"success","connection":"rebound"}'

    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == {
                "get_retrieval_status", "get_rhino_context", "get_rhino_probe", "get_rhino_viewport_image",
            }
            for name in ("get_rhino_context", "get_rhino_probe", "get_rhino_viewport_image"):
                assert tools[name].annotations.read_only_hint is True
                assert tools[name].annotations.destructive_hint is False
            result = await client.call_tool("get_rhino_context", {})
            assert json.loads(result.content[0].text)["connection"] == "rebound"
        assert json.loads(other.get_rhino_context())["connection"] == "other"

    asyncio.run(verify())


def test_retrieval_status_uses_current_store_paths_and_recipe_indexer(server):
    calls = []

    def stats(library_id=None):
        calls.append(library_id)
        return {"total": 7, "library_id": library_id}

    server.STATE_DB_PATH = "first.sqlite3"
    server.retrieval_store = SimpleNamespace(asset_stats=lambda *_: {"total": 0})
    server.drawing_recipe_indexer = SimpleNamespace(recipes={})
    server.drawing_asset_indexer = SimpleNamespace(assets={"a": {}})
    assert json.loads(server.get_retrieval_status())["drawing_recipes"] == 0
    server.STATE_DB_PATH = "rebound.sqlite3"
    server.retrieval_store = SimpleNamespace(asset_stats=stats)
    server.drawing_recipe_indexer = SimpleNamespace(recipes={"a": {}, "b": {}})
    result = json.loads(server.get_retrieval_status(include_ids=True))
    assert result == {
        "status": "ready", "database": "rebound.sqlite3",
        "asset_index": {"total": 7, "library_id": None},
        "drawing_asset_index": {"total": 1, "source": "manifest"},
        "model_asset_index": {"total": 7, "library_id": "generated_assets"},
        "drawing_recipes": 2, "retrieval": ["sqlite", "fts5", "rtree"],
        "embedding_adapter": "not_configured",
    }
    assert calls == [None, "generated_assets"]
