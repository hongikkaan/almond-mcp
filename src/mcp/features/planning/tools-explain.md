# Planning tools

## create_planning

<!-- instruction:create_planning -->
Phase 또는 Plan을 생성합니다. Plan의 Step은 선택한 scope의 템플릿에서 자동 생성합니다.

Args:
    request: target으로 phase 또는 plan을 선택하고 해당 생성 정보를 입력합니다. Step 독립 생성은 제공하지 않습니다.
<!-- /instruction:create_planning -->

## get_planning

<!-- instruction:get_planning -->
Phase, Plan 또는 Step의 작업 기록을 조회합니다. Plan과 Step은 현재 상태 또는 저장된 Loop·리비전을 읽습니다.

Args:
    request: target으로 phase, plan, step을 선택하고 해당 ID를 입력합니다. include_details로 상세 기록을 선택합니다.
<!-- /instruction:get_planning -->

## list_planning

<!-- instruction:list_planning -->
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록을 조회합니다. Step 목록은 같은 스냅샷의 Loop·리비전과 함께 반환합니다.

Args:
    request: target으로 phase, plan, step을 선택합니다. Step에는 plan_id가 필요하며 대상별 필터와 limit을 지정합니다.
<!-- /instruction:list_planning -->

## update_planning

<!-- instruction:update_planning -->
Phase·Plan의 작업 정보 또는 Step의 상태와 입력·출력 근거를 수정합니다. 기존 Loop·리비전 보호와 부분 적용 보고를 유지합니다.

Args:
    request: target으로 phase, plan, step을 선택하고 해당 ID와 바꿀 필드만 입력합니다. Step은 상태와 문자열 목록 패치로 기록을 갱신합니다.
<!-- /instruction:update_planning -->

## list_plan_revisions

<!-- instruction:list_plan_revisions -->
Plan과 Loop에 저장된 리비전과 변경 작업을 조회합니다.

Args:
    plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    limit: 최대 리비전 기록 수입니다. 범위는 1..500입니다.
    field_groups: 저장된 타임스탬프를 포함하려면 선택적으로 audit 또는 all을 사용합니다. 생략하거나 비어 있으면 loop_no, revision, operation 및 step_id를 반환합니다.
    loop_no: 선택 사항인 0 이상의 Loop 필터입니다. 생략하면 모든 Loop를 포함하며, 0은 실행 전 이력을 선택합니다.
    step_id: 직접적인 Step 변경에 사용할 선택 사항인 UUID Step 필터입니다. 비어 있으면 Plan 전체 기록도 포함합니다.
<!-- /instruction:list_plan_revisions -->

## resolve_targets

<!-- instruction:resolve_targets -->
Plan에 등록된 Holon 대상 집합을 조회합니다.

Args:
    plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    step_id: 선택한 Plan에 속하는지 확인할 Step ID입니다. 생략해도 Plan의 Holon 대상을 조회합니다.
    field_groups: 선택 사항: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 저장된 Plan 대상 ID를 반환합니다.
<!-- /instruction:resolve_targets -->

## get_selection_references

<!-- instruction:get_selection_references -->
현재 선택한 Rhino 객체와 상위 Holon을 참조하는 Plan을 찾습니다. 저장된 문서의 일반 모델에서 사용합니다.

Args:
    selection_limit: 검사할 선택된 Rhino 객체의 최대 개수이며, 범위는 1..200입니다.
    limit: 반환할 일치 Plan의 최대 개수이며, 범위는 1..500입니다.
    field_groups: 선택 사항인 그룹: steps, references, geometry, artifacts, description, scope, audit 또는 all. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:get_selection_references -->
