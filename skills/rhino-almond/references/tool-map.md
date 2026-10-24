# MCP 도구 선택

## Almond MCP 도구 선택

현재 연결에 노출된 도구 설명과 인자를 확인한 뒤 아래에서 목적에 맞는 기능을 골라라. 필요한 기능의 실제 지원 범위와 쓰기 대상을 확인하라. 도구를 많이 호출하는 것 자체를 목표로 삼지 마라. 아래는 MCP의 기능명이며 CLI의 서버 접두사는 별도다. COS에서는 `almond_project_info`가 `almond_cos_project_info`, 나머지 도구는 `almond_cos_<기능명>`으로 노출된다. `almond_cos_list_connections` → `almond_cos_connect`에서 얻은 `connection_id`를 연결별 호출에 전달하라.

| 현재 목적 | 우선 확인할 도구 | 활용·확인 사항 |
|---|---|---|
| 연결·자료 상태 파악 | `almond_project_info`, `get_retrieval_status` | 연결에 묶인 모델 경로와 실제 artifact_dir를 확인하라. `project_info`는 실제 활성 문서나 형상을 조회하지 않으며 `live_document_checked=false` 자체는 오류가 아니다. 검색 인덱스 상태와 실제 Rhino 형상 상태를 구분하라. |
| 실제 문서·선택·뷰 조회 | `get_rhino_context` | 편집 전 문서 identity·단위·공차·선택·현재 뷰를 조회하라. `selection_limit`은 정수 0–200, 기본 50이다. `selection.total/returned/truncated`, `warnings`와 `null`을 읽고 누락을 빈 상태로 간주하지 마라. 레이어·형상·Undo를 만들지 않는다. |
| 블록·지형·접합부 고정 조회 | `get_rhino_probe` | `probe`, `options`, `expected_model_path`로 아래 다섯 helper를 호출한다. 문서 경로를 검사하고 Undo·레이어·선택·뷰를 변경하지 않는다. 요청·응답은 각각 256 KiB 한도다. [고정 probe 계약](probe-tools.md)을 확인하라. |
| 현재 화면 확인 | `get_rhino_viewport_image` | JPEG ImageContent와 문서·뷰 metadata를 같은 응답에서 읽어라. `max_width/max_height`는 각각 정수 64–2048, 기본 1280/960이며 비율 유지·확대 없음·JPEG 4 MiB 한도다. 현재 카메라·Named View·display mode·clipping·선택을 바꾸지 않는다. |
| 형상 편집·계산값 회수 | `execute_rhino_script` | 전용 도구가 다루지 않는 형상과 계산에 사용하라. 작은 JSON-safe 반환은 `result`로 직접 받고 `result_error`를 실행 실패와 구분하라. 자동 레이어·Undo 등 부수 효과가 있으므로 읽기 전용 조회로 간주하지 마라. [실행·결과 계약](probe-tools.md)을 확인하라. |
| 과업·진행 상태 관리 | `list_generation_phases`, `create_generation_phase`, `list_generation_plans`, `create_generation_plan`, `get_generation_plan`, `update_generation_plan`, `update_generation_step`, `list_generation_plan_revisions` | **Phase ≥1·모든 Plan의 Phase 연결·새 독립 과업의 Plan 생성 및 사용 필수.** 기존 Phase/동일 작업 Plan은 재사용한다. `scope="component"`는 조사→설계→모델링→검증 단계다. revision과 의존성 확인 후 `expected_revision`으로 증거를 갱신하라. [계획 계약](components-and-plans.md). |
| 계획의 편집 대상 확인 | `resolve_generation_targets` | Step에 명시한 Component, 없으면 Plan의 Component를 반환한다. 명시적인 `[]`는 대상 없음이며 Scene 참조가 편집 대상을 늘리지 않는다. 결과는 `live_verified=false`이므로 현재 문서·소속·사용자 범위를 대조하라. |
| 검색·설계 근거 찾기 | `get_construction_guidance`, `get_typology_narrative`, `search_detail_sources`, `search_asset_repository` | 필요한 항목을 검색하고 출처·적용 조건을 확인하라. 검색된 자료나 자동 추천을 곧바로 설계 판정으로 삼지 마라. |
| 자산 선택·배치 | `list/search_drawing_assets`, `list/search_diagram_assets`, `get_drawing_asset`, `get_diagram_asset`, `place_drawing_asset`, `place_diagram_asset` | 목록 → 후보 상세 → 파일 가용성·단위·원점·배치 조건 → 배치 결과를 확인하라. 준비된 3DM과 파생 도면은 같은 asset ID를 사용한다. [자산·Sheet 계약](drawing-assets-and-sheets.md)을 확인하라. |
| 준비된 3DM 등록·파생 도면 | `register_drawing_asset`, `get_asset_drawing`, `audit_asset_drawing` | 외부 converter에서 검토·정리한 mm/Z-up/바닥 중심 원점 3DM을 등록한다. 등록은 방향·재료의 시각적 적합성을 판정하지 않는다. 동일 ID 갱신은 `replace_existing=true`로 명시하며 이전 파일과 manifest 백업을 보존한다. |
| Scene·Component 관리 | `create_design_scene`, `get_design_scene`, `upsert_design_component`, `get_design_component`, `list_design_components`, `sync_design_component`, `remove_design_component` | **Scene은 파일 아닌 공간·상황 단위.** Component는 하나 이상의 Scene과 독립 Rhino group을 가지며 직접 객체 소유자는 하나다. `object_ids`는 직접 소유, `child_component_ids`는 직접 자식; 부모 group은 하위 객체도 선택한다. 수동 변경 후 live 검사·명시적 sync. [계약](components-and-plans.md). |
| Scene 직접 객체·기존 배치 검사 | `register_scene_objects`, `get_scene_objects`, `upsert_design_room`, `register_scene_instance`, `validate_scene_layout` | 일반 객체를 Scene에 직접 연결할 수 있다. Room/asset instance는 선택적인 기존 배치·containment·하중 용도다. `validate_scene_layout`의 `passed_scope`·`coverage`를 읽고 legacy asset AABB 검사를 Component·일반 객체의 실제 충돌 검사로 확대하지 마라. |
| Component 교차·대상 집중 | `get_component_intersections`, `focus_components` | 중첩 멤버를 중복 제거해 후보 쌍을 검사하거나 isolate·ZoomSelected한다. **한 개 이상의 Component를 주어도 내부 소속 객체끼리의 쌍이 포함될 수 있다.** block·주석·상한·`unknown`·`complete=false`는 무충돌이 아니다. |
| 신규 Layout·Sheet 등록 | `upsert_drawing_sheet`, `get_drawing_sheet`, `list_drawing_sheets`, `sync_drawing_sheet`, `remove_drawing_sheet` | **등록한 Sheet만 조회. 기존 PageSpace Layout 전체 메타데이터 인벤토리 아님.** `upsert`는 Layout+detail 생성/변경이므로 기존 도면 목록 요구에는 사용하지 않는다. 등록 해제는 Layout/도면 형상을 남긴다. [범위](drawing-assets-and-sheets.md). |
| 구조 검토·시각화 | `list_design_codes`, `validate_structure`, `visualize_structure`, `export_structural_report` | 부재·지지점·단위·하중·접합 가정을 확인하라. 반환된 해석 방식과 신뢰도, 지원 범위와 누락 조건을 읽어라. 전체 모델의 검증 통과가 개별 접합부의 제작 가능성을 뜻하지는 않는다. |
| GH 정의 실행 | `list_library`, `get_logic_by_id`, `list_capsules`, `run_gh_definition` | 먼저 실제 라이브러리·캡슐과 입출력 계약을 조회하라. 필요한 기능과 맞는 정의가 있으면 사용하고 출력 핸들을 확인하라. |
| 재질 등록·구축 레이어 준비 | `list_materials`, `get_construction_guidance`, `get_modeling_policy`, `setup_modeling` | `operation="materials"`는 라이브러리 재질을 등록하고 `operation="layers"`는 구축 시스템별 `M::category::system.name::element.role` 레이어를 준비한다. 재질과 레이어의 준비는 별도 작업이며 객체를 이동하지 않는다. 기존 재질 덮어쓰기 선택과 [계약](modeling-materials.md)을 확인하라. |
| 재질·표현·내보내기 | `assign_material`, `list/get_drawing_recipe`, `apply_drawing_style`, `capture_conditioning_pass`, `export/import_asset_contract` | `assign_material`은 명시한 객체의 기존 레이어를 보존하고 재질·메타데이터만 적용한다. Bridge `modeling_materials=2`와 [재료·메타데이터 계약](modeling-materials.md)을 확인하라. 파일 생성·내보내기 뒤 실제 파일과 결과를 확인하라. |

