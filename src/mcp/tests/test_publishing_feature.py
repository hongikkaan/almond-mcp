"""Publishing contracts exercised without a Rhino connection or network posts."""

import asyncio
import hashlib
import io
import json
import socket
from pathlib import Path
from types import SimpleNamespace
import urllib.error

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.publishing import tools


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Publishing feature tests must not access the network")
    monkeypatch.setattr(tools.urllib.request, "urlopen", forbidden)


@pytest.fixture
def feature(tmp_path, monkeypatch):
    monkeypatch.setattr(tools.tempfile, "gettempdir", lambda: str(tmp_path))
    context = SimpleNamespace(CHESTNUT_URL="https://initial.invalid")
    mcp = FastMCP("Publishing fixture")
    exported = tools.register(mcp, context)
    vars(context).update(exported)
    return context, mcp


def fake_export(context, *, result=None, error=None):
    calls = []
    def send(payload, timeout):
        request = json.loads(payload)
        calls.append((request, timeout))
        Path(request["output_path"]).write_bytes(b"glTF-test")
        if error is not None:
            raise error
        return json.dumps(result if result is not None else {
            "status": "success", "document_path": "C:/models/test.3dm",
            "document_serial": 17, "object_guids": ["b", "a"],
            "units": "Millimeters", "bounds": {"min": [0, 0, 0], "max": [10, 20, 30]},
        })
    context._send_and_receive = send
    return calls


def fake_post(context, *, result=None, error=None):
    calls = []
    def post(url, fields, path):
        calls.append((url, json.loads(fields["metadata"]), Path(path).read_bytes()))
        if error is not None:
            raise error
        return result if result is not None else {"success": True, "updated": True, "assetId": "linked"}
    context._post_multipart = post
    return calls


def assert_cleaned(calls):
    assert calls
    assert all(not Path(request["output_path"]).exists() for request, _ in calls)


def test_fastmcp_registration_schema_and_call_time_sender(feature):
    context, mcp = feature
    async def run():
        async with Client(mcp) as client:
            registered = {tool.name: tool for tool in await client.list_tools()}
            assert set(registered) == {"publish_to_chestnut", "publish_objects_to_chestnut"}
            simple = registered["publish_to_chestnut"]
            assert simple.input_schema["required"] == ["guids", "asset_name"]
            assert set(simple.input_schema["properties"]) == {"guids", "asset_name", "behavior", "asset_id"}
            assert simple.input_schema["properties"]["behavior"]["default"] == "auto"
            advanced = registered["publish_objects_to_chestnut"].input_schema
            assert set(advanced["properties"]) == {
                "guids", "asset_name", "asset_id", "body_type", "collider", "preserve_scale", "mass",
            }
            assert advanced["properties"]["preserve_scale"]["default"] is True
            assert advanced["properties"]["mass"]["default"] == 0.0
            assert "safe semantic defaults" in simple.description
            calls = fake_export(context)
            posts = fake_post(context)
            context.CHESTNUT_URL = "https://rebound.invalid"
            await client.call_tool("publish_to_chestnut", {"guids": ["a"], "asset_name": "House"})
            assert posts[0][0] == "https://rebound.invalid/api/props/upsert"
            assert posts[0][1]["bodyType"] == "static"
            assert_cleaned(calls)
    asyncio.run(run())


def test_export_metadata_stable_identity_and_late_helper_binding(feature):
    context, _ = feature
    calls = fake_export(context)
    posts = fake_post(context)
    context.CHESTNUT_URL = "https://current.invalid"
    context._slug = lambda name: "patched-slug"
    result = json.loads(context.publish_objects_to_chestnut(
        ["a", "b"], "  Oak Chair  ", body_type="DYNAMIC", collider="CONVEX", preserve_scale=False,
    ))
    assert result == {"status": "success", "chestnut_url": "https://current.invalid",
                      "success": True, "updated": True, "assetId": "linked"}
    assert calls[0][0]["type"] == "export_glb"
    assert calls[0][0]["guids"] == ["a", "b"]
    assert calls[0][1] == 90.0
    url, metadata, glb = posts[0]
    digest = hashlib.sha256(b"C:/models/test.3dm|a|b").hexdigest()[:12]
    assert url == "https://current.invalid/api/props/upsert"
    assert metadata == {
        "assetId": f"patched-slug-{digest}", "name": "Oak Chair", "preserveScale": False,
        "bodyType": "dynamic", "collider": "convex", "mass": 1.0, "units": "Millimeters",
        "axisConvention": "glTF Y-up", "source": {
            "application": "Rhino", "documentPath": "C:/models/test.3dm", "documentSerial": 17,
            "objectGuids": ["b", "a"], "sourceId": f"rhino:{digest}",
        }, "bounds": {"min": [0, 0, 0], "max": [10, 20, 30]},
    }
    assert glb == b"glTF-test"
    assert_cleaned(calls)


