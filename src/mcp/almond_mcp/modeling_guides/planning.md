### Phase → Task → Step

**Phase는 작업 묶음, Task는 수행할 과업, Step은 과업 내부 단계**다. 현재 API에서 Task의 이름은 `Plan`이고 ID는 `plan_id`다. 진행 중이거나 중단된 작업을 조회해 이어서 사용할 수 있다. 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`다.

새 지시의 **도구 선택 전에** 현재 Task와의 관계를 판단한다. 알고 있는 Phase·Task·문서부터 사용하고, 빠진 정보만 작은 범위로 조회한다.

| Given: 지시의 맥락 | When: 판단·도구 선택 | Then: 필요한 행동·기록 |
| --- | --- | --- |
| 진행 중 Task의 보완 | 기존 목표·대상과 이어진다 | 같은 Task·Phase를 유지하고 필요한 실행을 한다. Step은 의미 있는 상태·대상·결과가 바뀔 때 기록한다. |
| 다른 과업으로 전환 | 기존 Task의 목표·대상이 달라진다 | 진행 중 Task는 필요하면 paused로 남기고 관련 Phase의 Task를 선택·재개하거나 만든다. 완료한 Task에 새 과업을 조용히 누적하지 않는다. |
| 맥락이 부족 | 현재 Task·대상·문서 중 무엇이 부족한지 먼저 정한다 | 알고 있는 ID는 단건 조회하고 모르면 status·Phase·Scene으로 목록을 좁힌다. 문서·경로 정보가 부족할 때만 project_info의 해당 sections를 읽고, 그래도 모호한 작업 대상은 사용자에게 확인한다. |
| 일회성 조회 | 이름·개수·상태만 묻는다 | 해당 요약 조회만 수행한다. 새 Phase·Task·Step을 만들거나 전체 계획을 다시 읽지 않는다. |

작업자료를 작성할 때는 선택한 Task에 `set_working_plan`을 적용한다. 실행·검수·중단·재개·완료의 의미 있는 상태를 해당 Step에 남기고, 도구 호출마다 기록을 늘리지 않는다. Task 완료는 요청한 실행과 필요한 검수가 끝난 뒤 판단한다.

Task의 상위 Phase는 `phase_id`로 지정한다. 관련성은 **Phase에는 Phase, Task에는 Task**를 기록하며, 같은 프로젝트의 다른 파일에 속한 항목도 참조할 수 있다. Task 간 참조는 `depends_on` 배열에 기록한다. Phase에는 전용 관계 필드가 없으므로 `description`에 관련 Phase ID를 적는다. 관계 기록은 참고용이며 실행 순서나 자동 완료를 강제하지 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| ----- | ----- | ----- |
| `list_phases` | 선택적 `limit` | 프로젝트의 Phase 목록 조회. |
| `get_phase` | `phase_id` | Phase 설명·파일명·소속 Task 수 조회. |
| `create_phase`  | `name`, 선택적 `description`, `file_name` | Phase 생성. |
| `update_phase`  | `phase_id`, 바꿀 `name`, `description`, `file_name` | Phase 정보 수정. |
| `list_plans` | 선택적 `phase_id`, `scene_id`, `status`, `limit` | 조건에 맞는 Task 목록 조회. |
| `get_plan`| `plan_id`, 선택적 `revision` | Task·Step의 대상·상태·기록 조회. |
| `create_plan`| `goal`, `scope`, 선택적 `phase_id`, `scene_ids`, `component_ids`, `depends_on` | Task와 기본 Step 생성. scope는 house, interior, structure, drawing, component. |
| `update_plan`| `plan_id`, 바꿀 목표·참조·상태·`artifact_refs`, `expected_revision` | Task 정보와 진행 기록 수정. |
| `update_step`| `plan_id`, `step_id`, `status`, 선택적 입출력 참조·대상, `expected_revision` | Step의 진행·중단·결과 기록. | 
| `resolve_targets`  | `plan_id`, 선택적 `step_id` | Task 또는 Step이 가리키는 ontological_component·문서·group 확인. |
| `list_plan_revisions` | `plan_id`, 선택적 `limit` | Task의 저장된 변경 이력 조회. |

Task의 `scene_ids`는 맥락, `component_ids`는 편집 대상이다. Step의 대상이 `null`이면 Task 대상을 상속하고 `[]`이면 대상이 없다. 수정에는 조회한 `revision`을 `expected_revision`으로 전달한다. 상태·참조 기록은 형상 실행과 별개다.

목록은 status·Phase·Scene과 작은 limit으로 좁힌다. 기본 조회는 요약이며, 실제 Step이 필요하면 `get_plan(..., field_groups=["steps"])`, 관계가 필요하면 `["references"]`, 산출물 위치가 필요하면 `["artifacts"]`를 추가한다. 지원 group은 도구별로 확인한다. 쓰기 응답의 handle·revision·개수·경고로 다음 행동을 정하고, 전체 기록을 즉시 다시 읽는 절차를 만들지 않는다.
