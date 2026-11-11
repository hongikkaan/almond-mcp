"""Split captures preserve live-view effects through image/transport failures."""
import asyncio
import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP
from PIL import Image

from almond_mcp.features.context.tools import register


def capture_tools(response=None, failure=None):
    calls = []
    def send(raw):
        request = json.loads(raw)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"view_capture": 1}})
        if failure:
            raise failure
        return json.dumps(response)
    tools = register(FastMCP("split-capture-test"), SimpleNamespace(_send_and_receive=send))
    return tools, calls


def png_response(scale=75, **metadata):
    buffer = io.BytesIO()
    pixels = 40 * scale // 100
    Image.new("RGB", (pixels, pixels), "white").save(buffer, format="PNG")
    return {"status": "success", "image": {"mime_type": "image/png",
            "data": base64.b64encode(buffer.getvalue()).decode(), "width": pixels, "height": pixels,
            "source_width": 40, "source_height": 40}, **metadata}


def invoke(tools, name="get_current_viewcapture", **arguments):
    return tools[name](expected_model_path=r"C:\offline\model.3dm", **arguments)


def test_default_current_capture_never_requests_selection_isolation_or_labels():
    tools, calls = capture_tools(png_response())
    assert not invoke(tools).is_error
    assert calls[-1]["type"] == "get_current_viewcapture"
    assert "target_ids" not in calls[-1]
    assert calls[-1]["isolate"] is False and calls[-1]["labels"] is False
    assert calls[-1]["display_mode"] == ""


def test_multiple_object_targets_and_isolation_use_one_native_capture_without_geometry_filters():
    ids = [str(UUID(int=1)), str(UUID(int=2))]
    effects = {"selection_changed": True, "isolated": True, "zoom_selected": True}
    tools, calls = capture_tools(png_response(mutation_applied=True, view_change=effects))
    result = invoke(tools, target_ids=[ids[0], ids[1], ids[0]], isolate=True)
    assert not result.is_error
    assert len(calls) == 2 and calls[-1]["target_ids"] == ids
    assert calls[-1]["target_kind"] == "object" and calls[-1]["isolate"] is True
    assert not {"object_types", "geometry_types"}.intersection(calls[-1])
    assert result.structured_content["mutation_applied"] is True
    assert result.structured_content["view_change"] == effects


@pytest.mark.parametrize("arguments", [
    {"target_ids": []}, {"target_ids": ["bad-guid"]}, {"target_ids": [str(UUID(int=0))]},
    {"target_ids": [3]}, {"target_kind": "group"}, {"isolate": True}, {"isolate": 1},
    {"target_kind": "mesh", "target_ids": [str(UUID(int=1))]},
])
def test_invalid_target_requests_do_not_reach_native(arguments):
    tools, calls = capture_tools()
    result = invoke(tools, **arguments)
    assert result.is_error and result.structured_content["mutation_applied"] is False
    assert calls == []


@pytest.mark.parametrize("options", [
    {"target_ids": [str(UUID(int=1))]}, {"display_mode": "Shaded"},
])
def test_timeout_after_possible_screen_change_is_uncertain_and_never_retried(options):
    tools, calls = capture_tools(failure=TimeoutError("native result pending"))
    result = invoke(tools, **options)
    assert result.is_error
    assert result.structured_content["mutation_applied"] is None
    assert result.structured_content["requires_reconciliation"] is True
    assert len(calls) == 2


def test_plain_capture_timeout_does_not_imply_screen_mutation():
    tools, calls = capture_tools(failure=TimeoutError())
    result = invoke(tools)
    assert result.is_error and result.structured_content["mutation_applied"] is False
    assert result.structured_content["requires_reconciliation"] is False and len(calls) == 2


@pytest.mark.parametrize("response", [
    {"status": "error", "error_code": "capture_failed", "mutation_applied": True,
     "view_change": {"zoom_selected": True}},
    {**png_response(mutation_applied=True, view_change={"zoom_selected": True}), "image": {"data": "bad"}},
])
def test_capture_or_image_validation_error_keeps_completed_view_change(response):
    tools, _ = capture_tools(response)
    result = invoke(tools, target_ids=[str(UUID(int=1))])
    assert result.is_error and result.structured_content["mutation_applied"] is True
    assert result.structured_content["view_change"]["zoom_selected"] is True


