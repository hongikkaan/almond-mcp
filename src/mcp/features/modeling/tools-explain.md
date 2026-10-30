# tools.py explain

## get_modeling_policy

<!-- instruction:get_modeling_policy -->
Return JSON-defined object/group metadata keys and material-layer naming rules.

Names are free. Do not automatically write Almond management UserStrings on objects.
Existing keys describe compatibility data, not a checklist to fill. Preserve existing
user metadata and asset provenance; ordinary naming, layer and material properties
are independent of management UserStrings.
<!-- /instruction:get_modeling_policy -->

## execute_rhino_script

<!-- instruction:execute_rhino_script -->
Execute source or a complete macro in the bound Rhino through official RhinoCode.

Python 3 is the default. Read get_modeling_guide(tool="execute_rhino_script") for
this contract and the bundled rhino3d-scripts skill, API maps and loading guidance.
No separate skill installation is required. The wrapper binds doc/scriptcontext,
owns Undo and redraw, and restores cwd/environment even after an exception.
Use document tolerance, explicit object IDs and validated geometry before replacing
or deleting originals. Batch loops belong in synchronous source with per-item results.

python/python2 assign a JSON value to result. csharp/csharp-script are C# statement
bodies with doc and result_json, not the former class/Run format. command accepts
one fully specified macro without adding !, Pause or dialogs. All modes require
StartScriptServer in the bound Rhino; there is no legacy Bridge executor fallback.
Fixed queries and audited internal recipes keep their existing native paths.

project_root is absolute; artifact_dir is relative to it. General scripts run with
project root as cwd. Use execute_project_python for the selected Plan folder as cwd.
Do not assume worker-venv packages exist in Rhino's embedded Python. Return only
measurements needed for the decision, collecting related work in one script.

A waiting response includes request_id. Use get_rhino_execution to retrieve that
same execution, page its results or read captured stdout. CLI exit, print output
and a timeout are not completion evidence. A completed exception may have partial
changes; result_error does not roll them back. Never automatically retry uncertain
work, open a different document or schedule detached document edits.

Args:
    script: Synchronous Python source, C# statement body or complete command macro.
    language: python (default Python 3), python2, csharp, csharp-script or command; every mode uses official RhinoCode.
    timeout_seconds: Integer 1-600, default 60; waiting limit only. Retrieve the same request after timeout.
Returns:
    JSON execution outcome and result with a recoverable request_id; pending or failed calls preserve completion evidence.
<!-- /instruction:execute_rhino_script -->

## save_rhino_document

<!-- instruction:save_rhino_document -->
Save the current connection's existing .3dm file without a command, prompt or Enter.
Use after an authorized editing batch when the file should be saved. It saves the
whole bound document to its existing path; there is no SaveAs or arbitrary path input.
Active or uncertain group/block editing, a mismatched document and a read-only file
are rejected before writing. A confirmed response returns saved=true and the actual
modified flag. An unconfirmed response is not failure proof: never automatically
repeat the save or clear the connection's native-completion protection.
<!-- /instruction:save_rhino_document -->

## setup_modeling

<!-- instruction:setup_modeling -->
Register materials or create construction layers in the current Rhino document.

operation="materials" registers the curated PBR library using readable names.
For matching names overwrite=true updates PBR channels, false preserves them;
omit it to choose Yes/No once in Rhino. Cancel performs no changes.

operation="layers" creates/reuses M/category/system.name/element.role paths,
assigns materials and matching display/print colors. A system uses its first
render_material_ids recipe; connection/reinforcement/decking use galvanized
steel, and Wood subfloor/sheathing use birch plywood. These are setup defaults,
not a role mapping supplied by the construction manifest. Container layers
are gray. Existing matching materials are reused; overwrite is only for
operation="materials". No object is moved or stamped with metadata.

Requires Bridge modeling_materials=2. The whole operation is one Undo step.
Success reports API execution, not visual review or a saved 3DM. An uncertain
result must be inspected before any retry.
<!-- /instruction:setup_modeling -->

## list_materials

<!-- instruction:list_materials -->
Lists the curated PBR material library used by assign_material without changing Rhino.

Each entry carries metallic/roughness PBR channels, an Unreal material
slot name (ue_material_slot) for deterministic remapping after import,
and tags. Materials do not define object layers. setup_modeling creates
M/category/system/role layers from the construction library separately.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds display, physical, metadata, source, paths, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_materials -->

## assign_material

<!-- instruction:assign_material -->
Assigns a curated PBR material and its canonical M:: layer to explicit Rhino objects.
The compiled helper creates only the chosen material/layer on demand and reuses
existing entries. Returns applied GUIDs without adding automatic dimensions.

For structural members, also declare what the object IS in construction
terms: structural_role (e.g. "joist", "girder", "stud", "truss_chord")
and construction_system (a system_id from get_construction_guidance).
An explicit structural_role retains its legacy user-text key. A system is
stored as the typed construction_reference described below. If the chosen material_id is
not a typical finish for the declared system, the response carries a
warning (it still applies).

floor is a user-supplied level label. construction_detail is a readable label;
construction_reference optionally identifies a known source as
{"kind": "construction_system", "id": "<system_id>"}. These source records
are preliminary system guidance, not verified construction details. The old
construction_system argument is accepted and produces the same typed reference.
A source name supplies the detail label when no explicit label is given.

Two effects, independently switchable:
- apply_render_material: creates/reuses a physically-based Rhino
  material using the library name and assigns it per object, so GLB
  export (publish_to_chestnut) and Datasmith carry real PBR channels. The
  object's layer is always preserved. If false, no native material is
  changed or created.
- attach_metadata: defaults to false; ordinary material application writes no
  object management UserStrings. Set true only for an explicit request to attach
  metadata. It writes only material_id when a native material is
  applied, plus supplied floor/detail/reference metadata. PBR channels
  remain on the native material. A metadata-only call preserves the
  current material identity and writes only the supplied metadata.

Unspecified metadata and asset provenance are preserved. Requires a Bridge
with modeling_materials=2; older Bridges are rejected before any mutation.
Works on breps, meshes, and block instances (an instance's material
applies to definition geometry set to 'by parent'; the metadata is
attached to the instance itself only when explicitly enabled). Query list_materials
when the required material ID is not already known.
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
