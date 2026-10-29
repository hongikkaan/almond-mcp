"""Public observation contracts with a fake bridge and an isolated state database."""
import asyncio
import base64
import importlib.util
import io
import json
from pathlib import Path
import uuid

import pytest
from fastmcp import Client
from PIL import Image


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("rhino-observation")
    source = Path(__file__).resolve().parents[3] / "src/mcp/server.py"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RHINO_MCP_STATE_DB", str(root / "state.sqlite3"))
        for suffix in ("LIBRARY", "DRAWING_ASSET", "DIAGRAM_ASSET", "GENERATED_ASSET",
                       "DRAWING_RECIPE", "DRAFTING", "CAPSULE", "MATERIAL", "CONSTRUCTION"):
            patch.setenv(f"RHINO_MCP_{suffix}_DIR", str(root / suffix.lower()))
        spec = importlib.util.spec_from_file_location(f"observation_server_{uuid.uuid4().hex}", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


def call(tool, **arguments):
    return getattr(tool, "fn", tool)(**arguments)


def capture_response(scale_percent=75):
    output = io.BytesIO()
    size = (max(1, 160 * scale_percent // 100), max(1, 80 * scale_percent // 100))
    Image.new("RGB", size, (40, 80, 120)).save(output, format="PNG")
    return {
        "status": "success", "document": {"name": "fixture.3dm", "runtime_serial_number": 7},
        "viewport": {"id": "fixture-view", "name": "Perspective", "width": 1600, "height": 800},
        "warnings": [],
        "image": {"mime_type": "image/png", "width": size[0], "height": size[1],
                  "source_width": 160, "source_height": 80,
                  "data": base64.b64encode(output.getvalue()).decode("ascii")},
    }


def test_context_sends_only_a_fixed_live_query(server, monkeypatch):
    requests = []
    response = {"status": "success", "document": {"runtime_serial_number": 42},
                "editor": {"mode": "unknown", "target": None, "stable": False},
                "selection": {"total": 5, "returned": 2, "truncated": True},
                "viewport": None, "warnings": ["No active view."]}

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps(response)

    monkeypatch.setattr(server, "_send_and_receive", send)
    assert json.loads(call(server.get_rhino_context, selection_limit=2, sections=["document", "selection", "viewport"])) == response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 2, "sections": ["document", "selection", "viewport"],
                         "recursive": False, "depth": 1, "include_image": False, "selection_entities": True}]


@pytest.mark.parametrize("limit", [-1, 201, True, "5", 2.5])
def test_context_rejects_bad_limits_before_bridge(server, monkeypatch, limit):
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected bridge call"))
    result = json.loads(call(server.get_rhino_context, selection_limit=limit))
    assert result["error_code"] == "invalid_arguments"


@pytest.mark.parametrize("arguments", [{"scale_percent": 0}, {"scale_percent": 101},
                                        {"scale_percent": True}, {"scale_percent": "50"},
                                        {"view": "Perspective"}, {"view": None}, {"include_usage": "false"}])
def test_capture_rejects_bad_limits_before_bridge(server, monkeypatch, arguments):
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected bridge call"))
    result = call(server.get_rhino_viewport_image, **arguments)
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_arguments"
    assert [item.type for item in result.content] == ["text"]


@pytest.mark.parametrize("name,arguments", [
    ("get_rhino_context", {"selection_limit": True}),
    ("get_rhino_context", {"selection_limit": "5"}),
    ("get_rhino_context", {"selection_limit": 5.0}),
    ("get_rhino_viewport_image", {"scale_percent": True}),
    ("get_rhino_viewport_image", {"scale_percent": "50"}),
    ("get_rhino_viewport_image", {"scale_percent": 50.0}),
    ("get_rhino_viewport_image", {"include_usage": 1}),
])
def test_mcp_protocol_rejects_coercible_non_integer_types(server, monkeypatch, name, arguments):
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected bridge call"))

    async def verify():
        async with Client(server.mcp) as client:
            result = await client.call_tool(name, arguments, raise_on_error=False)
            assert result.is_error
            assert all(item.type != "image" for item in result.content)
    asyncio.run(verify())


def test_real_mcp_image_and_metadata_survive_protocol(server, monkeypatch):
    response = capture_response()
    requests = []

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps(response)

    monkeypatch.setattr(server, "_send_and_receive", send)

    async def verify():
        async with Client(server.mcp) as client:
            result = await client.call_tool("get_rhino_viewport_image", {})
            assert not result.is_error
            assert [item.type for item in result.content] == ["image"]
            assert result.content[0].data == response["image"]["data"]
            assert result.content[0].mime_type == "image/png"
            assert result.structured_content is None
    asyncio.run(verify())
    assert requests == [{"type": "get_rhino_viewport_image", "view": "", "scale_percent": 75,
                         "display_mode": "", "labels": True, "depth": 1, "target_kind": "view", "target_id": ""}]


@pytest.mark.parametrize("fault", ["base64", "format", "mismatched_size", "too_wide", "not_image",
                                    "oversized", "missing_image", "not_object", "empty"])
def test_invalid_capture_never_emits_an_image(server, monkeypatch, fault):
    response = capture_response()
    if fault == "base64":
        response["image"]["data"] = "!not-base64!"
    elif fault == "format":
        response["image"]["mime_type"] = "image/jpeg"
    elif fault == "mismatched_size":
        response["image"]["width"] = 81
    elif fault == "too_wide":
        response["image"]["width"] = 2049
    elif fault == "not_image":
        response["image"]["data"] = base64.b64encode(b"no PNG here").decode("ascii")
    elif fault == "oversized":
        response["image"]["data"] = "A" * (4 * ((4 * 1024 * 1024 + 2) // 3) + 4)
    elif fault == "missing_image":
        response.pop("image")
    elif fault == "not_object":
        response = []
    elif fault == "empty":
        response["image"]["data"] = ""
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: json.dumps(response))
    result = call(server.get_rhino_viewport_image)
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_capture_response"
    assert [item.type for item in result.content] == ["text"]


def test_native_error_keeps_error_flag_and_drops_any_image(server, monkeypatch):
    response = capture_response()
    response.update(status="error", error_code="capture_failed", message="No bitmap was returned.")
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: json.dumps(response))

    async def verify():
        async with Client(server.mcp) as client:
            result = await client.call_tool("get_rhino_viewport_image", {}, raise_on_error=False)
            assert result.is_error
            assert result.structured_content["error_code"] == "capture_failed"
            assert "image" not in result.structured_content
            assert [item.type for item in result.content] == ["text"]
    asyncio.run(verify())


def test_bridge_exception_is_an_explicit_capture_error(server, monkeypatch):
    def failed(*_):
        raise TimeoutError("fixture acknowledgement timeout")
    monkeypatch.setattr(server, "_send_and_receive", failed)
    result = call(server.get_rhino_viewport_image)
    assert result.is_error
    assert result.structured_content["error_code"] == "bridge_error"
    assert "fixture acknowledgement timeout" in result.structured_content["message"]


@pytest.mark.parametrize("percent", [1, 50, 100])
def test_percent_and_optional_usage(server, monkeypatch, percent):
    requests = []
    guid = str(uuid.uuid4())
    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps(capture_response(percent))
    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.get_rhino_viewport_image, view=guid, scale_percent=percent, include_usage=True)
    assert not result.is_error
    assert [item.type for item in result.content] == ["image", "text"]
    usage = json.loads(result.content[1].text)
    assert (usage["width"], usage["height"]) == (max(1, 160 * percent // 100), max(1, 80 * percent // 100))
    assert usage["estimated_image_tokens"] == {1: 2, 50: 8, 100: 18}[percent]
    assert "actual model/detail may differ" in usage["assumption"]
    assert requests == [{"type": "get_rhino_viewport_image", "view": guid, "scale_percent": percent,
                         "display_mode": "", "labels": True, "depth": 1, "target_kind": "view", "target_id": ""}]


def test_view_list_protocol_has_only_grouped_names_and_guids(server, monkeypatch):
    groups = {name: [{"name": "같은 이름", "guid": str(uuid.uuid4()), "extra": "discard"}]
              for name in ("viewports", "named_views", "layouts")}
    def send(payload):
        assert json.loads(payload)["view"] == "a"
        return json.dumps({"status": "success", "views": groups})
    monkeypatch.setattr(server, "_send_and_receive", send)
    async def verify():
        async with Client(server.mcp) as client:
            result = await client.call_tool("get_rhino_viewport_image", {"view": "a", "include_usage": True})
            assert not result.is_error
            assert [item.type for item in result.content] == ["text"]
            assert result.structured_content is None
            parsed = json.loads(result.content[0].text)
            assert set(parsed) == set(groups)
            for group, entries in parsed.items():
                assert entries == [{"name": groups[group][0]["name"], "guid": groups[group][0]["guid"]}]
    asyncio.run(verify())


@pytest.mark.parametrize("groups", [None, {}, {"viewports": [], "named_views": [], "layouts": [None]},
                                    {"viewports": [], "named_views": [], "layouts": [{"name": "x", "guid": "bad"}]}])
def test_malformed_view_list_is_an_error(server, monkeypatch, groups):
    monkeypatch.setattr(server, "_send_and_receive", lambda _: json.dumps({"status": "success", "views": groups}))
    assert call(server.get_rhino_viewport_image, view="a").is_error




@pytest.mark.parametrize("mode", ["outline", "resolve-block"])
def test_fixed_mode_checks_capability_then_uses_native_query(server, monkeypatch, mode):
    requests = []
    model = "C:\\fixture\\model.3dm"
    response = {"status": "success", "mode": mode, "document": {"path": model}, "data": {"measured": 12}}

    def send(payload):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"block_analysis": 1}})
        return json.dumps(response)

    monkeypatch.setattr(server, "_send_and_receive", send)
    assert json.loads(call(server.analyze_block_reculviely, mode=mode, options={}, expected_model_path=model)) == response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0},
                        {"type": "analyze_block_reculviely", "mode": mode, "options": {}, "expected_model_path": model}]


