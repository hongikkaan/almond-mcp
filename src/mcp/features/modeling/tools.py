"""Modeling policy, script execution, setup and material tools."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.modeling.output import GROUPS, project
from almond_mcp.instruction_text import tool_instruction, read_instruction
from almond_mcp.managed_paths import bound_model_path
from pydantic import StrictBool, StrictInt
import json
import uuid

from almond_mcp.features.modeling import modeling_policy, modeling_setup


def register(mcp, context):
    """Register modeling tools against the current server execution context."""
    _material_script = modeling_setup.material_script

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_modeling_policy')
    def get_modeling_policy() -> dict:
        return {"status": "success", "policy": modeling_policy.POLICY}


    @mcp.tool()
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


    @mcp.tool(annotations={"destructiveHint": False})
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


    @mcp.tool()
    @tool_instruction(__file__, 'setup_modeling')
    def setup_modeling(operation: str, overwrite: bool | None = None) -> str:
        if operation not in ("materials", "layers"):
            return json.dumps(error_payload("operation must be materials or layers"))
        if overwrite is not None and type(overwrite) is not bool:
            return json.dumps(error_payload("overwrite must be true, false or null"))
        if operation == "layers" and overwrite is not None:
            return json.dumps(error_payload("overwrite applies only to materials"))
        try:
            code = modeling_setup.setup_script(operation, context.material_library, context.construction_library, overwrite)
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            return json.dumps({"status": "error", "mutation_state": "not_started", "message": str(exc)})
        result = modeling_setup.dispatch(code, context._send_and_receive, timeout=600.0)
        if result.get("status") == "success" and (result.get("result_error") or not isinstance(result.get("result"), dict)):
            result.update(mutation_state="unknown", message=read_instruction(__file__, 'response-750'))
        return json.dumps(result)


    @mcp.tool()
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


    @mcp.tool()
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
        "get_modeling_policy": get_modeling_policy,
        "execute_rhino_script": execute_rhino_script,
        "save_rhino_document": save_rhino_document,
        "setup_modeling": setup_modeling,
        "list_materials": list_materials,
        "assign_material": assign_material,
        "_material_script": _material_script,
    }
