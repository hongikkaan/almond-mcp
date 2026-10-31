# tools.py explain

<!-- instruction:get_modeling_guide -->
Read BASIC instructions or one tool's usage instructions.

Omit tool to read BASIC-INSTRUCTIONS.md and available public tool names at first use.
Pass an exact tool name, for example tool="assign_material", for its full explanation.
This reads static instructions without executing the named tool. Reuse instructions already read for the same guide_version. External connector management tools use connection instructions. BASIC links reference material directly.

Args:
    tool: Exact public Almond tool name; empty returns BASIC and available tool names.
<!-- /instruction:get_modeling_guide -->

## get_construction_guidance

<!-- instruction:get_construction_guidance -->
Look up construction systems, their constituent elements and assembly guidance.
Parameters are distilled from Ching's Building Construction Illustrated (4th ed.): per-system span ranges, depth rules of thumb (depth = span/N), member spacing, element roles, and assembly notes.

Span/depth rules support preliminary sizing; they do not establish a project's structural adequacy. Each system names its structural_material (validate_structure vocabulary) and render_material_ids (assign_material vocabulary).

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
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_construction_guidance -->

## get_typology_narrative

<!-- instruction:get_typology_narrative -->
Architectural typology narratives for project storytelling - precedents, eras, and urban roles distilled from Ching, Jarzombek & Prakash's A Global History of Architecture, with page references (gha_ref).

Entries provide historical context and precedent relationships. They contain no project-specific basis for member sizing, loads or structural capacity.

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
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_typology_narrative -->

## search_detail_sources

<!-- instruction:search_detail_sources -->
Search six curated free architectural source directories offline.
Matches titles, tags and formats; an empty query lists all sources. Korean terms are preserved and selected catalogue terms expand to English. Results include query_terms, expanded_terms and each source's matched_terms.
Prefer English search terms unless Korean sources are needed.
Returns links, formats and rights notes; no external content is fetched.
Results are research candidates, not attributed inputs or certified details.
DETAIL subscription access is not required.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:search_detail_sources -->

## response-732

<!-- instruction:response-732 -->
No system matched. Loosen the filters, or call with no arguments to list all systems.
<!-- /instruction:response-732 -->
