# Planning tools

## create_phase

<!-- instruction:create_phase -->
관련 Plan을 묶는 Phase를 생성합니다.

Args:
    name: Phase 이름을 문자열로 입력합니다. 빈 문자열은 사용할 수 없습니다.
    description: Phase의 목적이나 작업 범위를 문자열로 입력합니다.
    file_name: 이 Phase가 속한 Rhino 파일명입니다. 문자열 하나 또는 문자열 배열로 입력합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다.
    depends_on: 이 Phase가 의존하는 Phase ID 목록입니다.
    previous_id: 이전 Phase의 ID입니다.
<!-- /instruction:create_phase -->

## list_phases

<!-- instruction:list_phases -->
프로젝트의 Phase 목록을 조회합니다.

Args:
    limit: 최대 Phase 수입니다. 범위는 1..500이며, 이 목록에는 offset 인수가 없습니다.
    field_groups: 선택 사항인 그룹은 description, scope, audit 또는 all입니다. 생략하거나 비어 있으면 요약과 ID를 유지합니다.
<!-- /instruction:list_phases -->

## update_phase

<!-- instruction:update_phase -->
Phase의 이름·설명·상태·파일 연결·관계를 수정합니다.

Args:
    phase_id: list_phases.phases[].phase_id 또는 get_phase_plan_step.id에서 얻은 기존 Phase ID입니다.
    name: 선택 사항인 비어 있지 않은 대체 Phase 이름입니다.
    description: 선택 사항인 대체 설명입니다. 비어 있으면 지웁니다.
    file_name: 이 Phase가 속한 Rhino 파일명입니다. 문자열 하나 또는 문자열 배열로 입력합니다. [] 또는 ""는 연결 해제, 생략/null은 유지입니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.
    depends_on: Phase ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 충돌하거나 유효하지 않은 문자열 항목은 보고하고 건너뜁니다. 잘못된 타입은 요청 전체를 거부합니다.
    previous_id: 이전 Phase ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다.
<!-- /instruction:update_phase -->

## create_plan

<!-- instruction:create_plan -->
작업 목표와 템플릿에 따라 Plan과 Step을 생성합니다.

Args:
    title: Plan 목록에서 사용할 비어 있지 않은 짧은 제목입니다.
    goal: 비어 있지 않은 전체 목표와 의도한 결과입니다.
    scope: 작업 목적에 맞는 Step 템플릿을 선택합니다: spatial_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록한 사용자 템플릿도 사용할 수 있습니다.
    scene_id: 기존 방식의 단일 Scene ID입니다. scene_ids를 우선 사용합니다. 둘 다 전달하면 scene_ids의 첫 번째 항목과 같아야 합니다.
    phase_id: 선택 사항인 기존 Phase ID입니다. 비어 있으면 Plan을 Phase에 소속시키지 않습니다.
    scene_ids: 맥락을 설명하는 선택 사항인 기존 Scene ID 배열로, 여러 Scene을 포함할 수 있습니다. 생략하면 Scene 없이 작업할 수 있습니다. 형상 대상 집합을 확장하지는 않습니다.
    holon_ids: 이 Plan을 위해 명시적으로 지정하는 선택 사항인 등록된 Holon 대상입니다. Step에는 별도의 Holon 할당이 없습니다.
    depends_on: 이 Plan이 의존하는 Plan ID 목록입니다.
    previous_id: 이전 Plan의 ID입니다.
    parent_plan: 선택 사항인 상위 Plan ID 배열입니다.
    child_plan: 선택 사항인 하위 Plan ID 배열입니다.
<!-- /instruction:create_plan -->

## get_phase_plan_step

<!-- instruction:get_phase_plan_step -->
Phase, Plan 또는 Step 중 하나를 조회합니다. 상세 내용의 포함 여부를 선택할 수 있습니다.

