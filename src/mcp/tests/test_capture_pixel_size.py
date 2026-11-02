"""Requested output pixels never require resizing the live Rhino window."""
import base64
import io
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastmcp import FastMCP
from PIL import Image

from almond_mcp.features.context.tools import register


def pixel_capture(*, capable=True, wrong_size=False):
    calls = []

    def send(raw):
        request = json.loads(raw)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"capture_output_size": 1} if capable else {}})
        width, height = request.get("width", 640), request.get("height", 480)
        if wrong_size:
            height = width
        scale = request["scale_percent"]
        actual = (width * scale // 100, height * scale // 100)
        buffer = io.BytesIO()
        Image.new("RGB", actual).save(buffer, format="PNG")
        return json.dumps({"status": "success", "image": {
            "mime_type": "image/png", "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
            "width": actual[0], "height": actual[1], "source_width": width, "source_height": height,
        }})

    capture = register(FastMCP("pixel-size-test"), SimpleNamespace(_send_and_receive=send))["get_rhino_viewport_image"]
    return capture, calls


@pytest.mark.parametrize("target", [{"view": str(uuid4())},
                                    {"target_kind": "group", "target_id": str(uuid4())},
                                    {"target_kind": "block", "target_id": str(uuid4())}])
def test_independent_output_dimensions_are_sent_as_capture_options(target):
    capture, calls = pixel_capture()
    result = capture(width=128, height=192, scale_percent=100, **target)
    assert not result.is_error
    image = next(item for item in result.content if item.type == "image")
    with Image.open(io.BytesIO(base64.b64decode(image.data))) as picture:
        assert picture.size == (128, 192)
    assert [call["type"] for call in calls] == ["get_rhino_context", "get_rhino_viewport_image"]
    assert calls[-1]["width"] == 128 and calls[-1]["height"] == 192


@pytest.mark.parametrize("arguments", [
    {"width": 128}, {"width": 128, "height": 192},
    {"width": 0, "height": 192, "scale_percent": 100},
    {"width": 4096, "height": 192, "scale_percent": 100},
    {"width": True, "height": 192, "scale_percent": 100},
    {"view": "a", "width": 128, "height": 192, "scale_percent": 100},
])
def test_invalid_or_ambiguous_pixel_requests_do_not_reach_rhino(arguments):
    capture, calls = pixel_capture()
    result = capture(**arguments)
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_arguments"
    assert calls == []


def test_explicit_pixels_require_a_capable_bridge():
    capture, calls = pixel_capture(capable=False)
    result = capture(width=128, height=192, scale_percent=100)
    assert result.is_error
    assert result.structured_content["error_code"] == "unsupported_capture_size"
    assert len(calls) == 1


def test_native_cannot_silently_return_a_different_requested_size():
    capture, calls = pixel_capture(wrong_size=True)
    result = capture(width=128, height=192, scale_percent=100)
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_capture_response"
    assert all(item.type != "image" for item in result.content)


def test_legacy_percentage_capture_needs_no_new_capability_or_options():
    capture, calls = pixel_capture(capable=False)
    result = capture(scale_percent=50)
    assert not result.is_error
    assert len(calls) == 1
    assert "width" not in calls[0] and "height" not in calls[0]
