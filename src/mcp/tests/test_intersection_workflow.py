"""A computed pair remains actionable; uncertain subtraction is never replayed."""
import json
import uuid

import pytest

from almond_mcp.features.components import intersection_queries as iq

MODEL = r"C:\Models\test.3dm"
A = {"object_id": str(uuid.UUID(int=1)), "path": []}
B = {"object_id": str(uuid.UUID(int=2)), "path": []}
STATE = "a" * 64


def sender(native, capability=1):
    calls = []
    def send(data):
        request = json.loads(data)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"intersection_tools": capability}})
        if isinstance(native, Exception):
            raise native
        return json.dumps(native)
    return send, calls


def test_clear_needs_no_previous_pair_and_does_not_resolve_geometry():
    send, calls = sender({"status": "success", "cleared": True})
    result = json.loads(iq.request(send, operation="preview", clear=True, expected_model_path=MODEL))
    assert result["cleared"] is True
    assert calls[1] == {"type": "intersection_preview", "clear": True, "expected_model_path": MODEL}


def test_occurrence_handle_is_forwarded_without_losing_nested_path():
    nested = {**A, "path": [str(uuid.UUID(int=30)), str(uuid.UUID(int=31))]}
    send, calls = sender({"status": "success", "displayed": True})
    result = json.loads(iq.request(send, operation="preview", first=nested, second=B,
                                  pair_state=STATE, expected_model_path=MODEL))
    assert result["displayed"] is True and calls[1]["a"] == nested
    assert calls[1]["pair_state"] == STATE


@pytest.mark.parametrize("operation", ["preview", "resolve"])
def test_old_bridge_is_not_sent_a_new_operation(operation):
    send, calls = sender(None, capability=0)
    result = json.loads(iq.request(send, operation=operation, first=A, second=B,
                                  pair_state=STATE, expected_model_path=MODEL))
    assert result["error_code"] == "unsupported_intersection_tools"
    assert len(calls) == 1


@pytest.mark.parametrize("bad", [None, "", "not-a-hash", "A" * 64, "a" * 63])
def test_missing_or_invalid_state_never_reaches_rhino(bad):
    send, calls = sender(None)
    result = json.loads(iq.request(send, operation="resolve", first=A, second=B,
                                  pair_state=bad, expected_model_path=MODEL))
    assert result["status"] == "error" and calls == []


def test_subtraction_timeout_is_ambiguous_and_dispatched_only_once():
    send, calls = sender(TimeoutError("receipt lost"))
    result = json.loads(iq.request(send, operation="resolve", first=A, second=B,
                                  pair_state=STATE, expected_model_path=MODEL))
    assert result["mutation_state"] == "unknown" and result["requires_reconciliation"] is True
    assert [r["type"] for r in calls] == ["get_rhino_context", "intersection_resolve"]


def test_preview_timeout_does_not_claim_the_display_was_unchanged():
    send, calls = sender(TimeoutError("display acknowledgement lost"))
    result = json.loads(iq.request(send, operation="preview", first=A, second=B,
                                  pair_state=STATE, expected_model_path=MODEL))
    assert result["mutation_state"] == "unknown" and result["requires_reconciliation"] is True
    assert len(calls) == 2


@pytest.mark.parametrize("native", [
    {"status": "success", "result": None},
    {"status": "success", "result": {"edited": True, "keep_id": A["object_id"], "trim_id": B["object_id"],
                                      "geometry_crc": 4, "previous_geometry_crc": 4}},
    {"status": "success", "result_error": "too large", "result": {"edited": True}},
])
def test_success_without_a_matching_change_receipt_is_not_success(native):
    send, calls = sender(native)
    result = json.loads(iq.request(send, operation="resolve", first=A, second=B,
                                  pair_state=STATE, expected_model_path=MODEL))
    assert result["error_code"] == "intersection_resolution_unconfirmed" and len(calls) == 2


def test_success_receipt_identifies_both_operands_and_keeps_before_after_crcs():
    detail = {"edited": True, "keep_id": A["object_id"], "trim_id": B["object_id"],
              "geometry_crc": 5, "previous_geometry_crc": 4}
    send, _ = sender({"status": "success", "result": detail})
    result = json.loads(iq.request(send, operation="resolve", first=A, second=B,
                                  pair_state=STATE, expected_model_path=MODEL))
    assert result["status"] == "success" and result["result"] == detail
