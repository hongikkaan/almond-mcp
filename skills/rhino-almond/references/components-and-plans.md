# Scene·Component·계획

현재 문서는 `get_rhino_context`, 연결의 모델 경로는 `almond_project_info`로 확인한다. 아래는 MCP 기능명이며 COS에서는 `almond_cos_<기능명>`과 해당 `connection_id`를 사용한다.

## 관리 단위와 소유권

| 단위 | 실제 계약 |
|---|---|
| Scene | 공간의 의도·맥락. Component를 공유하고 일반 객체를 직접 연결할 수 있다. |
| Component | 명시적으로 등록한 Rhino group. **하나 이상의 기존 Scene에 속해야 한다.** 객체의 직접 소유자는 최대 하나이며 조상 group에는 하위 객체가 함께 포함된다. |
| 직접 Scene 객체 | asset instance나 Component 없이 연결한 top-level 객체. Scene의 실제 객체 목록은 직접 객체와 Component 멤버의 중복 없는 합집합이다. |
| Room·asset instance | 선택적인 기존 배치 검사 자료. Room AABB containment, asset AABB 충돌·배치·하중 계산에 사용하며 이전 데이터를 보존한다. |
| Phase | 여러 Plan을 조직하는 선택적인 부모. 기하·공간의 소유권을 뜻하지 않는다. |
| Plan·Step | 목표·의존성·상태·근거·명시적 Component 대상을 기록한다. 실제 모델링과 검증은 에이전트가 수행한다. |

객체 identity는 **저장된 모델 경로 + Rhino GUID**, Component의 group identity는 그 문서의 영속 group GUID다. 같은 이름이나 group index를 identity로 쓰지 않는다. 일반 group은 자동 등록되지 않는다. 자식은 하나의 부모만 가질 수 있고 순환은 금지된다. 부모 group이 자식의 객체까지 선택하더라도 객체의 `component_id`는 직접 소유 자식을 유지한다.

Component 등록 도구는 직접 소유 객체의 `component_id`와 기존 멤버의 내부 `component_record` 맵을 함께 관리한다. 맵의 group GUID별 record에는 이름·Scene·자식 연결이 저장되며 Rhino 객체 속성의 Undo/Redo와 파일 저장을 따른다. 자식 소유 객체가 조상 record도 보유할 수 있지만 직접 소유권은 하나다. 별도 anchor 형상을 만들지 않으며 group UserString이나 내부 record를 수동 복사해 등록을 대체하지 않는다.

block은 문서의 **top-level occurrence GUID**를 Component 멤버로 등록한다. 중첩 block도 바깥 occurrence를 한 객체로 취급하며 공유 definition 내부 객체를 occurrence별 소유 대상으로 등록하지 않는다. 중첩 내용·변환·블록 경로 조사는 `get_rhino_probe`의 [블록 조회](blocks-and-notes.md)를 사용한다. BlockEdit 임시 복제 객체와 reference 객체는 등록 대상에서 제외된다.

## Scene과 Component 호출

| 목적 | 공개 API와 핵심 인자 |
|---|---|
| Scene 생성·조회 | `create_design_scene(name, units="mm")`, `get_design_scene(scene_id)` |
| Component 등록·변경 | `upsert_design_component(expected_model_path, name, object_ids, scene_ids=None, component_id="", rhino_group_id="", child_component_ids=None)` |
| 캐시·live 조회 | `get_design_component(component_id, live=False)`, `list_design_components(expected_model_path="")` |
| live 관찰로 장부 갱신 | `sync_design_component(expected_model_path, component_id, rhino_group_id="")` |
| 등록 해제 | `remove_design_component(component_id)` |
| 직접 Scene 연결 | `register_scene_objects(scene_id, expected_model_path, object_ids, mode="add")`; mode는 `add`, `remove`, `replace` |
| Scene 객체 합집합 조회 | `get_scene_objects(scene_id)` |

`upsert_design_component`의 `object_ids`는 해당 Component가 **직접 소유할** top-level GUID 목록이다. `child_component_ids`는 직접 자식 목록이며 생략하면 유지, `[]`는 명시적 분리다. 자식이 존재하면 직접 객체는 없어도 된다. 부모 group의 물리 멤버는 직접 객체와 자손 객체의 합집합으로 정합된다. 일반 group을 채택하려면 정확한 직접·자손 멤버 구성이 맞아야 한다. 등록은 기하를 복제하지 않는다.

새 Component에는 `scene_ids`를 하나 이상 지정한다. 기존 Component에서 생략하면 기존 Scene 연결을 유지하고, 명시적인 `[]`는 거부된다. 직접 Scene 연결의 `remove`·`replace`는 Component 소속을 바꾸지 않는다. 부모가 없는 root Component는 자식을 포함한 상태로 등록 해제할 수 있다. 자식들의 소유권과 group을 보존하고 자식은 root가 되며 기존 부모 group은 일반 group으로 남는다. 자식 Component 자체의 해제는 먼저 부모에서 분리해야 한다. Plan·Step·Sheet 참조는 해제 전에 정리한다.

`get_design_component`, `list_design_components`, `get_scene_objects`는 저장된 관찰값이며 `live_verified=false`다. 등록·sync 성공 응답의 `live_verified=true`는 그 호출에서 확인한 snapshot을 뜻한다. 이후 Rhino의 수동 편집·Undo/Redo가 DB에 자동 반영되지는 않는다.

