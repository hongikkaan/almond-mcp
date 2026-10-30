# Native frame solver

`validate_structure` analyses line models (beams, columns, trusses, frames) with
Almond's own 3D frame solver by default. Users no longer need Karamba3D for these;
Karamba remains available for shells and as a cross-check.

| | Native (`engine="auto"` / `"native"`) | Karamba (`engine="karamba"`) |
| --- | --- | --- |
| Install | nothing beyond almond-mcp + RhinoAlmondBridge | Karamba3D 3.1 licence (trial: 20 members) |
| Elements | straight beams (axial, torsion, biaxial bending), truss bars | beams, shells |
| `analysis_method` | `"native"` | `"api"` / `"template"` / `"rule_based"` |

## Design codes

Combination factors, material factors and the deflection limit come from a design code profile:
the built-in Eurocode recommended values by default, a National Annex file you add, or `off`
(unfactored). See [design-codes.md](PROFILES-SPEC.md).

## In the Almond panel

The same engine runs from the panel, with no AI client: run **AlmondStructure**,
keep the engine on **Almond native**, select the members and **Use Rhino
selection**. Step 02 adds the native options (floor imposed and build-up loads,
loads from placed models, connections, load combinations, stability, deflection
span, and the viewport overlay: deflected shape or first buckling mode).
**Run native analysis** exports the conditioned line model, runs
`almond-mcp solve` out of process (JSON in, JSON out: `src/mcp/features/structure/structure_study.py`),
draws the result through the same `structure_draw` overlay the MCP tools use,
and fills step 04 with deflection, utilization, the governing combination,
αcr and the load facts. **Clear viewport overlay** removes the drawing.

**Open full results ↗** (or the `AlmondResults` command) opens the **Almond Results** panel,
docked beside the Almond panel: a summary, then every member (role, section, length, ULS
utilization with its governing check and combination, design forces N/V/M/T, stress, slenderness
and χ, SLS deflection and span/deflection, end connections), the support reactions for each
combination, the combinations and stability, the loads and settings, and all notes. Click a member
to select it in Rhino; **Save CSV** writes the member table. The same tables are available to the
MCP tools with `validate_structure(..., detail=True)`.

The panel and `visualize_structure` share `native_structure` and `structure_study.draw_message`.

The plugin finds the solver as `uvx almond-mcp@<plugin version> solve` (a
development build without a release version takes the latest), or the
command line in `ALMOND_SOLVER_COMMAND`. A protocol number in every request
and reply catches a plugin/solver mismatch.

## Live view

`visualize_structure` uses the same engines: the server exports the model
(`structure_model`), solves it with `frame_solver`, and sends the solved field to the
bridge (`structure_draw`), which draws it with the same overlay as the Karamba route —
deformed shape coloured by displacement or utilization, supports, loads and a
PASS/FAIL legend. Display-only updates (`reanalyze=False`: scale, colouring, reveal,
physics on/off, `display_guids`) resend no geometry.

`engine="auto"` routes to Karamba when the structure type is shell, gridshell or
membrane, when the selection contains shells, or when the installed bridge cannot
export a structural model (older than this change); the result then carries a
warning saying why.

## Method

- Direct stiffness method, Euler-Bernoulli beams, 6 DOF per node, rigid joints
  (`src/mcp/features/structure/frame_solver.py`, numpy only, written from the textbook method).
- Uniform and linearly varying member loads (self weight, floor-load triangles and
  trapezoids) are exact within each member: consistent fixed-end forces, Hermite
  interpolation of the end displacements plus the fixed-fixed particular solution
  `v = x²(L−x)²[w_a(3L−x) + w_b(x+2L)] / 120EIL`, so one element per member gives the
  exact deflected shape and moment diagram.
- Linear elastic, static; first order, with a second-order (P-Δ) analysis when the
  stability check calls for it (see Stability). Singular systems are reported as a
  **mechanism** with the nodes involved, never solved silently.
- Rotations at nodes that only truss bars meet are restrained automatically and
  reported (they carry no load).

## Modelling conventions (same as the Karamba path)

