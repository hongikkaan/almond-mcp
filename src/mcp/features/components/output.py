"""Ontological-component projections; no registration or alignment semantics."""
from almond_mcp.query_output import select_fields, requires_full_evidence

CORE = {"component_id", "name", "status", "registration_status", "availability", "object_count", "effective_object_count",
        "direct_object_count", "object_names", "object_types", "revision", "scene_revisions", "geometry_available"}
GROUPS = {
    "references": {"parent_component_id", "child_component_ids", "scene_ids", "rhino_group_id"},
    "geometry": {"object_ids", "direct_object_ids", "effective_object_ids", "objects", "effective_objects",
                 "pending_objects", "bounds_mm", "intersections", "pairs"},
    "scope": {"model_path", "expected_model_path", "project_file_id", "file_name"},
    "audit": {"created_at", "updated_at", "observed_at"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key in ("component", "components"):
        if key in result:
            def item(record):
                if requires_full_evidence(record):
                    return record
                selected = select_fields(record, groups, CORE, GROUPS)
                for objects in ("objects", "effective_objects", "pending_objects"):
                    if objects in selected:
                        selected[objects] = [select_fields(obj, groups,
                            {"rhino_guid", "component_id", "name", "object_type", "bounds_mm"}, GROUPS)
                            for obj in selected[objects]]
                return selected
            result[key] = [item(record) for record in result[key]] if isinstance(result[key], list) else item(result[key])
    if "component" not in result and "components" not in result:
        # Intersections expose the conclusion/counts even when pair detail is omitted.
        result = select_fields(result, groups,
            {"status", "action", "schema", "has_positive_overlap", "object_count", "supported_object_count",
             "candidate_pair_count", "bbox_pruned_pair_count", "evaluated_pairs", "max_pairs",
             "positive_pair_count", "unknown_pair_count", "document_units", "tolerance_model_units",
             "occurrence_count", "supported_occurrence_count", "include_blocks", "offset",
             "scope_state", "next_cursor", "pagination_complete", "remaining_candidate_pairs"}, GROUPS)
    return result
