# tools.py explain

## get_retrieval_status

<!-- instruction:get_retrieval_status -->
Returns compact diagnostics for the local structured retrieval system.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_retrieval_status -->

## get_rhino_context

<!-- instruction:get_rhino_context -->
Read selected LIVE Rhino context on the UI thread. sections accepts document,
selection and viewport; default is ["document"]. Unrequested sections are not collected.

Includes document identity/path, units/tolerances, object/layer counts, a bounded
selection summary and camera/display metadata. This query does not create layers,
geometry, dimensions or an Undo record. Unavailable values are null with warnings.
Counts and the current view are context, not a geometric or visibility validation.
Request only the context needed for the task. project_info already verifies the live
document; do not repeat this call merely to check whether that document is live.

Args:
    selection_limit: Maximum selected object summaries, from 0 to 200; total/truncated are still reported.
Returns:
    JSON with status, document, selection, viewport and warnings, or an explicit error.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
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
    expected_model_path: Usually omitted; the runtime supplies the bound document automatically.
Returns:
    JSON with status, probe, document identity/units/tolerance and data, or an explicit error.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_rhino_probe -->

## get_rhino_viewport_image

<!-- instruction:get_rhino_viewport_image -->
Return a Rhino viewport, Named View or Layout as a PNG image, without activating it.

Omit view to capture the current view. Pass view="a" to list viewports, named_views,
and layouts, with only name and guid for each entry. Then pass the desired GUID as view.
Names need not be unique. Named Views render the saved camera off screen using the
current display mode; they never replace the visible viewport. Layouts capture the
paper area, including its details, not the surrounding workspace. A current Layout
also captures its paper, even when a detail is active.

scale_percent=100 means the original pixel dimensions; 50 (default) halves both
dimensions and uses roughly one quarter of the pixels. Named Views use their saved
pixel size (current viewport size if unavailable); Layout 100% means paper at 96 dpi.
No temporary image file is created. Capture does not change camera, selection or
Undo state, or prove geometric correctness. A failed or oversized image is an error;
lower scale_percent explicitly instead of receiving a silently resized image.

Args:
    view: Empty for current view, "a" for the grouped list, or a listed GUID.
    scale_percent: Integer from 1 to 100; default 50. Applies to every capture type.
    include_usage: False returns only an image. True also returns dimensions and an
        illustrative token estimate (32px patches x 1.2, without provider resizing).
        Actual usage depends on the client's model and detail setting, which MCP
        does not supply. PNG compression reduces bytes, not pixel-token counts.
Returns:
    One MCP PNG image by default, or the grouped name/GUID list for view="a".
    Images are limited to 16 megapixels and 4 MiB. No repeated path or GUID metadata.
<!-- /instruction:get_rhino_viewport_image -->

## response-585

<!-- instruction:response-585 -->
Load a Bridge with fixed_probes=1 before calling geometry probes.
<!-- /instruction:response-585 -->
