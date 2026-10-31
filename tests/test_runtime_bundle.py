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


def test_sdk_selection_is_a_shared_runtime_build_input(tmp_path, monkeypatch):
    source = tmp_path / "global.json"
    source.write_text('{"sdk":{"version":"8.0.100","rollForward":"latestFeature"}}', encoding="utf-8")
    monkeypatch.setattr(runtime.subprocess, "check_output", lambda *a, **k: b"global.json\0")
    for component in runtime.MANIFESTS:
        assert runtime.source_files(tmp_path, component) == ["global.json"]
        manifest = {"sources": {"global.json": runtime.source_digest(source)}, "files": {}}
        source.write_text('{"sdk":{"version":"8.0.100","rollForward":"latestMajor"}}', encoding="utf-8")
        assert runtime.verify(tmp_path, manifest) == ["global.json"]
        source.write_text('{"sdk":{"version":"8.0.100","rollForward":"latestFeature"}}', encoding="utf-8")


@pytest.mark.parametrize("relative", [
    "src/rhp/RhinoTerminal/src/web/terminal.html",
    "src/mcp/features/context/native/BlockAnalysis.cs",
    "src/mcp/features/components/native/SolidIntersections.cs",
    "src/mcp/features/modeling/native/PlanarFaceEditing.cs",
    "src/mcp/features/assets/native/FurnitureAssetManager.cs",
    "src/mcp/features/drawings/native/DrawingStyleManager.cs",
    "src/mcp/features/grasshopper/native/GhDefinitionRunner.cs",
    "src/mcp/features/exchange/native/GlbExporter.cs",
    "src/mcp/features/structure/native/NativeSolver.cs",
])
def test_bridge_source_change_invalidates_runtime(tmp_path, monkeypatch, relative):
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text("<button>before</button>", encoding="utf-8")
    monkeypatch.setattr(runtime.subprocess, "check_output", lambda *a, **k: relative.encode())
    assert runtime.source_files(tmp_path, "bridge") == [relative]
    assert runtime.source_files(tmp_path, "cos") == []
    manifest = {"sources": {relative: runtime.source_digest(source)}, "files": {}}
    source.write_text("<button>almond</button>", encoding="utf-8")
    assert runtime.verify(tmp_path, manifest) == [relative]


def test_missing_runtime_file_is_rejected(tmp_path):
    assert runtime.verify(tmp_path, {"sources": {}, "files": {"Bridge.rhp": "missing"}}) == ["Bridge.rhp"]


def test_runtime_record_rejects_missing_dependency_notices(tmp_path, monkeypatch):
    for bundle, name in zip(runtime.BUNDLES, ("RhinoAlmondBridge.rhp", "AlmondRhino.rhp")):
        directory = tmp_path / bundle
        directory.mkdir(parents=True)
        (directory / name).write_bytes(b"fixture")
        (directory / "Almond.Engine.dll").write_bytes(b"same-engine")
    monkeypatch.setattr(runtime.subprocess, "check_output", lambda *args, **kwargs: b"")
    with pytest.raises(RuntimeError, match="required license notices"):
        runtime.record(tmp_path, "bridge")


def test_module_change_invalidates_only_its_owner_but_engine_invalidates_both(tmp_path, monkeypatch):
    sources = ["src/cos/rhp/RhinoHost.cs", "src/rhp/RhinoTerminal/src/AlmondHost.cs",
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
