"""Shared public tool declarations and their MCP output envelopes."""

from copy import deepcopy
from functools import cache
from importlib.resources import files
import json

from almond_mcp.public_names import public_tool_name


@cache
def _contracts() -> dict:
    resource = files("almond_mcp").joinpath("public_contract_data.json")
    return json.loads(resource.read_text(encoding="utf-8"))["tools"]


def _output_schema(payload: dict, wrapped: bool) -> dict:
    schema = deepcopy(payload)
    if not wrapped:
        return schema

    return {
        "type": "object",
        "properties": {
            "result": {
                "type": "string",
                "contentMediaType": "application/json",
                "contentSchema": schema,
            },
        },
        "required": ["result"],
        "x-fastmcp-wrap-result": True,
    }


def public_tool_contract(name: str) -> dict:
    """Return a tool's published description, schemas and result transport."""
    contract = _contracts()[name]
    return {
        "description": contract["description"],
        "input_schema": deepcopy(contract["input_schema"]),
        "output_schema": _output_schema(contract["payload_schema"], contract["wrapped"]),
        "wrapped": contract["wrapped"],
    }


def public_output_schema(name: str, wrapped: bool = True) -> dict:
    """Return an optionally wrapped result schema for a public or internal name."""
    contract = _contracts()[public_tool_name(name)]
    return _output_schema(contract["payload_schema"], wrapped)
