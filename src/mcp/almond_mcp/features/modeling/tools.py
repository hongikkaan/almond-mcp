"""Modeling policy, script execution, setup and material tools."""
import json
import socket
import uuid

from almond_mcp.features.modeling import modeling_policy, modeling_setup


def register(mcp, context):
    """Register modeling tools against the current server execution context."""
    _material_script = modeling_setup.material_script

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    def get_modeling_policy() -> dict:
        """Return JSON-defined object/group metadata keys and material-layer naming rules.

    Names are free. New modeling normally needs only component_id (registration),
    optional floor and construction_detail, plus material identity and a typed source
    reference when used. Internal compatibility keys are not a checklist to fill.
    """
        return {"status": "success", "policy": modeling_policy.POLICY}


    @mcp.tool()
    def execute_rhino_script(script: str) -> str:
        """
    Sends a C# RhinoCommon script to the Rhino 3D Bridge for compilation and execution.
    The script is compiled by Roslyn inside Rhino and executed natively as JIT-compiled C#.

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
    This executor can modify layers and create dimensions even for an inspection script;
    use get_rhino_context for a fixed read-only document snapshot. Execution success does
    not validate the geometry's design intent. Check meaningful invariants before Replace/Delete.

    Available namespaces (auto-imported if not present):
        System, System.Collections.Generic, System.Linq,
        Rhino, Rhino.Geometry, Rhino.DocObjects

    Args:
        script: C# source code containing a class with public static Run(RhinoDoc doc).
    Returns:
        JSON with status, declared guids, error_trace and optional result or result_error.
    """
        payload = json.dumps({"type": "execute", "script": script}).encode('utf-8')

        try:
            return context._send_and_receive(payload)
        except socket.timeout:
            return json.dumps({"status": "error", "message": "Rhino bridge timed out (>60s)."})
        except ConnectionRefusedError:
            return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"})
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Bridge error: {e}"})


    @mcp.tool()
    def setup_modeling(operation: str, overwrite: bool | None = None) -> str:
        """Register materials or create construction layers in the current Rhino document.

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
    """
        if operation not in ("materials", "layers"):
            return json.dumps({"status": "error", "message": "operation must be materials or layers"})
        if overwrite is not None and type(overwrite) is not bool:
            return json.dumps({"status": "error", "message": "overwrite must be true, false or null"})
        if operation == "layers" and overwrite is not None:
            return json.dumps({"status": "error", "message": "overwrite applies only to materials"})
        try:
            code = modeling_setup.setup_script(operation, context.material_library, context.construction_library, overwrite)
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            return json.dumps({"status": "error", "mutation_state": "not_started", "message": str(exc)})
        result = modeling_setup.dispatch(code, context._send_and_receive, timeout=600.0)
        if result.get("status") == "success" and (result.get("result_error") or not isinstance(result.get("result"), dict)):
            result.update(mutation_state="unknown", message="Setup ran but its result is unavailable. Inspect Rhino before retrying.")
        return json.dumps(result)


    @mcp.tool()
    def list_materials(category: str = "", query: str = "") -> str:
        """
    Lists the curated PBR material library used by assign_material without changing Rhino.

    Each entry carries metallic/roughness PBR channels, an Unreal material
    slot name (ue_material_slot) for deterministic remapping after import,
    and tags. Materials do not define object layers. setup_modeling creates
    M/category/system/role layers from the construction library separately.
    """
        materials = context.material_library.list(category=category, query=query)
        return json.dumps({
            "total": len(materials),
            "materials": materials,
            "library_dir": str(context.material_library.directory),
        })


    @mcp.tool()
    def assign_material(
        guids: list[str],
        material_id: str,
        apply_render_material: bool = True,
        attach_metadata: bool = True,
        structural_role: str = "",
        construction_system: str = "",
        floor: str = "",
        construction_detail: str = "",
        construction_reference: dict | None = None,
    ) -> str:
        """
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
    - attach_metadata: writes only material_id when a native material is
      applied, plus supplied floor/detail/reference metadata. PBR channels
      remain on the native material. A metadata-only call preserves the
      current material identity and writes only the supplied metadata.

    Unspecified metadata and asset provenance are preserved. Requires a Bridge
    with modeling_materials=2; older Bridges are rejected before any mutation.
    Works on breps, meshes, and block instances (an instance's material
    applies to definition geometry set to 'by parent'; the metadata is
    always attached to the instance itself). Call list_materials first to
    discover material_ids.
    """
        material = context.material_library.get(material_id)
        if not material:
            known = ", ".join(sorted(context.material_library.materials)) or "none loaded"
            return json.dumps({
                "status": "error",
                "message": f"Unknown material_id: {material_id}. Known: {known}",
            })
        guid_list = []
        for value in guids:
            try:
                guid = str(uuid.UUID(str(value)))
                if guid not in guid_list:
                    guid_list.append(guid)
            except ValueError:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid Rhino object GUID: {value}",
                })
        if not guid_list:
            return json.dumps({"status": "error", "message": "guids must not be empty."})

        warnings = []
        extra_strings: dict[str, str] = {}
        for name, value in (("floor", floor), ("construction_detail", construction_detail),
                            ("structural_role", structural_role), ("construction_system", construction_system)):
            if not isinstance(value, str):
                return json.dumps({"status": "error", "message": f"{name} must be a string."})
        if construction_reference is not None:
            if (not isinstance(construction_reference, dict)
                    or set(construction_reference) != {"kind", "id"}
                    or construction_reference.get("kind") != "construction_system"
                    or not isinstance(construction_reference.get("id"), str)
                    or not construction_reference["id"].strip()):
                return json.dumps({"status": "error", "message": "construction_reference requires kind=construction_system and a known id."})
            if construction_system and construction_system != construction_reference["id"]:
                return json.dumps({"status": "error", "message": "construction_system and construction_reference identify different sources."})
            construction_system = construction_reference["id"]
        if structural_role:
            extra_strings[modeling_policy.key("structural_role")] = structural_role
        if construction_system:
            system = context.construction_library.get(construction_system)
            if system is None:
                known = ", ".join(sorted(context.construction_library.systems)) or "none loaded"
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown construction_system: {construction_system}. "
                               f"Known: {known}",
                })
            construction_reference = {"kind": "construction_system", "id": construction_system}
            construction_detail = construction_detail or system["name"]
            extra_strings[modeling_policy.key("construction_reference")] = json.dumps(construction_reference, ensure_ascii=True, separators=(",", ":"))
            typical = system.get("render_material_ids", [])
            if typical and material_id not in typical:
                warnings.append(
                    f"Material '{material_id}' is not a typical finish for "
                    f"{construction_system} (typical: {', '.join(typical)}). "
                    f"Applied anyway.")

        if floor:
            extra_strings[modeling_policy.key("floor")] = floor
        if construction_detail:
            extra_strings[modeling_policy.key("construction_detail")] = construction_detail
        script = context._material_script(material, guid_list, apply_render_material,
                                  attach_metadata, extra_strings)
        response = modeling_setup.dispatch(script, context._send_and_receive)
        if response.get("status") != "success":
            return json.dumps(response)
        if response.get("result_error"):
            return json.dumps({**response, "material_id": material_id,
                               "message": "Material assignment ran but its result could not be returned. Inspect Rhino before retrying."})
        native = response.get("result")
        applied = native.get("applied_guids") if isinstance(native, dict) else None
        if (not isinstance(applied, list) or any(not isinstance(g, str) or g not in guid_list for g in applied)
                or len(applied) != len(set(applied)) or native.get("material_id") != material_id):
            return json.dumps({"status": "error", "error_code": "material_result_unavailable", "mutation_state": "unknown",
                               "message": "Material assignment returned no valid applied-object result. Inspect Rhino before retrying."})
        result = {
            "status": "success",
            "material_id": material_id,
            "rhino_material_name": material["name"],
            "ue_material_slot": material["ue_material_slot"],
            "applied_count": len(applied),
            "requested_count": len(guid_list),
            "applied_guids": applied,
            "metadata_attached": native.get("metadata_attached", attach_metadata and (apply_render_material or bool(extra_strings))),
            "material_metadata_attached": attach_metadata and apply_render_material,
            "render_material_applied": apply_render_material,
            "layer_path": native.get("layer_path"),
        }
        changed = native.get("changed_guids")
        if (isinstance(changed, list) and all(isinstance(g, str) and g in applied for g in changed)
                and len(changed) == len(set(changed))):
            result["changed_guids"] = changed
            result["changed_count"] = len(changed)
        if structural_role:
            result["structural_role"] = structural_role
        if construction_system:
            result["construction_system"] = construction_system
        if floor:
            result["floor"] = floor
        if construction_detail:
            result["construction_detail"] = construction_detail
        if construction_reference:
            result["construction_reference"] = construction_reference
        if warnings:
            result["warnings"] = warnings
        return json.dumps(result)


    return {
        "get_modeling_policy": get_modeling_policy,
        "execute_rhino_script": execute_rhino_script,
        "setup_modeling": setup_modeling,
        "list_materials": list_materials,
        "assign_material": assign_material,
        "_material_script": _material_script,
    }
