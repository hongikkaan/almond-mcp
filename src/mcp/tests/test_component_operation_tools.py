"""Public bounded Component intersection/focus wiring, without opening Rhino."""
import asyncio
import importlib.util
import json
from pathlib import Path
import uuid

import pytest
from fastmcp import Client


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("component-operation-tools")
    source = Path(__file__).resolve().parents[3] / "src/mcp/server.py"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RHINO_MCP_STATE_DB", str(root / "state.sqlite3"))
        for suffix in ("LIBRARY", "DRAWING_ASSET", "DIAGRAM_ASSET", "GENERATED_ASSET",
                       "DRAWING_RECIPE", "DRAFTING", "CAPSULE", "MATERIAL", "CONSTRUCTION"):
            patch.setenv(f"RHINO_MCP_{suffix}_DIR", str(root / suffix.lower()))
        spec = importlib.util.spec_from_file_location(f"component_operation_server_{uuid.uuid4().hex}", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


def call(server, name, **arguments):
    tool = getattr(server, name)
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def wire(server, monkeypatch, capable=True, native=None):
    calls = []
    def send(payload):
        request = json.loads(payload)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"component_operations": 1} if capable else {}})
        if isinstance(native, Exception):
            raise native
        response = native if native is not None else {"status": "success", "complete": False,
            "has_positive_overlap": None, "truncated": True, "object_count": 2}
        return json.dumps(response)
    monkeypatch.setattr(server, "_send_and_receive", send)
    return calls


def test_public_intersection_resolves_native_request_and_preserves_unknowns(server, monkeypatch):
    calls = wire(server, monkeypatch)
    result = call(server, "get_component_intersections", expected_model_path=r"C:\Models\test.3dm",
                  component_ids=["facade", "roof"], max_pairs=4, include_ids=True)
    assert result["status"] == "success"
    assert result["complete"] is False and result["has_positive_overlap"] is None
    assert [call_["type"] for call_ in calls] == ["get_rhino_context", "component_operation"]
    assert calls[1] == dict(type="component_operation", action="intersections",
                             expected_model_path=r"c:\models\test.3dm",
                             component_ids=["facade", "roof"], max_pairs=4)


def test_public_focus_sends_one_native_request_and_preserves_result(server, monkeypatch):
    native = {"status": "success", "isolated": True, "zoom_selected": True,
              "selected_ids": [str(uuid.UUID(int=1))], "restore_visibility_command": "Unisolate"}
    calls = wire(server, monkeypatch, native=native)
    result = call(server, "focus_components", expected_model_path=r"C:\Models\test.3dm",
                  component_ids=["facade"])
    assert result == native
    assert len(calls) == 2 and calls[1]["action"] == "focus"
    assert "max_pairs" not in calls[1]


def test_old_bridge_does_not_receive_unknown_native_component_operations(server, monkeypatch):
    calls = wire(server, monkeypatch, capable=False)
    for name, arguments in (
        ("get_component_intersections", {"max_pairs": 8}), ("focus_components", {}),
    ):
        result = call(server, name, expected_model_path=r"C:\Models\test.3dm",
                      component_ids=["panel"], **arguments)
        assert result["status"] == "error" and result["mutation_applied"] is False
        assert "component_operations=1" in result["message"]
    assert [request["type"] for request in calls] == ["get_rhino_context", "get_rhino_context"]


@pytest.mark.parametrize("component_ids,max_pairs", [
    ([], 64), (["panel", "panel"], 64), ([""], 64), (["panel"], 0), (["panel"], 65),
    (["panel"], True), (["panel"], 1.5), (["panel"] * 33, 64),
])
def test_invalid_arguments_do_not_reach_native(server, monkeypatch, component_ids, max_pairs):
    calls = wire(server, monkeypatch)
    result = call(server, "get_component_intersections", expected_model_path=r"C:\Models\test.3dm",
                  component_ids=component_ids, max_pairs=max_pairs, include_ids=True)
    assert result["status"] == "error" and result["error_code"] == "invalid_arguments"
    assert calls == []


def test_focus_timeout_never_auto_retries_ambiguous_change(server, monkeypatch):
    calls = wire(server, monkeypatch, native=TimeoutError("Lost focus acknowledgement"))
    result = call(server, "focus_components", expected_model_path=r"C:\Models\test.3dm",
                  component_ids=["panel"])
    assert result["status"] == "error"
    assert result["requires_reconciliation"] is True and result["mutation_applied"] is None
    assert [request["type"] for request in calls] == ["get_rhino_context", "component_operation"]


def test_protocol_schemas_expose_readonly_only_for_intersections(server):
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            read = tools["get_component_intersections"]
            focus = tools["focus_components"]
            assert read["annotations"]["readOnlyHint"] is True
            assert focus["annotations"].get("readOnlyHint") is not True
            assert read["inputSchema"]["properties"]["max_pairs"]["default"] == 64
            assert {"component_ids"} == set(focus["inputSchema"]["required"])
            assert focus["inputSchema"]["properties"]["expected_model_path"]["default"] == ""
            for bad in (True, "5", 5.0):
                result = await client.call_tool("get_component_intersections", {
                    "expected_model_path": r"C:\Models\test.3dm", "component_ids": ["panel"],
                    "max_pairs": bad,
                }, raise_on_error=False)
                assert result.is_error
    asyncio.run(verify())
