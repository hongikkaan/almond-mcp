"""Strict adapter for the active model viewport's relative camera operations."""
import json
import math
from uuid import UUID

from fastmcp.tools import ToolResult
from mcp.types import TextContent

from almond_mcp.managed_paths import bound_model_path


def _reply(body, detail=""):
    return ToolResult(
        content=[TextContent(type="text", text=detail or json.dumps(body))],
        structured_content=body,
        is_error=body["status"] == "error",
    )


def _error(code, detail, applied=False):
    return _reply({"status": "error", "error_code": code, "mutation_applied": applied,
                   "requires_reconciliation": applied is None}, detail)


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Camera arguments must be finite numbers.")
    return value


def execute(send, operation, *, mode=None, yaw_deg=None, pitch_deg=None, factor=None,
            expected_viewport_id=None, expected_model_path=None):
    try:
        request = {"type": "manipulate_view", "operation": operation,
                   "expected_model_path": bound_model_path(expected_model_path or "")}
        if expected_viewport_id is not None:
            viewport = UUID(expected_viewport_id)
            if not viewport.int:
                raise ValueError("expected_viewport_id cannot be empty.")
            request["expected_viewport_id"] = str(viewport)
        if operation == "rotate":
            if mode not in ("look", "orbit") or factor is not None:
                raise ValueError("Rotate requires mode look/orbit and does not accept factor.")
            yaw = 0 if yaw_deg is None else _number(yaw_deg)
            pitch = 0 if pitch_deg is None else _number(pitch_deg)
            if yaw == 0 and pitch == 0:
                raise ValueError("Specify a nonzero yaw_deg or pitch_deg.")
            request.update(mode=mode, yaw_deg=yaw, pitch_deg=pitch)
        elif operation == "zoom":
            if any(value is not None for value in (mode, yaw_deg, pitch_deg)) or _number(factor) <= 0:
                raise ValueError("Zoom requires only a positive factor.")
            request["factor"] = factor
        else:
            raise ValueError("Use operation rotate or zoom.")
        payload = json.dumps(request, allow_nan=False).encode()
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        return _error("invalid_arguments", str(exc))

    try:
        observation = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        capability = observation["capabilities"]["view_manipulation"]
        if observation.get("status") != "success" or type(capability) is not int or capability != 1:
            raise ValueError("Load the matching Bridge with view_manipulation=1.")
    except Exception:
        return _error("unsupported_view_manipulation", "Could not verify Bridge view_manipulation=1.")

    try:
        response = json.loads(send(payload))
        status, applied = response["status"], response["mutation_applied"]
        if status not in ("success", "error") or (type(applied) is not bool and applied is not None):
            raise ValueError("Bridge did not report a viewport mutation outcome.")
        if type(response.get("requires_reconciliation")) is not bool or response["requires_reconciliation"] != (applied is None):
            raise ValueError("Bridge reconciliation status disagreed with the viewport mutation outcome.")
        if status == "success":
            if applied is None or UUID(response["viewport_id"]).int == 0:
                raise ValueError("Missing verified viewport mutation outcome or viewport ID.")
            if expected_viewport_id is not None and UUID(response["viewport_id"]) != viewport:
                raise ValueError("Bridge response disagreed with the expected viewport.")
            for key in ("camera_location", "camera_target"):
                point = response[key]
                if not isinstance(point, list) or len(point) != 3:
                    raise ValueError("Invalid verified camera coordinates.")
                for coordinate in point:
                    _number(coordinate)
        elif applied is True or not isinstance(response.get("error_code"), str) or not response["error_code"].strip():
            raise ValueError("Bridge reported an inconsistent viewport failure.")
        detail = response.pop("message", "")
        return _reply(response, detail)
    except Exception:
        # The operation is relative, so replay after a lost reply could double the move.
        return _error("view_manipulation_bridge_error",
                      "Verify the current viewport before applying another relative operation.", None)
