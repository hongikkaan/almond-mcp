"""Public context/selection projections over the private native observation contract."""
import json

from almond_mcp.managed_paths import relative_output, relative_path
from almond_mcp.query_output import project_query
from almond_mcp.tool_response import error_payload


DEFAULT_SECTIONS = ("document", "named_views", "layouts", "layers", "display_modes")
SECTIONS = (*DEFAULT_SECTIONS, "worksession", "viewport", "editor", "viewports")
ALWAYS_IDENTIFIED = ("named_views", "layouts", "display_modes")
PROJECT_CATALOGUES = ("named_views", "layouts", "layers", "worksession")


def _error(message, code="invalid_arguments"):
    return json.dumps(error_payload(message, error_code=code), ensure_ascii=False)


def observe_context(send, sections, **options):
    """Read requested sections once for both public document discovery tools."""
    response = json.loads(send(json.dumps({"type": "get_rhino_context", "sections": sections,
                                          "public_context": True, **options}).encode("utf-8")))
    if not isinstance(response, dict) or response.get("status") not in ("success", "error"):
        raise ValueError("The Bridge returned an invalid context response.")
    required = 4 if "worksession" in sections else 3 if "layers" in sections else 2
    if response["status"] == "success" and response.get("capabilities", {}).get("context_sections", 0) < required:
        return error_payload(f"Load the matching Bridge with context_sections>={required} for the requested context sections.",
                             error_code="unsupported_context")
    if response["status"] == "success":
        missing = [section for section in sections if section not in response]
        if missing:
            raise ValueError("The Bridge omitted requested sections: " + ", ".join(missing))
    return response


def layer_tree(layers):
    """Render every live layer once, preserving names and parent identities."""
    if layers is None:
        return None
    if not isinstance(layers, list):
        raise ValueError("The Bridge returned an invalid layer catalogue.")
    nodes = {}
    for layer in layers:
        if (not isinstance(layer, dict) or not isinstance(layer.get("name"), str)
                or not isinstance(layer.get("id"), str) or not layer["id"]
                or layer["id"] in nodes):
            raise ValueError("The Bridge returned an invalid layer identity.")
        nodes[layer["id"]] = layer
    children = {key: [] for key in nodes}
    roots = []
    for key, layer in nodes.items():
        parent = layer.get("parent_id")
        if parent is not None and not isinstance(parent, str):
            raise ValueError("The Bridge returned an invalid layer parent identity.")
        if parent in (None, "", "00000000-0000-0000-0000-000000000000"):
            roots.append(key)
        elif parent in nodes:
            children[parent].append(key)
        else:
            raise ValueError("The Bridge returned a layer with a missing parent.")
    lines, visited = [], set()
    pending = [(key, 0) for key in reversed(roots)]
    while pending:
        key, depth = pending.pop()
        if key in visited:
            raise ValueError("The Bridge returned a cyclic layer hierarchy.")
        visited.add(key)
        name = nodes[key]["name"]
        # Keep embedded line breaks from masquerading as another layer.
        label = json.dumps(name, ensure_ascii=False) if any(c in name for c in "\r\n") else name
        lines.append("  " * depth + "- " + label)
        pending.extend((child, depth + 1) for child in reversed(children[key]))
    if len(visited) != len(nodes):
        raise ValueError("The Bridge returned a cyclic layer hierarchy.")
    return "\n".join(lines)


def context_catalogues(response, sections):
    """Shared catalogue projection; stored view identities and metadata survive."""
    return {section: layer_tree(response[section]) if section == "layers" else response[section]
            for section in sections if section in PROJECT_CATALOGUES}


def relative_context_output(value):
    """Keep attachment identities when Windows cannot form a relative path."""
    result = relative_output(value)
    worksession = value.get("worksession")
    if isinstance(worksession, dict):
        for source, target in zip(worksession["attachments"], result["worksession"]["attachments"]):
            target["path"] = relative_path(source["path"], preserve_cross_drive=True)
    return result


def query(send, sections=None, include_ids=False, include_editor_details=False):
    if type(include_ids) is not bool or type(include_editor_details) is not bool:
        return _error("include_ids and include_editor_details must be booleans.")
    default = sections is None
    sections = list(DEFAULT_SECTIONS) if default else sections
    if not isinstance(sections, list) or any(not isinstance(s, str) or s not in SECTIONS for s in sections):
        return _error("sections must contain " + ", ".join(SECTIONS) + ".")
    try:
        response = observe_context(send, sections)
        if response["status"] == "error":
            return json.dumps(response, ensure_ascii=False)
        result = {"status": "success", "warnings": response.get("warnings", [])}
        catalogues = context_catalogues(response, sections)
        for section in dict.fromkeys(sections):
            value = catalogues.get(section, response[section])
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
        return json.dumps(relative_context_output(result), ensure_ascii=False)
    except Exception as exc:
        return _error(f"Could not read the live Rhino context: {exc}", "bridge_error")
