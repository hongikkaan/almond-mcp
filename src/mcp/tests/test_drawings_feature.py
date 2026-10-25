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
from test_drawing_sheets import (
    component,
    model,
    test_invalid_metadata_and_references_never_call_native,
    test_known_native_rejection_is_not_ambiguous,
    test_layout_identity_conflicts_are_rejected_before_native,
    test_lost_sheet_unregister_recovers_through_inspect_without_repeating_mutation,
    test_native_float_roundoff_is_allowed_only_for_measured_numeric_fields,
    test_none_plan_id_is_empty_on_native_wire_and_readable_on_sync,
    test_sheet_context_wrapup_and_updates_do_not_rewrite_plan_snapshots,
    test_sheet_listing_exposes_truncation_and_uses_all_filters,
    test_sheet_reference_blocks_component_unregister_and_unregistered_sync,
    test_sheet_sync_cannot_invent_unregistered_identity,
    test_sheet_sync_refuses_mismatched_unregistered_proof,
    test_uncertain_native_success_never_retries_and_rolls_back_ledger,
    test_unregistration_requires_exact_native_identity_ack_before_delete,
)
from test_drawing_sheet_tools import (
    arguments,
    wire,
    test_actual_sheet_mcp_schema_and_numeric_guards,
    test_public_sheet_roundtrip_refs_filters_and_preserving_removal,
    test_sheet_capability_gate_sends_no_unknown_operation,
    test_sheet_timeout_returns_recovery_identity_and_inspection_never_replays,
)


