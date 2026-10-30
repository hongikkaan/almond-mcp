"""Bounded, read-only contact-sheet capture through a fixed native route."""
import base64
import io
import json
import math
import ntpath
import uuid

from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image


MAX_TILES = 16
MAX_PIXELS = 16 * 1024 * 1024
MAX_IMAGE_BYTES = 4 * 1024 * 1024
DIRECTIONS = frozenset((
    "current", "top", "bottom", "front", "back", "left", "right",
    "iso_ne", "iso_nw", "iso_se", "iso_sw",
    "below_ne", "below_nw", "below_se", "below_sw",
))


def _error(code, message, **extra):
    return {"status": "error", "error_code": code, "message": message, **extra}


def _result(metadata, image=None):
    content = [TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
    if image is not None:
        content.append(ImageContent(type="image", data=image, mimeType="image/png"))
    return ToolResult(content=content, structured_content=metadata,
                      is_error=metadata.get("status") != "success")


def _request(payload, path):
    if not isinstance(payload, dict) or set(payload) - {"views", "width", "height", "columns"}:
        raise ValueError("Use views, width, height and optional columns.")
    if not isinstance(path, str) or not path.strip() or not ntpath.isabs(path):
        raise ValueError("The bound document must have an absolute saved model path.")
    views = payload.get("views")
    if not isinstance(views, list) or not 1 <= len(views) <= MAX_TILES:
        raise ValueError("views must contain 1..16 explicitly chosen tiles.")
    normalized = []
    for view in views:
        if not isinstance(view, dict) or set(view) - {"object_ids", "direction", "display_mode", "label"}:
            raise ValueError("Each tile accepts object_ids, direction, display_mode and label.")
        direction = view.get("direction", "current")
        if not isinstance(direction, str) or direction not in DIRECTIONS:
            raise ValueError("Use a supported direction; current preserves the copied camera.")
        ids = view.get("object_ids", [])
        if not isinstance(ids, list) or len(ids) > 512 or any(not isinstance(value, str) for value in ids):
            raise ValueError("object_ids must contain at most 512 distinct top-level object GUIDs.")
        try:
            ids = [str(uuid.UUID(value)) for value in ids]
        except (ValueError, AttributeError):
            raise ValueError("object_ids must contain valid object GUIDs.") from None
        if len(set(ids)) != len(ids) or str(uuid.UUID(int=0)) in ids:
            raise ValueError("object_ids must contain distinct, nonempty GUIDs.")
        mode, label = view.get("display_mode", ""), view.get("label", "")
        if not isinstance(mode, str) or len(mode) > 512 or not isinstance(label, str) or len(label) > 120:
            raise ValueError("display_mode is a name/GUID up to 512 characters; label is at most 120 characters.")
        normalized.append({"object_ids": ids, "direction": direction,
                           "display_mode": mode, "label": label})
    width, height = payload.get("width", 640), payload.get("height", 480)
    columns = payload.get("columns", math.ceil(math.sqrt(len(views))))
    if (type(width) is not int or type(height) is not int or not 128 <= width <= 2048
            or not 128 <= height <= 2048 or type(columns) is not int or not 1 <= columns <= len(views)):
        raise ValueError("Tile width/height must be 128..2048 pixels; columns must be 1..tile count.")
    rows = math.ceil(len(views) / columns)
    if width * columns * height * rows > MAX_PIXELS:
        raise ValueError("The complete contact sheet must not exceed 16 megapixels.")
    request = {"type": "capture_rhino_inspection", "expected_model_path": path,
               "views": normalized, "width": width, "height": height, "columns": columns}
    if len(json.dumps(request, ensure_ascii=False).encode("utf-8")) > 262144:
        raise ValueError("Capture request exceeds 256 KiB; narrow the object sets.")
    return request


def execute(send, payload, path):
    """Validate before dispatch, gate the native capability, and return metadata plus PNG."""
    try:
        request = _request(payload, path)
    except (TypeError, ValueError) as exc:
        return _result(_error("invalid_arguments", str(exc)))
    try:
        capabilities = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(capabilities, dict) or capabilities.get("status") != "success":
            return _result(_error("unsupported_inspection_capture", "Could not verify the capture capability."))
        if capabilities.get("capabilities", {}).get("inspection_capture") != 1:
            return _result(_error("unsupported_inspection_capture", "Load a Bridge with inspection_capture=1."))
        response = send(json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        if len(response.encode("utf-8")) > 6 * 1024 * 1024:
            raise ValueError("Inspection capture response exceeds its bounded image and metadata budget.")
        response = json.loads(response)
    except Exception as exc:
        return _result(_error("bridge_error", f"Could not capture the inspection sheet: {exc}"))
    if not isinstance(response, dict):
        return _result(_error("invalid_capture_response", "Expected an inspection response object."))
    if response.get("status") != "success":
        response.pop("image", None)
        return _result(response)
    try:
        tiles = response.get("tiles")
        if not isinstance(tiles, list) or len(tiles) != len(request["views"]):
            raise ValueError("Native tile metadata does not match the requested tile count.")
        columns = request["columns"]
        rows = math.ceil(len(tiles) / columns)
        expected = (request["width"] * columns, request["height"] * rows)
        for index, tile in enumerate(tiles):
            if (not isinstance(tile, dict) or tile.get("index") != index
                    or tile.get("status") not in ("success", "error")
                    or tile.get("direction") != request["views"][index]["direction"]):
                raise ValueError("Native tile identity/status/direction is invalid.")
            if tile.get("status") == "success" and not isinstance(tile.get("scope"), dict):
                raise ValueError("A captured tile must report its actual scope.")
        captured = response["image"]
        encoded = captured["data"]
        if captured.get("mime_type") != "image/png" or not isinstance(encoded, str):
            raise ValueError("Expected a base64 PNG.")
        if len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
            raise ValueError("The PNG exceeds 4 MiB.")
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("The PNG is empty or exceeds 4 MiB.")
        dimensions = (captured.get("width"), captured.get("height"))
        if any(type(value) is not int for value in dimensions) or dimensions != expected:
            raise ValueError("PNG metadata dimensions differ from the requested sheet.")
        with Image.open(io.BytesIO(raw)) as picture:
            if picture.format != "PNG" or picture.size != dimensions:
                raise ValueError("PNG dimensions or format differ from its metadata.")
            picture.load()
        metadata = {key: value for key, value in response.items() if key != "image"}
        if len(json.dumps(metadata, ensure_ascii=False).encode("utf-8")) > 512 * 1024:
            raise ValueError("Tile metadata exceeds 512 KiB.")
    except Exception as exc:
        return _result(_error("invalid_capture_response", f"Invalid inspection sheet: {exc}"))
    return _result(metadata, encoded)
