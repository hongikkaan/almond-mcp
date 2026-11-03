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
          expected_geometry_crcs=None, include_ids=False, group_ids=None,
          selected=False, inside_window=False, recursive=False, depth=1, expected_snapshot=""):
    try:
        if scope not in ("current", "document"):
            raise ValueError("scope must be current or document.")
        if any(type(v) is not bool for v in (selected, inside_window, recursive)):
            raise ValueError("selected, inside_window and recursive must be booleans.")
        if selected and inside_window:
            raise ValueError("Choose selected or inside_window, not both.")
        if scope != "current" and (selected or inside_window):
            raise ValueError("selected and inside_window require scope=current.")
        ids = object_ids(ids, 4096)
        if ids and scope != "document":
            raise ValueError("object_ids requires scope=document.")
        try:
            groups = object_ids([] if group_ids is None else group_ids, 64)
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("group_ids: " + str(exc).replace("object_ids", "group_ids")) from exc
        if groups and ids:
            raise ValueError("Choose group_ids or object_ids; their identity namespaces differ.")
        if not isinstance(expected_snapshot, str) or (expected_snapshot and
                (len(expected_snapshot) != 64 or any(c not in "0123456789abcdef" for c in expected_snapshot))):
            raise ValueError("expected_snapshot must be the snapshot token from the first page.")
        if type(offset) is not int or not 0 <= offset <= 100000 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("offset must be 0..100000 and limit 1..200.")
        if type(include_geometry) is not bool:
            raise ValueError("include_geometry must be boolean.")
        if type(include_ids) is not bool:
            raise ValueError("include_ids must be boolean.")
        if result_mode not in ("objects", "hierarchy", "summary"):
            raise ValueError("result_mode must be objects, hierarchy or summary.")
        if type(depth) is not int or not 1 <= depth <= 8:
            raise ValueError("depth must be an integer in 1..8; root depth is 1.")
        if recursive:
            if result_mode == "summary":
                raise ValueError("recursive returns a hierarchy, not a summary.")
            result_mode = "hierarchy"
        elif depth != 1:
            raise ValueError("depth greater than 1 requires recursive=true.")
        if offset and not expected_snapshot:
            raise ValueError("Subsequent pages require expected_snapshot from the first page.")
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
        if crcs and (scope != "document" or set(crcs) - set(ids)):
            raise ValueError("expected_geometry_crcs keys must belong to the explicit document object_ids set.")
        if face_offset and (scope != "document" or not ids or set(crcs) != set(ids)):
            raise ValueError("A subsequent face page requires document object_ids and an observed CRC for every object.")
        if result_mode == "summary" and (fields is not None or include_geometry or crcs or face_offset or face_limit != 128):
            raise ValueError("Summary returns layer/type counts; object fields and face options require result_mode=objects.")
        if result_mode == "hierarchy" and (include_geometry or crcs or face_offset or face_limit != 128
                or set(fields or []) & {"geometry_valid", "solid", "manifold", "volume", "faces", "face_count"}):
            raise ValueError("Geometry detail and face editing references require result_mode=objects; hierarchy describes occurrences and metadata.")
        payload = dict(type="get_rhino_objects", scope=scope, object_ids=ids, filters=validate_filters(filters),
                       include_geometry=include_geometry, offset=offset, limit=limit)
        extended = result_mode != "objects" or fields is not None or face_offset or face_limit != 128 or crcs or "object_types" in filters
        if extended:
            payload.update(result_mode=result_mode, fields=fields, face_offset=face_offset,
                           face_limit=face_limit, expected_geometry_crcs=crcs)
        # Keep the private native route; older Bridges must not silently ignore group/expansion inputs.
        payload.update(group_ids=groups, selected=selected, inside_window=inside_window,
                       recursive=recursive, depth=depth, expected_snapshot=expected_snapshot)
        raw = dispatch(send, payload, expected_model_path, required_version=4)
        value = json.loads(raw)
        if isinstance(value, dict) and value.get("status") != "error":
            for key in ("schema", "model_path", "document_units", "tolerance_model_units"):
                value.pop(key, None)
        if isinstance(value, dict) and value.get("status") == "error":
            return json.dumps(value, ensure_ascii=False)
        # Explicit requested identity fields take precedence over the general query default.
        if not (include_ids or (fields is not None and bool({"id", "faces"} & set(fields)))):
            value = _without_object_ids(value)
        return json.dumps(relative_output(value), ensure_ascii=False)
    except (TypeError, ValueError, AttributeError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))


