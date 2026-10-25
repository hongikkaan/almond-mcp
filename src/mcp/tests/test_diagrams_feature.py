"""Diagram factories retain catalogue filters, bridge payloads and live bindings."""
import asyncio
import json
import socket

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.diagrams.tools import register
from almond_mcp.retrieval_store import AlmondStore


def asset(asset_id, category="people", dimensions=(600, 300, 1700), **extra):
    return {
        "asset_id": asset_id, "category": category, "series": "Diagram",
        "product": "Standing person", "variant": asset_id,
        "dimensions_mm": dict(zip(("width", "depth", "height"), dimensions)),
        "file_available": True, "_resolved_file": f"C:/diagrams/{asset_id}.svg",
        "drawing_roles": ["elevation"], "lod": "symbol", **extra,
    }


class FakeBridge:
    def __init__(self, response='{"status":"success","guids":["placed"]}', error=None):
        self.calls = []
        self.response = response
        self.error = error

    def __call__(self, payload, timeout):
        self.calls.append((json.loads(payload), timeout))
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture
def diagrams(tmp_path):
    store = AlmondStore(tmp_path / "diagrams.sqlite3")
    assets = [asset("small"), asset("large", dimensions=(1200, 700, 2300)),
              asset("tree", category="trees", product="Tree", dimensions=(2000, 2000, 4000)),
              asset("missing", category="symbols", product="Missing", file_available=False)]
    store.sync_assets(assets, library_id="diagram_assets")
    store.sync_assets([asset("drawing-only")], library_id="drawing_assets")
    bridge = FakeBridge()
    namespace = {"retrieval_store": store, "diagram_asset_indexer": {a["asset_id"]: a for a in assets},
                 "_send_and_receive": bridge}
    tools = register(FastMCP("diagrams"), FeatureContext(namespace))
    return tools, namespace, bridge


def test_factory_registers_exact_diagram_schema_and_descriptions(diagrams):
    _, namespace, _ = diagrams
    mcp = FastMCP("diagram-schema")
    exports = register(mcp, FeatureContext(namespace))
    expected = {
        "list_diagram_assets": ({"category": ("string", ""), "limit": ("integer", 20),
                                 "offset": ("integer", 0)}, [],
                                "Lists available vector and CAD diagram assets (people, trees, symbols)."),
        "search_diagram_assets": ({"query": ("string", ""), "category": ("string", ""),
                                   "max_width_mm": ("number", 0), "max_depth_mm": ("number", 0),
                                   "max_height_mm": ("number", 0), "limit": ("integer", 10),
                                   "offset": ("integer", 0)}, [], "Searches the diagram asset library."),
        "get_diagram_asset": ({"asset_id": ("string", None)}, ["asset_id"],
                              "Returns one diagram asset's metadata."),
        "place_diagram_asset": ({"asset_id": ("string", None), "x": ("number", 0),
                                  "y": ("number", 0), "z": ("number", 0),
                                  "rotation_degrees": ("number", 0), "scale": ("number", 1)},
                                 ["asset_id"], "Places an indexed diagram asset (SVG, DWG, DXF)."),
    }

    async def run():
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == set(exports) == set(expected)
            for name, (fields, required, description) in expected.items():
                tool = tools[name]
                schema = tool.input_schema
                assert set(schema["properties"]) == set(fields)
                assert schema.get("required", []) == required
                for field, (kind, default) in fields.items():
                    assert schema["properties"][field]["type"] == kind
                    if field not in required:
                        assert schema["properties"][field]["default"] == default
                assert tool.description == description
                assert tool.annotations is None
            result = await client.call_tool("list_diagram_assets", {"category": "trees"})
            assert json.loads(result.content[0].text)["assets"][0]["asset_id"] == "tree"

    asyncio.run(run())


def test_catalogue_listing_search_and_metadata_stay_scoped_to_diagrams(diagrams):
    tools, _, bridge = diagrams
    listing = json.loads(tools["list_diagram_assets"](category="people", limit=1))
    assert listing["library_id"] == "diagram_assets"
    assert listing["purpose"] == "2D vector diagramming and line-art"
    assert listing["total"] == 2 and listing["next_offset"] == 1
    next_page = json.loads(tools["list_diagram_assets"](category="people", limit=1, offset=1))
    assert next_page["assets"][0]["asset_id"] != listing["assets"][0]["asset_id"]
    assert next_page["next_offset"] is None
    hits = json.loads(tools["search_diagram_assets"](query="standing", category="people"))
    assert {a["asset_id"] for a in hits["assets"]} == {"small", "large"}
    assert json.loads(tools["search_diagram_assets"](query="unknown"))["total"] == 0
    assert json.loads(tools["list_diagram_assets"](category="unknown"))["assets"] == []
    record = json.loads(tools["get_diagram_asset"]("small"))
    assert record["status"] == "success"
    assert record["asset"]["dimensions_mm"]["height"] == 1700
    assert "_resolved_file" not in record["asset"]
    missing = json.loads(tools["get_diagram_asset"]("missing"))
    assert missing["asset"]["file_available"] is False
    for asset_id in ("unknown", "drawing-only"):
        assert json.loads(tools["get_diagram_asset"](asset_id)) == {
            "status": "error", "message": f"Unknown diagram asset_id: {asset_id}"}
    assert bridge.calls == []


