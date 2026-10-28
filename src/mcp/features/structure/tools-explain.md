# tools.py explain

## validate_structure

<!-- instruction:validate_structure -->
Validates AI-generated geometry with a structural analysis.
Call this AFTER execute_rhino_script to verify the generated structure is buildable.

engine="auto" (default) analyses line models (beams, columns, trusses, frames) with
Almond's built-in 3D frame solver: analysis_method "native", confidence "high",
no Karamba install needed. It is a linear-elastic first-order frame analysis with
EN 1993-1-1 member checks (elastic moduli; flexural buckling with L_cr = member
length; no lateral-torsional buckling), benchmarked against closed-form results
and live Karamba runs. Models with shells, and shell/gridshell/membrane structure
types, go to Karamba. engine="karamba" forces the Karamba route, which tries three
pathways in strict order of confidence and always tells you which one ran:
    analysis_method "api"        — direct Karamba 3.1 API solve, confidence "high"
    analysis_method "template"   — audited capsule GHX template,  confidence "medium"
    analysis_method "rule_based" — heuristic span/slenderness rules, confidence "low"
The verdict string names the method (e.g. "[RULE-BASED ESTIMATE, LOW CONFIDENCE] ...").
Treat rule_based/low results as estimates, NOT finite element analysis, and say so
when reporting to the user.

If the structure FAILS, modify the design (add supports, increase member size,
change material) and call execute_rhino_script + validate_structure again.
When worst_member_guids is present, edit only those offending members instead
of regenerating everything. Iterate up to 3 times before reporting the best attempt.

