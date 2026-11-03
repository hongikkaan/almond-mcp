# tools.py explain

## get_retrieval_status

<!-- instruction:get_retrieval_status -->
When to use: Diagnose the local retrieval indexes when library availability or search behavior is unclear.
Before calling: No other tool or live Rhino query is required; this is not a mandatory connection preflight when retrieval is already understood.
Inputs from earlier results: No target handle is needed. include_ids=true requests any diagnostic identities that the default response omits; it does not request asset records.
Interpretation: Read the fixed counts/status for the SQLite cache, drawing manifest, current model manifests and model states, configured retrieval mechanisms and embedding adapter. Use the relevant search/list tool next if actual library records are needed.
Limits: ready describes the retrieval system, not proof that every model file is present, placeable or correct. The response is intrinsically bounded and contains no asset list or geometric/scene validation; supplied target IDs are not echoed.

<!-- /instruction:get_retrieval_status -->

## get_rhino_context

<!-- instruction:get_rhino_context -->
When to use: Read needed live document properties, editing state or available view/display-mode catalogues.
Before calling: No preceding call is required for unknown context. Reuse known information; project_info already checks the live document and provides its filename/path. Requires the matching Bridge with context_sections>=2.
Inputs from earlier results: sections selects document, viewport, editor, named_views, layouts, display_modes or viewports. Omit sections for document/named_views/layouts/display_modes. Named View/Layout/Display Mode IDs are always returned, including with include_ids=false. include_ids controls other identities. Request editor with include_editor_details=true for provider, command and Undo evidence.
Interpretation: Explicit sections return only those sections; sections=[] returns status/warnings. next_step appears only when sections is omitted. Document angle_tolerance is in radians; absolute_tolerance uses document units. editor normally returns mode/target/stable/warnings; only a verified normal model is stable, unknown target identity stays null. Use get_objects(scope="selected") for selected entities and a capture tool for images.
Limits: No document or file writes. Counts and camera state do not establish geometric or pixel-visibility correctness. Unavailable observations are null with warnings. No implicit editor query accompanies document or viewport. display_modes is capped at 128 with a warning; use actually listed modes rather than invented aliases. include_editor_details does not implicitly request editor.

Args:
    sections: Optional section names; omitted requests document, named_views, layouts and display_modes.
    include_ids: Include identities outside the always-identified Named View/Layout/Display Mode catalogues.
    include_editor_details: Include provider/command/Undo evidence only when editor is requested.
Returns:
    JSON status/warnings and requested sections. No images, document filename or path.
<!-- /instruction:get_rhino_context -->

## analyze_block_reculviely

<!-- instruction:analyze_block_reculviely -->
When to use: Inspect nested block structure or resolve an occurrence path when top-level object observations are insufficient.
Before calling: Reuse known top-level block GUIDs or obtain them from get_objects(include_ids=true). No lookup is required for an already defined selected/viewport/document outline scope. Requires Bridge block_analysis=1; the tool checks support internally.
Inputs from earlier results: For outline pass options.ids or a previously observed options.path, or choose scope with depth/output budgets. Request options.field_groups for summary, objects, annotations or transforms and include_ids=true when the returned handles/path will feed another call. resolve-block takes only an explicit path of 1..65 GUIDs from the top-level instance inward; use the observed occurrence path, not a definition GUID. expected_model_path is normally supplied by the runtime.
Interpretation: Read mode, document identity/units/tolerance and the returned data as bounded structure/occurrence evidence. After truncation narrow the IDs/path/depth; max_items also bounds eligible visits and may report reason=max_visits. Geometry and annotation details require their explicit options.
Limits: Does not modify the document or certify unknown, unsupported or truncated observations. Requests and responses are capped at 256 KiB of UTF-8 JSON. IDs are omitted by default and supplied target IDs are not echoed; outline field_groups must be a nonempty supported list when supplied.

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

