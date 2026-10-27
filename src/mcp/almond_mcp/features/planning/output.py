"""Public planning summaries; persistence and revision snapshots remain complete."""
from almond_mcp.query_output import select_fields, requires_full_evidence


PLAN_CORE = {"plan_id", "goal", "scope", "status", "revision"}
PHASE_CORE = {"phase_id", "name", "plan_count"}
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
PLAN_GROUPS = {key: GROUPS[key] for key in ("steps", "references", "artifacts", "audit")}
PLAN_LIST_GROUPS = {key: GROUPS[key] for key in ("references", "artifacts", "audit")}
REVISION_GROUPS = {"audit": GROUPS["audit"]}
TARGET_GROUPS = {key: GROUPS[key] for key in ("references", "geometry", "scope", "audit")}


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
                    {"step_id", "name", "position", "kind", "status"}, GROUPS) for step in selected["steps"]]
            return selected
        result[key] = [item(record) for record in result[key]] if isinstance(result[key], list) else item(result[key])
    # Target resolution is already one bounded target set; preserve handles/counts.
    return result
