"""Register Phase, Plan and Step tools without owning server state."""
from almond_mcp.tool_response import error_payload, mcp_error_result
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.query_output import compact_ack
from almond_mcp.query_output import validate_field_groups, InvalidFieldGroups
from almond_mcp.features.planning.output import (
    GROUPS, PHASE_GROUPS, REVISION_GROUPS, TARGET_GROUPS, project,
    encode, phase_detail, plan_detail, step_detail, update_ack,
)
from almond_mcp.features.planning.updates import StringListPatch
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.instruction_text import tool_instruction, read_instruction

import json

from pydantic import StrictBool, StrictInt
from typing import Literal


PHASE_ACK_FIELDS = {"phase_id"}
PLAN_ACK_FIELDS = {"plan_id", "loop_no", "revision"}


def register(mcp, context):
    """Register planning tools against the calling server's live context."""


    @mcp.tool(output_schema=public_output_schema('create_phase', wrapped=True))
    @tool_instruction(__file__, 'create_phase')
    @holon_output
    def create_phase(name: str, description: str = "", file_name: str | list[str] = "",
                     status: Literal["pending", "running", "paused", "completed", "failed", "blocked"] = "pending", depends_on: list[str] | None = None,
                     previous_id: str | None = None) -> str:
        try:
            return json.dumps({"status": "success", "phase": compact_ack(context.retrieval_store.create_phase(name, description, file_name, None, status, depends_on, previous_id), PHASE_ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('list_phases', wrapped=True))
    @tool_instruction(__file__, 'list_phases')
    @holon_output
    def list_phases(limit: StrictInt = 50, field_groups: list[str] | None = None) -> str:
        try:
            validate_field_groups(field_groups, PHASE_GROUPS)
            page = context.retrieval_store.list_phases(limit)
            return encode(project({"status": "success", **page}, field_groups))
        except InvalidFieldGroups as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool(output_schema=public_output_schema('update_phase', wrapped=True))
    @tool_instruction(__file__, 'update_phase')
    @holon_output
    def update_phase(
        phase_id: str, name: str | None = None, description: str | None = None,
        file_name: str | list[str] | None = None, status: Literal["pending", "running", "paused", "completed", "failed", "blocked"] | None = None,
        depends_on: StringListPatch | None = None,
        previous_id: str | None = None,
    ) -> str:
        try:
            return json.dumps(update_ack(context.retrieval_store.edit_phase(
                phase_id, name, description, file_name, None, status, depends_on, previous_id), "phase"))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(output_schema=public_output_schema('create_plan', wrapped=True))
    @tool_instruction(__file__, 'create_plan')
    @holon_output
    def create_plan(
        title: str,
        goal: str,
        scope: str = "house",
        scene_id: str = "",
        phase_id: str = "",
        scene_ids: list[str] | None = None,
        holon_ids: list[str] | None = None,
        depends_on: list[str] | None = None,
        previous_id: str | None = None,
        parent_plan: list[str] | None = None,
        child_plan: list[str] | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success",
                "plan": compact_ack(context.retrieval_store.create_plan(
                    goal=goal,
                    title=title,
                    scope=scope,
                    scene_id=scene_id,
                    phase_id=phase_id,
                    scene_ids=scene_ids,
                    component_ids=holon_ids,
                    depends_on=depends_on,
                    previous_id=previous_id,
                    parent_plan=parent_plan,
                    child_plan=child_plan,
                ), PLAN_ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(name='get_phase_plan_step', title='get_phase·plan·step', annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_phase_plan_step', wrapped=True))
    @tool_instruction(__file__, 'get_phase_plan_step')
    @holon_output
    def get_phase_plan_step(phase_id: str = "", plan_id: str = "", step_id: str = "",
                            revision: StrictInt | None = None, include_details: StrictBool = False,
                            loop_no: StrictInt | None = None) -> str:
        try:
            if bool(phase_id) == bool(plan_id) or (step_id and not plan_id):
                raise ValueError("Supply phase_id or plan_id, never both; step_id also requires plan_id.")
            if phase_id:
                if revision is not None or loop_no is not None:
                    raise ValueError("loop_no and revision do not apply to a Phase.")
                phase = context.retrieval_store.get_phase(phase_id)
                if phase is None:
                    raise KeyError(f"Unknown phase_id: {phase_id}")
                return encode(phase_detail(phase, include_details))
            if step_id:
                step = context.retrieval_store.get_step(plan_id, step_id, revision, loop_no)
                if step is None:
                    raise KeyError(f"Unknown Plan/Step/revision: {plan_id}, {step_id}, {revision}")
                return encode(step_detail(step, include_details, historical=step["read_only"]))
            plan = context.retrieval_store.get_plan(plan_id, revision, loop_no)
            if plan is None:
                message = (f"Unknown plan_id: {plan_id}" if revision is None else
                           f"Unknown saved revision {revision} for plan_id: {plan_id}")
                return json.dumps(error_payload(message))
            return encode(plan_detail(plan, include_details, historical=plan["read_only"]))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('list_plans', wrapped=True))
    @tool_instruction(__file__, 'list_plans')
    @holon_output
    def list_plans(
        phase_id: str = "", scene_id: str = "",
        status: Literal["", "pending", "running", "paused", "completed", "failed", "blocked"] = "",
        limit: StrictInt = 50,
    ) -> str:
        try:
            page = context.retrieval_store.list_plans(phase_id, scene_id, status, limit)
            return encode({
                "status": "success", **page,
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(output_schema=public_output_schema('update_plan', wrapped=True))
    @tool_instruction(__file__, 'update_plan')
    @holon_output
    def update_plan(
        plan_id: str,
        goal: str | None = None,
        phase_id: str | None = None,
        scene_ids: list[str] | None = None,
        holon_ids: list[str] | None = None,
        expected_revision: StrictInt | None = None,
        depends_on: StringListPatch | None = None,
        status: Literal["pending", "running", "paused", "completed", "failed", "blocked"] | None = None,
        artifact_refs: list[str] | None = None,
        title: str | None = None,
        previous_id: str | None = None,
        parent_plan: list[str] | None = None,
        child_plan: list[str] | None = None,
        loop_no: StrictInt | None = None,
    ) -> str:
        try:
            return json.dumps(update_ack(context.retrieval_store.edit_plan(
                    plan_id, goal=goal, phase_id=phase_id, scene_ids=scene_ids,
                    component_ids=holon_ids, expected_revision=expected_revision,
                    depends_on=depends_on, status=status, artifact_refs=artifact_refs, title=title,
                    previous_id=previous_id, parent_plan=parent_plan, child_plan=child_plan, loop_no=loop_no,
                ), "plan"))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('list_plan_revisions', wrapped=True))
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


    @mcp.tool(output_schema=public_output_schema('update_step', wrapped=True))
    @tool_instruction(__file__, 'update_step')
    @holon_output
    def update_step(
        plan_id: str,
        step_id: str,
        status: Literal["pending", "running", "paused", "completed", "failed", "blocked"] | None = None,
        input_refs: StringListPatch | None = None,
        output_refs: StringListPatch | None = None,
        expected_revision: StrictInt | None = None,
        loop_no: StrictInt | None = None,
    ) -> str:
        try:
            return json.dumps(update_ack(context.retrieval_store.edit_step(
                    plan_id=plan_id,
                    step_id=step_id,
                    status=status,
                    input_refs=input_refs,
                    output_refs=output_refs,
                    expected_revision=expected_revision,
                    loop_no=loop_no,
                ), "plan", step_id))
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('resolve_targets', wrapped=True))
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

    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_selection_references', wrapped=True))
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
        "create_phase": create_phase,
        "list_phases": list_phases,
        "update_phase": update_phase,
        "create_plan": create_plan,
        "get_phase_plan_step": get_phase_plan_step,
        "list_plans": list_plans,
        "update_plan": update_plan,
        "list_plan_revisions": list_plan_revisions,
        "update_step": update_step,
        "resolve_targets": resolve_targets,
        "get_selection_references": get_selection_references,
    }
