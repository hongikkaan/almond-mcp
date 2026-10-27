### Phase → Task → Step

**Phase는 작업 묶음, Task는 수행할 과업, Step은 과업 내부 단계**다. 현재 API에서 Task의 이름은 `Plan`이고 ID는 `plan_id`다. 진행 중이거나 중단된 작업을 조회해 이어서 사용할 수 있다. 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`다.

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
| `resolve_targets`  | `plan_id`, 선택적 `step_id` | Task 또는 Step이 가리키는 ontological-component·문서·group 확인. |
| `list_plan_revisions` | `plan_id`, 선택적 `limit` | Task의 저장된 변경 이력 조회. |

Task의 `scene_ids`는 맥락, `component_ids`는 편집 대상이다. Step의 대상이 `null`이면 Task 대상을 상속하고 `[]`이면 대상이 없다. 수정에는 조회한 `revision`을 `expected_revision`으로 전달한다. 상태·참조 기록은 형상 실행과 별개다.
