# Structural validation: Karamba workflow

`validate_structure`의 Karamba 경로(`engine="karamba"`)와 입력·반환 계약이다. 선형 frame은 기본 `engine="auto"`에서 [native solver](native-solver.md)를 사용한다.

## 해석 대상과 자산 하중

`validate_structure(guids, ...)` and `visualize_structure(guids, ...)` take explicit Rhino GUIDs, not Component IDs. `StructureModelExport.Handle` runs `ModelConditioner.Condition`: Points become support anchors, Curves become member axes, slender Extrusions and prismatic Breps can heuristically become members, and Mesh/surface/plate-like geometry becomes shells; other solids can be skipped with warnings. The native frame solver requires line members and rejects shells. The Karamba fallback is not automatically equivalent EN 1990 / Eurocode verification. Passing all architectural Component geometry directly as structural members would overstate both coverage and analysis validity.

Generated-asset gravity loads are **loads**, not automatically members. Preserve `AssetPlacementExport.Handle` (including old/new asset-ID tags), `retrieval_store.scene_instances`, `asset_loads.placements_from_scene`, `LoadTable.lookup`, `asset_loads.apply`, `structure_study.asset_catalogue`, `server._structural_loads_path`, `_asset_load_spec`, `get_asset_passport`, `structural-loads.json`, and generated manifest `category`, `spatial.support_plane`, `nominal_dimensions_mm`, and stable asset IDs. This existing path assigns estimated G/Q product/occupancy loads to frame members while reporting skipped ground-only, wall-mounted and structural elements. `test_asset_load_tools.py` and `test_asset_loads.py` cover these consumers. Asset conversion must not drop those identities/loads.

## Process

```
validate_structure(guids, structure_type, load_kn, material)
        │  MCP worker → document-bound Engine bridge (A–J: 5501–5510)
        ▼
RhinoAlmondBridge.StructuralValidator
  1. resolve the Rhino objects, extract member axis segments (unit-scaled to meters)
  2. detect span, type-aware (bridge >= 0.5.2; results carry span_basis):
       beam/frame → longest single member ("member") — members run support
                    to support, so a multi-bay set reads its bay span, not
                    the building length
       truss/shell/canopy/gridshell/membrane/highrise → overall bounding
                    extent ("extent") — segments are shorter than the span
                    they form
       undeterminable → 5.0 m ("default")
  3. choose an analysis pathway, in strict order of confidence:
       api        → Karamba 3.1 solve via KarambaAdapter (real FEA)   confidence: high
       template   → audited capsule .ghx (karamba_*_v1)               confidence: medium
                    karamba_frame_v1 and karamba_truss_v1 are harnessed and
                    audited (2026-08-29; the truss capsule runs
                    01_InputCurvesAsTruss.ghx, which node-merges input lines):
                    frames that make the native solver throw now get a real
                    Karamba solve through the template instead of falling to
                    rule_based. Bridge >= 0.5.3 unit-scales bound geometry to
                    the port's declared units and feeds the conditioned
                    support nodes (declared anchors, else lowest-Z) into
                    ALMOND_IN_SUPPORTS-style point ports.
       rule_based → heuristic UDL formulas                            confidence: low
  4. pass/fail checks (same criteria for every pathway)
  5. record the run in the state DB → export_structural_report renders Markdown
```

The response always names the pathway that actually ran (`results.analysis_method`) and prefixes the verdict, e.g. `[KARAMBA 3.1 API, HIGH CONFIDENCE]` vs `[RULE-BASED ESTIMATE, LOW CONFIDENCE]`. A rule-based answer is an estimate, not FEA — the label is the contract.

## Inputs

| Parameter | Default | Meaning |
| --- | --- | --- |
| `guids` | required | Rhino object GUIDs (curves/pipes; axes are extracted) |
| `structure_type` | `"beam"` | analysis template: beam, truss, shell, frame, canopy, gridshell, membrane, highrise |
| `load_kn` | `10.0` | applied load in kN (also drives the rule-based UDL `w = load/span`) |
| `material` | `"Steel"` | Steel (S235), S355, Concrete, Wood, Aluminium |

Supports: when no anchors are declared, the bridge pins the lowest-Z node(s) automatically and says so in `warnings`.