## get_defined_viewcapture

<!-- instruction:get_defined_viewcapture -->
When to use: Capture a known Named View or actual Layout paper without activating it or changing the working camera.
Before calling: No preceding query is needed for a known name/ID. Obtain unknown Named View/Layout names and IDs from get_rhino_context. Requires view_capture=1; the tool checks this internally.
Inputs from earlier results: target_kind is named_view or layout, and target is its name or ID. Ambiguous names are errors; use a unique listed ID. Those two inputs suffice. Optional display_mode uses an installed name/ID for Named Views. The runtime supplies expected_model_path for the bound document.
Interpretation: Returns a PNG and image_file metadata (relative path, bytes, SHA256, lifetime or separate storage failure). Named Views use their saved camera and default Shaded mode. Layouts render the paper and details with print colors/widths, their actual paper proportions and 144 dpi as the 100% reference. Neither capture activates the saved view or changes the model.
Limits: Layouts retain each detail's mode and reject display-mode or explicit-pixel overrides. scale_percent is the desired upper bound, default 75; oversized defined-view PNGs are reduced automatically, with a warning and actual usage dimensions, to fit 16 megapixels/4 MiB. Explicit Named View pixels are never silently resized. No live camera/selection/visibility edits; file writes are additive. Labels default false; optional overlays are bounded to 200 and Layout detail labels are unavailable. Realtime display modes cannot be independently rendered.

Args:
    target_kind: named_view or layout.
    target: Existing name or ID; case-insensitive name matches must be unique.
    scale_percent: 1..100, default 75. Desired upper bound; percentage captures may shrink to fit the delivery budget.
    include_usage: Include actual dimensions and an illustrative pixel-based token estimate, not measured usage.
    display_mode: Installed mode name/ID for Named Views; empty uses Shaded. Layouts reject overrides.
    labels: Optional transient entity labels; default false.
    depth: Entity-label expansion depth 1..8.
    width, height: Optional Named View pixels, both 128..2048 with scale_percent=100. Not used for Layouts.
    expected_model_path: Usually omitted; runtime supplies the bound model.
Returns:
    PNG image and image_file metadata, plus warnings/usage when applicable.
<!-- /instruction:get_defined_viewcapture -->

## get_current_viewcapture

<!-- instruction:get_current_viewcapture -->
When to use: Capture the current model viewport, optionally selecting and zooming to several targets in the actual Rhino screen and isolating them there.
Before calling: No preceding query is required for the current screen. For targets, reuse observed object/group/Holon IDs; get_objects can supply missing object IDs. An active Layout requires switching to a model viewport, or get_defined_viewcapture for its paper. Requires view_capture=1.
Inputs from earlier results: target_ids accepts multiple IDs. target_kind=object accepts mixed Rhino geometry types, including block instances, without a geometry-type allowlist; block is the same object-ID route. group expands current group members; holon resolves live effective members. isolate defaults false and requires targets. Targets must currently exist and be selectable by Rhino; hidden/locked objects are not automatically shown or unlocked.
Interpretation: No arguments captures the current screen as is. Targets replace the live selection and apply Zoom Selected; isolate=true first invokes Rhino's native Isolate. The screen remains at that camera/selection/visibility after capture. A display_mode override also changes the live viewport. image_file reports managed PNG storage independently of image success. view_change/mutation_applied preserve completed or uncertain screen changes even when capture fails; never retry an uncertain mutation automatically.
Limits: Object shape/type is unrestricted; IDs must refer to current model-space objects, not Layout objects or block-definition members. The shared focus operation accepts at most 4096 resolved objects. Invalid input/targets are rejected before selection changes. Native Isolate retains locked context and supports Unisolate; no custom renderer or geometry duplication is used. The native command owns its Undo history. No 3DM save occurs. labels defaults false; optional labels are transient, bounded to 200, with depth 1..8. PNG is capped at 16 megapixels/4 MiB; image/storage failure does not undo screen changes. Realtime mode overrides are rejected before changes.