`list/search_*`와 `get_*`는 위 표의 계열 표기다. 그대로 호출할 함수명이 아니므로 현재 노출된 정확한 이름과 schema를 사용하라.

현재 화면 캡처는 Named View나 절단면을 준비하지 않는다. 필요한 검수 조건을 주 에이전트가 구성한 뒤 캡처하고 실제 이미지를 검토하라. 페이지 뷰의 이미지는 전체 페이지이며 `viewport`는 MainViewport를 설명한다. `capture_scope`, `active_viewport_id`, `warnings`로 활성 detail과 구분하라. 뷰 부재·캡처 실패는 이미지 없는 오류이며 이전 파일로 대신하지 않는다. 카메라 경로·복수 패스가 필요하면 기존 `capture_conditioning_pass`를 사용하되 카메라 복원은 best effort다.

#### 등록과 검증의 대응 확인

- 일반 Rhino group은 `upsert_design_component`로 등록해야 Component가 된다. Component는 하나 이상의 Scene을 공유할 수 있고 객체의 명시적 소유 Component는 최대 하나다. group 이름·UserString만으로 등록을 가정하지 마라. block occurrence는 멤버가 될 수 있으며 공유 definition 내부 객체는 occurrence별 소유 대상으로 등록하지 않는다.
- `get_design_component(live=False)`, `get_scene_objects`, `resolve_generation_targets`는 캐시 조회다. `get_design_component(live=True)`는 Rhino group을 수정하지 않고 현재 소속·미등록 TextDot 후보를 관찰한다. `sync_design_component`는 명시적으로 호출할 때만 단일 Undo 안에서 모호하지 않은 미등록 멤버를 채택하고 조상 group을 정합시킨다. 복사·외부 소유 stamp·불명확한 regroup은 자동 수리하지 않으며 타임아웃 뒤 변경을 자동 재실행하지 마라.
- 실제 대상 수·문서 경로+GUID·블록 경로와 등록 범위를 대응시켜라. 직접 Scene 객체와 Component 멤버의 합집합은 중복 제거되지만 실제 기하를 새로 생성하거나 검증하지 않는다. 기존 Room과 asset instance는 필요할 때 유지하며 `rhino_guid` 기록만으로 자동 동기화나 live 존재 확인을 가정하지 마라.
- `validate_scene_layout`의 `passed_scope="legacy_asset_instances"`와 `coverage`를 확인하라. Room이 지정된 asset instance의 containment와 AABB 충돌 결과는 등록된 Component·일반 객체의 접합·관입 판정까지 포함하지 않는다. 실제와 다른 bounds로 통과시키지 말고, 형상·배치·블록 정의 변경 뒤 영향받은 등록과 필요한 실제 기하 검사를 갱신하라.
- `passed`와 함께 해석 방식·신뢰도·누락 하중/부재·후보 수 상한을 읽어라. `rule_based`/`low` 또는 `indicative`/`passed=null`은 구조 적합성의 증명이 아니다. `unknown`·`not_measured`·`truncated`·검사 생략을 0이나 통과로 바꾸지 마라. AABB 후보는 필요한 실제 객체쌍과 사용 조건으로 좁혀 확인하고, 해결하지 못한 후보는 남겨라.

