"""Read ordinary top-level objects using the existing Bridge observation API."""
import json
import math
import ntpath
import os

# Rhino UnitSystem names, converted to millimetres. Unknown/custom units are
# left without bounds rather than silently reporting incorrect dimensions.
_UNIT_MM = {"Millimeters": 1.0, "Centimeters": 10.0, "Meters": 1000.0,
            "Kilometers": 1000000.0, "Inches": 25.4, "Feet": 304.8,
            "Yards": 914.4, "Miles": 1609344.0, "Microns": 0.001}


def observe_objects(send, model_path, ids):
    """Return verified rows and missing IDs, without exposing Bridge GUID errors."""
    context = json.loads(send(b'{"type":"get_rhino_context","selection_limit":0,"sections":[]}'))
    if context.get("status") != "success" or context.get("capabilities", {}).get("object_observation", 0) < 2:
        raise ValueError("A Bridge with object_observation=2 is required.")
    rows, missing = {}, set()

    def same_model(value):
        if not isinstance(value, str):
            return False
        norm = ntpath.normcase if ntpath.splitdrive(model_path)[0] else os.path.normcase
        pathnorm = ntpath.normpath if ntpath.splitdrive(model_path)[0] else os.path.normpath
        return norm(pathnorm(value)) == norm(pathnorm(model_path))

    if not ids:
        request = {"type": "get_rhino_objects", "scope": "document", "object_ids": [],
                   "expected_model_path": model_path, "filters": {}, "offset": 0, "limit": 1,
                   "include_geometry": False, "fields": ["id"]}
        reply = json.loads(send(json.dumps(request).encode("utf-8")))
        if reply.get("status") != "success" or not same_model(reply.get("model_path")):
            raise ValueError("Could not verify the bound Rhino document; no Scene membership changes were made.")
        return rows, missing

    def inspect(batch):
        request = {"type": "get_rhino_objects", "scope": "ids", "object_ids": batch,
                   "expected_model_path": model_path, "filters": {}, "include_geometry": False,
                   "offset": 0, "limit": len(batch), "fields": ["id", "name", "object_type", "bounds"]}
        reply = json.loads(send(json.dumps(request).encode("utf-8")))
        if reply.get("status") != "success":
            if reply.get("error_code") == "invalid_arguments" and str(reply.get("message", "")).startswith("IDs are not top-level model objects:"):
                if len(batch) == 1:
                    missing.add(batch[0])
                else:
                    mid = len(batch) // 2
                    inspect(batch[:mid]); inspect(batch[mid:])
                return
            raise ValueError("Could not observe the bound Rhino document; no Scene membership changes were made.")
        if not same_model(reply.get("model_path")):
            raise ValueError("Rhino returned an observation for a different document.")
        values = reply.get("objects")
        if reply.get("complete") is not True or not isinstance(values, list) or len(values) != len(batch):
            raise ValueError("The Rhino object observation was incomplete; no Scene membership changes were made.")
        found = {}
        for obj in values:
            if not isinstance(obj, dict) or not isinstance(obj.get("id"), str):
                raise ValueError("Invalid Rhino object observation.")
            key = obj["id"].lower()
            if key in found or key not in batch or not isinstance(obj.get("object_type"), str):
                raise ValueError("Invalid Rhino object observation.")
            row = {"rhino_guid": key, "name": obj.get("name") or "", "object_type": obj["object_type"],
                   "model_path": model_path, "live_verified": True}
            bounds = obj.get("bounds")
            factor = _UNIT_MM.get(reply.get("document_units"))
            if isinstance(bounds, dict) and factor is not None:
                low, high = bounds.get("min"), bounds.get("max")
                if (isinstance(low, list) and isinstance(high, list) and len(low) == len(high) == 3
                        and all(type(x) in (int, float) and math.isfinite(x) for x in low + high)):
                    row["bounds_mm"] = [x * factor for x in low + high]
            found[key] = row
        if set(found) != set(batch):
            raise ValueError("Invalid Rhino object observation.")
        rows.update(found)

    for start in range(0, len(ids), 200):
        inspect(ids[start:start + 200])
    return rows, missing