@pytest.mark.parametrize("dimension,maximum", [("width", 600), ("depth", 300), ("height", 1700)])
def test_search_dimension_filters_are_applied_by_shared_store(diagrams, dimension, maximum):
    tools, _, _ = diagrams
    result = json.loads(tools["search_diagram_assets"](
        category="people", **{f"max_{dimension}_mm": maximum}))
    assert [a["asset_id"] for a in result["assets"]] == ["small"]
    unbounded = json.loads(tools["search_diagram_assets"](
        category="people", **{f"max_{dimension}_mm": 0}))
    assert unbounded["total"] == 2


def test_placement_rejects_unknown_and_missing_files_before_bridge(diagrams):
    tools, _, bridge = diagrams
    assert json.loads(tools["place_diagram_asset"]("unknown")) == {
        "status": "error", "message": "Unknown diagram asset_id: unknown"}
    assert json.loads(tools["place_diagram_asset"]("missing")) == {
        "status": "error", "message": "Diagram asset file is missing for missing."}
    assert bridge.calls == []


def test_placement_preserves_protocol_payload_and_raw_bridge_response(diagrams):
    tools, _, bridge = diagrams
    result = tools["place_diagram_asset"]("small", x=10, y=20, z=30, rotation_degrees=90, scale=2)
    assert result == bridge.response
    assert bridge.calls == [({
        "type": "place_drawing_asset", "asset_id": "small", "file_path": "C:/diagrams/small.svg",
        "name": "Standing person small", "position": [10, 20, 30], "rotation_degrees": 90, "scale": 2,
        "metadata": {"library_id": "diagram_assets", "product": "Standing person", "variant": "small",
                     "category": "people", "dimensions_mm": {"width": 600, "depth": 300, "height": 1700},
                     "drawing_roles": ["elevation"], "lod": "symbol"},
    }, 90.0)]


@pytest.mark.parametrize("error,message", [(socket.timeout(), "Rhino diagram import timed out."),
                                           (ConnectionRefusedError("offline"), "Diagram asset placement failed: offline")])
def test_placement_preserves_bridge_error_messages_without_retry(diagrams, error, message):
    tools, namespace, _ = diagrams
    bridge = FakeBridge(error=error)
    namespace["_send_and_receive"] = bridge
    assert json.loads(tools["place_diagram_asset"]("small")) == {"status": "error", "message": message}
    assert len(bridge.calls) == 1


def test_registered_factories_read_current_store_indexer_sender_and_keep_server_isolation(diagrams, tmp_path):
    tools, namespace, original_bridge = diagrams
    isolated = register(FastMCP("isolated"), FeatureContext(dict(namespace)))
    replacement = AlmondStore(tmp_path / "replacement.sqlite3")
    replacement.sync_assets([asset("replacement", category="symbols")], library_id="diagram_assets")
    namespace["retrieval_store"] = replacement
    namespace["diagram_asset_indexer"] = {"replacement": asset("replacement", category="symbols")}
    namespace["_send_and_receive"] = FakeBridge(response="replacement response")
    assert json.loads(tools["list_diagram_assets"]())["total"] == 1
    assert json.loads(tools["search_diagram_assets"](query="replacement"))["total"] == 1
    assert json.loads(tools["get_diagram_asset"]("replacement"))["status"] == "success"
    assert tools["place_diagram_asset"]("replacement") == "replacement response"
    assert json.loads(tools["place_diagram_asset"]("small"))["status"] == "error"
    assert json.loads(isolated["list_diagram_assets"]())["total"] == 4
    assert json.loads(isolated["get_diagram_asset"]("replacement"))["status"] == "error"
    assert isolated["place_diagram_asset"]("small") == original_bridge.response
    assert len(original_bridge.calls) == 1
    assert len(namespace["_send_and_receive"].calls) == 1
