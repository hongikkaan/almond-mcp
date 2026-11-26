"""Typed PlanSection requests; never send caller-authored scripts or file paths."""
from __future__ import annotations

import json
import math
import uuid

UNCONFIRMED_GUIDE = ("Rhino 작업의 중단과 최종 도면 상태를 확인하세요. "
                     "확인 전에는 같은 클리핑 요청을 다시 실행하지 마세요.")


def _clipping_ids(clipping_ids):
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
    return ids


def unconfirmed_result(clipping_ids, message):
    detail = f"{message}\n{UNCONFIRMED_GUIDE}" if message else UNCONFIRMED_GUIDE
    result = dict(status="error", error_code="plan_section_unconfirmed", mutation_state="unknown",
                  requires_reconciliation=True, message=detail)
    try:
        result["unconfirmed_clipping_ids"] = _clipping_ids(clipping_ids)
    except ValueError:
        pass  # A broker can lose a worker response before worker-side input validation.
    return result


def request(operation, clipping_ids, points, hatch, small_details,
            near_width, far_width, near_dark, far_dark, model_path, include_attachments=None,
            section_width_source="source"):
    if operation not in ("Create", "Update", "Move"):
        raise ValueError("operation must be Create, Update or Move.")
    ids = _clipping_ids(clipping_ids)
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
    if section_width_source not in ("source", "output_layer"):
        raise ValueError("section_width_source must be source or output_layer.")
    payload = dict(type="plan_section", operation=operation, clipping_ids=ids, points=placements,
                   hatch=hatch, small_details=small_details,
                   near_width=near_width, far_width=far_width, near_dark=near_dark, far_dark=far_dark,
                   expected_model_path=model_path)
    if include_attachments is not None and operation != "Move":
        payload["include_attachments"] = include_attachments
    if operation != "Move":
        payload["section_width_source"] = section_width_source
    return payload


def dispatch(payload, send):
    """Check capability, send once, and distinguish execution from drawing completion."""
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") != "success":
            raise ValueError("Could not verify the bound Bridge's PlanSection capability.")
        version = context.get("capabilities", {}).get("plan_section")
        if type(version) is not int or version != 4:
            return dict(status="error", error_code="unsupported_plan_section", mutation_state="not_started",
                        message="120초 취소와 클리핑별 결과를 지원하는 Bridge(plan_section=4)를 로드한 뒤 도면을 생성하세요.")
        dispatched = True
        result = json.loads(send(json.dumps(payload).encode("utf-8"), timeout=600.0))
        if not isinstance(result, dict):
            raise ValueError("The Bridge returned an invalid PlanSection response.")
        drawing = result.pop("result", None)
        operation = payload["operation"]
        include_attachments = payload.get("include_attachments", False if operation == "Create" else None)
        confirmed = not result.get("result_error") and _confirmed(drawing, payload["clipping_ids"], operation, include_attachments)
        if confirmed:
            result.update(completed=drawing["completed"], requested=drawing["requested"], cuts=drawing["results"])
            if "stop_reason" in drawing:
                result["stop_reason"] = drawing["stop_reason"]
            unresolved = [item["clipping_id"] for item in drawing["results"]
                          if item.get("mutation_state") == "unknown" or item.get("cleanup_error")
                          or item.get("recovery", {}).get("requires_reconciliation")]
            if unresolved:
                result["unconfirmed_clipping_ids"] = unresolved
                result["requires_reconciliation"] = True
                result.setdefault("message", UNCONFIRMED_GUIDE)
        if result.get("status") != "success":
            if result.get("status") not in (None, "error"):
                result["native_status"] = result["status"]
            result["status"] = "error"
            if result.get("mutation_state") not in {"not_started", "unknown", "partial", "completed"}:
                result["mutation_state"] = "unknown"
            if result["mutation_state"] == "unknown":
                result["requires_reconciliation"] = True
                result.setdefault("message", UNCONFIRMED_GUIDE)
                if not confirmed:
                    result["unconfirmed_clipping_ids"] = payload["clipping_ids"]
                    if isinstance(drawing, dict) and drawing.get("status") == "unconfirmed":
                        cuts = drawing.get("results")
                        if (isinstance(cuts, list) and all(isinstance(i, dict) and i.get("status") in
                                ("unconfirmed", "not_started") for i in cuts)
                                and [i.get("clipping_id") for i in cuts] == payload["clipping_ids"]):
                            result.update(requested=len(cuts), cuts=cuts)
                            result["unconfirmed_clipping_ids"] = [i["clipping_id"] for i in cuts if i["status"] == "unconfirmed"]
            return result
        if not confirmed:
            result.update(status="error", error_code="plan_section_result_unconfirmed",
                          mutation_state="unknown", requires_reconciliation=True,
                          unconfirmed_clipping_ids=payload["clipping_ids"], message=UNCONFIRMED_GUIDE)
            return result
        drawing_status = drawing["status"]
        if drawing_status == "failed":
            result.update(status="error", error_code="plan_section_failed",
                          message="완료를 확인한 컷이 없습니다. 클리핑별 결과와 관찰된 객체 GUID를 확인하세요.")
        elif drawing_status == "cancelled" and drawing.get("stop_reason") == "deadline":
            if result.get("requires_reconciliation") or drawing.get("requires_reconciliation"):
                result.update(status="error", error_code="plan_section_recovery_unconfirmed",
                              requires_reconciliation=True,
                              message=f"취소 요청을 받았으나 변경 복구를 확인할 수 없는 컷이 있습니다. {UNCONFIRMED_GUIDE}")
            else:
                result.update(status="timeout", message="120초 취소 요청 후 Rhino가 중단과 정리를 완료했습니다.")
        else:
            result["status"] = "success" if drawing_status == "completed" else drawing_status
        return result
    except Exception as exc:
        if dispatched:
            return unconfirmed_result(payload["clipping_ids"], str(exc))
        return dict(status="error", error_code="plan_section_not_started", mutation_state="not_started",
                    requires_reconciliation=False, message=str(exc))


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
                or item.get("status") not in ("completed", "failed", "skipped", "cancelled", "not_started")):
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
        states = [item["status"] for item in drawing["results"]]
        if len(seen) != len(ids) or drawing.get("stop_reason") not in ("deadline", "user"):
            return False
        # A sequential batch reports every requested cut; unstarted cuts form its tail.
        if [item["clipping_id"] for item in drawing["results"]] != ids:
            return False
        first = next((i for i, state in enumerate(states) if state in ("cancelled", "not_started")), len(ids))
        return first < len(ids) and all(state == "not_started" for state in states[first+1:])
    if "stop_reason" in drawing or any(i["status"] in ("cancelled", "not_started") for i in drawing["results"]):
        return False
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
