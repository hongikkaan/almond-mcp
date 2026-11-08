# tools.py explain

## plan_section

<!-- instruction:plan_section -->
When to use: Generate or update model-space section curves, hatches and visible elevation curves from observed clipping-plane GUIDs using Almond's built-in PlanSection algorithm.
Before calling: Use Create for a new drawing or to replace the existing local drawing for the same clipping; Update regenerates existing drawings at their saved placement and skips missing ones. Supply clipping_ids and only intended options. Create points maps requested clipping GUIDs to finite [x,y] or [x,y,z] in document units; omit points for Update. Omitted Create placement uses saved draft_plane or the origin, so separate drawings may overlap unless you specify their placement.
Inputs from earlier results: Reuse observed clipping-plane GUIDs. Within the result budget, results return each clipping's status, generated object_ids and the algorithm report. This dedicated tool executes the packaged algorithm inside the Bridge; it requires plan_section=1 and the built-in Python runtime, not RhinoCode or StartScriptServer.
Interpretation: success means all requested drawings completed; partial or cancelled is a structured outcome (MCP isError=false), preserving per-clipping evidence and any already completed drawings, not confirmation that the whole request completed. Native execution failures become status=error/MCP isError=true with the original native_status and diagnostics preserved. Update may report skipped when no local drawing exists. Elevation object print colors and widths preserve distance interpolation through final output, defaulting to 0.09→0.04 mm and 80→45% darkness. Section and hatch print properties follow their Drawing layers.
Limits: Only Create/Update Document output is exposed here. This does not create Layouts, change Plan/Step status, save the model, or expose Move/PDF/Files. It reuses the existing Undo scope and never edits attached source geometry. A Layout Detail can present the model-space drawing; get_defined_viewcapture(target_kind="layout", target=Layout_ID) captures its paper. Timeout or an unconfirmed result is not rollback: inspect existing drawings and runtime completion before any retry. Do not regenerate to recover a missing response. Long native computation runs on Rhino's UI thread; Escape cancellation follows the existing PlanSection checkpoints.
Output size: Small results return per-clipping evidence directly. Larger/deeper results return result_delivery=paged with result_id, result_sha256 and counts; use get_plan_section_result to recover the full JSON without another drawing mutation. Retention is in the Bridge process for the same document instance: up to one hour, latest 8 receipts within 64 MiB UTF-16 total, with older receipts evicted as needed. Read promptly; save the reconstructed result in task artifacts if needed. A single result exceeding that retention budget returns unconfirmed/error rather than silently truncating. The common 64 KiB/16-container capture limits remain unchanged. Timeout, missing/expired receipt or unconfirmed output is not rollback and never authorizes automatic regeneration. This is not a RhinoCode journal. Existing metadata_conflicts remains a 64-entry sample with full metadata_conflict_count.

Args:
    operation: Create or Update.
    clipping_ids: Nonempty list of observed clipping-plane GUIDs. Duplicate identities are processed once.
    points: Optional Create-only mapping of requested clipping GUIDs to [x,y] or [x,y,z] absolute drawing origins in document units. Omit for Update.
    hatch: Generate section hatches from existing source section styles.
    elevation: Include visible elevation curves behind the clipping plane.
    small_details: Retain the existing small-detail protection mode when true.
    near_width: Nearest elevation object print width in mm; positive and at least far_width. Preserved in final output.
    far_width: Farthest elevation object print width in mm; positive and at most near_width. Preserved in final output.
    near_dark: Nearest elevation object print darkness percentage, 0..100 and at least far_dark. Preserved in final output.
    far_dark: Farthest elevation object print darkness percentage, 0..100 and at most near_dark. Preserved in final output.
    expected_model_path: Bound saved-document path supplied by the runtime; an explicit value must match that binding.
<!-- /instruction:plan_section -->

## get_plan_section_result

<!-- instruction:get_plan_section_result -->
When to use: Read a retained, paged PlanSection execution result without regenerating any drawing.
Before calling: Use the same bound document instance and result_id from plan_section.result when result_delivery=paged. Start at offset=0, then pass the returned next_offset until it is null.
Inputs from earlier results: plan_section.result.result_id selects the retained result; each page's next_offset selects the next fragment.
Interpretation: Concatenate json_chunk strings in order, then parse the reconstructed JSON. Offsets and total_characters count UTF-16 code units; use returned offsets, not a Python string length. result_sha256 hashes the reconstructed UTF-8 JSON. Pages are at most 4096 UTF-16 units and do not split surrogate pairs. Counts/status describe the stored execution, not current geometry.
Limits: Read-only; never calls PlanSection or creates Undo records. Receipts expire after one hour, Bridge restart, or cache eviction (latest 8 within 64 MiB total). A different document instance cannot read them. plan_section_result_expired means inspect existing drawings and execution evidence, not rerun Create/Update. No arbitrary file paths or code are accepted.

