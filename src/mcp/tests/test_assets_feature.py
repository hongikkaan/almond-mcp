"""Exercise the extracted asset factory, canonical dependencies and shared-DB mixin."""
import asyncio
import importlib
import json
import socket
from pathlib import Path
from types import SimpleNamespace

from fastmcp import Client, FastMCP
import pytest

from almond_mcp import paths
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.assets import drafting
from almond_mcp.features.assets.store import AssetsStore
from almond_mcp.features.assets.tools import register
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from test_drafting import box_glb
from test_drawing_asset_registration import extract_box


if issubclass(AlmondStore, AssetsStore):
    ExtractedStore = AlmondStore
else:
    class ExtractedStore(AssetsStore, AlmondStore):
        """Use extracted asset methods before the coordinator's facade cutover."""


def asset_record(asset_id, **updates):
    return {
        "asset_id": asset_id, "product": "Fixture chair", "category": "furniture",
        "file_available": True, "dimensions_mm": {"width": 2, "depth": 4, "height": 3},
        "tags": ["seating"], **updates,
    }


def fixture_index(root):
    return AssetLibraryIndexer(str(root), "drawing_assets", "fixture")


def make_feature(tmp_path):
    roots = {name: tmp_path / name for name in ("drawing", "generated", "drafting")}
    for root in roots.values():
        root.mkdir(parents=True)
        (root / "manifest.json").write_text('{"assets": []}', encoding="utf-8")
    namespace = {
        "retrieval_store": ExtractedStore(tmp_path / "state.sqlite3"),
        "drawing_asset_indexer": fixture_index(roots["drawing"]),
        "generated_asset_indexer": fixture_index(roots["generated"]),
        "diagram_asset_indexer": SimpleNamespace(assets={}),
        "DRAWING_LIBRARY_DIR": str(roots["drawing"]),
        "GENERATED_LIBRARY_DIR": str(roots["generated"]),
        "DRAFTING_LIBRARY_DIR": str(roots["drafting"]),
    }
    mcp = FastMCP("extracted-assets-test")
    context = FeatureContext(namespace)
    exports = register(mcp, context)
    namespace.update(exports)
    return mcp, context, namespace, exports


def test_agent_shortlists_assets_then_requests_dimensions_without_source_paths(tmp_path):
    """Given a shortlist, only a deliberate fit check asks for measured dimensions."""
    _, _, namespace, tools = make_feature(tmp_path)
    namespace["drawing_asset_indexer"].assets["fixture"] = asset_record(
        "fixture", model_path="private.3dm", source_url="https://example.test/source", created_at="yesterday")
    plain = json.loads(tools["list_drawing_assets"]())["assets"][0]
    assert plain["product"] == "Fixture chair" and "dimensions_mm" not in plain
    assert "source_url" not in plain and "model_path" not in plain and "created_at" not in plain
    detail = json.loads(tools["list_drawing_assets"](field_groups=["dimensions"], include_ids=True))["assets"][0]
    assert detail["asset_id"] == "fixture" and detail["dimensions_mm"] == {"width": 2, "depth": 4, "height": 3}
    assert "source_url" not in detail and "created_at" not in detail
    rejected = json.loads(tools["list_drawing_assets"](field_groups=["no_such_group"]))
    assert rejected["error_code"] == "invalid_arguments"


def test_factory_registers_only_existing_tools_and_all_resource_uris(tmp_path):
    mcp, _, _, exports = make_feature(tmp_path)
    async def check():
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == {
                "list_drawing_assets", "search_drawing_assets", "get_drawing_asset",
                "place_drawing_asset", "register_drawing_asset", "get_asset_drawing",
                "generate_asset_drawing_views", "audit_asset_drawing", "search_asset_repository",
            }
            assert set(tools["place_drawing_asset"].input_schema["properties"]) == {
                "asset_id", "x", "y", "z", "rotation_degrees", "scale"}
            assert tools["place_drawing_asset"].input_schema["required"] == ["asset_id"]
            assert tools["get_asset_drawing"].annotations.read_only_hint
            assert tools["register_drawing_asset"].annotations.destructive_hint is False
            uris = {str(resource.uri) for resource in await client.list_resources()}
            uris.update(resource.uri_template for resource in await client.list_resource_templates())
            assert uris == {
                "almond://assets/{asset_id}/sources", "almond://assets/{asset_id}/drawing/{view}/{scale}",
                "almond://drawing/{asset_id}/drawing/{view}/{scale}", "almond://assets/catalogue",
                "almond://assets/{asset_id}/passport", "almond://assets/{asset_id}/preview",
                "almond://repository/{asset_id}",
            }
    asyncio.run(check())
    assert {"_extract_drawing_asset", "_dimension_check", "_apply_import_correction",
            "list_assets", "search_assets", "recommend_assets",
            "get_asset_passport", "evaluate_asset_fit", "get_asset_sources",
            "get_asset", "place_asset"} <= exports.keys()


