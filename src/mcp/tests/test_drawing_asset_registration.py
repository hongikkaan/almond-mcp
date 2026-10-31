"""Registration publication, native proof and the public 3DM -> drawing -> placement flow."""
import asyncio
import json
from pathlib import Path

import ezdxf
import numpy as np
import pytest

from almond_mcp.features.assets import drawing_assets as assets, drafting
from almond_mcp.features.assets.asset_repository import AssetRepository
from almond_mcp.retrieval_store import AlmondStore
from test_generated_assets import load_server_module


def extract_box(source_path, output_path):
    # Native extraction is covered separately in actual Rhino. This boundary
    # fixture gives the Python publisher an analytic 2 x 4 x 3 mm solid.
    points = np.array([[x, y, z] for x in (-1, 1) for y in (-2, 2) for z in (0, 3)])
    faces = [[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],
             [2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]]
    metadata = {"schema": "almond-triangles/v1", "units": "mm", "up_axis": "z", "origin": "bottom_center",
                "source_sha256": drafting.sha(Path(source_path).read_bytes()), "triangle_count": 12,
                "bounds_mm": [-1, -2, 0, 1, 2, 3]}
    output = Path(output_path)
    output.write_text(json.dumps({**metadata, "triangles_mm": points[faces].tolist()}), encoding="utf-8")
    return {**metadata, "status": "success", "complete": True, "source_path": source_path,
            "output_path": output_path, "triangles_sha256": drafting.sha(output.read_bytes())}


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "drawing"
    root.mkdir()
    manifest = {"library_id": "drawing_assets", "custom_header": "retain", "assets": [
        {"asset_id": "unrelated", "file": "legacy.svg", "product": "Retain", "license": "original terms",
         "dimensions_mm": {"width": 10, "depth": 10, "height": 1}}]}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    source = tmp_path / "prepared.3dm"
    source.write_bytes(b"prepared-source-v1")
    return root, source


def register(library, **overrides):
    root, source = library
    args = dict(source_3dm=str(source), asset_id="drawing-fixture", name="Fixture", category="furniture",
                tags=["box"], description="Reviewed assembly", source_url="", replace_existing=False,
                extract=extract_box)
    args.update(overrides)
    return assets.register_prepared_3dm(root, **args)


def test_publishes_linked_source_dimensions_and_real_dxf_without_replacing_other_assets(library):
    root, source = library
    before = json.loads((root / "manifest.json").read_text())
    result = register(library)
    record = result["asset"]
    package = Path(result["package_dir"])
    assert Path(result["model_path"]).read_bytes() == source.read_bytes()
    assert record["dimensions_mm"] == {"width": 2, "depth": 4, "height": 3}
    assert json.loads((package / "dimensions.json").read_text())["asset_id"] == record["asset_id"]
    assert drafting.audit_package(package, Path(result["model_path"]))["source_geometry"] == "source_file_current"
    assert len(list(package.glob("*.dxf"))) == 6
    plan = ezdxf.readfile(package / "plan-1-50.dxf")
    assert plan.units == 4 and not plan.audit().errors
    vertices = np.array(list(plan.modelspace())[0].get_points())
    assert np.ptp(vertices[:, 0]) == pytest.approx(2)
    assert np.ptp(vertices[:, 1]) == pytest.approx(4)
    after = json.loads((root / "manifest.json").read_text())
    assert after["assets"][0] == before["assets"][0] and after["custom_header"] == "retain"
    assert list((root / "manifest-backups").glob("*.json"))
    repo = AssetRepository({"generated": root / "unused", "drawing": root, "drafting": root / "unused-drafts"})
    joined = repo.records[record["asset_id"]]
    assert joined["kind"] == "model" and joined["format"] == "3dm" and joined["available"]
    assert joined["drawing"]["source"]["asset_id"] == joined["id"] and joined["preview"]
    assert joined["drawing"]["dimensions"] in repo.files


def test_explicit_revision_retains_previous_source_and_publishes_new_file(library):
    first = register(library)
    previous = Path(first["model_path"])
    with pytest.raises(ValueError, match="already exists"):
        register(library)
    library[1].write_bytes(b"prepared-source-v2")
    second = register(library, replace_existing=True)
    assert second["previous_files_retained"] and second["model_path"] == first["model_path"]
    assert second["source_path_preserved"] and second["linked_instances_may_update"]
    assert (library[0] / second["asset"]["previous_source"]["file"]).read_bytes() == b"prepared-source-v1"
    assert Path(second["model_path"]).read_bytes() == b"prepared-source-v2"
    assert second["asset"]["sha256"] != first["asset"]["sha256"]
    Path(second["model_path"]).write_bytes(b"tampered")
    assert drafting.audit_package(Path(second["package_dir"]), Path(second["model_path"]))["status"] == "error"


