# Planning tools

## create_phase

<!-- instruction:create_phase -->
관련 Plan을 묶는 Phase를 생성하고 이름, 설명, 파일 연결과 관계를 기록합니다.

반환: status와 phase.phase_id를 반환합니다.

Args:
    name: Phase 이름을 문자열로 입력합니다. 빈 문자열은 사용할 수 없습니다.
    description: Phase의 목적이나 작업 범위를 문자열로 입력합니다.
    file_name: Phase가 속한 Rhino 파일명을 폴더 경로 없이 문자열로 입력합니다. 예: model.3dm.
    project_file_id: 등록된 프로젝트 파일 ID입니다. 같은 파일명이 여러 개일 때 project_info(sections=["project"], include_ids=true)에서 선택합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다.
    depends_on: 의존하는 Phase ID의 배열입니다. 각 값은 phase_로 시작합니다. 생략하면 빈 목록입니다.
    previous_id: 이전 Phase ID 하나를 입력합니다. 값은 phase_로 시작합니다.
<!-- /instruction:create_phase -->

## list_phases

<!-- instruction:list_phases -->
프로젝트의 Phase 목록과 각 Phase의 상태·Plan 수를 조회합니다.

반환: phases에 phase_id·name·status·plan_count·depends_on·previous_id를 반환합니다. total·limit·truncated가 반환 범위를 표시합니다.

Args:
    limit: 최대 Phase 수입니다. 범위는 1..500이며, 이 목록에는 offset 인수가 없습니다.
    field_groups: 선택 사항인 그룹은 description, scope, audit 또는 all입니다. 생략하거나 비어 있으면 요약과 ID를 유지합니다.
<!-- /instruction:list_phases -->

## update_phase

<!-- instruction:update_phase -->
Phase의 이름, 설명, 상태, 파일 연결과 관계를 수정합니다. 변경 결과와 건너뛴 패치 항목을 응답에서 확인합니다.

반환: changed와 phase, 건너뛴 항목의 issues를 반환합니다. status는 success, 변경과 건너뜀이 함께 있으면 partial_success, 건너뜀이 있고 변경이 없으면 no_change입니다.

Args:
    phase_id: list_phases.phases[].phase_id 또는 get_phase_plan_step.id에서 얻은 기존 Phase ID입니다.
    name: 선택 사항인 비어 있지 않은 대체 Phase 이름입니다.
    description: 선택 사항인 대체 설명입니다. 비어 있으면 지웁니다.
    file_name: 선택 사항인 저장할 파일명입니다. project_file_id를 생략한 경우 비어 있으면 연결 관계를 해제합니다.
    project_file_id: project_info(sections=["project"], include_ids=true)에서 얻은 기존 project.files[].project_file_id입니다. file_name도 함께 전달하면 두 값이 일치해야 합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.
    depends_on: Phase ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 충돌하거나 유효하지 않은 문자열 항목은 보고하고 건너뜁니다. 잘못된 타입은 요청 전체를 거부합니다.
    previous_id: 이전 Phase ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다.
<!-- /instruction:update_phase -->

## create_plan

<!-- instruction:create_plan -->
목표와 작업 목적에 맞는 템플릿으로 Plan과 Step을 생성합니다. 작업 공간은 set_working_plan으로 선택하고 회차는 execute_looping으로 시작합니다. 시공 상세 작업은 사용자가 요청한 범위에서 수행합니다.

반환: status와 plan.plan_id·loop_no·revision을 반환합니다. 최초 loop_no는 0입니다. 제목·상태와 Step ID는 Plan 상세에서 조회합니다.

Args:
    title: Plan 목록에서 사용할 비어 있지 않은 짧은 제목입니다.
    goal: 비어 있지 않은 전체 목표와 의도한 결과입니다.
    scope: 등록된 Step 템플릿 키이며 기본값은 house입니다. 기본 제공 키는 spatial_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior입니다. 등록된 사용자 지정 scope는 기본 제공 템플릿에 매핑됩니다. 작업 목적에 따라 선택합니다. 생성 시 Step이 실행되지는 않습니다.
    scene_id: 기존 방식의 단일 Scene ID입니다. scene_ids를 우선 사용합니다. 둘 다 전달하면 scene_ids의 첫 번째 항목과 같아야 합니다.
    phase_id: 선택 사항인 기존 Phase ID입니다. 비어 있으면 Plan을 Phase에 소속시키지 않습니다.
    scene_ids: 맥락을 설명하는 선택 사항인 기존 Scene ID 배열로, 여러 Scene을 포함할 수 있습니다. 생략하면 Scene 없이 작업할 수 있습니다. 형상 대상 집합을 확장하지는 않습니다.
    holon_ids: 이 Plan을 위해 명시적으로 지정하는 선택 사항인 등록된 Holon 대상입니다. Step에는 별도의 Holon 할당이 없습니다.
    depends_on: 선택 사항인 Plan ID 배열입니다(plan_ 접두사만 허용). 실행 순서를 강제하지 않고 의존성을 기록합니다.
    previous_id: 이전 Plan ID 하나를 입력합니다. 값은 plan_으로 시작합니다.
    parent_plan: 선택 사항인 상위 Plan ID 배열입니다.
    child_plan: 선택 사항인 하위 Plan ID 배열입니다.
