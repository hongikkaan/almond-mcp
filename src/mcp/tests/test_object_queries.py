import json
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP

from almond_mcp.features.context import object_queries
from almond_mcp.features.context.tools import register


ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PATH = "C:/model/guardhouse.3dm"


@pytest.fixture
def queries(monkeypatch):
    calls = []
    monkeypatch.setattr(object_queries, "bound_model_path", lambda path: path or PATH)

    def send(encoded):
        payload = json.loads(encoded)
        calls.append(payload)
        if payload["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"object_observation": 1}})
        return json.dumps({"status": "success", "objects": [{"id": ID}], "complete": False, "next_offset": 50})

    context = SimpleNamespace(_send_and_receive=send)
    exports = register(FastMCP("objects-test"), context)
    return SimpleNamespace(**exports, calls=calls, context=context)


def test_query_filters_reach_native_without_group_expansion(queries):
    filters = {"layer_paths": ["M::structure"], "name_contains": "column", "user_dictionary": [
        {"source": "geometry", "key": "levels", "any_of": ["B1", "1F"]}]}
    result = json.loads(queries.get_rhino_objects(scope="ids", object_ids=[ID], filters=filters,
                                                include_geometry=True, include_ids=True))
    assert result["objects"][0]["id"] == ID and not result["complete"]
    assert queries.calls[-1] == {"type": "get_rhino_objects", "scope": "ids", "object_ids": [ID],
                                "filters": filters, "include_geometry": True, "offset": 0, "limit": 50,
                                "expected_model_path": PATH}
    assert len(queries.calls) == 2


@pytest.mark.parametrize("arguments", [
    {"scope": "floor"}, {"scope": "ids"}, {"object_ids": [ID]},
    {"scope": "ids", "object_ids": [ID, ID]}, {"scope": "ids", "object_ids": ["bad"]},
    {"limit": True}, {"limit": 201}, {"offset": -1}, {"include_geometry": 1},
    {"filters": {"floor": "1F"}}, {"filters": {"layer_paths": []}},
    {"filters": {"user_dictionary": [{"source": "auto", "key": "levels", "any_of": ["1F"]}]}},
    {"filters": {"user_dictionary": [{"source": "geometry", "key": "levels", "any_of": [float("nan")]}]}},
])
def test_invalid_query_never_dispatches(queries, arguments):
    result = json.loads(queries.get_rhino_objects(**arguments))
    assert result["error_code"] == "invalid_arguments" and not queries.calls


def test_unsupported_bridge_never_receives_new_request(queries):
    queries.context._send_and_receive = lambda encoded: '{"status":"success","capabilities":{}}'
    assert json.loads(queries.get_object_intersections([ID]))["error_code"] == "unsupported_object_observation"
    assert not queries.calls


def test_intersections_use_explicit_guid_route_without_registration(queries):
    queries.get_object_intersections([ID], max_pairs=3)
    assert queries.calls[-1] == {"type": "get_object_intersections", "object_ids": [ID], "max_pairs": 3,
                                "expected_model_path": PATH}
    assert len(queries.calls) == 2


@pytest.mark.parametrize("ids,max_pairs", [([], 1), ([ID, ID], 2), ([ID], True), ([ID], 65)])
def test_invalid_intersection_is_local(queries, ids, max_pairs):
    result = json.loads(queries.get_object_intersections(ids, max_pairs=max_pairs))
    assert result["error_code"] == "invalid_arguments" and not queries.calls


def test_uncertain_read_is_not_replayed(queries):
    def send(encoded):
        queries.calls.append(json.loads(encoded))
        if len(queries.calls) == 1:
            return '{"status":"success","capabilities":{"object_observation":1}}'
        raise TimeoutError("late read")
    queries.context._send_and_receive = send
    result = json.loads(queries.get_rhino_objects())
    assert result["error_code"] == "bridge_error" and len(queries.calls) == 2
