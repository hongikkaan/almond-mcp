"""Whole-set transport without per-tile duplication or empty-to-document fallback."""
import base64
import io
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import FastMCP
from PIL import Image

from almond_mcp.features.context.tools import register


def make_capture(*, shared=True):
    calls = []

    def send(raw):
        request = json.loads(raw)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            capabilities = {"inspection_capture": 1}
            if shared:
                capabilities["inspection_shared_scope"] = 1
            return json.dumps({"status": "success", "capabilities": capabilities})
        return json.dumps({"status": "error", "error_code": "empty_scope", "message": "Fixture has no live model."})

    tool = register(FastMCP("shared-scope-test"), SimpleNamespace(_send_and_receive=send))["capture_rhino_inspection"]
    return tool, calls


@pytest.mark.parametrize("count", [1022, 4096])
def test_complete_scope_is_sent_once_for_all_views(count):
    tool, calls = make_capture()
    ids = [str(UUID(int=index + 1)) for index in range(count)]
    response = tool(
        views=[{"direction": "top"} for _ in range(16)], object_ids=ids,
        expected_model_path=r"C:\offline\inspection.3dm",
    )
    assert response.structured_content["error_code"] == "empty_scope"
    request = calls[-1]
    assert request["object_ids"] == ids
    assert all(not tile.get("object_ids") for tile in request["views"])
    assert len(json.dumps(request).encode("utf-8")) <= 262144


@pytest.mark.parametrize("ids", [[], [str(UUID(int=0))], [str(UUID(int=1))] * 2,
                                 [str(UUID(int=index + 1)) for index in range(4097)]])
def test_invalid_shared_set_never_expands_to_the_document(ids):
    tool, calls = make_capture()
    response = tool(views=[{"direction": "top"}], object_ids=ids,
                    expected_model_path=r"C:\offline\inspection.3dm")
    assert response.is_error
    assert response.structured_content["error_code"] == "invalid_arguments"
    assert calls == []


def test_shared_and_per_tile_sets_are_not_silently_combined():
    tool, calls = make_capture()
    response = tool(views=[{"object_ids": [str(UUID(int=2))]}], object_ids=[str(UUID(int=1))],
                    expected_model_path=r"C:\offline\inspection.3dm")
    assert response.is_error
    assert response.structured_content["error_code"] == "invalid_arguments"
    assert calls == []


def test_older_bridge_rejects_the_new_scope_before_capture():
    tool, calls = make_capture(shared=False)
    response = tool(views=[{"direction": "top"}], object_ids=[str(UUID(int=1))],
                    expected_model_path=r"C:\offline\inspection.3dm")
    assert response.is_error
    assert response.structured_content["error_code"] == "unsupported_inspection_shared_scope"
    assert [call["type"] for call in calls] == ["get_rhino_context"]


@pytest.mark.parametrize("corruption", [None, "count", "ids", "tile_count", "tile_reference"])
def test_native_scope_proof_is_checked_before_image_delivery(corruption, tmp_path, monkeypatch):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", "tmp/scope-test")
    ids = [str(UUID(int=1)), str(UUID(int=2))]
    picture = io.BytesIO()
    Image.new("RGB", (128, 128)).save(picture, format="PNG")
    scope = {"object_ids": ids[:], "object_count": 2}
    tile = {"complete": True, "eligible_count": 2, "shared_scope_ref": "shared_scope.object_ids"}
    if corruption == "count":
        scope["object_count"] = 1
    elif corruption == "ids":
        scope["object_ids"] = [str(UUID(int=3)), str(UUID(int=4))]
    elif corruption == "tile_count":
        tile["eligible_count"] = 1
    elif corruption == "tile_reference":
        tile.pop("shared_scope_ref")

    def send(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {
                "inspection_capture": 1, "inspection_shared_scope": 1}})
        return json.dumps({"status": "success", "complete": True, "shared_scope": scope,
                           "tiles": [{"index": 0, "direction": "top", "status": "success", "scope": tile}],
                           "image": {"mime_type": "image/png", "width": 128, "height": 128,
                                     "data": base64.b64encode(picture.getvalue()).decode("ascii")}})

    tool = register(FastMCP("scope-response-test"), SimpleNamespace(_send_and_receive=send))["capture_rhino_inspection"]
    response = tool(views=[{"direction": "top"}], object_ids=ids, width=128, height=128,
                    expected_model_path=r"C:\offline\inspection.3dm")
    if corruption is None:
        assert not response.is_error
        assert any(item.type == "image" for item in response.content)
        assert len(list(tmp_path.rglob("*.png"))) == 1
        return
    assert response.is_error
    assert response.structured_content["error_code"] == "invalid_capture_response"
    assert not any(item.type == "image" for item in response.content)
    assert not list(tmp_path.rglob("*.png"))


@pytest.mark.parametrize("complete", [True, False])
def test_partial_sheet_keeps_the_image_but_cannot_claim_complete(complete):
    picture = io.BytesIO()
    Image.new("RGB", (256, 128)).save(picture, format="PNG")

    def send(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"inspection_capture": 1}})
        return json.dumps({"status": "success", "complete": complete,
                           "tiles": [{"index": 0, "direction": "top", "status": "success", "scope": {"complete": True}},
                                     {"index": 1, "direction": "front", "status": "error", "error_code": "scope_not_visible"}],
                           "image": {"mime_type": "image/png", "width": 256, "height": 128,
                                     "data": base64.b64encode(picture.getvalue()).decode("ascii")}})

    tool = register(FastMCP("partial-sheet-test"), SimpleNamespace(_send_and_receive=send))["capture_rhino_inspection"]
    result = tool(views=[{"direction": "top"}, {"direction": "front"}], width=128, height=128,
                  expected_model_path=r"C:\offline\inspection.3dm")
    if complete:
        assert result.is_error
        assert result.structured_content["error_code"] == "invalid_capture_response"
    else:
        assert not result.is_error
        assert result.structured_content["complete"] is False
        assert result.structured_content["tiles"][1]["error_code"] == "scope_not_visible"
        assert any(item.type == "image" for item in result.content)
