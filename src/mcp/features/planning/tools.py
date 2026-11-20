"""Register Phase, Plan and Step tools without owning server state."""
from almond_mcp.tool_response import error_payload
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.features.components.tools import send_component_request
from almond_mcp.query_output import compact_ack
from almond_mcp.query_output import validate_field_groups, InvalidFieldGroups
from almond_mcp.features.planning.completion import update_step
from almond_mcp.features.planning.output import (
    GROUPS, PHASE_GROUPS, REVISION_GROUPS, TARGET_GROUPS, project,
    encode, phase_detail, plan_detail, step_detail, update_ack,
)
from almond_mcp.features.planning.requests import CreateRequest, GetRequest, ListRequest, UpdateRequest
from almond_mcp.tool_declarations import public_tool

import json

from pydantic import StrictInt


PHASE_ACK_FIELDS = {"phase_id"}
PLAN_ACK_FIELDS = {"plan_id", "loop_no", "revision"}


def register(mcp, context):
    """Register planning tools against the calling server's live context."""

    @public_tool(mcp, wrapped=True)
    @holon_output
    def create_planning(request: CreateRequest) -> str:
        """Phase 또는 Plan을 생성합니다. Plan은 scope에 맞는 Step을 자동으로 만들며 **작업을 실행하지 않습니다.**

        `result`는 생성된 `phase_id` 또는 `plan_id`와 상태를 담은 JSON 문자열입니다. 생성 오류도 `result.status`에 반환될 수 있습니다. Plan은 초기 loop_no=0, revision=1로 생성됩니다. 생성된 Plan의 Step은 plan_05-get tool에서 확인할 수 있습니다.

        Args:
            request: target으로 phase 또는 plan을 선택하고 해당 생성 정보를 입력합니다. Step 독립 생성은 제공하지 않습니다.
        """
        try:
            store = context.retrieval_store
            if request.target == "phase":
                phase = store.create_phase(request.name, request.description, request.file_name,
                    request.status, request.depends_on, request.previous_id)
                return json.dumps({"status": "success", "phase": compact_ack(phase, PHASE_ACK_FIELDS)})
            plan = store.create_plan(goal=request.goal, title=request.title, scope=request.scope,
                scene_id=request.scene_id, phase_id=request.phase_id, scene_ids=request.scene_ids,
                component_ids=request.holon_ids, depends_on=request.depends_on,
                previous_id=request.previous_id, parent_plan=request.parent_plan, child_plan=request.child_plan)
            return json.dumps({"status": "success", "plan": compact_ack(plan, PLAN_ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    @holon_output
    def get_planning(request: GetRequest) -> str:
        """Phase, Plan 또는 Step의 작업 기록을 조회합니다. 기본값은 식별·상태 요약이며, include_details=true이면 선택한 대상의 상세를 함께 반환합니다. Plan 상세에는 Step 요약이, Step 상세에는 입출력 참조와 Takeaways·Design rationale이 포함됩니다. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로를 열어 내용을 확인합니다.

        `result`는 조회 결과 또는 오류를 담은 JSON 문자열입니다. 성공 시 status는 대상의 작업 상태이며, 오류는 status=error입니다. Plan과 Step은 `loop_no`·`revision`·`read_only`를 함께 반환합니다. **revision을 명시하면 현재 번호여도 읽기 전용 스냅샷**입니다.

        Args:
            request: target으로 phase, plan, step을 선택하고 해당 ID를 입력합니다. include_details로 상세 기록을 선택합니다.
        """
        try:
            store = context.retrieval_store
            if request.target == "phase":
                phase = store.get_phase(request.phase_id)
                if phase is None:
                    raise KeyError(f"Unknown phase_id: {request.phase_id}")
                return encode(phase_detail(phase, request.include_details))
            if request.target == "step":
                step = store.get_step(request.plan_id, request.step_id, request.revision, request.loop_no)
                if step is None:
                    raise KeyError(f"Unknown Plan/Step/Loop/revision: {request.plan_id}, {request.step_id}, {request.loop_no}, {request.revision}")
                return encode(step_detail(step, request.include_details, historical=step["read_only"]))
            plan = store.get_plan(request.plan_id, request.revision, request.loop_no)
            if plan is None:
                raise KeyError(f"Unknown Plan/Loop/revision: {request.plan_id}, {request.loop_no}, {request.revision}")
            return encode(plan_detail(plan, request.include_details, historical=plan["read_only"]))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    @holon_output
    def list_planning(request: ListRequest) -> str:
        """Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록을 조회합니다.

        `result`는 상태와 `phases`·`plans`·`steps` 중 해당 목록을 담은 JSON 문자열입니다. `total`과 `truncated`는 목록 크기와 잘림 여부를 나타냅니다. **offset은 지원하지 않으며** `limit`은 최대 500입니다. Step 조회는 같은 스냅샷의 `loop_no`·`revision`과 `read_only`를 함께 반환합니다.

        Args:
            request: target으로 phase, plan, step을 선택합니다. Step에는 plan_id가 필요하며 대상별 필터와 limit을 지정합니다.
        """
        try:
            if request.target == "phase":
                validate_field_groups(request.field_groups, PHASE_GROUPS)
            store = context.retrieval_store
            if request.target == "phase":
                return encode(project({"status": "success", **store.list_phases(request.limit)}, request.field_groups))
            if request.target == "plan":
                return encode({"status": "success", **store.list_plans(
                    request.phase_id, request.scene_id, request.status, request.limit)})
            # One snapshot supplies both ordered rows and their revision identity.
            plan = store.get_plan(request.plan_id, request.revision, request.loop_no)
            if plan is None:
                raise KeyError(f"Unknown Plan/Loop/revision: {request.plan_id}, {request.loop_no}, {request.revision}")
            steps = [{key: step[key] for key in ("step_id", "step_type", "name", "status", "loop_no")}
                     for step in plan["steps"][:request.limit]]
            return encode({"status": "success", "plan_id": plan["plan_id"], "loop_no": plan["loop_no"],
                "revision": plan["revision"], "read_only": plan["read_only"], "steps": steps,
                "total": len(plan["steps"]), "limit": request.limit, "truncated": len(plan["steps"]) > request.limit})
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @public_tool(mcp, wrapped=True)
    @holon_output
    def update_planning(request: UpdateRequest) -> str:
        """Phase·Plan의 작업 정보 또는 Step의 상태, 입출력 참조, Takeaways·Design rationale을 수정합니다. Plan·Step은 현재 Loop만 변경할 수 있습니다.

        `depends_on`, `input_refs`, `output_refs`는 add/remove 패치이며 Plan의 대상·산출물·상하위 관계 배열은 전체 교체합니다. 생략 또는 null은 유지, 교체 배열의 []는 비웁니다. `takeaways`와 `design_rationale`은 빈 문자열로 비웁니다.

        응답은 JSON 문자열입니다. `changed`는 실제 변경 여부, `issues`는 건너뛴 항목입니다. 중복·충돌 등 적용하지 못한 패치 항목은 `issues`에 기록하며, 일부만 적용되면 `partial_success`를 반환합니다. Loop 실행 후 `expected_revision`을 지정할 때는 `loop_no`도 함께 지정합니다.

        Step 상태를 `completed`로 지정하면 다른 수정 필드와 함께 한 번의 요청으로 저장합니다.

        Args:
            request: target으로 phase, plan, step을 선택하고 해당 ID와 바꿀 필드만 입력합니다. Step은 상태·입출력 참조·판단 기록 중 필요한 필드만 갱신합니다.
        """
        try:
            store = context.retrieval_store
            if request.target == "phase":
                return json.dumps(update_ack(store.edit_phase(request.phase_id, request.name,
                    request.description, request.file_name, request.status,
                    request.depends_on, request.previous_id), "phase"))
            if request.target == "step":
                return json.dumps(update_step(store, request,
                    lambda payload, **options: context._send_and_receive(payload, **options)), ensure_ascii=False)
            return json.dumps(update_ack(store.edit_plan(request.plan_id,
                goal=request.goal, phase_id=request.phase_id, scene_ids=request.scene_ids,
                component_ids=request.holon_ids, expected_revision=request.expected_revision,
                depends_on=request.depends_on, status=request.status, artifact_refs=request.artifact_refs,
                title=request.title, previous_id=request.previous_id, parent_plan=request.parent_plan,
                child_plan=request.child_plan, loop_no=request.loop_no), "plan"))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    @holon_output
    def list_plan_revisions(plan_id: str, limit: StrictInt = 50, field_groups: list[str] | None = None,
                            loop_no: StrictInt | None = None, step_id: str = "") -> str:
        """Plan의 저장 리비전 목록을 최신 회차·리비전 순으로 조회합니다. Loop나 Step으로 필터링할 수 있으며, Step 필터는 그 Step의 직접 변경만 포함합니다.

        result는 revisions, total, limit, truncated를 담은 JSON 문자열입니다. offset은 지원하지 않으며 limit은 최대 500입니다. 선택한 과거 기록은 plan_05-get tool에서 같은 loop_no와 revision으로 조회합니다.

        Args:
            plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
            limit: 1~500, 기본 50.
            field_groups: audit 또는 all: 생성 시각 포함. 생략·빈 배열: 기본 필드.
            loop_no: 생략·null: 전체. 0: 실행 전 기록.
            step_id: 생략·빈 문자열: Plan 전체.
        """
        try:
            validate_field_groups(field_groups, REVISION_GROUPS)
            return encode(project({"status": "success", **context.retrieval_store.list_plan_revisions(plan_id, limit, loop_no, step_id)}, field_groups))
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    @holon_output
    def resolve_targets(plan_id: str, step_id: str = "", field_groups: list[str] | None = None) -> str:
        """Plan에 등록된 Scene·Holon 대상과 선택한 Holon 정보를 조회합니다. Step 지정 시 해당 Plan 소속 여부를 확인하지만 대상은 Plan 기준입니다. Scene의 모든 Holon을 자동으로 확장하지 않습니다.

        저장된 대상 조회이며 Rhino의 현재 구성원은 검증하지 않습니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.

        Args:
            plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
            step_id: Plan 소속 검사. 생략 시 Plan 기준.
            field_groups: references, geometry, scope, audit, all. 생략·빈 배열: 기본 요약.
        """
        try:
            validate_field_groups(field_groups, TARGET_GROUPS)
            return encode(project({"status": "success", **context.retrieval_store.resolve_targets(plan_id, step_id)}, field_groups))
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))

    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False}, errors=True)
    @holon_output
    def get_selection_references(selection_limit: StrictInt = 50, limit: StrictInt = 50,
                                 field_groups: list[str] | None = None) -> str:
        """현재 선택된 Rhino 객체의 소속 Holon과 상위 Holon을 참조하는 Plan을 찾습니다. 저장된 문서의 일반 모델에서 사용합니다.

        Plan의 일치 Holon과 Plan 전체 대상은 다를 수 있습니다. 선택 객체와 Plan 목록의 잘림 여부는 각각 selection_truncated와 truncated로 확인합니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.

        Args:
            selection_limit: 검사할 선택 객체 수: 1..200.
            limit: 반환할 Plan 수: 1..500.
            field_groups: steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열: 요약.
        """
        try:
            validate_field_groups(field_groups, GROUPS)
            if type(selection_limit) is not int or not 1 <= selection_limit <= 200:
                raise ValueError("selection_limit must be an integer from 1 to 200.")
            context.retrieval_store._generation_limit(limit)
            live = json.loads(context._send_and_receive(json.dumps({
                "type": "get_rhino_context", "sections": ["document", "selection"],
                "selection_limit": selection_limit,
            }).encode("utf-8")))
            if live.get("status") != "success":
                return json.dumps(live)
            document, selection = live.get("document"), live.get("selection")
            if not isinstance(document, dict) or not isinstance(selection, dict):
                raise ValueError("Live document/selection observation is incomplete.")
            result = context.retrieval_store.selection_references(
                document["path"], [obj["id"] for obj in selection["objects"]], limit,
                native_observe=lambda req: send_component_request(context._send_and_receive, req),
            )
            result["selection_total"] = selection["total"]
            result["selection_truncated"] = selection["truncated"]
            return encode(project({"status": "success", **result}, field_groups))
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps({**error_payload(str(exc)), **getattr(exc, "native_result", {})}, ensure_ascii=False)

    return {
        "create_planning": create_planning,
        "get_planning": get_planning,
        "list_planning": list_planning,
        "update_planning": update_planning,
        "list_plan_revisions": list_plan_revisions,
        "resolve_targets": resolve_targets,
        "get_selection_references": get_selection_references,
    }
