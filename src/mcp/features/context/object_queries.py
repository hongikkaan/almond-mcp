"""Bounded, capability-gated fixed observations of ordinary Rhino objects."""
import json
import uuid

from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import project_query, requires_full_evidence
from almond_mcp.managed_paths import relative_output


OBJECT_FIELDS = frozenset({
    "id", "name", "layer_path", "object_type", "geometry_kind", "geometry_crc",
    "visible", "selected", "hidden", "locked", "bounds", "groups", "user_dictionary",
    "geometry_valid", "solid", "manifold", "volume", "faces", "face_count",
})


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
    if not isinstance(filters, dict) or set(filters) - {"layer_paths", "object_types", "name_contains", "user_dictionary"}:
        raise ValueError("filters supports layer_paths, object_types, name_contains and user_dictionary only.")
    if "layer_paths" in filters:
        layers = filters["layer_paths"]
        if not isinstance(layers, list) or not 1 <= len(layers) <= 64 or any(not isinstance(v, str) or not v for v in layers):
            raise ValueError("layer_paths requires 1..64 exact full layer paths.")
    if "name_contains" in filters and (not isinstance(filters["name_contains"], str) or len(filters["name_contains"]) > 256):
        raise ValueError("name_contains must be a string of at most 256 characters.")
    if "object_types" in filters:
        kinds = filters["object_types"]
        if not isinstance(kinds, list) or not 1 <= len(kinds) <= 32 or any(not isinstance(v, str) or not v or len(v) > 64 for v in kinds):
            raise ValueError("object_types requires 1..32 Rhino object_type names from an observation.")
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


def query(send, *, scope, ids, filters, include_geometry, offset, limit, expected_model_path,
          result_mode="objects", fields=None, face_offset=0, face_limit=128,
          expected_geometry_crcs=None, include_ids=False):
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
        if type(include_ids) is not bool:
            raise ValueError("include_ids must be boolean.")
        if result_mode not in ("objects", "summary"):
            raise ValueError("result_mode must be objects or summary.")
        if fields is not None and (not isinstance(fields, list) or not fields
                or any(not isinstance(field, str) or field not in OBJECT_FIELDS for field in fields)
                or len(set(fields)) != len(fields)):
            raise ValueError("fields must be distinct supported object fields: " + ", ".join(sorted(OBJECT_FIELDS)))
        if type(face_offset) is not int or not 0 <= face_offset <= 100000 or type(face_limit) is not int or not 1 <= face_limit <= 128:
            raise ValueError("face_offset must be 0..100000 and face_limit 1..128.")
        crcs = {}
        if expected_geometry_crcs is not None:
            if not isinstance(expected_geometry_crcs, dict) or len(expected_geometry_crcs) > 4096:
                raise ValueError("expected_geometry_crcs must map at most 4096 object GUIDs to observed uint32 CRCs.")
            for key, crc in expected_geometry_crcs.items():
                identity = object_ids([key], 1, required=True)[0]
                if type(crc) is not int or not 0 <= crc <= 0xFFFFFFFF or identity in crcs:
                    raise ValueError("expected_geometry_crcs requires distinct object GUIDs and uint32 CRCs.")
                crcs[identity] = crc
        wants_faces = "faces" in fields if fields is not None else include_geometry
        if (face_offset or face_limit != 128) and not wants_faces:
            raise ValueError("Face pagination requires include_geometry=true or fields containing faces.")
        if crcs and (scope != "ids" or set(crcs) - set(ids)):
            raise ValueError("expected_geometry_crcs keys must belong to the explicit scope=ids object set.")
        if face_offset and (scope != "ids" or set(crcs) != set(ids)):
            raise ValueError("A subsequent face page requires scope=ids and an observed CRC for every object.")
        if result_mode == "summary" and (fields is not None or include_geometry or crcs or face_offset or face_limit != 128):
            raise ValueError("Summary returns layer/type counts; object fields and face options require result_mode=objects.")
        payload = dict(type="get_rhino_objects", scope=scope, object_ids=ids, filters=validate_filters(filters),
                       include_geometry=include_geometry, offset=offset, limit=limit)
        extended = result_mode != "objects" or fields is not None or face_offset or face_limit != 128 or crcs or "object_types" in filters
        if extended:
            payload.update(result_mode=result_mode, fields=fields, face_offset=face_offset,
                           face_limit=face_limit, expected_geometry_crcs=crcs)
        raw = dispatch(send, payload, expected_model_path, required_version=2 if extended else 1)
        value = json.loads(raw)
        if isinstance(value, dict) and requires_full_evidence(value):
            return raw
        # Explicit requested identity fields take precedence over the general query default.
        value = project_query(value, include_ids=include_ids or (fields is not None and bool({"id", "faces"} & set(fields))),
                              supplied={"object_ids": ids})
        return json.dumps(relative_output(value), ensure_ascii=False)
    except (TypeError, ValueError, AttributeError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))


def intersections(send, *, ids, max_pairs, expected_model_path, include_blocks=False, cursor="", include_ids=False):
    try:
        ids = object_ids(ids, 512, required=True)
        if type(max_pairs) is not int or not 1 <= max_pairs <= 64:
            raise ValueError("max_pairs must be an integer in 1..64.")
        if type(include_blocks) is not bool or type(include_ids) is not bool or not isinstance(cursor, str) or len(cursor) > 256:
            raise ValueError("include_blocks/include_ids must be boolean and cursor a string of at most 256 characters.")
        payload = dict(type="get_object_intersections", object_ids=ids, max_pairs=max_pairs)
        if include_blocks:
            payload["include_blocks"] = True
        if cursor:
            payload["cursor"] = cursor
        raw = dispatch(send, payload, expected_model_path, capability_name="intersection_queries")
        value = json.loads(raw)
        if isinstance(value, dict) and requires_full_evidence(value):
            return raw
        result = project_query(value, include_ids=include_ids, supplied={"object_ids": ids})
        # Occurrence handles and pair state are executable references, not redundant identity metadata.
        if isinstance(value, dict) and "pairs" in value:
            result["pairs"] = value["pairs"]
        return json.dumps(relative_output(result), ensure_ascii=False)
    except (TypeError, ValueError, AttributeError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))


def dispatch(send, payload, expected_model_path, required_version=1, capability_name="object_observation"):
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
        capability = snapshot.get("capabilities", {}).get(capability_name, 0)
        if type(capability) is not int or capability < required_version:
            return json.dumps(error_payload(f"Load a Bridge with {capability_name}>={required_version} before using this object query.",
                                           error_code="unsupported_object_observation"))
        return send(encoded)
    except Exception as exc:
        return json.dumps(error_payload(f"Could not observe Rhino objects: {exc}", error_code="bridge_error"))
