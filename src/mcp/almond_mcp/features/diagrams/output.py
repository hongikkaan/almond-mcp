"""Diagram names/readiness by default; measured and source detail on request."""
from almond_mcp.query_output import select_records, requires_full_evidence


CORE = {"asset_id", "name", "product", "variant", "category", "kind", "file_available"}
GROUPS = {
    "dimensions": {"dimensions_mm", "bounds_mm"},
    "drawing": {"drawing_roles", "lod", "projection"},
    "metadata": {"description", "series", "tags"},
    "source": {"source", "source_url", "warehouse_url", "license", "sha256"},
    "paths": {"file", "model_path", "preview", "preview_uri"},
    "audit": {"created_at", "updated_at"},
}


def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key in ("asset", "assets"):
        if key in result:
            result[key] = select_records(result[key], groups, CORE, GROUPS)
    return result
