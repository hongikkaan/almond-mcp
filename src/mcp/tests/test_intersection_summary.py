"""Public overlap counts consume native pages without exposing paging or losing failures."""
import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.context.tools import register
from almond_mcp.features.components.tools import register as register_holons


A, B, C = (str(UUID(int=n)) for n in (1, 2, 3))
MODEL = r"C:\offline\intersections.3dm"


def page(*statuses, cursor=None, unsupported=None):
    return {"status": "success", "pairs": [{"overlap": {"status": s}} for s in statuses],
            "unsupported_objects": unsupported or [], "pagination_complete": cursor is None,
            "next_cursor": cursor}


def setup(monkeypatch, pages):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    calls, replies = [], iter(pages)

    def send(raw):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"intersection_queries": 1}})
        calls.append(request)
        return json.dumps(next(replies))

    server = FastMCP("intersection-count")
    tools = register(server, SimpleNamespace(_send_and_receive=send))
    return tools["get_object_intersections"], calls, server


def test_whole_scope_count_spans_pages_and_keeps_private_bound_document(monkeypatch):
    tool, calls, _ = setup(monkeypatch, [page(*(["positive_volume"] * 64), cursor="state:64"),
                                       page("zero_volume", "positive_volume")])
    result = json.loads(tool(object_ids=[A, B]))
    assert result["intersections"] == {"number": 65}
    assert set(result) == {"intersections", "next_step_guide"}
    assert "intersect_02-resolve" in result["next_step_guide"] and "skip" in result["next_step_guide"]
    assert [request["cursor"] for request in calls] == ["", "state:64"]
    assert all(request["expected_model_path"] == MODEL and not request["include_blocks"] for request in calls)


def test_block_exclusion_is_intentional_but_unreadable_geometry_is_not_zero(monkeypatch):
    tool, _, _ = setup(monkeypatch, [page(unsupported=[{"object_id": A, "reason": "block_excluded"}])])
    empty = json.loads(tool(object_ids=[A]))
    assert empty["intersections"]["number"] == 0
    assert "no resolution call is needed" in empty["next_step_guide"]
    assert "intersect_02-resolve" not in empty["next_step_guide"]
    failure = {"object_id": A, "reason": "open_geometry"}
    tool, _, _ = setup(monkeypatch, [page(unsupported=[failure])])
    result = tool(object_ids=[A])
    assert result.is_error
    value = json.loads(result.structured_content["result"])
    assert value["unsupported_objects"] == [failure] and "intersections" not in value


def test_geometry_change_between_pages_does_not_publish_a_partial_count(monkeypatch):
    changed = {"status": "error", "error_code": "stale_scope", "message": "Geometry changed."}
    first = {**page("positive_volume", cursor="state:1"),
             "tolerance_model_units": 0.01, "document_units": "Inches"}
    tool, _, _ = setup(monkeypatch, [first, changed])
    result = tool(object_ids=[A, B])
    assert result.is_error
    body = json.loads(result.structured_content["result"])
    assert body == {**changed, "assessment": "incomplete", "unsupported_objects": None,
                    "failed_pairs": None, "tolerance_model_units": None, "document_units": None}


def test_incomplete_count_identifies_object_and_pair_with_their_observed_tolerance(monkeypatch):
    unsupported = {"object_id": C, "reason": "closed_manifold_brep_required"}
    failed = {"a": {"object_id": A}, "b": {"object_id": B},
              "overlap": {"status": "unknown", "reason": "Mesh BooleanIntersection failed.",
                          "meshing_tolerance": 0.005}}
    observation = {**page(unsupported=[unsupported]), "pairs": [failed],
                   "tolerance_model_units": 0.005, "document_units": "Meters"}
    tool, _, _ = setup(monkeypatch, [observation])

    output = tool(object_ids=[A, B, C])

    assert output.is_error
    body = json.loads(output.structured_content["result"])
    assert "intersections" not in body and body["assessment"] == "incomplete"
    assert body["unsupported_objects"] == [unsupported]
    assert body["failed_pairs"] == [{"objects": [failed["a"], failed["b"]], "reason": failed["overlap"]}]
    assert body["tolerance_model_units"] == 0.005 and body["document_units"] == "Meters"


def test_repeated_continuation_cannot_loop_or_inflate_the_count(monkeypatch):
    repeated = {**page("positive_volume", cursor="state:1"), "document_units": "Inches"}
    tool, calls, _ = setup(monkeypatch, [repeated, repeated])
    result = tool(object_ids=[A, B])
    assert result.is_error and len(calls) == 2
    body = json.loads(result.structured_content["result"])
    assert body["assessment"] == "incomplete" and "intersections" not in body
    assert body["error_code"] == "invalid_intersection_response"
    assert body["document_units"] == "Inches" and body["tolerance_model_units"] is None
    assert body["failed_pairs"] is None and body["unsupported_objects"] is None


