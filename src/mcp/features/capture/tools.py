"""MCP registration for camera-path conditioning capture."""
from almond_mcp.tool_response import error_payload
from almond_mcp.tool_declarations import public_tool
import json

from fastmcp.tools import ToolResult
from pydantic import StrictFloat, StrictInt
from typing import Literal

from almond_mcp.features.capture import conditioning, manipulation


def register(mcp, context):
    """Register capture tools against this server's live connection context."""
    @public_tool(mcp, errors=True)
    def capture_conditioning_pass(
        shot: str,
        out_dir: str = "",
        width: StrictInt = 832,
        height: StrictInt = 480,
        passes: str = "rgb,edge,depth",
        fps: StrictInt = 16,
        chunk: StrictInt = 16,
        rgb_mode: str = "Rendered",
        edge_mode: str = "Technical",
        invert_depth: bool = False,
    ) -> str:
        try:
            shot_dict = json.loads(shot)
            if not isinstance(shot_dict, dict):
                raise ValueError("shot must contain a JSON object")
            frames = conditioning.build_path(shot_dict)
        except (ValueError, KeyError, TypeError, IndexError, OverflowError) as e:
            return json.dumps(error_payload(f"Bad shot description: {e}", error_code="invalid_arguments"))
        pass_list = tuple(p.strip() for p in passes.split(",") if p.strip())
        try:
            summary = conditioning.capture_conditioning_pass(
                frames, out_dir, context._send_and_receive, width=width, height=height, passes=pass_list,
                rgb_mode=rgb_mode, edge_mode=edge_mode, invert_depth=invert_depth, chunk=chunk, fps=fps)
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
        except Exception as e:  # noqa: BLE001
            return json.dumps(error_payload(f"Conditioning pass failed: {e}"))
        return json.dumps(summary)


    @public_tool(mcp, annotations={"readOnlyHint": False, "destructiveHint": False,
                                                  "idempotentHint": False})
    def manipulate_view(
        operation: Literal["rotate", "zoom"],
        mode: Literal["look", "orbit"] = None,
        yaw_deg: StrictFloat = None,
        pitch_deg: StrictFloat = None,
        factor: StrictFloat = None,
        expected_viewport_id: str = None,
        expected_model_path: str = None,
    ) -> ToolResult:
        return manipulation.execute(
            context._send_and_receive, operation, mode=mode, yaw_deg=yaw_deg,
            pitch_deg=pitch_deg, factor=factor, expected_viewport_id=expected_viewport_id,
            expected_model_path=expected_model_path,
        )

    return {"capture_conditioning_pass": capture_conditioning_pass, "manipulate_view": manipulate_view}
