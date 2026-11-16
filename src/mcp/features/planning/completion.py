"""Agent confirmation for the destructive Step completion transition."""
from dataclasses import dataclass
from hashlib import sha256
import json
from secrets import token_urlsafe
from threading import Lock

from almond_mcp.features.planning.output import update_ack
from almond_mcp.features.planning.updates import PlanningUpdate
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload


WARNING = (
    "다음 스텝에서도 사용해야 할 자료는 먼저 temp가 아닌 다른 레이어로 옮겨야 합니다. "
    "현재 스텝을 완료하면 temp 및 그 하위 레이어에 속한 객체 전체가 삭제됩니다. "
    "모든 하위 레이어도 삭제되며 최상위 temp 레이어는 유지됩니다. "
    "로컬 블록 정의에서도 해당 레이어의 구성원이 삭제되어 temp 밖에 있는 인스턴스의 형상이 달라질 수 있습니다. "
    "스텝 상태를 완료로 변경하시겠습니까?"
)
CONFIRMATION_FIELDS = {"completion_token", "completion_decision"}


@dataclass(frozen=True)
class PendingCompletion:
    token: str
    model_path: str
    request_digest: bytes
    acknowledgement: dict


class CleanupFailure(RuntimeError):
    def __init__(self, message, state):
        super().__init__(message)
        self.state = state


def _cleanup_temp(send, model_path):
    """Return verified native counts or report the observed cleanup state."""
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
        return {key: counts[key] for key in ("deleted_layers", "deleted_objects")}
    except CleanupFailure:
        raise
    except Exception as exc:
        raise CleanupFailure(str(exc), "unknown" if dispatched else "not_started") from exc


class StepCompletion:
    """Keep one pending completion attempt per Step in this MCP worker."""

    def __init__(self, send):
        self._send = send
        self._pending = {}
        self._lock = Lock()

    def update(self, store, request):
        fields = request.model_dump(exclude={"target", "input_refs", "output_refs", *CONFIRMATION_FIELDS})
        fields.update(input_refs=request.input_refs, output_refs=request.output_refs)
        if request.completion_token is not None or request.completion_decision is not None:
            return self._confirm(store, request, fields)
        if request.status == "completed":
            plan, step = store.step_update_target(
                request.plan_id, request.step_id, request.expected_revision, request.loop_no)
            fields.update(expected_revision=plan["revision"], loop_no=plan["loop_no"])
            if step["status"] != "completed":
                return self._prepare(request, plan)
        return update_ack(store.edit_step(**fields), "plan", request.step_id)

    @staticmethod
    def _digest(request):
        return sha256(request.model_dump_json(exclude=CONFIRMATION_FIELDS).encode("utf-8")).digest()

    def _prepare(self, request, plan):
        token = token_urlsafe(24)
        ack = update_ack(PlanningUpdate(plan, False, []), "plan", request.step_id)
        attempt = PendingCompletion(token, bound_model_path(), self._digest(request), ack)
        key = (request.plan_id, request.step_id)
        with self._lock:
            self._pending[key] = attempt
        return {**ack, "status": "confirmation_required", "confirmation": {
            "token": token, "warning": WARNING, "choices": ["yes", "no"],
        }}

    def _confirm(self, store, request, fields):
        if request.status != "completed" or not request.completion_token or request.completion_decision is None:
            raise ValueError("Supply both completion fields for a Step completion request.")
        key = (request.plan_id, request.step_id)
        with self._lock:
            attempt = self._pending.get(key)
            if attempt is None or attempt.token != request.completion_token:
                return error_payload("No matching Step completion attempt. Request a fresh confirmation.",
                                     error_code="invalid_step_completion_confirmation")
            if request.completion_decision == "yes" and self._digest(request) != attempt.request_digest:
                return error_payload("Repeat the original Step update fields with the confirmation.",
                                     error_code="invalid_step_completion_confirmation")
            del self._pending[key]
        if request.completion_decision == "no":
            return {**attempt.acknowledgement, "status": "cancelled"}

        original = attempt.acknowledgement["plan"]
        fields.update(expected_revision=original["revision"], loop_no=original["loop_no"])
        try:
            if bound_model_path() != attempt.model_path:
                raise ValueError("The bound model changed. Request a fresh Step completion confirmation.")
        except ValueError as exc:
            return {**error_payload(str(exc), error_code="step_temp_cleanup_failed"),
                    "changed": False, "cleanup_state": "not_started", "requires_reconciliation": False}

        try:
            update = store.edit_step(**fields)
        except Exception as exc:
            error = {**error_payload(str(exc), error_code="step_completion_db_failed"),
                     "changed": False, "cleanup_state": "not_started", "requires_reconciliation": False}
            try:
                plan, _ = store.step_update_target(request.plan_id, request.step_id, None, None)
                observed = update_ack(PlanningUpdate(plan, False, []), "plan", request.step_id)
                error.update(plan=observed["plan"], step=observed["step"])
            except Exception:
                error["requires_reconciliation"] = True
            return error

        result = update_ack(update, "plan", request.step_id)
        try:
            result["cleanup"] = _cleanup_temp(self._send, attempt.model_path)
        except CleanupFailure as exc:
            result.update(error_payload(str(exc) + " Step completion was saved. Check the Rhino temp tree.",
                                        error_code="step_temp_cleanup_failed"),
                          cleanup_state=exc.state, requires_reconciliation=True)
        return result
