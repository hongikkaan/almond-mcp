"""Register Phase, Plan and Step tools without owning server state."""
from almond_mcp.tool_response import error_payload, mcp_error_result
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.query_output import compact_ack
from almond_mcp.query_output import validate_field_groups, InvalidFieldGroups
from almond_mcp.features.planning.output import (
    GROUPS, PHASE_GROUPS, REVISION_GROUPS, TARGET_GROUPS, project,
    encode, phase_detail, plan_detail, step_detail, update_ack,
)
from almond_mcp.features.planning.requests import CreateRequest, GetRequest, ListRequest, UpdateRequest
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.instruction_text import tool_instruction, read_instruction

import json

from pydantic import StrictInt


PHASE_ACK_FIELDS = {"phase_id"}
PLAN_ACK_FIELDS = {"plan_id", "loop_no", "revision"}


def register(mcp, context):
    """Register planning tools against the calling server's live context."""


    @mcp.tool(name='plan_02-create', output_schema=public_output_schema('create_planning', wrapped=True))
    @tool_instruction(__file__, 'create_planning')
    @holon_output
    def create_planning(request: CreateRequest) -> str:
        try:
            store = context.retrieval_store
            if request.target == "phase":
                phase = store.create_phase(request.name, request.description, request.file_name,
                    None, request.status, request.depends_on, request.previous_id)
                return json.dumps({"status": "success", "phase": compact_ack(phase, PHASE_ACK_FIELDS)})
            plan = store.create_plan(goal=request.goal, title=request.title, scope=request.scope,
                scene_id=request.scene_id, phase_id=request.phase_id, scene_ids=request.scene_ids,
                component_ids=request.holon_ids, depends_on=request.depends_on,
                previous_id=request.previous_id, parent_plan=request.parent_plan, child_plan=request.child_plan)
            return json.dumps({"status": "success", "plan": compact_ack(plan, PLAN_ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(name='plan_05-get', annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_planning', wrapped=True))
    @tool_instruction(__file__, 'get_planning')
    @holon_output
    def get_planning(request: GetRequest) -> str:
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


    @mcp.tool(name='plan_08-list', annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('list_planning', wrapped=True))
    @tool_instruction(__file__, 'list_planning')
    @holon_output
    def list_planning(request: ListRequest) -> str:
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


    @mcp.tool(name='plan_12-update', output_schema=public_output_schema('update_planning', wrapped=True))
    @tool_instruction(__file__, 'update_planning')
    @holon_output
    def update_planning(request: UpdateRequest) -> str:
        try:
            store = context.retrieval_store
            if request.target == "phase":
                return json.dumps(update_ack(store.edit_phase(request.phase_id, request.name,
                    request.description, request.file_name, None, request.status,
                    request.depends_on, request.previous_id), "phase"))
            if request.target == "step":
                return json.dumps(update_ack(store.edit_step(plan_id=request.plan_id, step_id=request.step_id,
                    status=request.status, input_refs=request.input_refs, output_refs=request.output_refs,
                    expected_revision=request.expected_revision, loop_no=request.loop_no), "plan", request.step_id))
            return json.dumps(update_ack(store.edit_plan(request.plan_id,
                goal=request.goal, phase_id=request.phase_id, scene_ids=request.scene_ids,
                component_ids=request.holon_ids, expected_revision=request.expected_revision,
                depends_on=request.depends_on, status=request.status, artifact_refs=request.artifact_refs,
                title=request.title, previous_id=request.previous_id, parent_plan=request.parent_plan,
                child_plan=request.child_plan, loop_no=request.loop_no), "plan"))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(name='plan_07-list_revisions', annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('list_plan_revisions', wrapped=True))
    @tool_instruction(__file__, 'list_plan_revisions')
    @holon_output
    def list_plan_revisions(plan_id: str, limit: StrictInt = 50, field_groups: list[str] | None = None,
                            loop_no: StrictInt | None = None, step_id: str = "") -> str:
        try:
            validate_field_groups(field_groups, REVISION_GROUPS)
            return encode(project({"status": "success", **context.retrieval_store.list_plan_revisions(plan_id, limit, loop_no, step_id)}, field_groups))
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool(name='inspect_05-resolve_targets', annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('resolve_targets', wrapped=True))
    @tool_instruction(__file__, 'resolve_targets')
    @holon_output
    def resolve_targets(plan_id: str, step_id: str = "", field_groups: list[str] | None = None) -> str:
        try:
            validate_field_groups(field_groups, TARGET_GROUPS)
            return encode(project({"status": "success", **context.retrieval_store.resolve_targets(plan_id, step_id)}, field_groups))
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))

    @mcp.tool(name='inspect_04-get_selection_references', annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_selection_references', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'get_selection_references')
    @holon_output
    def get_selection_references(selection_limit: StrictInt = 50, limit: StrictInt = 50,
                                 field_groups: list[str] | None = None) -> str:
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
                document["path"], [obj["id"] for obj in selection["objects"]], limit, native_observe=context._component_bridge,
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
