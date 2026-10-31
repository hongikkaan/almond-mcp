"""Verify shipped generated-model paths, byte hashes and provenance offline.

This does not inspect AppData, download community assets, or contact Rhino.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "asset/models/GeneratedAssetfiles"


def verify():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    assert manifest["library_id"] == provenance["library_id"] == "generated_assets"
    records = manifest["assets"]
    ids = [record["asset_id"] for record in records]
    assert ids and len(ids) == len(set(ids))
    assert set(ids) == set(provenance["assets"])
    for record in records:
        relative = Path(record["file"])
        assert not relative.is_absolute() and ".." not in relative.parts
        path = (ROOT / relative).resolve(strict=True)
        assert path.is_relative_to(ROOT.resolve())
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual.lower() == record["sha256"].lower(), record["asset_id"]
        assert provenance["assets"][record["asset_id"]], record["asset_id"]
    return len(records)


if __name__ == "__main__":
    print(f"Verified {verify()} generated model files against manifest and provenance.")