Args:
    guids: List of Rhino object GUID strings from execute_rhino_script output.
    structure_type: Analysis template to use. Options:
        "beam"       — simple beam bending/deflection
        "truss"      — axial force/buckling analysis
        "shell"      — shell stress/displacement
        "frame"      — moment/shear frame analysis
        "canopy"     — cantilevered canopy
        "gridshell"  — large deformation gridshell
        "membrane"   — form-finding membrane
        "highrise"   — high-rise structural systems
    load_kn: Applied load in kN (default 10.0).
    material: Material type: "Steel", "S355", "Concrete", "Wood", "Aluminium" (default "Steel").
    engine: "auto" | "native" | "karamba" (see above).
    fixed_supports: True = fully fixed supports, False = pinned (rotations free).
    self_weight: include member self weight.
    span_m: structural span in meters for the L/250 limit when members are split at
        every node (e.g. a 6.2 m joist drawn as two 3.1 m segments). Native engine only.
    asset_loads: add the gravity loads of placed library assets (estimated self weight
        plus in-use contents/occupants from each asset's load entry, e.g. a filled
        bathtub) where they stand on (or hang from) the frame. Placements come from
        Rhino objects tagged with an Almond asset id, or from the scene ledger when
        scene_id is given. Native engine only; the result's "asset_loads" lists every
        placement with its load and carrying members, or why it was not applied.
    scene_id: scene ledger to read placements from (default: tagged Rhino objects).
    floor_load_kn_m2: imposed floor load in kN/m2 (e.g. 2.0 for homes, EN 1991-1-1
        category A) on every bay enclosed by beams on a level; the beams take it by the
        45-degree rule (two-way, one-way above 2:1). Native engine only. A code floor load
        already covers movable furniture and people: combine it with asset_loads only for
        heavy specific items, and set load_kn to 0 to avoid double counting.
    floor_dead_kn_m2: superimposed dead load in kN/m2 (floor build-up, finishes) on the
        same bays.
    design_basis: "en1990" (default): deflection at SLS characteristic (G + Q), member
        checks at ULS 1.35 G + 1.5 Q. G = self weight, floor build-up and the weight of
        placed items; Q = load_kn, the occupancy floor load, contents and occupants.
        "unfactored" checks both at G + Q (the Karamba route's basis). Native engine.
    uls_combination: "6.10" or "6.10ab" (the worse of 6.10a and 6.10b per member). Default:
        the design code's choice (Eurocode profile: 6.10). A profile that prescribes one
        expression overrides the request (with a warning).
    design_code: design code profile for the numbers a code or National Annex sets
        (gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, deflection limit): "eurocode"
        (default, EN recommended values), any profile from list_design_codes, or "off"
        (unfactored G + Q, no partial factors; same as design_basis="unfactored").
        Results carry "design_code" with the values used and any unverified ones.
    fabrication: hollow steel sections (CHS/RHS) are "cold_formed" (default, EN 10219,
        buckling curve c) or "hot_finished" (EN 10210, curve a; a0 for S460). The difference
        is up to about 23 % in buckling resistance; use hot_finished only when specified.
    detail: native engine only. Adds "members" (per member: role, length, section, ULS design
        forces N/V/M/T, governing combination and check, slenderness, chi, stress,
        utilization, SLS deflection and span/deflection ratio, pinned ends) and "supports"
        (reactions Fx..Mz at SLS and each ULS combination). Off by default to keep replies short.
    connections: "rigid" (default: every joint transmits moment) or "simple": beams are
        pinned (major-axis bending released) and braces pinned in both axes where they
        stop - not where another member carries on in line - while columns stay
        continuous. Typical bolted steel and timber framing is closer to "simple"; rigid
        joints can flatter beam deflection. A curve's user text almond:release = "pinned" |
        "pinned_start" | "pinned_end" | "rigid" overrides either mode. Native engine.
    stability: "auto" (default): elastic critical load factor alpha_cr for every ULS
        combination (EN 1993-1-1 5.2.1) and sway imperfections phi = 1/200 x alpha_h x alpha_m
        (5.3.2) in +/-x and +/-y; alpha_cr < 10 runs a second-order (P-Delta) ULS analysis,
        alpha_cr <= 1 fails as unstable. "off": first-order without imperfections.
Prefer calling get_construction_guidance BEFORE generating the geometry:
pick a real construction system and size members from its depth/spacing
rules. This tool cross-checks the analyzed span against that same library
and appends a "construction_check" object (matching_systems with
fits_span and suggested member depths, plus warnings when the span falls
outside every curated system's range for this structure_type/material).

Returns:
    JSON from the bridge plus the construction_check. Top-level fields: status
    ("pass"|"fail"|"error"), passed (bool), verdict (text), suggestions,
    confidence ("high"|"medium"|"low"), warnings, and worst_member_guids
    (up to 5 Rhino GUIDs of the most over-utilized members — edit those
    first). The results object carries the numbers: max_deflection_mm,
    deflection_limit_mm, utilization_ratio, max_stress_mpa, yield_stress_mpa,
    span_m, analysis_method ("native"|"api"|"template"|"rule_based"), reactions_kn
    (total vertical reaction, api path only), and per_element_utilization —
    a list of {source_guids, utilization} entries (utilization 1.0 = at
    capacity) keyed back to the Rhino objects that produced each element.
<!-- /instruction:validate_structure -->

## list_design_codes

<!-- instruction:list_design_codes -->
Lists the design code profiles validate_structure / visualize_structure accept as design_code.

A profile holds the numbers a design code or National Annex sets (load factors gamma_G,
gamma_Q, psi_0, xi; the ULS expression; material factors gamma_M0, gamma_M1; the deflection
limit; suggested imposed floor loads), each with its source clause and a verified flag.
"eurocode" (EN recommended values) is built in and the default; "off" is unfactored mechanics.
Practices add National Annex profiles as JSON files in user_dir (see docs/structure/design-codes.md).
Unverified values are allowed but flagged in every result that uses them.

Returns JSON: default, profiles [{id, name, basis, origin, verified, unverified,
uls_expression, uls_default, deflection_limit_ratio, imposed_floor_kn_m2}], problems
(files that failed validation), user_dir.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds parameters, source, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_design_codes -->

## visualize_structure

<!-- instruction:visualize_structure -->
Run a live structural analysis on a line model and SHOW it in every Rhino viewport:
the undeformed wireframe, the exaggerated deformed shape coloured blue -> red by
displacement (or by utilization), supports, load arrows and a legend panel with
max deflection, the L/limit check and PASS/FAIL. Nothing is baked into the document.

Use it to make structural behaviour visible while designing: model the structural
axes as curves, include Rhino point objects at the supports, call this tool, then
fix the members it shows in red (add a column, shorten a cantilever, upsize the
section via beam_diameter_mm) and call it again. validate_structure gives the
auditable verdict; this tool is the visual, iterative view of the same solve.

Args:
    guids: Curve GUIDs of the structural axes plus point GUIDs marking supports
        (see fixed_supports). Without points, the lowest nodes are supported.
    load_kn: Total imposed load in kN, shared equally by the free nodes (-Z).
    material: "Steel", "S355", "Concrete", "Wood", "Aluminium".
    beam_diameter_mm, beam_wall_mm: circular hollow section for every member
        (default: inferred / CHS 114.3x4).
    self_weight: include gravity.
    fixed_supports: True = fully fixed supports, False = pinned (rotations free).
    deflection_limit_ratio: span/ratio limit, e.g. 250 for L/250. Default: the design code's
        limit (Eurocode profile: 250).
    span_m: reference span in meters for the limit (default: longest member).
        Set it when members are split at every node, e.g. a 6.2 m joist drawn
        as two 3.1 m segments.
    color_by: "displacement" or "utilization".
    scale: deformation exaggeration; omit for automatic (~6% of span).
    reveal: 0..1 fraction of members drawn (for staged construction playback).
    reanalyze: False re-uses the last solve and only changes the display
        (scale / color_by / reveal / physics / title) - cheap enough to animate.
    physics: False draws the same members as plain geometry with no analysis
        overlay ("physics off"), for before/after comparisons.
    display_guids: draw only these members (e.g. one frame line for a section
        view); the analysis still covers every member in guids.
    title: legend title.
    clear: remove the overlay.
    engine: "auto" (default: Almond's native frame solver, no Karamba needed; Karamba
        when the selection has shells or the bridge cannot export a model),
        "native" or "karamba".
    asset_loads, scene_id: add the loads of placed library assets (native engine), as in
        validate_structure; loaded points are drawn with load arrows.
    floor_load_kn_m2, floor_dead_kn_m2: floor area loads on every enclosed bay, as in
        validate_structure.
    design_basis, uls_combination, design_code: as in validate_structure; the overlay draws
        the SLS deflected shape coloured by the ULS utilization envelope.
    connections: "rigid" or "simple", as in validate_structure; pinned ends are drawn
        as small circles.
    stability: "auto" or "off", as in validate_structure.
    view: "deflection" (default) or "buckling": draw the first buckling mode of the
        governing ULS combination with its alpha_cr (STABLE >= 10, SWAY-SENSITIVE 1-10,
        UNSTABLE <= 1) instead of the deflected shape.

Returns JSON: status ("pass"|"fail"|"error"|"cleared"), max_displacement_mm,
deflection_limit_mm, span_m, max_utilization, scale, per-element
{source_guids, max_displacement_mm, utilization}, warnings.
The native engine reports analysis_method "native"; engine="karamba" needs
Karamba3D 3.1 (the trial caps models at 20 beam elements).
<!-- /instruction:visualize_structure -->

## export_structural_report

<!-- instruction:export_structural_report -->
Renders the persisted validate_structure history to a Markdown report.

Every successful validate_structure call is recorded in the local state
database (inputs, analysis method, confidence, numbers, warnings). This
tool writes them to a .md file, newest first, with an explanation of the
analysis pathways and pass criteria.

Args:
    path: Output file path. Default:
        <user data dir>/reports/structural-validation-<timestamp>.md
    limit: Maximum number of runs to include (default 50, max 500).
Returns:
    JSON with the report path and run count.
<!-- /instruction:export_structural_report -->

## response-981

<!-- instruction:response-981 -->
- Only **api** runs are finite element analysis; reactions_kn is
<!-- /instruction:response-981 -->

## response-982

<!-- instruction:response-982 -->
  populated on the api path only and should equal the applied load
<!-- /instruction:response-982 -->

## response-983

<!-- instruction:response-983 -->
- Known gaps in karambaCommon 3.1.60519 (issue #6): api-mode
<!-- /instruction:response-983 -->

## response-984

<!-- instruction:response-984 -->
  max_deflection and per-element utilization may read 0.0 due to
<!-- /instruction:response-984 -->

## response-985

<!-- instruction:response-985 -->
  signature drift — trust reactions and stability diagnostics;
<!-- /instruction:response-985 -->

## response-986

<!-- instruction:response-986 -->
  cross-check deflection against the rule_based estimate.
<!-- /instruction:response-986 -->

## response-987

<!-- instruction:response-987 -->
- rule_based results are labeled LOW CONFIDENCE for a reason: treat
<!-- /instruction:response-987 -->

## response-988

<!-- instruction:response-988 -->
  them as sanity checks, not engineering.
<!-- /instruction:response-988 -->

## response-1026

<!-- instruction:response-1026 -->
No validation runs recorded yet - call validate_structure first.
<!-- /instruction:response-1026 -->

## response-1031

<!-- instruction:response-1031 -->
view='buckling' draws the buckling mode.
<!-- /instruction:response-1031 -->