<!-- /instruction:create_plan -->

## get_phase_plan_step

<!-- instruction:get_phase_plan_step -->
Phase, Plan 또는 Step 하나를 조회합니다. phase_id로 Phase를, plan_id로 Plan을, plan_id와 step_id로 Step을 선택합니다. Plan의 Holon 목록은 include_holons=true로 포함합니다. loop_no와 revision으로 과거 기록을 선택할 수 있습니다.

반환: 공통 id·type·status와 선택한 phase, plan 또는 step을 반환합니다. status는 pending/running/paused/completed/failed/blocked이며 조회 실패는 error입니다. Plan·Step의 read_only=true는 과거 기록입니다. Plan의 steps는 요약, Step의 input_refs·output_refs는 근거 문자열입니다.

Args:
    phase_id: Phase를 선택합니다. plan_id와 함께 사용할 수 없습니다.
    plan_id: Plan을 선택합니다. phase_id와 함께 사용할 수 없습니다. Step 하나만 읽으려면 step_id를 추가합니다.
    step_id: 선택 사항인 plan_id 내 Step ID입니다. Plan 요약 대신 해당 Step의 입력/출력 기록을 선택합니다.
    revision: 선택한 Loop 안에 저장된 선택적 리비전입니다. 생략하면 선택한 Loop의 최신 상태를 읽습니다. Phase에는 사용할 수 없습니다.
    include_holons: Plan의 holon_ids를 포함합니다. Plan 조회에만 유효하며 Phase 또는 Step에는 사용할 수 없습니다.
    loop_no: Plan/Step 조회에 사용할 선택 사항인 0 이상의 Loop 번호입니다. 생략하면 최신 Loop를 선택합니다. 0은 실행 전 기록을 읽습니다. Phase에는 사용할 수 없습니다.
<!-- /instruction:get_phase_plan_step -->

## list_plans

<!-- instruction:list_plans -->
프로젝트 또는 특정 Phase·Scene·상태에 해당하는 Plan 목록을 조회합니다.

반환: plans에 plan_id·title·scope·status·loop_no·revision을 반환합니다. total·limit·truncated가 반환 범위를 표시합니다.

Args:
    phase_id: 선택 사항인 Phase ID 필터입니다. 비어 있으면 여러 Phase를 범위로 합니다.
    scene_id: 선택 사항인 Scene ID 필터입니다. 비어 있으면 어떤 Scene에 속하든, Scene이 없든 모든 Plan을 포함합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 빈 문자열이면 모든 상태를 포함합니다.
    limit: 최대 Plan 수입니다. 범위는 1..500이며, 이 목록에는 offset 인수가 없습니다.
<!-- /instruction:list_plans -->

## update_plan

<!-- instruction:update_plan -->
Plan의 제목, 목표, Phase·Scene·Holon 관계, 상태와 산출물 참조를 수정합니다. Plan 상태는 Step 상태와 별도로 기록하며 completed는 사용자의 완료 결정 후 지정합니다. 실행된 Loop에서는 현재 loop_no와 expected_revision을 함께 입력합니다.

반환: changed, plan.plan_id·status·revision, issues를 반환합니다. success/partial_success/no_change를 구분하며 실제 변경이 있을 때만 리비전이 증가합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    goal: 선택 사항인 비어 있지 않은 대체 전체 목표입니다.
    phase_id: 선택 사항인 기존 Phase ID입니다. 비어 있으면 Phase 소속을 해제하고, 생략/null이면 유지합니다.
    scene_ids: 선택 사항인 대체 Scene ID 배열입니다. []이면 비우고 생략/null이면 유지합니다. Scene은 맥락을 설명하며 자동 편집 대상이 아닙니다.
    holon_ids: 선택 사항인 대체 Plan Holon 대상 배열입니다. []이면 비우고 생략/null이면 유지합니다.
    expected_revision: 현재 조회한 리비전 번호입니다. Loop 실행 후에는 loop_no와 함께 필수이며, 현재 값과 다르면 변경을 거부합니다. Loop 0에서는 생략할 수 있습니다.
    depends_on: Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.
    artifact_refs: 선택 사항인 대체 산출물 참조 문자열 배열입니다. []이면 비우고 생략/null이면 유지합니다.
    title: 선택 사항인 비어 있지 않은 대체 짧은 제목입니다.
    previous_id: 이전 Plan ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다.
    parent_plan: 선택 사항인 대체 상위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다.
    child_plan: 선택 사항인 대체 하위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다.
    loop_no: 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Plan이 Loop를 실행한 후에는 expected_revision과 함께 필수로 전달해야 합니다.
