"""Construction candidates, typology narratives and source discovery projections."""
from almond_mcp.query_output import select_fields, requires_full_evidence

GROUPS = {
    "rules": {"span_range_m", "span_axis", "typical_spacing_m", "depth_rules", "depth_guidance", "elements",
              "construction_notes", "render_material_ids", "construction_detail", "construction_reference"},
    "narrative": {"narrative", "urban_role", "precedents", "related_construction_systems"},
    "source": {"source", "bci_ref", "gha_ref", "url", "urls", "license", "access", "formats", "reference"},
    "metadata": {"tags", "structure_types", "matched_terms", "notes", "description"},
    "audit": {"created_at", "updated_at"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    if requires_full_evidence(payload):
        return payload
    result = dict(payload)
    for key, core in (("systems", {"system_id", "name", "category", "structural_material", "fits_span"}),
                      ("entries", {"typology_id", "name", "era", "region"}),
                      ("sources", {"source_id", "title", "scope"})):
        if key in result:
            result[key] = [select_fields(item, groups, core, GROUPS) for item in result[key]]
    # Library-level source includes the preliminary-sizing/narration-only limitation.
    return result
