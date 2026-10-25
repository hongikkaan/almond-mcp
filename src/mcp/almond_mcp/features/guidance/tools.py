"""Register construction, typology and detail-source guidance tools."""

import json
import re
from pathlib import Path


def register(mcp, context):
    """Register guidance tools against the calling server's live context."""

    @mcp.tool()
    def get_construction_guidance(
        query: str = "",
        category: str = "",
        material: str = "",
        structure_type: str = "",
        span_m: float = 0.0,
        include_reference_data: bool = False,
    ) -> str:
        """
        Curated construction-system guidance for generating structures that are
        built the way real buildings are built - not arbitrary members in space.
        Parameters are distilled from Ching's Building Construction Illustrated
        (4th ed.): per-system span ranges, depth rules of thumb (depth = span/N),
        member spacing, element roles, and assembly notes.

        Call this BEFORE generating structural geometry: pick a system, size and
        space members from its rules, then generate and run validate_structure
        (which cross-checks the result against this same library). Each system
        names its structural_material (validate_structure vocabulary) and
        render_material_ids (assign_material vocabulary), so the declared
        construction material flows through analysis AND appears on the Rhino
        objects.

        Args:
            query: Free-text filter (e.g. "glulam", "longspan", "bearing wall").
            category: "floor", "wall", "roof", "foundation" (empty = all).
            material: "Wood", "Steel", "Concrete" - validate_structure names.
            structure_type: validate_structure type ("beam", "truss", "shell",
                "frame", "canopy", "gridshell", "membrane", "highrise").
            span_m: If > 0, each returned system reports fits_span and
                suggested member depths from its span-ratio rules.
            include_reference_data: Also return occupancy live loads (kPa) and
                material densities (kg/m3) for choosing load_kn inputs.
        Returns:
            JSON: {total, systems: [...], reference?} - for wall systems
            span_range_m is the unsupported height range (span_axis "vertical").
        """
        systems = context.construction_library.list(
            category=category, query=query, material=material,
            structure_type=structure_type)
        payload: dict = {
            "total": len(systems),
            "source": context.construction_library.source,
            "systems": [],
        }
        for system in systems:
            card = dict(system)
            card["construction_detail"] = system["name"]
            card["construction_reference"] = {"kind": "construction_system", "id": system["system_id"]}
            if span_m > 0:
                lo, hi = system["span_range_m"]
                if hi > 0:
                    card["fits_span"] = bool(lo <= span_m <= hi)
                    depths = [
                        {"element": rule["element"],
                         "suggested_depth_mm": round(span_m * 1000 / rule["span_ratio"]),
                         "rule": f"span/{rule['span_ratio']}"}
                        for rule in system.get("depth_rules", [])
                        if rule.get("span_ratio")
                    ]
                    if depths:
                        card["depth_guidance"] = depths
            payload["systems"].append(card)
        if include_reference_data:
            payload["reference"] = context.construction_library.reference
        if not systems:
            payload["hint"] = ("No system matched. Loosen the filters, or call "
                              "with no arguments to list all systems.")
        return json.dumps(payload)

    @mcp.tool()
    def get_typology_narrative(
        query: str = "",
        construction_system: str = "",
        structure_type: str = "",
        limit: int = 5,
    ) -> str:
        """
        Architectural typology narratives for project storytelling - precedents,
        eras, and urban roles distilled from Ching, Jarzombek & Prakash's
        A Global History of Architecture, with page references (gha_ref).

        NARRATION ONLY: use these entries to caption, contextualize and narrate
        a design (which tradition a courtyard block belongs to, what a truss
        hall's civic ancestors are). They must NEVER drive geometry, member
        sizing, or structural decisions - that is get_construction_guidance's
        job. A natural pairing: after building with a construction system, call
        this with construction_system=<that system_id> to fetch the lineage for
        the project description.

        Args:
            query: Free text (e.g. "courtyard", "skyscraper", "timber hall").
            construction_system: Filter to entries related to a construction
                library system_id (e.g. "steel-column-frame").
            structure_type: Filter by validate_structure type ("shell",
                "truss", "frame", "membrane", ...).
            limit: Maximum entries returned (default 5).
        Returns:
            JSON: {total, entries: [{typology_id, name, era, region, narrative,
            precedents, related_construction_systems, urban_role, gha_ref,
            tags}], source}.
        """
        entries = context.history_library.list(query=query,
                                       construction_system=construction_system,
                                       structure_type=structure_type)
        return json.dumps({
            "total": len(entries),
            "entries": entries[:max(1, limit)],
            "source": context.history_library.source,
        })

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def search_detail_sources(query: str = "") -> dict:
        """Search six curated free architectural source directories offline.
        Returns links, formats and rights notes; no external content is fetched.
        Results are research candidates, not attributed inputs or certified details.
        DETAIL subscription access is not required."""
        data = json.loads((Path(context.DRAFTING_LIBRARY_DIR)/"sources.json").read_text(encoding="utf-8"))
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        matches = []
        for source in data["sources"]:
            haystack = " ".join([source["title"], *source["tags"], *source["formats"]]).lower()
            matched = sorted(t for t in terms if t in haystack)
            if not terms or matched:
                matches.append({**source, "matched_terms": matched})
        matches.sort(key=lambda s: (-len(s["matched_terms"]), s["source_id"]))
        return {"status": "success", "scope": data["scope"], "sources": matches}

    return {
        "get_construction_guidance": get_construction_guidance,
        "get_typology_narrative": get_typology_narrative,
        "search_detail_sources": search_detail_sources,
    }
