"""Code names and verification status first, numeric parameters on request."""
from almond_mcp.query_output import select_fields, requires_full_evidence

GROUPS = {
    "parameters": {"uls_expression", "uls_default", "deflection_limit_ratio", "imposed_floor_kn_m2", "values"},
    "source": {"origin", "sources", "source"},
    "audit": {"created_at", "updated_at"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    result["profiles"] = [select_fields(item, groups, {"id", "name", "basis", "verified", "unverified"}, GROUPS)
                          for item in payload.get("profiles", [])]
    return result


def validation_result(payload):
    if not isinstance(payload, dict):
        return payload
    result = dict(payload)
    status = result.get("status")
    if status == "indicative":
        result["passed"] = None
    if status in {"error", "fail", "indicative"} and result.get("verdict"):
        result.setdefault("message", result["verdict"])

    # The bridge serializes unavailable metrics with numeric defaults.
    metrics = result.get("results")
    if isinstance(metrics, dict):
        metrics = dict(metrics)
        if metrics.get("displacement_available") is False:
            metrics.pop("max_deflection_mm", None)
        if metrics.get("utilization_available") is False:
            metrics.pop("utilization_ratio", None)
            metrics.pop("per_element_utilization", None)
        result["results"] = metrics
    return result
