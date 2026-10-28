"""Reviewed, revision-bound asset preparation; publication stays in drawing_assets.

Adapted from the user's almond-asset-converter installation (2026-10-19).
The helpers execute through the bound runtime. Status and pagination only read
durable reports and never repeat an import, command or native operation.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4


SCHEMA = "almond-asset-preparation/v1"
GROUPS = {"summary", "parts", "previews", "provenance", "all"}
STAGES = {"inspect", "normalize", "merge", "verify", "status"}
UNITS = {"", "mm", "cm", "m", "in", "ft"}
UNITLESS = {".obj", ".stl", ".ply", ".off"}
MAX_BYTES = 100_000_000
TEMPLATES = Path(__file__).with_name("preparation_templates")
OUTPUTS = {"inspect": "inspected.3dm", "normalize": "normalized.3dm", "merge": "final.3dm", "verify": "final.3dm"}
STATES = {"inspect": "inspected", "normalize": "normalized", "merge": "merged", "verify": "verified"}
PREREQUISITES = {"normalize": "inspected", "merge": "normalized", "verify": "merged"}


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest().upper()


def _write(path: Path, value) -> None:
    pending = path.with_name(path.name + ".pending-" + uuid4().hex)
    try:
        with pending.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
    finally:
        if pending.exists():
            pending.unlink()


def _read(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 8_000_000:
        raise ValueError("Preparation record is missing or exceeds 8 MB: " + path.name)
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("Preparation record must be a JSON object")
    return result


def _inside(root: Path, candidate: Path) -> Path:
    for part in (candidate, *candidate.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Preparation paths cannot traverse filesystem links")
        if part == root:
            break
    result = candidate.resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Preparation job must stay inside the selected artifact directory")
    return result


def _job(root: Path, value: str) -> tuple[Path, dict]:
    if not value:
        raise ValueError("Supply job_dir returned by inspect")
    path = _inside(root, Path(value))
    record = _read(path / "job.json")
    if record.get("schema") != SCHEMA or Path(record.get("job_dir", "")).resolve() != path:
        raise ValueError("Preparation job identity does not match its directory")
    return path, record


@contextmanager
def _lock(job: Path):
    with (job / ".prepare.lock").open("a+b") as handle:
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


def _match(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or path.stat().st_size > MAX_BYTES or not expected or sha(path) != expected:
        raise ValueError(label + " changed or its recorded SHA256 is missing")


def _report(job: Path, record: dict, stage: str) -> dict:
    saved = record.get("stages", {}).get(stage)
    if not isinstance(saved, dict):
        raise ValueError("Missing completed " + stage + " stage")
    path = _inside(job, job / (stage + ".json"))
    _match(path, saved.get("report_sha256", ""), stage + " report")
    script = _inside(job, job / (stage + (".py" if stage == "merge" else ".cs")))
    _match(script, saved.get("script_sha256", ""), stage + " command")
    report = _read(path)
    _check_report(job, record, stage, saved["operation_id"], report)
    if report["summary"]["sha256"] != saved.get("output_sha256"):
        raise ValueError("Stage output differs from its completed record")
    return report


def _check_report(job: Path, record: dict, stage: str, operation: str, report: dict) -> None:
    if (report.get("schema") != SCHEMA or report.get("status") != "success" or
            report.get("stage") != stage or report.get("operation_id") != operation or
            report.get("source_sha256") != record["source_sha256"]):
        raise ValueError("Native preparation receipt does not match this operation")
    summary = report.get("summary", {})
    output = _inside(job, job / OUTPUTS[stage])
    if Path(summary.get("file", "")).resolve() != output:
        raise ValueError("Native preparation receipt identifies a different output")
    _match(output, summary.get("sha256", ""), stage + " output")
    for preview in report.get("previews", []):
        path = _inside(job, job / preview["file"])
        _match(path, preview.get("sha256", ""), "Preview")
    if stage == "merge" and (report.get("command") != "_MergeAllCoplanarFaces" or
            report.get("command_applied") is not True or
            report.get("original_geometry_and_attributes_preserved") is not True or
            report.get("original_selection_preserved") is not True or report.get("cleanup_notes") or
            report.get("temporary_objects_removed") is not True):
        raise ValueError("Actual coplanar-merge command and document preservation were not verified")


def _review_normalize(job: Path, record: dict, review: dict) -> None:
    report = _report(job, record, "inspect")
    digest = report["summary"]["sha256"]
    if review.get("vision_reviewed") is not True or review.get("inspected_sha256") != digest:
        raise ValueError("Record actual before-image review tied to inspected_sha256")
    for key in ("name", "asset_id", "filename", "orientation_reason"):
        if not isinstance(review.get(key), str) or not review[key].strip() or len(review[key]) > 2000:
            raise ValueError("Review requires " + key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", review["filename"]):
        raise ValueError("Review filename must be a clean basename without an extension")
    angles = review.get("rotation_degrees_xyz")
    if (not isinstance(angles, list) or len(angles) != 3 or
            any(type(x) not in {int, float} or not math.isfinite(x) for x in angles)):
        raise ValueError("Supply explicit finite rotation_degrees_xyz")
    ids = {part["object_id"] for part in report["summary"].get("parts", [])}
    removals = review.get("remove", [])
    if not isinstance(removals, list) or len(removals) > len(ids):
        raise ValueError("remove must list inspected part IDs with their evidence")
    seen = set()
    for removal in removals:
        if (not isinstance(removal, dict) or removal.get("object_id") not in ids or
                removal["object_id"] in seen or not isinstance(removal.get("reason"), str) or
                not removal["reason"].strip() or len(removal["reason"]) > 2000):
            raise ValueError("Each removal needs one existing inspected part ID and a reason")
        seen.add(removal["object_id"])
    _write(job / "review.json", review)
    record["review_sha256"] = sha(job / "review.json")
    record["inspected_sha256"] = digest


def _review_after(job: Path, record: dict, review: dict, final: bool = False) -> None:
    stage, key = ("verify", "final_sha256") if final else ("normalize", "normalized_sha256")
    digest = _report(job, record, stage)["summary"]["sha256"]
    if review.get("vision_reviewed") is not True or review.get(key) != digest:
        raise ValueError("Record actual image review tied to " + key)
    path = job / ("final-review.json" if final else "after-review.json")
    _write(path, review)
    record["final_review_sha256" if final else "after_review_sha256"] = sha(path)
    record[key] = digest


def _dispatch(job: Path, record: dict, stage: str, sender, execute) -> None:
    if stage == "merge" and execute is None:
        raise ValueError("Official RhinoCode execution is unavailable; enable StartScriptServer.")
    template = "merge.py.txt" if stage == "merge" else "headless.cs.txt"
    script = (TEMPLATES / template).read_text(encoding="utf-8")
    replacement = json.dumps(str(job / "job.json")) if stage == "merge" else str(job / "job.json").replace('"', '""')
    script = script.replace("__JOB_JSON__", replacement)
    operation = uuid4().hex
    record.update(stage=stage, state="running", operation_id=operation, error="")
    record.pop("requires_reconciliation", None)
    _write(job / "job.json", record)
    script_path = job / (stage + (".py" if stage == "merge" else ".cs"))
    script_path.write_text(script, encoding="utf-8")
    record["script_sha256"] = sha(script_path)
    _write(job / "job.json", record)
    try:
        if stage == "merge":
            response = execute(script, "python", 120)
        else:
            response = sender(json.dumps({"type": "execute", "script": script}).encode("utf-8"), timeout=120.0)
        if isinstance(response, str):
            response = json.loads(response)
        record["execution"] = response
        if not isinstance(response, dict) or response.get("status") != "success":
            uncertain = not isinstance(response, dict) or response.get("requires_reconciliation") or response.get("mutation_state") in {"running", "pending", "unknown", "unconfirmed"}
            record.update(state="unconfirmed" if uncertain else "failed",
                          error="Preparation execution did not complete successfully; inspect execution evidence before retrying.")
            return
        report = _read(job / (stage + ".json"))
        _check_report(job, record, stage, operation, report)
        record.setdefault("stages", {})[stage] = {
            "operation_id": operation, "report_sha256": sha(job / (stage + ".json")),
            "output_sha256": report["summary"]["sha256"], "script_sha256": record["script_sha256"]}
        record.update(state=STATES[stage], error="")
        if stage == "merge":
            record["final_sha256"] = report["summary"]["sha256"]
    except Exception as exc:
        record.update(state="unconfirmed", error=str(exc), requires_reconciliation=True)
    finally:
        _write(job / "job.json", record)


def prepare(*, stage: str, source_file: str = "", job_dir: str = "", input_units: str = "",
            review: dict | None = None, field_groups: list[str] | None = None,
            include_ids: bool = False, offset: int = 0, limit: int = 50,
            sender=None, execute=None, artifact_dir: str | Path | None = None,
            expected_model_path: str = "") -> dict:
    if stage not in STAGES or input_units not in UNITS:
        raise ValueError("Use inspect/normalize/merge/verify/status and input_units mm/cm/m/in/ft")
    if (field_groups is not None and (not isinstance(field_groups, list) or any(group not in GROUPS for group in field_groups)) or
            type(include_ids) is not bool or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200):
        raise ValueError("Invalid field_groups, include_ids, offset or limit")
    if review is not None and not isinstance(review, dict):
        raise ValueError("review must be an object")
    value = artifact_dir or os.environ.get("ALMOND_ARTIFACT_DIR")
    if not value or not Path(value).is_absolute() or not Path(value).is_dir():
        raise ValueError("Select a working Plan artifact directory before preparing an asset")
    root = Path(value).resolve()
    if stage == "inspect":
        if job_dir or review is not None:
            raise ValueError("inspect creates a new job; use status to reread an existing one")
        source = Path(source_file)
        if not source.is_absolute() or not source.is_file() or source.stat().st_size > MAX_BYTES:
            raise ValueError("Supply an existing source file up to 100 MB")
        if source.suffix.lower() in UNITLESS and not input_units:
            raise ValueError("Unitless OBJ/STL/PLY/OFF sources require explicit input_units")
        content = source.read_bytes()
        if len(content) > MAX_BYTES:
            raise ValueError("Source exceeds 100 MB")
        job = root / ("asset-preparation-" + uuid4().hex)
        job.mkdir()
        copied = job / ("source" + source.suffix.lower())
        copied.write_bytes(content)
        record = {"schema": SCHEMA, "job_dir": str(job), "source": str(copied),
                  "original_path": str(source.resolve()), "source_sha256": sha(copied),
                  "input_units": input_units, "layer": "ASSETS::drawing::Fur",
                  "created_at": datetime.now(timezone.utc).isoformat(), "state": "new", "stages": {}}
        _write(job / "job.json", record)
        with _lock(job):
            _dispatch(job, record, stage, sender, execute)
    else:
        job, record = _job(root, job_dir)
        if source_file or input_units:
            raise ValueError("Source and units are fixed by inspect; omit them for later stages")
        if stage != "status":
            with _lock(job):
                record = _read(job / "job.json")
                _match(_inside(job, Path(record["source"])), record["source_sha256"], "Preserved source")
                if stage == "verify" and record["state"] == "verified" and review is not None:
                    _review_after(job, record, review, final=True)
                    record["state"] = "ready"
                    _write(job / "job.json", record)
                elif record["state"] in {STATES[stage], "ready"} and review is None:
                    pass  # Completed stages are inspected without repeating native work.
                else:
                    if record["state"] != PREREQUISITES[stage]:
                        raise ValueError("Stage requires " + PREREQUISITES[stage] + "; current state is " + record["state"] + ". Do not replay unconfirmed work.")
                    if stage == "normalize":
                        _review_normalize(job, record, review or {})
                    elif stage == "merge":
                        _review_after(job, record, review or {})
                        if not expected_model_path:
                            raise ValueError("Actual command requires the bound saved model path")
                        record["expected_model_path"] = expected_model_path
                    elif review is not None:
                        raise ValueError("First verify produces final images; review their exact final_sha256 in a second verify call")
                    _dispatch(job, record, stage, sender, execute)
    return present(job, record, field_groups=field_groups, include_ids=include_ids, offset=offset, limit=limit)


def present(job: Path, record: dict, *, field_groups=None, include_ids=False, offset=0, limit=50) -> dict:
    groups = set(field_groups or [])
    if "all" in groups:
        groups = GROUPS
    state = record["state"]
    result = {"status": "error" if state in {"running", "unconfirmed", "failed"} or record.get("error") else "success",
              "job_dir": str(job), "state": state, "ready_for_registration": state == "ready",
              "review_evidence": "caller attestations tied to file hashes; no automatic vision verification",
              "next_stage": {"inspected": "normalize", "normalized": "merge", "merged": "verify",
                             "verified": "verify with final image review", "ready": "register_drawing_asset"}.get(state)}
    if record.get("error"):
        result.update(message=record["error"], execution=record.get("execution"),
                      requires_reconciliation=state in {"running", "unconfirmed"})
    completed = next((name for name in ("verify", "merge", "normalize", "inspect") if name in record.get("stages", {})), None)
    if completed:
        report = _report(job, record, completed)
        summary = report["summary"]
        result["summary"] = {key: summary[key] for key in ("units", "dimensions_mm", "object_count", "mesh_face_count", "triangle_count", "count_basis", "limitations") if key in summary}
        result["review_targets"] = {OUTPUTS[name].split(".")[0] + "_sha256": item["output_sha256"] for name, item in record["stages"].items()}
        if "previews" in groups or field_groups is None:
            result["previews"] = [str(_inside(job, job / item["file"])) for item in report.get("previews", [])]
        if "parts" in groups:
            parts = summary.get("parts", [])
            selected = [dict(part) for part in parts[offset:offset + limit]]
            if not include_ids:
                for part in selected:
                    part.pop("object_id", None)
            result.update(parts=selected, total=len(parts), offset=offset, limit=limit,
                          next_offset=offset + len(selected) if offset + len(selected) < len(parts) else None)
        if "provenance" in groups:
            result["provenance"] = {key: record.get(key) for key in ("original_path", "source", "source_sha256", "input_units", "created_at", "stages")}
        if state == "ready":
            result["source_3dm"] = str(job / "final.3dm")
    return result


def copy_registration_evidence(job_dir: str, source: Path, destination: Path) -> dict:
    """Validate then copy evidence inside the existing publisher's atomic staging tree."""
    job = Path(job_dir).resolve()
    record = _read(job / "job.json")
    if record.get("schema") != SCHEMA or record.get("state") != "ready" or Path(record.get("job_dir", "")).resolve() != job:
        raise ValueError("Preparation must finish verification and final-image review before registration")
    if source.resolve() != (job / "final.3dm").resolve():
        raise ValueError("source_3dm differs from the reviewed preparation result")
    _match(_inside(job, Path(record["source"])), record["source_sha256"], "Preserved source")
    reports = {stage: _report(job, record, stage) for stage in OUTPUTS}
    for name, key in (("review.json", "review_sha256"), ("after-review.json", "after_review_sha256"), ("final-review.json", "final_review_sha256")):
        _match(_inside(job, job / name), record.get(key, ""), name)
    before, after, final = (_read(job / name) for name in ("review.json", "after-review.json", "final-review.json"))
    if (before.get("vision_reviewed") is not True or before.get("inspected_sha256") != reports["inspect"]["summary"]["sha256"] or
            after.get("vision_reviewed") is not True or after.get("normalized_sha256") != reports["normalize"]["summary"]["sha256"] or
            final.get("vision_reviewed") is not True or final.get("final_sha256") != reports["verify"]["summary"]["sha256"]):
        raise ValueError("Image review does not identify the actual stage files")
    files = {"job.json", "review.json", "after-review.json", "final-review.json", Path(record["source"]).name}
    for stage, report in reports.items():
        files.add(stage + ".json")
        files.add(stage + (".py" if stage == "merge" else ".cs"))
        files.update(item["file"] for item in report.get("previews", []))
    destination.mkdir()
    hashes = {}
    for name in sorted(files):
        path = _inside(job, job / name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        hashes[name] = sha(target)
        if hashes[name] != sha(path):
            raise ValueError("Preparation evidence changed while copying")
    return {"schema": SCHEMA, "original_path": record["original_path"], "original_file": Path(record["source"]).name,
            "original_sha256": record["source_sha256"], "input_units": record["input_units"],
            "review": "caller_attested_before_after_and_final", "command": "_MergeAllCoplanarFaces",
            "command_applied": True, "reviewed_name": before["name"], "reviewed_asset_id": before["asset_id"],
            "stages": record["stages"], "files": hashes,
            "limitations": "Shape previews and classic material metadata; full PBR/texture portability is not verified."}