Args:
    phase_id: 조회할 Phase ID입니다. plan_id와 함께 입력하지 않습니다.
    plan_id: 조회할 Plan ID입니다. Step 조회에도 함께 입력합니다.
    step_id: 조회할 Step ID입니다. 해당 plan_id와 함께 입력합니다.
    revision: 선택한 Loop 안에 저장된 선택적 리비전입니다. 생략하면 선택한 Loop의 최신 상태를 읽습니다. Phase에는 사용할 수 없습니다.
    include_details: true이면 선택한 유형의 상세 내용을 추가합니다.
    loop_no: Plan/Step 조회에 사용할 선택 사항인 0 이상의 Loop 번호입니다. 생략하면 최신 Loop를 선택합니다. 0은 실행 전 기록을 읽습니다. Phase에는 사용할 수 없습니다.
<!-- /instruction:get_phase_plan_step -->

## list_plans

<!-- instruction:list_plans -->
프로젝트의 Plan 목록을 조회합니다. Phase·Scene·상태로 범위를 좁힐 수 있습니다.

Args:
    phase_id: 선택 사항인 Phase ID 필터입니다. 비어 있으면 여러 Phase를 범위로 합니다.
    scene_id: 선택 사항인 Scene ID 필터입니다. 비어 있으면 어떤 Scene에 속하든, Scene이 없든 모든 Plan을 포함합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 빈 문자열이면 모든 상태를 포함합니다.
    limit: 최대 Plan 수입니다. 범위는 1..500이며, 이 목록에는 offset 인수가 없습니다.
<!-- /instruction:list_plans -->

## update_plan

<!-- instruction:update_plan -->
Plan의 목표·상태·대상·관계·산출물 참조를 수정합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    goal: 선택 사항인 비어 있지 않은 대체 전체 목표입니다.
    phase_id: 선택 사항인 기존 Phase ID입니다. 비어 있으면 Phase 소속을 해제하고, 생략/null이면 유지합니다.
    scene_ids: 선택 사항인 대체 Scene ID 배열입니다. []이면 비우고 생략/null이면 유지합니다. Scene은 맥락을 설명하며 자동 편집 대상이 아닙니다.
    holon_ids: 선택 사항인 대체 Plan Holon 대상 배열입니다. []이면 비우고 생략/null이면 유지합니다.
    expected_revision: 현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.
    depends_on: Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. completed는 사용자의 완료 결정 후 지정합니다. 생략/null은 유지입니다.
    artifact_refs: 선택 사항인 대체 산출물 참조 문자열 배열입니다. []이면 비우고 생략/null이면 유지합니다.
    title: 선택 사항인 비어 있지 않은 대체 짧은 제목입니다.
    previous_id: 이전 Plan ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다.
    parent_plan: 선택 사항인 대체 상위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다.
    child_plan: 선택 사항인 대체 하위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다.
    loop_no: 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다.
<!-- /instruction:update_plan -->

## list_plan_revisions

<!-- instruction:list_plan_revisions -->
Plan과 Loop에 저장된 리비전과 변경 작업을 조회합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    limit: 최대 리비전 기록 수입니다. 범위는 1..500입니다.
    field_groups: 저장된 타임스탬프를 포함하려면 선택적으로 audit 또는 all을 사용합니다. 생략하거나 비어 있으면 loop_no, revision, operation 및 step_id를 반환합니다.
    loop_no: 선택 사항인 0 이상의 Loop 필터입니다. 생략하면 모든 Loop를 포함하며, 0은 실행 전 이력을 선택합니다.
    step_id: 직접적인 Step 변경에 사용할 선택 사항인 UUID Step 필터입니다. 비어 있으면 Plan 전체 기록도 포함합니다.
<!-- /instruction:list_plan_revisions -->

## update_step

<!-- instruction:update_step -->
Step의 상태와 입력·출력 근거를 기록합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    step_id: 선택한 Plan의 상세 결과에서 얻은 Step ID입니다. 해당 Plan ID와 함께 사용합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.
    input_refs: 입력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. 유효하지 않은 문자열 항목은 건너뛰고 보고합니다.
    output_refs: 출력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. [] 형식의 전체 교체 배열은 허용하지 않습니다.
    expected_revision: 현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.
    loop_no: 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다.
<!-- /instruction:update_step -->

## resolve_targets

<!-- instruction:resolve_targets -->
Plan에 등록된 Holon 대상 집합을 조회합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    step_id: 컨텍스트를 검증하는 선택 사항인 Step ID입니다. Plan 대상을 재정의하지 않습니다.
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
