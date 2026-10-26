# tools.py explain

## capture_conditioning_pass

<!-- instruction:capture_conditioning_pass -->
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
<!-- /instruction:capture_conditioning_pass -->
