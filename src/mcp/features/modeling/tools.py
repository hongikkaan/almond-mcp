"""Modeling policy, script execution, setup and material tools."""
from almond_mcp.tool_response import error_payload, mcp_error_result
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.modeling.output import GROUPS, project
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.instruction_text import tool_instruction, read_instruction
from almond_mcp.managed_paths import bound_model_path
from pydantic import StrictBool, StrictFloat, StrictInt
import json
import uuid
from typing import Literal

from almond_mcp.features.modeling import face_edit, modeling_policy, modeling_setup, plan_section


def register(mcp, context):
    """Register modeling tools against the current server execution context."""
    _material_script = modeling_setup.material_script



    @mcp.tool(name='plan_section', output_schema=public_output_schema('plan_section', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'plan_section')
    def plan_section_tool(operation: Literal["Create", "Update"], clipping_ids: list[str],
                          points: dict[str, list[StrictFloat | StrictInt]] | None = None,
                          hatch: StrictBool = True, elevation: StrictBool = True, small_details: StrictBool = True,
                          near_width: StrictFloat | StrictInt = 0.09, far_width: StrictFloat | StrictInt = 0.04,
                          near_dark: StrictFloat | StrictInt = 80.0, far_dark: StrictFloat | StrictInt = 45.0,
                          expected_model_path: str = "") -> str:
        try:
            payload = plan_section.request(operation, clipping_ids, points, hatch, elevation, small_details,
                                           near_width, far_width, near_dark, far_dark,
                                           bound_model_path(expected_model_path))
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(plan_section.dispatch(payload, context._send_and_receive), ensure_ascii=False)

    @mcp.tool(annotations={'readOnlyHint': True, 'destructiveHint': False}, output_schema=public_output_schema('get_plan_section_result', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'get_plan_section_result')
    def get_plan_section_result(result_id: str, offset: StrictInt = 0, expected_model_path: str = "") -> str:
        try:
            if len(result_id) != 32 or any(c not in '0123456789abcdef' for c in result_id) or type(offset) is not int or not 0 <= offset <= 2147483647:
                raise ValueError("Supply a receipt ID and nonnegative offset from the preceding page.")
            payload = dict(type="get_plan_section_result", result_id=result_id, offset=offset,
                           expected_model_path=bound_model_path(expected_model_path))
            return context._send_and_receive(json.dumps(payload).encode('utf-8'))
        except Exception as exc:
            return json.dumps(error_payload(str(exc), error_code="plan_section_result_read_failed"))


    @mcp.tool(output_schema=public_output_schema('execute_rhino_script', wrapped=True))
    @tool_instruction(__file__, 'execute_rhino_script')
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


    @mcp.tool(output_schema=public_output_schema('edit_planar_face', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'edit_planar_face')
    def edit_planar_face(object_id: str, face_index: StrictInt, expected_geometry_crc: StrictInt,
                         translation: list[StrictFloat | StrictInt], expected_model_path: str = "") -> str:
        try:
            payload = face_edit.request(object_id, face_index, expected_geometry_crc, translation,
                                        bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive), ensure_ascii=False)


    @mcp.tool(output_schema=public_output_schema('edit_planar_faces', wrapped=True))
    @mcp_error_result
    @tool_instruction(__file__, 'edit_planar_faces')
    def edit_planar_faces(edits: list[dict], expected_model_path: str = "") -> str:
        try:
            payload = face_edit.batch_request(edits, bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive, batch=True), ensure_ascii=False)


    @mcp.tool(annotations={'destructiveHint': False}, output_schema=public_output_schema('save_rhino_document', wrapped=True))
    @tool_instruction(__file__, 'save_rhino_document')
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


    @mcp.tool(output_schema=public_output_schema('setup_modeling', wrapped=True))
    @tool_instruction(__file__, 'setup_modeling')
    def setup_modeling(overwrite: StrictBool) -> str:
        try:
            code = modeling_setup.setup_script(context.material_library, context.construction_library, overwrite)
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            return json.dumps({"status": "error", "mutation_state": "not_started", "message": str(exc)})
        result = modeling_setup.dispatch(code, context._send_and_receive, timeout=600.0, require_setup=True)
        return json.dumps(modeling_setup.setup_result(result), ensure_ascii=False)


    @mcp.tool(output_schema=public_output_schema('list_materials', wrapped=True))
    @tool_instruction(__file__, 'list_materials')
    @query_output
    def list_materials(category: str = "", query: str = "", include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        materials = context.material_library.list(category=category, query=query)
        return json.dumps(project({
            "total": len(materials),
            "materials": materials,
            "library_dir": str(context.material_library.directory),
        }, field_groups))


    @mcp.tool(output_schema=public_output_schema('assign_material', wrapped=True))
    @tool_instruction(__file__, 'assign_material')
    def assign_material(
        guids: list[str],
        material_id: str,
        apply_render_material: bool = True,
        attach_metadata: bool = False,
        structural_role: str = "",
        construction_system: str = "",
        floor: str = "",
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
        extra_strings: dict[str, str] = {}
        for name, value in (("floor", floor), ("construction_detail", construction_detail),
                            ("structural_role", structural_role), ("construction_system", construction_system)):
            if not isinstance(value, str):
                return json.dumps(error_payload(f"{name} must be a string."))
        if construction_reference is not None:
            if (not isinstance(construction_reference, dict)
                    or set(construction_reference) != {"kind", "id"}
                    or construction_reference.get("kind") != "construction_system"
                    or not isinstance(construction_reference.get("id"), str)
                    or not construction_reference["id"].strip()):
                return json.dumps(error_payload("construction_reference requires kind=construction_system and a known id."))
            if construction_system and construction_system != construction_reference["id"]:
                return json.dumps(error_payload("construction_system and construction_reference identify different sources."))
            construction_system = construction_reference["id"]
        if structural_role:
            extra_strings[modeling_policy.key("structural_role")] = structural_role
        if construction_system:
            system = context.construction_library.get(construction_system)
            if system is None:
                known = ", ".join(sorted(context.construction_library.systems)) or "none loaded"
                return json.dumps(error_payload(f"Unknown construction_system: {construction_system}. "
                               f"Known: {known}"))
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
                               "message": read_instruction(__file__, 'response-754')})
        native = response.get("result")
        applied = native.get("applied_guids") if isinstance(native, dict) else None
        if (not isinstance(applied, list) or any(not isinstance(g, str) or g not in guid_list for g in applied)
                or len(applied) != len(set(applied)) or native.get("material_id") != material_id):
            return json.dumps({"status": "error", "error_code": "material_result_unavailable", "mutation_state": "unknown",
                               "message": read_instruction(__file__, 'response-755')})
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
        "plan_section": plan_section_tool,
        "get_plan_section_result": get_plan_section_result,
        "execute_rhino_script": execute_rhino_script,
        "edit_planar_face": edit_planar_face,
        "edit_planar_faces": edit_planar_faces,
        "save_rhino_document": save_rhino_document,
        "setup_modeling": setup_modeling,
        "list_materials": list_materials,
        "assign_material": assign_material,
        "_material_script": _material_script,
    }
