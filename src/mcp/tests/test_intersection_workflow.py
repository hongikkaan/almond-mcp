"""Numbered choices must stay attached to the image actually delivered to this connection."""
import asyncio
import base64
import io
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP
from PIL import Image

from almond_mcp.features.components.intersection_workflow import Workflow
from almond_mcp.features.components.tools import register
from almond_mcp.runtime.shared_store import capture_file_write, writes_artifacts

A, B, C = (str(UUID(int=i)) for i in (1, 2, 3))
HA, HB, HC = ({"object_id": v, "path": []} for v in (A, B, C))


def pair(a=HA, b=HB, status="positive_volume"):
    return {"a": {"handle": a}, "b": {"handle": b}, "overlap": {"status": status}}


def page(*pairs, cursor=None):
    return {"status": "success", "pairs": list(pairs), "unsupported_objects": [],
            "pagination_complete": cursor is None, "next_cursor": cursor}


def image(a=HA, b=HB):
    data = io.BytesIO()
    Image.new("RGB", (1280, 504), "white").save(data, format="PNG")
    return {"status": "success", "objects": [{"number": 1, "handle": a}, {"number": 2, "handle": b}],
            "image": {"data": base64.b64encode(data.getvalue()).decode(), "mime_type": "image/png", "width": 1280, "height": 504},
            "mutation_applied": True, "view_change": {"geometry_changed": False, "comparison_isolation_restored": True}}


def edited(choice):
    return {"status": "success", "result": {"edited": True, "keep_id": B if choice == 1 else A,
            "trim_id": A if choice == 1 else B, "previous_geometry_crc": 1, "geometry_crc": 2}}


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(tmp_path / "review.3dm"))
    monkeypatch.setattr("almond_mcp.features.components.intersection_workflow.save_png", lambda *_: {"status": "saved"})
    def create(*replies):
        responses = iter(replies)
        calls = []
        def send(raw):
            request = json.loads(raw)
            if request["type"] == "get_rhino_context":
                return json.dumps({"status": "success", "capabilities": {"intersection_queries": 1, "intersection_review": 1}})
            calls.append(request)
            value = next(responses)
            if isinstance(value, Exception):
                raise value
            return json.dumps(value)
        return Workflow(send), calls, send
    return create


def test_stops_at_first_positive_without_scanning_later_pairs(setup):
    workflow, calls, _ = setup(page(pair(status="zero_volume"), cursor="s:1"), page(pair(), cursor="s:2"), image())
    response = workflow.execute([A, B, C])
    assert not response.is_error and response.structured_content["state"] == "awaiting_choice"
    assert [c["type"] for c in calls] == ["get_object_intersections", "get_object_intersections", "intersection_review"]
    assert all(c["max_pairs"] == 64 and c["stop_at_first_positive"] is True for c in calls[:2])
    assert "pair_state" not in calls[-1] and response.content[0].type == "image"


def test_registered_workflow_rebinds_sender_and_keeps_pending_review(setup):
    from almond_mcp.feature_context import FeatureContext
    _, calls, current = setup(page(pair()), image(), edited(1), page())
    def unbound(*args, **kwargs):
        raise AssertionError("Registration-time sender must not dispatch")
    namespace = {"_send_and_receive": unbound}
    tools = register(FastMCP("late-bound-review"), FeatureContext(namespace))
    namespace["_send_and_receive"] = current
    first = tools["resolve_object_intersection"]([A, B]).structured_content
    output = tools["resolve_object_intersection"](review_id=first["review_id"], choice=1)
    assert output.structured_content["state"] == "completed"
    assert [c["type"] for c in calls] == ["get_object_intersections", "intersection_review", "intersection_resolve", "get_object_intersections"]
    assert tools["resolve_object_intersection"](review_id=first["review_id"], choice=1).is_error


@pytest.mark.parametrize("choice", [1, 2])
def test_number_trims_selected_object_and_requeries_live_scope_from_start(setup, choice):
    workflow, calls, _ = setup(page(pair()), image(), edited(choice), page())
    first = workflow.execute([A, B]).structured_content
    response = workflow.execute(review_id=first["review_id"], choice=choice)
    assert not response.is_error and response.structured_content["state"] == "completed"
    assert response.structured_content["previous_result"]["edited"] is True
    mutation = calls[2]
    assert mutation["type"] == "intersection_resolve"
    assert mutation["trim"] == (HA if choice == 1 else HB)
    assert mutation["keep"] == (HB if choice == 1 else HA)
    assert "pair_state" not in mutation and calls[-1]["cursor"] == ""
    repeated = workflow.execute(review_id=first["review_id"], choice=choice)
    assert repeated.is_error and len(calls) == 4


def test_skip_never_mutates_and_advances_to_next_distinct_pair(setup):
    workflow, calls, _ = setup(page(pair()), image(), page(pair(), cursor="s:1"), page(pair(HA, HC)), image(HA, HC))
    first = workflow.execute([A, B, C]).structured_content
    output = workflow.execute(review_id=first["review_id"], choice="skip").structured_content
    assert output["number"] == 2 and output["review_id"] != first["review_id"]
    assert output["previous_result"]["status"] == "skipped"
    assert not any(c["type"] == "intersection_resolve" for c in calls)


def test_choice_cannot_target_a_replaced_review_or_changed_document(setup, monkeypatch):
    workflow, calls, _ = setup(page(pair()), image(), page(pair(HA, HC)), image(HA, HC))
    first = workflow.execute([A, B]).structured_content
    workflow.execute([A, C])
    assert workflow.execute(review_id=first["review_id"], choice=1).is_error
    monkeypatch.setenv("ALMOND_MODEL_PATH", r"C:\offline\other.3dm")
    assert workflow.execute().is_error and len(calls) == 4


