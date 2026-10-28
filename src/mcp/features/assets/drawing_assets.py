"""Publish a prepared 3DM and its derived drawings as one versioned library entry."""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit
from uuid import uuid4

import numpy as np

from almond_mcp.features.assets import drafting, preparation


@contextmanager
def _manifest_lock(root: Path):
    # An OS lock is released after a crash; a stale marker must not block the library.
    with (root / ".register.lock").open("a+b") as handle:
        if handle.seek(0, 2) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _text(value, label, maximum=300):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters")
    return value.strip()


def _native_triangles(source: Path, output: Path, extract):
    expected = drafting.sha(source.read_bytes())
    result = extract(str(source), str(output))
    if not isinstance(result, dict) or result.get("status") != "success" or result.get("complete") is not True:
        raise ValueError(f"3DM extraction did not complete: {result}")
    if (Path(result.get("source_path", "")).resolve() != source.resolve() or
            Path(result.get("output_path", "")).resolve() != output.resolve()):
        raise ValueError("Native extraction acknowledged different paths")
    if not output.is_file() or output.stat().st_size > 100_000_000:
        raise ValueError("Native triangle artifact is missing or exceeds 100 MB")
    data = output.read_bytes()
    if drafting.sha(data) != str(result.get("triangles_sha256", "")).upper():
        raise ValueError("Native triangle artifact checksum differs from acknowledgement")
    artifact = json.loads(data)
    for record in (result, artifact):
        if (record.get("schema") != "almond-triangles/v1" or record.get("units") != "mm" or
                record.get("up_axis") != "z" or record.get("origin") != "bottom_center" or
                str(record.get("source_sha256", "")).upper() != expected):
            raise ValueError("Native extraction identity, units or source checksum is invalid")
    triangles = np.asarray(artifact.get("triangles_mm"), dtype=float)
    if (triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or
            not 0 < len(triangles) <= drafting.MAX_TRIANGLES or
            not np.isfinite(triangles).all() or np.abs(triangles).max() > 1e9):
        raise ValueError("Invalid native triangle geometry")
    low, high = triangles.min(axis=(0, 1)), triangles.max(axis=(0, 1))
    bounds = np.concatenate((low, high))
    for record in (result, artifact):
        actual = np.asarray(record.get("bounds_mm"), dtype=float)
        if (type(record.get("triangle_count")) is not int or record["triangle_count"] != len(triangles) or
                actual.shape != (6,) or not np.allclose(actual, bounds, rtol=1e-10, atol=1e-6)):
            raise ValueError("Native dimensions or triangle count disagree with the artifact")
    if abs(low[2]) > .01 or np.abs((low[:2] + high[:2]) / 2).max() > .01:
        raise ValueError(read_instruction(__file__, 'response-360'))
    if np.any(high - low <= 0) or drafting.sha(source.read_bytes()) != expected:
        raise ValueError("The source is flat, degenerate or changed during extraction")
    return triangles, expected, bounds.tolist()


