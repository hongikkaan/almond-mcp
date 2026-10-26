# tools.py explain

## get_retrieval_status

<!-- instruction:get_retrieval_status -->
Returns compact diagnostics for the local structured retrieval system.
<!-- /instruction:get_retrieval_status -->

## get_rhino_context

<!-- instruction:get_rhino_context -->
Read the LIVE bound Rhino document, selection and current viewport on the UI thread.

Includes document identity/path, units/tolerances, object/layer counts, a bounded
selection summary and camera/display metadata. This query does not create layers,
geometry, dimensions or an Undo record. Unavailable values are null with warnings.
Counts and the current view are context, not a geometric or visibility validation.
Use this snapshot before focused object inspection or editing an existing model.

Args:
    selection_limit: Maximum selected object summaries, from 0 to 200; total/truncated are still reported.
Returns:
    JSON with status, document, selection, viewport and warnings, or an explicit error.
<!-- /instruction:get_rhino_context -->

## get_rhino_probe

<!-- instruction:get_rhino_probe -->
Read fixed geometry observations on the bound Rhino UI thread without modifying the document.

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
<!-- /instruction:get_rhino_probe -->

## get_rhino_viewport_image

<!-- instruction:get_rhino_viewport_image -->
Return the LIVE current Rhino viewport as a JPEG image with document/view metadata.

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
<!-- /instruction:get_rhino_viewport_image -->

## response-585

<!-- instruction:response-585 -->
Load a Bridge with fixed_probes=1 before calling geometry probes.
<!-- /instruction:response-585 -->
