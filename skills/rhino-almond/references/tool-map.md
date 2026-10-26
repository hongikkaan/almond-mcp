# MCP 도구 선택

## Almond MCP 도구 선택

현재 연결에 노출된 도구 설명과 인자를 확인해 **이번 과업에 필요한 도구만** 고른다. 아래 묶음은 순차 작업 절차가 아니다. Sheet 관리, 발행, 형상 편집 등은 각각 독립적으로 시작할 수 있다. CLI와 COS는 같은 도구 이름을 사용하며, COS 연결별 호출에는 `connection_id`를 전달한다.

**영향 표기:** `조회`는 Rhino·Almond 기록을 바꾸지 않는다. `화면`은 Rhino의 선택·가시성·뷰 또는 일시적 표시를 바꾼다. `Rhino`는 활성 문서의 형상·속성·레이어·Layout 등을 바꾼다. `DB`는 `.almond` 기록을 바꾼다. `파일`은 산출물이나 자산 라이브러리에 쓴다. `외부`는 다른 서비스에 발행한다. 한 도구에 여러 효과가 있을 수 있으므로 실제 설명과 응답을 대조한다.

## 공통 확인과 재사용 조회

| 판단할 내용 | 도구 | 영향과 사용 기준 |
|---|---|---|
| 연결된 모델과 출력 위치 | `project_info` | 조회. 첫 Rhino 동작 전에 binding·`artifact_dir`를 확인한다. 이 응답만으로 활성 문서를 확인했다고 보지 않는다. |
| 실제 문서·선택·현재 화면 | `get_rhino_context`, `get_rhino_viewport_image` | 조회. 문서 경로·단위·공차·선택과 현재 뷰를 대조한다. 화면 캡처는 카메라·clipping을 설정하거나 형상 적합성을 증명하지 않는다. |
| Phase·Plan·Step 기록 | `list_generation_phases`, `get_generation_phase`, `create_generation_phase`, `update_generation_phase`, `list_generation_plans`, `get_generation_plan`, `create_generation_plan`, `update_generation_plan`, `update_generation_step`, `list_generation_plan_revisions`, `resolve_generation_targets` | 목록·상세·대상 해석은 조회, 생성·갱신은 DB. 독립 Almond 과업의 Phase·Plan 정책과 Step 증거는 [계획 계약](components-and-plans.md)을 따른다. Scene 참조만으로 편집 대상을 늘리지 않는다. |
| 현재 의미 단위와 객체 연결 | `get_design_scene`, `list_design_components`, `get_design_component`, `get_scene_objects` | 조회. 저장된 결과와 `live=True` 관찰을 구분한다. 알고 있는 Scene ID의 상세 조회는 가능하지만 Scene 전체 목록 도구는 없다. |
| 재료·구축 지침·검색 상태 | `list_materials`, `get_modeling_policy`, `get_construction_guidance`, `get_retrieval_status` | 조회. 재료 ID나 정책·구축 기준이 필요한 과업에서 사용한다. 목록을 Rhino 재료 등록이나 형상 검증으로 간주하지 않는다. |
| 설계 근거와 자산 후보 | `get_typology_narrative`, `search_detail_sources`, `search_asset_repository` | 조회. typology는 서술용, 상세 출처 검색은 후보 디렉터리, 자산 검색은 사용 가능성 판단의 출발점이다. |

## 과업별로 선택하는 도구

