"""Returned occurrence handles connect inspection, preview and explicit subtraction."""
import json
import uuid

from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload


def handle(value):
    if not isinstance(value, dict) or set(value) - {"object_id", "path"}:
        raise ValueError("Use the returned occurrence handle containing object_id and path.")
    identity = uuid.UUID(value.get("object_id", ""))
    path = value.get("path", [])
    if not identity.int or not isinstance(path, list) or len(path) > 32:
        raise ValueError("A handle needs a nonempty object GUID and at most 32 member GUIDs.")
    members = []
    for part in path:
        member = uuid.UUID(part)
        if not member.int:
            raise ValueError("Occurrence path GUIDs must be nonempty.")
        members.append(str(member))
    return {"object_id": str(identity), "path": members}


def request(send, *, operation, first=None, second=None, pair_state="", clear=False,
            expected_model_path=""):
    dispatched = False
    mutation = operation == "resolve"
    try:
        if operation not in {"preview", "resolve"} or type(clear) is not bool:
            raise ValueError("Invalid intersection operation.")
        if operation == "resolve" and clear:
            raise ValueError("clear applies only to the preview.")
        payload = {"type": "intersection_" + operation,
                   "expected_model_path": bound_model_path(expected_model_path)}
        if clear:
            payload["clear"] = True
        else:
            a, b = handle(first), handle(second)
            if a == b:
                raise ValueError("Choose two distinct occurrence handles.")
            if (not isinstance(pair_state, str) or len(pair_state) != 64
                    or any(c not in "0123456789abcdef" for c in pair_state)):
                raise ValueError("Pass pair_state from the current intersection result.")
            payload.update({"keep" if mutation else "a": a,
                            "trim" if mutation else "b": b, "pair_state": pair_state})
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if (not isinstance(context, dict) or context.get("status") != "success"
                or context.get("capabilities", {}).get("intersection_tools") != 1):
            return json.dumps(error_payload("Load a Bridge with intersection_tools=1 before previewing or resolving an overlap.",
                                            error_code="unsupported_intersection_tools"))
        encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
        dispatched = True
        result = json.loads(send(encoded))
        if not isinstance(result, dict):
            raise ValueError("Invalid native intersection response.")
        if mutation and result.get("status") == "success":
            detail = result.get("result")
            if (result.get("result_error") or not isinstance(detail, dict) or detail.get("edited") is not True
                    or detail.get("keep_id") != a["object_id"] or detail.get("trim_id") != b["object_id"]
                    or type(detail.get("geometry_crc")) is not int
                    or detail.get("geometry_crc") == detail.get("previous_geometry_crc")):
                result.update(status="error", error_code="intersection_resolution_unconfirmed",
                              mutation_state="unknown", requires_reconciliation=True,
                              message="Subtraction ran but its result is unconfirmed. Inspect the target before any retry.")
        return json.dumps(result, ensure_ascii=False)
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        return json.dumps({**error_payload(str(exc), error_code="intersection_request_failed"),
                           "mutation_state": "unknown" if dispatched else "not_started",
                           "requires_reconciliation": dispatched})
    except Exception as exc:
        return json.dumps({**error_payload(str(exc), error_code="intersection_bridge_error"),
                           "mutation_state": "unknown" if dispatched else "not_started",
                           "requires_reconciliation": dispatched})
