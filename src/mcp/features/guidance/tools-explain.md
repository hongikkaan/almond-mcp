# tools.py explain

<!-- instruction:get_modeling_guide -->
Read BASIC operating guidance and, when requested, the bundled Rhino scripting references.

When to use: Read shared design and verification principles, or the packaged scripting skill when source-authoring references are needed. Plans and Steps organize the work; apply BASIC's modeling, inspection and drafting principles to the current activity regardless of the Plan template or Step.
Before calling: No model observation is required. Reuse guidance already read at the same guide_version across activities. Tool descriptions are already delivered in full by tools/list; do not call this reader to retrieve a tool explanation.
Inputs from earlier results: None. Omit include_scripting for BASIC and the public-name inventory; set include_scripting=true only when the bundled rhino3d-scripts material is needed.
Interpretation: text is BASIC, tools lists public names, and source_refs/guide_version identify the pinned documentation. include_scripting adds scripting_skill sources without selecting or executing a modeling tool.
Limits: This is static documentation, not live model state or a validation result. Per-tool description lookup and its tool argument are not supported. It does not edit the model, task database or user artifacts.

Args:
    include_scripting: Include bundled Rhino scripting reference material as well as the concise design guidance; false returns only the basic guide and tool discovery information.
<!-- /instruction:get_modeling_guide -->

## get_construction_guidance

<!-- instruction:get_construction_guidance -->
Find construction systems and preliminary span, member-depth and assembly guidance from the local construction library.

When to use: Compare floor, wall, roof or foundation options before selecting a structural scheme.
Before calling: Choose optional filters; span_m is metres and must be positive to add fits_span and depth_guidance. No prior lookup is required. Construction detailing is off unless requested for the current task. For a target already on a system Layer, use that system as the starting point and check its members and surroundings. A category-only Layer leaves the system undecided: research suitable systems and discuss alternatives before applying one, rather than building every alternative first. Layer names alone prove no joint, load or construction condition.
Inputs from earlier results: Reuse a known structural_material as material. Request include_ids=true for systems[].system_id; pass it as get_typology_narrative.construction_system or assign_material.construction_system. field_groups=["rules"] adds construction_detail, construction_reference and render_material_ids for the corresponding assign_material inputs.
Interpretation: Summary cards retain name, category, structural_material and any fits_span. rules adds span_range_m, span_axis, typical_spacing_m and suggested_depth_mm; wall span ranges mean unsupported vertical height. include_reference_data adds live loads in kPa and densities in kg/m3; these require tributary-area/volume conversion before choosing kN loads.
Limits: Ching BCI 4th-edition ranges and span/N depths are sizing heuristics, not structural adequacy checks. rules, source and metadata expose supporting detail; summary alone is not an assembly specification.

Args:
    query: Free-text filter (e.g. "glulam", "longspan", "bearing wall").
    category: "floor", "wall", "roof", "foundation" (empty = all).
    material: "Wood", "Steel", "Concrete" - validate_structure names.
    structure_type: validate_structure type ("beam", "truss", "shell", "frame", "canopy", "gridshell", "membrane", "highrise").
    span_m: If > 0, each returned system reports fits_span and suggested member depths from its span-ratio rules.
    include_reference_data: Also return occupancy live loads (kPa) and material densities (kg/m3) for choosing load_kn inputs.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: rules, narrative, source, metadata, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
Returns:
    JSON: {total, systems: [...], reference?} - for wall systems
    span_range_m is the unsupported height range (span_axis "vertical").
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
<!-- /instruction:get_construction_guidance -->

## get_typology_narrative

<!-- instruction:get_typology_narrative -->
Find architectural typology narratives, historical precedents and urban roles in the local history library.

When to use: Develop project storytelling or relate a construction system to historical examples.
Before calling: Select optional text/system/type filters and a limit; no project model or prior call is required.
Inputs from earlier results: Pass get_construction_guidance.systems[].system_id to construction_system, requesting include_ids=true on that lookup. A known structure_type can also be reused directly.
Interpretation: total counts all matches before the limit; entries defaults to name, era and region. field_groups=["narrative","source"] adds narrative, precedents, related_construction_systems, urban_role and gha_ref page references; include_ids=true retains typology_id and related identifier fields.
Limits: These entries are historical context distilled from A Global History of Architecture, not evidence for project loads, member sizing or structural capacity. The effective minimum result limit is one.

Args:
    query: Free text (e.g. "courtyard", "skyscraper", "timber hall").
    construction_system: Filter to entries related to a construction library system_id (e.g. "steel-column-frame").
    structure_type: Filter by validate_structure type ("shell", "truss", "frame", "membrane", ...).
    limit: Maximum entries returned (default 5).
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: rules, narrative, source, metadata, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
Returns:
    JSON: {total, entries: [{typology_id, name, era, region, narrative,
    precedents, related_construction_systems, urban_role, gha_ref,
    tags}], source}.
field_groups adds rules, narrative, source, metadata, audit, or all; default is summary.
<!-- /instruction:get_typology_narrative -->

## search_detail_sources

<!-- instruction:search_detail_sources -->
Search six curated architectural source directories offline and return research candidates.

When to use: Find places to research details, drawings or reusable reference material without fetching external content.
Before calling: Use English catalogue terms where practical; an empty query lists all sources. Selected Korean catalogue terms expand to English, not general translation.
Inputs from earlier results: No prior result is required; system names, element names or material terms can inform query. Request field_groups=["source"] to obtain source URLs, formats, access and license notes for later research.
Interpretation: query_terms, expanded_terms and sources[].matched_terms show why titles/tags/formats matched; results are ordered by matched-term count. Default cards show title and scope; include_ids=true retains source_id.
Limits: This searches directory metadata, not hosted detail content or certified assemblies. Links are candidates, not attributed project inputs; rights/access must be checked before reuse. DETAIL subscription access is not required.

Args:
    query: Free-text search terms; empty leaves the text filter unset.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: rules, narrative, source, metadata, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
<!-- /instruction:search_detail_sources -->

## response-732

<!-- instruction:response-732 -->
No system matched. Loosen the filters, or call with no arguments to list all systems.
<!-- /instruction:response-732 -->
