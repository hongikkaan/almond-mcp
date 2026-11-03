# Construction-system guidance: real assemblies, not arbitrary members

Why Almond v0.6 adds a construction knowledge layer, where its numbers come from, and how it threads through `get_construction_guidance`, `validate_structure`, and `assign_material`.

## The problem it solves

Karamba validation (see [structural-validation.md](../structure/validation/SPEC.md)) tells you whether a set of members *solves* — deflection, utilization, reactions. It cannot tell you whether the members correspond to anything a builder would recognize: a 15 m sawn-lumber joist can pass FEA if you make it deep enough, but it is not a thing that exists. The construction library closes that gap with curated knowledge of how structural systems are actually formed: which material, which element roles, what spans and spacings are real, and what member depth a given span implies.

## Source and honesty

Parameters are distilled and paraphrased from **Francis D.K. Ching, *Building Construction Illustrated*, 4th ed. (Wiley, 2014)** — each system entry carries `bci_ref` section numbers. They are the book's preliminary-sizing rules of thumb (e.g. steel beam depth ≈ span/20, wood joist depth ≈ span/16, open-web joist span ≤ 24 × depth), intended for design plausibility, **not** a substitute for engineering analysis or the governing code. The manifest states this in its `source` field and every `construction_check` repeats it.

## The library

`src/mcp/profiles/construction_system/manifest.json` — 23 systems across four categories:

| Category | Systems |
| --- | --- |
| floor | wood joist, wood I-joist/trussed joist, plank-and-beam, steel wide-flange, open-web steel joist, light-gauge steel joist, one-way slab, one-way joist (pan) slab, flat plate/flat slab, waffle slab, precast hollow-core, precast tees |
| wall | wood platform framing, cast-in-place bearing wall, concrete column grid, reinforced CMU, steel column frame |
| roof | steel rigid frame, steel trusses, space frame, wood rafters, wood trusses |
| foundation | concrete shallow foundation (spread footings / walls / slab on grade) |

Each system entry:

- `structural_material` — `validate_structure`'s material vocabulary (`Steel`, `Concrete`, `Wood`; `S355` is normalized to Steel).
- `structure_types` — which `validate_structure` templates the system maps to.
- `render_material_ids` — Materialfiles PBR ids, so the declared construction material is *visible in Rhino* and survives GLB/Datasmith export.
- `span_range_m` — real span range (for `category: wall`, `span_axis` is `"vertical"` and the range is unsupported height).
- `depth_rules` — `depth ≈ span / span_ratio` rules per element.
- `typical_spacing_m`, `elements` (role + guidance), `construction_notes`, `bci_ref`, `tags`.

The manifest also ships `reference` tables: occupancy live loads (kPa) and material densities (kg/m³) from BCI appendix A.06–A.07, for choosing `load_kn` inputs honestly.

Every parameter is itemized with its exact BCI section title and page in the generated **[construction spec register](../../profiles/construction_system/SPEC.md)** (`src/mcp/features/guidance/build_spec_register.py` regenerates it from the manifest).

## The workflow

```
get_construction_guidance(material="Wood", structure_type="beam", span_m=4.5)
        │  pick a system; size members from depth/spacing rules
        ▼
execute_rhino_script          — generate members at real sections/spacings
        ▼
assign_material(guids, "wood-oak",
                structural_role="joist",
                construction_system="wood-joist-floor")
        │  applies material and the supported metadata described below
        ▼
validate_structure(guids, "beam", load_kn, "Wood")
        │  Karamba pathway as before, PLUS construction_check appended:
        │  which curated systems cover this structure_type/material,
        │  fits_span per system, suggested depths, and a warning when the
        │  span is outside every curated system's range
```

`construction_check.warnings` are also merged into the response's top-level `warnings`, so an implausible-as-drawn structure is flagged even when the solver passes it.

## Egress checking

`check_egress` turns the manifest's egress rules into one verdict pass: occupant load from plate area and occupancy, required exit count (tiers + the multi-story minimum of two), exit separation against the plate diagonal, total and per-exit egress widths, and optional measured travel distances and dead-end lengths. Each check names its requirement, the provided value, and its basis, so a failing layout says what to fix (add an exit, move a core, widen a stair). IBC-typical numeric factors are labeled as such and the response repeats the verify-governing-code note.