<!-- /instruction:update_plan -->

## list_plan_revisions

<!-- instruction:list_plan_revisions -->
Plan과 Loop의 저장 리비전 목록, 변경 작업과 관련 Step을 조회합니다. 반환된 loop_no와 revision을 함께 사용해 해당 기록을 읽습니다.

반환: revisions에 loop_no·revision·operation·step_id를 반환합니다. Plan 전체 변경의 step_id는 null입니다. audit 그룹은 created_at을 추가합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    limit: 최대 리비전 기록 수입니다. 범위는 1..500입니다.
    field_groups: 저장된 타임스탬프를 포함하려면 선택적으로 audit 또는 all을 사용합니다. 생략하거나 비어 있으면 loop_no, revision, operation 및 step_id를 반환합니다.
    loop_no: 선택 사항인 0 이상의 Loop 필터입니다. 생략하면 모든 Loop를 포함하며, 0은 실행 전 이력을 선택합니다.
    step_id: 직접적인 Step 변경에 사용할 선택 사항인 UUID Step 필터입니다. 비어 있으면 Plan 전체 기록도 포함합니다.
<!-- /instruction:list_plan_revisions -->

## update_step

<!-- instruction:update_step -->
Step의 상태와 입력·출력 근거를 기록합니다. Plan 상태는 별도로 유지됩니다. 실행된 Loop에서는 현재 loop_no와 expected_revision을 함께 입력하고, 응답에서 적용 결과와 건너뛴 항목을 확인합니다.

반환: changed, plan과 step의 ID·상태, plan.revision, issues를 반환합니다. success/partial_success/no_change를 구분합니다. issues는 field·operation·index·value·reason을 포함합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    step_id: 선택한 Plan의 상세 결과에서 얻은 Step ID입니다. 해당 Plan ID와 함께 사용합니다.
    status: pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.
    input_refs: 입력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. 유효하지 않은 문자열 항목은 건너뛰고 보고합니다.
    output_refs: 출력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. [] 형식의 전체 교체 배열은 허용하지 않습니다.
    expected_revision: 현재 조회한 리비전 번호입니다. Loop 실행 후에는 loop_no와 함께 필수이며, 현재 값과 다르면 변경을 거부합니다. Loop 0에서는 생략할 수 있습니다.
    loop_no: 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Plan이 Loop를 실행한 후에는 expected_revision과 함께 필수로 전달해야 합니다.
<!-- /instruction:update_step -->

## resolve_targets

<!-- instruction:resolve_targets -->
Plan에 등록된 Holon 대상 집합을 조회합니다. 빈 대상은 빈 목록으로 반환합니다. 현재 구성원과 형상은 후속 관찰에서 확인합니다.

반환: plan_id·step_id·revision, scene_ids·holon_ids·holons와 live_verified·source를 반환합니다. Holon ID는 등록된 대상 참조입니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    step_id: 컨텍스트를 검증하는 선택 사항인 Step ID입니다. Plan 대상을 재정의하지 않습니다.
    field_groups: 선택 사항: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 저장된 Plan 대상 ID를 반환합니다.
<!-- /instruction:resolve_targets -->

## get_selection_references

<!-- instruction:get_selection_references -->
현재 Rhino 선택 객체와 상위 Holon을 참조하는 Plan을 찾습니다. 객체 소유 관계는 현재 문서에서, Plan 관계는 저장된 기록에서 읽습니다. 저장된 일반 모델 컨텍스트가 필요합니다.

반환: objects·holons·plans와 총수·truncated, ownership_live_verified·references_live_verified를 반환합니다. 현재 소유 관계와 저장된 Plan 참조를 구분합니다.

Args:
    selection_limit: 검사할 선택된 Rhino 객체의 최대 개수이며, 범위는 1..200입니다.
    limit: 반환할 일치 Plan의 최대 개수이며, 범위는 1..500입니다.
    field_groups: 선택 사항인 그룹: steps, references, geometry, artifacts, description, scope, audit 또는 all. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:get_selection_references -->
