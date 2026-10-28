# tools.py explain

<!-- instruction:get_modeling_guide -->
Read a versioned topic from the packaged Rhino Almond modeling guide.
Use the startup topic summaries to read a known topic directly; topic="index"
is optional discovery. Reuse topics read for the same guide_version. For semantic
grouping examples, read topic="ontological-component-evidence" with include_images=true.
Images are original reference PNGs, not captures of the current Rhino document.
This reader does not edit the model, task database or user artifacts. Existing
connection control and operation receipts still apply. Unknown topics fail explicitly.
No personal skill installation, filesystem path or external URL is needed.
<!-- /instruction:get_modeling_guide -->

## get_construction_guidance

<!-- instruction:get_construction_guidance -->
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
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_construction_guidance -->

## get_typology_narrative

<!-- instruction:get_typology_narrative -->
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
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_typology_narrative -->

## search_detail_sources

<!-- instruction:search_detail_sources -->
Search six curated free architectural source directories offline.
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
