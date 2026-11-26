"""Modeling policy, script execution and material tools."""
from almond_mcp.tool_response import error_payload, script_result
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.modeling.output import GROUPS, project
from almond_mcp.tool_declarations import public_tool
from almond_mcp.managed_paths import bound_model_path
from pydantic import StrictBool, StrictFloat, StrictInt
import json
import uuid
from typing import Literal

from almond_mcp.features.modeling import face_edit, modeling_policy, modeling_setup
from almond_mcp.features.modeling import plan_section as section_operations


def register(mcp, context):
    """Register modeling tools against the current server execution context."""

    @public_tool(mcp, errors=True)
    def plan_section(operation: Literal["Create", "Update", "Move"], clipping_ids: list[str],
                          points: dict[str, list[StrictFloat | StrictInt]] | None = None,
                          hatch: StrictBool = True, small_details: StrictBool = False,
                          near_width: StrictFloat | StrictInt = 0.09, far_width: StrictFloat | StrictInt = 0.04,
                          near_dark: StrictFloat | StrictInt = 80.0, far_dark: StrictFloat | StrictInt = 45.0,
                          include_attachments: StrictBool | None = None,
                          section_width_source: Literal["source", "output_layer"] = "source") -> str:
        try:
            payload = section_operations.request(operation, clipping_ids, points, hatch, small_details,
                                                 near_width, far_width, near_dark, far_dark,
                                                 bound_model_path(), include_attachments=include_attachments,
                                                 section_width_source=section_width_source)
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(section_operations.dispatch(payload, context._send_and_receive), ensure_ascii=False)

    @public_tool(mcp)
    def execute_rhino_script(script: str, language: str = "python",
                             timeout_seconds: StrictInt = 60) -> str:
        if not isinstance(script, str) or not script.strip():
            return json.dumps(error_payload("script must be nonempty source or a command.",
                                            error_code="invalid_arguments"))
        if not isinstance(language, str) or language not in {"csharp", "python", "python2", "csharp-script", "command"}:
            return json.dumps(error_payload(
                "language must be csharp, python, python2, csharp-script or command.",
                error_code="invalid_arguments"))
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            return json.dumps(error_payload("timeout_seconds must be an integer from 1 to 600.",
                                            error_code="invalid_arguments"))
        execute = getattr(context, "_execute_rhinocode", None)
        if execute is None:
            return json.dumps({**error_payload(
                "RhinoCode execution requires a bound Almond runtime and StartScriptServer in its Rhino.",
                error_code="rhinocode_unavailable"), "mutation_state": "not_started"})
        # All public source runs in ScriptEditor. Private native recipes use
        # their own sender and are not callers of this public tool.
        return json.dumps(execute(script, "csharp-script" if language == "csharp" else language,
                                  timeout_seconds), ensure_ascii=False)


    @public_tool(mcp, errors=True)
    def edit_planar_face(object_id: str, face_index: StrictInt, expected_geometry_crc: StrictInt,
                         translation: list[StrictFloat | StrictInt], expected_model_path: str = "") -> str:
        try:
            payload = face_edit.request(object_id, face_index, expected_geometry_crc, translation,
                                        bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive), ensure_ascii=False)


    @public_tool(mcp, errors=True)
    def edit_planar_faces(edits: list[dict], expected_model_path: str = "") -> str:
        try:
            payload = face_edit.batch_request(edits, bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive, batch=True), ensure_ascii=False)


    @public_tool(mcp, annotations={'destructiveHint': False})
    def save_rhino_document() -> str:
        try:
            model_path = bound_model_path()
            snapshot = json.loads(context._send_and_receive(json.dumps({
                "type": "get_rhino_context", "sections": [], "selection_limit": 0,
            }).encode("utf-8")))
            if not isinstance(snapshot, dict) or snapshot.get("status") != "success":
                raise ValueError("Could not verify the document-save capability.")
            if snapshot.get("capabilities", {}).get("document_save") != 1:
                return json.dumps({**error_payload(
                    "This Bridge does not support noninteractive document saving.",
                    error_code="unsupported_document_save"), "saved": False})
        except Exception as exc:
            return json.dumps({**error_payload(str(exc), error_code="save_not_started"), "saved": False})
        try:
            result = json.loads(context._send_and_receive(json.dumps({
                "type": "save_rhino_document", "expected_model_path": model_path,
            }).encode("utf-8")))
            if isinstance(result, dict) and result.get("status") == "error":
                return json.dumps(result, ensure_ascii=False)
            if (not isinstance(result, dict) or result.get("status") != "success"
                    or result.get("saved") is not True or type(result.get("modified")) is not bool):
                raise ValueError("The Bridge did not return a confirmed save result.")
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({**error_payload(str(exc), error_code="save_result_unconfirmed"),
                               "saved": None, "requires_reconciliation": True})


    @public_tool(mcp)
    @query_output
    def list_materials(category: str = "", query: str = "", field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        materials = context.material_library.list(category=category, query=query)
        return json.dumps(project({
            "total": len(materials),
            "materials": materials,
            "library_dir": str(context.material_library.directory),
        }, field_groups))


    @public_tool(mcp)
    def assign_material(
        guids: list[str],
        material_id: str,
        floor: str,
        structural_role: str,
        apply_render_material: bool = True,
        attach_metadata: bool = False,
        construction_detail: str = "",
        construction_reference: dict | None = None,
    ) -> str:
        material = context.material_library.get(material_id)
        if not material:
            known = ", ".join(sorted(context.material_library.materials)) or "none loaded"
            return json.dumps(error_payload(f"Unknown material_id: {material_id}. Known: {known}"))
        guid_list = []
        for value in guids:
            try:
                guid = str(uuid.UUID(str(value)))
                if guid not in guid_list:
                    guid_list.append(guid)
            except ValueError:
                return json.dumps(error_payload(f"Invalid Rhino object GUID: {value}"))
        if not guid_list:
            return json.dumps(error_payload("guids must not be empty."))

        warnings = []
        for name, value in (("floor", floor), ("construction_detail", construction_detail),
                            ("structural_role", structural_role)):
            if not isinstance(value, str):
                return json.dumps(error_payload(f"{name} must be a string."))
        if not floor.strip() or not structural_role.strip():
            return json.dumps(error_payload("floor and structural_role must both be nonempty."))
        if construction_reference is not None:
            if (not isinstance(construction_reference, dict)
                    or set(construction_reference) != {"kind", "id"}
                    or construction_reference.get("kind") != "construction_system"
                    or not isinstance(construction_reference.get("id"), str)
                    or not construction_reference["id"].strip()):
                return json.dumps(error_payload("construction_reference requires kind=construction_system and a known id."))
            construction_system = construction_reference["id"]
            system = context.construction_library.get(construction_system)
            if system is None:
                known = ", ".join(sorted(context.construction_library.systems)) or "none loaded"
                return json.dumps(error_payload(f"Unknown construction_system: {construction_system}. "
                               f"Known: {known}"))
            typical = system.get("render_material_ids", [])
            if typical and material_id not in typical:
                warnings.append(
                    f"Material '{material_id}' is not a typical finish for "
                    f"{construction_system} (typical: {', '.join(typical)}).")

        extra_strings = {"Floor": floor, "structural_role": structural_role}
        if construction_detail.strip():
            extra_strings["construction_detail"] = construction_detail
        if construction_reference:
            extra_strings["construction_reference"] = json.dumps(construction_reference, ensure_ascii=True, separators=(",", ":"))
        try:
            script = modeling_setup.material_script(material, guid_list, apply_render_material,
                                                   attach_metadata, extra_strings)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc)))
        response = modeling_setup.dispatch(script, context._send_and_receive,
                                           require_material_layer=apply_render_material)
        if response.get("status") != "success":
            return json.dumps(response)
        if response.get("result_error"):
            return json.dumps({**script_result(response), "material_id": material_id,
                               "message": 'Material assignment ran but its result could not be returned. Inspect Rhino before retrying.'})
        native = response.get("result")
        applied = native.get("applied_guids") if isinstance(native, dict) else None
        if (not isinstance(applied, list) or any(not isinstance(g, str) or g not in guid_list for g in applied)
                or len(applied) != len(set(applied)) or native.get("material_id") != material_id):
            return json.dumps({"status": "error", "error_code": "material_result_unavailable", "mutation_state": "unknown",
                               "message": 'Material assignment returned no valid applied-object result. Inspect Rhino before retrying.'})
        if native.get("metadata_attached") is not bool(applied):
            return json.dumps({"status": "error", "error_code": "material_metadata_unconfirmed", "mutation_state": "unknown",
                               "message": "Could not confirm assignment metadata. Inspect the target objects before retrying."})
        layer_path, layer_action, layer_changed = None, "not_applied", []
        if apply_render_material:
            layer_path = native.get("layer_path")
            layer_action = native.get("layer_action")
            layer_changed = native.get("layer_changed_guids")
            expected_path = modeling_policy.material_layer(material)["path"]
            changed = native.get("changed_guids")
            actual = layer_path.casefold().split("::") if isinstance(layer_path, str) else []
            expected = expected_path.casefold().split("::")
            if (len(actual) != 3 or not actual[-1] or actual[:2] != expected[:2]
                    or layer_action not in ("created", "reused")
                    or (layer_action == "created" and actual != expected)
                    or native.get("render_material_applied") is not True
                    or not isinstance(layer_changed, list) or not isinstance(changed, list)
                    or any(not isinstance(g, str) or g not in applied or g not in changed for g in layer_changed)
                    or len(layer_changed) != len(set(layer_changed))):
                return json.dumps({"status": "error", "error_code": "material_layer_result_unavailable",
                                   "mutation_state": "unknown",
                                   "message": "Could not confirm material layer assignment. Inspect Rhino before retrying."})
        status = "success"
        if not applied:
            status = "executed"
        elif len(applied) < len(guid_list):
            status = "partial"
        result = {
            "status": status,
            "material_id": material_id,
            "rhino_material_name": material["name"],
            "ue_material_slot": material["ue_material_slot"],
            "applied_count": len(applied),
            "requested_count": len(guid_list),
            "applied_guids": applied,
            "metadata_attached": bool(applied),
            "material_metadata_attached": bool(applied) and attach_metadata and apply_render_material,
            "render_material_applied": apply_render_material,
            "layer_path": layer_path,
            "layer_action": layer_action,
            "layer_changed_guids": layer_changed,
        }
        changed = native.get("changed_guids")
        if (isinstance(changed, list) and all(isinstance(g, str) and g in applied for g in changed)
                and len(changed) == len(set(changed))):
            result["changed_guids"] = changed
            result["changed_count"] = len(changed)
        if applied:
            result.update(floor=floor, structural_role=structural_role)
            if "construction_detail" in extra_strings:
                result["construction_detail"] = construction_detail
            if construction_reference:
                result["construction_reference"] = construction_reference
        if warnings:
            result["warnings"] = warnings
        return json.dumps(result)


    return {
        "plan_section": plan_section,
        "execute_rhino_script": execute_rhino_script,
        "edit_planar_face": edit_planar_face,
        "edit_planar_faces": edit_planar_faces,
        "save_rhino_document": save_rhino_document,
        "list_materials": list_materials,
        "assign_material": assign_material,
    }
