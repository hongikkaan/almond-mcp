"""Material names first; rendering and provenance are explicit choices."""
from almond_mcp.query_output import select_fields, requires_full_evidence

GROUPS = {
    "display": {"base_color", "metallic", "roughness", "opacity", "emission", "ior", "ue_material_slot", "textures"},
    "physical": {"density", "density_kg_m3", "structural_material", "physical"},
    "metadata": {"description", "tags"},
    "source": {"source", "provenance", "license"},
    "paths": {"library_dir", "file"},
    "audit": {"created_at", "updated_at"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = select_fields(payload, groups, {"status", "total", "materials"}, GROUPS)
    if "materials" in result:
        result["materials"] = [select_fields(item, groups, {"material_id", "name", "category"}, GROUPS)
                               for item in result["materials"]]
    return result
