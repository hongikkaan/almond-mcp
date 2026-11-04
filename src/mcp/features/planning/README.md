# Phase·Plan·Step 도구 계약

기본 조회 순서는 `list_phases` → `list_plans` → `get_phase_plan_step`이다. MCP 호출 이름은 `get_phase_plan_step`, 표시 제목(title)은 `get_phase·plan·step`이다. 표시 제목을 지원하지 않는 클라이언트에서는 호출 이름이 보일 수 있다.

이 모듈의 조회에는 `include_ids`가 없고 ID를 항상 출력한다. 작업 상태값은 `pending | running | paused | completed | failed | blocked`다. 아래 `?`는 선택 입력이다. 통합 상세 응답의 최상위 `status`는 선택한 항목의 작업 상태다. 목록·생성 성공은 `status: success`, 오류는 `status: error`와 message를 사용한다. 수정 응답의 적용 여부와 부분 성공은 아래 계약을 따른다.

## 통합 상세 조회

```text
get_phase_plan_step Input
  phase_id?: string          기본 ""
  plan_id?: string           기본 ""
  step_id?: string           기본 ""
  revision?: integer | null  기본 null, 0 이상인 저장된 Plan revision
  include_holons?: boolean  기본 false
```

`phase_id`와 `plan_id` 중 정확히 하나가 필요하다. `step_id`는 `plan_id`와 함께 사용한다. `revision`은 Plan 또는 Step의 과거 상태 조회에 사용한다. `include_holons=true`는 Plan 상세에서만 허용한다. Phase에 revision을 넣거나 Step에 Component를 요청하면 오류다. `field_groups`와 `audit` 옵션은 없다.

```text
Output — phase_id로 조회
  id: string                Phase ID
  type: "phase"
  status: workflow status
  phase:
    name: string
    description: string
    file_name: string       미지정이면 ""
    project_file_id: string | null
    depends_on: string[]    Phase ID만
    plan_titles: string[]   소속 Plan 제목, 중복 제목 허용

Output — plan_id로 조회
  id: string                Plan ID
  type: "plan"
  status: workflow status
  next_step: string          Step 상세 조회와 실제 작업 선택 안내
  plan:
    title: string
    goal: string
    scope: string
    revision: integer
    phase: null | object
      phase_id: string
      name: string | null   과거 snapshot에 이름이 없으면 null
    depends_on: string[]    Plan ID만
    scene_ids: string[]
    artifact_dir: string    미선택이면 ""
    artifact_refs: string[]
    created_at: string      KST, YYYY-MM-DD-HH:mm
    updated_at: string      KST, YYYY-MM-DD-HH:mm
    steps[]:
      step_id: string
      name: string
      status: workflow status
    available_details: string[]  미요청 시 ["include_holons"]
    holon_ids?: string[]     include_holons=true일 때

Output — plan_id와 step_id로 조회
  id: string                해당 Plan 안의 Step ID
  type: "step"
  status: workflow status
  next_step: string          set_working_plan 작업 선택 안내
  step:
    plan_id: string
    revision: integer       소속 Plan revision
    name: string
    input_refs: string[]
    output_refs: string[]
```

Plan의 Step 목록에는 긴 입출력 기록이 없다. 특정 Step을 선택하면 그 Step의 기록만 반환한다. Step에는 Component를 할당하지 않는다. revision은 Plan 메타데이터와 Step 기록의 snapshot이며 Rhino 형상 백업이 아니다.

과거 Plan의 `next_step`은 같은 revision을 지정해 Step을 조회하도록 안내한다. 현재 작업을 선택하려면 revision 없이 최신 상태를 먼저 조회한다. `set_working_plan`은 현재 Plan을 선택하며 과거 revision을 복원하지 않는다.

## 목록과 이력

