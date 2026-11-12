"""Discriminated planning requests keep each target's accepted fields explicit."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from almond_mcp.features.planning.updates import StringListPatch


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreatePhase(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    name: str = Field(..., description='Phase 이름을 문자열로 입력합니다. 빈 문자열은 사용할 수 없습니다.')
    description: str = Field('', description='Phase의 목적이나 작업 범위를 문자열로 입력합니다.')
    file_name: str | list[str] = Field('', description='이 Phase가 속한 Rhino 파일명입니다. 문자열 하나 또는 문자열 배열로 입력합니다.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] = Field('pending', description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다.')
    depends_on: list[str] | None = Field(None, description='이 Phase가 의존하는 Phase ID 목록입니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다.')
    previous_id: str | None = Field(None, description='이전 Phase의 ID입니다.')

class CreatePlan(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    title: str = Field(..., description='Plan 목록에서 사용할 비어 있지 않은 짧은 제목입니다.')
    goal: str = Field(..., description='비어 있지 않은 전체 목표와 의도한 결과입니다.')
    scope: str = Field('house', description='작업 목적에 맞는 Step 템플릿을 선택합니다: spatial_development, drawing_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록한 사용자 템플릿도 사용할 수 있습니다.')
    scene_id: str = Field('', description='기존 방식의 단일 Scene ID입니다. scene_ids를 우선 사용합니다. 둘 다 전달하면 scene_ids의 첫 번째 항목과 같아야 합니다.')
    phase_id: str = Field('', description='선택 사항인 기존 Phase ID입니다. 비어 있으면 Plan을 Phase에 소속시키지 않습니다.')
    scene_ids: list[str] | None = Field(None, description='Plan의 작업 맥락이 되는 기존 Scene ID 배열입니다. 생략하면 Scene 없이 생성합니다.')
    holon_ids: list[str] | None = Field(None, description='이 Plan에서 작업할 기존 Holon ID 배열입니다.')
    depends_on: list[str] | None = Field(None, description='이 Plan이 의존하는 Plan ID 목록입니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다.')
    previous_id: str | None = Field(None, description='이전 Plan의 ID입니다.')
    parent_plan: list[str] | None = Field(None, description='이 Plan에 기록할 선택 사항인 상위 Plan ID 배열입니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다.')
    child_plan: list[str] | None = Field(None, description='이 Plan에 기록할 선택 사항인 하위 Plan ID 배열입니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다.')

class GetPhase(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    phase_id: str = Field(..., description='조회할 Phase ID입니다.')
    include_details: StrictBool = Field(False, description='false이면 식별·상태 요약, true이면 선택한 Phase·Plan·Step의 상세 작업 기록을 함께 조회합니다.')

class GetPlan(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.')
    revision: StrictInt | None = Field(None, description='선택한 Loop 안에 저장된 선택적 리비전입니다. 생략하면 선택한 Loop의 최신 상태를 읽습니다. Phase에는 사용할 수 없습니다.')
    include_details: StrictBool = Field(False, description='false이면 식별·상태 요약, true이면 선택한 Phase·Plan·Step의 상세 작업 기록을 함께 조회합니다.')
    loop_no: StrictInt | None = Field(None, description='Plan/Step 조회에 사용할 선택 사항인 0 이상의 Loop 번호입니다. 생략하면 최신 Loop를 선택합니다. 0은 실행 전 기록을 읽습니다. Phase에는 사용할 수 없습니다.')

class GetStep(PlanningRequest):
    target: Literal['step'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.')
    step_id: str = Field(..., description='선택한 Plan에 속한 Step ID입니다.')
    revision: StrictInt | None = Field(None, description='선택한 Loop 안에 저장된 선택적 리비전입니다. 생략하면 선택한 Loop의 최신 상태를 읽습니다. Phase에는 사용할 수 없습니다.')
    include_details: StrictBool = Field(False, description='false이면 식별·상태 요약, true이면 선택한 Phase·Plan·Step의 상세 작업 기록을 함께 조회합니다.')
    loop_no: StrictInt | None = Field(None, description='Plan/Step 조회에 사용할 선택 사항인 0 이상의 Loop 번호입니다. 생략하면 최신 Loop를 선택합니다. 0은 실행 전 기록을 읽습니다. Phase에는 사용할 수 없습니다.')

class ListPhases(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    limit: StrictInt = Field(50, description='최대 Phase 수입니다. 범위는 1..500입니다.')
    field_groups: list[str] | None = Field(None, description='선택 사항인 그룹은 description, scope, audit 또는 all입니다. 생략하거나 비어 있으면 요약과 ID를 유지합니다.')

class ListPlans(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    phase_id: str = Field('', description='선택 사항인 Phase ID 필터입니다. 비어 있으면 여러 Phase를 범위로 합니다.')
    scene_id: str = Field('', description='선택 사항인 Scene ID 필터입니다. 비어 있으면 어떤 Scene에 속하든, Scene이 없든 모든 Plan을 포함합니다.')
    status: Literal['', 'pending', 'running', 'paused', 'completed', 'failed', 'blocked'] = Field('', description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 빈 문자열이면 모든 상태를 포함합니다.')
    limit: StrictInt = Field(50, description='최대 Plan 수입니다. 범위는 1..500입니다.')

class UpdatePhase(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    phase_id: str = Field(..., description='plan_08-list tool에 request.target=phase로 조회한 phases[].phase_id 또는 plan_05-get tool의 id에서 얻은 기존 Phase ID입니다.')
    name: str | None = Field(None, description='선택 사항인 비어 있지 않은 대체 Phase 이름입니다.')
    description: str | None = Field(None, description='선택 사항인 대체 설명입니다. 비어 있으면 지웁니다.')
    file_name: str | list[str] | None = Field(None, description='이 Phase가 속한 Rhino 파일명입니다. 문자열 하나 또는 문자열 배열로 입력합니다. [] 또는 ""는 연결 해제, 생략/null은 유지입니다.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = Field(None, description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.')
    depends_on: StringListPatch | None = Field(None, description='Phase ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 충돌하거나 유효하지 않은 문자열 항목은 보고하고 건너뜁니다. 잘못된 타입은 요청 전체를 거부합니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다.')
    previous_id: str | None = Field(None, description='이전 Phase ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다.')

class UpdatePlan(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.')
    goal: str | None = Field(None, description='선택 사항인 비어 있지 않은 대체 전체 목표입니다.')
    phase_id: str | None = Field(None, description='선택 사항인 기존 Phase ID입니다. 비어 있으면 Phase 소속을 해제하고, 생략/null이면 유지합니다.')
    scene_ids: list[str] | None = Field(None, description='Plan의 작업 맥락이 되는 기존 Scene ID 배열로 교체합니다. []이면 비우고 생략/null이면 유지합니다.')
    holon_ids: list[str] | None = Field(None, description='선택 사항인 대체 Plan Holon 대상 배열입니다. []이면 비우고 생략/null이면 유지합니다.')
    expected_revision: StrictInt | None = Field(None, description='현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.')
    depends_on: StringListPatch | None = Field(None, description='Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = Field(None, description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. completed는 사용자의 완료 결정 후 지정합니다. 생략/null은 유지입니다.')
    artifact_refs: list[str] | None = Field(None, description='선택 사항인 대체 산출물 참조 문자열 배열입니다. []이면 비우고 생략/null이면 유지합니다.')
    title: str | None = Field(None, description='선택 사항인 비어 있지 않은 대체 짧은 제목입니다.')
    previous_id: str | None = Field(None, description='이전 Plan ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다.')
    parent_plan: list[str] | None = Field(None, description='이 Plan에 기록할 대체 상위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다.')
    child_plan: list[str] | None = Field(None, description='이 Plan에 기록할 대체 하위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다.')
    loop_no: StrictInt | None = Field(None, description='선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다.')

class UpdateStep(PlanningRequest):
    target: Literal['step'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.')
    step_id: str = Field(..., description='선택한 Plan의 상세 결과에서 얻은 Step ID입니다. 해당 Plan ID와 함께 사용합니다.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = Field(None, description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.')
    input_refs: StringListPatch | None = Field(None, description='입력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. 유효하지 않은 문자열 항목은 건너뛰고 보고합니다.')
    output_refs: StringListPatch | None = Field(None, description='출력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. [] 형식의 전체 교체 배열은 허용하지 않습니다.')
    expected_revision: StrictInt | None = Field(None, description='현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.')
    loop_no: StrictInt | None = Field(None, description='선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다.')


class ListSteps(PlanningRequest):
    target: Literal["step"] = Field(description="Step 목록을 선택합니다.")
    plan_id: str = Field(description="Step 목록을 읽을 기존 Plan ID입니다.")
    revision: StrictInt | None = Field(None, description="선택한 Loop 안의 리비전입니다. 생략하면 해당 Loop의 최신 상태를 읽습니다.")
    loop_no: StrictInt | None = Field(None, description="선택할 0 이상의 Loop 번호입니다. 생략하면 최신 Loop, 0은 실행 전 기록입니다.")
    limit: StrictInt = Field(50, ge=1, le=500, description="정의된 순서대로 반환할 최대 Step 수입니다. 범위는 1..500입니다.")


CreateRequest = Annotated[CreatePhase | CreatePlan, Field(discriminator="target")]
GetRequest = Annotated[GetPhase | GetPlan | GetStep, Field(discriminator="target")]
ListRequest = Annotated[ListPhases | ListPlans | ListSteps, Field(discriminator="target")]
UpdateRequest = Annotated[UpdatePhase | UpdatePlan | UpdateStep, Field(discriminator="target")]
