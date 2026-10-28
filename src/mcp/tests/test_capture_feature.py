"""Capture factory contracts with bounded senders and no live Rhino calls."""
import inspect
import json
from types import SimpleNamespace

import pytest

from almond_mcp.features.capture import conditioning, tools


class FakeMCP:
    def __init__(self):
        self.registered = {}
        self.options = {}

    def tool(self, **options):
        def decorate(function):
            self.registered[function.__name__] = function
            self.options[function.__name__] = options
            return function
        return decorate


def register(sender):
    mcp = FakeMCP()
    context = SimpleNamespace(_send_and_receive=sender)
    exported = tools.register(mcp, context)
    return exported["capture_conditioning_pass"], context, mcp, exported


def test_factory_keeps_registration_and_public_signature():
    tool, _, mcp, exported = register(None)
    assert exported == mcp.registered == {"capture_conditioning_pass": tool}
    assert mcp.options == {"capture_conditioning_pass": {}}
    signature = inspect.signature(tool)
    assert list(signature.parameters) == [
        "shot", "out_dir", "width", "height", "passes", "fps", "chunk",
        "rgb_mode", "edge_mode", "invert_depth",
    ]
    assert [p.default for p in signature.parameters.values()][2:] == [
        832, 480, "rgb,edge,depth", 16, 16, "Rendered", "Technical", False,
    ]
    assert signature.return_annotation is str
    from almond_mcp.instruction_text import read_instruction
    assert "building0.camera/0.1" not in tool.__doc__
    assert "building0.camera/0.1" in read_instruction(
        inspect.getsourcefile(tool), 'capture_conditioning_pass')


def test_canonical_module_patch_and_live_sender_binding_are_preserved(monkeypatch):
    assert tools.conditioning is conditioning
    first, replacement, other = object(), object(), object()
    calls = []

    def fake_capture(frames, out_dir, sender, **options):
        calls.append((frames, out_dir, sender, options))
        return {"status": "success"}

    monkeypatch.setattr(conditioning, "capture_conditioning_pass", fake_capture)
    shot = '{"type":"orbit","center":[0,0,0],"radius":1,"height":2,"frames":1}'
    tool, context, _, _ = register(first)
    independent, _, _, _ = register(other)
    tool(shot, "first")
    context._send_and_receive = replacement
    assert json.loads(tool(shot, "second", passes=" depth, ,rgb ")) == {"status": "success"}
    independent(shot, "third")
    assert [call[2] for call in calls] == [first, replacement, other]
    assert calls[1][3] == {
        "width": 832, "height": 480, "passes": ("depth", "rgb"),
        "rgb_mode": "Rendered", "edge_mode": "Technical", "invert_depth": False,
        "chunk": 16, "fps": 16,
    }


@pytest.mark.parametrize("shot", ["{", '{"type":"unknown"}', '{"type":"orbit"}'])
def test_bad_shot_returns_existing_error_without_sender(shot):
    def unexpected_send(*args):
        pytest.fail("invalid input must not send a Rhino request")

    tool, _, _, _ = register(unexpected_send)
    result = json.loads(tool(shot, "unused"))
    assert result["status"] == "error"
    assert result["message"].startswith("Bad shot description: ")


@pytest.mark.parametrize("error, message", [
    (ConnectionRefusedError(), "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"),
    (RuntimeError("capture failed"), "Conditioning pass failed: capture failed"),
])
def test_capture_failures_keep_existing_json_contract(monkeypatch, error, message):
    def fail_capture(*args, **kwargs):
        raise error

    monkeypatch.setattr(conditioning, "capture_conditioning_pass", fail_capture)
    tool, _, _, _ = register(None)
    shot = '{"type":"track","cam0":[0,0,0],"cam1":[1,0,0],"target0":[0,1,0],"target1":[1,1,0],"frames":1}'
    assert json.loads(tool(shot, "unused")) == {"status": "error", "message": message}


def test_extracted_tool_runs_capture_receipts_chunks_and_restore(tmp_path, monkeypatch):
    calls = []
    doc_info = {
        "document": "capture-test.3dm", "units": "Millimeters", "camera": [4, 5, 6],
        "target": [1, 2, 3], "lens_mm": 28,
    }

    def fake_send(payload, timeout):
        request = json.loads(payload)
        assert request["type"] == "execute"
        assert "__" not in request["script"]
        calls.append((request, timeout))
        if '"doc.json"' in request["script"]:
            (tmp_path / "doc.json").write_text(json.dumps(doc_info), encoding="utf-8")
        return json.dumps({"status": "success", "guids": []})

    monkeypatch.setattr(conditioning, "assemble_video", lambda *args: False)
    tool, _, _, _ = register(fake_send)
    shot = '{"type":"orbit","center":[0,0,0],"radius":10,"height":5,"frames":5}'
    summary = json.loads(tool(shot, str(tmp_path), width=640, height=360,
                              passes="rgb,depth", chunk=2, fps=24, invert_depth=True))
    assert summary["status"] == "success"
    assert summary["frames_requested"] == summary["frames_captured"] == 5
    assert summary["resolution"] == [640, 360]
    assert summary["passes"] == ["rgb", "depth"]
    assert summary["fps"] == 24
    assert summary["videos"] == {"rgb": None, "depth": None}
    assert summary["document"]["document"] == "capture-test.3dm"
    assert [timeout for _, timeout in calls] == [90.0, 320.0, 320.0, 320.0, 60.0]
    assert [request["timeout_s"] for request, _ in calls] == [60.0, 300.0, 300.0, 300.0, 30.0]
    assert "new Point3d(1.0, 2.0, 3.0), new Point3d(4.0, 5.0, 6.0)" in calls[-1][0]["script"]
    receipt = json.loads((tmp_path / "camera.json").read_text(encoding="utf-8"))
    assert receipt["frame_count"] == 5
    assert receipt["depth"]["near_is_bright"] is False
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == summary
