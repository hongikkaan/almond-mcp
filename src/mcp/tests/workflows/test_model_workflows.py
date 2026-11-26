import base64
import io
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import FastMCP
from PIL import Image

from almond_mcp.features.context import tools as context_tools
from almond_mcp.features.drawings import tools as drawing_tools
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


def test_object_geometry_and_dictionary(tmp_path, monkeypatch, call_tool):
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(tmp_path / "Atrium.3dm"))
    fields = ["geometry_valid", "solid", "manifold", "volume", "user_dictionary"]
    attributes = {"values": {"source_id": "author metadata"}, "total_keys": 1, "truncated": False}
    observed = {"id": FIRST, "geometry_valid": True, "solid": True, "manifold": True, "volume": 4000,
                "user_dictionary": {"attributes": attributes}}

    def bridge(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"object_observation": 4}})
        assert request["fields"] == fields
        return json.dumps({"status": "success", "objects": [observed]})

    server = with_bridge(context_tools.register, bridge)
    reply, evidence = call_tool(server, "inspect_02-get_objects", fields=fields)
    assert not reply.is_error
    assert evidence["objects"] == [{key: observed[key] for key in fields}]


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


@pytest.mark.parametrize(
    ("native_status", "cut_status", "expected_status"),
    [("success", "completed", "success"), ("runtime_error", "unconfirmed", "error")],
)
def test_section_cut_evidence(tmp_path, monkeypatch, call_tool, native_status, cut_status, expected_status):
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(tmp_path / "Courtyard.3dm"))
    cut = {"clipping_id": FIRST, "status": cut_status, "object_ids": [SECOND]}
    drawing = {"requested": 1, "results": [cut], "status": cut_status}
    if native_status == "success":
        drawing["completed"] = 1
        cut["draw_plane"] = {"origin": [0, 0, 0], "xaxis": [1, 0, 0], "yaxis": [0, 1, 0]}

    def bridge(raw, **_options):
        if json.loads(raw)["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"plan_section": 4}})
        return json.dumps({"status": native_status, "result": drawing})

    server = with_bridge(modeling_tools.register, bridge)
    _, evidence = call_tool(server, "drawing_06-generate_plan_section", operation="Move",
                            clipping_ids=[FIRST], points={FIRST: [0, 0]})
    assert evidence["status"] == expected_status
    assert evidence["requested"] == 1 and evidence["cuts"] == [cut]
    assert "result" not in evidence
    if native_status == "success":
        assert evidence["completed"] == 1
    else:
        assert evidence["requires_reconciliation"] and evidence["unconfirmed_clipping_ids"] == [FIRST]


def test_drawing_style_print_review(call_tool):
    recipe = {"layers": [], "review_preparation": {"print_display": True}}
    server = FastMCP("Bound drawing workflow")
    drawing_tools.register(server, SimpleNamespace(
        drawing_recipe_indexer=SimpleNamespace(get={"sample": recipe}.get),
        _send_and_receive=lambda _raw, **_options: '{"status":"success","layers":[]}',
    ))
    _, style = call_tool(server, "drawing_01-apply_style", recipe_id="sample")
    assert "_Scope=_Document _Viewport=_Model" in style["print_display_review"]["macro"]


def test_material_list_details(tmp_path, call_tool):
    server = FastMCP("Bound material library")
    material = {"material_id": "oak", "name": "Oak", "category": "Wood", "roughness": 0.5}
    modeling_tools.register(server, SimpleNamespace(material_library=SimpleNamespace(
        directory=tmp_path, list=lambda **_filters: [material],
    )))
    _, summary = call_tool(server, "model_04-list_materials")
    assert summary["materials"] == [{key: material[key] for key in ("material_id", "name", "category")}]
    _, detailed = call_tool(server, "model_04-list_materials", field_groups=["display"])
    assert detailed["materials"] == [material]


def test_layout_capture_rejects_detail_labels(tmp_path, monkeypatch, call_tool):
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(tmp_path / "Atrium.3dm"))
    attempted = []
    server = with_bridge(context_tools.register, attempted.append)
    reply, evidence = call_tool(server, "capture_04-defined_view", target_kind="layout", target="A4", labels=True)
    assert reply.is_error and evidence["error_code"] == "invalid_arguments"
    assert attempted == []


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