## 재료·구축 레이어 구현

도구 입력은 `tools/list`의 `setup_modeling`·`assign_material` 설명 전문과 schema를 따른다. 설명 원본은 [모델링 도구 설명](../modeling/tools-explain.md), Layer 위계는 위 setup_modeling 설명에, 과업별 구축 상세화 판단은 [get_construction_guidance 설명](tools-explain.md)에 있다.

MCP owns catalog loading, material choices, construction-layer specifications and metadata policy. `modeling_setup.py` supplies resolved recipes to the shared C# implementation in `src/mcp/rhino/`. The Bridge compiles those files to execute Rhino API operations on its UI thread; it does not independently read the material or construction manifests. Native document access, Undo recovery, panels and geometry services remain in RHP. `DocumentLayers.Ensure` is the common native layer-path adapter used by drawing styles, asset placement and setup.

`setup_modeling(overwrite: boolean)` registers Materials then Layers in one native execution. The boolean is required and applies to both tables: false creates missing entries and preserves all existing values; true updates prescribed properties. No operation selector or UI prompt is used. New materials use readable manifest names. Existing `ALMOND::<id>` render materials are recognized; false preserves their names and reports the difference, while true reconciles them. Conflicting material IDs or legacy material-table entries without matching render content are reported for inspection rather than silently replaced.

Layers use `M/category/system.name/element.role` with material and matching display/print colors. Existing Layers are unchanged when overwrite=false, even when they differ from the library. The system default is the first `render_material_ids` entry. Current role defaults use galvanized steel for connection/reinforcement/decking and birch plywood for Wood subfloor/sheathing; these are setup choices, not mappings present in the construction manifest. M and category containers are gray. Setup preserves objects, their layer assignments/ByLayer choices and unrelated Layer properties.

Confirmed full application returns `{status: "success", applied: true}`. Otherwise a completed setup returns `{status: "incomplete", applied: false, differences: [...], errors: [...]}`. Each difference names kind/material-or-layer name/property/current/expected; errors name kind/name/message. This can include preserved differences and partial changes, and does not imply rollback. Transport timeout or an unreadable native result is `mutation_state: "unknown"`; inspect before any retry. No processing counts are represented as created-object counts.

`assign_material` preserves the object's layer and unspecified metadata. Registration, assignment, layer setup and archive placement share one PBR implementation. Archive recipes with hash-suffixed names reuse only exact names and remain separate from legacy `ALMOND::<id>` materials. Direct batch scripts may call `ModelingMaterials.CreateAttributes` with a resolved recipe JSON string; passing only a library ID is no longer supported. No operation guesses a layer from a material name or watches material-table events to move unrelated objects. Catalog reads and plugin startup create no modeling state.

MCP checks `modeling_materials=2` before these mutations and additionally `modeling_setup=1` before combined setup, rejecting an older loaded Bridge before dispatch. RHP source changes require a rebuilt Bridge and a new Rhino process. Rebuilding a file does not change a running process's assembly.

`modeling_policy.json` defines supported material-assignment keys and legacy metadata names. Material assignment accepts floor, construction-detail label, typed construction reference and structural role; names remain optional/free. Component identities, group bindings, Scene context and semantic children live in the document-private registry described by the [Component contract](../components/SPEC.md), not in newly written object stamps. Necessary stable material IDs, asset provenance and licensing fields are retained where real consumers need them. New assignments stop duplicating material name/category, UE slot and PBR channels onto object user strings: native materials hold the visual values. Existing unrelated user strings are preserved. Legacy key names remain documented for reading existing files, not as a list of required new stamps.

The existing construction catalog contains preliminary construction systems, not verified detail drawings. A human-readable construction label and a typed stable source reference are stored separately. A system ID is not relabeled as a certified detail ID. Floor values are supplied, not inferred from names or layer strings. Metadata updates do not erase unrelated user keys.

## Companion narration

`asset/history/Historyfiles/manifest.json` + `get_typology_narrative` provide historical narratives, precedents and urban roles from Ching/Jarzombek/Prakash, *A Global History of Architecture*, linked to construction-system IDs and page references (`gha_ref`). They contain no project-specific dimensions, loads or structural capacity. Page-indexed TOCs remain in [reference/](../../profiles/construction_system/references) for deeper reading.
