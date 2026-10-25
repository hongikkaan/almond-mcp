"""Register Phase, Plan and Step tools without owning server state."""

import json

from pydantic import StrictInt


def register(mcp, context):
    """Register planning tools against the calling server's live context."""

    @mcp.tool()
    def create_generation_phase(name: str, description: str = "") -> str:
        """Create an organizational Phase for Plans; this does not edit Rhino geometry."""
        try:
            return json.dumps({"status": "success", "phase": context.retrieval_store.create_generation_phase(name, description)})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def get_generation_phase(phase_id: str) -> str:
        """Read a Phase's name, description and Plan count."""
        try:
            phase = context.retrieval_store.get_generation_phase(phase_id)
            if phase is None:
                return json.dumps({"status": "error", "message": f"Unknown phase_id: {phase_id}"})
            return json.dumps({"status": "success", "phase": phase})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def list_generation_phases(limit: StrictInt = 50) -> str:
        """List organizational Phases with totals and an explicit truncation flag; limit is 1-500."""
        try:
            return json.dumps({"status": "success", **context.retrieval_store.list_generation_phases(limit)})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def update_generation_phase(
        phase_id: str, name: str | None = None, description: str | None = None,
    ) -> str:
        """Update Phase organization; omitted fields retain their values."""
        try:
            return json.dumps({
                "status": "success", "phase": context.retrieval_store.update_generation_phase(phase_id, name, description),
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def create_generation_plan(
        goal: str,
        scope: str = "house",
        scene_id: str = "",
        phase_id: str = "",
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
    ) -> str:
        """
        Create a dependency-ordered Plan in an optional organizational Phase.
        scope is house, interior, structure, drawing, or component; component uses
        inspect_context, design, model, validate. scene_ids are context; component_ids
        explicitly bind targets without requiring membership in those Scenes.
        Legacy scene_id must match the first scene_ids entry when both are supplied.
        Plans record state and evidence, do not execute steps, and do not authorize edits.
        """
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
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def get_generation_plan(plan_id: str, revision: StrictInt | None = None) -> str:
        """Read the current Plan or an immutable saved revision, including legacy baseline 0.

        Snapshots contain Plan metadata, step state and handles; they are not Rhino
        geometry backups. A missing requested revision never falls back to current state.
        """
        try:
            plan = context.retrieval_store.get_generation_plan(plan_id, revision)
            if plan is None:
                message = (f"Unknown plan_id: {plan_id}" if revision is None else
                           f"Unknown saved revision {revision} for plan_id: {plan_id}")
                return json.dumps({"status": "error", "message": message})
            return json.dumps({"status": "success", "plan": plan})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def list_generation_plans(
        phase_id: str = "", scene_id: str = "", status: str = "", limit: StrictInt = 50,
    ) -> str:
        """List compact Plan summaries, optionally filtered by Phase, contextual Scene or status."""
        try:
            return json.dumps({
                "status": "success", **context.retrieval_store.list_generation_plans(phase_id, scene_id, status, limit),
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def update_generation_plan(
        plan_id: str,
        goal: str | None = None,
        phase_id: str | None = None,
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
        expected_revision: StrictInt | None = None,
    ) -> str:
        """Update Plan metadata and bindings atomically, recording a new saved revision.

        Omitted fields retain prior values; [] clears refs, and phase_id='' detaches
        the Phase. expected_revision rejects stale updates without changing the Plan.
        References provide context and explicit targets, not permission to edit geometry.
        """
        try:
            return json.dumps({
                "status": "success", "plan": context.retrieval_store.update_generation_plan(
                    plan_id, goal=goal, phase_id=phase_id, scene_ids=scene_ids,
                    component_ids=component_ids, expected_revision=expected_revision,
                ),
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def list_generation_plan_revisions(plan_id: str, limit: StrictInt = 50) -> str:
        """List saved Plan revisions newest first, with operation labels and truncation metadata."""
        try:
            return json.dumps({"status": "success", **context.retrieval_store.list_generation_plan_revisions(plan_id, limit)})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool()
    def update_generation_step(
        plan_id: str,
        step_id: str,
        status: str,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        component_ids: list[str] | None = None,
        expected_revision: StrictInt | None = None,
    ) -> str:
        """
        Record a Step's status, evidence and optional explicit Component targets.
        Omitted refs retain prior values; [] clears them. Step component_ids=null in a
        returned Plan inherits Plan targets; explicit [] selects none. Scene refs never
        expand the selection. running/completed require completed prerequisites, and a
        prerequisite cannot regress while descendants run or remain completed.
        expected_revision rejects stale updates. No Rhino operation is executed here.
        """
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
            return json.dumps({"status": "error", "message": str(exc)})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def resolve_generation_targets(plan_id: str, step_id: str = "") -> str:
        """Resolve registered Step targets, or Plan targets when the Step has no override.

        An explicit empty Step selection stays empty. Contextual Scenes never expand
        targets. Returned group/document identities have live_verified=false; inspect
        current Rhino state and user intent before editing. This does not grant authority.
        """
        try:
            return json.dumps({"status": "success", **context.retrieval_store.resolve_generation_targets(plan_id, step_id)})
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

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
