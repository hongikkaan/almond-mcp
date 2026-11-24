"""Behavioral coverage of camera operations across the MCP/Bridge boundary."""
import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.capture import manipulation, tools
from almond_mcp.tool_declarations import declaration_sources, inspect_declarations, register_inert_tools


NAME = "capture_05-manipulate_view"


def test_live_and_inert_schemas_publish_exclusive_flat_operations():
    async def check():
        live = FastMCP("viewport-live")
        tools.register(live, SimpleNamespace(_send_and_receive=None))
        inert = FastMCP("viewport-inert")
        path, = (path for path in declaration_sources() if path.parent.name == "capture")
        register_inert_tools(inert, inspect_declarations((path,)))
        async with Client(live) as live_client, Client(inert) as inert_client:
            live_tool = next(tool for tool in await live_client.list_tools() if tool.name == NAME)
            inert_tool = next(tool for tool in await inert_client.list_tools() if tool.name == NAME)
            schema = live_tool.input_schema
            assert schema == inert_tool.input_schema
            rotate, zoom = schema["oneOf"]
            assert rotate["required"] == ["operation", "mode"]
            assert rotate["not"] == {"required": ["factor"]}
            assert zoom["required"] == ["operation", "factor"]
            assert zoom["properties"]["factor"]["exclusiveMinimum"] == 0
            assert {entry["required"][0] for entry in zoom["not"]["anyOf"]} == {"mode", "yaw_deg", "pitch_deg"}

    asyncio.run(check())


@pytest.mark.parametrize(
    ("operation", "args"),
    [("rotate", {"mode": "look"}), ("rotate", {"mode": "orbit", "yaw_deg": 10, "factor": 2}),
     ("rotate", {"mode": "look", "pitch_deg": float("inf")}), ("rotate", {"mode": "look", "yaw_deg": True}),
     ("zoom", {"factor": 0}), ("zoom", {"factor": -1}), ("zoom", {"factor": "2"}),
     ("zoom", {"factor": 2, "mode": "look"}), ("zoom", {"factor": 2, "expected_viewport_id": "bad"})],
)
def test_invalid_operations_never_touch_bridge(monkeypatch, operation, args):
    monkeypatch.setenv("ALMOND_MODEL_PATH", r"C:\test.3dm")

    def forbidden(_payload):
        pytest.fail("invalid arguments touched bridge")

    result = manipulation.execute(forbidden, operation, **args)
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_arguments"
    assert result.structured_content["mutation_applied"] is False


def test_mcp_routes_flat_request_and_preserves_verified_result(monkeypatch):
    model = r"C:\test.3dm"
    monkeypatch.setenv("ALMOND_MODEL_PATH", model)
    requests = []
    viewport = str(uuid4())
    native = {"status": "success", "viewport_id": viewport, "camera_location": [4, 5, 6],
              "camera_target": [1, 2, 3], "mutation_applied": True, "requires_reconciliation": False}

    def bridge(payload):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"view_manipulation": 1}})
        return json.dumps(native)

    async def check():
        server = FastMCP("viewport-tool")
        tools.register(server, SimpleNamespace(_send_and_receive=bridge))
        async with Client(server) as client:
            response = await client.call_tool(NAME, {"operation": "rotate", "mode": "orbit", "yaw_deg": 30,
                                                     "expected_viewport_id": viewport})
            assert response.structured_content == native
            for args in ({"operation": "zoom", "factor": 2, "yaw_deg": 0},
                         {"operation": "zoom", "factor": True},
                         {"operation": "zoom", "factor": 2, "mode": None}):
                denied = await client.call_tool(NAME, args, raise_on_error=False)
                assert denied.is_error

    asyncio.run(check())
    assert requests == [
        {"type": "get_rhino_context", "sections": [], "selection_limit": 0},
        {"type": "manipulate_view", "operation": "rotate", "mode": "orbit", "yaw_deg": 30.0,
         "pitch_deg": 0, "expected_viewport_id": viewport, "expected_model_path": model},
    ]


@pytest.mark.parametrize("reply", [None,
    {"status": "error", "error_code": "view_manipulation_failed", "mutation_applied": True, "requires_reconciliation": False},
    {"status": "error", "error_code": " ", "mutation_applied": False, "requires_reconciliation": False},
    {"status": "success"}, {"status": "success", "mutation_applied": True,
    "requires_reconciliation": False, "viewport_id": str(uuid4()), "camera_location": [1, 2, 3], "camera_target": [1, 2, 3]}])
def test_unverified_relative_mutation_is_never_retried(monkeypatch, reply):
    monkeypatch.setenv("ALMOND_MODEL_PATH", r"C:\test.3dm")
    types = []

    def bridge(payload):
        types.append(json.loads(payload)["type"])
        if len(types) == 1:
            return json.dumps({"status": "success", "capabilities": {"view_manipulation": 1}})
        if reply is None:
            raise TimeoutError
        return json.dumps(reply)

    result = manipulation.execute(bridge, "zoom", factor=2, expected_viewport_id=str(uuid4()))
    assert result.is_error
    assert result.structured_content["mutation_applied"] is None
    assert result.structured_content["requires_reconciliation"] is True
    assert types == ["get_rhino_context", "manipulate_view"]


@pytest.mark.parametrize("applied", [False, None])
def test_verified_native_failures_keep_their_outcome(monkeypatch, applied):
    monkeypatch.setenv("ALMOND_MODEL_PATH", r"C:\test.3dm")
    failure = {"status": "error", "error_code": "view_manipulation_failed", "mutation_applied": applied,
               "requires_reconciliation": applied is None}
    replies = iter([{"status": "success", "capabilities": {"view_manipulation": 1}}, failure])
    result = manipulation.execute(lambda payload: json.dumps(next(replies)), "zoom", factor=2)
    assert result.is_error and result.structured_content == failure


def test_native_view_guards_projection_readback_and_rollback(tmp_path):
    from pathlib import Path

    from test_stage2_native_feedback import build_host

    source = Path(__file__).with_name("view_manipulation_host") / "Program.cs"
    run = build_host(tmp_path, source.read_text(encoding="utf-8"),
                     ["features/capture/native/ViewManipulation.cs"])
    assert run("camera") == {"verified": True}