def test_manifest_reload_prunes_removed_assets_from_index_and_retrieval(library, tmp_path):
    server = load_server_module()
    root, _ = library
    indexer = server.AssetLibraryIndexer(str(root), "drawing_assets", "drawing")
    store = AlmondStore(tmp_path / "index-reload.sqlite3")
    assert indexer.get("unrelated") is not None
    store.sync_assets(list(indexer.assets.values()), library_id="drawing_assets")
    assert store.search_assets(library_id="drawing_assets")["total"] == 1

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    indexer._load()
    assert indexer.get("unrelated") is None
    assert indexer.search() == []
    store.sync_assets(list(indexer.assets.values()), library_id="drawing_assets")
    assert store.search_assets(library_id="drawing_assets")["total"] == 0


@pytest.mark.parametrize("change", ["hash", "source", "units", "count", "incomplete"])
def test_mismatched_native_proof_never_publishes(library, change):
    root, _ = library
    original = (root / "manifest.json").read_bytes()
    def damaged(source, output):
        reply = extract_box(source, output)
        if change == "hash":
            Path(output).write_text("{}")
        elif change == "source":
            reply["source_path"] = source + ".other"
        elif change == "units":
            reply["units"] = "m"
        elif change == "count":
            reply["triangle_count"] = 11
        else:
            reply["complete"] = False
        return reply
    with pytest.raises(ValueError):
        register(library, extract=damaged)
    assert (root / "manifest.json").read_bytes() == original
    assert not list(root.glob(".register-*")) and not (root / "registered").exists()


def test_failed_manifest_swap_retains_original_and_removes_only_new_staged_files(library, monkeypatch):
    root, source = library
    original = (root / "manifest.json").read_bytes()
    def fail(*args):
        raise OSError("publication failed")
    monkeypatch.setattr(assets.os, "replace", fail)
    with pytest.raises(OSError, match="publication failed"):
        register(library)
    assert source.read_bytes() == b"prepared-source-v1"
    assert (root / "manifest.json").read_bytes() == original
    assert not list((root / "registered").iterdir())


def test_manifest_lock_rejects_competing_writer_and_releases_after_failure(library):
    with assets._manifest_lock(library[0]):
        with pytest.raises(OSError):
            register(library)
    assert register(library)["status"] == "success"


def test_public_registration_query_resource_and_placement_share_one_id(library, tmp_path, monkeypatch):
    from fastmcp import Client
    server = load_server_module()
    root, source = library
    monkeypatch.setattr(server, "DRAWING_LIBRARY_DIR", str(root))
    monkeypatch.setattr(server, "drawing_asset_indexer", server.AssetLibraryIndexer(str(root), "drawing_assets", "drawing"))
    monkeypatch.setattr(server, "retrieval_store", AlmondStore(tmp_path / "scene.sqlite3"))
    calls = []
    def native(payload, **kwargs):
        request = json.loads(payload)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_asset_extract": 2, "drawing_asset_linked": 1}})
        if request["type"] == "drawing_asset_extract":
            return json.dumps(extract_box(request["source_path"], request["output_path"]))
        assert request["type"] == "place_drawing_asset"
        assert request["metadata"]["sha256"] == drafting.sha(Path(request["file_path"]).read_bytes())
        assert request["position"] == [1, 2, 3]
        return json.dumps({"status": "success", "object_guid": "fixture"})
    monkeypatch.setattr(server, "_send_and_receive", native)
    async def run():
        async with Client(server.mcp) as client:
            names = {t.name for t in await client.list_tools()}
            assert {"register_drawing_asset", "place_drawing_asset", "validate_structure", "generate_asset_drawing_views"} <= names
            assert not {"list_assets", "place_asset", "get_asset_sources"} & names
            result = await client.call_tool("register_drawing_asset", {
                "source_3dm": str(source), "asset_id": "drawing-fixture", "name": "Fixture"})
            registered = result.structured_content
            assert registered["status"] == "success" and registered["live_index_refreshed"], registered.get("message", registered)
            record = json.loads(server.get_drawing_asset("drawing-fixture", include_ids=True))
            assert record["status"] == "success" and "asset_id" not in record["asset"] and record["asset"]["product"] == "Fixture"
            drawing = await client.call_tool("get_asset_drawing", {"asset_id": "drawing-fixture"})
            assert "asset_id" not in drawing.structured_content["manifest"]["source"]
            svg = await client.read_resource("almond://drawing/drawing-fixture/drawing/plan/50")
            assert svg[0].mime_type == "image/svg+xml"
            assert json.loads(server.place_drawing_asset("drawing-fixture", x=1, y=2, z=3))["status"] == "success"
            return registered
    registered = asyncio.run(run())
    assert [c["type"] for c in calls] == ["get_rhino_context", "drawing_asset_extract", "get_rhino_context", "place_drawing_asset"]
    def unavailable(*args, **kwargs):
        raise RuntimeError("index unavailable")
    monkeypatch.setattr(server.drawing_asset_indexer, "_load", unavailable)
    result = server.register_drawing_asset(str(source), "drawing-another", "Another")
    assert result["status"] == "error" and result["registration_applied"] and not result["live_index_refreshed"]
    assert Path(result["model_path"]).is_file() and Path(registered["model_path"]).is_file()
