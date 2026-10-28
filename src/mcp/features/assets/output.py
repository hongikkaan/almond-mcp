"""Drawing/repository shortlist fields and explicit detail groups."""
from almond_mcp.query_output import select_fields, select_records, requires_full_evidence


CORE = {"asset_id", "id", "name", "product", "variant", "category", "kind", "file_available",
        "drawing_ready", "ready", "available", "format", "match_status"}
GROUPS = {
    "dimensions": {"dimensions_mm", "dimension_basis", "bounds_mm", "spatial", "clearance_mm"},
    "source": {"source", "source_url", "warehouse_url", "license", "provenance", "sha256"},
    "paths": {"file", "model", "preview", "contract", "generation_image", "model_path", "preview_uri",
              "package_dir", "dimensions_path", "library_dir"},
    "drawing": {"drawing", "drawing_roles", "lod", "drawing_package", "drawing_manifest"},
    "metadata": {"metadata", "description", "tags", "series", "material_id", "render_material_id", "passport"},
    "audit": {"created_at", "updated_at", "generated_at"},
}


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key in ("asset", "assets"):
        if key in result:
            result[key] = select_records(result[key], groups, CORE, GROUPS)
    # get_asset_drawing's manifest and URI are the requested, intrinsically bounded payload.
    return select_fields(result, groups,
        {"status", "library_id", "purpose", "asset", "assets", "total", "limit", "offset",
         "truncated", "has_more", "manifest", "plan_svg_uri", "asset_id", "hint"}, GROUPS)
