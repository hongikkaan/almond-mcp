"""Capsule discovery is compact; a requested parsed logic remains usable."""
from almond_mcp.query_output import select_fields

GROUPS = {
    "ports": {"inputs", "outputs", "input_ports", "output_ports"},
    "definition": {"definition", "definition_file", "metadata", "all_descriptions", "components"},
    "source": {"source", "source_url", "license", "provenance"},
    "paths": {"library_dir", "capsule_library_dir", "file_name", "definition_file"},
    "audit": {"created_at", "updated_at", "audit", "audit_status", "sha256"},
}

def project(payload: dict, groups: list[str] | None) -> dict:
    # Parsed logic is the requested payload, rather than a discovery list.
    core = {"status", "logic_id", "total_entries", "logic_names", "logic_ids", "total", "limit", "offset", "next_offset",
            "capsules", "components", "all_descriptions", "metadata", "file_name"}
    result = select_fields(payload, groups, core, GROUPS)
    if "capsules" in result:
        result["capsules"] = [select_fields(item, groups,
            {"capsule_id", "title", "name", "capabilities", "capability", "structure_type", "audited", "auditable", "reason"}, GROUPS)
            for item in result["capsules"]]
    return result