## Pass criteria

- **Deflection:** `max_deflection_mm ≤ span_mm / 250` (e.g. 24 mm for a 6 m span, 48 mm for 12 m).
- **Strength:** utilization < 1.0 against yield (S235: fy = 235 MPa).
- Rule-based pathway: mid-span UDL deflection `5wL⁴/384EI`, moment `wL²/8`, with load sharing across members.

## Karamba 로드와 확인

Karamba는 build-time reference 없이 `KarambaAdapter.cs`가 reflection으로 찾는다. native solver에는 필요하지 않다. 이미 로드된 `karambaCommon`을 우선 사용하고, 없으면 다음 순서로 `karambaCommon.dll`을 찾는다.

1. 코드의 `KarambaAdapter.OverridePluginPath`.
2. `ALMOND_KARAMBA_DIR` 환경변수.
3. `C:\Program Files\Rhino 8\Plug-ins` 아래 Karamba 또는 Karamba3D.
4. `%APPDATA%\McNeel\Rhinoceros\packages\8.0`의 Karamba 패키지.

찾지 못하면 경고와 함께 audited template, 이어서 rule-based 추정으로 내려간다. `analysis_method`와 실제 결과의 완전성을 확인하고 낮은 confidence를 FEA로 해석하지 않는다. 진단만을 위해 정상 설치를 덮어쓰거나 프로젝트 참조에 Karamba DLL을 추가하지 않는다.

## Rhino에서 검증

준비·빌드는 [AGENTS.md](../../AGENTS.md)를 따르고 일회용 문서에서 실행한다.

- 문서·단위·공차 정보가 필요하면 `project_info`의 document 항목에서 live 문서를 확인한다. 같은 확인을 위해 `get_rhino_context`를 추가 호출하지 않는다. 포트 충돌이면 해당 프로세스를 조사하고 강제 종료하지 않는다.
- 단순 beam의 치수·단위·하중·지점을 명시해 해석하고 `analysis_method`, 변위, 반력 평형, 부재 utilization과 경고를 확인한다.
- Karamba 미설치 조건에서도 명시적인 downgrade와 오류가 반환돼야 한다. capsule의 `audited` 상태는 실제 harness 검증 근거가 있어야 한다.
- `run_gh_definition`의 미등록 capsule·필수 입력 누락·잘못된 타입은 native 실행 전에 거절되어야 한다.
- timeout 뒤에는 완료 상태를 확인한다. 불확실한 geometry 수정을 재시도하지 않는다.
- 고정 조회·캡처와 표시 overlay, 일반 C# 수정의 부수효과를 구분한다. 실제 결과와 테스트 환경을 보고한다.

## Live structure view

`visualize_structure(guids=[...])` solves the frame (native solver by default, `engine="karamba"` for the Karamba route; see [native-solver.md](native-solver.md)) and draws it in every viewport through a display conduit (nothing is baked): ghosted undeformed axes, the exaggerated deformed shape coloured blue → red by displacement or utilization, supports, load arrows and a legend with max δ, the L/limit check and PASS/FAIL. `reanalyze=False` updates only the display (`scale`, `color_by`, `reveal`, `title`), so a staged construction sequence can be played back with `reveal` from 0 to 1, and `physics=False` draws the same members as plain geometry (physics off) for comparisons. `span_m` sets the reference span for the L/limit check when members are split at every node, `fixed_supports=False` pins the supports. `clear=True` removes the overlay. A 20-member frame solves in ~1.5 s (verified live on the Atelier-07 mezzanine: CHS 114.3x4 fails at 183 mm / utilization 3.59; CHS 193.7x8 passes at 20.9 mm / 0.66 against L/250 = 24.8 mm).

## Getting a report

Every recorded run can be exported as Markdown:

```text
validate_structure(guids=[...], structure_type="truss", load_kn=25)
export_structural_report()            # → %LOCALAPPDATA%\Almond\reports\structural-validation-<ts>.md
export_structural_report(path="C:\\project\\checks.md", limit=10)
```

The report contains the pathway explanation, a run table (span, deflection vs limit, utilization, reactions, member count, PASS/FAIL), per-run verdicts and warnings, and the interpretation notes above.