The bridge's `structure_model` message exports the conditioned geometry used by the
Karamba path: welded nodes, members split at intersections, inferred sections, curved
axes polygonized identically. `src/mcp/features/structure/native_structure.py` then applies:

- **Supports:** declared Rhino points (snapped to the nearest node within 50 mm), else
  every lowest-Z node. `fixed_supports=False` pins them (translations only).
- **Loads:** `load_kn` shared equally by the free nodes, acting downward; self weight
  γ·A along every member unless `self_weight=False`.
- **Deflection limit:** span/250. Span = longest member for beam/frame, else overall
  extent; `span_m` overrides it when members are split at every node (a 6.2 m joist
  drawn as two 3.1 m segments).
- **Member checks (EN 1993-1-1, `src/mcp/features/structure/ec3.py`), per member** (the member between its
  joints, whatever the analysis split it into), for every ULS combination:
  - **Section class** from Table 5.2 for the actual stresses, with ε = √(235/f_y):
    CHS d/t against 50/70/90 ε² (Class 4 above 59.6 in S355); RHS walls (c = h − 3t) and
    I-section webs from ψ and α; I-section flange outstands 9/10/14 ε. **Class 4 fails as
    not covered** (effective sections, EN 1993-1-5/-1-6, are not applied).
  - **Cross-section** 6.2.1(7) `|N|/N_Rd + |M_y|/M_y,Rd + |M_z|/M_z,Rd` (CHS: resultant
    moment), elastic moduli by default; plastic only for Class 1/2 when plastic design is
    requested.
  - **Flexural buckling** 6.3.1 about both axes with L_cr = the member length, curves from
    Table 6.2: hollow sections **cold-formed (EN 10219) → curve c by default**, hot-finished
    (EN 10210) → a (a0 for S460) with `fabrication="hot_finished"`; rolled I by h/b and t_f.
  - **Compression + bending** 6.3.3 (6.61)/(6.62) with the **Annex B** interaction factors
    (Class 3 form with elastic moduli, Class 1/2 form with plastic) and Table B.3 C_m:
    0.6 + 0.4ψ ≥ 0.4 for linear moment diagrams, the table's upper bound 1.0 for members
    with transverse load.
  - γ_M0, γ_M1 from the design code profile.

**Not covered:** shells, large-displacement (geometrically nonlinear) analysis beyond P-Δ, member bow imperfections (5.3.2(6)), lateral-torsional buckling (hollow sections are immune; I-sections are not checked for it), shear resistance (6.2.6) and torsion, Class 4 effective sections, aluminium to EN 1999, dynamics, connections. Results are a preliminary design check, not an engineer's sign-off.

### Validation

- `src/mcp/tests/test_hand_calculations.py` and `src/mcp/tests/test_ec3.py`: closed forms worked from first
  principles and from the standard's text (beam, cantilever, column buckling on curves a and
  c, Table 5.2 classes by grade, Table B.3 C_m, an Annex B case where k = 1.3).
- `src/mcp/features/structure/validation/mutation_check.py` plants known engineering errors one at a time (wrong factors,
  wrong curve, unscaled class limits, buckling length of one analysis element, ...) and
  reports whether the tests catch each.
## Stability (EN 1993-1-1 5.2)

With `stability="auto"` (the default), every ULS combination gets:

- **Elastic critical load factor α_cr**: the smallest α with det(K + α·K_G) = 0, where K_G is
  the consistent geometric stiffness from the first-order axial forces (compression softens,
  tension stiffens; Wagner term in torsion). Solved as a symmetric eigenproblem through the
  Cholesky factor of K. Compression members are split into 4 elements first — one element
  per member overstates α_cr by ~22 % for a pin-ended column; four are within ~0.05 %.
- **Sway imperfections** (5.3.2): φ = φ₀·α_h·α_m with φ₀ = 1/200, α_h = 2/√h (⅔…1),
  α_m = √(0.5(1 + 1/m)), h the height of the structure and m the number of column lines,
  applied as horizontal forces φ·V at every loaded node in +x, −x, +y and −y; the member
  checks take the worst direction. No columns (no height) → no sway imperfection.
