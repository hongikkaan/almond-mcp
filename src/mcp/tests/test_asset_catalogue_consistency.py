"""Asset identity remains consistent at startup and on catalogue reads."""
import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP
import pytest

from almond_mcp import paths
from almond_mcp.features.assets.asset_repository import AssetRepository
from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from almond_mcp.features.assets.tools import register
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.startup import create_server


def write_manifest(root, library, *assets):
    root.mkdir(exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({"library_id": library, "assets": list(assets)}), encoding="utf-8")


def test_startup_rejects_ambiguous_sqlite_asset_id_before_sync(tmp_path):
    dirs = {key: str(tmp_path / key.removeprefix("RHINO_MCP_")) for key in paths.LIBRARY_DIRS}
    generated = tmp_path / "GENERATED_ASSET_DIR"
    diagram = tmp_path / "DIAGRAM_ASSET_DIR"
    asset = {"asset_id": "shared", "file": "fixture.svg", "product": "Original",
             "dimensions_mm": {"width": 100, "depth": 100, "height": 100}, "file_available": True}
    write_manifest(diagram, "diagram_assets", asset)
    write_manifest(generated, "generated_assets", {**asset, "product": "Other"})
    state_db = tmp_path / "state.sqlite3"
    store = AlmondStore(state_db)
    store.sync_assets([asset], library_id="diagram_assets")
    with pytest.raises(ValueError, match="diagram_assets.*generated_assets.*shared"):
        create_server(state_db=state_db, library_dirs=dirs, send=lambda *_: pytest.fail("Unexpected Rhino call"))
    assert store.search_assets("original", library_id="diagram_assets")["total"] == 1
    assert store.get_asset("shared", library_id="generated_assets") is None


def test_sqlite_owner_conflict_rolls_back_all_library_updates(tmp_path):
    dirs = {key: str(tmp_path / key.removeprefix("RHINO_MCP_")) for key in paths.LIBRARY_DIRS}
    diagram = tmp_path / "DIAGRAM_ASSET_DIR"
    generated = tmp_path / "GENERATED_ASSET_DIR"
    example = {"file": "fixture.svg", "dimensions_mm": {"width": 100, "depth": 100, "height": 100}}
    original = {**example, "asset_id": "existing", "product": "Original"}
    conflict = {**example, "asset_id": "shared", "product": "Earlier project index"}
    state_db = tmp_path / "state.sqlite3"
    store = AlmondStore(state_db)
    store.sync_assets([original], library_id="diagram_assets")
    store.sync_assets([conflict], library_id="project_fixture")
    write_manifest(diagram, "diagram_assets", {**original, "product": "Replacement"})
    write_manifest(generated, "generated_assets", conflict)
    with pytest.raises(ValueError, match="shared.*project_fixture.*generated_assets"):
        create_server(state_db=state_db, library_dirs=dirs, send=lambda *_: pytest.fail("Unexpected Rhino call"))
    reopened = AlmondStore(state_db)
    assert reopened.get_asset("existing", library_id="diagram_assets")["product"] == "Original"
    assert reopened.get_asset("shared", library_id="project_fixture")["product"] == "Earlier project index"
    assert reopened.get_asset("shared", library_id="generated_assets") is None


@pytest.mark.parametrize("canonical", ["valid", "outside", "missing"])
def test_model_resource_and_archive_agree_on_canonical_precedence(tmp_path, canonical):
    roots = {key: tmp_path / key for key in ("generated", "drawing", "drafting")}
    legacy = {"asset_id": "fixture", "file": "legacy.glb", "product": "Legacy", "category": "fixture"}
    write_manifest(roots["generated"], "generated_assets", legacy)
    (roots["generated"] / "legacy.glb").touch()
    filename = "../outside.3dm" if canonical == "outside" else "canonical.3dm"
    write_manifest(roots["drawing"], "drawing_assets", {**legacy, "file": filename, "product": "Canonical"})
    (tmp_path / "outside.3dm").touch()
    if canonical == "valid":
        (roots["drawing"] / filename).touch()
    expected = "Canonical" if canonical == "valid" else "Legacy"
    mcp = FastMCP("catalogue-fixture")
    register(mcp, SimpleNamespace(
        DRAWING_LIBRARY_DIR=str(roots["drawing"]), GENERATED_LIBRARY_DIR=str(roots["generated"]),
        DRAFTING_LIBRARY_DIR=str(roots["drafting"]),
        drawing_asset_indexer=AssetLibraryIndexer(roots["drawing"], "drawing_assets", "drawing"),
        generated_asset_indexer=AssetLibraryIndexer(roots["generated"], "generated_assets", "generated"),
    ))

    async def run():
        async with Client(mcp) as client:
            results = await client.read_resource("almond://assets/catalogue")
            payload = json.loads(results[0].text)
            assert payload["assets"][0]["product"] == expected

    asyncio.run(run())
    records = AssetRepository(roots).catalogue()["assets"]
    assert records[0]["name"] == expected
    assert records[0]["source_only"] == (canonical != "valid")


def test_diagram_reload_is_consistent_with_an_existing_server(tmp_path):
    dirs = {key: str(tmp_path / key.removeprefix("RHINO_MCP_")) for key in paths.LIBRARY_DIRS}
    diagram = tmp_path / "DIAGRAM_ASSET_DIR"
    drawing = tmp_path / "DRAWING_ASSET_DIR"
    asset = {"asset_id": "fixture", "file": "old.svg", "product": "Old", "category": "people",
             "dimensions_mm": {"width": 100, "depth": 100, "height": 100}}
    write_manifest(diagram, "diagram_assets", asset)
    (diagram / "old.svg").touch()
    # Bundled diagram and drawing each intentionally contain their own copy.
    write_manifest(drawing, "drawing_assets", asset)
    (drawing / "old.svg").touch()
    state_db = tmp_path / "state.sqlite3"
    server = create_server(state_db=state_db, library_dirs=dirs, send=lambda raw, **_: json.dumps({
        "status": "success", "placed_file": json.loads(raw)["file_path"]}))
    revision = server.features.diagram_asset_indexer.revision
    write_manifest(diagram, "diagram_assets", {**asset, "file": "new.svg", "product": "New"})
    (diagram / "new.svg").touch()
    second = create_server(state_db=state_db, library_dirs=dirs, send=lambda *_: pytest.fail("Unexpected Rhino call"))
    assert second.features.diagram_asset_indexer.revision != revision

    async def run():
        async with Client(server.mcp) as client:
            found = await client.call_tool("diagram_01-get", {"asset_id": "fixture", "field_groups": ["all"]})
            assert json.loads(found.content[0].text)["asset"]["product"] == "New"
            placed = await client.call_tool("diagram_03-place", {"asset_id": "fixture"})
            assert json.loads(placed.content[0].text)["placed_file"] == str(diagram / "new.svg")
            copied = await client.call_tool("asset_06-place", {"asset_id": "fixture"})
            assert json.loads(copied.content[0].text)["placed_file"] == str(drawing / "old.svg")

    asyncio.run(run())


def test_manifest_missing_and_valid_empty_are_distinct(tmp_path):
    missing = AssetLibraryIndexer(tmp_path, "diagram_assets", "diagram")
    write_manifest(tmp_path, "diagram_assets")
    empty = AssetLibraryIndexer(tmp_path, "diagram_assets", "diagram")
    assert not missing.manifest_loaded and missing.revision is None
    assert empty.manifest_loaded and empty.revision
    assert missing.assets == empty.assets == {}
