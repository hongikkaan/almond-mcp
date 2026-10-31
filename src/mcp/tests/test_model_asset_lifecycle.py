"""Model identity, editable linked source publication and revision-bound preparation."""
import json
from pathlib import Path
import re
import os
import subprocess
import sys

import pytest

from almond_mcp.features.assets import drawing_assets, drafting, preparation
from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from almond_mcp.features.assets.model_index import ModelAssetIndex
from almond_mcp.features.assets.asset_repository import AssetRepository
from test_drawing_asset_registration import extract_box, library, register


def test_refresh_preserves_linked_path_and_previous_revision(library):
    first = register(library)
    source = Path(first["model_path"])
    old_package = Path(first["package_dir"])
    source.write_bytes(b"edited-linked-model")
    assert drafting.audit_package(old_package, source)["source_geometry"] == "stale"
    refreshed = drawing_assets.refresh_registered_asset(library[0], "drawing-fixture", extract=extract_box)
    assert refreshed["model_path"] == str(source) and refreshed["source_path_preserved"]
    assert source.read_bytes() == b"edited-linked-model"
    assert old_package.is_dir() and Path(refreshed["package_dir"]) != old_package
    assert (library[0] / first["asset"]["published_source"]).read_bytes() == b"prepared-source-v1"
    assert drafting.audit_package(Path(refreshed["package_dir"]), source)["source_geometry"] == "source_file_current"
    assert refreshed["asset"]["sha256"] == drafting.sha(source.read_bytes())
    assert not refreshed["rhino_linked_instances_updated"]


def test_refresh_rejects_concurrent_source_edit_without_publishing(library):
    first = register(library)
    source = Path(first["model_path"])
    source.write_bytes(b"first edit")
    manifest = (library[0] / "manifest.json").read_bytes()
    def concurrent(snapshot, output):
        receipt = extract_box(snapshot, output)
        source.write_bytes(b"later user edit")
        return receipt
    with pytest.raises(ValueError, match="changed while refresh"):
        drawing_assets.refresh_registered_asset(library[0], "drawing-fixture", extract=concurrent)
    assert source.read_bytes() == b"later user edit"
    assert (library[0] / "manifest.json").read_bytes() == manifest


def test_source_replacement_rolls_back_only_its_own_bytes(library, monkeypatch):
    first = register(library)
    source = Path(first["model_path"])
    original_manifest = (library[0] / "manifest.json").read_bytes()
    library[1].write_bytes(b"replacement")
    real_replace = drawing_assets.os.replace
    def fail_manifest(src, dst):
        if Path(dst).name == "manifest.json":
            raise OSError("manifest write failed")
        return real_replace(src, dst)
    monkeypatch.setattr(drawing_assets.os, "replace", fail_manifest)
    with pytest.raises(OSError, match="manifest write failed"):
        register(library, replace_existing=True)
    assert source.read_bytes() == b"prepared-source-v1"
    assert (library[0] / "manifest.json").read_bytes() == original_manifest
    def edit_then_fail(src, dst):
        if Path(dst).name == "manifest.json":
            source.write_bytes(b"concurrent user edit")
            raise OSError("manifest write failed")
        return real_replace(src, dst)
    monkeypatch.setattr(drawing_assets.os, "replace", edit_then_fail)
    with pytest.raises(drawing_assets.PublicationUnconfirmed, match="Concurrent source edit preserved"):
        register(library, replace_existing=True)
    assert source.read_bytes() == b"concurrent user edit"
    assert (library[0] / "manifest.json").read_bytes() == original_manifest
    assert list((library[0] / "registered").glob("*/manifest.pending.json"))


def test_unified_index_prefers_registered_3dm_and_keeps_legacy_provenance(library, tmp_path):
    root, _ = library
    legacy = tmp_path / "generated"
    legacy.mkdir()
    (legacy / "old.glb").write_bytes(b"preserved source")
    original = {"asset_id": "drawing-fixture", "file": "old.glb", "product": "Old", "category": "furniture"}
    (legacy / "manifest.json").write_text(json.dumps({"library_id": "generated_assets", "assets": [original]}))
    old = AssetLibraryIndexer(str(legacy), "generated_assets", "legacy")
    drawing = AssetLibraryIndexer(str(root), "drawing_assets", "models")
    record = ModelAssetIndex(drawing, old).get("drawing-fixture")
    assert record["source_only"] and not record["file_available"]
    first = register(library, legacy_source=original)
    drawing._load()
    record = ModelAssetIndex(drawing, old).get("drawing-fixture")
    assert record["file_available"] and record["model_status"] == "ready"
    assert record["legacy_source"] == original and record["drawing_ready"]
    Path(first["model_path"]).write_bytes(b"user source edit")
    record = ModelAssetIndex(drawing, old).get("drawing-fixture")
    assert record["model_status"] == "needs_refresh" and record["drawing_status"] == "stale"
    assert (legacy / "old.glb").read_bytes() == b"preserved source"


