"""Inspection capture protocol checks without connecting to Rhino or a model."""
import base64
import copy
import io
import json

import pytest
from PIL import Image

from almond_mcp.features.context.inspection_capture import execute


MODEL = r"C:\models\guardpost.3dm"
OBJECT = "20ac2693-52d2-4121-bfb0-58bd1c3b6f54"


def response(views, width=128, height=128, columns=1):
    rows = (len(views) + columns - 1) // columns
    with Image.new("RGB", (width * columns, height * rows), "white") as image:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    return {
        "status": "success", "complete": True,
        "tiles": [{"index": i, "status": "success", "direction": v.get("direction", "current"),
                   "scope": {"eligible_object_ids": [OBJECT], "eligible_count": 1,
                             "visibility_evidence": "document visibility, not pixels"}}
                  for i, v in enumerate(views)],
        "image": {"mime_type": "image/png", "width": width * columns, "height": height * rows,
                  "data": base64.b64encode(buffer.getvalue()).decode("ascii")},
    }


def sender(reply, capability=1):
    calls = []

    def send(payload):
        calls.append(json.loads(payload))
        if calls[-1]["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"inspection_capture": capability}})
        return json.dumps(reply)

    return send, calls


def metadata(result):
    return json.loads(result.content[0].text)


@pytest.mark.parametrize("payload", [
    {"views": []}, {"views": [{}] * 17}, {"views": [{"direction": "orbit"}]},
    {"views": [{"object_ids": [OBJECT, OBJECT]}]}, {"views": [{"object_ids": ["not-guid"]}]},
    {"views": [{"object_ids": ["00000000-0000-0000-0000-000000000000"]}]},
    {"views": [{"group_id": OBJECT}]}, {"views": [{}], "width": True},
    {"views": [{}], "height": 127}, {"views": [{}], "columns": 2},
    {"views": [{}] * 16, "width": 2048, "height": 2048},
])
def test_invalid_request_never_reaches_rhino(payload):
    send, calls = sender({})
    result = execute(send, payload, MODEL)
    assert metadata(result)["error_code"] == "invalid_arguments"
    assert calls == []


def test_missing_bound_path_and_old_bridge_do_not_dispatch_capture():
    send, calls = sender({}, capability=0)
    assert metadata(execute(send, {"views": [{}]}, "relative.3dm"))["error_code"] == "invalid_arguments"
    assert calls == []
    result = execute(send, {"views": [{}]}, MODEL)
    assert metadata(result)["error_code"] == "unsupported_inspection_capture"
    assert [call["type"] for call in calls] == ["get_rhino_context"]


def test_explicit_choices_are_preserved_without_group_expansion_or_fixed_view_sequence():
    views = [{"direction": "below_sw", "object_ids": [OBJECT], "display_mode": "Custom mode", "label": "하부"},
             {"direction": "current"}, {"direction": "iso_ne", "object_ids": []}]
    send, calls = sender(response(views))
    result = execute(send, {"views": views, "width": 128, "height": 128, "columns": 1}, MODEL)
    assert not result.is_error
    assert [item.type for item in result.content] == ["text", "image"]
    request = calls[1]
    assert request["type"] == "capture_rhino_inspection"
    assert request["expected_model_path"] == MODEL
    assert len(request["views"]) == 3
    assert request["views"][0] == views[0]
    assert request["views"][1]["object_ids"] == []
    assert calls[0]["sections"] == []
    assert "image" not in metadata(result)


def test_partial_sheet_keeps_tile_error_and_does_not_claim_complete():
    views = [{"direction": "front"}, {"direction": "back"}]
    reply = response(views)
    reply["complete"] = False
    reply["tiles"][1] = {"index": 1, "direction": "back", "status": "error",
                         "error_code": "unsupported_block_filter"}
    send, calls = sender(reply)
    result = execute(send, {"views": views, "width": 128, "height": 128, "columns": 1}, MODEL)
    assert not result.is_error
    assert metadata(result)["complete"] is False
    assert metadata(result)["tiles"][1]["error_code"] == "unsupported_block_filter"
    assert len(calls) == 2


def test_failed_native_capture_does_not_publish_an_unverified_image_or_retry():
    send, calls = sender({"status": "error", "error_code": "observation_state_changed", "image": {"data": "unsafe"}})
    result = execute(send, {"views": [{}]}, MODEL)
    assert result.is_error
    assert metadata(result)["error_code"] == "observation_state_changed"
    assert "image" not in metadata(result)
    assert len(result.content) == 1
    assert len(calls) == 2


@pytest.mark.parametrize("fault", ["wrong_size", "invalid_png", "wrong_tile", "missing_scope", "wrong_direction"])
def test_malformed_capture_is_rejected_without_image(fault):
    views = [{"direction": "top"}]
    reply = copy.deepcopy(response(views))
    if fault == "wrong_size":
        reply["image"]["width"] = 129
    elif fault == "invalid_png":
        reply["image"]["data"] = base64.b64encode(b"not a png").decode("ascii")
    elif fault == "wrong_tile":
        reply["tiles"][0]["index"] = 1
    elif fault == "wrong_direction":
        reply["tiles"][0]["direction"] = "bottom"
    else:
        del reply["tiles"][0]["scope"]
    send, calls = sender(reply)
    result = execute(send, {"views": views, "width": 128, "height": 128}, MODEL)
    assert metadata(result)["error_code"] == "invalid_capture_response"
    assert len(result.content) == 1
    assert len(calls) == 2
