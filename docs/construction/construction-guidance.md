# Construction-system guidance: real assemblies, not arbitrary members

Why Almond v0.6 adds a construction knowledge layer, where its numbers come from, and how it threads through `get_construction_guidance`, `validate_structure`, and `assign_material`.

## The problem it solves

Karamba validation (see [structural-validation.md](../structure/structural-validation.md)) tells you whether a set of members *solves* — deflection, utilization, reactions. It cannot tell you whether the members correspond to anything a builder would recognize: a 15 m sawn-lumber joist can pass FEA if you make it deep enough, but it is not a thing that exists. The construction library closes that gap with curated knowledge of how structural systems are actually formed: which material, which element roles, what spans and spacings are real, and what member depth a given span implies.

## Source and honesty

Parameters are distilled and paraphrased from **Francis D.K. Ching, *Building Construction Illustrated*, 4th ed. (Wiley, 2014)** — each system entry carries `bci_ref` section numbers. They are the book's preliminary-sizing rules of thumb (e.g. steel beam depth ≈ span/20, wood joist depth ≈ span/16, open-web joist span ≤ 24 × depth), intended for design plausibility, **not** a substitute for engineering analysis or the governing code. The manifest states this in its `source` field and every `construction_check` repeats it.

## The library

`asset/constructions/Constructionfiles/manifest.json` — 23 systems across four categories:

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

Every parameter is itemized with its exact BCI section title and page in the generated **[construction spec register](construction-spec-register.md)** (`src/mcp/tools/build_spec_register.py` regenerates it from the manifest).

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

도구 입력과 적용 기준은 [템플릿 지침](../modeling/guidance/modeling-guide.md#템플릿재료구축-레이어)과 [모델링 지침](../modeling/guidance/modeling-guide.md#형상-편집설계-자료)을 따른다.

MCP owns catalog loading, material choices, construction-layer specifications and metadata policy. `modeling_setup.py` supplies resolved recipes to the shared C# implementation in `src/mcp/almond_mcp/rhino/`. The Bridge compiles those files to execute Rhino API operations on its UI thread; it does not independently read the material or construction manifests. Native document access, Undo recovery, panels and geometry services remain in RHP. `DocumentLayers.Ensure` is the common native layer-path adapter used by drawing styles, asset placement and setup.

`setup_modeling(operation="materials")` registers the library under its readable names. Omit `overwrite` for one Yes/No choice in Rhino; true updates matching materials, false leaves them as they are. Existing `ALMOND::<id>` names are accepted for migration, but new materials use the manifest's `name`.

`setup_modeling(operation="layers")` creates/reuses `M/category/system.name/element.role`, sets material and matching display/print colors, and leaves all objects in their existing layers. The system default is the first `render_material_ids` entry. Current role defaults use galvanized steel for connection/reinforcement/decking and birch plywood for Wood subfloor/sheathing; these are setup choices, not mappings present in the construction manifest. M and category containers are gray. Existing matching materials are reused.

`assign_material` preserves the object's layer and unspecified metadata. Registration, assignment, layer setup and archive placement share one PBR implementation. Archive recipes with hash-suffixed names reuse only exact names and remain separate from legacy `ALMOND::<id>` materials. Direct batch scripts may call `ModelingMaterials.CreateAttributes` with a resolved recipe JSON string; passing only a library ID is no longer supported. No operation guesses a layer from a material name or watches material-table events to move unrelated objects. Catalog reads and plugin startup create no modeling state.

MCP checks `modeling_materials=2` before these mutations; older Bridges with automatic material routing are rejected. RHP source changes require a rebuilt Bridge and a new Rhino process. Rebuilding a file does not change a running process's assembly.

`modeling_policy.json` defines supported keys. Public modeling metadata is Component ID, floor and construction-detail label; names remain optional/free. The Component's group-GUID-keyed internal record map on existing objects carries name, Scene references and direct children. Necessary stable material IDs, asset provenance and licensing fields are retained where real consumers need them. New assignments stop duplicating material name/category, UE slot and PBR channels onto object user strings: native materials hold the visual values. Existing unrelated user strings are preserved. Legacy key names remain documented for reading existing files, not as a list of required new stamps.

The existing construction catalog contains preliminary construction systems, not verified detail drawings. A human-readable construction label and a typed stable source reference are stored separately. A system ID is not relabeled as a certified detail ID. Floor values are supplied, not inferred from names or layer strings. Metadata updates do not erase unrelated user keys.

## Companion narration

`asset/history/Historyfiles/manifest.json` + `get_typology_narrative`: 18 typology narratives distilled from Ching/Jarzombek/Prakash, *A Global History of Architecture* — precedents, eras and urban roles, cross-linked to construction-system ids and page-referenced (`gha_ref`, matching [reference/gha_toc.txt](reference/gha_toc.txt)). NARRATION ONLY by contract: entries caption and contextualize designs (the perimeter block's Hof lineage, the ger behind every membrane roof); they never drive geometry — that is the construction library's job. Page-indexed TOCs of both volumes remain in [reference/](reference/) for deep reading.
