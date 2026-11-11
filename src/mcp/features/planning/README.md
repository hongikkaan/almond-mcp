# Phase·Plan·Step 도구 계약

계획 도구는 생성 `plan_02-create` tool, 조회 `plan_05-get` tool, 목록 `plan_08-list` tool, 수정 `plan_12-update` tool 네 가지다. 각 호출은 단일 `request` 객체를 받고 `request.target`으로 대상을 선택한다. create는 `phase | plan`, get/list/update는 `phase | plan | step`을 지원한다. Step은 Plan 생성 시 scope 템플릿에서 자동 생성하며 독립 생성·추가·삭제 도구는 없다.

기본 조회 순서는 `plan_08-list` tool의 `request.target="phase"` → 같은 도구의 `request.target="plan"`과 `phase_id` → `plan_05-get` tool이다. 각 target에 허용된 필드만 입력할 수 있으며 다른 대상의 필드와 알 수 없는 필드는 요청 전체를 거절한다. 아래 입력 표·목록의 필드는 모두 `request` 안에 넣는다. 별도 도구인 `plan_07-list_revisions`, `plan_03-execute_looping`, `plan_10-set_working`, `plan_09-rename_artifact_folder`는 기존 최상위 입력을 유지한다.

```json
{"request":{"target":"step","plan_id":"plan_example","step_id":"step_example","include_details":true}}
```

이 모듈의 조회에는 `include_ids`가 없고 ID를 항상 출력한다. 작업 상태값은 `pending | running | paused | completed | failed | blocked`다. 아래 `?`는 선택 입력이다. 통합 상세 응답의 최상위 `status`는 선택한 항목의 작업 상태다. 목록·생성 성공은 `status: success`, 오류는 `status: error`와 message를 사용한다. 수정 응답의 적용 여부와 부분 성공은 아래 계약을 따른다.

## 통합 상세 조회

`plan_05-get` tool은 `request.target="phase"`일 때 `phase_id`, `"plan"`일 때 `plan_id`, `"step"`일 때 `plan_id`와 `step_id`를 받는다. Phase 조회는 loop_no/revision을 받지 않는다.

| 입력 | 타입 | 의미 |
|---|---|---|
| phase_id | string | 조회할 Phase ID |
| plan_id | string | 조회할 Plan 또는 Step의 소속 Plan ID |
| step_id | string | 조회할 Step ID |
| include_details | boolean, 기본 false | true이면 해당 유형의 상세 객체 포함 |
| loop_no | integer 또는 null | Plan·Step의 회차. 생략하면 현재, 0은 실행 전 |
| revision | integer 또는 null | 선택 회차의 저장 리비전. 생략하면 최신 |

공통 출력은 `id`, `type`, `name`, `status`다. `status`는 해당 항목의 업무 상태이며 조회 오류는 `error`다. Plan·Step에는 상세 선택과 무관하게 `plan_id`, `loop_no`, `revision`, `read_only`도 포함한다.

`include_details=true`일 때 추가하는 본문은 다음과 같다.

- `phase`: description, file_name 배열, depends_on, previous_id, plan_titles.
- `plan`: goal, scope, phase, scene_ids, holon_ids, depends_on, previous_id, parent_plan, child_plan, artifact_dir, loop_artifact_dir, artifact_refs, feedback, created_at, updated_at, steps.
- `step`: step_type, input_refs, output_refs.

Plan의 steps는 Step ID·역할·이름·상태·회차의 요약이다. 특정 Step 조회는 해당 Step의 긴 입출력 기록만 읽는다. Plan의 시각은 KST `YYYY-MM-DD-HH:mm`으로 반환한다.

과거 기록은 `read_only=true`다. 과거 요약의 상세를 보려면 같은 target·ID·loop_no·revision을 유지하고 include_details=true로 조회한다. 현재 기록이 필요하면 loop_no와 revision을 생략한다. `next_step_guide`는 이 구분과 현재 상세에서 필요한 작업 선택을 안내한다.

## Phase의 파일 연결

`plan_02-create` tool의 `request.target="phase"`에서 `file_name`은 파일명 문자열 또는 문자열 배열을 받는다. `plan_12-update` tool의 `request.target="phase"`에서 `file_name`도 같으며 생략/null은 유지, 빈 문자열이나 빈 배열은 연결 해제다. 공개 Phase 도구에는 `project_file_id` 입력이 없다. Phase 상세와 목록 scope 그룹의 `file_name`은 항상 배열이다.

