"""Agent decisions: ask only for the editor, selection or capture being used."""

import asyncio
import json
from types import SimpleNamespace
import uuid

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.context.tools import register
from test_rhino_observation import capture_response


@pytest.fixture
def context():
    value = SimpleNamespace(mcp=FastMCP("observation-decisions"), requests=[])

    def send(payload):
        request = json.loads(payload)
        value.requests.append(request)
        if request["type"] == "get_rhino_viewport_image":
            return json.dumps(capture_response())
        return json.dumps({"status": "success", "editor": {"mode": "unknown", "target": None,
                           "stable": False}, "selection": {"total": 0, "objects": []}})

    value._send_and_receive = send
    value.__dict__.update(register(value.mcp, value))
    return value


def test_given_uncertain_editor_when_editor_requested_then_preserve_unknown(context):
    result = json.loads(context.get_rhino_context(sections=["editor"]))
    assert result["editor"] == {"mode": "unknown", "target": None, "stable": False}
    assert "selection" not in result
    assert context.requests == [{"type": "get_rhino_context", "sections": ["editor"],
                                 "selection_limit": 50, "recursive": False, "depth": 1, "include_image": False}]


def test_given_selection_when_no_recursion_requested_then_send_shallow_defaults(context):
    context.get_rhino_context(sections=["selection"])
    assert context.requests[0]["recursive"] is False
    assert context.requests[0]["depth"] == 1


def test_given_default_context_when_editor_not_explicit_then_compact_mode_is_still_visible(context):
    result = json.loads(context.get_rhino_context())
    assert result["editor"] == {"mode": "unknown", "target": None, "stable": False}


def test_given_unsupported_runtime_when_default_context_read_then_never_assume_model(context):
    context._send_and_receive = lambda _: '{"status":"success","document":{"name":"fixture"}}'
    result = json.loads(context.get_rhino_context())
    assert result["editor"] == {"mode": "unknown", "target": None, "stable": False}


def test_given_only_capabilities_needed_when_sections_empty_then_no_editor_is_added(context):
    result = json.loads(context.get_rhino_context(sections=[]))
    assert "editor" not in result


def test_given_nested_target_when_details_needed_then_send_explicit_depth(context):
    context.get_rhino_context(sections=["selection"], recursive=True, depth=3)
    assert context.requests[0]["recursive"] is True
    assert context.requests[0]["depth"] == 3


@pytest.mark.parametrize("arguments", [{"recursive": 1}, {"recursive": "false"},
                                        {"depth": True}, {"depth": 0}, {"depth": 9}])
def test_given_bad_selection_options_when_queried_then_never_send_native(context, arguments):
    result = json.loads(context.get_rhino_context(**arguments))
    assert result["error_code"] == "invalid_arguments"
    assert context.requests == []


def test_given_capture_when_options_omitted_then_transient_labels_depth_one(context):
    result = context.get_rhino_viewport_image()
    assert not result.is_error
    assert context.requests == [{"type": "get_rhino_viewport_image", "view": "", "scale_percent": 50,
                                 "display_mode": "", "labels": True, "depth": 1,
                                 "target_kind": "view", "target_id": ""}]


def test_given_incomplete_overlay_when_captured_then_public_result_keeps_warning(context):
    response = capture_response()
    response["warnings"] = ["labels: limited to 200 entities; capture a smaller target."]
    context._send_and_receive = lambda _: json.dumps(response)
    result = context.get_rhino_viewport_image()
    assert [block.type for block in result.content] == ["image", "text"]
    assert json.loads(result.content[1].text)["warnings"] == response["warnings"]


@pytest.mark.parametrize("kind", ["group", "block"])
def test_given_group_or_block_when_captured_then_target_identity_is_explicit(context, kind):
    target = str(uuid.uuid4())
    result = context.get_rhino_viewport_image(target_kind=kind, target_id=target,
                                              display_mode="Shaded", labels=False, depth=2)
    assert not result.is_error
    request = context.requests[0]
    assert (request["target_kind"], request["target_id"], request["display_mode"]) == (kind, target, "Shaded")
    assert request["labels"] is False and request["depth"] == 2


