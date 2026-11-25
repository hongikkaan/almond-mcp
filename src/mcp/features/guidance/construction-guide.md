# Construction-system guidance: real assemblies, not arbitrary members

Why Almond v0.6 adds a construction knowledge layer, where its numbers come from, and how it threads through `research_01-get_construction_guidance` tool, `analysis_02-validate_structure` tool, and `model_01-assign_material` tool.

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

- `structural_material` — `analysis_02-validate_structure` tool's material vocabulary (`Steel`, `Concrete`, `Wood`; `S355` is normalized to Steel).
- `structure_types` — which `analysis_02-validate_structure` tool templates the system maps to.
- `render_material_ids` — Materialfiles PBR ids, so the declared construction material is *visible in Rhino* and survives GLB/Datasmith export.
- `span_range_m` — real span range (for `category: wall`, `span_axis` is `"vertical"` and the range is unsupported height).
- `depth_rules` — `depth ≈ span / span_ratio` rules per element.
- `typical_spacing_m`, `elements` (role + guidance), `construction_notes`, `bci_ref`, `tags`.

The manifest also ships `reference` tables: occupancy live loads (kPa) and material densities (kg/m³) from BCI appendix A.06–A.07, for choosing `load_kn` inputs honestly.

Every parameter is itemized with its exact BCI section title and page in the generated **[construction spec register](../../profiles/construction_system/SPEC.md)** (`src/mcp/features/guidance/build_spec_register.py` regenerates it from the manifest).

## The workflow

```
research_01-get_construction_guidance tool(material="Wood", structure_type="beam", span_m=4.5)
        │  pick a system; size members from depth/spacing rules
        ▼
script_02-run_rhino tool          — generate members at real sections/spacings
        ▼
model_01-assign_material tool(guids, "wood-oak",
                structural_role="joist",
                construction_system="wood-joist-floor")
        │  applies material and the supported metadata described below
        ▼
analysis_02-validate_structure tool(guids, "beam", load_kn, "Wood")
        │  Karamba pathway as before, PLUS construction_check appended:
        │  which curated systems cover this structure_type/material,
        │  fits_span per system, suggested depths, and a warning when the
        │  span is outside every curated system's range
```

`construction_check.warnings` are also merged into the response's top-level `warnings`, so an implausible-as-drawn structure is flagged even when the solver passes it.

## Egress checking

`analysis_05-check_egress` tool turns the manifest's egress rules into one verdict pass: occupant load from plate area and occupancy, required exit count (tiers + the multi-story minimum of two), exit separation against the plate diagonal, total and per-exit egress widths, and optional measured travel distances and dead-end lengths. Each check names its requirement, the provided value, and its basis, so a failing layout says what to fix (add an exit, move a core, widen a stair). IBC-typical numeric factors are labeled as such and the response repeats the verify-governing-code note.

## 재료·구축 레이어 구현

재료 선택과 배정은 `model_04-list_materials` tool과 `model_01-assign_material` tool을 사용한다. 입력과 결과는 [모델링 도구 구현](../modeling/tools.py), 과업별 구축 상세화 판단은 [구축 지침 구현](tools.py)에 있다.

기본 재질은 처음 배정할 때 재질 레이어의 화면색과 출력색을 해당 재질의 `base_color`로 설정한다. 기본 재질은 선폭과 선종을 지정하지 않는다. 이전 문서에서 `ALMOND::<id>`라는 이름으로 등록한 렌더 재질도 해당 ID를 배정할 때 재사용한다. %%이거 뭔소린데? 이 기능은 왜 있는데? `almon::<id>`는 또 뭔데??%%

`model_01-assign_material` tool moves the selected objects to their material layer (default `M::<category>::<material_id>`) and assigns ByLayer when applying a render material. Only newly created layers receive the recipe’s layer settings. Metadata-only calls preserve object layers and render materials. Unspecified metadata is preserved. Material assignment and archive placement share one PBR implementation. Archive recipes with hash-suffixed names reuse only exact names and remain separate from legacy `ALMOND::<id>` materials. Use `model_01-assign_material` tool for material assignment in general modeling. Imports of existing generated assets restore the asset materials and use the specified placement layer. No operation guesses a layer from a material name or watches material-table events to move unrelated objects. Catalog reads and plugin startup create no modeling state.

MCP checks `modeling_materials=2` before these mutations and additionally `material_layer_assignment=1` before render assignment, rejecting an older loaded Bridge before dispatch. RHP source changes require a rebuilt Bridge and a new Rhino process. Rebuilding a file does not change a running process's assembly.

`modeling_policy.json` defines shared modeling metadata names. The material assignment tool owns its input validation and accepts floor, construction-detail label, typed construction reference and structural role; names remain optional/free. Component identities, group bindings, Scene context and semantic children live in the document-private registry described by the [Component contract](../components/SPEC.md), not in newly written object stamps. Necessary stable material IDs, asset provenance and licensing fields are retained where real consumers need them. New assignments stop duplicating material name/category, UE slot and PBR channels onto object user strings: native materials hold the visual values. Existing unrelated user strings are preserved. Legacy key names remain documented for reading existing files, not as a list of required new stamps.

The existing construction catalog contains preliminary construction systems, not verified detail drawings. A human-readable construction label and a typed stable source reference are stored separately. A system ID is not relabeled as a certified detail ID. Floor values are supplied, not inferred from names or layer strings. Metadata updates do not erase unrelated user keys.

## Companion narration

`asset/history/Historyfiles/manifest.json` + `research_02-get_typology_narrative` tool provide historical narratives, precedents and urban roles from Ching/Jarzombek/Prakash, *A Global History of Architecture*, linked to construction-system IDs and page references (`gha_ref`). They contain no project-specific dimensions, loads or structural capacity. Page-indexed TOCs remain in [reference/](../../profiles/construction_system/references) for deeper reading.
