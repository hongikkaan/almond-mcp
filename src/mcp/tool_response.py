"""Common response fields and explicit error propagation at the MCP boundary."""

from functools import wraps
import json


def error_payload(message: str, *, error_code: str | None = None) -> dict:
    """Build an error envelope without inferring mutation or reconciliation state."""
    result = {"status": "error"}
    if error_code is not None:
        result["error_code"] = error_code
    result["message"] = message
    return result


def mcp_error_result(function):
    """Preserve the JSON string contract while marking explicit failures as MCP errors."""
    @wraps(function)
    def invoke(*args, **kwargs):
        serialized = function(*args, **kwargs)
        if isinstance(serialized, str):
            value = json.loads(serialized)
            if isinstance(value, dict) and value.get("status") == "error":
                from fastmcp.tools import ToolResult
                from mcp.types import TextContent
                return ToolResult(content=[TextContent(type="text", text=serialized)],
                                  structured_content={"result": serialized}, is_error=True)
        return serialized
    return invoke
