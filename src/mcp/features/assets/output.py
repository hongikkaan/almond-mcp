"""Drawing/repository shortlist fields and explicit detail groups."""
from almond_mcp.query_output import select_fields, select_records, requires_full_evidence


CORE = {"asset_id", "id", "name", "product", "variant", "category", "kind", "file_available",
        "drawing_ready", "drawing_status", "ready", "available", "format", "match_status",
        "asset_kind", "model_status", "source_only", "source_available", "next_tool", "next_step", "conversion_target", "verification_issue"}
GROUPS = {
    "dimensions": {"dimensions_mm", "dimension_basis", "bounds_mm", "spatial", "clearance_mm"},
    "source": {"source", "source_url", "warehouse_url", "license", "provenance", "sha256"},
    "paths": {"file", "model", "preview", "contract", "generation_image", "model_path", "preview_uri",
              "package_dir", "dimensions_path", "library_dir", "source_path", "source_file"},
    "drawing": {"drawing", "drawing_roles", "lod", "drawing_package", "drawing_manifest"},
    "metadata": {"metadata", "description", "tags", "series", "material_id", "render_material_id", "passport"},
    "audit": {"created_at", "updated_at", "generated_at", "verification_basis"},
}


def with_next_step(record: dict) -> dict:
    """Explain existing readiness hints without choosing an asset or hiding missing inputs."""
    tool = record.get("next_tool")
    if tool not in {"prepare_drawing_asset", "refresh_asset"}:
        return record
    identity = "id" if "id" in record else "asset_id"
    prerequisite = (f"Reuse this row's {identity} as asset_id, or retain the ID supplied to this detail query; "
                    "if unknown, repeat the list/search with include_ids=true. ")
    if tool == "refresh_asset":
        hint = "If updating this saved source is intended, call refresh_asset(asset_id=...). Review the refreshed model/drawings before placement."
    else:
        hint = ("To convert this source, request get_drawing_asset(asset_id=..., field_groups=['paths']) if its path is missing, "
                "then prepare_drawing_asset(stage='inspect', source_file=...) with the actual source units and a selected Plan. "
                "Managed source_file must be project-relative; an external library path must first be made available within the project. "
                "An asset ID is not a file path; retain it for registration.")
    return {**record, "next_step": prerequisite + hint}


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key in ("asset", "assets"):
        if key in result:
            records = result[key]
            records = [with_next_step(item) for item in records] if isinstance(records, list) else with_next_step(records)
            result[key] = select_records(records, groups, CORE, GROUPS)
    # get_asset_drawing's manifest and URI are the requested, intrinsically bounded payload.
    return select_fields(result, groups,
        {"status", "library_id", "purpose", "asset", "assets", "total", "limit", "offset",
         "truncated", "has_more", "manifest", "plan_svg_uri", "asset_id", "hint"}, GROUPS)