수동 편집이나 Undo/Redo 이후 `get_design_component(live=True)`로 현재 group과 `pending_objects`를 읽는다. TextDot 등 소유자가 없는 새 그룹 멤버는 읽기 전용 검사에서 후보로만 보인다. 명시적 `sync_design_component`는 **모호하지 않은** 후보를 가장 깊은 등록 group의 직접 소유 객체로 채택하고 조상 group 멤버십을 한 Undo에 정합시키며 DB snapshot을 갱신한다. 이미 정합된 경우 Rhino를 수정하지 않는다. 복사·외부 소유 stamp·불명확한 그룹 중첩은 명시적으로 수리해야 한다. 오류·타임아웃 뒤 원래 수정을 자동 재실행하지 않는다. [네이티브 계층 계약](../../../docs/modeling/component-system.md#native-component-hierarchy)도 확인하라.

`validate_scene_layout`은 기존 asset instance 검사다. `passed_scope="legacy_asset_instances"`, `coverage.registered_object_collisions_checked=false`와 실제 검사 범위를 읽는다. Room이 지정된 instance의 containment와 AABB 충돌 통과를 Component·직접 Scene 객체의 실제 접합·관입·공간 사용성 판정으로 확대하지 않는다.

## Phase·Plan·Step 호출

| 목적 | 공개 API와 핵심 인자 |
|---|---|
| Phase | `create_generation_phase(name, description="")`, `get_generation_phase(phase_id)`, `list_generation_phases(limit=50)`, `update_generation_phase(phase_id, name=None, description=None)` |
| Plan 생성 | `create_generation_plan(goal, scope="house", scene_id="", phase_id="", scene_ids=None, component_ids=None)` |
| Plan 조회·검색 | `get_generation_plan(plan_id, revision=None)`, `list_generation_plans(phase_id="", scene_id="", status="", limit=50)` |
| Plan 변경 | `update_generation_plan(plan_id, goal=None, phase_id=None, scene_ids=None, component_ids=None, expected_revision=None)` |
| Step 갱신 | `update_generation_step(plan_id, step_id, status, input_refs=None, output_refs=None, component_ids=None, expected_revision=None)` |
| 대상 해석 | `resolve_generation_targets(plan_id, step_id="")` |
| revision 목록 | `list_generation_plan_revisions(plan_id, limit=50)` |

지원 scope는 `house`, `interior`, `structure`, `drawing`, `component`다. Component 과업에는 `scope="component"`로 `inspect_context → design → model → validate` 단계를 만든다. 처음 등록할 형상을 계획한다면 Component 참조 없이 시작한 뒤, 실제 등록된 ID를 `update_generation_plan`으로 연결할 수 있다.

Plan의 `scene_ids`는 맥락이고 `component_ids`는 명시적인 대상이다. 참조하는 Component가 Plan의 맥락 Scene에 속해야 하는 조건은 없다. Scene 참조만으로 그 안의 모든 객체를 편집 대상으로 삼지 않는다. 호환용 단일 `scene_id`를 함께 전달하면 `scene_ids`의 첫 항목과 일치해야 한다.

대상은 `resolve_generation_targets`로 확인한다. **응답의** Step `component_ids=null`은 Plan 대상을 상속하고, 명시적인 `[]`는 대상 없음이며, 목록은 그 Step의 별도 대상이다. 변경 호출에서 `component_ids`를 생략하거나 `null`로 보내면 기존 설정을 유지한다. 현재 API에는 이미 지정한 Step override를 다시 상속 상태로 바꾸는 별도 인자가 없다. Plan/Step 대상 조회는 등록된 문서·group 핸들을 반환하며 `live_verified=false`다. 실제 문서와 현재 사용자 범위를 대조한 뒤 작업한다.

Step 상태는 `pending`, `running`, `completed`, `failed`, `blocked`다. `running`·`completed`는 모든 선행 단계가 완료돼야 한다. 후속 단계가 실행 중이거나 완료 상태이면 선행 단계를 뒤로 돌릴 수 없으므로 실제 재작업 순서에 맞춰 후속 상태부터 갱신한다. `input_refs`·`output_refs`에는 관련 핸들과 실제 검증 근거를 기록한다. 상태 변경 자체가 형상을 생성하거나 검증을 수행하지 않는다.

## revision과 변경 의미

Plan metadata·참조·Step 상태에 실제 변경이 생기면 전체 계획 snapshot을 immutable revision으로 저장한다. 같은 값으로 갱신하면 revision이 늘지 않는다. 기존 DB의 현재 계획은 migration 시 revision 0 baseline으로 남고, 존재하지 않았던 과거 기록을 만들지 않는다.

수정 전에 읽은 Plan의 `revision`을 `expected_revision`으로 전달해 다른 갱신을 덮어쓰지 않게 한다. 불일치하면 최신 Plan을 다시 읽고 변경 내용을 재검토한다. `get_generation_plan(plan_id, revision=N)`은 그 revision만 조회하며 없으면 오류다. 저장된 snapshot은 계획 metadata·Step 상태·참조 핸들이므로 Rhino 기하를 복원하는 백업으로 쓰지 않는다. Phase 이름·설명 편집은 Phase 조직 정보를 갱신한다.

변경 API의 생략값은 기존 값을 유지한다. Plan의 `scene_ids=[]`·`component_ids=[]`는 참조를 비우며, `phase_id=""`는 Phase에서 분리한다. 이는 **Component 자체에는 최소 한 Scene이 필요한 규칙**과 구분한다. 목록 API의 `limit`은 1–500이며 `total`·`truncated`를 확인한다.
