"""Public context/selection projections over the private native observation contract."""
import json

from almond_mcp.managed_paths import relative_output
from almond_mcp.query_output import project_query
from almond_mcp.tool_response import error_payload


DEFAULT_SECTIONS = ("document", "named_views", "layouts", "display_modes")
SECTIONS = (*DEFAULT_SECTIONS, "viewport", "editor", "viewports")
ALWAYS_IDENTIFIED = ("named_views", "layouts", "display_modes")


def _error(message, code="invalid_arguments"):
    return json.dumps(error_payload(message, error_code=code), ensure_ascii=False)


def _observe(send, sections, **options):
    response = json.loads(send(json.dumps({"type": "get_rhino_context", "sections": sections,
                                          "public_context": True, **options}).encode("utf-8")))
    if not isinstance(response, dict) or response.get("status") not in ("success", "error"):
        raise ValueError("The Bridge returned an invalid context response.")
    if response["status"] == "success" and response.get("capabilities", {}).get("context_sections", 0) < 2:
        return error_payload("Load the matching Bridge with context_sections>=2 for context and selection queries.",
                             error_code="unsupported_context")
    return response


def query(send, sections=None, include_ids=False, include_editor_details=False):
    if type(include_ids) is not bool or type(include_editor_details) is not bool:
        return _error("include_ids and include_editor_details must be booleans.")
    default = sections is None
    sections = list(DEFAULT_SECTIONS) if default else sections
    if not isinstance(sections, list) or any(not isinstance(s, str) or s not in SECTIONS for s in sections):
        return _error("sections must contain " + ", ".join(SECTIONS) + ".")
    try:
        response = _observe(send, sections)
        if response["status"] == "error":
            return json.dumps(response, ensure_ascii=False)
        missing = [s for s in sections if s not in response]
        if missing:
            raise ValueError("The Bridge omitted requested sections: " + ", ".join(missing))
        result = {"status": "success", "warnings": response.get("warnings", [])}
        for section in dict.fromkeys(sections):
            value = response[section]
            if section == "document" and isinstance(value, dict):
                value = {k: value.get(k) for k in ("units", "absolute_tolerance", "modified", "object_count", "layer_count")}
                value["angle_tolerance"] = response[section].get("angle_tolerance_radians")
            elif section == "editor" and isinstance(value, dict) and not include_editor_details:
                value = {k: value.get(k) for k in ("mode", "target", "stable", "warnings")}
            elif section == "editor" and isinstance(value, dict) and not include_ids and isinstance(value.get("evidence"), dict):
                value = {**value, "evidence": {k: v for k, v in value["evidence"].items() if k != "document_serial_number"}}
            result[section] = value
        # Only these three catalogues always retain IDs; other identities keep the usual policy.
        catalogues = {key: result.pop(key) for key in ALWAYS_IDENTIFIED if key in result}
        result = project_query(result, include_ids=include_ids)
        result.update(catalogues)
        if default:
            result["next_step_guide"] = "현재 화면을 보려면 capture_03-current_view tool을 사용하세요."
        return json.dumps(relative_output(result), ensure_ascii=False)
    except Exception as exc:
        return _error(f"Could not read the live Rhino context: {exc}", "bridge_error")
