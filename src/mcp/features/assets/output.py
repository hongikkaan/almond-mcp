"""Drawing/repository shortlist fields and explicit detail groups."""
from almond_mcp.public_names import public_tool_name
from almond_mcp.query_output import select_fields, select_records, requires_full_evidence


CORE = {"asset_id", "id", "name", "product", "variant", "category", "kind", "file_available",
        "drawing_ready", "drawing_status", "ready", "available", "format", "match_status",
        "asset_kind", "model_status", "source_only", "source_available", "next_tool", "conversion_target", "verification_issue"}
GROUPS = {
    "dimensions": {"dimensions_mm", "dimension_basis", "bounds_mm", "spatial", "clearance_mm"},
    "source": {"source", "source_url", "warehouse_url", "license", "provenance", "sha256"},
    "paths": {"file", "model", "preview", "contract", "generation_image", "model_path", "preview_uri",
              "package_dir", "dimensions_path", "library_dir", "source_path", "source_file"},
    "drawing": {"drawing", "drawing_roles", "lod", "drawing_package", "drawing_manifest"},
    "metadata": {"metadata", "description", "tags", "series", "material_id", "render_material_id", "passport"},
    "audit": {"created_at", "updated_at", "generated_at", "verification_basis"},
}


def _public_next_tool(record: dict) -> dict:
    if "next_tool" not in record:
        return record
    return {**record, "next_tool": public_tool_name(record["next_tool"])}


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key in ("asset", "assets"):
        if key in result:
            records = result[key]
            records = [_public_next_tool(item) for item in records] if isinstance(records, list) else _public_next_tool(records)
            result[key] = select_records(records, groups, CORE, GROUPS)
    return select_fields(result, groups,
        {"status", "library_id", "purpose", "asset", "assets", "total", "limit", "offset",
         "next_offset", "truncated", "has_more", "asset_id", "hint"}, GROUPS)
