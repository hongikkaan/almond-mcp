"""Fixed observation errors use the MCP error flag without discarding evidence."""
import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP
from fastmcp.tools import ToolResult

from almond_mcp.features.context.tools import register


@pytest.mark.parametrize("name,arguments", [
    ("get_objects", {"scope": "not-a-scope"}),
    ("get_object_intersections", {"object_ids": []}),
])
def test_invalid_observation_input_sets_mcp_error_without_native_dispatch(name, arguments):
    calls = []
    tools = register(FastMCP("observation-error-test"), SimpleNamespace(_send_and_receive=calls.append))

    result = tools[name](**arguments)

    assert isinstance(result, ToolResult)
    assert result.is_error
    assert json.loads(result.structured_content["result"])["error_code"] == "invalid_arguments"
    assert result.content[0].text == result.structured_content["result"]
    assert calls == []


@pytest.mark.parametrize("name,arguments", [
    ("get_objects", {}),
    ("get_object_intersections", {"object_ids": [str(UUID(int=1))]}),
])
def test_native_observation_error_keeps_details_and_sets_mcp_error(name, arguments, monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", r"C:\offline\model.3dm")
    error = {"status": "error", "error_code": "document_mismatch", "message": "Bound document changed.",
             "details": {"observed_path": "other.3dm"}, "complete": False}

    def send(raw):
        if json.loads(raw)["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"object_observation": 4, "intersection_queries": 1}})
        return json.dumps(error)

    tools = register(FastMCP("observation-error-test"), SimpleNamespace(_send_and_receive=send))
    result = tools[name](**arguments)
    assert isinstance(result, ToolResult)
    assert result.is_error
    assert json.loads(result.structured_content["result"]) == error


def test_unknown_intersections_cannot_be_reported_as_a_complete_count(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", r"C:\offline\model.3dm")
    evidence = {"status": "success", "complete": False, "pagination_complete": False,
                "next_cursor": "continue-the-same-scope", "unsupported_objects": [],
                "pairs": [{"a": {"handle": "a"}, "b": {"handle": "b"},
                           "overlap": {"status": "unknown", "reason": "Boolean failed"}}]}

    def send(raw):
        if json.loads(raw)["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"intersection_queries": 1}})
        return json.dumps(evidence)

    tool = register(FastMCP("observation-partial-test"), SimpleNamespace(_send_and_receive=send))["get_object_intersections"]
    result = tool(object_ids=[str(UUID(int=1))])
    assert isinstance(result, ToolResult) and result.is_error
    detail = json.loads(result.structured_content["result"])
    assert detail["error_code"] == "intersection_count_incomplete"
    assert "intersections" not in detail
    assert detail["failed_pairs"][0]["reason"] == evidence["pairs"][0]["overlap"]


@pytest.mark.parametrize("name,arguments", [
    ("inspect_02-get_objects", {"scope": "not-a-scope"}),
    ("intersect_01-find", {"object_ids": []}),
])
def test_mcp_client_receives_the_error_flag_and_original_json(name, arguments):
    calls = []
    server = FastMCP("observation-protocol-test")
    register(server, SimpleNamespace(_send_and_receive=calls.append))

    async def call():
        async with Client(server) as client:
            return await client.call_tool(name, arguments, raise_on_error=False)

    result = asyncio.run(call())
    assert result.is_error
    metadata = result.structured_content
    assert json.loads(metadata["result"])["error_code"] == "invalid_arguments"
    assert result.content[0].text == metadata["result"]
    assert calls == []
