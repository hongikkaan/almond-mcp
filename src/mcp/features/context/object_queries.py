"""Bounded, capability-gated fixed observations of ordinary Rhino objects."""
import json
import uuid

from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload


def object_ids(value, maximum, *, required=False):
    if not isinstance(value, list) or len(value) > maximum or (required and not value):
        raise ValueError(f"object_ids must contain {'1' if required else '0'}..{maximum} GUIDs.")
    normalized = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("object_ids must be GUID strings.")
        parsed = uuid.UUID(item)
        if not parsed.int:
            raise ValueError("object_ids must not contain the empty GUID.")
        normalized.append(str(parsed))
    if len(set(normalized)) != len(normalized):
        raise ValueError("object_ids must be distinct.")
    return normalized


def validate_filters(filters):
    if not isinstance(filters, dict) or set(filters) - {"layer_paths", "name_contains", "user_dictionary"}:
        raise ValueError("filters supports layer_paths, name_contains and user_dictionary only.")
    if "layer_paths" in filters:
        layers = filters["layer_paths"]
        if not isinstance(layers, list) or not 1 <= len(layers) <= 64 or any(not isinstance(v, str) or not v for v in layers):
            raise ValueError("layer_paths requires 1..64 exact full layer paths.")
    if "name_contains" in filters and (not isinstance(filters["name_contains"], str) or len(filters["name_contains"]) > 256):
        raise ValueError("name_contains must be a string of at most 256 characters.")
    conditions = filters.get("user_dictionary", [])
    if not isinstance(conditions, list) or len(conditions) > 16:
        raise ValueError("user_dictionary must contain at most 16 conditions.")
    for condition in conditions:
        if (not isinstance(condition, dict) or set(condition) != {"source", "key", "any_of"}
                or condition["source"] not in ("attributes", "geometry")
                or not isinstance(condition["key"], str) or not condition["key"]
                or not isinstance(condition["any_of"], list) or not 1 <= len(condition["any_of"]) <= 64
                or any(type(v) not in (str, bool, int, float) for v in condition["any_of"])):
            raise ValueError("Dictionary conditions require source=attributes|geometry, key and 1..64 scalar any_of values.")
    return filters


def query(send, *, scope, ids, filters, include_geometry, offset, limit, expected_model_path):
    try:
        if scope not in ("visible", "selected", "ids", "document"):
            raise ValueError("scope must be visible, selected, ids or document.")
        ids = object_ids(ids, 4096, required=scope == "ids")
        if ids and scope != "ids":
            raise ValueError("object_ids requires scope=ids.")
        if type(offset) is not int or not 0 <= offset <= 100000 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("offset must be 0..100000 and limit 1..200.")
        if type(include_geometry) is not bool:
            raise ValueError("include_geometry must be boolean.")
        payload = dict(type="get_rhino_objects", scope=scope, object_ids=ids, filters=validate_filters(filters),
                       include_geometry=include_geometry, offset=offset, limit=limit)
        return dispatch(send, payload, expected_model_path)
    except (TypeError, ValueError, AttributeError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))


def intersections(send, *, ids, max_pairs, expected_model_path):
    try:
        ids = object_ids(ids, 512, required=True)
        if type(max_pairs) is not int or not 1 <= max_pairs <= 64:
            raise ValueError("max_pairs must be an integer in 1..64.")
        return dispatch(send, dict(type="get_object_intersections", object_ids=ids, max_pairs=max_pairs), expected_model_path)
    except (TypeError, ValueError, AttributeError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))


def dispatch(send, payload, expected_model_path):
    try:
        payload["expected_model_path"] = bound_model_path(expected_model_path)
        encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
        if len(encoded) > 262144:
            raise ValueError("Object observation request exceeds 256 KiB.")
    except (TypeError, ValueError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
    try:
        raw = send(b'{"type":"get_rhino_context","selection_limit":0,"sections":[]}')
        snapshot = json.loads(raw)
        if not isinstance(snapshot, dict) or snapshot.get("status") not in ("success", "error"):
            raise ValueError("Bridge returned an invalid context response.")
        if snapshot["status"] == "error":
            return raw
        if snapshot.get("capabilities", {}).get("object_observation") != 1:
            return json.dumps(error_payload("Load a Bridge with object_observation=1 before using object queries.",
                                           error_code="unsupported_object_observation"))
        return send(encoded)
    except Exception as exc:
        return json.dumps(error_payload(f"Could not observe Rhino objects: {exc}", error_code="bridge_error"))
