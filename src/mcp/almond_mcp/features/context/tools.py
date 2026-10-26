"""Live Rhino observations and local retrieval diagnostics."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.instruction_text import tool_instruction, read_instruction

import base64
import io
import json
import math
import uuid

from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image as PillowImage
from pydantic import StrictBool, StrictInt


def register(mcp, context):
    """Register observation tools using the server's current connection and state."""
    @mcp.tool()
    @tool_instruction(__file__, 'get_retrieval_status')
    @query_output
    def get_retrieval_status(include_ids: StrictBool = False) -> str:
        return json.dumps({
            "status": "ready",
            "database": context.STATE_DB_PATH,
            "asset_index": context.retrieval_store.asset_stats(),
            "drawing_asset_index": {"source": "manifest", "total": len(context.drawing_asset_indexer.assets)},
            "model_asset_index": context.retrieval_store.asset_stats("generated_assets"),
            "drawing_recipes": len(context.drawing_recipe_indexer.recipes),
            "retrieval": ["sqlite", "fts5", "rtree"],
            "embedding_adapter": "not_configured",
        })


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_context')
    @query_output
    def get_rhino_context(selection_limit: StrictInt = 50, sections: list[str] | None = None,
                          include_ids: StrictBool = False) -> str:
        sections = ["document"] if sections is None else sections
        if not isinstance(sections, list) or any(section not in ("document", "selection", "viewport") for section in sections):
            return json.dumps(error_payload("sections must be an array of document, selection or viewport.", error_code="invalid_arguments"))
        if type(selection_limit) is not int or not 0 <= selection_limit <= 200:
            return json.dumps(error_payload(
                "selection_limit must be an integer from 0 to 200.",
                error_code="invalid_arguments",
            ))
        payload = json.dumps({"type": "get_rhino_context", "selection_limit": selection_limit, "sections": sections}).encode("utf-8")
        try:
            result = json.loads(context._send_and_receive(payload))
            # An older Bridge may collect extra sections; never expose them as requested data.
            for section in ("document", "selection", "viewport"):
                if section not in sections:
                    result.pop(section, None)
            result.pop("capabilities", None)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return json.dumps(error_payload(
                f"Could not read the live Rhino context: {exc}",
                error_code="bridge_error",
            ))


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_probe')
    @query_output
    def get_rhino_probe(probe: str, options: dict, expected_model_path: str = "", include_ids: StrictBool = False) -> str:
        try:
            expected_model_path = bound_model_path(expected_model_path)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        if (probe not in ("outline", "resolve-block", "sections", "vertical-probe", "joint-pairs")
                or not isinstance(options, dict) or not isinstance(expected_model_path, str)
                or not expected_model_path.strip()):
            return json.dumps(error_payload(
                "A fixed probe, options object and expected_model_path are required.",
                error_code="invalid_arguments",
            ))
        try:
            payload = json.dumps({"type": "get_rhino_probe", "probe": probe, "options": options,
                                  "expected_model_path": expected_model_path}, allow_nan=False).encode("utf-8")
            if len(payload) > 262144:
                raise ValueError("Probe request exceeds 256 KiB; narrow the request.")
        except (TypeError, ValueError) as exc:
            return json.dumps(error_payload(
                str(exc),
                error_code="invalid_arguments",
            ))
        try:
            # Older observation-capable Bridges route unknown request types into ScriptExecutor.
            context_response = context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}')
            snapshot = json.loads(context_response)
            if not isinstance(snapshot, dict) or snapshot.get("status") not in ("success", "error"):
                raise ValueError("Bridge returned an invalid context response.")
            if snapshot["status"] == "error":
                return context_response
            if snapshot.get("capabilities", {}).get("fixed_probes") != 1:
                return json.dumps(error_payload(
                    read_instruction(__file__, 'response-585'),
                    error_code="unsupported_probe",
                ))
            return context._send_and_receive(payload)
        except Exception as exc:
            return json.dumps(error_payload(
                f"Could not read the live Rhino probe: {exc}",
                error_code="bridge_error",
            ))


    def _viewport_result(metadata: dict) -> ToolResult:
        content = [TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
        return ToolResult(content=content, structured_content=metadata,
                          is_error=metadata.get("status") != "success")


    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_viewport_image')
    def get_rhino_viewport_image(view: str = "", scale_percent: StrictInt = 50,
                                 include_usage: StrictBool = False) -> ToolResult:
        if (not isinstance(view, str) or type(scale_percent) is not int or
                not 1 <= scale_percent <= 100 or type(include_usage) is not bool):
            return _viewport_result(error_payload(
                "view must be a string, scale_percent an integer from 1 to 100, and include_usage a boolean.",
                error_code="invalid_arguments",
            ))
        view = view.strip().lower()
        if view not in ("", "a"):
            try:
                view = str(uuid.UUID(view))
            except ValueError:
                return _viewport_result(error_payload(
                    "Omit view for the active viewport, use 'a' to list views, or pass a listed GUID.",
                    error_code="invalid_arguments",
                ))
        payload = json.dumps({"type": "get_rhino_viewport_image", "view": view,
                              "scale_percent": scale_percent}).encode("utf-8")
        try:
            response = json.loads(context._send_and_receive(payload))
        except Exception as exc:
            return _viewport_result(error_payload(
                f"Could not capture the live Rhino viewport: {exc}",
                error_code="bridge_error",
            ))
        if not isinstance(response, dict):
            return _viewport_result(error_payload(
                "The viewport response must be a JSON object.",
                error_code="invalid_capture_response",
            ))
        if response.get("status") != "success":
            response.pop("image", None)
            return _viewport_result(response)
        try:
            if view == "a":
                groups = response["views"]
                if not isinstance(groups, dict) or set(groups) != {"viewports", "named_views", "layouts"}:
                    raise ValueError("Expected viewport, named view and layout lists.")
                compact = {}
                for group, entries in groups.items():
                    if not isinstance(entries, list):
                        raise ValueError("Each view group must be a list.")
                    compact[group] = []
                    for entry in entries:
                        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                            raise ValueError("Each view must have a name and GUID.")
                        compact[group].append({"name": entry["name"], "guid": str(uuid.UUID(entry["guid"]))})
                return ToolResult(content=[TextContent(type="text", text=json.dumps(compact, ensure_ascii=False))])
            captured = response["image"]
            encoded = captured["data"]
            byte_limit = 4 * 1024 * 1024
            if captured["mime_type"] != "image/png" or not isinstance(encoded, str):
                raise ValueError("Expected base64 PNG image data. Load the matching Bridge runtime if it still returns JPEG.")
            if len(encoded) > 4 * ((byte_limit + 2) // 3):
                raise ValueError("The captured PNG exceeds 4 MiB; use a lower scale_percent.")
            raw = base64.b64decode(encoded, validate=True)
            if not raw or len(raw) > byte_limit:
                raise ValueError("The captured PNG is empty or exceeds 4 MiB.")
            dimensions = (captured["width"], captured["height"])
            source = (captured["source_width"], captured["source_height"])
            if (any(type(value) is not int or value < 1 for value in (*dimensions, *source)) or
                    dimensions[0] * dimensions[1] > 16 * 1024 * 1024 or
                    dimensions != tuple(max(1, value * scale_percent // 100) for value in source)):
                raise ValueError("Captured dimensions do not match the requested percentage or exceed 16 megapixels.")
            with PillowImage.open(io.BytesIO(raw)) as picture:
                if picture.format != "PNG" or picture.size != dimensions:
                    raise ValueError("PNG dimensions or format do not match the capture metadata.")
                picture.load()
        except Exception as exc:
            return _viewport_result(error_payload(
                f"Invalid viewport image: {exc}",
                error_code="invalid_capture_response",
            ))
        content = [ImageContent(type="image", data=encoded, mimeType="image/png")]
        if include_usage:
            # Pixel patches, not compressed PNG bytes, drive this example estimate.
            # The client model/detail is not supplied by MCP; never call it actual usage.
            patches = ((dimensions[0] + 31) // 32) * ((dimensions[1] + 31) // 32)
            usage = {"width": dimensions[0], "height": dimensions[1], "scale_percent": scale_percent,
                     "patches_32px": patches, "estimated_image_tokens": math.ceil(patches * 1.2),
                     "assumption": "32px patches x 1.2, no provider resizing; actual model/detail may differ"}
            content.append(TextContent(type="text", text=json.dumps(usage)))
        return ToolResult(content=content)


    return {
        "get_retrieval_status": get_retrieval_status,
        "get_rhino_context": get_rhino_context,
        "get_rhino_probe": get_rhino_probe,
        "_viewport_result": _viewport_result,
        "get_rhino_viewport_image": get_rhino_viewport_image,
    }
