"""Public planning summaries; persistence and revision snapshots remain complete."""
from almond_mcp.query_output import select_fields, requires_full_evidence
from almond_mcp.managed_paths import relative_output
from almond_mcp.features.planning.updates import PlanningUpdate
from datetime import datetime, timedelta, timezone
import json


PLAN_CORE = {"plan_id", "title", "scope", "status", "loop_no", "revision"}
PHASE_CORE = {"phase_id", "name", "status", "plan_count", "depends_on", "previous_id"}
GROUPS = {
    "steps": {"steps"},
    "references": {"phase_id", "scene_ids", "component_id", "component_ids", "depends_on",
                   "parent_component_id", "child_component_ids", "related_component_ids",
                   "input_refs", "output_refs", "matched_step_ids"},
    "geometry": {"direct_object_ids", "effective_object_ids"},
    "artifacts": {"artifact_dir", "artifact_refs"},
    "description": {"description"},
    "scope": {"file_name", "model_path", "rhino_group_id"},
    "audit": {"created_at", "updated_at"},
}
PHASE_GROUPS = {key: GROUPS[key] for key in ("description", "scope", "audit")}
REVISION_GROUPS = {"audit": GROUPS["audit"]}
TARGET_GROUPS = {key: GROUPS[key] for key in ("references", "geometry", "scope", "audit")}


def encode(payload: dict) -> str:
    """Planning handles are always visible; errors retain their original evidence."""
    value = payload if requires_full_evidence(payload) else relative_output(payload)
    return json.dumps(value, ensure_ascii=False)


def update_ack(update: PlanningUpdate, kind: str, step_id: str = "") -> dict:
    """Report skips separately from persisted data; never claim a no-op was applied."""
    outcome = ("partial_success" if update.changed else "no_change") if update.issues else "success"
    keys = ("phase_id", "status") if kind == "phase" else ("plan_id", "status", "loop_no", "revision")
    result = {"status": outcome, "changed": update.changed,
              kind: {key: update.record[key] for key in keys}, "issues": update.issues}
    if step_id:
        step = next(item for item in update.record["steps"] if item["step_id"] == step_id)
        result["step"] = {"step_id": step_id, "status": step["status"], "loop_no": update.record["loop_no"]}
    return result


def kst_minute(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d-%H:%M")


def phase_detail(phase: dict, include_details: bool = False) -> dict:
    result = {"id": phase["phase_id"], "type": "phase", "name": phase["name"], "status": phase["status"]}
    if include_details:
        result["phase"] = {key: phase[key] for key in ("description", "depends_on", "previous_id", "plan_titles")}
        result["phase"]["file_name"] = phase["file_names"]
    return result


def plan_detail(plan: dict, include_details: bool = False, *, historical: bool = False) -> dict:
    result = {"id": plan["plan_id"], "type": "plan", "name": plan["title"], "status": plan["status"],
              "plan_id": plan["plan_id"], "loop_no": plan["loop_no"], "revision": plan["revision"], "read_only": historical}
    if include_details:
        detail = {key: plan[key] for key in (
            "goal", "scope", "phase", "scene_ids", "artifact_dir", "artifact_refs", "previous_id",
            "parent_plan", "child_plan", "loop_artifact_dir", "feedback", "component_ids")}
        detail["depends_on"] = [v for v in plan["depends_on"] if isinstance(v, str) and v.startswith("plan_") and v[5:].strip()]
        detail.update({key: kst_minute(plan[key]) for key in ("created_at", "updated_at")})
        detail["steps"] = [{key: step[key] for key in ("step_id", "step_type", "name", "status", "loop_no")} for step in plan["steps"]]
        result["plan"] = detail
    return result


def step_detail(record: dict, include_details: bool = False, *, historical: bool = False) -> dict:
    step = record["step"]
    result = {"id": step["step_id"], "type": "step", "name": step["name"], "status": step["status"],
              "plan_id": record["plan_id"], "loop_no": record["loop_no"], "revision": record["revision"], "read_only": historical}
    if include_details:
        result["step"] = {key: step[key] for key in ("step_type", "input_refs", "output_refs")}
    return result


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key, core in (("plan", PLAN_CORE), ("plans", PLAN_CORE), ("phase", PHASE_CORE),
                      ("phases", PHASE_CORE), ("revisions", {"loop_no", "revision", "operation", "step_id"}),
                      ("components", {"component_id", "name", "object_count", "effective_object_count"}),
                      ("objects", {"object_id", "rhino_guid", "component_id", "registered", "object_type"})):
        if key not in result:
            continue
        def item(record):
            if requires_full_evidence(record):
                return record
            record = dict(record)
            if "file_names" in record:
                record["file_name"] = record["file_names"]
                record.pop("project_file_id", None)
                record.pop("file_names", None)
            selected = select_fields(record, groups, core, GROUPS)
            if "steps" in selected and "all" not in (groups or []):
                selected["steps"] = [select_fields(step, groups,
                    {"step_id", "step_type", "name", "position", "kind", "status", "loop_no", "input_refs", "output_refs"},
                    GROUPS) for step in selected["steps"]]
            return selected
        result[key] = [item(record) for record in result[key]] if isinstance(result[key], list) else item(result[key])
    # Target resolution is already one bounded target set; preserve handles/counts.
    return result
