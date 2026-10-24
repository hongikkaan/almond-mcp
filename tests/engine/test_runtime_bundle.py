"""Prevent a source-only update from silently leaving the shipped RHP stale."""
import importlib.util
import json
from pathlib import Path

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
