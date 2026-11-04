# tools.py explain

<!-- instruction:list_design_scenes -->
List Scene names across the project without a Plan or live document lookup.
When to use: Discover Scene handles for metadata, live-object queries or Plan context.
Before calling: name is a case-insensitive substring and file_name an exact optional filter; choose limit (1–200) and nonnegative offset.
Inputs from earlier results: None required. With include_ids=true, scenes[].scene_id feeds get_design_scene, update_design_scene, get_scene_objects or Plan scene_ids; scope also exposes project_file_id for file-binding inputs when recorded.
Interpretation: Names are the default; field_groups supports scope (file_name, units), state (revision), audit (timestamps) or all, plus geometry when available. total counts matches and truncated marks additional results after the page.
Limits: include_ids independently exposes handles; field_groups cannot invent absent data. This lists stored Scene metadata, not live objects or proof of which document is open.

Args:
    name: Optional case-insensitive Scene name filter.
    file_name: Optional stored project filename filter; this does not verify current geometry.
    limit: Page size, 1..200.
    offset: Zero-based starting row for this page; use the same filters when requesting the next page.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: scope, state, geometry, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
<!-- /instruction:list_design_scenes -->

## create_design_scene

<!-- instruction:create_design_scene -->
Create a persistent Scene handle with units and an optional project-file association.
When to use: Establish local Scene context for semantic Holons or planning, without generating geometry. A Scene describes behavior, program, a meaningful situation and its spatial context; it may continue across Phases. Its name alone establishes neither actual geometry nor edit targets.
Before calling: Choose units from mm, cm, m, in or ft. file_name must contain no folders; a blank name becomes Untitled scene.
Inputs from earlier results: If choosing an existing file, project_info(sections=["project"], include_ids=true).project.files[].project_file_id feeds project_file_id and disambiguates duplicate filenames; an unambiguous file_name can be supplied instead.
Interpretation: scene.scene_id feeds get_design_scene, update_design_scene, get_scene_objects or Plan scene_ids; scene.revision records the initial metadata revision. Metadata is retrieved by handle rather than repeated in model context.
Limits: This creates neither Rhino geometry nor Holon bindings and does not verify a live model. A file reference is metadata, not a model rename, move or document switch.

Args:
    name: Scene name describing a design area or behavioral/programmatic context; an empty name becomes Untitled.
    units: Scene unit code: mm, cm, m, in or ft; does not change Rhino document units.
    file_name: Project filename without folders. Use project_file_id to disambiguate duplicate filenames; this is a stored association, not a file operation.
    project_file_id: Existing project.files[].project_file_id from project_info(sections=["project"], include_ids=true). Must agree with file_name when both are supplied.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Read a stored Scene summary with revision, units and registered Holon/object counts.
When to use: Inspect known Scene metadata without requesting live geometry.
Before calling: Supply an existing scene_id; select field_groups for additional available metadata.
Inputs from earlier results: Use create_design_scene.scene.scene_id or list_design_scenes(include_ids=true).scenes[].scene_id as scene_id. With scope and include_ids=true, scene.project_file_id feeds file-binding inputs; retain the supplied scene_id for get_scene_objects or Plan scene_ids.
Interpretation: Summary includes name, units, revision, holons, objects and direct_objects; objects is null when direct memberships or exclusions make a deduplicated live count necessary. live_verified=false marks cached counts. field_groups supports scope (file_name, empty when unrecorded, and available units/model_path), state (revision), geometry (available bounds/component), audit (timestamps) or all.
DB와 Rhino 문서의 상태가 다르면 수동으로 정렬(align)해야 합니다.
Scene membership is a design decision, not an automatically detected mismatch. Existing Holon requires_sync reports technical registration state separately.
Limits: IDs are hidden unless include_ids=true, and the supplied scene_id is not echoed. Optional groups expose only returned fields; this is not current Rhino membership, a geometry backup or edit authorization.

Args:
    scene_id: Existing Scene ID from list_design_scenes(include_ids=true) or a recorded Scene reference.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: scope, state, geometry, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
<!-- /instruction:get_design_scene -->

<!-- instruction:update_design_scene -->
Change or clear a Scene's project-file association without renaming or moving the Rhino document.
When to use: Correct stored file context for an existing Scene.
Before calling: Supply scene_id; omit both file inputs to retain the association, or set file_name='' without project_file_id to clear it. A filename must contain no folders.
Inputs from earlier results: A created/listed scene_id feeds scene_id. project_info(sections=["project"], include_ids=true).project.files[].project_file_id feeds project_file_id for an existing file, required when filenames are duplicated.
Interpretation: scene.scene_id remains reusable for Scene queries; scene.revision changes when the association changes and stays unchanged for a no-op.
Limits: This updates only metadata, not Scene name/units, geometry, Holon ownership, the live document or its path. It has no expected_revision input; a returned Scene revision is not a Plan expected_revision.

