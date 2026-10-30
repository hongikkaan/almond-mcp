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


def test_a4_recipe_keeps_explicit_linetype_segments_through_discovery_and_native_apply(server, tmp_path):
    recipe = {
        "recipe_id": "architectural_plan_section_a4_v1",
        "name": "Architectural Plan and Section A4",
        "projection": {"type": "parallel"},
        "recommended_scales": ["1:50", "1:100", "1:200"],
        "output": {"paper": "A4", "orientation": "landscape"},
        "layers": [{
            "path": "ALMOND-DRAW::HIDDEN", "role": "hidden",
            "color": [120, 120, 120], "plot_color": [90, 90, 90],
            "plot_weight_mm": 0.1, "linetype": "ALMOND A4 Hidden",
            "linetype_segments": [
                {"length": 3.0, "is_solid": True},
                {"length": 1.5, "is_solid": False},
            ],
        }],
    }
    (tmp_path / "a4.json").write_text(json.dumps(recipe), encoding="utf-8")
    server.drawing_recipe_indexer = DrawingRecipeIndexer(str(tmp_path))
    sent = []

    def sender(payload, timeout=None):
        sent.append(json.loads(payload))
        return json.dumps({"status": "success"})

    server._send_and_receive = sender
    discovered = call(server, "get_drawing_recipe", recipe_id=recipe["recipe_id"],
                      field_groups=["parameters", "scales"])["recipe"]
    assert discovered["layers"] == recipe["layers"]
    assert discovered["recommended_scales"] == recipe["recommended_scales"]
    assert discovered["output"] == recipe["output"]
    assert call(server, "apply_drawing_style", recipe_id=recipe["recipe_id"])["status"] == "success"
    assert len(sent) == 1
    assert sent[0]["recipe_id"] == recipe["recipe_id"]
    assert sent[0]["layers"] == recipe["layers"]


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


def test_a4_style_success_suggests_print_review_without_executing_it(server, tmp_path):
    """After layer application, review preparation is a next call, not a mutation."""
    recipe_id = "architectural_plan_section_a4_v1"
    server.drawing_recipe_indexer = recipe_index(tmp_path, recipe_id=recipe_id)
    recipe = server.drawing_recipe_indexer.get(recipe_id)
    recipe["review_preparation"] = {"print_display": True}
    native_result = {"status": "success", "layers": [{"path": "ALMOND-DRAW::HIDDEN"}]}
    sent = []

    def sender(payload, timeout=None):
        sent.append((json.loads(payload), timeout))
        return json.dumps(native_result)

    server._send_and_receive = sender
    response = call(server, "apply_drawing_style", recipe_id=recipe_id)
    preparation = response.pop("review_preparation")
    assert response == native_result
    assert preparation["status"] == "not_executed"
    assert preparation["cli"] == {
        "program": "rhinocode",
        "discovery_arguments": ["list", "--json"],
        "arguments_template": [
            "--rhino", "{matched_pipeId}", "command", (
                "_PrintDisplay _Scope=_Document _Viewport=_Model _State=_On _Color=_Print "
                "_Viewport=_Layout _State=_On _Color=_Print _DetailBorder=_UsePrintWidth _Enter"
            ),
        ],
    }
    assert sent == [({"type": "apply_drawing_style", "recipe_id": recipe_id,
                     "layers": recipe["layers"]}, 60.0)]


@pytest.mark.parametrize("native_response", [
    '{"status":"error","layers":[{"path":"already-applied"}],"message":"Layer update failed"}',
    '{"status":"partial","message":"Layer application incomplete"}',
    'Unconfirmed native response',
])
def test_a4_style_does_not_suggest_review_after_unconfirmed_application(server, tmp_path, native_response):
    recipe_id = "architectural_plan_section_a4_v1"
    server.drawing_recipe_indexer = recipe_index(tmp_path, recipe_id=recipe_id)
    server.drawing_recipe_indexer.get(recipe_id)["review_preparation"] = {"print_display": True}
    server._send_and_receive = lambda *_args, **_kwargs: native_response
    assert server.exports["apply_drawing_style"](recipe_id=recipe_id) == native_response


@pytest.mark.parametrize("recipe_id, preparation", [
    ("technical_axon_v1", None),
    ("technical_axon_v1", {"print_display": True}),
    ("architectural_plan_section_a4_v1", None),
    ("architectural_plan_section_a4_v1", {"script": "_Delete"}),
])
def test_existing_and_nonopted_in_styles_keep_native_response_and_payload(server, tmp_path, recipe_id, preparation):
    server.drawing_recipe_indexer = recipe_index(tmp_path, recipe_id=recipe_id)
    recipe = server.drawing_recipe_indexer.get(recipe_id)
    if preparation is not None:
        recipe["review_preparation"] = preparation
    native_response = '{ "status": "success", "layers": [] }\n'
    sent = []

    def sender(payload, timeout=None):
        sent.append((json.loads(payload), timeout))
        return native_response

    server._send_and_receive = sender
    assert server.exports["apply_drawing_style"](recipe_id=recipe_id) == native_response
    assert sent == [({"type": "apply_drawing_style", "recipe_id": recipe_id,
                     "layers": recipe["layers"]}, 60.0)]


def test_a4_review_preparation_is_available_in_parameters_without_expanding_summary(server, tmp_path):
    recipe_id = "architectural_plan_section_a4_v1"
    server.drawing_recipe_indexer = recipe_index(tmp_path, recipe_id=recipe_id)
    preparation = {"print_display": True}
    server.drawing_recipe_indexer.get(recipe_id)["review_preparation"] = preparation
    summary = call(server, "get_drawing_recipe", recipe_id=recipe_id)["recipe"]
    parameters = call(server, "get_drawing_recipe", recipe_id=recipe_id,
                      field_groups=["parameters"])["recipe"]
    assert "review_preparation" not in summary
    assert parameters["review_preparation"] == preparation
