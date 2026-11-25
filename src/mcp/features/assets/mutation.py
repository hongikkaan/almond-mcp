"""Preserve completion evidence for native asset mutations."""
import json


_PLACEMENT_TIMEOUT = 90.0


def send_placement(
    send, *, asset_id: str, asset: dict, position: tuple[float, float, float],
    rotation_degrees: float, scale: float, library_id: str, action: str,
    extra_metadata: dict | None = None,
) -> dict:
    """Send the native block placement request shared by both asset libraries."""
    payload = json.dumps({
        "type": "place_drawing_asset",
        "asset_id": asset_id,
        "file_path": asset["_resolved_file"],
        "name": f"{asset.get('product', '')} {asset.get('variant', '')}".strip(),
        "position": position,
        "rotation_degrees": rotation_degrees,
        "scale": scale,
        "metadata": {
            "library_id": library_id,
            "product": asset.get("product"),
            "variant": asset.get("variant"),
            "category": asset.get("category"),
            "dimensions_mm": asset.get("dimensions_mm"),
            "drawing_roles": asset.get("drawing_roles", []),
            "lod": asset.get("lod"),
            **(extra_metadata or {}),
        },
    }).encode("utf-8")
    return send_mutation(send, payload, timeout=_PLACEMENT_TIMEOUT, action=action)


def unresolved(message: str, *, reply=None, imported_guids=None, partial=False) -> dict:
    result = {
        **(reply or {}),
        "status": "error",
        "message": message,
        "mutation_state": "partial" if partial else "unknown",
        "mutation_applied": None,
        "requires_reconciliation": True,
    }
    if imported_guids:
        result["imported_guids"] = imported_guids
    return result


def send_mutation(send, payload: bytes, *, timeout: float, action: str) -> dict:
    try:
        result = json.loads(send(payload, timeout=timeout))
        if not isinstance(result, dict) or result.get("status") not in {"success", "error"}:
            raise ValueError("Invalid native response")
    except ConnectionRefusedError:
        return {"status": "error", "message": "Rhino bridge is unavailable.",
                "mutation_state": "not_started", "mutation_applied": False}
    except Exception as exc:
        return unresolved(f"{action} completion is unconfirmed: {exc}. Inspect Rhino before retrying.")
    state = result.get("mutation_state")
    if (result.get("result_error") or state in ("partial", "unknown")
            or result["status"] == "error" and state != "not_started"):
        return unresolved(result.get("message") or f"{action} completion is unconfirmed. Inspect Rhino before retrying.",
                          reply=result, partial=state == "partial")
    return result
