"""Model-view selection stays an observation request, not a UI switch."""
import json
from types import SimpleNamespace
from uuid import uuid4

from fastmcp import FastMCP

from almond_mcp.features.context.tools import register


def capture_tool(capabilities):
    calls = []

    def send(raw):
        request = json.loads(raw)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": capabilities})
        return json.dumps({"status": "error", "error_code": "empty_scope", "message": "No visible objects."})

    tools = register(FastMCP("inspection-view-test"), SimpleNamespace(_send_and_receive=send))
    return tools["capture_rhino_inspection"], calls


def test_explicit_model_view_is_forwarded_without_a_ui_mutation():
    capture, calls = capture_tool({"inspection_capture": 1, "inspection_model_view": 1})
    model_view = str(uuid4())
    result = capture(
        views=[{"direction": "top"}], model_view_id=model_view,
        expected_model_path=r"C:\offline\inspection.3dm",
    )
    assert [call["type"] for call in calls] == ["get_rhino_context", "capture_rhino_inspection"]
    assert calls[-1]["model_view_id"] == model_view
    assert result.structured_content["error_code"] == "empty_scope"


def test_model_view_extension_is_rejected_before_dispatch_on_an_older_bridge():
    capture, calls = capture_tool({"inspection_capture": 1})
    result = capture(
        views=[{"direction": "top"}], model_view_id=str(uuid4()),
        expected_model_path=r"C:\offline\inspection.3dm",
    )
    assert result.is_error
    assert result.structured_content["error_code"] == "unsupported_inspection_model_view"
    assert [call["type"] for call in calls] == ["get_rhino_context"]


def test_invalid_model_view_guid_never_reaches_rhino():
    capture, calls = capture_tool({"inspection_capture": 1, "inspection_model_view": 1})
    result = capture(
        views=[{"direction": "top"}], model_view_id="not-a-guid",
        expected_model_path=r"C:\offline\inspection.3dm",
    )
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_arguments"
    assert calls == []


def test_legacy_active_view_request_does_not_require_the_new_capability():
    capture, calls = capture_tool({"inspection_capture": 1})
    result = capture(views=[{"direction": "top"}], expected_model_path=r"C:\offline\inspection.3dm")
    assert "model_view_id" not in calls[-1]
    assert result.structured_content["error_code"] == "empty_scope"
