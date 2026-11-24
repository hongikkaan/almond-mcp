"""Discriminated planning requests keep each target's accepted fields explicit."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from almond_mcp.features.planning.updates import StringListPatch


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreatePhase(PlanningRequest):
    target: Literal['phase']
    name: str = Field(..., description='공백만 있는 이름은 거부.')
    description: str = ''
    file_name: str | list[str] = Field('', description='context_04-get_project_info tool의 `project.files`에 등록된 파일명.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] = 'pending'
    depends_on: list[str] | None = Field(None, description='같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음.')
    previous_id: str | None = Field(None, description='Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음.')

class CreatePlan(PlanningRequest):
    target: Literal['plan']
    title: str = Field(..., description='공백만 있는 제목은 거부.')
    goal: str = Field(..., description='공백만 있는 목표는 거부.')
    scope: str = Field('house', description='Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능.')
    scene_id: str = Field('', description='단일 Scene용 호환 입력. `scene_ids`와 함께 지정하면 배열의 첫 ID와 일치해야 함.')
    phase_id: str = ''
    scene_ids: list[str] | None = Field(None, description='생략하거나 `null`이면 `scene_id` 사용.')
    holon_ids: list[str] | None = None
    depends_on: list[str] | None = Field(None, description='결과나 결정에 의존하는 관련 Plan. 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음.')
    previous_id: str | None = Field(None, description='작업 순서상 직전 Plan. Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음.')
    parent_plan: list[str] | None = Field(None, description='상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음.')
    child_plan: list[str] | None = Field(None, description='하위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음.')

class GetPhase(PlanningRequest):
    target: Literal['phase']
    phase_id: str
    include_details: StrictBool = False

class GetPlan(PlanningRequest):
    target: Literal['plan']
    plan_id: str
    revision: StrictInt | None = Field(None, description='생략·`null`은 선택한 회차의 최신 상태.')
    include_details: StrictBool = False
    loop_no: StrictInt | None = Field(None, description='0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.')

class GetStep(PlanningRequest):
    target: Literal['step']
    plan_id: str
    step_id: str = Field(..., description='같은 요청의 `plan_id`에 속한 Step만 조회 가능.')
    revision: StrictInt | None = Field(None, description='생략·`null`은 선택한 회차의 최신 상태.')
    include_details: StrictBool = False
    loop_no: StrictInt | None = Field(None, description='0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.')

class ListPhases(PlanningRequest):
    target: Literal['phase']
    limit: StrictInt = Field(50, description='1~500.')
    field_groups: list[str] | None = Field(None, description='`description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환.')

class ListPlans(PlanningRequest):
    target: Literal['plan']
    phase_id: str = Field('', description='생략하거나 비우면 Phase 소속 여부와 관계없이 조회.')
    scene_id: str = Field('', description='생략하거나 비우면 Scene 연결 여부와 관계없이 조회.')
    status: Literal['', 'pending', 'running', 'paused', 'completed', 'failed', 'blocked'] = Field('', description='생략하거나 비우면 상태 필터를 적용하지 않음.')
    limit: StrictInt = Field(50, description='1~500.')

class UpdatePhase(PlanningRequest):
    target: Literal['phase']
    phase_id: str = Field(..., description='plan_08-list tool의 `request.target="phase"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 Phase `id`.')
    name: str | None = Field(None, description='빈 이름은 거부.')
    description: str | None = Field(None, description='빈 문자열은 설명 삭제.')
    file_name: str | list[str] | None = Field(None, description='context_04-get_project_info tool의 `project.files`에 등록된 파일명. 빈 문자열 또는 `[]`는 연결 해제, 생략·`null`은 연결 유지.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = None
    depends_on: StringListPatch | None = Field(None, description='같은 종류의 Phase ID만 사용. 대상 존재·순환·완료 여부는 검사하지 않음.')
    previous_id: str | None = Field(None, description='빈 문자열은 연결 해제.')

class UpdatePlan(PlanningRequest):
    target: Literal['plan']
    plan_id: str = Field(..., description='plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id')
    goal: str | None = Field(None, description='빈 목표는 거부.')
    phase_id: str | None = Field(None, description='빈 문자열은 Phase 소속 해제.')
    scene_ids: list[str] | None = None
    holon_ids: list[str] | None = None
    expected_revision: StrictInt | None = Field(None, description='현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정.')
    depends_on: StringListPatch | None = Field(None, description='결과나 결정에 의존하는 관련 Plan. Plan ID 형식만 검사. 대상 존재·자기 참조·순환은 확인하지 않으며 순서나 완료도 강제하지 않음.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = Field(None, description='`completed`는 사용자의 완료 결정 후 지정.')
    artifact_refs: list[str] | None = None
    title: str | None = Field(None, description='빈 제목은 거부.')
    previous_id: str | None = Field(None, description='작업 순서상 직전 Plan. 빈 문자열은 연결 해제.')
    parent_plan: list[str] | None = Field(None, description='상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.')
    child_plan: list[str] | None = Field(None, description='상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.')
    loop_no: StrictInt | None = Field(None, description='현재 회차만 허용. 생략하면 현재 회차 적용.')

class UpdateStep(PlanningRequest):
    target: Literal['step']
    plan_id: str = Field(..., description='plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id')
    step_id: str = Field(..., description='plan_05-get tool의 Plan 상세에서 확인한 Step ID.')
    status: Literal['pending', 'running', 'paused', 'completed', 'failed', 'blocked'] | None = None
    input_refs: StringListPatch | None = None
    output_refs: StringListPatch | None = None
    takeaways: str | None = Field(None, description='다음 작업에 넘길 핵심 결론과 확인 사항. 빈 문자열은 내용 삭제.')
    design_rationale: str | None = Field(None, description='설계 결정의 이유와 근거. 빈 문자열은 내용 삭제.')
    expected_revision: StrictInt | None = Field(None, description='현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정.')
    loop_no: StrictInt | None = Field(None, description='현재 회차만 허용. 생략하면 현재 회차 적용.')


class ListSteps(PlanningRequest):
    target: Literal["step"]
    plan_id: str
    revision: StrictInt | None = Field(None, description='생략·`null`은 선택한 회차의 최신 상태. 지정하면 읽기 전용 스냅샷.')
    loop_no: StrictInt | None = Field(None, description='0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.')
    limit: StrictInt = Field(50, ge=1, le=500, description='1~500. 정의된 순서의 앞부분을 반환.')


CreateRequest = Annotated[CreatePhase | CreatePlan, Field(discriminator="target")]
GetRequest = Annotated[GetPhase | GetPlan | GetStep, Field(discriminator="target")]
ListRequest = Annotated[ListPhases | ListPlans | ListSteps, Field(discriminator="target")]
UpdateRequest = Annotated[UpdatePhase | UpdatePlan | UpdateStep, Field(discriminator="target")]
