"""Run the native request handler and public capture tool with a synthetic document and raster."""
import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import FastMCP
from PIL import Image

from almond_mcp.features.context.tools import register
from test_stage2_native_feedback import build_host


ORDINARY = str(UUID(int=1))
BLOCK = str(UUID(int=2))
HIDDEN_BLOCK = str(UUID(int=3))
MISSING = str(UUID(int=4))


@pytest.fixture(scope="module")
def native_capture(tmp_path_factory):
    tests = Path(__file__).parent
    source = (tests.parent / "features/context/native/InspectionCapture.cs").read_text(encoding="utf-8")
    # The public Handle method owns both scope classification and sheet-level error/partial success.
    # Replace only viewport/raster operations, outside Handle, so both decisions run in production code.
    handler = source[source.index("        const int MaxPixels"):source.index("        static Bitmap Capture(")]
    helpers = source[source.index("        static string Text("):source.index("        static void DrawCaption(")]
    errors = source[source.index("        static void TileError("):source.rindex("    }")]
    harness = (tests / "inspection_capture_host/Fixture.cs").read_text(encoding="utf-8")
    return build_host(tmp_path_factory.mktemp("capture"), harness.replace("// CAPTURE_HANDLER", handler + helpers + errors), [])


@pytest.fixture
def capture(native_capture, tmp_path, monkeypatch):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", "tmp/capture")

    def send(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"inspection_capture": 1, "inspection_shared_scope": 1}})
        assert request["type"] == "capture_rhino_inspection"
        png = io.BytesIO()
        Image.new("RGB", (128 * len(request["views"]), 128)).save(png, format="PNG")
        return json.dumps(native_capture(json.dumps({
            "request": request, "raster": base64.b64encode(png.getvalue()).decode("ascii"),
        }))["response"])

    tool = register(FastMCP("block-scope"), SimpleNamespace(_send_and_receive=send))["capture_rhino_inspection"]

    def invoke(views, **scope):
        return tool(views=views, width=128, height=128, columns=len(views),
                    expected_model_path=r"C:\offline\inspection.3dm", **scope)
    return invoke


@pytest.mark.parametrize(("change", "scans"), [
    (None, 2), ("hide_visible", 2), ("remove_hidden", 2), ("mark_modified", 1),
])
def test_capture_rechecks_the_document_once(native_capture, change, scans):
    result = native_capture(json.dumps({
        "request": {"type": "capture_rhino_inspection", "views": [{}]},
        "raster": "AA==", "change": change,
    }))
    assert result["scans"] == scans
    response = result["response"]
    if change is None:
        assert response["status"] == "success" and "image" in response
    else:
        assert response["error_code"] == "observation_state_changed"
        assert "image" not in response


def test_shared_mixed_scope_identifies_the_block_and_returns_no_png(capture, tmp_path):
    result = capture([{}, {}], object_ids=[ORDINARY, BLOCK])
    assert result.is_error
    error = result.structured_content
    assert error["error_code"] == "unsupported_block_filter"
    assert "object_ids" in error["message"] and "views[" not in error["message"]
    assert BLOCK in error["message"] and ORDINARY not in error["message"]
    assert "image_file" not in error
    assert all(item.type != "image" for item in result.content)
    assert not list(tmp_path.rglob("*.png"))


def test_repeated_block_in_individual_tiles_fails_the_whole_capture(capture, tmp_path):
    result = capture([{}, {"object_ids": [BLOCK, HIDDEN_BLOCK, MISSING]}, {"object_ids": [ORDINARY, BLOCK]}])
    assert result.is_error
    error = result.structured_content
    assert error["error_code"] == "unsupported_block_filter"
    message = error["message"]
    assert "views[0]" not in message and ORDINARY not in message and MISSING not in message
    first = message.index("views[1].object_ids")
    second = message.index("views[2].object_ids")
    assert BLOCK in message[first:second] and HIDDEN_BLOCK in message[first:second]
    assert BLOCK in message[second:] and HIDDEN_BLOCK not in message[second:]
    assert "image_file" not in error
    assert all(item.type != "image" for item in result.content)
    assert not list(tmp_path.rglob("*.png"))


def test_visible_block_in_unfiltered_tile_and_other_tile_error_keep_partial_png(capture, tmp_path):
    result = capture([{}, {"object_ids": [MISSING]}])
    assert not result.is_error
    sheet = result.structured_content
    assert sheet["complete"] is False
    first, second = sheet["tiles"]
    assert first["status"] == "success" and BLOCK in first["scope"]["eligible_object_ids"]
    assert second["error_code"] == "scope_unavailable"
    assert any(item.type == "image" for item in result.content)
    assert sheet["image_file"]["status"] == "saved"
    assert len(list(tmp_path.rglob("*.png"))) == 1
