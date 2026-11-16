"""Explicit catalog authoring for the connection's project database."""

from almond_mcp.tool_response import error_payload


def save_project_file(get_store, file_name: str, description: str | None) -> dict:
    """Upsert the explicit database record for the current project."""
    try:
        return {"status": "success", **get_store().upsert_project_file(file_name, description)}
    except (ValueError, RuntimeError) as exc:
        return error_payload(str(exc))