def test_publisher_accepts_preserved_origin_and_records_measured_bounds(library):
    def offset_box(source, output):
        result = extract_box(source, output)
        artifact = json.loads(Path(output).read_text())
        for triangle in artifact["triangles_mm"]:
            for point in triangle:
                point[0] += 100
                point[2] += 40
        bounds = [99, -2, 40, 101, 2, 43]
        artifact.update(bounds_mm=bounds, origin="preserved")
        Path(output).write_text(json.dumps(artifact))
        result.update(bounds_mm=bounds, origin="preserved", triangles_sha256=drafting.sha(Path(output).read_bytes()))
        return result
    result = register(library, extract=offset_box)
    assert result["asset"]["spatial"]["bounds_mm"] == [99, -2, 40, 101, 2, 43]
    assert result["asset"]["spatial"]["origin"] == "preserved"


def fake_preparation_sender(calls):
    def send(payload, **kwargs):
        request = json.loads(payload)
        matched = re.search(r'Read<Config>\(@"([^\"]+)"\)', request["script"])
        job = Path(matched.group(1)).parent
        record = json.loads((job / "job.json").read_text())
        stage = record["stage"]
        calls.append(stage)
        output = job / preparation.OUTPUTS[stage]
        if stage != "verify":
            output.write_bytes(b"native 3dm copy")
        preview = job / (stage + ".png")
        preview.write_bytes(b"preview")
        report = {"schema": preparation.SCHEMA, "status": "success", "stage": stage,
                  "operation_id": record["operation_id"], "source_sha256": record["source_sha256"],
                  "summary": {"file": str(output), "sha256": preparation.sha(output), "units": "Meters",
                              "object_count": 1, "parts": [{"object_id": "top-level-block", "type": "InstanceReference"}]},
                  "previews": [{"file": preview.name, "sha256": preparation.sha(preview)}]}
        (job / (stage + ".json")).write_text(json.dumps(report))
        return {"status": "success"}
    return send


def test_preparation_can_register_without_forced_normalization_or_merge(tmp_path):
    original = tmp_path / "assembly.3dm"
    original.write_bytes(b"original assembly")
    calls = []
    args = {"artifact_dir": tmp_path, "sender": fake_preparation_sender(calls)}
    inspected = preparation.prepare(stage="inspect", source_file=str(original), **args)
    job = inspected["job_dir"]
    verified = preparation.prepare(stage="verify", job_dir=job, **args)
    ready = preparation.prepare(stage="verify", job_dir=job, review={"vision_reviewed": True,
        "final_sha256": verified["review_targets"]["final_sha256"], "name": "Assembly", "asset_id": "assembly"}, **args)
    evidence = preparation.copy_registration_evidence(job, Path(ready["source_3dm"]), tmp_path / "evidence")
    assert ready["ready_for_registration"] and calls == ["inspect", "verify"]
    assert evidence["command_applied"] is False and evidence["reviewed_asset_id"] == "assembly"
    assert original.read_bytes() == b"original assembly"
    preparation.prepare(stage="status", job_dir=job, **args)
    assert calls == ["inspect", "verify"]


def test_requested_asset_does_not_hash_other_models_and_exposes_controlled_paths(library, monkeypatch):
    from types import SimpleNamespace
    from almond_mcp.features.assets import model_index
    first = register(library)
    indexer = AssetLibraryIndexer(str(library[0]), "drawing_assets", "models")
    unrelated = library[0] / "unrelated.3dm"
    unrelated.write_bytes(b"locked")
    indexer.assets["other"] = {"asset_id": "other", "file": "unrelated.3dm", "_resolved_file": str(unrelated),
                               "file_available": True, "sha256": "unused"}
    model_index._VERIFIED.clear()
    real_hash = drafting.file_sha
    reads = []
    def observed_hash(path):
        reads.append(Path(path))
        if Path(path) == unrelated:
            raise PermissionError("locked")
        return real_hash(path)
    monkeypatch.setattr(drafting, "file_sha", observed_hash)
    index = ModelAssetIndex(indexer, SimpleNamespace(assets={}))
    record = index.public_record(index.get("drawing-fixture"))
    assert record["model_path"] == first["model_path"] and record["source_path"] == first["model_path"]
    assert reads == [Path(first["model_path"])]
    assert index.get("other")["model_status"] == "unverified"
    assert index.get("drawing-fixture")["drawing_ready"]
    assert reads.count(Path(first["model_path"])) == 1


