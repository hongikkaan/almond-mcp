"""Verify the delivered runtime and its offline registration transaction."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = Path("src/rhp/tools/verify_runtime.py")


def verify_runtime(root, *arguments):
    return subprocess.run([sys.executable, "-B", "-X", "utf8", str(VERIFIER), *arguments], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", timeout=60)


def test_shipped_runtime_manifest():
    result = verify_runtime(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_engine_digest_mismatch(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, timeout=15)
    verifier = tmp_path / VERIFIER
    verifier.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / VERIFIER, verifier)
    (tmp_path / "src/beyond").mkdir()
    bundle = tmp_path / "src/rhp/AlmondRhino/plugin-runtime"
    bundle.mkdir(parents=True)
    (bundle / "AlmondRhino.rhp").write_bytes(b"fixture plugin")
    engine = bundle / "Almond.Engine.dll"
    engine.write_bytes(b"recorded fixture engine")
    result = verify_runtime(tmp_path, "--component", "beyond", "--record")
    assert result.returncode == 0, result.stdout + result.stderr

    engine.write_bytes(b"changed fixture engine")
    result = verify_runtime(tmp_path, "--component", "beyond")
    assert result.returncode != 0
    assert "runtime differs" in result.stderr and "Almond.Engine.dll" in result.stderr


def run_registration(tmp_path, script, *options):
    shell = shutil.which("pwsh") or shutil.which("powershell")
    script_path = ROOT / "tests/fixtures" / script
    args = [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script_path),
            "-Scratch", str(tmp_path), *options]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("options", [(), ("-FailOnSecondPlugin",)], ids=["commit", "rollback"])
def test_registration_upgrade(tmp_path, options):
    run_registration(tmp_path, "runtime_upgrade.ps1", *options)


@pytest.mark.parametrize("options", [(), ("-ReusePid",)], ids=["loaded", "reused-pid"])
def test_registration_restore(tmp_path, options):
    run_registration(tmp_path, "temporary_registration.ps1", *options)