def test_registration_resources_repository_and_placement_share_one_asset(tmp_path, monkeypatch):
    mcp, _, namespace, exports = make_feature(tmp_path)
    root = Path(namespace["DRAWING_LIBRARY_DIR"])
    source = tmp_path / "prepared.3dm"
    source.write_bytes(b"reviewed-source")
    calls = []
    def native(payload, **kwargs):
        request = json.loads(payload)
        calls.append(request["type"])
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_asset_extract": 1}})
        if request["type"] == "drawing_asset_extract":
            return json.dumps(extract_box(request["source_path"], request["output_path"]))
        assert request["type"] == "place_drawing_asset"
        assert request["position"] == [1, 2, 3]
        assert request["metadata"]["sha256"] == drafting.sha(Path(request["file_path"]).read_bytes())
        return '{"status": "success", "object_guid": "fixture"}'
    namespace["_send_and_receive"] = native
    for variable, key in (("RHINO_MCP_DRAWING_ASSET_DIR", "DRAWING_LIBRARY_DIR"),
                          ("RHINO_MCP_GENERATED_ASSET_DIR", "GENERATED_LIBRARY_DIR"),
                          ("RHINO_MCP_DRAFTING_DIR", "DRAFTING_LIBRARY_DIR")):
        monkeypatch.setenv(variable, namespace[key])
    async def check():
        async with Client(mcp) as client:
            result = await client.call_tool("register_drawing_asset", {
                "source_3dm": str(source), "asset_id": "drawing-fixture", "name": "Fixture"})
            assert result.structured_content["live_index_refreshed"]
            record = json.loads(exports["get_drawing_asset"]("drawing-fixture", include_ids=True))["asset"]
            assert "asset_id" not in record and record["product"] == "Fixture"
            drawing = exports["get_asset_drawing"]("drawing-fixture", include_ids=True)
            assert "asset_id" not in drawing["manifest"]["source"]
            svg = await client.read_resource("almond://drawing/drawing-fixture/drawing/plan/50")
            assert svg[0].mime_type == "image/svg+xml"
            assert json.loads(exports["place_drawing_asset"]("drawing-fixture", x=1, y=2, z=3))["status"] == "success"
            found = exports["search_asset_repository"]("Fixture", drawing_ready=True, include_ids=True)
            assert found["total"] == 1
            record = json.loads(exports["repository_asset_resource"]("drawing-fixture"))
            assert record["id"] == "drawing-fixture" and record["drawing"]
            assert all(Path(path).is_file() for path in record["local_files"].values())
            return result.structured_content
    registered = asyncio.run(check())
    assert calls == ["get_rhino_context", "drawing_asset_extract", "place_drawing_asset"]
    def fail_refresh(*args, **kwargs):
        raise RuntimeError("fixture index unavailable")
    monkeypatch.setattr(namespace["drawing_asset_indexer"], "_load", fail_refresh)
    failed = exports["register_drawing_asset"](str(source), "drawing-second", "Second")
    assert failed["registration_applied"] and not failed["live_index_refreshed"]
    assert Path(failed["model_path"]).is_file() and Path(registered["model_path"]).is_file()
    assert (root / "manifest.json").is_file()