- **Regime** (5.2.1): α_cr ≥ 10 → first-order results; 1 < α_cr < 10 → a second-order
  (P-Δ) ULS analysis, iterating (K + K_G(N))·u = F until the axial forces settle; α_cr ≤ 1
  (or a second-order stiffness that stops being positive definite) → **FAIL, unstable**.
- Member buckling checks use L_cr = the member length, also when the stability check has
  split the member into elements: conservative for non-sway frames (α_cr ≥ 10) and permitted
  after a global second-order analysis with sway imperfections (5.2.2(7)b).

`visualize_structure(view="buckling")` draws the first buckling mode of the governing ULS
combination with its α_cr and a STABLE / SWAY-SENSITIVE / UNSTABLE badge.
`stability="off"` returns to first-order without imperfections.

Verified against closed forms: pin-ended Euler column (one element: exactly 12/π² × the
Euler load, the textbook value; eight: within 0.003 %), cantilever (2L effective length),
sway of a fixed-base portal with a stiff beam (π²EI/L² per column, within 0.04 %), and the
exact second-order cantilever deflection H/(Pk)·(tan kL − kL) and base moment (within
1e-5).

## Connections (end releases)

`connections="rigid"` (default) makes every joint transmit moment. Real bolted steel and
timber framing is usually closer to **simple construction**, and rigid joints flatter
beam deflection, so `connections="simple"` models it:

- **Beams** (members within ~3° of horizontal) are pinned for major-axis bending where they
  *stop* — not where another member carries on in line, so pieces drawn along one line
  form one continuous member and secondary beams pin into continuous primaries and walls.
  Minor-axis (plan) rotation stays continuous, which is what stops pin-ended columns
  spinning about their own axis.
- **Braces** (inclined members) are pinned in both bending axes; **columns** stay continuous.
- Torsion is released at one end of any member pinned at both ends, so it cannot twist as
  a rigid body.
- **Per member:** a curve's user text `almond:release` = `pinned` | `pinned_start` |
  `pinned_end` | `rigid` overrides either mode (the bridge exports the curve's own start and
  end so one-sided releases know the direction).

**Sections per curve.** A curve's user text `almond:section` sets its section, in millimetres unless a
unit follows (`rect 30x64 cm`):
`rect 300x640` (solid, width x depth: concrete, timber), `box 200x300x8` (width x depth x wall) or
`chs 114.3x4` (diameter x wall). It takes precedence over a section inferred from the geometry; the
panel's *Override beam section* still overrides everything. An unreadable value is reported as a
warning and the inferred or default CHS is used.

The solver applies releases by **static condensation**: the released end DOFs are
eliminated from the member's stiffness and fixed-end forces, then recovered after the solve
so deflected shapes and moment diagrams stay exact (a member pinned at both ends between
fixed supports reproduces 5wL⁴/384EI with zero end moments). Releases can leave rotations
that nothing stiffens, or let pieces of a member twist as a group with no load acting on
them; those zero-energy, rotation-only modes are pinned out and reported. A mode that moves
a translation or carries load is a real mechanism and is reported as one (for example a chain
of pin-ended pieces with nothing under the shared node). The overlay draws pinned ends as
small circles.

## Load combinations (EN 1990)

Every load carries a case: **G** (permanent — self weight, `floor_dead_kn_m2`, the weight
of placed items) or **Q** (variable — `load_kn`, `floor_load_kn_m2`, contents and
occupants of placed items). The solver factorises the stiffness matrix once, solves each
case, and builds every combination by exact superposition (displacements, member forces
and member load shapes), so a combination costs no extra solve.

With `design_basis="en1990"` (the default):

| Check | Combination | Factors |
| --- | --- | --- |
| Deflection (L/250) | SLS characteristic | 1.0 G + 1.0 Q |
| Member utilization | ULS 6.10 (default) | 1.35 G + 1.5 Q |
| Member utilization | ULS 6.10a / 6.10b (`uls_combination="6.10ab"`), worse per member | 1.35 G + 1.05 Q / 1.15 G + 1.5 Q |

