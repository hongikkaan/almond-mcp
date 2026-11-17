"""Both public placement tools retain the same evidence after native reply loss."""
import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from jsonschema import validate
import pytest

from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from almond_mcp.features.assets.tools import register as asset_tools
from almond_mcp.features.diagrams.tools import register as diagram_tools
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.retrieval_store import AlmondStore


@pytest.mark.parametrize("tool", ["asset_06-place", "diagram_03-place"])
@pytest.mark.parametrize("outcome", ["timeout", "lost_reply", "connection_refused", "not_started", "native_unknown", "success"])
def test_placement_preserves_native_mutation_state(tmp_path, tool, outcome):
    requests = []
    (tmp_path / "item.svg").touch()
    asset = {"asset_id": "fixture", "file": "item.svg", "_resolved_file": str(tmp_path / "item.svg"),
             "file_available": True, "dimensions_mm": {"width": 100, "depth": 100, "height": 100}}
    index = SimpleNamespace(get=lambda _: asset, assets={"fixture": asset})

    def send(raw, **kwargs):
        requests.append(json.loads(raw))
        if outcome == "timeout":
            raise TimeoutError("delayed native response")
        if outcome == "lost_reply":
            raise ConnectionError("connection closed after request")
        if outcome == "connection_refused":
            raise ConnectionRefusedError("no listening connection")
        if outcome == "success":
            return '{"status":"success","object_guid":"00000000-0000-0000-0000-000000000001"}'
        state = "unknown" if outcome == "native_unknown" else "not_started"
        return json.dumps({"status": "error", "mutation_state": state, "error_code": "fixture_failure"})

    store = AlmondStore(tmp_path / "state.sqlite3")
    store.sync_assets([asset], library_id="diagram_assets")
    context = SimpleNamespace(drawing_asset_indexer=index, retrieval_store=store,
        diagram_asset_indexer=AssetLibraryIndexer(tmp_path, "diagram_assets", "diagram"), _send_and_receive=send)
    mcp = FastMCP("placement-outcomes")
    asset_tools(mcp, context)
    diagram_tools(mcp, context)

    async def run():
        async with Client(mcp) as client:
            reply = await client.call_tool(tool, {"asset_id": "fixture"}, raise_on_error=False)
            return json.loads(reply.content[0].text)

    result = asyncio.run(run())
    contract = "place_drawing_asset" if tool.startswith("asset_") else "place_diagram_asset"
    validate(result, public_output_schema(contract, wrapped=False))
    assert len(requests) == 1 and requests[0]["type"] == "place_drawing_asset"
    if outcome == "success":
        assert result["status"] == "success"
        assert result["object_guid"] == "00000000-0000-0000-0000-000000000001"
        assert not result.get("requires_reconciliation")
    elif outcome in {"not_started", "connection_refused"}:
        assert result["mutation_state"] == "not_started"
        assert not result.get("requires_reconciliation")
        if outcome == "connection_refused":
            assert result["mutation_applied"] is False
    else:
        assert result["status"] == "error" and result["requires_reconciliation"] is True
        assert result["mutation_state"] == "unknown"
        assert result["mutation_applied"] is None