def test_snapshot_cli_emits_private_allowlist_without_changing_sources(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    source = root / "symbol.svg"
    source.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({"assets": [{"asset_id": "symbol", "file": "symbol.svg"}]}))
    env = {**os.environ, "RHINO_MCP_DRAWING_ASSET_DIR": str(root),
           "RHINO_MCP_GENERATED_ASSET_DIR": str(tmp_path / "empty-generated"),
           "RHINO_MCP_DRAFTING_DIR": str(tmp_path / "empty-drafts")}
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "almond_mcp.features.assets.asset_repository", "--snapshot"],
                            env=env, capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["catalogue"]["counts"]["assets"] == 1
    item = next(iter(payload["files"].values()))
    assert Path(item["path"]) == source and Path(item["root"]) == root
    assert item["size"] == source.stat().st_size and item["mtime_ns"] == source.stat().st_mtime_ns
    assert source.read_text() == '<svg xmlns="http://www.w3.org/2000/svg"/>'


def test_snapshot_leaves_model_currentness_unverified_without_hashing_library(library, tmp_path, monkeypatch):
    from almond_mcp.features.assets.asset_repository import snapshot
    register(library)
    repository = AssetRepository({"drawing": library[0], "generated": tmp_path / "no-generated",
                                  "drafting": tmp_path / "no-drafts"})
    def unexpected_read(*args, **kwargs):
        raise AssertionError("Panel listing must not hash every source model")
    monkeypatch.setattr(drafting, "file_sha", unexpected_read)
    payload = snapshot(repository)
    record = next(asset for asset in payload["catalogue"]["assets"] if asset["id"] == "drawing-fixture")
    assert record["model_status"] == "unverified" and not record["drawing_ready"]
    assert record["model"] in payload["files"]


def test_shipped_drawing_3d_sources_require_conversion_before_any_native_placement(tmp_path):
    from types import SimpleNamespace
    from test_asset_repository import repository, REPO
    from test_assets_feature import make_feature
    _, _, context, exports = make_feature(tmp_path)
    drawing = AssetLibraryIndexer(str(REPO / "asset/drawing/DrawingAssetfiles"), "drawing_assets", "shipped drawing")
    context["drawing_asset_indexer"] = drawing
    def forbidden(*args, **kwargs):
        raise AssertionError("A non-3DM model must not reach Rhino placement")
    context["_send_and_receive"] = forbidden
    unified = ModelAssetIndex(drawing, SimpleNamespace(assets={}))
    archive = repository()
    models = [asset for asset in drawing.assets.values() if Path(asset["file"]).suffix.lower() == ".skp"]
    assert len(models) == 4
    for original in models:
        asset_id = original["asset_id"]
        record = unified.public_record(unified.get(asset_id))
        assert record["asset_kind"] == "model" and record["model_status"] == "needs_conversion"
        assert record["source_only"] and not record["file_available"] and "model_path" not in record
        assert record["source_path"] == original["_resolved_file"]
        archived = archive.records[asset_id]
        assert archived["kind"] == "model" and archived["source_only"] and not archived["available"]
        assert archived["model"] is None
        assert archived["source_available"] == Path(original["_resolved_file"]).is_file()
        assert not archived["source_available"] or archived["source_file"] in archive.files
        rejected = json.loads(exports["place_drawing_asset"](asset_id))
        assert rejected["error_code"] == "asset_needs_conversion" and rejected["mutation_state"] == "not_started"
    for original in drawing.assets.values():
        if Path(original["file"]).suffix.lower() == ".svg":
            assert unified.get(original["asset_id"])["asset_kind"] == "drawing"
            assert not unified.get(original["asset_id"]).get("source_only", False)


@pytest.mark.parametrize("name,mode,model", [("mesh.obj", "", True), ("model.fbx", "", True),
    ("plan.dxf", "2d_plan", False), ("plan.dwg", "", False), ("solid.dwg", "3d_model", True),
    ("symbol.svg", "", False), ("texture.png", "", False)])
def test_3d_source_detection_preserves_actual_2d_formats(name, mode, model):
    from almond_mcp.features.assets.model_index import is_model_source
    assert is_model_source({"file": name, "geometry_mode": mode}) is model


def test_http_metadata_excludes_local_paths_without_rewriting_manifest(library):
    first = register(library)
    manifest_path = library[0] / "manifest.json"
    original = manifest_path.read_bytes()
    repository = AssetRepository({"drawing": library[0], "generated": library[0] / "absent-generated",
                                  "drafting": library[0] / "absent-drafts"})
    record = repository.records["drawing-fixture"]
    assert "path" not in record["metadata"]["source"]
    assert record["metadata"]["file"] == first["asset"]["file"]
    assert str(library[1]) not in json.dumps(repository.catalogue(verify=False))
    assert str(library[1]) not in json.dumps(record)
    assert manifest_path.read_bytes() == original