파일 연결은 순서가 있는 `generation_phase_files`에 저장한다. 기존 단일 연결을 이관하며 Plan·Step 이력은 바꾸지 않는다. 내부 호환 키에는 첫 파일을 남기고, 이전 저장소가 단일 연결을 변경하면 트리거로 연결을 맞춘다. 여러 파일 중 하나라도 유효하지 않거나 이름이 모호하면 해당 요청의 파일 등록과 Phase 변경을 모두 되돌린다. 같은 이름의 여러 등록 파일을 임의로 선택하지 않는다. Scene의 단일 파일 입력 계약은 유지한다.

## 목록과 이력

```text
plan_08-list tool request (target="phase")
  limit?: integer           기본 50, 1~500
  field_groups?: string[] | null  description | scope | audit | all
Output
  status: "success"
  phases[]:
    phase_id: string
    name: string
    status: pending | running | paused | completed | failed | blocked
    plan_count: integer
    depends_on: string[]
    description?: string             description 선택
    file_name?: string[]             scope 선택
    created_at?: string              audit 선택, 저장 시각
    updated_at?: string              audit 선택, 저장 시각
  total: integer
  limit: integer
  truncated: boolean
  next_step_guide?: string          Phase 상세 조회 또는 plan_08-list tool 필터 안내

plan_08-list tool request (target="plan")
  phase_id?: string          기본 "", 생략 시 모든 Phase
  scene_id?: string          기본 ""
  status?: string            기본 "", 지정 시 pending | running | paused | completed | failed | blocked
  limit?: integer            기본 50, 1~500
Output
  status: "success"
  plans[]:
    plan_id: string
    title: string
    scope: string
    status: pending | running | paused | completed | failed | blocked
    loop_no: integer
    revision: integer
  total: integer
  limit: integer
  truncated: boolean
  next_step_guide?: string          plan_id를 통합 상세에 넣는 안내

plan_08-list tool request (target="step")
  plan_id: string            필수
  loop_no?: integer | null   생략하면 최신 Loop
  revision?: integer | null  생략하면 해당 Loop의 최신 상태
  limit?: integer            기본 50, 1~500
Output
  status: "success"
  plan_id: string
  loop_no: integer
  revision: integer
  read_only: boolean
  steps[]:                   선택한 스냅샷의 정의 순서 유지
    step_id: string
    step_type: string
    name: string
    status: pending | running | paused | completed | failed | blocked
    loop_no: integer
  total: integer
  limit: integer
  truncated: boolean
  next_step_guide?: string    같은 스냅샷의 Step 상세 조회 안내

plan_07-list_revisions tool Input
  plan_id: string            필수
  loop_no?: integer | null   생략하면 모든 Loop
  step_id?: string           직접 Step 변경 기록만 필터
  limit?: integer            기본 50, 1~500
  field_groups?: string[] | null  audit | all
Output
  status: "success"
  plan_id: string
  revisions[]:
    loop_no: integer
    revision: integer
    operation: string
    step_id: string | null    직접 Step 변경이면 UUID, Plan 전체 변경이면 null
    created_at?: string     audit 선택, 저장 시각
  total: integer
  limit: integer
  truncated: boolean
```

Step 목록은 한 Plan 스냅샷에서만 읽으며 없는 Plan·Loop·revision은 빈 목록 대신 오류를 반환한다.

목록에 표시된 total/truncated는 조회 한도로 인한 누락을 알린다. 텍스트 길이를 기준으로 기록을 자르지 않는다. 목록 순서는 Phase 생성 시각, Plan 최신 수정 시각, revision 내림차순이며 동일 시각에는 ID로 정렬한다.

## 생성과 수정

