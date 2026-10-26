"""Common tool response fields, independent of JSON and MCP transport."""


def error_payload(message: str, *, error_code: str | None = None) -> dict:
    """Build an error envelope without inferring mutation or reconciliation state."""
    result = {"status": "error"}
    if error_code is not None:
        result["error_code"] = error_code
    result["message"] = message
    return result
