"""Live Rhino observations and local retrieval diagnostics."""
from almond_mcp.tool_response import error_payload, mcp_error_result
from almond_mcp.query_output import query_output
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.instruction_text import tool_instruction
from almond_mcp.features.context import object_queries
from almond_mcp.features.context.capture_artifacts import save_png

import base64
import io
import json
import math

from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image as PillowImage
from pydantic import StrictBool, StrictInt


def _observation_result(serialized: str) -> str | ToolResult:
    """Keep the wrapped-string schema while marking explicit observation errors."""
    value = json.loads(serialized)
    if isinstance(value, dict) and value.get("status") == "error":
        return ToolResult(content=[TextContent(type="text", text=serialized)],
                          structured_content={"result": serialized}, is_error=True)
    return serialized


def register(mcp, context):
    """Register observation tools using the server's current connection and state."""


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_rhino_context', wrapped=True))
    @tool_instruction(__file__, 'get_rhino_context')
    def get_rhino_context(sections: list[str] | None = None, include_ids: StrictBool = False,
                          include_editor_details: StrictBool = False) -> str | ToolResult:
        from almond_mcp.features.context.context_query import query
        return _observation_result(query(context._send_and_receive, sections, include_ids, include_editor_details))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('analyze_block_reculviely', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'analyze_block_reculviely')
    @query_output
    def analyze_block_reculviely(mode: str, options: dict, expected_model_path: str = "", include_ids: StrictBool = False) -> str:
        try:
            expected_model_path = bound_model_path(expected_model_path)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        if (mode not in ("outline", "resolve-block")
                or not isinstance(options, dict) or not isinstance(expected_model_path, str)
                or not expected_model_path.strip()):
            return json.dumps(error_payload(
                "outline or resolve-block, an options object and expected_model_path are required.",
                error_code="invalid_arguments",
            ))
        fields = options.get("field_groups")
        if mode == "outline" and "field_groups" in options and (
                not isinstance(fields, list) or not fields or
                any(not isinstance(group, str) or group not in ("summary", "objects", "annotations", "transforms") for group in fields)):
            return json.dumps(error_payload(
                "outline field_groups must be a nonempty array of summary, objects, annotations or transforms.",
                error_code="invalid_arguments"))
        try:
            payload = json.dumps({"type": "analyze_block_reculviely", "mode": mode, "options": options,
                                  "expected_model_path": expected_model_path}, allow_nan=False).encode("utf-8")
            if len(payload) > 262144:
                raise ValueError("Block analysis request exceeds 256 KiB; narrow the request.")
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
            if snapshot.get("capabilities", {}).get("block_analysis") != 1:
                return json.dumps(error_payload(
                    'Load a Bridge with block_analysis=1 before analyzing blocks.',
                    error_code="unsupported_block_analysis",
                ))
            return context._send_and_receive(payload)
        except Exception as exc:
            return json.dumps(error_payload(
                f"Could not analyze the live Rhino block: {exc}",
                error_code="bridge_error",
            ))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_objects', wrapped=True))
    @tool_instruction(__file__, 'get_objects')
    def get_objects(scope: str = "current", object_ids: list[str] | None = None,
                          filters: dict | None = None, include_geometry: StrictBool = False,
                          offset: StrictInt = 0, limit: StrictInt = 50,
                          expected_model_path: str = "", include_ids: StrictBool = False,
                          result_mode: str = "objects", fields: list[str] | None = None,
                          face_offset: StrictInt = 0, face_limit: StrictInt = 128,
                          expected_geometry_crcs: dict[str, StrictInt] | None = None,
                          group_ids: list[str] | None = None, selected: StrictBool = False,
                          inside_window: StrictBool = False, recursive: StrictBool = False,
                          depth: StrictInt = 1, expected_snapshot: str = "") -> str | ToolResult:
        return _observation_result(object_queries.query(context._send_and_receive, scope=scope,
                                    ids=[] if object_ids is None else object_ids,
                                    filters={} if filters is None else filters,
                                    include_geometry=include_geometry, offset=offset, limit=limit,
                                    expected_model_path=expected_model_path, result_mode=result_mode,
                                    fields=fields, face_offset=face_offset, face_limit=face_limit,
                                    expected_geometry_crcs=expected_geometry_crcs, include_ids=include_ids,
                                    group_ids=group_ids, selected=selected, inside_window=inside_window,
                                    recursive=recursive, depth=depth, expected_snapshot=expected_snapshot))


    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_object_intersections', wrapped=True))
    @tool_instruction(__file__, 'get_object_intersections')
    def get_object_intersections(object_ids: list[str], include_block: StrictBool = False) -> str | ToolResult:
        return _observation_result(object_queries.intersections(
            context._send_and_receive, ids=object_ids, include_block=include_block))


    @mcp.tool(annotations={'readOnlyHint': False, 'destructiveHint': False}, output_schema=public_output_schema('capture_rhino_inspection', wrapped=False))
    @tool_instruction(__file__, 'capture_rhino_inspection')
    def capture_rhino_inspection(views: list[dict], width: StrictInt = 640, height: StrictInt = 480,
                                 columns: StrictInt | None = None, expected_model_path: str = "",
                                 model_view_id: str = "", object_ids: list[str] | None = None) -> ToolResult:
        from almond_mcp.features.context.inspection_capture import execute
        try:
            path = bound_model_path(expected_model_path)
        except ValueError as exc:
            return _viewport_result(error_payload(str(exc), error_code="invalid_arguments"))
        payload = {"views": views, "width": width, "height": height}
        if columns is not None:
            payload["columns"] = columns
        if model_view_id != "":
            payload["model_view_id"] = model_view_id
        if object_ids is not None:
            payload["object_ids"] = object_ids
        return execute(context._send_and_receive, payload, path)


    def _viewport_result(metadata: dict) -> ToolResult:
        content = [TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
        return ToolResult(content=content, structured_content=metadata,
                          is_error=metadata.get("status") != "success")


    @mcp.tool(annotations={'readOnlyHint': False, 'destructiveHint': False}, output_schema=public_output_schema('get_defined_viewcapture', wrapped=False))
    @tool_instruction(__file__, 'get_defined_viewcapture')
    def get_defined_viewcapture(target_kind: str, target: str, scale_percent: StrictInt = 75,
                                include_usage: StrictBool = False, display_mode: str = "",
                                labels: StrictBool = False, depth: StrictInt = 1,
                                width: StrictInt | None = None, height: StrictInt | None = None,
                                expected_model_path: str = "") -> ToolResult:
        from almond_mcp.features.context.view_capture import execute
        result = execute(context._send_and_receive, "get_defined_viewcapture", target_kind=target_kind, target=target,
                         scale_percent=scale_percent, include_usage=include_usage, display_mode=display_mode,
                         labels=labels, depth=depth, width=width, height=height, expected_model_path=expected_model_path)
        return _capture_result(result, scale_percent, include_usage,
                               requested_size=(width, height) if width is not None and height is not None else None)


    @mcp.tool(annotations={'readOnlyHint': False, 'destructiveHint': False}, output_schema=public_output_schema('get_current_viewcapture', wrapped=False))
    @tool_instruction(__file__, 'get_current_viewcapture')
    def get_current_viewcapture(target_ids: list[str] | None = None, target_kind: str = "object",
                                isolate: StrictBool = False, scale_percent: StrictInt = 75,
                                include_usage: StrictBool = False, display_mode: str = "",
                                labels: StrictBool = False, depth: StrictInt = 1,
                                width: StrictInt | None = None, height: StrictInt | None = None,
                                expected_model_path: str = "") -> ToolResult:
        from almond_mcp.features.context.view_capture import execute
        result = execute(context._send_and_receive, "get_current_viewcapture", target_kind=target_kind, target_ids=target_ids,
                         isolate=isolate, scale_percent=scale_percent, include_usage=include_usage, display_mode=display_mode,
                         labels=labels, depth=depth, width=width, height=height, expected_model_path=expected_model_path)
        return _capture_result(result, scale_percent, include_usage,
                               requested_size=(width, height) if width is not None and height is not None else None)

    def _capture_result(response: dict, scale_percent: int, include_usage: bool,
                        *, kind: str = "viewport", requested_size: tuple[int, int] | None = None) -> ToolResult:
        if response.get("status") != "success":
            response.pop("image", None)
            return _viewport_result(response)
        try:
            scale_percent = response.get("scale_percent", scale_percent)
            if type(scale_percent) is not int or not 1 <= scale_percent <= 100:
                raise ValueError("Invalid actual capture scale.")
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
            if requested_size is not None and (dimensions != requested_size or source != requested_size):
                raise ValueError("Captured dimensions do not match the explicit requested pixels.")
            if (any(type(value) is not int or value < 1 for value in (*dimensions, *source)) or
                    dimensions[0] * dimensions[1] > 16 * 1024 * 1024 or
                    dimensions != tuple(max(1, value * scale_percent // 100) for value in source)):
                raise ValueError("Captured dimensions do not match the requested percentage or exceed 16 megapixels.")
            with PillowImage.open(io.BytesIO(raw)) as picture:
                if picture.format != "PNG" or picture.size != dimensions:
                    raise ValueError("PNG dimensions or format do not match the capture metadata.")
                picture.load()
        except Exception as exc:
            error = error_payload(f"Invalid viewport image: {exc}", error_code="invalid_capture_response")
            error.update({key: response[key] for key in ("view_change", "mutation_applied", "requires_reconciliation", "warnings") if key in response})
            return _viewport_result(error)
        image_file = save_png(raw, kind)
        metadata = {"image_file": image_file}
        metadata.update({key: response[key] for key in ("view_change", "mutation_applied", "requires_reconciliation") if key in response})
        content = [ImageContent(type="image", data=encoded, mimeType="image/png"),
                   TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
        if response.get("warnings"):
            content.append(TextContent(type="text", text=json.dumps({"warnings": response["warnings"]}, ensure_ascii=False)))
        if include_usage:
            # Pixel patches, not compressed PNG bytes, drive this example estimate.
            # The client model/detail is not supplied by MCP; never call it actual usage.
            patches = ((dimensions[0] + 31) // 32) * ((dimensions[1] + 31) // 32)
            usage = {"width": dimensions[0], "height": dimensions[1], "scale_percent": scale_percent,
                     "patches_32px": patches, "estimated_image_tokens": math.ceil(patches * 1.2),
                     "assumption": "32px patches x 1.2, no provider resizing; actual model/detail may differ"}
            content.append(TextContent(type="text", text=json.dumps(usage)))
        return ToolResult(content=content, structured_content=metadata)


    return {
        "get_rhino_context": get_rhino_context,
        "analyze_block_reculviely": analyze_block_reculviely,
        "_viewport_result": _viewport_result,
        "get_defined_viewcapture": get_defined_viewcapture,
        "get_current_viewcapture": get_current_viewcapture,
        "get_objects": get_objects,
        "get_object_intersections": get_object_intersections,
        "capture_rhino_inspection": capture_rhino_inspection,
    }