def _without_object_ids(value):
    """Keep every coverage/diagnostic field, including on partial pages, but honor ID opt-in."""
    if isinstance(value, list):
        return [_without_object_ids(item) for item in value]
    if not isinstance(value, dict) or value.get("status") == "error":
        return value
    return {key: _without_object_ids(item) for key, item in value.items()
            if key not in {"id", "ids", "guid", "guids", "document_serial_number"}
            and not key.endswith(("_id", "_ids", "_guid", "_guids"))}


def intersections(send, *, ids, include_block=False):
    """Count the whole requested scope; native paging stays private and bounded."""
    try:
        ids = object_ids(ids, 512, required=True)
        if type(include_block) is not bool:
            raise ValueError("include_block must be boolean.")
        path = bound_model_path()
    except (TypeError, ValueError, AttributeError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
    cursor, seen, count, evaluated = "", set(), 0, 0
    try:
        while True:
            payload = dict(type="get_object_intersections", object_ids=ids, max_pairs=64,
                           include_blocks=include_block, cursor=cursor)
            raw = dispatch(send, payload, path, capability_name="intersection_queries")
            page = json.loads(raw)
            if not isinstance(page, dict):
                raise ValueError("Native intersection query returned a non-object response.")
            if page.get("status") == "error":
                return raw
            pairs, unsupported = page.get("pairs"), page.get("unsupported_objects")
            if page.get("status") != "success" or not isinstance(pairs, list) or not isinstance(unsupported, list):
                raise ValueError("Native intersection query omitted its pair or unsupported-object evidence.")
            # An explicitly excluded block is outside the requested scope, not a failed solid.
            failures = [item for item in unsupported
                        if include_block or item.get("reason") != "block_excluded"]
            unknown = [pair for pair in pairs
                       if pair.get("overlap", {}).get("status") not in {"positive_volume", "zero_volume"}]
            if failures or unknown:
                return json.dumps({**error_payload(
                    "The total overlap count could not be established. Inspect the unsupported objects or failed pairs.",
                    error_code="intersection_count_incomplete"),
                    "unsupported_objects": failures,
                    "failed_pairs": [{"objects": [pair.get("a"), pair.get("b")],
                                      "reason": pair.get("overlap")} for pair in unknown]}, ensure_ascii=False)
            count += sum(pair["overlap"]["status"] == "positive_volume" for pair in pairs)
            evaluated += len(pairs)
            if evaluated > 20000:
                raise ValueError("Native intersection query exceeded its 20000-candidate bound.")
            next_cursor = page.get("next_cursor")
            if page.get("pagination_complete") is True:
                if next_cursor:
                    raise ValueError("A completed intersection query returned a continuation cursor.")
                return json.dumps({"intersections": {"number": count}, "next_step":
                    "같은 object_ids와 include_block으로 resolve_object_intersection을 시작해 비교 이미지·객체 정보를 확인하세요. 이어 review_id와 choice=1/2 또는 'skip'을 보내 처리합니다."},
                    ensure_ascii=False)
            if not pairs or not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen:
                raise ValueError("Native intersection pagination did not advance.")
            seen.add(next_cursor)
            cursor = next_cursor
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        return json.dumps(error_payload(str(exc), error_code="invalid_intersection_response"))


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
