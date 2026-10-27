"""A helper script is the requested payload; ancillary notes are optional."""
from almond_mcp.query_output import select_fields, requires_full_evidence

GROUPS = {"notes": {"note"}, "audit": {"created_at", "updated_at"}}

def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    return select_fields(payload, groups, {"status", "action", "script"}, GROUPS)
