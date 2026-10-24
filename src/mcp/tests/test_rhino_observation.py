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
    source = Path(__file__).resolve().parents[3] / "src/mcp/almond_mcp/server.py"
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


def capture_response():
    output = io.BytesIO()
    Image.new("RGB", (80, 40), (40, 80, 120)).save(output, format="JPEG")
    return {
        "status": "success", "document": {"name": "fixture.3dm", "runtime_serial_number": 7},
        "viewport": {"id": "fixture-view", "name": "Perspective", "width": 1600, "height": 800},
        "warnings": [],
        "image": {"mime_type": "image/jpeg", "width": 80, "height": 40,
                  "data": base64.b64encode(output.getvalue()).decode("ascii")},
    }


def test_context_sends_only_a_fixed_live_query(server, monkeypatch):
    requests = []
    response = {"status": "success", "document": {"runtime_serial_number": 42},
                "selection": {"total": 5, "returned": 2, "truncated": True},
                "viewport": None, "warnings": ["No active view."]}

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps(response)

    monkeypatch.setattr(server, "_send_and_receive", send)
    assert json.loads(call(server.get_rhino_context, selection_limit=2)) == response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 2}]


@pytest.mark.parametrize("limit", [-1, 201, True, "5", 2.5])
def test_context_rejects_bad_limits_before_bridge(server, monkeypatch, limit):
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected bridge call"))
    result = json.loads(call(server.get_rhino_context, selection_limit=limit))
    assert result["error_code"] == "invalid_arguments"


@pytest.mark.parametrize("arguments", [{"max_width": 63}, {"max_height": 2049},
                                        {"max_width": True}, {"max_height": "960"}])
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
    ("get_rhino_viewport_image", {"max_width": True}),
    ("get_rhino_viewport_image", {"max_height": "960"}),
    ("get_rhino_viewport_image", {"max_width": 1280.0}),
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
            result = await client.call_tool("get_rhino_viewport_image", {"max_width": 320, "max_height": 240})
            assert not result.is_error
            assert [item.type for item in result.content] == ["text", "image"]
            assert result.content[1].data == response["image"]["data"]
            metadata = json.loads(result.content[0].text)
            assert metadata == result.structured_content
            assert metadata["document"] == response["document"]
            assert metadata["viewport"] == response["viewport"]
            assert metadata["image"]["byte_count"] == len(base64.b64decode(result.content[1].data))
            assert "data" not in metadata["image"]
            assert response["image"]["data"] not in result.content[0].text
    asyncio.run(verify())
    assert requests == [{"type": "get_rhino_viewport_image", "max_width": 320, "max_height": 240}]


@pytest.mark.parametrize("fault", ["base64", "format", "mismatched_size", "too_wide", "not_image",
                                    "oversized", "missing_image", "not_object", "empty"])
def test_invalid_capture_never_emits_an_image(server, monkeypatch, fault):
    response = capture_response()
    if fault == "base64":
        response["image"]["data"] = "!not-base64!"
    elif fault == "format":
        response["image"]["mime_type"] = "image/png"
    elif fault == "mismatched_size":
        response["image"]["width"] = 81
    elif fault == "too_wide":
        response["image"]["width"] = 2049
    elif fault == "not_image":
        response["image"]["data"] = base64.b64encode(b"no JPEG here").decode("ascii")
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




@pytest.mark.parametrize("probe", ["outline", "resolve-block", "sections", "vertical-probe", "joint-pairs"])
def test_fixed_probe_checks_capability_then_uses_native_query(server, monkeypatch, probe):
    requests = []
    model = "C:\\fixture\\model.3dm"
    response = {"status": "success", "probe": probe, "document": {"path": model}, "data": {"measured": 12}}

    def send(payload):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"fixed_probes": 1}})
        return json.dumps(response)

    monkeypatch.setattr(server, "_send_and_receive", send)
    assert json.loads(call(server.get_rhino_probe, probe=probe, options={}, expected_model_path=model)) == response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0},
                        {"type": "get_rhino_probe", "probe": probe, "options": {}, "expected_model_path": model}]


@pytest.mark.parametrize("arguments", [
    {"probe": "execute"}, {"options": []}, {"expected_model_path": ""},
    {"options": {"sample": float("nan")}}, {"options": {"value": "x" * 262144}},
])
def test_bad_probe_requests_never_reach_the_bridge(server, monkeypatch, arguments):
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected bridge call"))
    request = dict(probe="outline", options={}, expected_model_path="C:\\fixture\\model.3dm")
    request.update(arguments)
    assert json.loads(call(server.get_rhino_probe, **request))["error_code"] == "invalid_arguments"


def test_probe_preserves_context_error_without_sending_geometry_query(server, monkeypatch):
    requests = []
    response = json.dumps({"status": "error", "error_code": "no_document",
                           "message": "No active Rhino document.", "warnings": []}, indent=2)

    def send(payload):
        requests.append(json.loads(payload))
        return response

    monkeypatch.setattr(server, "_send_and_receive", send)
    assert call(server.get_rhino_probe, probe="outline", options={},
                expected_model_path="C:\\fixture\\model.3dm") == response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]


@pytest.mark.parametrize("context", [None, [], {}, {"status": "pending"}])
def test_malformed_context_is_a_bridge_error_without_sending_probe(server, monkeypatch, context):
    requests = []

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps(context)

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.get_rhino_probe, probe="outline", options={}, expected_model_path="C:\\fixture\\model.3dm")
    assert json.loads(result)["error_code"] == "bridge_error"
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]


def test_old_bridge_never_receives_an_unknown_probe_type(server, monkeypatch):
    requests = []

    def send(payload):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "document": {"path": "C:\\fixture\\model.3dm"}})

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.get_rhino_probe, probe="outline", options={}, expected_model_path="C:\\fixture\\model.3dm")
    assert json.loads(result)["error_code"] == "unsupported_probe"
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]
