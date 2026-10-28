"""MCP registration for camera-path conditioning capture."""
from almond_mcp.tool_response import error_payload
from almond_mcp.instruction_text import tool_instruction
import json

from almond_mcp.features.capture import conditioning


def register(mcp, context):
    """Register capture tools against this server's live connection context."""
    @mcp.tool()
    @tool_instruction(__file__, 'capture_conditioning_pass')
    def capture_conditioning_pass(
        shot: str,
        out_dir: str = "",
        width: int = 832,
        height: int = 480,
        passes: str = "rgb,edge,depth",
        fps: int = 16,
        chunk: int = 16,
        rgb_mode: str = "Rendered",
        edge_mode: str = "Technical",
        invert_depth: bool = False,
    ) -> str:
        try:
            shot_dict = json.loads(shot)
            frames = conditioning.build_path(shot_dict)
        except (ValueError, KeyError, TypeError) as e:
            return json.dumps(error_payload(f"Bad shot description: {e}"))
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


    return {"capture_conditioning_pass": capture_conditioning_pass}
