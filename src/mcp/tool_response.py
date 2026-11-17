"""Common response fields and explicit error propagation at the MCP boundary."""

from functools import wraps
import json


def transform_response(result, transform, *, text_transform=None):
    """Map a JSON body without changing its public transport or binary evidence.

    FastMCP represents a string return as ``{result: <JSON text>}``; a dict
    return is structured directly. Only that outer wrapper is decoded. Strings
    inside the body are user data. Matching text/structured bodies are mapped
    once, and unrelated text blocks change only when a text mapper is supplied.
    """
    def decode(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                return None
        return value if isinstance(value, (dict, list)) else None

    if isinstance(result, (dict, list)):
        return transform(result)
    if isinstance(result, str):
        body = decode(result)
        if body is not None:
            updated = transform(body)
            return result if updated == body else json.dumps(updated, ensure_ascii=False)
        return text_transform(result) if text_transform else result

    from fastmcp.tools import ToolResult
    if not isinstance(result, ToolResult):
        return result
    structured = result.structured_content
    wrapped = (isinstance(structured, dict) and set(structured) == {"result"}
               and isinstance(structured["result"], str))
    body = decode(structured["result"] if wrapped else structured)
    serialized = None
    if body is not None:
        updated = transform(body)
        serialized = json.dumps(updated, ensure_ascii=False)
        structured = {"result": serialized} if wrapped else updated
    content = []
    for block in result.content:
        if block.type == "text":
            if body is not None and decode(block.text) == body:
                block = block.model_copy(update={"text": serialized})
            elif text_transform:
                block = block.model_copy(update={"text": text_transform(block.text)})
        content.append(block)
    return result.model_copy(update={"content": content, "structured_content": structured})


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
