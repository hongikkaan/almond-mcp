"""Display-mode evidence delivered by the inspection contact-sheet tool."""
import asyncio
import base64
import io
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP
from PIL import Image

from almond_mcp.features.context.tools import register


@pytest.mark.parametrize("tool,options", [
    ("get_rhino_context", {}),
    ("get_rhino_context", {"sections": ["display_modes"]}),
    ("get_current_viewcapture", {"display_mode": "Shaded"}),
    ("get_defined_viewcapture", {"target_kind": "named_view", "target": "Entrance"}),
    ("capture_rhino_inspection", {"views": [{}, {"display_mode": "Shaded"}]}),
])
def test_old_bridge_does_not_expose_or_apply_unfiltered_display_modes(tool, options):
    calls = []

    def send(raw):
        request = json.loads(raw)
        calls.append(request["type"])
        return json.dumps({"status": "success", "capabilities": {
            "context_sections": 2, "view_capture": 1, "inspection_capture": 1},
            "display_modes": [{"id": "hidden", "name": "Hidden mode"}]})

    if tool != "get_rhino_context":
        options = {**options, "expected_model_path": r"C:\offline\model.3dm"}
    tools = register(FastMCP("legacy-display-menu"), SimpleNamespace(_send_and_receive=send))
    result = tools[tool](**options)
    assert result.is_error
    payload = result.structured_content
    if tool == "get_rhino_context":
        payload = json.loads(payload["result"])
    assert payload["error_code"] == "unsupported_display_mode_menu"
    assert "display_modes" not in payload
    assert calls == ["get_rhino_context"]


@pytest.mark.parametrize("tool,options", [
    ("get_current_viewcapture", {}),
    ("get_defined_viewcapture", {"target_kind": "layout", "target": "Paper"}),
    ("capture_rhino_inspection", {"views": [{}]}),
])
def test_old_bridge_can_capture_without_selecting_a_display_mode(tool, options):
    calls = []
    def send(raw):
        calls.append(json.loads(raw)["type"])
        if calls[-1] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"view_capture": 1, "inspection_capture": 1}})
        return json.dumps({"status": "error", "error_code": "no_viewport"})

    tools = register(FastMCP("legacy-current-mode"), SimpleNamespace(_send_and_receive=send))
    result = tools[tool](expected_model_path=r"C:\offline\model.3dm", **options)
    assert calls == ["get_rhino_context", tool]
    assert result.structured_content["error_code"] == "no_viewport"


def test_inspection_public_description_explains_mode_discovery_and_object_scope():
    async def list_tools():
        mcp = FastMCP("inspection-discovery")
        register(mcp, SimpleNamespace())
        async with Client(mcp) as client:
            return {tool.name: tool.description for tool in await client.list_tools()}

    descriptions = asyncio.run(list_tools())
    inspection = descriptions["capture_02-inspection"]
    assert 'inspect_03-get_document_context tool' in inspection
    assert 'display_modes' in inspection
    for mode in ("Wireframe", "Shaded", "Technical"):
        assert mode in inspection
    assert "object_ids" in inspection and "inspect_02-get_objects tool" in inspection
    assert "capture_02-inspection tool" in descriptions["capture_03-current_view"]


CUSTOM_MODE_ID = "f24230d5-159b-4228-b674-0be9ebde30a2"
OTHER_MODE_ID = "f64230d5-159b-4228-b674-0be9ebde30a2"


@pytest.mark.parametrize("selector,reported_mode,observed_id", [
    ("Custom Section", CUSTOM_MODE_ID, CUSTOM_MODE_ID),
    (CUSTOM_MODE_ID.upper(), CUSTOM_MODE_ID, CUSTOM_MODE_ID),
    (CUSTOM_MODE_ID, CUSTOM_MODE_ID, OTHER_MODE_ID),
    (CUSTOM_MODE_ID, OTHER_MODE_ID, OTHER_MODE_ID),
    ("Custom Section", None, None),
])
def test_inspection_only_delivers_an_image_with_matching_display_mode(
    selector, reported_mode, observed_id, tmp_path, monkeypatch,
):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", "tmp/inspection-display-test")
    picture = io.BytesIO()
    Image.new("RGB", (128, 128)).save(picture, format="PNG")

    def send(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"inspection_capture": 1, "display_mode_menu": 1}})
        assert request["views"][0]["display_mode"] == selector
        tile = {"index": 0, "direction": "top", "status": "success", "scope": {"complete": True}}
        if reported_mode is not None:
            tile["display_mode"] = {"name": "Custom Section", "id": reported_mode}
            tile["camera"] = {"display_mode_id": observed_id}
        return json.dumps({"status": "success", "complete": True, "tiles": [tile],
                           "image": {"mime_type": "image/png", "width": 128, "height": 128,
                                     "data": base64.b64encode(picture.getvalue()).decode("ascii")}})

    capture = register(FastMCP("inspection-modes"), SimpleNamespace(_send_and_receive=send))["capture_rhino_inspection"]
    result = capture(
        views=[{"direction": "top", "display_mode": selector}], width=128, height=128,
        expected_model_path=r"C:\offline\inspection.3dm",
    )
    if observed_id == CUSTOM_MODE_ID:
        assert not result.is_error
        assert result.structured_content["tiles"][0]["display_mode"]["id"] == CUSTOM_MODE_ID
        assert any(item.type == "image" for item in result.content)
    else:
        assert result.is_error
        assert result.structured_content["error_code"] == "invalid_capture_response"
        assert not list(tmp_path.rglob("*.png"))
