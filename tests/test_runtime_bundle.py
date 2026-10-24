"""Prevent a source-only update from silently leaving the shipped RHP stale."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_runtime", ROOT / "src/rhp/tools/verify_runtime.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def test_committed_runtime_matches_source_and_binary_hashes():
    for component, relative in runtime.MANIFESTS.items():
        manifest = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert runtime.verify(ROOT, manifest) == []
        assert sorted(manifest["sources"]) == runtime.source_files(ROOT, component)
    runtime.verify_engine_pair(ROOT)


def test_changed_source_requires_new_runtime_record(tmp_path):
    source = tmp_path / "probe.cs"
    source.write_text("before")
    manifest = {"sources": {"probe.cs": runtime.digest(source)}, "files": {}}
    source.write_text("after")
    assert runtime.verify(tmp_path, manifest) == ["probe.cs"]


def test_missing_runtime_file_is_rejected(tmp_path):
    assert runtime.verify(tmp_path, {"sources": {}, "files": {"Bridge.rhp": "missing"}}) == ["Bridge.rhp"]


def test_runtime_record_rejects_missing_dependency_notices(tmp_path, monkeypatch):
    for bundle, name in zip(runtime.BUNDLES, ("RhinoAlmondBridge.rhp", "AlmondCOS.rhp")):
        directory = tmp_path / bundle
        directory.mkdir(parents=True)
        (directory / name).write_bytes(b"fixture")
        (directory / "Almond.Engine.dll").write_bytes(b"same-engine")
    monkeypatch.setattr(runtime.subprocess, "check_output", lambda *args, **kwargs: b"")
    with pytest.raises(RuntimeError, match="required license notices"):
        runtime.record(tmp_path, "bridge")


def test_module_change_invalidates_only_its_owner_but_engine_invalidates_both(tmp_path, monkeypatch):
    sources = ["src/cos/rhp/CosHost.cs", "src/rhp/RhinoTerminal/src/AlmondHost.cs",
               "src/rhp/Engine/SessionFiles.cs", "src/rhp/Engine/tests/Program.cs"]
    for relative in sources:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original", encoding="utf-8")
    monkeypatch.setattr(runtime.subprocess, "check_output", lambda *a, **k: "\0".join(sources).encode())
    manifests = {component: {"sources": {p: runtime.source_digest(tmp_path / p)
                                        for p in runtime.source_files(tmp_path, component)}, "files": {}}
                 for component in runtime.MANIFESTS}
    cos = tmp_path / sources[0]
    cos.write_text("COS-only change", encoding="utf-8")
    assert runtime.verify(tmp_path, manifests["bridge"]) == []
    assert runtime.verify(tmp_path, manifests["cos"]) == [sources[0]]
    cos.write_text("original", encoding="utf-8")
    (tmp_path / sources[2]).write_text("shared change", encoding="utf-8")
    assert runtime.verify(tmp_path, manifests["bridge"]) == [sources[2]]
    assert runtime.verify(tmp_path, manifests["cos"]) == [sources[2]]
    assert all(sources[3] not in m["sources"] for m in manifests.values())
