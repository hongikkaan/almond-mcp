"""Live Rhino observations and local retrieval diagnostics."""
from almond_mcp.instruction_text import tool_instruction, read_instruction

import base64
import io
import json

from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image as PillowImage
from pydantic import StrictInt


def register(mcp, context):
    """Register observation tools using the server's current connection and state."""
    @mcp.tool()
    @tool_instruction(__file__, 'get_retrieval_status')
    def get_retrieval_status() -> str:
        return json.dumps({
            "status": "ready",
            "database": context.STATE_DB_PATH,
            "asset_index": context.retrieval_store.asset_stats(),
            "drawing_asset_index": context.retrieval_store.asset_stats("drawing_assets"),
            "generated_asset_index": context.retrieval_store.asset_stats("generated_assets"),
            "drawing_recipes": len(context.drawing_recipe_indexer.recipes),
            "retrieval": ["sqlite", "fts5", "rtree"],
            "embedding_adapter": "not_configured",
        })


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_context')
    def get_rhino_context(selection_limit: StrictInt = 50) -> str:
        if type(selection_limit) is not int or not 0 <= selection_limit <= 200:
            return json.dumps({"status": "error", "error_code": "invalid_arguments",
                               "message": "selection_limit must be an integer from 0 to 200."})
        payload = json.dumps({"type": "get_rhino_context", "selection_limit": selection_limit}).encode("utf-8")
        try:
            return context._send_and_receive(payload)
        except Exception as exc:
            return json.dumps({"status": "error", "error_code": "bridge_error",
                               "message": f"Could not read the live Rhino context: {exc}"})


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_probe')
    def get_rhino_probe(probe: str, options: dict, expected_model_path: str) -> str:
        if (probe not in ("outline", "resolve-block", "sections", "vertical-probe", "joint-pairs")
                or not isinstance(options, dict) or not isinstance(expected_model_path, str)
                or not expected_model_path.strip()):
            return json.dumps({"status": "error", "error_code": "invalid_arguments",
                               "message": "A fixed probe, options object and expected_model_path are required."})
        try:
            payload = json.dumps({"type": "get_rhino_probe", "probe": probe, "options": options,
                                  "expected_model_path": expected_model_path}, allow_nan=False).encode("utf-8")
            if len(payload) > 262144:
                raise ValueError("Probe request exceeds 256 KiB; narrow the request.")
        except (TypeError, ValueError) as exc:
            return json.dumps({"status": "error", "error_code": "invalid_arguments", "message": str(exc)})
        try:
            # Older observation-capable Bridges route unknown request types into ScriptExecutor.
            context_response = context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}')
            snapshot = json.loads(context_response)
            if not isinstance(snapshot, dict) or snapshot.get("status") not in ("success", "error"):
                raise ValueError("Bridge returned an invalid context response.")
            if snapshot["status"] == "error":
                return context_response
            if snapshot.get("capabilities", {}).get("fixed_probes") != 1:
                return json.dumps({"status": "error", "error_code": "unsupported_probe",
                                   "message": read_instruction(__file__, 'response-585')})
            return context._send_and_receive(payload)
        except Exception as exc:
            return json.dumps({"status": "error", "error_code": "bridge_error",
                               "message": f"Could not read the live Rhino probe: {exc}"})


    def _viewport_result(metadata: dict, image_data: str | None = None) -> ToolResult:
        content = [TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
        if image_data is not None:
            content.append(ImageContent(type="image", data=image_data, mimeType="image/jpeg"))
        return ToolResult(content=content, structured_content=metadata,
                          is_error=metadata.get("status") != "success")


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_viewport_image')
    def get_rhino_viewport_image(max_width: StrictInt = 1280, max_height: StrictInt = 960) -> ToolResult:
        if any(type(value) is not int or not 64 <= value <= 2048 for value in (max_width, max_height)):
            return _viewport_result({"status": "error", "error_code": "invalid_arguments",
                                     "message": "max_width and max_height must be integers from 64 to 2048."})
        payload = json.dumps({"type": "get_rhino_viewport_image", "max_width": max_width,
                              "max_height": max_height}).encode("utf-8")
        try:
            response = json.loads(context._send_and_receive(payload))
        except Exception as exc:
            return _viewport_result({"status": "error", "error_code": "bridge_error",
                                     "message": f"Could not capture the live Rhino viewport: {exc}"})
        if not isinstance(response, dict):
            return _viewport_result({"status": "error", "error_code": "invalid_capture_response",
                                     "message": "The viewport response must be a JSON object."})
        if response.get("status") != "success":
            response.pop("image", None)
            return _viewport_result(response)
        try:
            captured = response["image"]
            encoded = captured["data"]
            byte_limit = 4 * 1024 * 1024
            if captured["mime_type"] != "image/jpeg" or not isinstance(encoded, str):
                raise ValueError("Expected base64 JPEG image data.")
            if len(encoded) > 4 * ((byte_limit + 2) // 3):
                raise ValueError("The captured JPEG exceeds 4 MiB.")
            raw = base64.b64decode(encoded, validate=True)
            if not raw or len(raw) > byte_limit:
                raise ValueError("The captured JPEG is empty or exceeds 4 MiB.")
            dimensions = (captured["width"], captured["height"])
            if any(type(value) is not int or value < 1 or value > limit
                   for value, limit in zip(dimensions, (max_width, max_height))):
                raise ValueError("Captured dimensions exceed the requested bounds.")
            with PillowImage.open(io.BytesIO(raw)) as picture:
                if picture.format != "JPEG" or picture.size != dimensions:
                    raise ValueError("JPEG dimensions or format do not match the capture metadata.")
                picture.load()
        except Exception as exc:
            return _viewport_result({"status": "error", "error_code": "invalid_capture_response",
                                     "message": f"Invalid viewport image: {exc}"})
        response["image"] = {"mime_type": "image/jpeg", "width": dimensions[0],
                             "height": dimensions[1], "byte_count": len(raw)}
        return _viewport_result(response, encoded)


    return {
        "get_retrieval_status": get_retrieval_status,
        "get_rhino_context": get_rhino_context,
        "get_rhino_probe": get_rhino_probe,
        "_viewport_result": _viewport_result,
        "get_rhino_viewport_image": get_rhino_viewport_image,
    }
