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
        """Phase 또는 Plan 생성. Plan은 `scope`의 Step 템플릿을 적용해 `loop_no=0`, `revision=1`에서 시작하며 실제 작업은 별도 수행. 생성 오류는 `result.status`에서 확인. 자동 생성된 Step은 plan_05-get tool로 확인."""
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
        """Phase·Plan·Step 작업 기록 조회. `include_details=true`로 상세를 포함. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로로 열어 확인.

        Plan·Step 조회에 `revision`을 지정하면 현재 번호여도 읽기 전용 스냅샷 반환.
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
        """Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록 조회. `offset` 미지원. Step 목록과 리비전 정보는 같은 스냅샷을 기준으로 반환."""
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
        """Phase·Plan 작업 정보 또는 Step 상태·입출력 참조·판단 기록 수정. Plan·Step은 현재 회차만 수정 가능.

        `depends_on`, `input_refs`, `output_refs`는 `add`/`remove` 패치. 나머지 대상·산출물·상하위 관계 배열은 전체 교체. 생략·`null`은 기존 값 유지, 교체 배열의 `[]`는 전체 삭제.

        적용하지 못한 패치 항목은 `issues`에서 확인. 일부만 적용되면 `partial_success`. Step을 `completed`로 지정하면 함께 전달한 필드와 한 번에 저장.

        Plan 완료는 사용자 확인 후 지정.
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
        """Plan 리비전 목록을 최신 회차·리비전 순으로 조회. Step 필터는 해당 Step의 직접 변경만 포함. `offset` 미지원.

        과거 기록은 plan_05-get tool에 같은 `loop_no`와 `revision`을 넣어 조회.

        Args:
            plan_id: plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
            limit: 1~500.
            field_groups: `audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환.
            loop_no: 생략·`null`은 모든 회차, 0은 실행 전 기록.
            step_id: 생략하거나 비우면 Step으로 필터링하지 않음.
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
        """Plan에 등록된 Scene·Holon 대상과 저장된 Holon 정보 조회. Step 지정 시 해당 Plan 소속을 검사하며 대상은 Plan 기준. Scene 전체로 Holon을 늘리거나 Rhino의 현재 구성원을 확인하지 않는다.

        Args:
            plan_id: plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
            field_groups: references, geometry, scope, audit, all. 생략·빈 배열이면 요약.
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
        """저장된 Rhino 문서의 일반 모델에서 선택 객체의 소속 Holon과 상위 Holon을 참조하는 Plan 조회. 일치한 Holon과 Plan의 전체 대상은 다를 수 있다. selection_truncated는 선택 목록, truncated는 Plan 목록에 적용.

        Args:
            selection_limit: 검사할 선택 객체 수 1..200
            limit: 반환할 Plan 수 1..500
            field_groups: steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약.
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