def test_timeout_consumes_choice_and_blocks_automatic_continuation(setup):
    workflow, calls, _ = setup(page(pair()), image(), TimeoutError("pending"))
    first = workflow.execute([A, B]).structured_content
    output = workflow.execute(review_id=first["review_id"], choice=1)
    assert output.is_error and output.structured_content["requires_reconciliation"]
    assert workflow.execute(review_id=first["review_id"], choice=1).is_error
    assert workflow.execute().is_error and len(calls) == 3


@pytest.mark.parametrize("next_page", [{"status": "success"}, {"status": "error", "message": "query failed"}])
def test_error_after_confirmed_edit_keeps_completed_mutation_receipt(setup, next_page):
    workflow, _, _ = setup(page(pair()), image(), edited(1), next_page)
    first = workflow.execute([A, B]).structured_content
    output = workflow.execute(review_id=first["review_id"], choice=1)
    assert output.is_error and output.structured_content["previous_result"]["edited"] is True


def test_invalid_image_cannot_authorize_a_numbered_edit(setup):
    invalid = image()
    invalid["image"]["data"] = "invalid"
    workflow, calls, _ = setup(page(pair()), invalid)
    response = workflow.execute([A, B])
    assert response.is_error and workflow.pending is None
    assert workflow.execute(review_id=response.structured_content["review_id"], choice=1).is_error
    assert len(calls) == 2


@pytest.mark.parametrize("missing", [False, True])
def test_absent_image_cannot_authorize_a_numbered_edit(setup, missing):
    invalid = image()
    if missing:
        del invalid["image"]
    else:
        invalid["image"] = None
    workflow, calls, _ = setup(page(pair()), invalid)
    response = workflow.execute([A, B])
    assert response.is_error and workflow.pending is None
    assert "review_id" not in response.structured_content
    assert workflow.execute(review_id="undelivered", choice=1).is_error
    assert len(calls) == 2


def test_block_members_are_reviewable_but_only_skip_is_applied(setup):
    member = {"object_id": A, "path": [C]}
    workflow, calls, _ = setup(page(pair(member, HB)), image(member, HB), page(pair(member, HB)))
    first = workflow.execute([A, B], include_block=True).structured_content
    assert workflow.execute(review_id=first["review_id"], choice=1).is_error
    output = workflow.execute(review_id=first["review_id"], choice="skip")
    assert not output.is_error and output.structured_content["skipped_pairs"] == 1
    assert not any(c["type"] == "intersection_resolve" for c in calls)


def test_unconfirmed_native_receipt_stops_before_querying_more(setup):
    wrong = edited(1)
    wrong["result"]["trim_id"] = C
    workflow, calls, _ = setup(page(pair()), image(), wrong)
    first = workflow.execute([A, B]).structured_content
    output = workflow.execute(review_id=first["review_id"], choice=1)
    assert output.is_error and output.structured_content["error_code"] == "intersection_resolution_unconfirmed"
    assert len(calls) == 3


def test_native_runtime_error_preserves_undo_failure_and_stops_continuation(setup):
    failure = {"status": "runtime_error", "message": "EndUndoRecord failed",
               "error_trace": "undo restoration failed", "guids": [A]}
    workflow, calls, _ = setup(page(pair()), image(), failure)
    first = workflow.execute([A, B]).structured_content
    output = workflow.execute(review_id=first["review_id"], choice=1).structured_content
    assert output["status"] == "error" and output["native_status"] == "runtime_error"
    assert output["message"] == failure["message"] and output["error_trace"] == failure["error_trace"]
    assert output["guids"] == [A] and output["requires_reconciliation"] is True
    assert output["geometry_change_possible"] is True
    assert workflow.execute().is_error and len(calls) == 3


@pytest.mark.parametrize("invalid", ["image", "identity"])
def test_invalid_comparison_preserves_screen_change_evidence_and_blocks_continuation(setup, invalid):
    response = image()
    response["requires_reconciliation"] = True
    if invalid == "image":
        response.pop("image")
    else:
        response["objects"][1]["handle"] = HC
    workflow, calls, _ = setup(page(pair()), response)
    output = workflow.execute([A, B]).structured_content
    assert output["status"] == "error" and output["mutation_applied"] is True
    assert output["view_change"] == response["view_change"] and output["requires_reconciliation"] is True
    assert workflow.pending is None and workflow.execute().is_error and len(calls) == 2


def test_public_tool_combines_review_and_choice_with_strict_schema(setup):
    _, calls, send = setup()
    server = FastMCP("review-test")
    register(server, SimpleNamespace(_send_and_receive=send))
    async def run():
        async with Client(server) as client:
            tools = {v.name: v for v in await client.list_tools()}
            assert "show_object_intersection" not in tools
            schema = tools["intersect_02-resolve"].input_schema
            assert set(schema["properties"]) == {"object_ids", "include_block", "review_id", "choice"}
            for args in ({"choice": True}, {"choice": "1"}, {"choice": 3}, {"pair_state": "x"},
                         {"object_ids": [A], "choice": 1}, {"review_id": "missing", "choice": 2}):
                response = await client.call_tool("intersect_02-resolve", args, raise_on_error=False)
                assert response.is_error
            assert not calls
    asyncio.run(run())
    assert writes_artifacts("resolve_object_intersection", {})
    assert capture_file_write("resolve_object_intersection", {})