Args:
    result_id: Opaque 32-character receipt ID from plan_section.result.result_id.
    offset: Start at zero; subsequently copy next_offset from the preceding page.
    expected_model_path: Bound saved-document path; explicit value must agree with the runtime binding.
<!-- /instruction:get_plan_section_result -->

## get_modeling_policy

<!-- instruction:get_modeling_policy -->
When to use: Read the metadata vocabulary and material/layer conventions when an explicitly requested naming or metadata operation needs them.
Before calling: No other tool is required; reuse a known policy rather than fetching it for every modeling action.
Inputs from earlier results: None; this tool takes no arguments. Use policy keys to interpret existing metadata or author only the metadata the user requested.
Interpretation: status and policy describe JSON-defined object/group keys and naming conventions, not the current contents of Rhino.
Limits: Reading policy does not create layers, assign materials or stamp objects. Names are free; compatibility keys are not a checklist. Preserve user metadata and asset provenance; ordinary names, layers and materials do not require Almond management UserStrings.

<!-- /instruction:get_modeling_policy -->

## execute_rhino_script

<!-- instruction:execute_rhino_script -->
When to use: Run synchronous modeling, editing or custom measurements in the bound Rhino when a fixed observation or dedicated tool does not cover the task.
Before calling: Use known document units/tolerance and explicit targets; obtain missing object IDs or geometry from get_objects rather than guessing. Official RhinoCode/StartScriptServer must be available. The bundled rhino3d-scripts skill and API/loading references remain available through get_modeling_guide(include_scripting=True); no separate installation is needed.
Inputs from earlier results: Reuse observed object GUIDs in script and choose language explicitly when not using the default Python 3. Python/python2 assign JSON-compatible values to result; dict/list keep structured data, whereas json.dumps produces text. csharp/csharp-script accept statement bodies with doc and result_json, not a class/Run wrapper. command accepts one complete macro without added !, Pause or dialogs. General scripts use project root as cwd; execute_project_python uses the selected Plan folder instead.
Interpretation: Read completed, status, mutation_state and the returned result together. A first response includes up to 20 items per array/top-level list field or 4096 top-level string characters. Feed its exact request_id to get_rhino_execution only while pending, when more pages are needed or when output/diagnostics remain unchecked; completed output containing the needed result needs no extra read. Record useful GUIDs, measurements and artifact refs for later calls.
Limits: The wrapper binds doc/scriptcontext and owns Undo/redraw plus cwd/environment restoration; it does not guarantee a script's design correctness, rollback of partial changes or a saved document. A timeout, CLI exit, print output or result_error is not rollback/completion proof: reconcile the same request instead of automatically rerunning uncertain writes. Do not switch documents or create detached/background document writers. Use validated geometry before replacing originals and synchronous batches with per-item results. Rhino embedded packages can differ from the worker venv; fixed native queries/recipes do not use this public executor. project_root is absolute and artifact_dir is relative. If writing Floor metadata, use the object's actual level labels, a typed string array for multiple levels or a string for one, preserve unrelated attributes and verify the stored value; never copy a Scene's whole level range onto every object.

Args:
    script: Synchronous Python source, C# statement body or complete command macro.
    language: python (default Python 3), python2, csharp, csharp-script or command; every mode uses official RhinoCode.
    timeout_seconds: Integer 1-600, default 60; waiting limit only. Retrieve the same request after timeout.
Returns:
    JSON execution outcome and result with a recoverable request_id; pending or failed calls preserve completion evidence.
<!-- /instruction:execute_rhino_script -->

## edit_planar_face

<!-- instruction:edit_planar_face -->
When to use: Extend or retract one planar face of an existing closed Brep when Rhino PushPull Extend preserves the intended element and connections.
Before calling: Reuse a current get_objects geometry observation of the target; request faces if the required face index is unknown. Finish group/block editing first: editor Replace/Undo/save/cancel integration is not verified, even when its working objects can be observed. Requires Bridge face_edit=1 and Rhino 8.16+.
Inputs from earlier results: Pass object_id, the chosen face index as face_index and the same observation's geometry_crc as expected_geometry_crc; do not mix observations. translation is an XYZ vector in document units with a normal component greater than document tolerance. expected_model_path is normally supplied by the bound runtime.
Interpretation: A confirmed edited=true result provides the new geometry_crc, before/after volumes and face counts under the same object GUID. Face indices can change, so observe faces again before a further face edit.
Limits: Only unlocked top-level model-space Breps with planar selected and adjacent faces are supported; extrusion conversion and block interiors are not. A prepared duplicate must remain valid, closed, manifold, correctly oriented and positive finite volume before replacement. Attributes, groups, geometry UserStrings and UserDictionary are preserved; other unverifiable custom geometry data is rejected. Native execution owns Undo, but timeout/result_error is not rollback proof. Inspect uncertain outcomes before retrying. This is geometric editing, not construction/clearance validation or a document save.

