"""Fixed single and batch face edits; the native executor owns Undo and completion."""
from __future__ import annotations

import json
import math
import uuid

def request(object_id, face_index, expected_geometry_crc, translation, model_path):
    try:
        identity = uuid.UUID(object_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("object_id must be a nonempty object GUID.") from exc
    if not identity.int:
        raise ValueError("object_id must be a nonempty object GUID.")
    if type(face_index) is not int or not 0 <= face_index <= 0x7FFFFFFF:
        raise ValueError("face_index must be a nonnegative int32 from a current Brep observation.")
    if type(expected_geometry_crc) is not int or not 0 <= expected_geometry_crc <= 0xFFFFFFFF:
        raise ValueError("expected_geometry_crc must be the observed uint32 geometry_crc.")
    if (not isinstance(translation, list) or len(translation) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in translation)
            or not any(translation)):
        raise ValueError("translation must contain three finite numbers and be nonzero, in document units.")
    if not isinstance(model_path, str) or not model_path.strip():
        raise ValueError("A bound model path is required.")
    return dict(object_id=str(identity), face_index=face_index,
                expected_geometry_crc=expected_geometry_crc,
                translation=translation, expected_model_path=model_path)


def batch_request(edits, model_path):
    if not isinstance(edits, list) or not 1 <= len(edits) <= 32:
        raise ValueError("edits must contain 1..32 face-edit objects.")
    normalized, identities = [], set()
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"object_id", "face_index", "expected_geometry_crc", "translation"}:
            raise ValueError("Each edit needs object_id, face_index, expected_geometry_crc and translation only.")
        item = request(**edit, model_path=model_path)
        item.pop("expected_model_path")
        if item["object_id"] in identities:
            raise ValueError("A batch accepts one face per distinct object; observe changed faces before another edit of the same object.")
        identities.add(item["object_id"])
        normalized.append(item)
    return dict(edits=normalized, expected_model_path=model_path)


def _confirmed_edit(edit, expected):
    return (isinstance(edit, dict) and edit.get("edited") is True
            and edit.get("object_id") == expected["object_id"]
            and edit.get("previous_geometry_crc") == expected["expected_geometry_crc"]
            and type(edit.get("geometry_crc")) is int and 0 <= edit["geometry_crc"] <= 0xFFFFFFFF
            and edit["geometry_crc"] != expected["expected_geometry_crc"])


def dispatch(payload, send, *, batch=False):
    """Gate before dispatch, retain native evidence, and never replay a mutation."""
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") != "success":
            raise ValueError("Could not verify the bound Bridge's face-edit capability.")
        capability = "face_edit_batch" if batch else "face_edit"
        version = context.get("capabilities", {}).get(capability, 0)
        if type(version) is not int or version < 1:
            return dict(status="error", error_code="unsupported_face_edit", mutation_state="not_started",
                        message=f"Load a Bridge with {capability}>=1 before editing planar faces.")
        dispatched = True
        response = json.loads(send(json.dumps({"type": "edit_planar_faces" if batch else "edit_planar_face", **payload}).encode("utf-8"), timeout=60.0))
        if not isinstance(response, dict):
            raise ValueError("The Bridge returned an invalid face-edit execution result.")
        if response.get("status") != "success":
            return response
        edit = response.get("result")
        confirmed = _confirmed_edit(edit, payload) if not batch else (
            isinstance(edit, dict) and edit.get("status") == "success" and edit.get("complete") is True
            and type(edit.get("requested_count")) is int and type(edit.get("applied_count")) is int
            and edit.get("requested_count") == len(payload["edits"])
            and edit.get("applied_count") == len(payload["edits"])
            and edit.get("mutation_state") == "applied"
            and isinstance(edit.get("items"), list) and len(edit["items"]) == len(payload["edits"])
            and all(_confirmed_edit(item, expected) and item.get("status") == "applied"
                    for item, expected in zip(edit["items"], payload["edits"])))
        if response.get("result_error") or not confirmed:
            response.update(status="error", error_code="face_edit_result_unconfirmed",
                            mutation_state="unknown", requires_reconciliation=True,
                            message="Face editing ran but its result is unconfirmed. Inspect the object before any retry.")
        return response
    except Exception as exc:
        return dict(status="error", error_code="face_edit_unconfirmed" if dispatched else "face_edit_not_started",
                    mutation_state="unknown" if dispatched else "not_started",
                    requires_reconciliation=dispatched, message=str(exc))