def test_missing_native_change_evidence_is_not_reported_as_unchanged():
    tools, _ = capture_tools(png_response())
    result = invoke(tools, target_ids=[str(UUID(int=1))])
    assert result.is_error and result.structured_content["mutation_applied"] is None
    assert result.structured_content["requires_reconciliation"] is True


@pytest.mark.parametrize("kind", ["named_view", "layout"])
def test_defined_target_alone_is_sufficient_and_uses_the_right_native_tool(kind):
    tools, calls = capture_tools(png_response())
    result = invoke(tools, "get_defined_viewcapture", target_kind=kind, target="도면 A")
    assert not result.is_error
    assert calls[-1]["target_kind"] == kind and calls[-1]["target"] == "도면 A"
    assert calls[-1]["type"] == "get_defined_viewcapture"
    assert "width" not in calls[-1] and "height" not in calls[-1]
    assert calls[-1]["display_mode"] == ("Shaded" if kind == "named_view" else "")


@pytest.mark.parametrize("mode,expected", [("", "Shaded"), ("Technical", "Technical"),
    ("AGENT_Section_Glass", "AGENT_Section_Glass"),
    ("f24230d5-159b-4228-b674-0be9ebde30a2", "f24230d5-159b-4228-b674-0be9ebde30a2")])
def test_named_view_default_and_explicit_modes_are_sent_without_reading_saved_mode(mode, expected):
    tools, calls = capture_tools(png_response())
    result = invoke(tools, "get_defined_viewcapture", target_kind="named_view", target="section", display_mode=mode)
    assert not result.is_error
    assert [call["type"] for call in calls] == ["get_rhino_context", "get_defined_viewcapture"]
    assert calls[0]["sections"] == []  # Capability check, not a stored Named View mode lookup.
    assert calls[-1]["display_mode"] == expected


def test_defined_capture_public_schema_explains_target_specific_mode_defaults():
    async def schema():
        mcp = FastMCP("defined-capture-schema")
        register(mcp, SimpleNamespace())
        async with Client(mcp) as client:
            return next(tool for tool in await client.list_tools() if tool.name == "capture_04-defined_view")
    tool = asyncio.run(schema())
    properties = tool.input_schema["properties"]
    assert properties["display_mode"]["default"] == ""  # Neutral for Layout; resolved by target kind.
    assert "Named View" in tool.description and "Layout" in tool.description
    for text in (properties["target_kind"]["description"], properties["display_mode"]["description"]):
        assert "Shaded" in text and "Detail" in text
    assert "AGENT_Section_Glass" in properties["display_mode"]["description"]
    baseline = Path(__file__).resolve().parents[3] / "tests/integration/tool_schemas.json"
    assert tool.input_schema == json.loads(baseline.read_text(encoding="utf-8"))["capture_04-defined_view"]["inputSchema"]


def test_defined_capture_automatic_scale_is_verified_against_the_returned_png():
    tools, _ = capture_tools(png_response(scale=37, scale_percent=37, warnings=["Capture scale reduced."]))
    result = invoke(tools, "get_defined_viewcapture", target_kind="layout", target="A0", include_usage=True)
    assert not result.is_error
    metadata = [json.loads(item.text) for item in result.content if item.type == "text"]
    assert any(item.get("scale_percent") == 37 and item.get("width") == 14 for item in metadata)
    assert any(item.get("warnings") == ["Capture scale reduced."] for item in metadata)


@pytest.mark.parametrize("options", [{"width": 128, "height": 128, "scale_percent": 100}, {"display_mode": "Shaded"}])
def test_layout_rejects_pixel_and_mode_overrides_before_dispatch(options):
    tools, calls = capture_tools()
    result = invoke(tools, "get_defined_viewcapture", target_kind="layout", target="A3", **options)
    assert result.is_error and calls == []
