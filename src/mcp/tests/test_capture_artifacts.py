"""Public capture tools retain their PNG content when saving owned files."""

import base64
import asyncio
import pytest
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from fastmcp import FastMCP

from almond_mcp.features.context import tools as context_tools


def test_capture_annotations_disclose_file_writes_without_claiming_destructive_model_edits():
    server = FastMCP("capture-effects-test")
    context_tools.register(server, SimpleNamespace(_send_and_receive=None))
    tools = {tool.name: tool.to_mcp_tool().model_dump(mode="json", by_alias=True)
             for tool in asyncio.run(server.list_tools())}
    for name in ("get_current_viewcapture", "get_defined_viewcapture", "capture_rhino_inspection"):
        assert tools[name]["annotations"]["readOnlyHint"] is False
        assert tools[name]["annotations"]["destructiveHint"] is False
    for name in ("get_rhino_context", "get_objects"):
        assert tools[name]["annotations"]["readOnlyHint"] is True


class RegisteredTools:
    def __init__(self):
        self.tools = {}

    def tool(self, **_options):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


def _tools(send):
    mcp = RegisteredTools()
    def capable_send(payload):
        if json.loads(payload)["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"view_capture": 1, "inspection_capture": 1}})
        return send(payload)
    context_tools.register(mcp, SimpleNamespace(_send_and_receive=capable_send))
    return mcp.tools


def _png(width=30, height=30):
    output = io.BytesIO()
    Image.new("RGB", (width, height), (34, 95, 180)).save(output, format="PNG")
    return output.getvalue()


def _native_image(raw):
    return {"mime_type": "image/png", "data": base64.b64encode(raw).decode("ascii"),
            "width": 30, "height": 30, "source_width": 40, "source_height": 40}


def _owned(monkeypatch, root, *, plan="tmp/design"):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(root))
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", plan)
    monkeypatch.setenv("ALMOND_CAPTURE_ROOT", str(root / ".almond" / "tmp" / "python" / ("a" * 32) / "captures"))
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(root / "model.3dm"))


def _image(result):
    return next(content for content in result.content if content.type == "image")


def test_viewport_public_tool_saves_identical_png_in_bound_plan_artifacts(tmp_path, monkeypatch):
    _owned(monkeypatch, tmp_path)
    raw = _png()
    tools = _tools(lambda _request: json.dumps({"status": "success", "image": _native_image(raw), "warnings": []}))

    response = tools["get_current_viewcapture"]()

    assert not response.is_error
    assert base64.b64decode(_image(response).data) == raw
    metadata = response.structured_content["image_file"]
    assert metadata["status"] == "saved"
    assert metadata["lifetime"] == "plan"
    assert metadata["bytes"] == len(raw)
    assert metadata["sha256"] == hashlib.sha256(raw).hexdigest()
    assert Path(metadata["path"]).is_absolute() is False
    assert Path(tmp_path / metadata["path"]).read_bytes() == raw
    assert metadata["path"].startswith("tmp/design/captures/")


def test_inspection_public_tool_keeps_png_and_saves_in_connection_owned_scratch(tmp_path, monkeypatch):
    _owned(monkeypatch, tmp_path, plan="")
    raw = _png(128, 128)

    def send(encoded_request):
        request = json.loads(encoded_request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"inspection_capture": 1}})
        assert request["type"] == "capture_rhino_inspection"
        return json.dumps({"status": "success", "complete": True, "columns": 1, "rows": 1,
                           "tiles": [{"index": 0, "status": "success", "direction": "top",
                                      "scope": {"complete": True}}],
                           "image": {"mime_type": "image/png", "data": base64.b64encode(raw).decode("ascii"),
                                     "width": 128, "height": 128}})

    response = _tools(send)["capture_rhino_inspection"]([{"direction": "top"}], width=128, height=128)

    assert not response.is_error
    assert base64.b64decode(_image(response).data) == raw
    image_file = response.structured_content["image_file"]
    assert image_file["status"] == "saved"
    assert image_file["lifetime"] == "connection"
    assert image_file["path"].startswith(f".almond/tmp/python/{'a' * 32}/captures/")
    assert (tmp_path / image_file["path"]).read_bytes() == raw


def test_storage_failure_keeps_viewport_png_and_reports_file_error(tmp_path, monkeypatch):
    _owned(monkeypatch, tmp_path)
    occupied = tmp_path / "tmp" / "design" / "captures"
    occupied.parent.mkdir(parents=True)
    occupied.write_bytes(b"untouched")
    raw = _png()
    response = _tools(lambda _: json.dumps({"status": "success", "image": _native_image(raw)}))[
        "get_current_viewcapture"]()

    assert not response.is_error
    assert base64.b64decode(_image(response).data) == raw
    error = response.structured_content["image_file"]
    assert error["status"] == "error" and error["error_code"] == "capture_file_write_failed"
    assert error["bytes"] == len(raw) and error["sha256"] == hashlib.sha256(raw).hexdigest()
    assert "path" not in error
    assert occupied.read_bytes() == b"untouched"


