"""Typed PlanSection requests; never send caller-authored scripts or file paths."""
from __future__ import annotations

import json
import math
import uuid


def request(operation, clipping_ids, points, hatch, small_details, include_references,
            near_width, far_width, near_dark, far_dark, model_path, request_id=""):
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
    if points is not None and (not isinstance(points, dict) or operation not in ("Create", "Move")):
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
    if any(type(value) is not bool for value in (hatch, small_details, include_references)):
        raise ValueError("hatch, small_details and include_references must be booleans.")
    if request_id:
        request_id = str(uuid.UUID(request_id))
        if not uuid.UUID(request_id).int:
            raise ValueError("request_id cannot be an empty UUID.")
    numbers = (near_width, far_width, near_dark, far_dark)
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in numbers):
        raise ValueError("Line widths and darkness must be finite numbers.")
    if not 0 < far_width <= near_width or not 0 <= far_dark <= near_dark <= 100:
        raise ValueError("Require 0 < far_width <= near_width and 0 <= far_dark <= near_dark <= 100.")
    if not isinstance(model_path, str) or not model_path.strip():
        raise ValueError("A bound saved model path is required.")
    return dict(type="plan_section", operation=operation, clipping_ids=ids, points=placements,
                hatch=hatch, small_details=small_details, include_references=include_references, request_id=request_id,
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
        if result.get("response_replayed") is True and result.get("historical_response") is True:
            result["recorded_mutation_state"] = result.get("mutation_state", "unknown")
            result["historical_drawing_status"] = result.pop("drawing_status", None) or (result.get("result") or {}).get("status")
            result.update(status="error", error_code="plan_section_historical_response",
                          mutation_state="unknown", requires_reconciliation=True,
                          next_step_guide="과거 프로세스·문서의 실행 응답입니다. 저장되지 않은 출력이 현재 문서에 없을 수 있으므로 현재 도면을 확인합니다. 같은 요청은 다시 생성하지 않았습니다.")
            return result
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
        if (result.get("mutation_state") == "unknown" or result.get("requires_reconciliation") is True
                or isinstance(drawing, dict) and (drawing.get("mutation_state") == "unknown"
                    or drawing.get("requires_reconciliation") is True
                    or any(isinstance(item, dict) and (item.get("mutation_state") == "unknown"
                           or item.get("requires_reconciliation") is True) for item in drawing.get("results", [])))):
            result.update(status="error", error_code="plan_section_mutation_unconfirmed", mutation_state="unknown",
                          requires_reconciliation=True,
                          next_step_guide="문서 복구 또는 수정 완료 상태가 불확실합니다. 현재 출력과 실행 상태를 확인하고 복구하기 전에는 자동 재실행하거나 새 request_id로 생성·갱신하지 않습니다.")
            return result
        if (isinstance(drawing, dict) and drawing.get("result_delivery") == "unavailable"
                and drawing.get("status") in ("completed", "partial", "cancelled")
                and type(drawing.get("requested")) is int and drawing["requested"] == len(payload["clipping_ids"])
                and type(drawing.get("completed")) is int and 0 <= drawing["completed"] <= drawing["requested"]
                and (drawing["status"] != "completed" or drawing["completed"] == drawing["requested"])):
            result.update(status="error", error_code="plan_section_response_incomplete",
                          drawing_status=drawing["status"],
                          mutation_state="completed" if drawing["status"] == "completed" else "partial",
                          requires_reconciliation=True,
                          next_step_guide=("생성 완료 상태는 확인됐습니다. 응답 상세가 부족하다는 이유만으로 재생성하지 말고 기존 도면을 확인합니다."
                                           if drawing["status"] == "completed" else
                                           "도면이 불완전하거나 취소됐으며 응답 상세도 부족합니다. 기존 출력과 필요한 clipping을 확인한 뒤 필요한 경우에만 새 request_id로 drawing_06-generate_plan_section tool의 Create 또는 Update를 실행합니다."))
            return result
        if result.get("result_error") or not _confirmed(drawing, payload["clipping_ids"]):
            result.update(status="error", error_code="plan_section_result_unconfirmed",
                          mutation_state="unknown", requires_reconciliation=True,
                          message="PlanSection ran but its result is unconfirmed. Retry with the same request_id to recover the retained response without regenerating; if no request_id was supplied, inspect drawings before retrying.")
            return result
        result["status"] = "success" if drawing["status"] == "completed" else drawing["status"]
        result["drawing_status"] = drawing["status"]
        if drawing["status"] != "completed":
            result["next_step_guide"] = "도면이 불완전합니다. 실패한 clipping을 확인한 뒤 새 request_id로 drawing_06-generate_plan_section tool의 Create 또는 Update를 실행합니다. 기존 유효 도면은 보존됩니다."
        return result
    except Exception as exc:
        return dict(status="error", error_code="plan_section_unconfirmed" if dispatched else "plan_section_not_started",
                    mutation_state="unknown" if dispatched else "not_started",
                    requires_reconciliation=dispatched, request_id=payload.get("request_id", ""),
                    next_step_guide=("외부 연결의 native 완료 fence가 해제·회복된 뒤 같은 request_id와 동일 입력으로 drawing_06-generate_plan_section tool을 호출하면 보관된 완료 응답을 회수합니다. pending/unknown 동안 새 요청으로 자동 재생성하지 말고 기존 도면과 실행 상태를 먼저 확인합니다."
                                     if payload.get("request_id") else "응답 유실은 생성 실패를 뜻하지 않습니다. 기존 도면과 실행 상태를 확인하기 전 자동 재생성하지 않습니다."),
                    message=str(exc))


def _confirmed(drawing, ids):
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
