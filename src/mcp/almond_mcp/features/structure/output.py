"""Code names and verification status first, numeric parameters on request."""
from almond_mcp.query_output import select_fields

GROUPS = {
    "parameters": {"uls_expression", "uls_default", "deflection_limit_ratio", "imposed_floor_kn_m2", "values"},
    "source": {"origin", "sources", "source"},
    "audit": {"created_at", "updated_at"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    result = dict(payload)
    result["profiles"] = [select_fields(item, groups, {"id", "name", "basis", "verified", "unverified"}, GROUPS)
                          for item in payload.get("profiles", [])]
    return result
