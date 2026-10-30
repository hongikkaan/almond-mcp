# tools.py explain

## get_retrieval_status

<!-- instruction:get_retrieval_status -->
Returns compact diagnostics for the local structured retrieval system.
This is an intrinsically bounded diagnostic: fixed scalar counts/status and configured index names, not asset records.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_retrieval_status -->

## get_rhino_context

<!-- instruction:get_rhino_context -->
Read selected LIVE Rhino context on the UI thread. sections accepts document,
selection, viewport, editor and display_modes; default is ["document"]. Unrequested sections are not collected.
Document/selection/viewport responses also contain compact editor mode/target/stable
so isolation is immediately visible. Request editor for provider evidence and warnings;
sections=[] skips editor observation for capability-only calls.
editor reports mode (model/group/block/unknown), the known target and stable. Only a
verified normal model is stable; active isolation, transitions and unsupported editor
versions are unstable. Unknown target identity remains null, never inferred from selection.
display_modes lists at most 128 installed mode names/GUIDs. Shaded, Dark and CadWhite
are choices only if actually installed; do not invent aliases for custom modes.

Includes document identity/path, units/tolerances, object/layer counts, a bounded
selection summary and camera/display metadata. This query does not create layers,
geometry, dimensions or an Undo record. Unavailable values are null with warnings.
Counts and the current view are context, not a geometric or visibility validation.
Request only the context needed for the task. project_info already verifies the live
document; do not repeat this call merely to check whether that document is live.

Args:
    selection_limit: Maximum selected object summaries, from 0 to 200; total/truncated are still reported.
    recursive: False by default: summarize complete top-level groups and block instances.
        True expands nested members only to depth; partial groups remain object selections.
    depth: 1..8, default 1. IDs are omitted unless include_ids=true.
    include_image: False keeps the JSON-only response. True returns JSON text first and
        the current PNG from the same native UI call. An image_error preserves available
        context when capture fails. Use this when the current viewport is needed visually.
Returns:
    JSON with status, document, selection, viewport and warnings, or an explicit error.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_rhino_context -->

## analyze_block_reculviely

<!-- instruction:analyze_block_reculviely -->
Read nested block structure or resolve a block occurrence without modifying the document.

Requests and responses are bounded to 256 KiB of UTF-8 JSON. Unknown, unsupported
and truncated observations remain unverified. Requires Bridge block_analysis=1.

Args:
    mode: outline traverses objects and nested definitions; resolve-block finds
        candidates for the current editing context along an explicit occurrence path.
    options: outline accepts ids or path, otherwise scope (selected/viewport/document),
        depth and output budgets. field_groups is a nonempty list of summary, objects,
        annotations and transforms; the default is a compact summary. include_geometry
        and annotations explicitly request their details. Narrow IDs/path/depth after
        truncation; max_items also bounds eligible visits (reason=max_visits).
        resolve-block accepts only path: 1..65 GUIDs from the top-level instance inward.
    expected_model_path: Usually omitted; the runtime supplies the bound document path.
    include_ids: Include IDs when needed; supplied target IDs are not repeated.
Returns:
    JSON with status, mode, document identity/units/tolerance and data, or an explicit error.
<!-- /instruction:analyze_block_reculviely -->

## get_rhino_viewport_image

<!-- instruction:get_rhino_viewport_image -->
Return a Rhino viewport, Named View or Layout as a PNG image, without activating it.

Omit view to capture the current view. Pass view="a" to list viewports, named_views,
and layouts, with only name and guid for each entry. Then pass the desired GUID as view.
Names need not be unique. Named Views render the saved camera off screen using
Shaded by default; they never replace the visible viewport. Layouts capture the
paper area, including its details, not the surrounding workspace. A current Layout
also captures its paper, even when a detail is active.

scale_percent=100 means the original pixel dimensions; 75 (default) retains 75% of both
dimensions and uses 56.25% of the pixels. Named Views use their saved
pixel size (current viewport size if unavailable); Layout 100% means paper at 96 dpi.
No temporary image file is created. Capture does not change camera, selection or
Undo state, or prove geometric correctness. A failed or oversized image is an error;
lower scale_percent explicitly instead of receiving a silently resized image.

Args:
    view: Empty for current view, "a" for the grouped list, or a listed GUID.
    scale_percent: Integer from 1 to 100; default 75. Use 100 for visual drawing review. Controls pixels, not a Layout Detail's drawing scale.
    include_usage: False returns only an image. True also returns dimensions and an
        illustrative token estimate (32px patches x 1.2, without provider resizing).
        Actual usage depends on the client's model and detail setting, which MCP
        does not supply. PNG compression reduces bytes, not pixel-token counts.
    display_mode: Installed display mode name or GUID. Empty preserves the current
        model viewport mode; Named View/group/block captures default to Shaded. List
        available modes with get_rhino_context(sections=["display_modes"], include_ids=true).
        Realtime rendering modes such as Raytraced are rejected; this tool does not
        wait for asynchronous rendering to finish.
    labels: True by default. Transient pixels show top-level group name/GUID, block
        instance name/GUID and ungrouped object GUID, without creating document objects.
        At most 200 labels; explicit smaller targets/depth narrow a truncated overlay.
    depth: 1..8, default 1; higher values expose nested entity labels.
    target_kind: view (default), group or block. group/block frame target bounds in a
        detached viewport and label that target; surrounding geometry stays visible.
    target_id: Persistent group GUID or block instance GUID for group/block; leave view
        empty. Definition GUIDs are not block instance targets.
    Layouts retain each detail's mode, reject a mode override, and explicitly warn that
        detail labels are unavailable; capture a Named View/model viewport for labels.
Returns:
    One MCP PNG image by default, with text only for explicit warnings/usage, or the grouped name/GUID list for view="a".
    Images are limited to 16 megapixels and 4 MiB. No repeated path or GUID metadata.
<!-- /instruction:get_rhino_viewport_image -->