@pytest.mark.parametrize("coverage", [{"remaining_candidate_pairs": 2}, {"truncated": True}])
def test_completion_with_reported_work_remaining_cannot_publish_zero(monkeypatch, coverage):
    observation = {**page(), **coverage, "document_units": "Millimeters", "tolerance_model_units": 0.03}
    tool, _, _ = setup(monkeypatch, [observation])
    output = tool(object_ids=[A, B])
    assert output.is_error
    body = json.loads(output.structured_content["result"])
    assert body["assessment"] == "incomplete" and "intersections" not in body
    assert body["tolerance_model_units"] == 0.03 and body["document_units"] == "Millimeters"
    assert next(iter(coverage)) in body["message"]


def test_missing_overlap_keeps_known_pair_and_rejects_unusable_tolerance_metadata(monkeypatch):
    observation = {**page(), "pairs": [{"a": {"object_id": A}, "b": {"object_id": B}, "overlap": None}],
                   "tolerance_model_units": False, "document_units": ""}
    tool, _, _ = setup(monkeypatch, [observation])
    result = tool(object_ids=[A, B])
    assert result.is_error
    body = json.loads(result.structured_content["result"])
    assert body["assessment"] == "incomplete" and "intersections" not in body
    assert body["failed_pairs"] == [{"objects": [{"object_id": A}, {"object_id": B}], "reason": None}]
    assert body["tolerance_model_units"] is None and body["document_units"] is None


def test_missing_pair_list_preserves_the_reported_unsupported_object(monkeypatch):
    unsupported = {"object_id": A, "reason": "closed_extrusion_required"}
    excluded = {"object_id": B, "reason": "block_excluded"}
    observation = {"status": "success", "unsupported_objects": [unsupported, excluded], "document_units": "Meters"}
    tool, _, _ = setup(monkeypatch, [observation])
    result = tool(object_ids=[A, B])
    assert result.is_error
    body = json.loads(result.structured_content["result"])
    assert body["assessment"] == "incomplete" and body["error_code"] == "invalid_intersection_response"
    assert body["unsupported_objects"] == [unsupported] and body["failed_pairs"] is None
    assert body["tolerance_model_units"] is None and body["document_units"] == "Meters"


@pytest.mark.parametrize("unsupported,pairs,known_objects,known_pairs", [
    ([{"object_id": C, "reason": "invalid_geometry"}], [None],
     [{"object_id": C, "reason": "invalid_geometry"}], None),
    ([None], [], None, []),
    ([None], [{"a": {"object_id": A}, "b": {"object_id": B}, "overlap": {"status": "unknown"}}], None,
     [{"objects": [{"object_id": A}, {"object_id": B}], "reason": {"status": "unknown"}}]),
])
def test_invalid_row_does_not_hide_valid_targets_or_enter_the_failure_lists(
        monkeypatch, unsupported, pairs, known_objects, known_pairs):
    observation = {**page(unsupported=unsupported), "pairs": pairs, "document_units": "Meters"}
    tool, _, _ = setup(monkeypatch, [observation])
    result = tool(object_ids=[A, B, C], include_block=True)
    assert result.is_error
    body = json.loads(result.structured_content["result"])
    assert body["assessment"] == "incomplete" and "intersections" not in body
    assert body["unsupported_objects"] == known_objects and body["failed_pairs"] == known_pairs
    assert body["document_units"] == "Meters"


def test_public_schema_has_only_targets_and_singular_include_block(monkeypatch):
    _, calls, server = setup(monkeypatch, [page("positive_volume")])

    async def run():
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = tools["intersect_01-find"].input_schema
            assert set(schema["properties"]) == {"object_ids", "include_block"}
            assert schema["required"] == ["object_ids"]
            assert schema["properties"]["include_block"]["default"] is False
            for extra in ({"max_pairs": 1}, {"cursor": "old"}, {"include_ids": True},
                          {"include_blocks": True}, {"include_block": 1}):
                result = await client.call_tool("intersect_01-find", {"object_ids": [A, B], **extra},
                                               raise_on_error=False)
                assert result.is_error
            assert not calls
            result = await client.call_tool("intersect_01-find", {"object_ids": [A, B], "include_block": True})
            assert not result.is_error and calls[-1]["include_blocks"] is True
    asyncio.run(run())


def test_removed_holon_overlap_is_not_registered_or_callable():
    context = SimpleNamespace(_send_and_receive=lambda _: None)
    server = FastMCP("object-overlap-only")
    registered = register_holons(server, context)
    assert "get_holon_intersections" not in registered

    async def run():
        async with Client(server) as client:
            assert "get_holon_intersections" not in {tool.name for tool in await client.list_tools()}
            result = await client.call_tool("get_holon_intersections", {"holon_ids": ["old"]}, raise_on_error=False)
            assert result.is_error
    asyncio.run(run())