```text
list_phases Input
  limit?: integer           기본 50, 1~500
  field_groups?: string[] | null  description | scope | audit | all
Output
  status: "success"
  phases[]:
    phase_id: string
    name: string
    status: workflow status
    plan_count: integer
    depends_on: string[]
    description?: string             description 선택
    file_name?: string               scope 선택
    project_file_id?: string | null  scope 선택
    created_at?: string              audit 선택, 저장 시각
    updated_at?: string              audit 선택, 저장 시각
  total: integer
  limit: integer
  truncated: boolean
  next_step: string          Phase 상세 조회 또는 list_plans 필터 안내

list_plans Input
  phase_id?: string          기본 "", 생략 시 모든 Phase
  scene_id?: string          기본 ""
  status?: string            기본 "", 지정 시 workflow status
  limit?: integer            기본 50, 1~500
Output
  status: "success"
  plans[]:
    plan_id: string
    title: string
    scope: string
    status: workflow status
    revision: integer
  total: integer
  limit: integer
  truncated: boolean
  next_step: string          plan_id를 통합 상세에 넣는 안내

list_plan_revisions Input
  plan_id: string            필수
  limit?: integer            기본 50, 1~500
  field_groups?: string[] | null  audit | all
Output
  status: "success"
  plan_id: string
  revisions[]:
    revision: integer
    operation: string
    created_at?: string     audit 선택, 저장 시각
  total: integer
  limit: integer
  truncated: boolean
```

목록에 표시된 total/truncated는 조회 한도로 인한 누락을 알린다. 텍스트 길이를 기준으로 기록을 자르지 않는다. 목록 순서는 Phase 생성 시각, Plan 최신 수정 시각, revision 내림차순이며 동일 시각에는 ID로 정렬한다.

## 생성과 수정

```text
create_phase Input
  name: string              필수, 비어 있지 않은 이름
  description?: string      기본 ""
  file_name?: string        기본 "", 폴더 제외 파일명
  project_file_id?: string | null
  status?: string           기본 pending
  depends_on?: string[] | null  Phase ID만

update_phase Input
  phase_id: string          필수
  name?: string | null
  description?: string | null
  file_name?: string | null
  project_file_id?: string | null
  status?: string | null
  depends_on?: object | null
    add?: string[]          Phase ID만, 기본 []
    remove?: string[]       Phase ID만, 기본 []

create_plan Input
  title: string             필수, 비어 있지 않은 제목
  goal: string              필수, 비어 있지 않은 목표
  scope?: string            기본 house, 등록된 템플릿 scope
  phase_id?: string         기본 "", Phase 없는 Plan 허용
  scene_id?: string         기본 "", 단일 Scene 호환 입력
  scene_ids?: string[] | null
  holon_ids?: string[] | null
  depends_on?: string[] | null  Plan ID만

update_plan Input
  plan_id: string           필수
  title?: string | null
  goal?: string | null
  phase_id?: string | null  ""이면 연결 해제
  scene_ids?: string[] | null
  holon_ids?: string[] | null
  depends_on?: object | null
    add?: string[]          Plan ID만, 기본 []
    remove?: string[]       Plan ID만, 기본 []
  status?: string | null
  artifact_refs?: string[] | null
  expected_revision?: integer | null

update_step Input
  plan_id: string           필수
  step_id: string           필수
  status?: string | null    생략/null이면 유지
  input_refs?: object | null
    add?: string[]          기본 []
    remove?: string[]       기본 []
  output_refs?: object | null
    add?: string[]          기본 []
    remove?: string[]       기본 []
  expected_revision?: integer | null

Output — create_phase
  status: "success"
  phase:
    phase_id: string
    status: workflow status

Output — create_plan
  status: "success"
  plan:
    plan_id: string
    status: workflow status
    revision: integer

Output — update_phase / update_plan / update_step
  status: success | partial_success | no_change
  changed: boolean
  phase?:                  update_phase
    phase_id: string
    status: workflow status
  plan?:                   update_plan / update_step
    plan_id: string
    status: workflow status
    revision: integer
  step?:                   update_step
    step_id: string
    status: workflow status
  issues[]:                건너뛴 입력 항목만; 없으면 []
    field: string          depends_on | input_refs | output_refs
    operation: add | remove
    index: integer         해당 add/remove 배열의 0부터 시작하는 위치
    value: string          해당 원래 입력
    reason: invalid_value | invalid_reference_kind | conflicting_operation
            | duplicate_input | already_present | not_found
```