```text
plan_02-create tool request (target="phase")
  name: string              필수, 비어 있지 않은 이름
  description?: string      기본 ""
  file_name?: string | string[]    기본 "", Rhino 파일명
  status?: string           기본 pending
  depends_on?: string[] | null  Phase ID만

plan_12-update tool request (target="phase")
  phase_id: string          필수
  name?: string | null
  description?: string | null
  file_name?: string | string[] | null
  status?: string | null
  depends_on?: object | null
    add?: string[]          Phase ID만, 기본 []
    remove?: string[]       Phase ID만, 기본 []

plan_02-create tool request (target="plan")
  title: string             필수, 비어 있지 않은 제목
  goal: string              필수, 비어 있지 않은 목표
  scope?: string            기본 house, 등록된 템플릿 scope
  phase_id?: string         기본 "", Phase 없는 Plan 허용
  scene_id?: string         기본 "", 단일 Scene 호환 입력
  scene_ids?: string[] | null
  holon_ids?: string[] | null
  depends_on?: string[] | null  Plan ID만
  parent_plan?: string[] | null  기본 []
  child_plan?: string[] | null   기본 []

plan_12-update tool request (target="plan")
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
  parent_plan?: string[] | null  생략/null이면 유지, []이면 비움
  child_plan?: string[] | null   생략/null이면 유지, []이면 비움
  expected_revision?: integer | null  선택적 오래된 상태 검사
  loop_no?: integer | null   현재 Loop 검사, 실행 후 expected_revision과 함께 필요

plan_12-update tool request (target="step")
  plan_id: string           필수
  step_id: string           필수
  status?: string | null    생략/null이면 유지
  input_refs?: object | null
    add?: string[]          기본 []
    remove?: string[]       기본 []
  output_refs?: object | null
    add?: string[]          기본 []
    remove?: string[]       기본 []
  expected_revision?: integer | null  선택적 오래된 상태 검사
  loop_no?: integer | null   현재 Loop 검사, 실행 후 expected_revision과 함께 필요

Output — plan_02-create tool (target="phase")
  status: "success"
  phase:
    phase_id: string
    status: pending | running | paused | completed | failed | blocked

Output — plan_02-create tool (target="plan")
  status: "success"
  plan:
    plan_id: string
    status: pending | running | paused | completed | failed | blocked
    loop_no: integer
    revision: integer

Output — plan_12-update tool
  status: success | partial_success | no_change
  changed: boolean
  phase?:                  target="phase"
    phase_id: string
    status: pending | running | paused | completed | failed | blocked
  plan?:                   target="plan" 또는 "step"
    plan_id: string
    status: pending | running | paused | completed | failed | blocked
    loop_no: integer
    revision: integer
  step?:                   target="step"
    step_id: string
    status: pending | running | paused | completed | failed | blocked
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
{"request":{"target":"step","plan_id":"plan_example","step_id":"step_4cfa2ee3887946c4967dfb844cfe8022","output_refs":{"add":["검토 기록"],"remove":["철회한 기록"]},"loop_no":1,"expected_revision":7}}
```

`scene_id`와 `scene_ids`를 함께 넣으면 단일 값이 배열 첫 항목과 같아야 한다. Plan의 Component와 Scene은 실제 저장된 대상을 참조한다. `depends_on`은 Phase에는 `phase_`, Plan에는 `plan_` ID만 받지만 미생성 참조·자기 참조·순환을 허용하고 실행/완료를 강제하지 않는다.

`parent_plan`·`child_plan`은 이 Plan에만 기록하는 단방향 참조 목록이며 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검증하지 않는다.

제목·상태·참조가 실제로 바뀌면 Plan revision을 기록하고 같은 값이면 시각/revision을 유지한다. Step 상태가 바뀌어도 Plan 상태는 자동 변경하지 않는다. Plan 완료는 사용자가 판단한다. status/input_refs/output_refs는 어떤 조합으로도 선택 수정하며 한 요청은 실제 변경이 있을 때 revision을 한 번만 증가시킨다. 기록만 수정할 때 status를 생략할 수 있고 Step 상태와 Plan의 paused/completed 상태가 유지된다. 조회 응답의 next_step_guide는 후속 조회·작업 선택을 안내하지만, 조회나 plan_10-set_working tool 선택 자체가 상태 변경 또는 실행을 뜻하지 않는다. `expected_revision`은 선택 입력으로, 저장된 최신 revision과 다르면 수정을 거절한다.

`inspect_05-resolve_targets` tool는 Plan의 Component 대상을 해석한다. 선택적 step_id는 소속 Step을 확인할 뿐 대상을 바꾸지 않는다. `inspect_04-get_selection_references` tool도 Plan 대상을 기준으로 선택 객체와 관련된 Plan/Step을 찾는다. 두 도구의 상세 선택은 각 tools/list 설명을 따른다. `plan_10-set_working` tool의 선택·산출물 폴더 계약은 [runtime 설명](../../runtime/mcp_server-explain.md)을 따른다.

`plan_10-set_working` tool은 plan_id·step_id·loop_no·plan_artifact_dir·artifact_dir와 선택 시점의 Plan revision을 반환한다. 첫 산출물 경로 설정으로 revision이 증가할 수 있으므로, 선택적 expected_revision 검사를 쓸 때에는 선택 응답의 revision과 loop_no를 함께 사용한다. 번호 계산이나 직접 증가는 필요 없다. 폴더를 재사용하는 선택만으로는 revision이 증가하지 않는다.

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

새 스키마를 처음 열 때 빈 제목을 goal의 첫 비어 있지 않은 줄에서 최대 80자로 채운다. goal 원문은 보존한다. 실제 프로젝트의 읽기 좋은 제목 작성은 plan_12-update tool의 request.target="plan"과 title로 기록한다. 동종이 아닌 의존 참조와 Step별 활성 대상을 정리하되 Step별 이전 대상은 `_retired_step_targets`에 보존한다. 대상/의존 관계가 달라진 Plan은 새 revision을 남긴다. 기존 revision JSON은 그대로 보존하며 과거 조회에서 현재 계약에 맞는 필드만 보여준다. 타임스탬프 저장은 UTC, Plan 상세 표시는 KST다.