def test_factory_uses_rebound_store_sender_and_call_local_overrides(tmp_path):
    _, context, namespace, exports = make_feature(tmp_path / "one")
    _, _, other, other_exports = make_feature(tmp_path / "two")
    record = asset_record("drawing-one", _resolved_file="fixture.3dm")
    namespace["drawing_asset_indexer"].assets[record["asset_id"]] = record
    other["drawing_asset_indexer"].assets[record["asset_id"]] = record
    other["drawing_asset_indexer"].assets["drawing-two"] = asset_record("drawing-two")
    assert json.loads(exports["list_drawing_assets"](include_ids=True))["assets"][0]["asset_id"] == "drawing-one"
    namespace["drawing_asset_indexer"] = other["drawing_asset_indexer"]
    assert {item["asset_id"] for item in json.loads(exports["list_drawing_assets"](include_ids=True))["assets"]} == {"drawing-one", "drawing-two"}
    namespace["_send_and_receive"] = lambda *a, **kw: '{"connection":"rebound"}'
    other["_send_and_receive"] = lambda *a, **kw: '{"connection":"other"}'
    with context.override(_send_and_receive=lambda *a, **kw: '{"connection":"scoped"}'):
        assert json.loads(exports["place_drawing_asset"]("drawing-one"))["connection"] == "scoped"
        assert json.loads(other_exports["place_drawing_asset"]("drawing-one"))["connection"] == "other"
    assert json.loads(exports["place_drawing_asset"]("drawing-one"))["connection"] == "rebound"
    attempts = []
    def timed_out(*args, **kwargs):
        attempts.append(1)
        raise socket.timeout()
    with context.override(_send_and_receive=timed_out):
        result = json.loads(exports["place_drawing_asset"]("drawing-one"))
    assert result["requires_reconciliation"] and attempts == [1]


def test_generated_resources_and_cross_feature_helpers_use_current_context(tmp_path):
    mcp, _, namespace, exports = make_feature(tmp_path)
    generated = Path(namespace["GENERATED_LIBRARY_DIR"])
    drafting_root = Path(namespace["DRAFTING_LIBRARY_DIR"])
    model = box_glb(generated / "box.glb")
    record = asset_record("gen-fixture", file="box.glb", sha256=drafting.sha(model.read_bytes()),
                          contract_file="contract.json", passport={"name": "Fixture"})
    namespace["generated_asset_indexer"].assets[record["asset_id"]] = record
    (generated / "source-register.json").write_text(json.dumps({"assets": [
        {"asset_id": record["asset_id"], "model_sha256": record["sha256"]}]}), encoding="utf-8")
    (generated / "previews").mkdir()
    (generated / "previews/gen-fixture.png").write_bytes(b"fixture-preview")
    drafting.create_package(model, drafting_root / "package", asset_id="gen-fixture", name="Fixture", units="mm", up_axis="y")
    (drafting_root / "manifest.json").write_text('{"assets":[{"asset_id":"gen-fixture","package":"package"}]}', encoding="utf-8")
    table = generated / "loads.json"
    table.write_text('{"basis":"fixture","assets":{"gen-fixture":{"self_kg":5}}}', encoding="utf-8")
    namespace["_structural_loads_path"] = lambda: table
    assert exports["get_asset_passport"]("gen-fixture")["structural_loads"]["self_kg"] == 5
    namespace["_structural_loads_path"] = lambda: generated / "missing.json"
    assert "structural_loads" not in exports["get_asset_passport"]("gen-fixture")
    async def check():
        async with Client(mcp) as client:
            for uri, mime in (("sources", "application/json"), ("passport", "application/json"),
                              ("preview", "image/png"), ("drawing/plan/50", "image/svg+xml")):
                content = await client.read_resource("almond://assets/gen-fixture/" + uri)
                assert content[0].mime_type == mime
            catalogue = await client.read_resource("almond://assets/catalogue")
            assert "gen-fixture" in catalogue[0].text
    asyncio.run(check())
    namespace["exchange"] = SimpleNamespace(load_contract=lambda path: {"path": str(path)})
    namespace["_receive_contract"] = lambda contract, *a: {"status": "success", "connection": "first"}
    assert json.loads(exports["place_asset"]("gen-fixture"))["connection"] == "first"
    namespace["_receive_contract"] = lambda contract, *a: {"status": "success", "connection": "second"}
    assert json.loads(exports["place_asset"]("gen-fixture"))["connection"] == "second"
    namespace["exchange"] = SimpleNamespace(load_contract=lambda path: {"changed": True})
    namespace["_receive_contract"] = lambda contract, *a: {"status": "success", "received": contract}
    assert json.loads(exports["place_asset"]("gen-fixture"))["received"] == {"changed": True}


