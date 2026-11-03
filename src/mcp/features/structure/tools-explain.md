# tools.py explain

## validate_structure

<!-- instruction:validate_structure -->
Analyze selected live Rhino geometry under explicit loads, support assumptions and structural design settings.

When to use: Check a structural scheme and locate governing member demand, deflection or stability issues.
Before calling: Confirm geometry scope, actual supports, sections, material, joint behavior and load basis. Loads are kN, floor loads kN/m2 and span_m metres; native load_kn is a total downward (-Z) imposed load shared equally among free nodes. Use the full physical span when members are segmented. Avoid counting occupancy/furniture twice when combining floor and asset loads; load_kn may need to be zero.
Inputs from earlier results: Pass observed Rhino object id strings to guids (request include_ids=true on object discovery), not asset/scene IDs. list_design_codes.profiles[].id, obtained with include_ids=true, maps to design_code. Construction/reference loads are guidance and require conversion to the applied load scope, not direct copying of kPa as kN.
Interpretation: Report results.analysis_method, confidence, warnings and design_code.unverified. auto uses native frames for line models, otherwise Karamba; forced karamba tries api/high, template/medium then rule_based/low. results deflections are mm, stresses MPa, spans m; utilization 1 means capacity. per_element_utilization[].source_guids and worst_member_guids locate objects; detail=true adds members/support reactions. Native EN 1990 uses SLS G+Q and ULS combinations; stability=auto adds imperfections and P-Delta when alpha_cr<10, failing instability at <=1.
Limits: Rule-based results are estimates, not FEA. Native steel checks exclude lateral-torsional buckling and use member length for flexural buckling; non-steel capacity may be indicative with no pass/fail. High confidence is not code certification. Karamba checks unfactored loads; floor/asset loads are native-only and fallback warnings matter. construction_check is a heuristic span/depth cross-check, not capacity proof. Connections/load path govern interpretation, not red-member replacement alone. This does not edit model geometry; pass/fail runs are recorded best-effort for export_structural_report, while error/indicative runs need not appear.

Args:
    guids: Current Rhino object GUID strings in the analysis scope.
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
The tool also compares the analyzed span with the construction-system library
and appends a "construction_check" object (matching_systems with
fits_span and suggested member depths, plus warnings when the span falls
outside every curated system's range for this structure_type/material).

Returns:
    JSON from the bridge plus the construction_check. Top-level fields: status
    ("pass"|"fail"|"error"), passed (bool), verdict (text), suggestions,
    confidence ("high"|"medium"|"low"), warnings, and worst_member_guids
    (up to 5 Rhino GUIDs of the most over-utilized members). The results
    object carries the numbers: max_deflection_mm,
    deflection_limit_mm, utilization_ratio, max_stress_mpa, yield_stress_mpa,
    span_m, analysis_method ("native"|"api"|"template"|"rule_based"), reactions_kn
    (total vertical reaction, api path only), and per_element_utilization —
    a list of {source_guids, utilization} entries (utilization 1.0 = at
    capacity) keyed back to the Rhino objects that produced each element.
<!-- /instruction:validate_structure -->

## list_design_codes

<!-- instruction:list_design_codes -->
List the design-code profiles available to structural validation and viewport analysis.

When to use: Choose numerical load/material factors, ULS expressions and deflection limits for the intended jurisdiction.
Before calling: No model or prior result is required; the built-in default is eurocode and off selects unfactored mechanics.
Inputs from earlier results: None required. Request include_ids=true and pass profiles[].id as validate_structure.design_code or visualize_structure.design_code.
Interpretation: Summary shows name, basis, verified and unverified parameter names. field_groups=["parameters"] adds ULS choices, deflection_limit_ratio (250 means L/250) and imposed_floor_kn_m2 suggestions; ["source"] adds origin. problems lists profiles rejected during loading; user_dir identifies the optional custom-profile folder.
Limits: verified concerns profile values, not approval of a structure or project compliance. Unverified values are allowed and flagged in analysis results. off still uses an indicative L/250 screen; listing a floor-load suggestion does not apply it to a model.

<!-- /instruction:list_design_codes -->

## visualize_structure

<!-- instruction:visualize_structure -->
Analyze live Rhino structural axes and display a temporary viewport overlay of deformation, utilization or buckling behavior.

When to use: Inspect load paths, support assumptions and iterative design changes visually without baking geometry.
Before calling: Supply structural curve GUIDs and support-point GUIDs, or accept lowest-node supports. Match actual joints and load scope; kN loads, kN/m2 floor loads, mm section sizes and metre spans are distinct. Use clear=true to remove the overlay.
Inputs from earlier results: Reuse validate_structure's geometry scope or observed object id strings as guids; request include_ids=true on discovery. Use per_element_utilization[].source_guids for display_guids to isolate members visually without shrinking analysis scope. list_design_codes.profiles[].id maps to design_code. Even reanalyze=false requires a nonempty guids list unless clearing.
Interpretation: Deformation is exaggerated by scale, not actual geometry. Native overlays combine SLS displacement with ULS utilization; read max_displacement_mm, deflection_limit_mm, max_utilization, analysis_method and warnings. Red may mean displacement or utilization according to color_by, not a diagnosed design cause. Buckling mode shape has no physical displacement magnitude: use buckling.alpha_cr (>1 for the returned pass; 1-10 remains sway-sensitive, >=10 the first-order threshold).
Limits: reanalyze=false reuses the prior solve and only changes display; it does not validate changed geometry or loads. physics=false/reveal/display_guids affect presentation only. No objects are baked, but viewport state changes. Native non-steel results can be indicative; read status rather than claiming a pass. Karamba requires its runtime (3.1 trial: 20 beam elements); fallback/load warnings and validate_structure's analysis limits still apply.

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
    asset_loads: add the loads of placed library assets (native engine), as in
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
Write locally recorded structural-validation runs to a newest-first Markdown report.

When to use: Export the persisted validation history for review without running another solve.
Before calling: Ensure the intended validate_structure pass/fail runs were recorded; select an output path and run limit. No live Rhino analysis occurs.
Inputs from earlier results: This reads history automatically rather than accepting validation JSON or GUIDs. A prior validate_structure response may not be present if best-effort persistence failed; an empty history returns an error.
Interpretation: path locates the written .md file, runs is the exported count and latest_method identifies the newest stored analysis method. Stored numbers, confidence, verdicts and warnings describe past runs, not current model state.
Limits: The limit is clamped to 1..500. Parent folders are created and an existing target file is overwritten. The history stores summary fields, not all detailed settings/member results; exported pathway/pass-criteria narrative is static and may not fully describe current native/code behavior. Export is not a fresh validation or engineering certification.

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
