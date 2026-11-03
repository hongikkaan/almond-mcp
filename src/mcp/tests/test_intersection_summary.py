"""Public overlap counts consume native pages without exposing paging or losing failures."""
import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

from fastmcp import Client, FastMCP

from almond_mcp.features.context.tools import register
from almond_mcp.features.components.tools import register as register_holons


A, B = (str(UUID(int=n)) for n in (1, 2))
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
    assert set(result) == {"intersections", "next_step"}
    assert "resolve_object_intersection" in result["next_step"] and "skip" in result["next_step"]
    assert [request["cursor"] for request in calls] == ["", "state:64"]
    assert all(request["expected_model_path"] == MODEL and not request["include_blocks"] for request in calls)


def test_block_exclusion_is_intentional_but_unreadable_geometry_is_not_zero(monkeypatch):
    tool, _, _ = setup(monkeypatch, [page(unsupported=[{"object_id": A, "reason": "block_excluded"}])])
    empty = json.loads(tool(object_ids=[A]))
    assert empty["intersections"]["number"] == 0
    assert "no resolution call is needed" in empty["next_step"]
    assert "resolve_object_intersection" not in empty["next_step"]
    failure = {"object_id": A, "reason": "open_geometry"}
    tool, _, _ = setup(monkeypatch, [page(unsupported=[failure])])
    result = tool(object_ids=[A])
    assert result.is_error
    value = json.loads(result.structured_content["result"])
    assert value["unsupported_objects"] == [failure] and "intersections" not in value


def test_geometry_change_between_pages_does_not_publish_a_partial_count(monkeypatch):
    changed = {"status": "error", "error_code": "stale_scope", "message": "Geometry changed."}
    tool, _, _ = setup(monkeypatch, [page("positive_volume", cursor="state:1"), changed])
    result = tool(object_ids=[A, B])
    assert result.is_error and json.loads(result.structured_content["result"]) == changed


def test_repeated_continuation_cannot_loop_or_inflate_the_count(monkeypatch):
    repeated = page("positive_volume", cursor="state:1")
    tool, calls, _ = setup(monkeypatch, [repeated, repeated])
    result = tool(object_ids=[A, B])
    assert result.is_error and len(calls) == 2


def test_public_schema_has_only_targets_and_singular_include_block(monkeypatch):
    _, calls, server = setup(monkeypatch, [page("positive_volume")])

    async def run():
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = tools["get_object_intersections"].input_schema
            assert set(schema["properties"]) == {"object_ids", "include_block"}
            assert schema["required"] == ["object_ids"]
            assert schema["properties"]["include_block"]["default"] is False
            for extra in ({"max_pairs": 1}, {"cursor": "old"}, {"include_ids": True},
                          {"include_blocks": True}, {"include_block": 1}):
                result = await client.call_tool("get_object_intersections", {"object_ids": [A, B], **extra},
                                               raise_on_error=False)
                assert result.is_error
            assert not calls
            result = await client.call_tool("get_object_intersections", {"object_ids": [A, B], "include_block": True})
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