def test_custom_projection_generation_and_staleness_use_extracted_tools(tmp_path, monkeypatch):
    _, _, _, exports = make_feature(tmp_path)
    model = box_glb(tmp_path / "custom.glb")
    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path / "user")
    assert exports["generate_asset_drawing_views"](source_glb=str(model))["status"] == "error"
    result = exports["generate_asset_drawing_views"](source_glb=str(model), input_units="mm", scales=[50])
    assert result["status"] == "success"
    package = Path(result["package_dir"])
    assert list(package.glob("*.dxf")) and list(package.glob("*.svg"))
    assert exports["audit_asset_drawing"](str(package), str(model))["source_geometry"] == "current"
    model.write_bytes(model.read_bytes() + b"changed")
    stale = exports["audit_asset_drawing"](str(package), str(model))
    assert stale["status"] == "error"


def test_extracted_store_preserves_library_scoping_search_and_retired_references(tmp_path):
    store = ExtractedStore(tmp_path / "store.sqlite3")
    store.sync_assets([asset_record("drawing-kept", _resolved_file="private-path")], library_id="drawing_assets")
    store.sync_assets([asset_record("generated-placed"), asset_record("generated-stale")], library_id="generated_assets")
    assert store.search_assets(query="seating", library_id="generated_assets", max_width_mm=1)["total"] == 0
    assert store.search_assets(query="seating", library_id="generated_assets")["total"] == 2
    assert "_resolved_file" not in store.get_asset("drawing-kept")
    scene = store.create_scene("Asset references")
    from test_retired_placement import seed_legacy_placement
    seed_legacy_placement(store, scene["scene_id"], "generated-placed")
    store.sync_assets([], library_id="generated_assets")
    assert store.get_asset("generated-stale") is None
    assert store.get_asset("generated-placed") is not None
    assert store.asset_stats("retired")["total"] == 1
    assert store.asset_stats("drawing_assets")["total"] == 1
    assert store.search_assets(query="Fixture")["total"] == 1
    with store._connect() as connection:
        assert connection.execute("SELECT count(*) FROM instances").fetchone()[0] == 1
    with store._connect() as connection:
        assert connection.execute("SELECT count(*) FROM asset_rtree").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM asset_fts").fetchone()[0] == 1


def test_extracted_store_rolls_back_manifest_fts_and_spatial_updates_together(tmp_path):
    store = ExtractedStore(tmp_path / "rollback.sqlite3")
    store.sync_assets([asset_record("original")], library_id="drawing_assets")
    invalid = asset_record("invalid", dimensions_mm={"width": 0, "depth": 1, "height": 1})
    with pytest.raises(ValueError, match="invalid dimensions"):
        store.sync_assets([asset_record("new"), invalid], library_id="drawing_assets")
    assert store.get_asset("new") is None
    assert store.search_assets(query="original")["total"] == 1
    assert store.asset_stats("drawing_assets")["total"] == 1
    with store._connect() as connection:
        assert connection.execute("SELECT count(*) FROM asset_rtree").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM asset_fts").fetchone()[0] == 1


@pytest.mark.parametrize("consumer, dependency", [
    ("tools", "drawing_assets"), ("tools", "drafting"), ("drawing_assets", "drafting"),
])
def test_asset_consumers_share_canonical_module_dependencies(consumer, dependency):
    module = importlib.import_module("almond_mcp.features.assets." + consumer)
    canonical = importlib.import_module("almond_mcp.features.assets." + dependency)
    assert getattr(module, dependency) is canonical


def test_repository_tool_resolves_patched_canonical_repository(tmp_path, monkeypatch):
    from almond_mcp.features.assets import asset_repository

    calls = []
    repository = SimpleNamespace(search=lambda *args: calls.append(args) or {"total": 0})
    monkeypatch.setattr(asset_repository, "AssetRepository", lambda: repository)
    _, _, _, exports = make_feature(tmp_path)
    assert exports["search_asset_repository"]("chair", "model", True, 5, include_ids=True) == {"total": 0}
    assert calls == [("chair", "model", True, 5)]
    assert asset_repository.UI_ROOT == Path(__file__).resolve().parents[2] / "rhp/Asset_Panel/web"
    assert (asset_repository.UI_ROOT / "index.html").is_file()