계획은 [작업 지침](workflow.md)의 완료 기준과 실제 단계·의존성을 연결하라. 하위 계획 ID나 설명상의 관계가 자동 실행·자동 완료를 보장한다고 가정하지 마라.

전용 도구로 해결되지 않는 실제 형상 조회에는 [C# 실행과 결과 회수](probe-tools.md)을 사용하라. 새 형상 생성·설계 변경은 과업의 요구와 현재 모델에 맞춰 수행하라. 보조 코드의 선택 때문에 구조 형식이나 모델 관리 단위를 고정하지 마라.

### Rhino 코드 도구

아래 표에서 필요한 기능을 고른 뒤 해당 문서에서 입출력을 확인하고 `get_rhino_probe`로 호출하라. 구현은 `src/rhp/RhinoAlmondBridge/Probes`의 제품 코드이며 별도 스킬 스크립트를 조립하지 않는다.

| 필요한 기능 | 활용 | 사용법·코드 |
|---|---|---|
| 블록과 주석 | 중첩 블록 outline, definition/instance 이름, TextDot 연결과 BlockEditNew 대상 확인 | [사용법](blocks-and-notes.md) |
| 지형 단면 | Brep/Mesh/Extrusion을 지정한 X/Y/Z 위치에서 잘라 단면의 닫힘·길이·범위를 관찰 | [사용법](terrain-probes.md) |
| 수직선 검사 | 지정한 XY에서 교차 높이·채움 구간·객체 사이 표본 관입을 확인 | [사용법](terrain-probes.md) |
| 접합부 쌍 검사 | Brep/Extrusion 쌍의 실제 교차 체적, bbox 거리 하한, 선택적 Join/Union 결과를 관찰 | [사용법](joint-probes.md) |
| 호출과 결과 회수 | 고정 probe를 호출하고 같은 응답의 문서 identity·측정값·누락을 확인 | [사용법](probe-tools.md) |
