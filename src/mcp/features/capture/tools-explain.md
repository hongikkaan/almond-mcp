# tools.py explain

## capture_conditioning_pass

<!-- instruction:capture_conditioning_pass -->
Capture RGB, edge and depth image sequences along a camera path in the live Rhino document for geometry-guided video conditioning.

When to use: Produce aligned model-derived conditioning frames and per-frame camera receipts for Wan VACE/ControlNet-style workflows.
Before calling: Choose a writable out_dir explicitly (empty resolves to the process working directory), even pixel width/height, desired passes and display modes. shot is a JSON string: orbit needs center/radius/height; track needs cam0/cam1/target0/target1; keyframes needs camera/target entries. All support frames; lens is mm, path coordinates/radii/heights use actual document units, not assumed mm.
Inputs from earlier results: No prior call is required. Reuse verified model bounds/camera coordinates for shot and respect their units; a previous camera.json records frames[].camera, target and lens_mm, but keyframe shot entries use lens, not lens_mm.
Interpretation: Compare frames_captured with frames_requested, inspect errors and status, and use camera_json/videos paths. Writes selected rgb/edge/depth PNG folders, doc.json, camera.json (building0.camera/0.1), zrange.csv and summary.json; MP4 entries may be null when ffmpeg is unavailable or fails. Depth is model Z-buffer grayscale-8bit, near bright unless inverted, not a metric distance image; zrange.csv records per-frame ranges. 81 frames at 16 fps encodes about 5 seconds; Wan commonly uses 4n+1 frames.
Limits: The pass changes the active camera/display and writes or overwrites named outputs; camera restoration is best effort. Partial capture can leave files and the receipt still lists the planned path. Success counts completed script chunks, not an independent audit of every PNG; inspect outputs before downstream use. This does not generate a video with an AI model.

<!-- /instruction:capture_conditioning_pass -->
