"""Live Rhino observations and local retrieval diagnostics."""

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
    def get_retrieval_status() -> str:
        """Returns compact diagnostics for the local structured retrieval system."""
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
    def get_rhino_context(selection_limit: StrictInt = 50) -> str:
        """Read the LIVE bound Rhino document, selection and current viewport on the UI thread.

    Includes document identity/path, units/tolerances, object/layer counts, a bounded
    selection summary and camera/display metadata. This query does not create layers,
    geometry, dimensions or an Undo record. Unavailable values are null with warnings.
    Counts and the current view are context, not a geometric or visibility validation.
    Use this snapshot before focused object inspection or editing an existing model.

    Args:
        selection_limit: Maximum selected object summaries, from 0 to 200; total/truncated are still reported.
    Returns:
        JSON with status, document, selection, viewport and warnings, or an explicit error.
    """
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
    def get_rhino_probe(probe: str, options: dict, expected_model_path: str) -> str:
        """Read fixed geometry observations on the bound Rhino UI thread without modifying the document.

    Does not execute supplied C#, create layers/Undo records, edit geometry, select objects,
    change views or write files. Requires the Bridge fixed_probes capability. Requests and
    responses are limited to 256 KiB of UTF-8 JSON. Unknown/omitted/truncated observations
    do not mean zero, clearance, structural approval or design correctness.

    Args:
        probe: One of outline, resolve-block, sections, vertical-probe, joint-pairs.
        options: Fixed helper options: outline uses scope/ids/path/depth; resolve-block uses
            path (1..65 GUIDs); sections uses ids/axis/stations; vertical-probe uses ids/xy;
            joint-pairs uses pairs and optional compare_operations. Coordinates are model units.
        expected_model_path: Absolute normalized saved .3dm path from project_info; must match the active document.
    Returns:
        JSON with status, probe, document identity/units/tolerance and data, or an explicit error.
    """
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
                                   "message": "Load a Bridge with fixed_probes=1 before calling geometry probes."})
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
    def get_rhino_viewport_image(max_width: StrictInt = 1280, max_height: StrictInt = 960) -> ToolResult:
        """Return the LIVE current Rhino viewport as a JPEG image with document/view metadata.

    Captures the current view without changing its camera, projection, display mode,
    clipping, selection or Undo history. The image preserves the viewport aspect ratio
    within the requested bounds; it does not zoom to fit or prove geometric correctness.
    A missing view, failed capture or oversized image is an explicit error, never a stale
    file. Use capture_conditioning_pass for deliberate camera paths and multiple passes.

    Args:
        max_width: Maximum image width in pixels, from 64 to 2048.
        max_height: Maximum image height in pixels, from 64 to 2048.
    Returns:
        An MCP image content block plus JSON metadata. JPEG data is limited to 4 MiB.
    """
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