def register_prepared_3dm(root: Path, *, source_3dm: str, asset_id: str, name: str,
                          category: str, tags: list[str] | None, description: str,
                          source_url: str, replace_existing: bool, extract,
                          preparation_job: str = "") -> dict:
    """Stage all files, then atomically publish one manifest revision under an OS lock."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", asset_id) or asset_id in {".", ".."}:
        raise ValueError("asset_id must be a stable 1-100 character identifier")
    name, category = _text(name, "name"), _text(category, "category", 100)
    if not isinstance(description, str) or len(description) > 4000:
        raise ValueError("description must be at most 4000 characters")
    if tags is not None and (not isinstance(tags, list) or len(tags) > 32 or
                             any(not isinstance(t, str) or not t.strip() or len(t) > 80 for t in tags)):
        raise ValueError("Supply at most 32 nonempty tags of at most 80 characters")
    if source_url and (len(source_url) > 2000 or urlsplit(source_url).scheme not in {"http", "https"}):
        raise ValueError("source_url must be an HTTP(S) URL")
    source = Path(source_3dm)
    if not source.is_absolute() or source.suffix.lower() != ".3dm" or not source.is_file():
        raise ValueError("Supply an absolute path to the reviewed, prepared 3DM")
    if source.stat().st_size > 100_000_000:
        raise ValueError("3DM exceeds 100 MB limit")
    source_data = source.read_bytes()
    if len(source_data) > 100_000_000:
        raise ValueError("3DM exceeds 100 MB limit")
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    with _manifest_lock(root):
        original = manifest_path.read_bytes() if manifest_path.exists() else None
        manifest = json.loads(original.decode("utf-8-sig")) if original else {"library_id": "drawing_assets", "assets": []}
        if manifest.get("library_id", "drawing_assets") != "drawing_assets" or not isinstance(manifest.get("assets"), list):
            raise ValueError("The selected library is not a valid drawing_assets manifest")
        entries = manifest["assets"]
        matches = [i for i, a in enumerate(entries) if a.get("asset_id") == asset_id]
        if len(matches) > 1:
            raise ValueError(read_instruction(__file__, 'response-372'))
        if matches and not replace_existing:
            raise ValueError(read_instruction(__file__, 'response-373'))
        version = uuid4().hex
        stage = Path(tempfile.mkdtemp(prefix=".register-", dir=root))
        final = root / "registered" / f"{asset_id}-{version}"
        committed = False
        try:
            model = stage / "model.3dm"
            model.write_bytes(source_data)
            evidence = preparation.copy_registration_evidence(preparation_job, source, stage / "preparation") if preparation_job else None
            if evidence and (evidence["reviewed_asset_id"] != asset_id or evidence["reviewed_name"] != name):
                raise ValueError("Registration identity must match the reviewed preparation")
            if evidence and preparation.sha(model) != preparation.sha(source):
                raise ValueError("Prepared source changed before publication")
            source_record = {"evidence_status": "prepared_3dm", "original_path": str(source.resolve()),
                             "visual_review": "not_verified_by_registration"}
            if evidence:
                source_record.update(evidence_status="reviewed_preparation", visual_review=evidence["review"],
                    original_path=evidence["original_path"], original_sha256=evidence["original_sha256"],
                    preparation_record="../preparation/job.json", command=evidence["command"],
                    command_applied=evidence["command_applied"])
            triangles, source_hash, bounds = _native_triangles(model, stage / "triangles.json", extract)
            package = drafting.create_package(model, stage / "drawing", asset_id=asset_id, name=name,
                units="mm", up_axis="z", triangles_mm=triangles,
                source_record=source_record)
            check = drafting.audit_package(stage / "drawing", model)
            if check["status"] != "success":
                raise ValueError(f"Derived drawing package did not verify: {check}")
            (stage / "triangles.json").unlink()
            record = dict(entries[matches[0]]) if matches else {}
            prefix = final.relative_to(root).as_posix()
            record.update(asset_id=asset_id, product=name, category=category, description=description,
                file=prefix + "/model.3dm", sha256=source_hash, format="3dm",
                dimensions_mm=package["manifest"]["source"]["dimensions_mm"],
                drawing_package=prefix + "/drawing", drawing_roles=["plan", "elevation"],
                match_status="measured_geometry", schema="almond-drawing-asset/v1",
                source={"path": str(source.resolve()), "sha256": source_hash,
                        "registered_at": datetime.now(timezone.utc).isoformat(),
                        "visual_review": source_record["visual_review"]},
                spatial={"bounds_source": "measured_native_mesh", "bounds_mm": bounds,
                         "local_aabb": {"min": bounds[:3], "max": bounds[3:]},
                         "units": "mm", "up_axis": "z", "origin": "bottom_center"})
            if evidence:
                record["preparation"] = {**evidence, "directory": prefix + "/preparation"}
                record["source"].update(original_path=evidence["original_path"],
                    original_file=prefix + "/preparation/" + evidence["original_file"],
                    original_sha256=evidence["original_sha256"])
            else:
                record.pop("preparation", None)
            record["tags"] = list(dict.fromkeys(t.strip() for t in tags)) if tags is not None else record.get("tags", [])
            if source_url:
                record["warehouse_url"] = source_url
            record.setdefault("license", "Source terms apply; not cleared for redistribution")
            if matches:
                entries[matches[0]] = record
            else:
                entries.append(record)
            pending = stage / "manifest.pending.json"
            with pending.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if original is not None:
                backups = root / "manifest-backups"
                backups.mkdir(exist_ok=True)
                (backups / f"{version}.json").write_bytes(original)
            final.parent.mkdir(exist_ok=True)
            stage.rename(final)
            os.replace(final / "manifest.pending.json", manifest_path)
            committed = True
            return {"status": "success", "asset": record, "library_dir": str(root),
                    "model_path": str(final / "model.3dm"), "package_dir": str(final / "drawing"),
                    "manifest_path": str(manifest_path), "previous_files_retained": bool(matches)}
        finally:
            if stage.exists():
                shutil.rmtree(stage)
            if not committed and final.exists():
                shutil.rmtree(final)
