"""Register Phase, Plan and Step tools without owning server state."""
from almond_mcp.tool_response import error_payload
from almond_mcp.instruction_text import tool_instruction

import json

from pydantic import StrictInt


def register(mcp, context):
    """Register planning tools against the calling server's live context."""

    @mcp.tool()
    @tool_instruction(__file__, 'create_generation_phase')
    def create_generation_phase(name: str, description: str = "") -> str:
        try:
            return json.dumps({"status": "success", "phase": context.retrieval_store.create_generation_phase(name, description)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_generation_phase')
    def get_generation_phase(phase_id: str) -> str:
        try:
            phase = context.retrieval_store.get_generation_phase(phase_id)
            if phase is None:
                return json.dumps(error_payload(f"Unknown phase_id: {phase_id}"))
            return json.dumps({"status": "success", "phase": phase})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_generation_phases')
    def list_generation_phases(limit: StrictInt = 50) -> str:
        try:
            return json.dumps({"status": "success", **context.retrieval_store.list_generation_phases(limit)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'update_generation_phase')
    def update_generation_phase(
        phase_id: str, name: str | None = None, description: str | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success", "phase": context.retrieval_store.update_generation_phase(phase_id, name, description),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'create_generation_plan')
    def create_generation_plan(
        goal: str,
        scope: str = "house",
        scene_id: str = "",
        phase_id: str = "",
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success",
                "plan": context.retrieval_store.create_generation_plan(
                    goal=goal,
                    scope=scope,
                    scene_id=scene_id,
                    phase_id=phase_id,
                    scene_ids=scene_ids,
                    component_ids=component_ids,
                ),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_generation_plan')
    def get_generation_plan(plan_id: str, revision: StrictInt | None = None) -> str:
        try:
            plan = context.retrieval_store.get_generation_plan(plan_id, revision)
            if plan is None:
                message = (f"Unknown plan_id: {plan_id}" if revision is None else
                           f"Unknown saved revision {revision} for plan_id: {plan_id}")
                return json.dumps(error_payload(message))
            return json.dumps({"status": "success", "plan": plan})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_generation_plans')
    def list_generation_plans(
        phase_id: str = "", scene_id: str = "", status: str = "", limit: StrictInt = 50,
    ) -> str:
        try:
            return json.dumps({
                "status": "success", **context.retrieval_store.list_generation_plans(phase_id, scene_id, status, limit),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'update_generation_plan')
    def update_generation_plan(
        plan_id: str,
        goal: str | None = None,
        phase_id: str | None = None,
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
        expected_revision: StrictInt | None = None,
    ) -> str:
        try:
            return json.dumps({
                "status": "success", "plan": context.retrieval_store.update_generation_plan(
                    plan_id, goal=goal, phase_id=phase_id, scene_ids=scene_ids,
                    component_ids=component_ids, expected_revision=expected_revision,
                ),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'list_generation_plan_revisions')
    def list_generation_plan_revisions(plan_id: str, limit: StrictInt = 50) -> str:
        try:
            return json.dumps({"status": "success", **context.retrieval_store.list_generation_plan_revisions(plan_id, limit)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool()
    @tool_instruction(__file__, 'update_generation_step')
    def update_generation_step(
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
                "plan": context.retrieval_store.update_plan_step(
                    plan_id=plan_id,
                    step_id=step_id,
                    status=status,
                    input_refs=input_refs,
                    output_refs=output_refs,
                    component_ids=component_ids,
                    expected_revision=expected_revision,
                ),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'resolve_generation_targets')
    def resolve_generation_targets(plan_id: str, step_id: str = "") -> str:
        try:
            return json.dumps({"status": "success", **context.retrieval_store.resolve_generation_targets(plan_id, step_id)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))

    return {
        "create_generation_phase": create_generation_phase,
        "get_generation_phase": get_generation_phase,
        "list_generation_phases": list_generation_phases,
        "update_generation_phase": update_generation_phase,
        "create_generation_plan": create_generation_plan,
        "get_generation_plan": get_generation_plan,
        "list_generation_plans": list_generation_plans,
        "update_generation_plan": update_generation_plan,
        "list_generation_plan_revisions": list_generation_plan_revisions,
        "update_generation_step": update_generation_step,
        "resolve_generation_targets": resolve_generation_targets,
    }
