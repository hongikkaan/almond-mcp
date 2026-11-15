"""Discriminated planning requests keep each target's accepted fields explicit."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from almond_mcp.features.planning.updates import StringListPatch


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreatePhase(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    name: str = Field(..., description='공백만 있는 이름은 허용하지 않습니다.')
    description: str = Field('', description='Phase의 목적이나 작업 범위를 문자열로 입력합니다.')
    file_name: str | list[str] = Field('', description='연결할 파일명 하나 또는 배열. 생략하면 파일 연결 없음.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] = Field('pending', description='생략하면 pending.')
    depends_on: list[str] | None = Field(None, description='같은 종류의 ID 형식만 검사하며 대상 존재·순환·작업 순서를 검증하거나 강제하지 않습니다.')
    previous_id: str | None = Field(None, description='이전 Phase 참조. 같은 종류의 ID 형식을 검사하며 존재는 검증하지 않습니다.')

class CreatePlan(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    title: str = Field(..., description='공백만 있는 제목은 허용하지 않습니다.')
    goal: str = Field(..., description='공백만 있는 목표는 허용하지 않습니다.')
    scope: str = Field('house', description='Step 템플릿. 생략하면 house. 기본 제공: spatial_development, drawing_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록된 사용자 템플릿도 사용 가능.')
    scene_id: str = Field('', description='단일 Scene의 호환 입력. scene_ids와 함께 쓰면 첫 항목과 같아야 합니다.')
    phase_id: str = Field('', description='기존 Phase ID. 생략·빈 문자열은 소속 없음.')
    scene_ids: list[str] | None = Field(None, description='기존 Scene ID 배열. 생략하면 scene_id를 사용하고 둘 다 없으면 Scene 연결 없음.')
    holon_ids: list[str] | None = Field(None, description='작업 대상인 기존 Holon ID 배열.')
    depends_on: list[str] | None = Field(None, description='같은 종류의 ID 형식만 검사하며 대상 존재·순환·작업 순서를 검증하거나 강제하지 않습니다.')
    previous_id: str | None = Field(None, description='이전 Plan 참조. 같은 종류의 ID 형식을 검사하며 존재는 검증하지 않습니다.')
    parent_plan: list[str] | None = Field(None, description='기록할 상위 Plan ID. 상대 Plan을 자동 수정하거나 존재를 검증하지 않습니다.')
    child_plan: list[str] | None = Field(None, description='기록할 하위 Plan ID. 상대 Plan을 자동 수정하거나 존재를 검증하지 않습니다.')

class GetPhase(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    phase_id: str = Field(..., description='조회할 Phase ID입니다.')
    include_details: StrictBool = Field(False, description='기본 false. true이면 Phase 상세를 포함합니다.')

class GetPlan(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.')
    revision: StrictInt | None = Field(None, description='선택한 Loop의 리비전. 생략·null이면 해당 Loop의 최신 상태; 지정하면 읽기 전용 스냅샷.')
    include_details: StrictBool = Field(False, description='기본 false. true이면 Plan 상세와 Step 요약을 포함합니다.')
    loop_no: StrictInt | None = Field(None, description='0 이상의 Loop 번호. 생략·null이면 최신 Loop, 0은 실행 전 기록.')

class GetStep(PlanningRequest):
    target: Literal['step'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.')
    step_id: str = Field(..., description='해당 Plan에 속한 Step ID.')
    revision: StrictInt | None = Field(None, description='선택한 Loop의 리비전. 생략·null이면 해당 Loop의 최신 상태; 지정하면 읽기 전용 스냅샷.')
    include_details: StrictBool = Field(False, description='기본 false. true이면 이 Step의 유형과 입출력 참조를 포함합니다.')
    loop_no: StrictInt | None = Field(None, description='0 이상의 Loop 번호. 생략·null이면 최신 Loop, 0은 실행 전 기록.')

class ListPhases(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    limit: StrictInt = Field(50, description='1~500, 기본 50.')
    field_groups: list[str] | None = Field(None, description='description: 설명, scope: 연결 파일, audit: 생성·수정 시각, all: 전체. 생략·빈 배열은 요약.')

class ListPlans(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    phase_id: str = Field('', description='생략·빈 문자열이면 Phase 소속 여부와 관계없이 포함.')
    scene_id: str = Field('', description='생략·빈 문자열이면 Scene 소속 여부와 관계없이 포함.')
    status: Literal['', 'pending', 'running', 'paused', 'completed', 'failed', 'blocked'] = Field('', description='생략·빈 문자열이면 모든 상태.')
    limit: StrictInt = Field(50, description='1~500, 기본 50.')

class UpdatePhase(PlanningRequest):
    target: Literal['phase'] = Field(description="작업할 대상 종류입니다.")
    phase_id: str = Field(..., description='plan_08-list tool에 request.target=phase로 조회한 phases[].phase_id 또는 plan_05-get tool의 id에서 얻은 기존 Phase ID입니다.')
    name: str | None = Field(None, description='빈 이름 불가.')
    description: str | None = Field(None, description='빈 문자열은 설명 삭제.')
    file_name: str | list[str] | None = Field(None, description='빈 문자열 또는 []는 연결 해제.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = Field(None, description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.')
    depends_on: StringListPatch | None = Field(None, description='동일 종류 ID의 add/remove 패치. 존재·순환·완료 여부는 검사하지 않음.')
    previous_id: str | None = Field(None, description='빈 문자열은 연결 해제.')

class UpdatePlan(PlanningRequest):
    target: Literal['plan'] = Field(description="작업할 대상 종류입니다.")
    plan_id: str = Field(..., description='plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.')
    goal: str | None = Field(None, description='빈 목표 불가.')
    phase_id: str | None = Field(None, description='빈 문자열은 소속 해제.')
    scene_ids: list[str] | None = Field(None, description='Plan의 작업 맥락이 되는 기존 Scene ID 배열로 교체합니다. []이면 비우고 생략/null이면 유지합니다.')
    holon_ids: list[str] | None = Field(None, description='선택 사항인 대체 Plan Holon 대상 배열입니다. []이면 비우고 생략/null이면 유지합니다.')
    expected_revision: StrictInt | None = Field(None, description='현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.')
    depends_on: StringListPatch | None = Field(None, description='Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = Field(None, description='pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. completed는 사용자의 완료 결정 후 지정합니다. 생략/null은 유지입니다.')
    artifact_refs: list[str] | None = Field(None, description='선택 사항인 대체 산출물 참조 문자열 배열입니다. []이면 비우고 생략/null이면 유지합니다.')
    title: str | None = Field(None, description='빈 제목 불가.')
    previous_id: str | None = Field(None, description='빈 문자열은 연결 해제.')
    parent_plan: list[str] | None = Field(None, description='상호 관계 자동 변경 및 참조 대상 존재 검증 없음.')
    child_plan: list[str] | None = Field(None, description='상호 관계 자동 변경 및 참조 대상 존재 검증 없음.')
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
    revision: StrictInt | None = Field(None, description='선택한 Loop의 저장 리비전. 생략·null은 최신 상태; 지정하면 읽기 전용 스냅샷.')
    loop_no: StrictInt | None = Field(None, description='0 이상의 Loop 번호. 생략·null은 최신, 0은 실행 전 기록.')
    limit: StrictInt = Field(50, ge=1, le=500, description='1~500, 기본 50. 지정 순서의 앞부분부터 반환.')


CreateRequest = Annotated[CreatePhase | CreatePlan, Field(discriminator="target")]
GetRequest = Annotated[GetPhase | GetPlan | GetStep, Field(discriminator="target")]
ListRequest = Annotated[ListPhases | ListPlans | ListSteps, Field(discriminator="target")]
UpdateRequest = Annotated[UpdatePhase | UpdatePlan | UpdateStep, Field(discriminator="target")]