@pytest.mark.parametrize("arguments", [
    {"mode": "execute"}, {"mode": "sections"}, {"mode": "vertical-probe"}, {"mode": "joint-pairs"}, {"options": []}, {"expected_model_path": ""},
    {"options": {"sample": float("nan")}}, {"options": {"value": "x" * 262144}},
])
def test_bad_mode_requests_never_reach_the_bridge(server, monkeypatch, arguments):
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected bridge call"))
    request = dict(mode="outline", options={}, expected_model_path="C:\\fixture\\model.3dm")
    request.update(arguments)
    assert json.loads(call(server.analyze_block_reculviely, **request))["error_code"] == "invalid_arguments"


def test_mode_preserves_context_error_without_sending_geometry_query(server, monkeypatch):
    requests = []
    response = json.dumps({"status": "error", "error_code": "no_document",
                           "message": "No active Rhino document.", "warnings": []}, indent=2)

    def send(payload):
        requests.append(json.loads(payload))
        return response

    monkeypatch.setattr(server, "_send_and_receive", send)
    assert call(server.analyze_block_reculviely, mode="outline", options={},
                expected_model_path="C:\\fixture\\model.3dm") == response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]


@pytest.mark.parametrize("context", [None, [], {}, {"status": "pending"}])
def test_malformed_context_is_a_bridge_error_without_sending_mode(server, monkeypatch, context):
    requests = []

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps(context)

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.analyze_block_reculviely, mode="outline", options={}, expected_model_path="C:\\fixture\\model.3dm")
    assert json.loads(result)["error_code"] == "bridge_error"
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]


def test_old_bridge_never_receives_an_unknown_mode_type(server, monkeypatch):
    requests = []

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "document": {"path": "C:\\fixture\\model.3dm"}})

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.analyze_block_reculviely, mode="outline", options={}, expected_model_path="C:\\fixture\\model.3dm")
    assert json.loads(result)["error_code"] == "unsupported_block_analysis"
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]
