"""Validate capture requests and preserve uncertainty after a live-view dispatch."""
import json
from uuid import UUID

from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload


def execute(send, name, *, scale_percent=75, include_usage=False, display_mode="", labels=False,
            depth=1, width=None, height=None, expected_model_path="", **target):
    changes_view = name == "get_current_viewcapture" and bool(target.get("target_ids") or display_mode)
    try:
        if type(scale_percent) is not int or not 1 <= scale_percent <= 100:
            raise ValueError("scale_percent must be an integer from 1 to 100.")
        if type(include_usage) is not bool or type(labels) is not bool or type(depth) is not int or not 1 <= depth <= 8:
            raise ValueError("include_usage/labels must be booleans and depth an integer from 1 to 8.")
        if not isinstance(display_mode, str) or len(display_mode) > 512:
            raise ValueError("display_mode must be an installed name or ID of at most 512 characters.")
        explicit_size = width is not None or height is not None
        if explicit_size and (type(width) is not int or type(height) is not int or
                              not 128 <= width <= 2048 or not 128 <= height <= 2048 or scale_percent != 100):
            raise ValueError("Explicit width and height must both be 128..2048 pixels with scale_percent=100.")
        if name == "get_defined_viewcapture":
            if target["target_kind"] not in ("named_view", "layout") or not isinstance(target["target"], str) or not target["target"].strip():
                raise ValueError("Specify target_kind named_view/layout and a nonempty name or ID as target.")
            if target["target_kind"] == "layout" and (explicit_size or display_mode):
                raise ValueError("Layout captures use their paper size and detail display modes; omit pixels and display_mode.")
        elif name == "get_current_viewcapture":
            kind, ids, isolate = target["target_kind"], target["target_ids"], target["isolate"]
            if kind not in ("object", "group", "block", "holon") or type(isolate) is not bool:
                raise ValueError("Use target_kind object/group/block/holon and boolean isolate.")
            if ids is None:
                if isolate or kind != "object":
                    raise ValueError("target_ids are required for isolation or a nondefault target_kind.")
                target.pop("target_ids")
            else:
                if not isinstance(ids, list) or not ids or any(not isinstance(v, str) or not v.strip() for v in ids):
                    raise ValueError("target_ids must be a nonempty array of strings when supplied.")
                if kind != "holon":
                    if any(UUID(v).int == 0 for v in ids):
                        raise ValueError("Target GUIDs must not be empty.")
                    ids = [str(UUID(v)) for v in ids]
                target["target_ids"] = list(dict.fromkeys(ids))
        else:
            raise ValueError("Unknown capture tool.")
        request = {"type": name, "scale_percent": scale_percent, "display_mode": display_mode,
                   "labels": labels, "depth": depth, "expected_model_path": bound_model_path(expected_model_path), **target}
        if explicit_size:
            request.update(width=width, height=height)
        payload = json.dumps(request, allow_nan=False).encode("utf-8")
        if len(payload) > 262144:
            raise ValueError("Capture request exceeds 256 KiB; narrow the target set.")
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        return {**error_payload(str(exc), error_code="invalid_arguments"), "mutation_applied": False}
    try:
        observed = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(observed, dict) or observed.get("status") != "success" or observed.get("capabilities", {}).get("view_capture") != 1:
            raise ValueError("Load the matching Bridge with view_capture=1 before using the split capture tools.")
    except Exception as exc:
        return {**error_payload(str(exc), error_code="unsupported_view_capture"), "mutation_applied": False}
    try:
        response = json.loads(send(payload))
        if not isinstance(response, dict) or response.get("status") not in ("success", "error"):
            raise ValueError("The capture response must contain status success/error.")
        if changes_view and "mutation_applied" not in response:
            raise ValueError("The capture response omitted the live-view change outcome.")
        return response
    except Exception as exc:
        return {**error_payload(f"Capture completion could not be read: {exc}", error_code="capture_bridge_error"),
                "mutation_applied": None if changes_view else False, "requires_reconciliation": changes_view}