Args:
    object_id: Current unlocked top-level closed Brep GUID from an observation in the bound document.
    face_index: Zero-based planar face index from the same geometry observation as expected_geometry_crc.
    expected_geometry_crc: Geometry CRC from that observation; changed geometry rejects the edit before replacement.
    translation: Three finite XYZ numbers in document units; its face-normal component must exceed document tolerance.
    expected_model_path: Usually omitted; runtime supplies the bound saved document.
Returns:
    JSON edit outcome and replacement geometry evidence; explicit errors set MCP isError=true and retain mutation uncertainty.
<!-- /instruction:edit_planar_face -->

## edit_planar_faces

<!-- instruction:edit_planar_faces -->
When to use: Edit one already identified planar face on each of 1..32 distinct Breps in one native call and one Undo record.
Before calling: Obtain each target's current face and geometry_crc through get_objects when not already known; the single-face edit_planar_face eligibility and preservation rules apply. Requires Bridge face_edit_batch=1.
Inputs from earlier results: Each edits item supplies object_id, face_index, expected_geometry_crc and translation from its own current observation; translations use document units. Duplicate object IDs are rejected because editing can invalidate that object's face indices. The runtime normally supplies expected_model_path.
Interpretation: All replacements are prepared and checked before document changes; preparation failure leaves originals unchanged. Read each item's applied/failed/unknown/not_attempted state and applied_count, not only the outer status, to determine which objects require inspection.
Limits: A replacement failure stops further edits but completed replacements stay in the Undo record; this is not automatic rollback or an all-or-nothing transaction. Never repeat the whole batch after partial/uncertain execution. Reconcile unknown items and observe any changed face indices before another edit. It does not establish construction suitability or save the model.

Args:
    edits: 1..32 items for distinct Breps, each containing object_id, face_index, expected_geometry_crc and translation; the single-face eligibility rules apply.
    expected_model_path: Usually omitted; runtime supplies the bound saved document.
Returns:
    JSON per-item applied/failed/unknown/not_attempted states and applied_count; partial changes are not rolled back automatically.
<!-- /instruction:edit_planar_faces -->

## save_rhino_document

<!-- instruction:save_rhino_document -->
When to use: Save the whole bound document to its existing .3dm path after an authorized editing batch when persistence is requested.
Before calling: No additional query is mandatory if the bound saved document and completed edits are already known. Resolve uncertain prior mutations and finish group/block editing before saving; the tool performs its own document/capability checks.
Inputs from earlier results: None; it uses the current connection's model path and accepts no SaveAs path, command or prompt response.
Interpretation: Require saved=true and read the returned modified flag as the confirmed save result. saved=null or an unconfirmed response requires reconciliation rather than assuming either success or failure.
Limits: Saves all document changes, not just the current task. It has no SaveAs/arbitrary-path mode and rejects read-only files, mismatched documents or active/unverified editing contexts. Do not automatically repeat an uncertain save or clear native-completion protection to force a retry. Saving is not geometric/design validation.

<!-- /instruction:save_rhino_document -->

## setup_modeling

<!-- instruction:setup_modeling -->
When to use: 사전 정의된 Material과 Layer를 현재 Rhino 문서에 등록합니다.
Before calling: Supply the required overwrite boolean for both Materials and Layers. false preserves existing values, creates missing entries and reports differences; true updates predefined properties. Bridge modeling_materials=2 and modeling_setup=1 are required. Setup is not a prerequisite for every modeling action or assign_material call.
Inputs from earlier results: No IDs or preceding lookup are required when the task's setup and overwrite intent are known. There is no operation argument or Rhino Yes/No prompt. Consider existing project settings before choosing overwrite.
Interpretation: Materials are processed before Layers in one caller-owned Undo action. success with applied=true confirms that predefined properties match. incomplete with applied=false includes differences (kind, name, property, current, expected) and errors (kind, name, message). Missing entries can be created while other values remain different or fail. An error can occur after a partial mutation; this is not rollback or proof that nothing changed. Layer는 건축 유형 → 구축 시스템 → 구성 요소 역할의 위계로 구성됩니다. 시스템이 미정일 때는 유형 Layer를, 시스템이 정해진 단순 모델에는 시스템 Layer를, 부재·마감을 구체화할 때는 요소 역할 Layer를 사용합니다. 시스템과 요소 Layer에는 각각 기본 Material과 표시·출력 색이 설정됩니다. These levels express design resolution; setup does not move objects or change their ByLayer assignments.
Limits: Setup does not move objects, change their ByLayer settings, attach object metadata or enable construction detail. Layer defaults use each system's first render_material_ids, galvanized steel for connection/reinforcement/decking and birch plywood for Wood subfloor/sheathing; containers are gray. Only prescribed properties are reconciled. Unrelated properties and objects are preserved. API confirmation is not visual review or a saved 3DM. Inspect errors or mutation_state=unknown before retrying.