@pytest.mark.parametrize(("behavior", "name", "body", "mass"), [
    ("auto", "Canopy pavilion", "static", 0.0), ("auto", "Chair", "dynamic", 1.0),
    (" architecture ", "Chair", "static", 0.0), ("object", "Wall", "dynamic", 1.0),
    ("ANIMATED", "Door", "kinematic", 0.0),
])
def test_semantic_presets_use_current_public_binding(feature, behavior, name, body, mass):
    context, _ = feature
    received = []
    context.publish_objects_to_chestnut = lambda **kwargs: received.append(kwargs) or "patched-result"
    assert context.publish_to_chestnut(["id"], name, behavior, "stable") == "patched-result"
    assert received == [{"guids": ["id"], "asset_name": name, "asset_id": "stable",
                         "body_type": body, "collider": "box", "preserve_scale": True, "mass": mass}]


@pytest.mark.parametrize("kwargs", [
    {"guids": []}, {"asset_name": "  "}, {"body_type": "invalid"},
    {"collider": "invalid"}, {"mass": -1},
])
def test_invalid_inputs_do_not_export(feature, kwargs):
    context, _ = feature
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid publishing input reached the bridge")
    context._send_and_receive = forbidden
    args = {"guids": ["a"], "asset_name": "Chair", **kwargs}
    assert json.loads(context.publish_objects_to_chestnut(**args))["status"] == "error"
    assert json.loads(context.publish_to_chestnut(["a"], "Chair", "invalid"))["status"] == "error"


@pytest.mark.parametrize(("error", "message"), [
    (ConnectionRefusedError(), "Rhino bridge is unavailable. Start RhinoAlmondBridge first."),
    (socket.timeout(), "Rhino GLB export timed out."),
    (RuntimeError("unavailable"), "unavailable"),
])
def test_export_failures_clean_up_without_retry(feature, error, message):
    context, _ = feature
    calls = fake_export(context, error=error)
    assert json.loads(context.publish_objects_to_chestnut(["a"], "Chair"))["message"] == message
    assert len(calls) == 1
    assert_cleaned(calls)


def test_export_rejection_invalid_id_and_post_failure_clean_up(feature):
    context, _ = feature
    calls = fake_export(context, result={"status": "error", "message": "not exported"})
    assert json.loads(context.publish_objects_to_chestnut(["a"], "Chair")) == {
        "status": "error", "message": "not exported",
    }
    assert_cleaned(calls)
    calls = fake_export(context)
    assert "asset_id must contain" in json.loads(context.publish_objects_to_chestnut(
        ["a"], "Chair", asset_id="unsafe/id",
    ))["message"]
    assert_cleaned(calls)
    for post_result, error, message in [
        ({"success": False, "error": "rejected"}, None, "rejected"),
        (None, RuntimeError("upload failed"), "upload failed"),
    ]:
        calls = fake_export(context)
        posts = fake_post(context, result=post_result, error=error)
        assert json.loads(context.publish_objects_to_chestnut(["a"], "Chair"))["message"] == message
        assert len(posts) == 1
        assert_cleaned(calls)


def test_register_keeps_server_contexts_separate():
    contexts = []
    for number in (1, 2):
        context = SimpleNamespace(CHESTNUT_URL=f"https://server-{number}.invalid")
        vars(context).update(tools.register(FastMCP(f"Server {number}"), context))
        context.publish_objects_to_chestnut = lambda _number=number, **kwargs: str(_number)
        contexts.append(context)
    assert contexts[0].publish_to_chestnut(["a"], "Chair") == "1"
    assert contexts[1].publish_to_chestnut(["a"], "Chair") == "2"
    assert contexts[0]._slug("!  WALL_ 12") == "wall-12"
    assert contexts[0]._slug("!") == "rhino-asset"
    assert len(contexts[0]._slug("a" * 80)) == 48


def test_multipart_bytes_timeout_and_http_error(feature, tmp_path, monkeypatch):
    context, _ = feature
    glb = tmp_path / "chair.glb"
    glb.write_bytes(b"glTF\x00\xff")
    requests = []
    def open_request(request, timeout):
        requests.append((request, timeout))
        return io.BytesIO(b'{"success":true}')
    monkeypatch.setattr(tools.urllib.request, "urlopen", open_request)
    assert context._post_multipart("https://fake.invalid/upsert", {"metadata": "한글"}, str(glb)) == {"success": True}
    request, timeout = requests[0]
    boundary = request.get_header("Content-type").split("boundary=", 1)[1]
    expected = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n'.encode()
        + "한글".encode() + b"\r\n"
        + f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="chair.glb"\r\n'.encode()
        + b"Content-Type: model/gltf-binary\r\n\r\nglTF\x00\xff\r\n"
        + f"--{boundary}--\r\n".encode()
    )
    assert request.get_method() == "POST"
    assert request.data == expected
    assert timeout == 90
    def rejected(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 409, "Conflict", {}, io.BytesIO(b"bad \xff"))
    monkeypatch.setattr(tools.urllib.request, "urlopen", rejected)
    with pytest.raises(RuntimeError, match="Chestnut returned HTTP 409: bad "):
        context._post_multipart("https://fake.invalid/upsert", {}, str(glb))
