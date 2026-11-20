# 구축 상세

재료·부재·경간·간격을 정할 때 아래의 구축 시스템 설명을 참고한다. 원문 예시의 도구명과 메타데이터 키는 당시 표기다. 현재 호출명과 입력은 `tools/list`에서 확인한다.

Almond MCP 원문은 `d2de2db9fb39e3b549d02b2f7ea2115811eb3bd2:docs/construction-guidance.md`의 제목부터 `The workflow` 절까지다.

````markdown
# Construction-system guidance: real assemblies, not arbitrary members

Why Almond v0.6 adds a construction knowledge layer, where its numbers come
from, and how it threads through `get_construction_guidance`,
`validate_structure`, and `assign_material`.

## The problem it solves

Karamba validation (see [structural-validation.md](structural-validation.md))
tells you whether a set of members *solves* — deflection, utilization,
reactions. It cannot tell you whether the members correspond to anything a
builder would recognize: a 15 m sawn-lumber joist can pass FEA if you make it
deep enough, but it is not a thing that exists. The construction library closes
that gap with curated knowledge of how structural systems are actually formed:
which material, which element roles, what spans and spacings are real, and
what member depth a given span implies.

## Source and honesty

Parameters are distilled and paraphrased from **Francis D.K. Ching,
*Building Construction Illustrated*, 4th ed. (Wiley, 2014)** — each system
entry carries `bci_ref` section numbers. They are the book's preliminary-sizing
rules of thumb (e.g. steel beam depth ≈ span/20, wood joist depth ≈ span/16,
open-web joist span ≤ 24 × depth), intended for design plausibility, **not** a
substitute for engineering analysis or the governing code. The manifest states
this in its `source` field and every `construction_check` repeats it.

## The library

`Constructionfiles/manifest.json` — 23 systems across four categories:

| Category | Systems |
| --- | --- |
| floor | wood joist, wood I-joist/trussed joist, plank-and-beam, steel wide-flange, open-web steel joist, light-gauge steel joist, one-way slab, one-way joist (pan) slab, flat plate/flat slab, waffle slab, precast hollow-core, precast tees |
| wall | wood platform framing, cast-in-place bearing wall, concrete column grid, reinforced CMU, steel column frame |
| roof | steel rigid frame, steel trusses, space frame, wood rafters, wood trusses |
| foundation | concrete shallow foundation (spread footings / walls / slab on grade) |

Each system entry:

- `structural_material` — `validate_structure`'s material vocabulary
  (`Steel`, `Concrete`, `Wood`; `S355` is normalized to Steel).
- `structure_types` — which `validate_structure` templates the system maps to.
- `render_material_ids` — Materialfiles PBR ids, so the declared construction
  material is *visible in Rhino* and survives GLB/Datasmith export.
- `span_range_m` — real span range (for `category: wall`, `span_axis` is
  `"vertical"` and the range is unsupported height).
- `depth_rules` — `depth ≈ span / span_ratio` rules per element.
- `typical_spacing_m`, `elements` (role + guidance), `construction_notes`,
  `bci_ref`, `tags`.

The manifest also ships `reference` tables: occupancy live loads (kPa) and
material densities (kg/m³) from BCI appendix A.06–A.07, for choosing
`load_kn` inputs honestly.

Every parameter is itemized with its exact BCI section title and page in
the generated **[construction spec register](construction-spec-register.md)**
(`tools/build_spec_register.py` regenerates it from the manifest).

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
        │  stamps almond:structural_role / almond:construction_system /
        │  almond:structural_material user text on the objects
        ▼
validate_structure(guids, "beam", load_kn, "Wood")
        │  Karamba pathway as before, PLUS construction_check appended:
        │  which curated systems cover this structure_type/material,
        │  fits_span per system, suggested depths, and a warning when the
        │  span is outside every curated system's range
```

`construction_check.warnings` are also merged into the response's top-level
`warnings`, so an implausible-as-drawn structure is flagged even when the
solver passes it.

````
