"""Public planning summaries; persistence and revision snapshots remain complete."""
from almond_mcp.query_output import select_fields, requires_full_evidence
from almond_mcp.managed_paths import relative_output
from almond_mcp.features.planning.updates import PlanningUpdate
from datetime import datetime, timedelta, timezone
import json


PLAN_CORE = {"plan_id", "title", "scope", "status", "revision"}
PHASE_CORE = {"phase_id", "name", "status", "plan_count", "depends_on"}
GROUPS = {
    "steps": {"steps"},
    "references": {"phase_id", "scene_ids", "component_id", "component_ids", "depends_on",
                   "parent_component_id", "child_component_ids", "related_component_ids",
                   "input_refs", "output_refs", "matched_step_ids"},
    "geometry": {"direct_object_ids", "effective_object_ids"},
    "artifacts": {"artifact_dir", "artifact_refs"},
    "description": {"description"},
    "scope": {"file_name", "project_file_id", "model_path", "rhino_group_id"},
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
    keys = ("phase_id", "status") if kind == "phase" else ("plan_id", "status", "revision")
    result = {"status": outcome, "changed": update.changed,
              kind: {key: update.record[key] for key in keys}, "issues": update.issues}
    if step_id:
        step = next(item for item in update.record["steps"] if item["step_id"] == step_id)
        result["step"] = {"step_id": step_id, "status": step["status"]}
    return result


def kst_minute(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d-%H:%M")


def phase_detail(phase: dict) -> dict:
    return {"id": phase["phase_id"], "type": "phase", "status": phase["status"],
            "phase": {key: phase[key] for key in ("name", "description", "file_name", "project_file_id", "depends_on", "plan_titles")}}


def plan_detail(plan: dict, include_components: bool, *, historical: bool = False) -> dict:
    detail = {key: plan[key] for key in (
        "title", "goal", "scope", "revision", "phase", "scene_ids", "artifact_dir", "artifact_refs")}
    # Old immutable snapshots keep their original data in storage. The current
    # public view no longer exposes mixed-kind dependencies or Step assignments.
    detail["depends_on"] = [v for v in plan["depends_on"] if isinstance(v, str) and v.startswith("plan_") and v[5:].strip()]
    detail.update({key: kst_minute(plan[key]) for key in ("created_at", "updated_at")})
    detail["steps"] = [{key: step[key] for key in ("step_id", "name", "status")} for step in plan["steps"]]
    detail["available_details"] = [] if include_components else ["include_components"]
    if include_components:
        detail["component_ids"] = plan["component_ids"]
    next_step = (f"For a Step in this saved state, use id as plan_id, its step_id and revision={plan['revision']} in get_phase_plan_step. "
                 "Before selecting current work, query the Plan without revision; set_working_plan uses current state and does not restore history."
                 if historical else
                 "Use id as plan_id and a plan.steps[].step_id in get_phase_plan_step for that Step's records. Once you choose actual work, use set_working_plan(plan_id=..., step_id=...) to select it and its artifact location; selection does not execute work or change status.")
    return {"id": plan["plan_id"], "type": "plan", "status": plan["status"], "plan": detail,
            "next_step": next_step}


def step_detail(record: dict, *, historical: bool = False) -> dict:
    step = record["step"]
    next_step = ("Before selecting current work, query step.plan_id and id as step_id without revision in get_phase_plan_step; "
                 "set_working_plan uses current state and does not restore this saved Step."
                 if historical else
                 "If this is the Step you intend to work on, use step.plan_id as plan_id and id as step_id in set_working_plan. Selection sets the working context and artifact location; it does not execute the Step or change status.")
    return {"id": step["step_id"], "type": "step", "status": step["status"], "step": {
        "plan_id": record["plan_id"], "revision": record["revision"],
        **{key: step[key] for key in ("name", "input_refs", "output_refs")}},
        "next_step": next_step}


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key, core in (("plan", PLAN_CORE), ("plans", PLAN_CORE), ("phase", PHASE_CORE),
                      ("phases", PHASE_CORE), ("revisions", {"revision", "operation"}),
                      ("components", {"component_id", "name", "object_count", "effective_object_count"}),
                      ("objects", {"object_id", "rhino_guid", "component_id", "registered", "object_type"})):
        if key not in result:
            continue
        def item(record):
            if requires_full_evidence(record):
                return record
            selected = select_fields(record, groups, core, GROUPS)
            if "steps" in selected and "all" not in (groups or []):
                selected["steps"] = [select_fields(step, groups,
                    {"step_id", "name", "position", "kind", "status", "input_refs", "output_refs"},
                    GROUPS) for step in selected["steps"]]
            return selected
        result[key] = [item(record) for record in result[key]] if isinstance(result[key], list) else item(result[key])
    # Target resolution is already one bounded target set; preserve handles/counts.
    return result