@pytest.mark.parametrize("arguments", [
    {"target_kind": "definition"}, {"target_kind": "group"},
    {"target_kind": "block", "target_id": "not-a-guid"},
    {"target_kind": "group", "target_id": str(uuid.uuid4()), "view": "a"},
    {"labels": "false"}, {"labels": 1}, {"depth": True}, {"depth": 0}, {"depth": 9},
    {"display_mode": None}, {"display_mode": "x" * 513},
])
def test_given_bad_capture_options_when_called_then_never_send_native(context, arguments):
    result = context.get_rhino_viewport_image(**arguments)
    assert result.is_error
    assert result.structured_content["error_code"] == "invalid_arguments"
    assert context.requests == []


def test_given_mode_choice_needed_when_modes_requested_then_no_image_request(context):
    context._send_and_receive = lambda payload: json.dumps({"status": "success", "display_modes": [
        {"name": "Shaded", "id": str(uuid.uuid4())}, {"name": "CADWhite2", "id": str(uuid.uuid4())}]})
    result = json.loads(context.get_rhino_context(sections=["display_modes"]))
    assert [row["name"] for row in result["display_modes"]] == ["Shaded", "CADWhite2"]
    assert all("id" not in row for row in result["display_modes"])


def test_given_visual_context_when_image_requested_then_text_and_png_share_native_call(context):
    def snapshot(payload):
        request = json.loads(payload)
        context.requests.append(request)
        assert request["type"] == "get_rhino_context" and request["include_image"] is True
        return json.dumps({"status": "success", "viewport": {"display_mode": "Shaded", "id": str(uuid.uuid4())},
                           "image": capture_response()["image"]})
    context._send_and_receive = snapshot
    result = context.get_rhino_context(sections=["viewport"], include_image=True)
    assert [block.type for block in result.content] == ["text", "image"]
    metadata = json.loads(result.content[0].text)
    assert metadata == {"status": "success", "viewport": {"display_mode": "Shaded"},
                        "editor": {"mode": "unknown", "target": None, "stable": False}}
    assert len(context.requests) == 1


def test_given_capture_failure_when_context_requested_then_keep_editor_and_explicit_error(context):
    context._send_and_receive = lambda _: json.dumps({"status": "success", "editor": {"mode": "group", "stable": False},
        "image_error": {"status": "error", "error_code": "capture_failed", "message": "No bitmap"}})
    result = context.get_rhino_context(sections=["editor"], include_image=True)
    assert [block.type for block in result.content] == ["text"]
    metadata = json.loads(result.content[0].text)
    assert metadata["editor"]["mode"] == "group"
    assert metadata["image_error"]["error_code"] == "capture_failed"


def test_given_forged_context_image_when_requested_then_never_emit_image(context):
    context._send_and_receive = lambda _: json.dumps({"status": "success", "image": {"data": "no PNG"}})
    result = context.get_rhino_context(sections=["viewport"], include_image=True)
    assert [block.type for block in result.content] == ["text"]
    assert json.loads(result.content[0].text)["image_error"]["error_code"] == "invalid_capture_response"


def test_given_mcp_client_when_visual_context_requested_then_protocol_keeps_text_and_image(context):
    context._send_and_receive = lambda _: json.dumps({"status": "success", "editor": {"mode": "unknown", "stable": False},
                                                     "image": capture_response()["image"]})
    async def verify():
        async with Client(context.mcp) as client:
            result = await client.call_tool("get_rhino_context", {"sections": ["editor"], "include_image": True})
            assert [block.type for block in result.content] == ["text", "image"]
            assert json.loads(result.content[0].text)["editor"] == {"mode": "unknown", "stable": False}
    asyncio.run(verify())


@pytest.mark.parametrize("groups", [None, [], ["everything"], "summary", ["summary", "invalid"]])
def test_given_unsupported_outline_fields_when_queried_then_reject_before_native(context, groups):
    result = json.loads(context.get_rhino_probe(probe="outline", options={"field_groups": groups},
                                                expected_model_path="C:\\fixture\\model.3dm"))
    assert result["error_code"] == "invalid_arguments"
    assert context.requests == []
