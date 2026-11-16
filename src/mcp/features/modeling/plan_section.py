"""Typed PlanSection requests; never send caller-authored scripts or file paths."""
from __future__ import annotations

import json
import math
import uuid


def request(operation, clipping_ids, points, hatch, small_details,
            near_width, far_width, near_dark, far_dark, model_path, include_attachments=None):
    if operation not in ("Create", "Update", "Move"):
        raise ValueError("operation must be Create, Update or Move.")
    if not isinstance(clipping_ids, list) or not clipping_ids:
        raise ValueError("clipping_ids must contain nonempty GUIDs.")
    ids = []
    for value in clipping_ids:
        if not isinstance(value, str):
            raise ValueError("clipping_ids must contain GUID strings.")
        identity = uuid.UUID(value)
        if not identity.int:
            raise ValueError("A clipping GUID cannot be empty.")
        if str(identity) not in ids:
            ids.append(str(identity))
    if points is not None and (not isinstance(points, dict) or operation == "Update"):
        raise ValueError("points is a GUID-to-coordinate object for Create or Move; omit it for Update.")
    placements = {}
    for key, values in (points or {}).items():
        identity = str(uuid.UUID(key))
        if identity not in ids or identity in placements:
            raise ValueError("Each placement must name one requested clipping GUID exactly once.")
        if (not isinstance(values, list) or len(values) not in (2, 3)
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in values)):
            raise ValueError("Placement coordinates must be finite [x,y] or [x,y,z] in document units.")
        placements[identity] = list(values)
    if operation == "Move" and len(placements) != len(ids):
        raise ValueError("Move requires a placement point for every clipping GUID.")
    if any(type(value) is not bool for value in (hatch, small_details)):
        raise ValueError("hatch and small_details must be booleans.")
    numbers = (near_width, far_width, near_dark, far_dark)
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in numbers):
        raise ValueError("Line widths and darkness must be finite numbers.")
    if not 0 < far_width <= near_width or not 0 <= far_dark <= near_dark <= 100:
        raise ValueError("Require 0 < far_width <= near_width and 0 <= far_dark <= near_dark <= 100.")
    if not isinstance(model_path, str) or not model_path.strip():
        raise ValueError("A bound saved model path is required.")
    if include_attachments is not None and type(include_attachments) is not bool:
        raise ValueError("include_attachments must be boolean or omitted.")
    payload = dict(type="plan_section", operation=operation, clipping_ids=ids, points=placements,
                   hatch=hatch, small_details=small_details,
                   near_width=near_width, far_width=far_width, near_dark=near_dark, far_dark=far_dark,
                   expected_model_path=model_path)
    if include_attachments is not None and operation != "Move":
        payload["include_attachments"] = include_attachments
    return payload


def dispatch(payload, send):
    """Check capability, send once, and distinguish execution from drawing completion."""
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") != "success":
            raise ValueError("Could not verify the bound Bridge's PlanSection capability.")
        version = context.get("capabilities", {}).get("plan_section")
        if type(version) is not int or version != 2:
            return dict(status="error", error_code="unsupported_plan_section", mutation_state="not_started",
                        message="Load a Bridge with plan_section=2 before generating drawings.")
        dispatched = True
        result = json.loads(send(json.dumps(payload).encode("utf-8"), timeout=600.0))
        if not isinstance(result, dict):
            raise ValueError("The Bridge returned an invalid PlanSection response.")
        if result.get("status") != "success":
            if result.get("status") not in (None, "error"):
                result["native_status"] = result["status"]
            result["status"] = "error"
            if result.get("mutation_state") not in {"not_started", "unknown", "partial", "completed"}:
                result["mutation_state"] = "unknown"
            if result["mutation_state"] == "unknown":
                result["requires_reconciliation"] = True
            return result
        drawing = result.get("result")
        operation = payload["operation"]
        include_attachments = payload.get("include_attachments", False if operation == "Create" else None)
        if result.get("result_error") or not _confirmed(drawing, payload["clipping_ids"], operation, include_attachments):
            result.update(status="error", error_code="plan_section_result_unconfirmed",
                          mutation_state="unknown", requires_reconciliation=True,
                          message="PlanSection ran but its result is unconfirmed. Inspect drawings before retrying.")
            return result
        drawing_status = drawing["status"]
        result["drawing_status"] = drawing_status
        if drawing_status == "failed":
            result.update(status="error", error_code="plan_section_failed",
                          message="No drawing completed. See the result for each clipping plane.")
        else:
            result["status"] = "success" if drawing_status == "completed" else drawing_status
        return result
    except Exception as exc:
        return dict(status="error", error_code="plan_section_unconfirmed" if dispatched else "plan_section_not_started",
                    mutation_state="unknown" if dispatched else "not_started",
                    requires_reconciliation=dispatched, message=str(exc))


def _confirmed(drawing, ids, operation, include_attachments):
    if (not isinstance(drawing, dict)
            or drawing.get("status") not in ("completed", "partial", "cancelled", "failed")
            or type(drawing.get("requested")) is not int or drawing["requested"] != len(ids)
            or type(drawing.get("completed")) is not int
            or not 0 <= drawing["completed"] <= drawing["requested"]
            or not isinstance(drawing.get("results"), list) or len(drawing["results"]) > len(ids)):
        return False
    seen, completed = set(), 0
    for item in drawing["results"]:
        if (not isinstance(item, dict) or item.get("clipping_id") not in ids
                or item["clipping_id"] in seen
                or item.get("status") not in ("completed", "failed", "skipped", "cancelled")):
            return False
        seen.add(item["clipping_id"])
        if item["status"] == "completed":
            if not _placed(item, operation, include_attachments):
                return False
            completed += 1
    status = drawing["status"]
    if completed != drawing["completed"]:
        return False
    if status == "cancelled":
        return True  # Cancellation may leave untouched clipping planes.
    if len(seen) != len(ids):
        return False
    return status == ("completed" if completed == len(ids) else "partial" if completed else "failed")


def _placed(item, operation, include_attachments):
    plane = item.get("draw_plane")
    if not isinstance(plane, dict) or any(
        not isinstance(plane.get(key), list) or len(plane[key]) != 3
        or any(type(x) not in (int, float) or not math.isfinite(x) for x in plane[key])
        for key in ("origin", "xaxis", "yaxis")
    ):
        return False
    if not isinstance(item.get("object_ids"), list):
        return False
    if operation == "Move":
        return bool(item["object_ids"])
    extraction = item.get("extraction")
    return (
        isinstance(extraction, dict)
        and isinstance(extraction.get("layers"), list)
        and all(isinstance(name, str) for name in extraction["layers"])
        and type(extraction.get("source_object_count")) is int
        and extraction["source_object_count"] >= 0
        and all(type(extraction.get(key)) is bool
                for key in ("include_hidden", "include_locked", "include_attachments"))
        and (include_attachments is None or extraction["include_attachments"] is include_attachments)
    )