Python 변경을 사용하려면 관련 MCP/Terminal almond 세션을 정상 종료하고 새로 시작한다. 외부 카탈로그는 시작 시 현재 소스에서 자동 생성된다. 이 변경에는 RHP 빌드·교체·등록 변경이 필요하지 않다.


### 이전 작업 연결

Plan과 Phase의 `previous_id`는 같은 종류의 직전 작업 하나를 기록하며, 여러 관계를 담는 `depends_on`과 독립적이다. 생성·수정 도구와 상세 조회에 공개한다. 수정에서 null/생략은 유지, 빈 문자열은 해제이다. 같은 종류의 ID 형식만 검사하며 관계를 근거로 실행 순서나 완료를 강제하지 않는다. 과거 snapshot에 이 필드가 없으면 조회 시 null을 반환하고 저장 원문은 바꾸지 않는다. nullable 열을 추가하는 migration은 기존 데이터·상태·이력을 보존한다.


## Loop 실행과 저장

- `plan_03-execute_looping tool(plan_id, resume=false, feedback="", artifact_name="")`은 다음 회차를 시작하고 작업 맥락을 선택한다. 첫 호출은 1, 다음 호출은 2다. `resume=true`는 최신 회차의 번호와 Step 기록을 유지한다. 실행 전에는 재개할 회차가 없다.
- 응답에는 목표, Plan 상태, 피드백, 순서 있는 Step 및 입출력 기록, 다음 미완료 Step, 이전 회차 기록, 산출물 경로, 짧은 실행·보고 원칙가 있다. Step을 자동 실행하지 않는다. 회차에는 종료·중단·진행 상태가 없고 Plan·Step의 기존 6개 상태만 사용한다.
- Step UUID와 유형/이름은 별개다. 새 회차에도 UUID·순서·유형을 유지하며 회차별 상태는 pending, 입출력 기록은 빈 배열로 시작한다. 이전 결과의 유효성을 확인한 뒤 원래 경로를 input_refs로 참조한다.
- Plan의 `loop_no=0`은 아직 plan_03-execute_looping tool을 호출하지 않았다는 값이다. 실행 Loop 테이블에 0 행을 만들지 않고 00 폴더도 만들지 않는다. 기존 생성·수정 기록은 번호와 snapshot 원문을 그대로 보존하며 loop_no=0으로 조회한다.
- `generation_plan_steps`는 Step 정의, `generation_loop_steps`는 (plan_id, loop_no, step_id)별 상태·입출력, `generation_plan_loops`는 실제 1 이상 회차와 피드백, `generation_plan_revisions`는 (plan_id, loop_no, revision)별 전체 snapshot이다. Step 수정 revision의 별도 step_id 열로 필터한다. Plan-wide 기록의 step_id는 null이다.
- 현재 Loop의 MAX(revision)+1을 기존 BEGIN IMMEDIATE 트랜잭션 안에서 할당하고 데이터 변경과 snapshot을 함께 commit한다. 새 Loop는 revision 1부터 시작한다. 현재 Plan의 revision은 현재 Loop 최신 번호이며 전역 카운터가 아니다. 조회·무변경·일반 Rhino/Python 호출은 revision을 만들지 않는다.
- 현재보다 작은 Loop와 그 기록은 읽기 전용이다. 조회에 loop_no를 생략하면 최신 회차, revision도 생략하면 그 회차 최신 상태다. 과거 상태는 읽을 수 있지만 복원하거나 다시 수정하지 않는다. 선택적 expected_revision은 실행 후 loop_no와 함께 검사해 서로 다른 회차의 같은 번호를 혼동하지 않는다.
- Plan 폴더 아래 01, 02처럼 회차별 출력을 저장한다. 같은 회차 안에서는 덮어쓸 수 있으며 이전 회차 내용은 새 회차 폴더로 옮기지 않는다. 실행 전은 기존 Plan 루트를 사용한다. 과거 경로 보존을 위해 실행한 Plan의 루트나 과거 Loop가 참조하는 폴더는 이름 변경하지 않는다.
- 연결의 작업 선택이 다른 연결의 회차 진행으로 오래되면 관리되는 출력은 최신 회차 재선택까지 차단한다. 상대경로 helper는 상위/절대경로와 파일시스템 링크를 거절한다. 임의 Python/C#이나 외부 OS 파일 작업까지 샌드박스로 막는 기능은 아니므로 이전 회차 파일을 쓰지 않는 정책도 따른다. revision은 파일 바이트나 Rhino 형상 백업이 아니다.
