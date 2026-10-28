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
                                 "selection_limit": 50, "recursive": False, "depth": 1, "include_image": False,
                                 "selection_entities": True}]


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
    assert context.requests == [{"type": "get_rhino_viewport_image", "view": "", "scale_percent": 75,
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
            assert result.structured_content == {"result": result.content[0].text}
    asyncio.run(verify())


def test_given_existing_client_when_default_context_requested_then_string_result_schema_is_preserved(context):
    async def verify():
        async with Client(context.mcp) as client:
            tool = next(tool for tool in await client.list_tools() if tool.name == "get_rhino_context")
            assert tool.output_schema["properties"]["result"]["type"] == "string"
            assert tool.output_schema["x-fastmcp-wrap-result"] is True
            result = await client.call_tool("get_rhino_context", {})
            assert [block.type for block in result.content] == ["text"]
            assert result.structured_content == {"result": result.content[0].text}
    asyncio.run(verify())


def test_given_native_failure_when_visual_context_requested_then_structured_error_keeps_proof(context):
    evidence_id = str(uuid.uuid4())
    context._send_and_receive = lambda _: json.dumps({"status": "error", "error_code": "document_mismatch",
        "expected_document_id": evidence_id, "image": {"data": "forged"}})
    async def verify():
        async with Client(context.mcp) as client:
            result = await client.call_tool("get_rhino_context", {"include_image": True}, raise_on_error=False)
            assert result.is_error
            assert [block.type for block in result.content] == ["text"]
            assert result.structured_content == {"result": result.content[0].text}
            metadata = json.loads(result.content[0].text)
            assert metadata == {"status": "error", "error_code": "document_mismatch", "expected_document_id": evidence_id}
    asyncio.run(verify())


@pytest.mark.parametrize("groups", [None, [], ["everything"], "summary", ["summary", "invalid"]])
def test_given_unsupported_outline_fields_when_queried_then_reject_before_native(context, groups):
    result = json.loads(context.get_rhino_probe(probe="outline", options={"field_groups": groups},
                                                expected_model_path="C:\\fixture\\model.3dm"))
    assert result["error_code"] == "invalid_arguments"
    assert context.requests == []


def test_given_full_group_selected_when_references_requested_then_member_objects_find_component_and_plan():
    from test_generation_plans import GenerationPlanTests
    from almond_mcp.features.planning.tools import register as planning_tools
    case = GenerationPlanTests()
    case.setUp()
    try:
        model = case.store._component_model_path(str(case.database.parent / "model.3dm"))
        member = "00000000-0000-0000-0000-000000000099"
        with case.store._connect() as connection:
            connection.execute("UPDATE components SET model_path = ?", (model,))
            connection.execute("""INSERT INTO document_objects(model_path,rhino_guid,component_id,object_type,
                min_x,max_x,min_y,max_y,min_z,max_z,observed_at)
                VALUES(?,?,?,'Point',0,0,0,0,0,0,'fixture')""", (model, member, case.component_a))
        plan = case.plan(component_ids=[case.component_a])
        requests = []
        def native(payload):
            request = json.loads(payload)
            requests.append(request)
            assert request.get("selection_entities", False) is False
            return json.dumps({"status": "success", "document": {"path": model},
                "selection": {"total": 1, "truncated": False, "objects": [{"id": member}]}})
        server = SimpleNamespace(mcp=FastMCP("selection-reference-decision"),
            retrieval_store=case.store, _send_and_receive=native)
        exports = planning_tools(server.mcp, server)
        result = json.loads(exports["get_selection_references"](include_ids=True))
        assert result["status"] == "success"
        assert result["objects"][0]["component_id"] == case.component_a
        assert result["plans"][0]["plan_id"] == plan["plan_id"]
        assert requests[0]["sections"] == ["document", "selection"]
    finally:
        case.doCleanups()
