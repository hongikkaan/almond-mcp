"""MCP registration for camera-path conditioning capture."""
import json

from almond_mcp.features.capture import conditioning


def register(mcp, context):
    """Register capture tools against this server's live connection context."""
    @mcp.tool()
    def capture_conditioning_pass(
        shot: str,
        out_dir: str,
        width: int = 832,
        height: int = 480,
        passes: str = "rgb,edge,depth",
        fps: int = 16,
        chunk: int = 16,
        rgb_mode: str = "Rendered",
        edge_mode: str = "Technical",
        invert_depth: bool = False,
    ) -> str:
        """
        Capture RGB + edge (line drawing) + depth frames along a camera path from the LIVE Rhino
        document, as conditioning for geometry-guided video generation (Wan VACE / ControlNet).
        Depth and edges are read from the model itself, not estimated, and every frame's camera is
        recorded so the generated video can be re-projected against the source geometry.

        The shot JSON describes a camera path in model units, usually mm, using one of these forms.
          {"type":"orbit","center":[x,y,z],"radius":r,"height":z,"frames":81,
           "start_deg":0,"end_deg":90,"lens":35,"target_height":z}
          {"type":"track","cam0":[x,y,z],"cam1":[..],"target0":[..],"target1":[..],"frames":81,"lens":35}
          {"type":"keyframes","keyframes":[{"camera":[..],"target":[..],"lens":35}, ...],"frames":81}
        Use 4n+1 frames for Wan models (17, 33, 49, 65, 81). 81 frames = 5 s at 16 fps.

        Writes to out_dir: rgb/ edge/ depth/ (f0000.png ...), rgb.mp4 / edge.mp4 / depth.mp4
        (when ffmpeg is available), camera.json (per-frame camera receipt, schema building0.camera/0.1),
        zrange.csv (per-frame depth range), doc.json, summary.json. Depth is grayscale with near = bright
        (Rhino's native convention, what Wan/ControlNet depth expects); set invert_depth for near = dark.
        Camera restoration is best effort after the pass. Returns the summary JSON.
        """
        try:
            shot_dict = json.loads(shot)
            frames = conditioning.build_path(shot_dict)
        except (ValueError, KeyError, TypeError) as e:
            return json.dumps({"status": "error", "message": f"Bad shot description: {e}"})
        pass_list = tuple(p.strip() for p in passes.split(",") if p.strip())
        try:
            summary = conditioning.capture_conditioning_pass(
                frames, out_dir, context._send_and_receive, width=width, height=height, passes=pass_list,
                rgb_mode=rgb_mode, edge_mode=edge_mode, invert_depth=invert_depth, chunk=chunk, fps=fps)
        except ConnectionRefusedError:
            return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"})
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "error", "message": f"Conditioning pass failed: {e}"})
        return json.dumps(summary)


    return {"capture_conditioning_pass": capture_conditioning_pass}