PUBLIC_TOOLS = {
    "list_drawing_recipes", "get_drawing_recipe", "apply_drawing_style",
    "import_drawing_hatch_patterns", "upsert_drawing_sheet", "get_drawing_sheet",
    "list_drawing_sheets", "sync_drawing_sheet", "remove_drawing_sheet",
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


@pytest.fixture
def store(server, tmp_path):
    result = DrawingTestStore(tmp_path / "drawings.sqlite3")
    assert result.get_drawing_sheet.__func__ is DrawingsStore.get_drawing_sheet
    server.retrieval_store = result
    server._send_and_receive = lambda *_: pytest.fail("Unexpected native call")
    return result


def call(server, name, **arguments):
    return json.loads(server.exports[name](**arguments))


def test_factory_registers_nine_tools_with_original_recipe_and_hatch_schema(server):
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == PUBLIC_TOOLS
            assert set(server.exports) == PUBLIC_TOOLS | {"_drawing_sheet_bridge", "_drawing_sheet_error"}
            expected = {
                "list_drawing_recipes": ({}, set()),
                "get_drawing_recipe": ({"recipe_id": "string"}, {"recipe_id"}),
                "apply_drawing_style": ({"recipe_id": "string"}, set()),
                "import_drawing_hatch_patterns": ({"asset_id": "string"}, {"asset_id"}),
            }
            for name, (fields, required) in expected.items():
                schema = tools[name].input_schema
                assert set(schema["properties"]) == set(fields)
                assert set(schema.get("required", [])) == required
                for field, kind in fields.items():
                    assert schema["properties"][field]["type"] == kind
            assert tools["apply_drawing_style"].input_schema["properties"]["recipe_id"]["default"] == "technical_axon_v1"
            assert tools["get_drawing_sheet"].annotations.read_only_hint is True
            assert tools["list_drawing_sheets"].annotations.read_only_hint is True
            assert tools["remove_drawing_sheet"].annotations.destructive_hint is False
    asyncio.run(verify())


def recipe_index(tmp_path, recipe_id="technical_axon_v1", label="First"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "recipe.json").write_text(json.dumps({
        "recipe_id": recipe_id, "name": label, "layers": [{"name": label}],
        "projection": {"type": "axonometric"}, "recommended_scales": [50, 100],
    }), encoding="utf-8")
    return DrawingRecipeIndexer(str(tmp_path))


def test_factory_uses_replaced_indexes_store_and_sender_without_cross_server_leak(server, store, tmp_path):
    server.drawing_recipe_indexer = recipe_index(tmp_path / "first")
    other = make_server()
    other.drawing_recipe_indexer = server.drawing_recipe_indexer
    assert call(other, "get_drawing_recipe", recipe_id="technical_axon_v1")["recipe"]["name"] == "First"
    server.drawing_recipe_indexer = recipe_index(tmp_path / "replacement", label="Replacement")
    sent = []
    def sender(payload, timeout=None):
        sent.append((json.loads(payload), timeout))
        return json.dumps({"status": "success", "source": "replacement"})
    server._send_and_receive = sender
    assert call(server, "list_drawing_recipes")["recipes"][0]["name"] == "Replacement"
    record = call(server, "get_drawing_recipe", recipe_id="technical_axon_v1")["recipe"]
    assert record["name"] == "Replacement" and "_source_file" not in record
    assert call(server, "apply_drawing_style")["source"] == "replacement"
    assert sent[-1] == ({"type": "apply_drawing_style", "recipe_id": "technical_axon_v1", "layers": [{"name": "Replacement"}]}, 60.0)
    assert call(other, "get_drawing_recipe", recipe_id="technical_axon_v1")["recipe"]["name"] == "First"
    server.retrieval_store = DrawingTestStore(tmp_path / "replacement.sqlite3")
    assert call(server, "list_drawing_sheets")["total"] == 0
    assert server.retrieval_store is not store
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


def test_sheet_bridge_reads_call_scoped_sender_and_restores_bound_sender(server):
    def normal(payload):
        request = json.loads(payload)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_sheets": 1}})
        return json.dumps({"status": "success", "source": "bound"})
    scoped_calls = []
    def scoped(payload):
        scoped_calls.append(json.loads(payload))
        return normal(payload).replace('"bound"', '"scoped"')
    server._send_and_receive = normal
    request = {"type": "drawing_sheet", "action": "inspect"}
    with server._feature_context.override(_send_and_receive=scoped):
        assert server._drawing_sheet_bridge(request)["source"] == "scoped"
    assert [item["type"] for item in scoped_calls] == ["get_rhino_context", "drawing_sheet"]
    assert server._drawing_sheet_bridge(request)["source"] == "bound"


def test_sheet_bridge_rejects_oversized_request_before_capability_or_mutation(server):
    server._send_and_receive = lambda *_: pytest.fail("Request must be rejected before transport")
    result = server._drawing_sheet_bridge({"type": "drawing_sheet", "title": "x" * 2_097_152})
    assert result["mutation_applied"] is False and "exceeds 2 MiB" in result["message"]
    with pytest.raises(ValueError, match="Out of range float"):
        server._drawing_sheet_bridge({"type": "drawing_sheet", "value": float("nan")})


@pytest.mark.parametrize("native_response, message", [
    ('[]', "Invalid native drawing sheet response"),
    ('x' * 2_097_153, "response exceeds 2 MiB"),
], ids=["invalid-json-type", "oversized-response"])
def test_uncertain_sheet_response_stops_after_one_mutation(server, store, arguments, native_response, message):
    requests = []
    def sender(payload):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_sheets": 1}})
        return native_response
    server._send_and_receive = sender
    result = call(server, "upsert_drawing_sheet", **arguments)
    assert result["requires_reconciliation"] is True and message in result["message"]
    assert result["sheet_id"] == requests[-1]["sheet_id"]
    assert [request.get("action") for request in requests] == [None, "upsert"]
    assert store.list_drawing_sheets()["total"] == 0


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


def test_extracted_sheet_initializer_migrates_without_changing_existing_data(store, model):
    scene = store.create_scene("Existing")["scene_id"]
    comp = component(store, model, scene)
    plan = store.create_generation_plan("Existing", component_ids=[comp["component_id"]])
    tables = ("scenes", "scene_revisions", "components", "document_objects", "scene_components",
              "generation_plans", "generation_plan_steps", "generation_plan_revisions", "generation_plan_components")
    with store._connect() as connection:
        before = {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
                  for table in tables}
        for table in ("drawing_sheet_scenes", "drawing_sheet_components", "drawing_sheets"):
            connection.execute(f"DROP TABLE {table}")
    migrated = DrawingTestStore(store.database_path)
    with migrated._connect() as connection:
        after = {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
                 for table in tables}
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert after == before and migrated.get_generation_plan(plan["plan_id"], 1) == plan
    assert migrated.list_drawing_sheets()["total"] == 0