생성의 depends_on은 전체 초기 배열이다. 수정의 depends_on·input_refs·output_refs는 add/remove 객체만 받으며 기존 전체 교체 배열은 받지 않는다. 생략/null/{} 및 빈 add/remove는 유지다. 모두 비우려면 조회한 기존 값을 remove에 넣는다. scene_ids·holon_ids·artifact_refs는 기존 전체 교체 방식으로, 생략/null은 유지하고 []는 비운다.

항목은 앞뒤 공백을 제외해 비교하고 새 값은 정규화해 추가한다. 기존 항목 순서는 보존하고 새 항목은 add 순서로 뒤에 붙인다. 같은 값이 add/remove 양쪽에 있으면 양쪽 모두 건너뛰며 다른 정상 항목은 적용한다. 같은 작업 내 반복 입력은 첫 항목을 처리하고 이후 항목을 중복으로 보고한다. 비어 있는 문자열, 잘못된 종류의 의존 ID, 이미 있는 값의 추가, 없는 값의 제거는 해당 항목만 건너뛴다.

건너뛴 항목이 없으면 success이며, 유효한 변경과 건너뛴 항목이 함께 있으면 partial_success다. 문제 항목은 있으나 실제 변경이 없으면 no_change다. 빈 요청 등 문제 없는 무변경은 success와 changed=false다. 실제 변경이 없으면 revision·시각을 유지한다. partial_success/no_change의 issues는 축약하거나 숨기지 않는다.

잘못된 일반 필드, 존재하지 않는 수정 대상, 예상 revision 불일치는 요청 전체 미적용이다. 자료형·입력 구조 오류도 전체 거절한다. 예를 들어 add=["기록", 42], add=null, 알 수 없는 patch 키, 기존 배열 형식은 MCP 입력 검증에서 거절된다. 이 오류는 MCP isError=true이고, 저장소의 일반 필드 오류는 기존처럼 본문 status=error를 반환한다. 배열 항목별 부분 성공은 입력 형식이 올바른 문자열의 내용 문제에 적용된다.

```json
{"plan_id":"plan_example","step_id":"design","output_refs":{"add":["검토 기록"],"remove":["철회한 기록"]},"expected_revision":7}
```

`scene_id`와 `scene_ids`를 함께 넣으면 단일 값이 배열 첫 항목과 같아야 한다. Plan의 Component와 Scene은 실제 저장된 대상을 참조한다. `depends_on`은 Phase에는 `phase_`, Plan에는 `plan_` ID만 받지만 미생성 참조·자기 참조·순환을 허용하고 실행/완료를 강제하지 않는다.

제목·상태·참조가 실제로 바뀌면 Plan revision을 기록하고 같은 값이면 시각/revision을 유지한다. Step 상태가 바뀔 때만 Plan 상태를 재계산한다. status/input_refs/output_refs는 어떤 조합으로도 선택 수정하며 한 요청은 실제 변경이 있을 때 revision을 한 번만 증가시킨다. 기록만 수정할 때 status를 생략할 수 있고 Step 상태와 Plan의 paused/completed 상태가 유지된다. 조회 응답의 next_step은 후속 조회·작업 선택을 안내하지만, 조회나 set_working_plan 선택 자체가 상태 변경 또는 실행을 뜻하지 않는다. `expected_revision`은 선택 입력으로, 저장된 최신 revision과 다르면 수정을 거절한다.

`resolve_targets`는 Plan의 Component 대상을 해석한다. 선택적 step_id는 소속 Step을 확인할 뿐 대상을 바꾸지 않는다. `get_selection_references`도 Plan 대상을 기준으로 선택 객체와 관련된 Plan/Step을 찾는다. 두 도구의 상세 선택은 각 tools/list 설명을 따른다. `set_working_plan`의 선택·산출물 폴더 계약은 [runtime 설명](../../runtime/mcp_server-explain.md)을 따른다.

