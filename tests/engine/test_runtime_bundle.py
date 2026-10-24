"""Prevent a source-only update from silently leaving the shipped RHP stale."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verify_runtime", ROOT / "src/rhp/tools/verify_runtime.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def test_committed_runtime_matches_source_and_binary_hashes():
    manifest = json.loads((ROOT / runtime.MANIFEST).read_text(encoding="utf-8"))
    assert runtime.verify(ROOT, manifest) == []
    assert runtime.digest(ROOT / runtime.BUNDLES[0] / "Almond.Engine.dll") == runtime.digest(
        ROOT / runtime.BUNDLES[1] / "Almond.Engine.dll")


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
        runtime.record(tmp_path)
