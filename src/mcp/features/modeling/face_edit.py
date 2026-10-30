"""One fixed planar-face operation; the native executor owns Undo and completion."""
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


def dispatch(payload, send):
    """Gate before dispatch, retain native evidence, and never replay a mutation."""
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") != "success":
            raise ValueError("Could not verify the bound Bridge's face-edit capability.")
        if context.get("capabilities", {}).get("face_edit") != 1:
            return dict(status="error", error_code="unsupported_face_edit", mutation_state="not_started",
                        message="Load a Bridge with face_edit=1 before editing a planar face.")
        dispatched = True
        response = json.loads(send(json.dumps({"type": "edit_planar_face", **payload}).encode("utf-8"), timeout=60.0))
        if not isinstance(response, dict):
            raise ValueError("The Bridge returned an invalid face-edit execution result.")
        if response.get("status") != "success":
            return response
        edit = response.get("result")
        if (response.get("result_error") or not isinstance(edit, dict)
                or edit.get("edited") is not True or edit.get("object_id") != payload["object_id"]
                or edit.get("previous_geometry_crc") != payload["expected_geometry_crc"]
                or type(edit.get("geometry_crc")) is not int
                or not 0 <= edit["geometry_crc"] <= 0xFFFFFFFF
                or edit["geometry_crc"] == payload["expected_geometry_crc"]):
            response.update(status="error", error_code="face_edit_result_unconfirmed",
                            mutation_state="unknown", requires_reconciliation=True,
                            message="Face editing ran but its result is unconfirmed. Inspect the object before any retry.")
        return response
    except Exception as exc:
        return dict(status="error", error_code="face_edit_unconfirmed" if dispatched else "face_edit_not_started",
                    mutation_state="unknown" if dispatched else "not_started",
                    requires_reconciliation=dispatched, message=str(exc))
