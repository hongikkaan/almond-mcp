"""Register Phase, Plan and Step tools without owning server state."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import compact_ack
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.planning.output import (
    GROUPS, PHASE_GROUPS, PLAN_GROUPS, PLAN_LIST_GROUPS, REVISION_GROUPS, TARGET_GROUPS, project,
)
from almond_mcp.instruction_text import tool_instruction

import json

from pydantic import StrictBool, StrictInt


PHASE_ACK_FIELDS = {"phase_id"}
PLAN_ACK_FIELDS = {"plan_id", "revision"}


def register(mcp, context):
    """Register planning tools against the calling server's live context."""

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_project_files')
    @query_output
    def list_project_files(limit: StrictInt = 50, offset: StrictInt = 0, include_ids: StrictBool = False) -> str:
        try:
            return json.dumps({"status": "success", **context.retrieval_store.list_project_files(limit, offset)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))

    @mcp.tool()
    @tool_instruction(__file__, 'create_phase')
    def create_phase(name: str, description: str = "", file_name: str = "", project_file_id: str | None = None, status: str = "pending") -> str:
        try:
            return json.dumps({"status": "success", "phase": compact_ack(context.retrieval_store.create_phase(name, description, file_name, project_file_id, status), PHASE_ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_phase')
    @query_output
    def get_phase(phase_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, PHASE_GROUPS)
        try:
            phase = context.retrieval_store.get_phase(phase_id)
            if phase is None:
                return json.dumps(project(error_payload(f"Unknown phase_id: {phase_id}"), field_groups))
            return json.dumps(project({"status": "success", "phase": phase}, field_groups))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_phases')
    @query_output
    def list_phases(limit: StrictInt = 50, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, PHASE_GROUPS)
        try:
            return json.dumps(project({"status": "success", **context.retrieval_store.list_phases(limit)}, field_groups))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool()
    @tool_instruction(__file__, 'update_phase')
    def update_phase(
        phase_id: str, name: str | None = None, description: str | None = None,
        file_name: str | None = None, project_file_id: str | None = None, status: str | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success", "phase": compact_ack(context.retrieval_store.update_phase(phase_id, name, description, file_name, project_file_id, status), PHASE_ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'create_plan')
    def create_plan(
        goal: str,
        scope: str = "house",
        scene_id: str = "",
        phase_id: str = "",
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
        depends_on: list[str] | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success",
                "plan": compact_ack(context.retrieval_store.create_plan(
                    goal=goal,
                    scope=scope,
                    scene_id=scene_id,
                    phase_id=phase_id,
                    scene_ids=scene_ids,
                    component_ids=component_ids,
                    depends_on=depends_on,
                ), PLAN_ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_plan')
    @query_output
    def get_plan(plan_id: str, revision: StrictInt | None = None, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, PLAN_GROUPS)
        try:
            plan = context.retrieval_store.get_plan(plan_id, revision)
            if plan is None:
                message = (f"Unknown plan_id: {plan_id}" if revision is None else
                           f"Unknown saved revision {revision} for plan_id: {plan_id}")
                return json.dumps(project(error_payload(message), field_groups))
            return json.dumps(project({"status": "success", "plan": plan}, field_groups))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_plans')
    @query_output
    def list_plans(
        phase_id: str = "", scene_id: str = "", status: str = "", limit: StrictInt = 50,
        include_ids: StrictBool = False, field_groups: list[str] | None = None,
    ) -> str:
        validate_field_groups(field_groups, PLAN_LIST_GROUPS)
        try:
            return json.dumps(project({
                "status": "success", **context.retrieval_store.list_plans(phase_id, scene_id, status, limit),
            }, field_groups))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool()
    @tool_instruction(__file__, 'update_plan')
    def update_plan(
        plan_id: str,
        goal: str | None = None,
        phase_id: str | None = None,
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
        expected_revision: StrictInt | None = None,
        depends_on: list[str] | None = None,
        status: str | None = None,
        artifact_refs: list[str] | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success", "plan": compact_ack(context.retrieval_store.update_plan(
                    plan_id, goal=goal, phase_id=phase_id, scene_ids=scene_ids,
                    component_ids=component_ids, expected_revision=expected_revision,
                    depends_on=depends_on, status=status, artifact_refs=artifact_refs,
                ), PLAN_ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_plan_revisions')
    @query_output
    def list_plan_revisions(plan_id: str, limit: StrictInt = 50, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, REVISION_GROUPS)
        try:
            return json.dumps(project({"status": "success", **context.retrieval_store.list_plan_revisions(plan_id, limit)}, field_groups))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))


    @mcp.tool()
    @tool_instruction(__file__, 'update_step')
    def update_step(
        plan_id: str,
        step_id: str,
        status: str,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        component_ids: list[str] | None = None,
        expected_revision: StrictInt | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success",
                "plan": compact_ack(context.retrieval_store.update_plan_step(
                    plan_id=plan_id,
                    step_id=step_id,
                    status=status,
                    input_refs=input_refs,
                    output_refs=output_refs,
                    component_ids=component_ids,
                    expected_revision=expected_revision,
                ), PLAN_ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'resolve_targets')
    @query_output
    def resolve_targets(plan_id: str, step_id: str = "", include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, TARGET_GROUPS)
        try:
            return json.dumps(project({"status": "success", **context.retrieval_store.resolve_targets(plan_id, step_id)}, field_groups))
        except Exception as exc:
            return json.dumps(project(error_payload(str(exc)), field_groups))

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_selection_references')
    @query_output
    def get_selection_references(selection_limit: StrictInt = 50, limit: StrictInt = 50,
                                 include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        try:
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
            return json.dumps(project({"status": "success", **result}, field_groups), ensure_ascii=False)
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))

    return {
        "list_project_files": list_project_files,
        "create_phase": create_phase,
        "get_phase": get_phase,
        "list_phases": list_phases,
        "update_phase": update_phase,
        "create_plan": create_plan,
        "get_plan": get_plan,
        "list_plans": list_plans,
        "update_plan": update_plan,
        "list_plan_revisions": list_plan_revisions,
        "update_step": update_step,
        "resolve_targets": resolve_targets,
        "get_selection_references": get_selection_references,
    }
