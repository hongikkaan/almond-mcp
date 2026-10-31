"""Native archive decoder must accept the shipped asset and reject corruption."""
import json
import os
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.archive_host


def run(path, asset_id):
    return subprocess.run([os.environ["ALMOND_ARCHIVE_TEST_HOST"], "--mesh", str(path), asset_id],
                          capture_output=True, text=True, encoding="utf-8")


def test_shipped_asset_and_invalid_inputs(tmp_path):
    original = ROOT / "asset/models/GeneratedAssetfiles/models/gen-office-chair-1.glb"
    result = run(original, original.stem)
    assert result.returncode == 0, result.stderr
    decoded = json.loads(result.stdout)
    assert decoded["Passport"]["asset_id"] == original.stem
    assert decoded["TriangleCount"] > 0
    assert run(original, "wrong-id").returncode != 0
    truncated = tmp_path / "truncated.glb"
    truncated.write_bytes(original.read_bytes()[:-1])
    assert run(truncated, original.stem).returncode != 0
