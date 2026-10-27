"""Recipe purpose is enough for discovery; execution details are opt-in."""
from almond_mcp.query_output import select_records

GROUPS = {
    "scales": {"recommended_scales", "scales"},
    "parameters": {"projection", "layers", "linework", "hatches", "style", "parameters", "views",
                   "layout", "annotations", "output", "display", "units"},
    "source": {"source", "references", "license"},
    "audit": {"created_at", "updated_at"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    result = dict(payload)
    core = {"recipe_id", "name", "description", "projection"}
    for key in ("recipe", "recipes"):
        if key in result:
            result[key] = select_records(result[key], groups, core, GROUPS)
    return result
