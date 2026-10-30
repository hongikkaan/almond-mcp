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
Execute code or a command in the bound Rhino, using an explicit language and tracked completion.

For new general queries and scripts use language="python" with the official RhinoCode
runtime. The synchronous Python body receives doc, result and artifact_dir; assign a
JSON value to result. Return only the information needed for the decision, grouping
related measurements in one call. Fixed probes remain useful for their guaranteed
nonmutating observations; they are not a prerequisite for every custom query.

Official modes are python, python2, csharp-script and command. They require the bound
runtime's current RhinoCode capability and StartScriptServer in that Rhino. Unverified
language modes are rejected before dispatch. csharp-script is a C# statement body with
doc and result_json, not a Run class; use explicit JSON result text. command runs a fully
specified Rhino macro only in a verified script-runner context, without adding ! or prompts.

Completion and result display are independent. A waiting response includes request_id;
get_rhino_execution reads that same execution's state/result, selects fields or pages,
and recovers late completion without re-executing code. stdout is a log, not proof of
execution. A completed exception may have partial changes. Do not automatically retry,
open another document, schedule background document edits, or undo unrelated work.

The default language="csharp" preserves the existing Bridge/Roslyn contract below.

The script MUST define a class with a public static Run(RhinoDoc doc) method.
The existing modelling form returns a List<Guid>:

    public class Script
    {
        public static List<Guid> Run(RhinoDoc doc)
        {
            var guids = new List<Guid>();
            // Use doc.Objects.AddSphere(), doc.Objects.AddBrep(), etc.
            // Append each GUID: guids.Add(guid);
            return guids;
        }
    }

For numeric or inspection results, Run may instead return a JSON-safe object, for example:

    public static object Run(RhinoDoc doc)
    {
        return new { object_count = doc.Objects.Count };
    }

Supported results are finite scalars, anonymous objects, arrays/lists and string-keyed
dictionaries of supported values, limited to 16 container levels and 64 KiB of compact
UTF-8 JSON. Void/null and List<Guid> retain their existing behaviour. A result_error
means the result could not be represented; already executed model changes are not
rolled back for that reason. Inspect the current state and do not automatically retry.
The guids field contains the script's declared IDs, not a complete change history.
This legacy executor starts an Undo record and List<Guid> results can create dimensions;
use get_rhino_context for a fixed read-only document snapshot. Execution success does
not validate the geometry's design intent. Check meaningful invariants before Replace/Delete.

Available namespaces (auto-imported if not present):
    System, System.Collections.Generic, System.Linq,
    Rhino, Rhino.Geometry, Rhino.DocObjects

Args:
    script: Source for the chosen language, or a complete command macro. Default C# requires a class with public static Run(RhinoDoc doc).
    language: csharp (legacy default), python, python2, csharp-script or command. Official modes require a verified bound runtime.
    timeout_seconds: Integer from 1 to 600, default 60. In official modes this limits waiting, not Rhino execution; use get_rhino_execution after a waiting response.
Returns:
    JSON execution status and result; official modes include a recoverable request_id. Legacy C# retains guids, error_trace and optional result/result_error.
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