`set_working_plan`은 plan_id·step_id·artifact_dir와 선택 시점의 Plan revision을 반환한다. 첫 산출물 경로 설정으로 revision이 증가할 수 있으므로, 이어지는 수정의 expected_revision에는 선택 응답의 revision을 사용한다. 폴더를 재사용하는 선택만으로는 revision이 증가하지 않는다.

## Step 템플릿 선택

기존 `house`, `interior`, `structure`, `drawing`, `component`와 기본값 `house`는 유지한다. 기존 Plan의 Step이나 이력을 새 템플릿으로 바꾸지 않는다. Task의 주된 목적에 따라 아래 scope를 추가로 선택할 수 있다. 범주는 배타적인 분류나 실행 권한이 아니다.

| scope | 용도 | 생성되는 Step 순서 |
|---|---|---|
| `spatial_development` | 공간 생성·구성·발전 | inspect_context → identify_opportunities → develop_options → apply_design → validate_relationships |
| `plan_editing` | 기존 2D 평면 편집 | inspect_plan → define_changes → edit_plan → validate_plan |
| `construction_detail` | 요청된 구축 상세 발전 | inspect_context → review_system → resolve_detail → model_detail → validate_detail |
| `model_revision` | 기존 설계·모델 수정 | inspect_context → diagnose_issue → define_changes → apply_changes → validate_impacts |
| `inspection` | 변경을 전제하지 않는 검수 | define_criteria → observe → evaluate → report_findings |
| `semantic_exploration` | 공간과 주변 맥락의 해석·보고 | inspect_context → inspect_surroundings → interpret_spatial_context → report_findings |

`drawing`은 도면 생성·표현·출력 흐름이고 `plan_editing`은 기존 평면의 공간·선·치수 관계를 편집하는 흐름이다. 일반 공간 발전·모델 수정 템플릿에는 구축 상세를 자동 요구하는 Step이 없다. 검수의 report_findings는 판단·기록 단계이며 모델 수정 단계가 아니다.

Construction detail은 저장된 ON/OFF 필드가 없다. 해당 Task의 사용자 요청과 작업 기록·지침으로 판단하며 기본 OFF다. `construction_detail` scope를 선택했다고 사용자 요청이 생긴 것으로 간주하지 않는다. `review_system`에서는 실제 시스템 Layer면 해당 자료와 주변 조건을 확인하고, 유형 Layer면 시스템 미정으로 보고 대안을 논의한다. `resolve_detail`에서 필요한 선택을 정한 뒤 모델링한다. 일반 자료 조회 자체를 금지하는 정책은 아니다.

새 scope는 기존 registry에 누락된 이름만 추가한다. 같은 이름의 사용자 정의 scope가 이미 있으면 기존 template_scope 매핑을 보존한다. 이후 생성한 Plan의 실제 Step 목록으로 해당 매핑을 확인한다. Step 추가·삭제·템플릿 편집 API는 제공하지 않는다.

## 기존 데이터

새 스키마를 처음 열 때 빈 제목을 goal의 첫 비어 있지 않은 줄에서 최대 80자로 채운다. goal 원문은 보존한다. 실제 프로젝트의 읽기 좋은 제목 작성은 update_plan으로 기록한다. 동종이 아닌 의존 참조와 Step별 활성 대상을 정리하되 Step별 이전 대상은 `_retired_step_targets`에 보존한다. 대상/의존 관계가 달라진 Plan은 새 revision을 남긴다. 기존 revision JSON은 그대로 보존하며 과거 조회에서 현재 계약에 맞는 필드만 보여준다. 타임스탬프 저장은 UTC, Plan 상세 표시는 KST다.

Python 변경을 사용하려면 관련 MCP/Terminal almond 세션을 정상 종료하고 새로 시작한다. 외부 카탈로그는 시작 시 현재 소스에서 자동 생성된다. 이 변경에는 RHP 빌드·교체·등록 변경이 필요하지 않다.
