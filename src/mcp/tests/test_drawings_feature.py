"""Extracted drawing factories and mixins retain Sheet and recipe contracts."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.drawings.library import DrawingRecipeIndexer
from almond_mcp.features.drawings.store import DrawingsStore
from almond_mcp.features.drawings.tools import register
from almond_mcp.retrieval_store import AlmondStore

# Reuse behavioral regressions with the extracted mixin/factory fixtures below.


PUBLIC_TOOLS = {
    "list_drawing_recipes", "get_drawing_recipe", "apply_drawing_style",
    "import_drawing_hatch_patterns",
}

# Exercise this implementation both before and after the coordinator's cutover.
if issubclass(AlmondStore, DrawingsStore):
    DrawingTestStore = AlmondStore
else:
    class DrawingTestStore(DrawingsStore, AlmondStore):
        pass


def make_server():
    server = SimpleNamespace(mcp=FastMCP("drawings-feature"))
    server._feature_context = FeatureContext(vars(server))
    server.exports = register(server.mcp, server._feature_context)
    vars(server).update(server.exports)
    return server


@pytest.fixture
def server():
    return make_server()




def call(server, name, **arguments):
    return json.loads(server.exports[name](**arguments))


def test_factory_keeps_presentation_tools_and_removes_sheet_registration(server):
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == PUBLIC_TOOLS
            assert set(server.exports) == PUBLIC_TOOLS
            expected = {
                "list_drawing_recipes": ({"include_ids": "boolean"}, set()),
                "get_drawing_recipe": ({"recipe_id": "string", "include_ids": "boolean"}, {"recipe_id"}),
                "apply_drawing_style": ({"recipe_id": "string"}, set()),
                "import_drawing_hatch_patterns": ({"asset_id": "string"}, {"asset_id"}),
            }
            for name, (fields, required) in expected.items():
                schema = tools[name].input_schema
                assert set(schema["properties"]) == set(fields) | ({"field_groups"} if "include_ids" in fields else set())
                if "include_ids" in fields:
                    assert schema["properties"]["field_groups"] == {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": None}
                assert set(schema.get("required", [])) == required
                for field, kind in fields.items():
                    assert schema["properties"][field]["type"] == kind
            assert tools["apply_drawing_style"].input_schema["properties"]["recipe_id"]["default"] == "technical_axon_v1"
    asyncio.run(verify())


def recipe_index(tmp_path, recipe_id="technical_axon_v1", label="First"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "recipe.json").write_text(json.dumps({
        "recipe_id": recipe_id, "name": label, "layers": [{"name": label}],
        "projection": {"type": "axonometric"}, "recommended_scales": [50, 100],
    }), encoding="utf-8")
    return DrawingRecipeIndexer(str(tmp_path))


def test_factory_uses_replaced_indexes_store_and_sender_without_cross_server_leak(server, tmp_path):
    server.drawing_recipe_indexer = recipe_index(tmp_path / "first")
    other = make_server()
    other.drawing_recipe_indexer = server.drawing_recipe_indexer
    assert call(other, "get_drawing_recipe", recipe_id="technical_axon_v1", include_ids=True, field_groups=["all"])["recipe"]["name"] == "First"
    server.drawing_recipe_indexer = recipe_index(tmp_path / "replacement", label="Replacement")
    sent = []
    def sender(payload, timeout=None):
        sent.append((json.loads(payload), timeout))
        return json.dumps({"status": "success", "source": "replacement"})
    server._send_and_receive = sender
    assert call(server, "list_drawing_recipes", include_ids=True, field_groups=["all"])["recipes"][0]["name"] == "Replacement"
    record = call(server, "get_drawing_recipe", recipe_id="technical_axon_v1", include_ids=True, field_groups=["all"])["recipe"]
    assert record["name"] == "Replacement" and "_source_file" not in record
    assert call(server, "apply_drawing_style")["source"] == "replacement"
    assert sent[-1] == ({"type": "apply_drawing_style", "recipe_id": "technical_axon_v1", "layers": [{"name": "Replacement"}]}, 60.0)
    assert call(other, "get_drawing_recipe", recipe_id="technical_axon_v1", include_ids=True, field_groups=["all"])["recipe"]["name"] == "First"
    server.drawing_asset_indexer = SimpleNamespace(get=lambda _: {"file_available": True, "_resolved_file": "controlled/pattern.pat"})
    assert call(server, "import_drawing_hatch_patterns", asset_id="pattern")["source"] == "replacement"
    assert sent[-1] == ({"type": "import_hatch_patterns", "file_path": "controlled/pattern.pat"}, 60.0)


@pytest.mark.parametrize("asset, message", [
    (None, "Unknown drawing asset_id"),
    ({"file_available": False}, "file is missing"),
    ({"file_available": True, "_resolved_file": "controlled/model.3dm"}, "not a .pat"),
])
def test_hatch_import_rejects_unavailable_or_wrong_manifest_file_before_native(server, asset, message):
    server.drawing_asset_indexer = SimpleNamespace(get=lambda _: asset)
    server._send_and_receive = lambda *_: pytest.fail("No native operation is permitted")
    response = call(server, "import_drawing_hatch_patterns", asset_id="pattern")
    assert response["status"] == "error" and message in response["message"]








def test_recipe_indexer_skips_invalid_records_and_keeps_controlled_source_private(tmp_path, capsys):
    assert DrawingRecipeIndexer(str(tmp_path / "missing")).recipes == {}
    (tmp_path / "malformed.json").write_text("{", encoding="utf-8")
    (tmp_path / "invalid.json").write_text(json.dumps({"recipe_id": "../outside"}), encoding="utf-8")
    index = recipe_index(tmp_path, recipe_id="valid-v1", label="Verified")
    assert list(index.recipes) == ["valid-v1"]
    record = index.get("valid-v1")
    assert record["_source_file"] == str(tmp_path / "recipe.json")
    assert index.public_record(record)["name"] == "Verified"
    assert "_source_file" not in index.public_record(record)
    assert index.get("missing") is None
    assert "Skipping drawing recipe" in capsys.readouterr().err
