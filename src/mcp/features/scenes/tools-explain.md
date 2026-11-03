# tools.py explain

<!-- instruction:list_design_scenes -->
List Scene names across the project without a Plan or live document lookup.
When to use: Discover Scene handles for metadata, live-object queries or Plan context.
Before calling: name is a case-insensitive substring and file_name an exact optional filter; choose limit (1–200) and nonnegative offset.
Inputs from earlier results: None required. With include_ids=true, scenes[].scene_id feeds get_design_scene, update_design_scene, get_scene_objects or Plan scene_ids; scope also exposes project_file_id for file-binding inputs when recorded.
Interpretation: Names are the default; field_groups supports scope (file_name, units), state (revision), audit (timestamps) or all, plus geometry when available. total counts matches and truncated marks additional results after the page.
Limits: include_ids independently exposes handles; field_groups cannot invent absent data. This lists stored Scene metadata, not live objects or proof of which document is open.
<!-- /instruction:list_design_scenes -->

## create_design_scene

<!-- instruction:create_design_scene -->
Create a persistent Scene handle with units and an optional project-file association.
When to use: Establish local Scene context for semantic Holons or planning, without generating geometry.
Before calling: Choose units from mm, cm, m, in or ft. file_name must contain no folders; a blank name becomes Untitled scene.
Inputs from earlier results: If choosing an existing file, project_info(sections=["project"], include_ids=true).project.files[].project_file_id feeds project_file_id and disambiguates duplicate filenames; an unambiguous file_name can be supplied instead.
Interpretation: scene.scene_id feeds get_design_scene, update_design_scene, get_scene_objects or Plan scene_ids; scene.revision records the initial metadata revision. Metadata is retrieved by handle rather than repeated in model context.
Limits: This creates neither Rhino geometry nor Holon bindings and does not verify a live model. A file reference is metadata, not a model rename, move or document switch.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Read a stored Scene summary with revision, units and registered Holon/object counts.
When to use: Inspect known Scene metadata without requesting live geometry.
Before calling: Supply an existing scene_id; select field_groups for additional available metadata.
Inputs from earlier results: Use create_design_scene.scene.scene_id or list_design_scenes(include_ids=true).scenes[].scene_id as scene_id. With scope and include_ids=true, scene.project_file_id feeds file-binding inputs; retain the supplied scene_id for get_scene_objects or Plan scene_ids.
Interpretation: Summary includes name, units, revision, holons and objects; live_verified=false marks cached counts. field_groups supports scope (file_name, empty when unrecorded, and available units/model_path), state (revision), geometry (available bounds/component), audit (timestamps) or all.
DB와 Rhino 문서의 상태가 다르면 수동으로 정렬(align)해야 합니다.
Scene membership is a design decision, not an automatically detected mismatch. Existing Holon requires_sync reports technical registration state separately.
Limits: IDs are hidden unless include_ids=true, and the supplied scene_id is not echoed. Optional groups expose only returned fields; this is not current Rhino membership, a geometry backup or edit authorization.
<!-- /instruction:get_design_scene -->

<!-- instruction:update_design_scene -->
Change or clear a Scene's project-file association without renaming or moving the Rhino document.
When to use: Correct stored file context for an existing Scene.
Before calling: Supply scene_id; omit both file inputs to retain the association, or set file_name='' without project_file_id to clear it. A filename must contain no folders.
Inputs from earlier results: A created/listed scene_id feeds scene_id. project_info(sections=["project"], include_ids=true).project.files[].project_file_id feeds project_file_id for an existing file, required when filenames are duplicated.
Interpretation: scene.scene_id remains reusable for Scene queries; scene.revision changes when the association changes and stays unchanged for a no-op.
Limits: This updates only metadata, not Scene name/units, geometry, Holon ownership, the live document or its path. It has no expected_revision input; a returned Scene revision is not a Plan expected_revision.
<!-- /instruction:update_design_scene -->

## get_scene_objects

<!-- instruction:get_scene_objects -->
Read live Rhino objects belonging to a Scene's registered semantic Holon groups in the bound model.
When to use: Inspect current members of registered groups, including linked descendant Holons, rather than cached Scene counts.
Before calling: Use a live saved document in stable editing state; at most 64 Holon registrations may be observed for that model. expected_model_path uses the bound model when omitted and can explicitly fence the model to observe; choose limit (1–200) and nonnegative offset.
Inputs from earlier results: A created/listed scene_id feeds scene_id. With include_ids=true, objects[].rhino_guid can feed upsert_ontological_holon.object_ids only for a separately intended and authorized mutation; field_groups=["geometry"] also exposes holon_id for get_ontological_holon.holon_id and available bounds_mm. scope exposes available model_path for expected_model_path.
Interpretation: live_verified=true identifies successful live observation; total, offset and truncated bound the returned object page, not the entire project's geometry. field_groups supports scope, state, geometry, audit or all for available object fields; audit enables timestamps when present.
Limits: IDs/GUIDs are hidden by default; supplied scene_id is not echoed. Incomplete, unstable or unresolved native observations fail. This read never registers individual objects in the DB, and pagination does not bypass the 64-group observation limit.
<!-- /instruction:get_scene_objects -->