| 과업 | 도구 | 영향과 핵심 경계 |
|---|---|---|
| 실제 형상·블록·접합 관찰 | `get_rhino_probe`, `get_component_intersections` | 조회. 고정 probe의 문서 경로·단위·표본·`unknown`·잘림과 교차 검사의 `complete`를 확인한다. [Probe](probe-tools.md)·[접합](joint-probes.md). |
| Rhino 대상에 집중 | `focus_components` | 화면. 선택·격리·확대가 바뀐다. 불명확한 실행을 자동 재시도하지 않는다. |
| Scene·Component 등록 | `create_design_scene`, `upsert_design_component`, `sync_design_component`, `remove_design_component`, `register_scene_objects` | DB 및 일부 Rhino group·객체 속성. 의미 단위와 직접 소유 객체를 구분하고 live 소속을 확인한다. [구성 기준](components-and-plans.md). |
| 기존 Room·asset instance 배치 | `upsert_design_room`, `remove_design_room`, `register_scene_instance`, `remove_scene_instance`, `validate_scene_layout` | 등록·해제는 DB, 검사는 조회. `validate_scene_layout`은 legacy asset-instance AABB 범위이며 Component 형상 충돌 검사가 아니다. |
| 형상 생성·변경·계산 | `execute_rhino_script` | Rhino 변경 가능. 조회용 C#도 Undo 범위에서 실행되고 `List<Guid>` 반환은 자동 치수를 만들 수 있다. 작은 계산값은 `result`로 회수한다. [실행 계약](probe-tools.md). |
| 재료·구축 레이어 준비 및 할당 | `setup_modeling`, `assign_material` | Rhino 재료·레이어 또는 객체 속성 변경. 두 `setup_modeling` operation을 구분하고, `assign_material`은 기존 객체 레이어를 보존한다. [재료 계약](modeling-materials.md). |
| 구조·피난 검토 | `list_design_codes`, `validate_structure`, `visualize_structure`, `check_egress`, `export_structural_report` | 코드 목록·피난 계산은 조회, 구조 검증은 DB 이력, 시각화는 화면, 보고서는 파일. 해석 방법·신뢰도·하중과 입력 가정을 함께 읽는다. `rule_based/low`는 FEA가 아니다. |
| Grasshopper 정의 확인·실행 | `list_library`, `get_logic_by_id`, `list_capsules`, `run_gh_definition` | 목록·원형 조회는 조회. 실행은 정의에 따라 Rhino에 bake할 수 있다. `audited=true`와 정확한 입출력 port 계약을 확인한다. |
| 3DM·GLB 도면 자산 | `list_drawing_assets`, `search_drawing_assets`, `get_drawing_asset`, `register_drawing_asset`, `get_asset_drawing`, `generate_asset_drawing_views`, `audit_asset_drawing`, `place_drawing_asset` | 목록·상세·감사는 조회, 등록·도면 생성은 파일, 배치는 Rhino. 준비된 3DM과 custom GLB 경로·단위·축을 구분한다. [자산 계약](drawing-assets-and-sheets.md). |
| 다이어그램 자산 | `list_diagram_assets`, `search_diagram_assets`, `get_diagram_asset`, `place_diagram_asset` | 탐색은 조회, 배치는 Rhino. 실제 파일 가용성과 크기·배치 조건을 확인한다. |
| Rhino Sheet·Layout | `list_drawing_sheets`, `get_drawing_sheet`, `upsert_drawing_sheet`, `sync_drawing_sheet`, `remove_drawing_sheet` | 조회, Rhino Layout·DB 생성/변경, DB 정합/해제를 구분한다. 목록은 Almond 등록 Sheet만 포함한다. 기존 PageSpace 도면 인벤토리를 만들기 위해 `upsert`하지 않는다. [Sheet 계약](drawing-assets-and-sheets.md). |
| 도면 표현 | `list_drawing_recipes`, `get_drawing_recipe`, `apply_drawing_style`, `import_drawing_hatch_patterns` | recipe 조회와 Rhino 레이어·해치 변경을 구분한다. |
| 카메라 경로 산출물 | `capture_conditioning_pass` | 파일 및 일시적 화면 변경. 프레임·깊이·카메라 기록을 확인하고 카메라 복원은 best effort로 본다. |
| 교환·외부 발행 | `export_asset_contract`, `import_asset_contract`, `get_blender_helper_script`, `publish_to_chestnut`, `publish_objects_to_chestnut` | helper script 조회, 파일 export, Rhino import, Chestnut 외부 발행을 구분한다. 발행·가져오기 대상과 결과를 명시적으로 확인한다. |

현재 화면 캡처는 Named View나 절단면을 준비하지 않는다. 필요한 검수 조건을 준비한 뒤 실제 이미지를 검토한다. PageSpace 캡처와 ModelSpace/Detail을 반환 metadata로 구분한다. 뷰 부재·캡처 실패를 이전 파일로 대체하지 않는다.

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
