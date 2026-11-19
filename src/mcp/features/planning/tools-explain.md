# Planning tools

## create_planning

<!-- instruction:create_planning -->
Phase 또는 Plan을 생성합니다. Plan은 scope에 맞는 Step을 자동으로 만들며 **작업을 실행하지 않습니다.**

`result`는 생성된 `phase_id` 또는 `plan_id`와 상태를 담은 JSON 문자열입니다. 생성 오류도 `result.status`에 반환될 수 있습니다. Plan은 초기 loop_no=0, revision=1로 생성됩니다. 생성된 Plan의 Step은 plan_05-get tool에서 확인할 수 있습니다.

Args:
    request: target으로 phase 또는 plan을 선택하고 해당 생성 정보를 입력합니다. Step 독립 생성은 제공하지 않습니다.
<!-- /instruction:create_planning -->

## get_planning

<!-- instruction:get_planning -->
Phase, Plan 또는 Step의 작업 기록을 조회합니다. 기본값은 식별·상태 요약이며, include_details=true이면 선택한 대상의 상세를 함께 반환합니다. Plan 상세에는 Step 요약이, Step 상세에는 입출력 참조와 Takeaways·Design rationale이 포함됩니다. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로를 열어 내용을 확인합니다.

`result`는 조회 결과 또는 오류를 담은 JSON 문자열입니다. 성공 시 status는 대상의 작업 상태이며, 오류는 status=error입니다. Plan과 Step은 `loop_no`·`revision`·`read_only`를 함께 반환합니다. **revision을 명시하면 현재 번호여도 읽기 전용 스냅샷**입니다.

Args:
    request: target으로 phase, plan, step을 선택하고 해당 ID를 입력합니다. include_details로 상세 기록을 선택합니다.
<!-- /instruction:get_planning -->

## list_planning

<!-- instruction:list_planning -->
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록을 조회합니다.

`result`는 상태와 `phases`·`plans`·`steps` 중 해당 목록을 담은 JSON 문자열입니다. `total`과 `truncated`는 목록 크기와 잘림 여부를 나타냅니다. **offset은 지원하지 않으며** `limit`은 최대 500입니다. Step 조회는 같은 스냅샷의 `loop_no`·`revision`과 `read_only`를 함께 반환합니다.

Args:
    request: target으로 phase, plan, step을 선택합니다. Step에는 plan_id가 필요하며 대상별 필터와 limit을 지정합니다.
<!-- /instruction:list_planning -->

## update_planning

<!-- instruction:update_planning -->
Phase·Plan의 작업 정보 또는 Step의 상태, 입출력 참조, Takeaways·Design rationale을 수정합니다. Plan·Step은 현재 Loop만 변경할 수 있습니다.

`depends_on`, `input_refs`, `output_refs`는 add/remove 패치이며 Plan의 대상·산출물·상하위 관계 배열은 전체 교체합니다. 생략 또는 null은 유지, 교체 배열의 []는 비웁니다. `takeaways`와 `design_rationale`은 빈 문자열로 비웁니다.

응답은 JSON 문자열입니다. `changed`는 실제 변경 여부, `issues`는 건너뛴 항목입니다. 중복·충돌 등 적용하지 못한 패치 항목은 `issues`에 기록하며, 일부만 적용되면 `partial_success`를 반환합니다. Loop 실행 후 `expected_revision`을 지정할 때는 `loop_no`도 함께 지정합니다.

Step 상태를 `completed`로 지정하면 다른 수정 필드와 함께 한 번의 요청으로 저장합니다.

Args:
    request: target으로 phase, plan, step을 선택하고 해당 ID와 바꿀 필드만 입력합니다. Step은 상태·입출력 참조·판단 기록 중 필요한 필드만 갱신합니다.
<!-- /instruction:update_planning -->

## list_plan_revisions

<!-- instruction:list_plan_revisions -->
Plan의 저장 리비전 목록을 최신 회차·리비전 순으로 조회합니다. Loop나 Step으로 필터링할 수 있으며, Step 필터는 그 Step의 직접 변경만 포함합니다.

result는 revisions, total, limit, truncated를 담은 JSON 문자열입니다. offset은 지원하지 않으며 limit은 최대 500입니다. 선택한 과거 기록은 plan_05-get tool에서 같은 loop_no와 revision으로 조회합니다.

Args:
    plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    limit: 1~500, 기본 50.
    field_groups: audit 또는 all: 생성 시각 포함. 생략·빈 배열: 기본 필드.
    loop_no: 생략·null: 전체. 0: 실행 전 기록.
    step_id: 생략·빈 문자열: Plan 전체.
<!-- /instruction:list_plan_revisions -->

## resolve_targets

<!-- instruction:resolve_targets -->
Plan에 등록된 Scene·Holon 대상과 선택한 Holon 정보를 조회합니다. Step 지정 시 해당 Plan 소속 여부를 확인하지만 대상은 Plan 기준입니다. Scene의 모든 Holon을 자동으로 확장하지 않습니다.

저장된 대상 조회이며 Rhino의 현재 구성원은 검증하지 않습니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.

Args:
    plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    step_id: Plan 소속 검사. 생략 시 Plan 기준.
    field_groups: references, geometry, scope, audit, all. 생략·빈 배열: 기본 요약.
<!-- /instruction:resolve_targets -->

## get_selection_references

<!-- instruction:get_selection_references -->
현재 선택된 Rhino 객체의 소속 Holon과 상위 Holon을 참조하는 Plan을 찾습니다. 저장된 문서의 일반 모델에서 사용합니다.

Plan의 일치 Holon과 Plan 전체 대상은 다를 수 있습니다. 선택 객체와 Plan 목록의 잘림 여부는 각각 selection_truncated와 truncated로 확인합니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.

Args:
    selection_limit: 검사할 선택 객체 수: 1..200.
    limit: 반환할 Plan 수: 1..500.
    field_groups: steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열: 요약.
<!-- /instruction:get_selection_references -->