Recommended values of EN 1990 Table A1.2(B) (γ_G 1.35, γ_Q 1.5, ψ0 0.7 for category A,
ξ 0.85); national annexes may differ. Results report the governing combination per member,
every combination's maxima and reactions, and the overlay draws the SLS shape coloured by
the ULS envelope. `design_basis="unfactored"` checks both at G + Q, which is the Karamba
route's basis.

## Floor area loads

`validate_structure(..., floor_load_kn_m2=2.0, floor_dead_kn_m2=1.0)` (and the same on
`visualize_structure`) loads every floor bay of the frame:

- **Bays** are the areas enclosed by beams on one level (faces of the plan graph, found
  with a half-edge walk). A straight line between two adjacent supports with no beam
  along it is a **bearing wall**: bays close on it and its share goes straight into those
  supports (in the reactions, bending no member). Diagonals between supports that would
  cut an already closed bay are rejected.
- **Distribution:** rectangular bays use 45° lines from the corners — short edges carry a
  triangle, long edges a trapezoid; above 2:1 the bay spans one way onto its long edges.
  Other convex bays use a centroid fan (each edge a triangle peaking under the centroid).
- **Exact:** members are split at the load shape's kinks and each part carries a linear
  load, solved exactly (a triangle on a simple span reproduces `WL³/60EI` and `WL/6`).
- **Loads:** `floor_load_kn_m2` is the imposed (occupancy) load — e.g. 1.5–2.0 kN/m² for
  homes (EN 1991-1-1 category A) — and `floor_dead_kn_m2` the superimposed dead load
  (build-up, finishes). Set `load_kn=0` so the generic node load does not double count.

## Loads from placed assets

`validate_structure(..., asset_loads=True)` and `visualize_structure(..., asset_loads=True)`
add the gravity load of every placed library asset that stands on (or hangs from) the
frame:

- **Load data:** `asset/models/GeneratedAssetfiles/structural-loads.json` gives each of the 50 library
  assets an estimated self weight (dead) and in-use load (imposed: occupants at 80 kg,
  water in a filled bath, books on shelves), with category defaults for other libraries.
  These are typical-product estimates, not measured or manufacturer data. The internal asset passport reader also retains `structural_loads`.
- **Placements:** Rhino objects tagged with an Almond asset id (`Almond.AssetId`,
  `almond:asset_id`) via the bridge's `asset_placements` message. Scene ledger IDs are not public load inputs.
- **Load path:** floor items load the highest frame level up to 1.6 m below their base (a
  lamp on a desk still loads the floor); ceiling items hang from the lowest level up to
  1.5 m above their top. The load goes to the nearest member, or is shared by the lever
  rule between the two parallel members either side (a floor spanning one way between
  them). Members are split at the load points, so point loads are exact.
- **Not applied, and reported why:** wall-mounted items, ground-only items (trees, cars,
  street furniture), structural elements, assets outside the frame's plan, and assets
  with no frame level below.
- **Sizes:** the load is the nominal product's. A placement whose plan size differs from
  the catalogue product by more than 1.5× (or less than 0.67×) is flagged, not rescaled:
  Almond's placement scale usually corrects generated-mesh proportions.

**Asset loads and floor loads.** A code imposed floor load (`floor_load_kn_m2`, e.g.
EN 1991-1-1 category A, 1.5–2.0 kN/m²) already covers movable furniture and people. Use
asset loads to check heavy, specific items (a filled bath, full bookshelves, a kitchen
island) on top of the floor load — accepting some double counting as conservative — or
on their own with the superimposed dead load as a furniture check.

## Verification

`src/mcp/tests/test_frame_solver.py`, `test_hand_calculations.py` and `test_ec3.py` compare closed-form beam/column results, equilibrium, superposition, orientation invariance, mechanisms, section properties and member checks. `test_native_structure.py` compares the reference cases in `src/mcp/tests/data/karamba_reference.json`; `features/structure/validation/mutation_check.py` checks whether known calculation faults are detected.

The native solver uses Euler-Bernoulli beams while Karamba may include Timoshenko shear deformation, so differences must be interpreted against the actual analysis method and assumptions. Benchmark outputs belong under ignored `data/`, not in this contract. Live functionality is verified in the working Rhino files the user connected, preserving existing model state.
