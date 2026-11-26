import base64
import io
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import FastMCP
from PIL import Image

from almond_mcp.features.context import tools as context_tools
from almond_mcp.features.modeling import tools as modeling_tools


FIRST, SECOND = (str(UUID(int=n)) for n in (1, 2))


def with_bridge(register, bridge):
    server = FastMCP("Bound model workflow")
    register(server, SimpleNamespace(_send_and_receive=bridge))
    return server


def test_stale_intersection_count(tmp_path, monkeypatch, call_tool):
    bound_model = str(tmp_path / "Atrium.3dm")
    monkeypatch.setenv("ALMOND_MODEL_PATH", bound_model)
    requested_cursors = []

    def bridge(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"intersection_queries": 1}})
        assert request["expected_model_path"] == bound_model
        requested_cursors.append(request["cursor"])
        if request["cursor"] == "page-2":
            return json.dumps({"status": "error", "error_code": "stale_scope", "message": "Geometry changed"})
        return json.dumps({"status": "success", "pairs": [{"overlap": {"status": "positive_volume"}}],
                           "unsupported_objects": [], "pagination_complete": False, "next_cursor": "page-2"})

    server = with_bridge(context_tools.register, bridge)
    result, evidence = call_tool(server, "intersect_01-find", object_ids=[FIRST, SECOND])
    assert result.is_error and evidence["error_code"] == "stale_scope"
    assert evidence["assessment"] == "incomplete" and "intersections" not in evidence
    assert requested_cursors == ["", "page-2"]


def test_invalid_scope(call_tool):
    attempted = []
    server = with_bridge(context_tools.register, attempted.append)
    result, evidence = call_tool(server, "inspect_02-get_objects", scope="wall-selection")
    assert result.is_error and evidence["error_code"] == "invalid_arguments"
    assert attempted == []


def test_lost_section_reply(tmp_path, monkeypatch, call_tool):
    model = str(tmp_path / "Courtyard.3dm")
    monkeypatch.setenv("ALMOND_MODEL_PATH", model)
    received = []

    def bridge(raw, **_options):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"plan_section": 4}})
        received.append(request)
        raise TimeoutError("Lost reply while drawing was in progress")

    server = with_bridge(modeling_tools.register, bridge)
    reply, evidence = call_tool(server, "drawing_06-generate_plan_section",
                               operation="Create", clipping_ids=[FIRST, SECOND])
    assert reply.is_error and evidence["requires_reconciliation"]
    assert evidence["mutation_state"] == "unknown"
    assert evidence["unconfirmed_clipping_ids"] == [FIRST, SECOND]
    attempt, = received
    assert attempt["type"] == "plan_section" and attempt["clipping_ids"] == [FIRST, SECOND]
    assert attempt["expected_model_path"] == model


@pytest.mark.parametrize("destination", ["available", "blocked"])
def test_capture_artifact_receipt(tmp_path, monkeypatch, call_tool, destination):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", "design")
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(tmp_path / "Atrium.3dm"))
    artifacts = tmp_path / "design"
    artifacts.mkdir()
    capture_directory = artifacts / "captures"
    if destination == "blocked":
        capture_directory.write_bytes(b"Keep existing data")
    raster = io.BytesIO()
    Image.new("RGB", (30, 30), color="black").save(raster, format="PNG")
    png = raster.getvalue()

    def bridge(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"view_capture": 1}})
        assert request["type"] == "get_current_viewcapture"
        return json.dumps({"status": "success", "image": {
            "mime_type": "image/png", "data": base64.b64encode(png).decode(),
            "width": 30, "height": 30, "source_width": 40, "source_height": 40,
        }})

    server = with_bridge(context_tools.register, bridge)
    result, _ = call_tool(server, "capture_03-current_view")
    assert not result.is_error
    image, = [content for content in result.content if content.type == "image"]
    assert base64.b64decode(image.data) == png
    receipt = result.structured_content["image_file"]
    if destination == "blocked":
        assert receipt["status"] == "error" and receipt["error_code"] == "capture_file_write_failed"
        assert "path" not in receipt and capture_directory.read_bytes() == b"Keep existing data"
        return

    assert receipt["status"] == "saved" and receipt["lifetime"] == "plan"
    saved, = capture_directory.iterdir()
    assert saved == tmp_path / receipt["path"] and saved.read_bytes() == png
