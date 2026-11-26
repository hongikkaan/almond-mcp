"""Complete a Step in one request, preserving the native post-commit operation."""
import json

from almond_mcp.features.planning.output import update_ack
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload


class CleanupFailure(RuntimeError):
    def __init__(self, message, state):
        super().__init__(message)
        self.state = state


def _cleanup_temp(send, model_path):
    """Require verified native counts, but do not include them in the tool response."""
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        version = context.get("capabilities", {}).get("step_temp_cleanup")
        if context.get("status") != "success" or type(version) is not int or version < 1:
            raise ValueError("Load a Bridge that supports Step temp cleanup and reconnect.")
        payload = json.dumps({"type": "cleanup_step_temp", "expected_model_path": model_path}).encode("utf-8")
        dispatched = True
        reply = json.loads(send(payload, timeout=60.0))
        if reply.get("status") == "error" and reply.get("cleanup_state") in {"not_started", "rolled_back", "unknown"}:
            raise CleanupFailure(reply.get("message") or "Rhino could not clean the temp layer.", reply["cleanup_state"])
        counts = reply.get("cleanup")
        if (reply.get("status") != "success" or not isinstance(counts, dict)
                or not all(type(counts.get(key)) is int and counts[key] >= 0
                           for key in ("deleted_layers", "deleted_objects"))):
            raise ValueError("Could not confirm the Rhino temp cleanup result.")
    except CleanupFailure:
        raise
    except Exception as exc:
        raise CleanupFailure(str(exc), "unknown" if dispatched else "not_started") from exc


def update_step(store, request, send):
    """Commit Step fields once and run the native operation only on a transition."""
    fields = dict(status=request.status, input_refs=request.input_refs, output_refs=request.output_refs,
                  expected_revision=request.expected_revision, loop_no=request.loop_no,
                  takeaways=request.takeaways, design_rationale=request.design_rationale)
    model_path = None
    if request.status == "completed":
        plan, step = store.read_step_completion(request.plan_id, request.step_id,
                                               request.expected_revision, request.loop_no)
        fields.update(expected_revision=plan["revision"], loop_no=plan["loop_no"])
        if step["status"] != "completed":
            model_path = bound_model_path()
    try:
        update = store.edit_step(request.plan_id, request.step_id, **fields)
    except Exception as exc:
        if model_path is None:
            raise
        error = {**error_payload(str(exc), error_code="step_completion_db_failed"),
                 "changed": False, "cleanup_state": "not_started", "requires_reconciliation": False}
        try:
            plan, step = store.read_step_completion(request.plan_id, request.step_id, None, None)
            error.update(plan=plan, step=step)
        except Exception:
            error["requires_reconciliation"] = True
        return error

    result = update_ack(update, "plan", request.step_id)
    if model_path is not None and update.changed:
        try:
            _cleanup_temp(send, model_path)
        except CleanupFailure as exc:
            result.update(error_payload("The Step was saved as completed, but the Rhino follow-up could not be "
                                        "confirmed. Check the Rhino document before continuing.",
                                        error_code="step_temp_cleanup_failed"),
                          cleanup_state=exc.state, requires_reconciliation=True)
    return result
