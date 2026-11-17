"""Release verification must not trust an incomplete output inventory."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_verifier", ROOT / "src/rhp/tools/verify_runtime.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


@pytest.fixture
def release(tmp_path):
    bundle = "src/rhp/AlmondRhino/plugin-runtime"
    files = {}
    for name in ("AlmondRhino.rhp", "Almond.Engine.dll", "AlmondRhino.deps.json"):
        relative = f"{bundle}/{name}"
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        files[relative] = verifier.digest(path)
    return tmp_path, {"format": 1, "component": "cos", "sources": {}, "files": files}


def test_empty_output_inventory_is_rejected(release):
    root, manifest = release
    manifest["files"] = {}
    assert verifier.verify(root, manifest)


@pytest.mark.parametrize("missing", ["AlmondRhino.rhp", "Almond.Engine.dll"])
@pytest.mark.parametrize("remove_file", [False, True])
def test_required_output_must_be_recorded_and_present(release, missing, remove_file):
    root, manifest = release
    relative = f"src/rhp/AlmondRhino/plugin-runtime/{missing}"
    del manifest["files"][relative]
    if remove_file:
        (root / relative).unlink()
    assert relative in verifier.verify(root, manifest)


def test_additional_unrecorded_files_are_not_forbidden(release):
    root, manifest = release
    (root / "src/rhp/AlmondRhino/plugin-runtime/additional.txt").write_text("allowed")
    assert verifier.verify(root, manifest) == []


@pytest.mark.parametrize("damage", ["missing", "modified"])
def test_recorded_optional_file_damage_is_detected(release, damage):
    root, manifest = release
    relative = "src/rhp/AlmondRhino/plugin-runtime/AlmondRhino.deps.json"
    if damage == "missing":
        (root / relative).unlink()
    else:
        (root / relative).write_text("different")
    assert relative in verifier.verify(root, manifest)


def test_cli_rejects_empty_inventory(release, monkeypatch):
    root, manifest = release
    manifest["files"] = {}
    destination = root / "src/cos/runtime-manifest.json"
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(verifier, "ROOT", root)
    # This test isolates output validation; source inventory has its own gate.
    monkeypatch.setattr(verifier, "source_files", lambda *_: [])
    monkeypatch.setattr("sys.argv", ["verify_runtime.py", "--component", "cos"])
    with pytest.raises(SystemExit, match="runtime differs"):
        verifier.main()


@pytest.mark.parametrize("missing", [
    "RhinoAlmondBridge.rhp", "Almond.Engine.dll", "LICENSE", "archive/ATTRIBUTION.txt",
])
def test_bridge_required_outputs_cannot_be_omitted(tmp_path, missing):
    bundle = "src/rhp/RhinoAlmondBridge/plugin-runtime"
    names = (
        "RhinoAlmondBridge.rhp", "Almond.Engine.dll", "LICENSE", "THIRD-PARTY-NOTICES.md",
        "archive/THIRD-PARTY-NOTICES.md", "archive/ATTRIBUTION.txt", "archive/ui/vendor/LICENSE",
        "archive/ui/vendor/THIRD-PARTY-LICENSES.txt", "licenses/Porta.Pty-LICENSE.txt",
        "licenses/Vanara-LICENSE.txt", "licenses/addon-fit-LICENSE.txt", "licenses/xterm-LICENSE.txt",
    )
    files = {}
    for name in names:
        path = tmp_path / bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
        files[f"{bundle}/{name}"] = verifier.digest(path)
    manifest = {"format": 1, "component": "bridge", "sources": {}, "files": files}
    assert verifier.verify(tmp_path, manifest) == []
    relative = f"{bundle}/{missing}"
    del files[relative]
    assert relative in verifier.verify(tmp_path, manifest)