Args:
    target_ids: Optional nonempty string array of object, group or Holon IDs. Duplicate resolved objects are selected once.
    target_kind: object (default), group, block (ordinary object IDs), or holon; this selects the ID namespace, not allowed geometry types.
    isolate: False by default. True invokes actual Rhino Isolate before Zoom Selected; use Unisolate to restore visibility.
    scale_percent: 1..100, default 75; changes image resolution, not viewport window size.
    include_usage: Include dimensions and an illustrative pixel-token estimate, not measured usage.
    display_mode: Optional installed raster mode name/ID; changes the live model viewport when supplied.
    labels: Optional transient labels; default false. The selection highlight remains Rhino's normal display.
    depth: Label expansion depth 1..8.
    width, height: Optional image pixels, both 128..2048 with scale_percent=100; does not resize the Rhino window.
    expected_model_path: Usually omitted; runtime supplies the bound model.
Returns:
    PNG image and image_file metadata; requested live changes also return their outcome. Errors preserve mutation uncertainty.
<!-- /instruction:get_current_viewcapture -->
<!-- instruction:get_objects -->
When to use: Read the actual object set, properties, grouping or Brep faces needed to choose targets or verify a modeling decision without changing Rhino.
Before calling: No preceding call is needed to discover visible, selected or document objects. Reuse known object GUIDs with scope="ids", or actual Rhino group GUIDs (including a Holon's rhino_group_id) with scope="groups". Holon registration is not required. Requires object_observation>=3; the tool checks the loaded Bridge before dispatch.
Inputs from earlier results: object_ids accepts 1..4096 distinct GUIDs only with scope="ids"; group_ids accepts 1..64 distinct group GUIDs only with scope="groups". Filters select top-level model objects before grouping or block expansion: exact layer_paths/object_types, case-insensitive name_contains and explicit UserDictionary conditions combined with AND. include_ids=true retains identities; fields=["id"] explicitly requests them. Geometry/face details use result_mode="objects" and the observed object GUID/geometry_crc; later face pages require expected_geometry_crcs for all requested IDs. The runtime supplies the bound expected_model_path.
Interpretation: visible is the default, selected reads current selection, document includes hidden objects, and groups returns the distinct current model-space members of the specified groups. result_mode="objects" is a flat list of document objects; summary counts by layer/object/geometry type. hierarchy summarizes complete groups and blocks, then expand_groups/expand_blocks independently expand them to depth 1..8 (root=1). Explicit group roots remain identifiable after filtering. nodes use number/parent_number to preserve hierarchy even without IDs or across pages. Overlapping/equal-member groups are separate branches; repeated occurrences are not distinct document objects. document_object=false marks block-definition members, identified by root_object_id plus block_path_ids, never standalone edit GUIDs. Their bounds are in world coordinates, metadata comes from the definition, and effective occurrence visible/selected is null. Geometry detail/face editing references are available only in objects mode.
Limits: No selection, camera, geometry or file writes. Scope and filters do not infer architectural identity, Scene membership, screen pixels or occlusion. Group relations never pull in other groups' outside members. Expansion/depth require hierarchy mode; depth defaults 1 and both expansion flags default false. children_state distinguishes leaf/collapsed/expanded/depth_limit/cycle. complete covers pagination at the requested depth, not unexpanded descendants. Keep scope/options/model unchanged across offset/limit pages and read next_offset; numbers are traversal positions, not persistent handles. Object/hierarchy/summary pages allow 1..200 rows, face pages 1..128 faces, scans/traversals at most 100000 entries, and JSON 256 KiB. fields selects id/name/layer_path/object_type/geometry_kind/geometry_crc/visible/selected/hidden/locked/bounds/groups/user_dictionary; objects additionally allows geometry_valid/solid/manifold/volume/face_count/faces or include_geometry. Explicit fields override include_geometry. UserDictionary filters use source=attributes|geometry, key, scalar any_of; values are not split or inferred. Metadata omissions and unfinished pages remain explicit; errors retain evidence with MCP isError=true.

<!-- /instruction:get_objects -->

<!-- instruction:get_object_intersections -->
When to use: Check volume overlap among identified closed solid objects without requiring Component registration or modifying the document.
Before calling: Reuse known current object GUIDs or obtain them from get_objects(include_ids=true/fields=["id"]). Choose the explicit scope rather than assuming group membership adds targets.
Inputs from earlier results: Pass 1..512 object_ids; max_pairs=1..64 bounds candidate-pair calculations per page. Reuse next_cursor with exactly the same targets to continue; a geometry/scope change invalidates the cursor. include_blocks=true expands transformed nested block members without changing definitions.
Interpretation: Combine required pages and distinguish pagination_complete (candidate enumeration finished) from complete (this response alone verifies the whole scope). Each pair's a.handle, b.handle and pair_state are supplied independently of ID-display settings; pass that same observation to show_object_intersection or resolve_object_intersection if a later authorized display/edit is needed. Read unsupported/unknown/unexamined outcomes instead of treating them as clear pairs.
Limits: Supports closed Breps/Extrusions and oriented manifold Meshes. Brep/Mesh mixing uses temporary meshing and is explicitly approximate; disjoint Meshes need not be split/rejoined in the document. This is volume-overlap evidence, not clearance, design suitability or code compliance. status="error" maps to MCP isError=true; normal unknown/complete=false/next_cursor values remain normal evidence and must not be rewritten as no intersection.

<!-- /instruction:get_object_intersections -->

<!-- instruction:capture_rhino_inspection -->
When to use: Compare several specified viewpoints or object sets in one PNG when visual evidence beyond a single current viewport is needed.
Before calling: Reuse known GUIDs and view/mode choices; obtain missing targets through get_objects and unknown modes through get_rhino_context(sections=["display_modes"], include_ids=true). Requires a verified stable model editor context; group/block or unknown editing is rejected. No separate context refresh is mandatory if the needed information is already current.
Inputs from earlier results: views contains 1..16 tiles with direction, display_mode, label and optional distinct top-level object_ids (1..512). An omitted/empty tile set uses existing document visibility. Alternatively pass one common top-level object_ids set (1..4096, never empty) for all tiles with inspection_shared_scope=1; do not mix it with nonempty tile-level sets. model_view_id can reuse a listed model viewport GUID to preserve an active Layout/Detail, with inspection_model_view=1. Runtime normally supplies expected_model_path.
Interpretation: Read the image with each tile's metadata/errors. Top-level complete means the requested tiles captured; scope.complete concerns requested GUIDs being in document-visible scope, not pixel exposure or design correctness. Common-scope GUIDs/count are returned once in shared_scope and referenced by scope.shared_scope_ref. Partial success retains usable tiles and tile errors. image_file supplies a managed relative path, bytes, SHA256 and Plan/connection lifetime or a separate storage error while image content remains available.
Limits: Camera/selection/hidden state and document content are unchanged; PNG storage is additive, not a 3DM save. Filtered tiles reject block instances/interior objects, while unfiltered visible scope renders blocks normally. An active Layout without model_view_id gives layout_not_supported; use get_defined_viewcapture(target_kind="layout", target=Layout_ID) for paper. direction accepts current, top/bottom/front/back/left/right, iso_ne/nw/se/sw and below_ne/nw/se/sw. Tile pixels are 128..2048 each (default 640x480), columns controls layout; combined output is capped at 16M pixels/4 MiB PNG. Requests are 256 KiB and non-image metadata 512 KiB; oversize data is not silently truncated. A preview or subset capture cannot establish full-scope visibility.

<!-- /instruction:capture_rhino_inspection -->