Args:
    scene_id: Existing Scene ID from list_design_scenes(include_ids=true) or a recorded Scene reference.
    file_name: Optional replacement filename without folders; empty clears the association when project_file_id is omitted. Omission keeps it.
    project_file_id: Optional existing project file ID; must agree with file_name when both are supplied. This changes metadata, not a file on disk.
<!-- /instruction:update_design_scene -->

## get_scene_objects

<!-- instruction:get_scene_objects -->
Read live Rhino objects belonging to a Scene, including registered Holon members, ordinary objects and clipping planes.
When to use: Inspect current registered objects, including direct members and linked descendant Holons, rather than cached Scene counts.
Before calling: Use a live saved document in stable editing state; at most 64 Holon registrations may be observed for that model. expected_model_path uses the bound model when omitted and can explicitly fence the model to observe; choose limit (1–200) and nonnegative offset.
Inputs from earlier results: A created/listed scene_id feeds scene_id. With include_ids=true, objects[].rhino_guid can feed upsert_ontological_holon.object_ids only for a separately intended and authorized mutation; field_groups=["geometry"] also exposes holon_id for get_ontological_holon.holon_id and available bounds_mm. scope exposes available model_path for expected_model_path.
Interpretation: live_verified=true identifies successful live observation; total, offset and truncated bound the returned object page, not the entire project's geometry. field_groups supports scope, state, geometry, audit or all for available object fields; audit enables timestamps when present.
Limits: IDs/GUIDs are hidden by default; supplied scene_id is not echoed. Incomplete, unstable or unresolved native observations fail with MCP isError=true. Group/block editing cannot certify persistent Holon ownership; an unavailable member set is not an empty Scene or cached live substitute. Direct memberships and Scene-specific exclusions are stored per model; missing direct members make the query fail until removed. Pagination does not bypass the 64-group observation limit.

Args:
    scene_id: Existing Scene ID from list_design_scenes(include_ids=true) or a recorded Scene reference.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: scope, state, geometry, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
    limit: Page size, 1..200, for verified live Scene objects.
    offset: Zero-based starting row for this page; use the same filters when requesting the next page.
    expected_model_path: Usually omitted: managed sessions supply the bound saved Rhino document. An explicit path must match that binding; it does not switch documents.
<!-- /instruction:get_scene_objects -->


<!-- instruction:add_scene_objects -->
Register a GUID array of top-level Rhino objects including ordinary geometry and clipping planes in a Scene, returning only zero-based indices for failed and already-present entries while omitting successful GUIDs.
When to use: Add direct Scene membership or restore a group member excluded from this Scene. A member already present through a Holon counts as already present. No group or geometry is edited.
Before calling: Use a saved bound model, an existing scene_id, and an object_ids array of at most 4096 GUID strings. Items are processed in input order, including duplicates. A malformed, missing or unsupported GUID fails individually.
Inputs from earlier results: Use a created/listed scene_id and Rhino object GUIDs obtained from observation or model creation.
Interpretation: failed_indices and already_present_indices contain zero-based positions in object_ids. Successful GUIDs and positions are not returned. Overall errors mean the batch could not be safely evaluated.
Limits: This persists Scene membership per model and does not delete or create geometry. Reopen clients after the source change; older workers cannot safely interpret direct membership.

Args:
    scene_id: Existing Scene ID from list_design_scenes(include_ids=true).
    object_ids: Array of object GUIDs, including ordinary geometry or clipping planes, up to 4096 entries.
    expected_model_path: Usually omitted; the managed session supplies the bound saved document. An explicit path must match it.
<!-- /instruction:add_scene_objects -->

<!-- instruction:remove_scene_objects -->
Remove a GUID array of top-level Rhino objects including ordinary geometry and clipping planes from a Scene, returning only zero-based indices for failed and already-absent entries while omitting successful GUIDs.
When to use: Remove direct membership or exclude a Holon member from this Scene without changing the group or deleting geometry.
Before calling: Use a saved bound model, an existing scene_id and an object_ids array of at most 4096 GUID strings. Items are processed in input order, including duplicates.
Inputs from earlier results: Use a created/listed scene_id and object GUIDs from a prior observation or Scene membership record.
Interpretation: failed_indices and already_absent_indices contain zero-based positions in object_ids. A valid GUID absent from the Scene is already absent even when absent from the document; successful GUIDs and positions are omitted.
Limits: This changes Scene membership only, not model objects or Holon groups. Overall errors mean the batch could not be safely evaluated.

Args:
    scene_id: Existing Scene ID from list_design_scenes(include_ids=true).
    object_ids: Array of object GUIDs, including ordinary geometry or clipping planes, up to 4096 entries.
    expected_model_path: Usually omitted; the managed session supplies the bound saved document. An explicit path must match it.
<!-- /instruction:remove_scene_objects -->