def test_invalid_managed_path_cannot_write_outside_project(tmp_path, monkeypatch):
    _owned(monkeypatch, tmp_path, plan="../outside")
    raw = _png()
    response = _tools(lambda _: json.dumps({"status": "success", "image": _native_image(raw)}))[
        "get_current_viewcapture"]()

    assert not response.is_error
    assert base64.b64decode(_image(response).data) == raw
    assert response.structured_content["image_file"]["status"] == "error"
    assert not (tmp_path.parent / "outside").exists()


def test_missing_connection_binding_never_saves_into_random_working_directory(tmp_path, monkeypatch):
    _owned(monkeypatch, tmp_path, plan="")
    monkeypatch.setenv("ALMOND_CAPTURE_ROOT", str(tmp_path.parent / "foreign" / "captures"))
    raw = _png()
    response = _tools(lambda _: json.dumps({"status": "success", "image": _native_image(raw)}))[
        "get_current_viewcapture"]()

    assert not response.is_error
    assert response.structured_content["image_file"]["status"] == "error"
    assert base64.b64decode(_image(response).data) == raw
    assert not (tmp_path.parent / "foreign").exists()


def test_capture_public_tool_through_owned_runtime_preserves_connection_lifetime(tmp_path, monkeypatch):
    """The public tool receives the current connection's private output binding."""
    from project import connection_paths
    from shared_store import ProjectRuntime

    model = tmp_path / "model.3dm"
    model.touch()
    token = "b" * 32
    locations = connection_paths(model, "A", token, create=True)
    (Path(locations["session_dir"]) / "worker.json").write_text(
        json.dumps({"pid": 1, "process_start_ticks": "1"}), encoding="utf-8")
    runtime = ProjectRuntime(SimpleNamespace(token=token), {}, locations, check_owner=False)
    runtime.validate = lambda: None  # Only live binding attestation is excluded in this offline fixture.
    runtime.workspace = SimpleNamespace(current=lambda: {"artifact_dir": ""})
    _owned(monkeypatch, tmp_path, plan="")
    foreign = str(tmp_path / "untrusted")
    monkeypatch.setenv("ALMOND_CAPTURE_ROOT", foreign)
    raw = _png()
    capture = _tools(lambda _: json.dumps({"status": "success", "image": _native_image(raw)}))[
        "get_current_viewcapture"]

    class Message:
        name = "get_current_viewcapture"
        arguments = {}

        def model_copy(self, update):
            return self

    class Context:
        message = Message()

        def copy(self, **_updates):
            return self

    async def call_next(_context):
        return capture()

    result = asyncio.run(runtime.on_call_tool(Context(), call_next))

    assert not result.is_error
    assert base64.b64decode(_image(result).data) == raw
    stored = result.structured_content["image_file"]
    assert stored["path"].startswith(f".almond/tmp/python/{token}/captures/")
    assert (tmp_path / stored["path"]).read_bytes() == raw
    assert os.environ["ALMOND_CAPTURE_ROOT"] == foreign
    assert not (tmp_path / "untrusted").exists()
    assert not (Path(locations["session_dir"]) / "artifact-write.json").exists()


@pytest.mark.parametrize("blocker", ["unconfirmed", "legacy_folder"])
def test_capture_still_returns_png_when_persistence_is_blocked(tmp_path, monkeypatch, blocker):
    from project import connection_paths
    import shared_store

    model = tmp_path / "model.3dm"
    model.touch()
    token = "c" * 32
    locations = connection_paths(model, "A", token, create=True)
    (Path(locations["session_dir"]) / "worker.json").write_text(
        json.dumps({"pid": 1, "process_start_ticks": "1"}), encoding="utf-8")
    runtime = shared_store.ProjectRuntime(SimpleNamespace(token=token), {}, locations, check_owner=False)
    runtime.validate = lambda: None  # Do not contact a live Rhino in this offline test.
    runtime.workspace = SimpleNamespace(current=lambda: {"artifact_dir": ""})
    _owned(monkeypatch, tmp_path, plan="")

    def unavailable(_storage):
        raise RuntimeError("Previous artifact write has unconfirmed native completion")

    if blocker == "unconfirmed":
        monkeypatch.setattr(shared_store, "validate_artifact_writers", unavailable)
    else:
        def legacy_path():
            raise ValueError("Plan artifacts must be under .almond/produced")
        runtime.workspace = SimpleNamespace(current=lambda: {"artifact_dir": "tmp/legacy"},
                                            artifact_path=legacy_path)
    raw = _png()
    capture = _tools(lambda _: json.dumps({"status": "success", "image": _native_image(raw)}))[
        "get_current_viewcapture"]

    class Message:
        name = "get_current_viewcapture"
        arguments = {}

        def model_copy(self, update):
            return self

    class Context:
        message = Message()

        def copy(self, **_updates):
            return self

    async def call_next(_context):
        return capture()

    result = asyncio.run(runtime.on_call_tool(Context(), call_next))

    assert not result.is_error
    assert base64.b64decode(_image(result).data) == raw
    file_info = result.structured_content["image_file"]
    assert file_info["status"] == "error"
    assert file_info["error_code"] == "capture_file_write_failed"
    assert not (tmp_path / file_info.get("path", "missing.png")).exists()
