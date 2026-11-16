"""Public context/selection projections over the private native observation contract."""
import json
from collections import defaultdict

from almond_mcp.managed_paths import relative_output
from almond_mcp.query_output import project_query
from almond_mcp.tool_response import error_payload


VIEW_CATALOGUES = ("named_views", "layouts")
DISCOVERY_SECTIONS = ("document", *VIEW_CATALOGUES, "layer_tree")
DEFAULT_SECTIONS = (*DISCOVERY_SECTIONS, "display_modes")
SECTIONS = (*DEFAULT_SECTIONS, "viewport", "editor", "viewports")
ALWAYS_IDENTIFIED = (*VIEW_CATALOGUES, "display_modes")
VIEW_LIST_LIMIT = 128


def _error(message, code="invalid_arguments"):
    return json.dumps(error_payload(message, error_code=code), ensure_ascii=False)


def observe(send, sections, **options):
    request = {"type": "get_rhino_context", "sections": sections, "public_context": True, **options}
    return json.loads(send(json.dumps(request).encode("utf-8")))


def document_metadata(document, *, angle_key):
    if not isinstance(document, dict):
        return document
    return {
        **{key: document.get(key) for key in ("units", "absolute_tolerance", "modified", "object_count", "layer_count")},
        angle_key: document.get("angle_tolerance_radians"),
    }


def _format_layer_tree(layers):
    if not isinstance(layers, list):
        raise ValueError("Rhino returned an invalid layer list.")
    children = defaultdict(list)
    ids = set()
    for layer in layers:
        layer_id, parent_id, name = layer["id"], layer["parent_id"], layer["name"]
        if not isinstance(layer_id, str) or not layer_id or layer_id in ids or not isinstance(name, str):
            raise ValueError("Rhino returned an invalid or duplicate layer identity.")
        ids.add(layer_id)
        children[parent_id].append((layer_id, name))

    lines = []
    pending = [(layer_id, name, 0) for layer_id, name in reversed(children[None])]
    while pending:
        layer_id, name, depth = pending.pop()
        line_name = name.replace("\r", r"\r").replace("\n", r"\n")
        lines.append("  " * depth + line_name)
        pending.extend((child_id, child_name, depth + 1) for child_id, child_name in reversed(children[layer_id]))
    if len(lines) != len(ids):
        raise ValueError("Rhino returned an incomplete or cyclic layer hierarchy.")
    return "\n".join(lines)


def project_discovery_section(section, value, warnings):
    if value is None:
        if not any(str(warning).startswith(f"{section}:") for warning in warnings):
            warnings.append(f"{section}: Rhino did not return the requested observation.")
        return None
    if section == "layer_tree":
        try:
            return _format_layer_tree(value)
        except (TypeError, KeyError, ValueError) as exc:
            warnings.append(f"layer_tree: {exc}")
            return None
    if not isinstance(value, list):
        warnings.append(f"{section}: Rhino returned an invalid list.")
        return None
    if len(value) > VIEW_LIST_LIMIT:
        warnings.append(f"{section}: first {VIEW_LIST_LIMIT} of {len(value)} returned.")
    return value[:VIEW_LIST_LIMIT]


def _observe(send, sections):
    response = observe(send, sections)
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
        warnings = list(response.get("warnings", []))
        result = {"status": "success", "warnings": warnings}
        for section in dict.fromkeys(sections):
            value = response[section]
            if section == "document":
                value = document_metadata(value, angle_key="angle_tolerance")
            elif section in DISCOVERY_SECTIONS:
                value = project_discovery_section(section, value, warnings)
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
        return json.dumps(relative_output(result, preserve_text_fields=("name", "layer_tree")), ensure_ascii=False)
    except Exception as exc:
        return _error(f"Could not read the live Rhino context: {exc}", "bridge_error")
