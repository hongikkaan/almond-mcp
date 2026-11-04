# tools.py explain

## capture_conditioning_pass

<!-- instruction:capture_conditioning_pass -->
Capture RGB, edge and depth image sequences along a camera path in the live Rhino document for geometry-guided video conditioning.

When to use: Produce aligned model-derived conditioning frames and per-frame camera receipts for Wan VACE/ControlNet-style workflows.
Before calling: In managed sessions select a working Plan; out_dir is relative to its artifact directory and defaults to conditioning. Standalone empty out_dir uses the process working directory. Choose even pixel width/height, desired passes and display modes. shot is a JSON string: orbit needs center/radius/height; track needs cam0/cam1/target0/target1; keyframes needs camera/target entries. All support frames; lens is mm, path coordinates/radii/heights use actual document units, not assumed mm.
Inputs from earlier results: Reuse an already selected Plan and verified model bounds/camera coordinates for shot, respecting their units; a previous camera.json records frames[].camera, target and lens_mm, but keyframe shot entries use lens, not lens_mm.
Interpretation: Compare frames_captured with frames_requested, inspect errors and status, and use camera_json/videos paths. Writes selected rgb/edge/depth PNG folders, doc.json, camera.json (building0.camera/0.1), zrange.csv and summary.json; MP4 entries may be null when ffmpeg is unavailable or fails. Depth is model Z-buffer grayscale-8bit, near bright unless inverted, not a metric distance image; zrange.csv records per-frame ranges. 81 frames at 16 fps encodes about 5 seconds; Wan commonly uses 4n+1 frames.
Limits: The pass changes the active camera/display and writes or overwrites named outputs; camera restoration is best effort. Partial capture can leave files and the receipt still lists the planned path. Success counts completed script chunks, not an independent audit of every PNG; inspect outputs before downstream use. This does not generate a video with an AI model.

Args:
    shot: JSON string describing an orbit, track or keyframes shot; coordinates use document units and lens values use millimetres. See the shot examples in this tool description.
    out_dir: Managed session: relative folder beneath the selected Plan artifact directory, default conditioning; select a Plan first. Standalone: output folder, default current working directory.
    width: Even output frame width in pixels.
    height: Even output frame height in pixels.
    passes: Comma-separated pass names: rgb, edge, depth.
    fps: Frames per second recorded for the shot.
    chunk: Number of frames captured per Rhino execution chunk.
    rgb_mode: Installed Rhino display mode used for RGB frames, default Rendered.
    edge_mode: Installed Rhino display mode used for edge frames, default Technical.
    invert_depth: Invert the depth pass when true.
<!-- /instruction:capture_conditioning_pass -->
