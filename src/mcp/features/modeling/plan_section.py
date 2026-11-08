"""Typed PlanSection requests; never send caller-authored scripts or file paths."""
from __future__ import annotations

import json
import math
import uuid


def request(operation, clipping_ids, points, hatch, elevation, small_details,
            near_width, far_width, near_dark, far_dark, model_path):
    if operation not in ("Create", "Update"):
        raise ValueError("operation must be Create or Update.")
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
    if points is not None and (not isinstance(points, dict) or operation != "Create"):
        raise ValueError("points is a GUID-to-coordinate object for Create only; omit it for Update.")
    placements = {}
    for key, values in (points or {}).items():
        identity = str(uuid.UUID(key))
        if identity not in ids or identity in placements:
            raise ValueError("Each placement must name one requested clipping GUID exactly once.")
        if (not isinstance(values, list) or len(values) not in (2, 3)
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in values)):
            raise ValueError("Placement coordinates must be finite [x,y] or [x,y,z] in document units.")
        placements[identity] = list(values)
    if any(type(value) is not bool for value in (hatch, elevation, small_details)):
        raise ValueError("hatch, elevation and small_details must be booleans.")
    numbers = (near_width, far_width, near_dark, far_dark)
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in numbers):
        raise ValueError("Line widths and darkness must be finite numbers.")
    if not 0 < far_width <= near_width or not 0 <= far_dark <= near_dark <= 100:
        raise ValueError("Require 0 < far_width <= near_width and 0 <= far_dark <= near_dark <= 100.")
    if not isinstance(model_path, str) or not model_path.strip():
        raise ValueError("A bound saved model path is required.")
    return dict(type="plan_section", operation=operation, clipping_ids=ids, points=placements,
                hatch=hatch, elevation=elevation, small_details=small_details,
                near_width=near_width, far_width=far_width, near_dark=near_dark, far_dark=far_dark,
                expected_model_path=model_path)


def dispatch(payload, send):
    """Check capability, send once, and distinguish execution from drawing completion."""
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") != "success":
            raise ValueError("Could not verify the bound Bridge's PlanSection capability.")
        version = context.get("capabilities", {}).get("plan_section")
        if type(version) is not int or version != 1:
            return dict(status="error", error_code="unsupported_plan_section", mutation_state="not_started",
                        message="Load a Bridge with plan_section=1 before generating drawings.")
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
        if result.get("result_error") or not _confirmed(drawing, payload["clipping_ids"]):
            result.update(status="error", error_code="plan_section_result_unconfirmed",
                          mutation_state="unknown", requires_reconciliation=True,
                          message="PlanSection ran but its result is unconfirmed. Inspect drawings before retrying.")
            return result
        result["status"] = "success" if drawing["status"] == "completed" else drawing["status"]
        result["drawing_status"] = drawing["status"]
        return result
    except Exception as exc:
        return dict(status="error", error_code="plan_section_unconfirmed" if dispatched else "plan_section_not_started",
                    mutation_state="unknown" if dispatched else "not_started",
                    requires_reconciliation=dispatched, message=str(exc))


def _confirmed(drawing, ids):
    if isinstance(drawing, dict) and drawing.get("result_delivery") == "paged":
        return (drawing.get("status") in ("completed", "partial", "cancelled")
                and type(drawing.get("requested")) is int and drawing["requested"] == len(ids)
                and type(drawing.get("completed")) is int and 0 <= drawing["completed"] <= len(ids)
                and (drawing["status"] != "completed" or drawing["completed"] == len(ids))
                and isinstance(drawing.get("result_id"), str) and len(drawing["result_id"]) == 32
                and all(c in "0123456789abcdef" for c in drawing["result_id"])
                and type(drawing.get("result_characters")) is int and drawing["result_characters"] > 0
                and isinstance(drawing.get("result_sha256"), str) and len(drawing["result_sha256"]) == 64)
    if (not isinstance(drawing, dict) or drawing.get("status") not in ("completed", "partial", "cancelled")
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
        completed += item["status"] == "completed"
    return (completed == drawing["completed"]
            and (drawing["status"] != "completed" or completed == len(ids)))