Args:
    overwrite: Required boolean for both Materials and Layers. False preserves existing values, creates missing entries and reports differences; true updates predefined properties.
Returns:
    JSON applied status with differences/errors when incomplete; partial changes and unknown mutation state require inspection before retrying.
<!-- /instruction:setup_modeling -->

## list_materials

<!-- instruction:list_materials -->
When to use: Find a curated PBR material or inspect its properties when the material needed for assignment or export is not already known.
Before calling: No other tool or Rhino connection is required. Reuse a known valid material_id rather than listing the library for every assignment.
Inputs from earlier results: Optional category/query narrow the known material requirement. Set include_ids=true to obtain materials[].material_id for assign_material or get_blender_helper_script; request display, physical, metadata, source, paths, audit or all through field_groups only as needed.
Interpretation: The default summary returns material names/categories; display adds PBR channels and ue_material_slot for cross-application remapping. include_ids independently controls handles and audit adds timestamps. Use the selected material_id unchanged in the next call.
Limits: This reads the library without changing Rhino; it does not prove materials are installed/applied or assign object layers. setup_modeling registers Materials and construction Layers together. Supplied target IDs are not repeated and paths require the corresponding fields.

Args:
    category: Optional library category filter; empty includes all categories.
    query: Free-text search terms; empty leaves the text filter unset.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    field_groups: Optional detail groups: display, physical, metadata, source, paths, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
<!-- /instruction:list_materials -->

## assign_material

<!-- instruction:assign_material -->
When to use: Apply a chosen curated PBR material or explicitly requested metadata to identified Rhino objects without changing their layers.
Before calling: Reuse known valid object GUIDs and material_id; otherwise obtain them from get_objects and list_materials(include_ids=true). Only look up get_construction_guidance(include_ids=true) when a requested construction reference is not already known. Requires Bridge modeling_materials=2; no bulk setup call is required.
Inputs from earlier results: Pass observed GUIDs as guids and the selected materials[].material_id as material_id. An explicitly requested construction source uses its system_id in construction_reference={"kind":"construction_system","id":...}; legacy construction_system accepts that same ID and must agree with an explicit reference. structural_role, floor and construction_detail are supplied labels, not inferred identities. A source name fills a missing detail label.
Interpretation: Compare applied_count with requested_count and inspect applied_guids, optional changed_guids/changed_count, render_material_applied, metadata_attached and warnings. A material atypical for a declared system warns but still applies. Reuse confirmed applied GUIDs for export or follow-up observation.
Limits: apply_render_material controls native PBR assignment, preserving object layers. attach_metadata defaults false; enable it only for an explicit metadata request. It writes supplied floor/detail/reference/role data and material identity only when appropriate; unspecified metadata and provenance survive. Metadata-only calls preserve native material identity; even these require a known material_id. Block-instance materials affect definition geometry set by-parent, while requested metadata belongs to the instance. No dimensions, saved-document proof or construction verification are produced. An uncertain result/result_error must be inspected before retrying.

Args:
    guids: Current Rhino object GUIDs to assign; reuse an observation or creation result.
    material_id: Canonical library material ID from list_materials(include_ids=true).
    apply_render_material: Apply the canonical render material to the specified objects when true.
    attach_metadata: Attach Almond material/construction metadata when true; false applies only the requested render material.
    structural_role: Optional structural role metadata, used with attach_metadata.
    construction_system: Optional construction system label, used with attach_metadata.
    floor: Optional floor label metadata, used with attach_metadata.
    construction_detail: Optional construction detail note, used with attach_metadata.
    construction_reference: Optional source-reference object, used with attach_metadata; omission adds no reference.
<!-- /instruction:assign_material -->

## response-750

<!-- instruction:response-750 -->
Setup ran but its result is unavailable. Inspect Rhino before retrying.
<!-- /instruction:response-750 -->

## response-754

<!-- instruction:response-754 -->
Material assignment ran but its result could not be returned. Inspect Rhino before retrying.
<!-- /instruction:response-754 -->

## response-755

<!-- instruction:response-755 -->
Material assignment returned no valid applied-object result. Inspect Rhino before retrying.
<!-- /instruction:response-755 -->
