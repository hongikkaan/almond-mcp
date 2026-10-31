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
            return json.dumps({"status": "success", "capabilities": {"object_observation": 2, "intersection_queries": 1}})
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


def test_summary_and_type_filter_reach_native_without_expensive_detail(queries):
    queries.get_rhino_objects(result_mode="summary", filters={"object_types": ["Mesh"]}, offset=2, limit=4)
    payload = queries.calls[-1]
    assert payload["result_mode"] == "summary" and payload["fields"] is None
    assert payload["filters"] == {"object_types": ["Mesh"]}
    assert payload["include_geometry"] is False and payload["offset"] == 2


def test_explicit_id_field_is_retained_without_second_id_switch(queries):
    def send(encoded):
        payload = json.loads(encoded)
        queries.calls.append(payload)
        if payload["type"] == "get_rhino_context":
            return '{"status":"success","capabilities":{"object_observation":2}}'
        return json.dumps({"status": "success", "complete": True, "objects": [{"id": ID}]})
    queries.context._send_and_receive = send
    result = json.loads(queries.get_rhino_objects(fields=["id"]))
    assert result["objects"] == [{"id": ID}]
    assert queries.calls[-1]["fields"] == ["id"]


def test_default_query_still_omits_ids_on_complete_result(queries):
    queries.context._send_and_receive = lambda raw: (
        '{"status":"success","capabilities":{"object_observation":1}}'
        if json.loads(raw)["type"] == "get_rhino_context" else
        json.dumps({"status": "success", "complete": True, "objects": [{"id": ID, "name": "column"}]}))
    assert json.loads(queries.get_rhino_objects())["objects"] == [{"name": "column"}]


def test_face_continuation_binds_explicit_objects_to_observed_crc(queries):
    queries.get_rhino_objects(scope="ids", object_ids=[ID], fields=["faces"],
                              face_offset=128, face_limit=64, expected_geometry_crcs={ID: 123})
    payload = queries.calls[-1]
    assert payload["face_offset"] == 128 and payload["face_limit"] == 64
    assert payload["expected_geometry_crcs"] == {ID: 123}


@pytest.mark.parametrize("arguments", [
    {"result_mode": "counts"}, {"fields": []}, {"fields": ["id", "id"]}, {"fields": ["arbitrary"]},
    {"fields": ["id"], "face_offset": 1}, {"fields": ["faces"], "face_offset": 128},
    {"scope": "ids", "object_ids": [ID], "fields": ["faces"], "face_offset": 1},
    {"scope": "ids", "object_ids": [ID], "expected_geometry_crcs": {ID: True}},
    {"result_mode": "summary", "include_geometry": True}, {"result_mode": "summary", "fields": ["id"]},
    {"filters": {"object_types": []}}, {"face_limit": 0}, {"face_offset": True},
])
def test_invalid_extended_query_never_dispatches(queries, arguments):
    result = json.loads(queries.get_rhino_objects(**arguments))
    assert result["error_code"] == "invalid_arguments" and queries.calls == []


def test_extended_queries_cannot_silently_run_on_older_bridge(queries):
    calls = []
    def send(encoded):
        calls.append(json.loads(encoded))
        return '{"status":"success","capabilities":{"object_observation":1}}'
    queries.context._send_and_receive = send
    result = json.loads(queries.get_rhino_objects(fields=["id"]))
    assert result["error_code"] == "unsupported_object_observation"
    assert len(calls) == 1 and calls[0]["type"] == "get_rhino_context"


def test_intersection_continuation_and_block_scope_are_forwarded(queries):
    queries.get_object_intersections([ID], include_blocks=True, cursor="observed-state:64")
    assert queries.calls[-1]["include_blocks"] is True
    assert queries.calls[-1]["cursor"] == "observed-state:64"


def test_complete_intersection_keeps_actionable_pair_handles_without_include_ids(queries):
    pair = {"a": {"handle": {"object_id": ID, "path": []}},
            "b": {"handle": {"object_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "path": []}},
            "pair_state": "observed-state", "overlap": {"status": "positive_volume"}}
    def send(encoded):
        if json.loads(encoded)["type"] == "get_rhino_context":
            return '{"status":"success","capabilities":{"intersection_queries":1}}'
        return json.dumps({"status": "success", "complete": True, "object_ids": [ID], "pairs": [pair]})
    queries.context._send_and_receive = send
    result = json.loads(queries.get_object_intersections([ID]))
    assert result["pairs"] == [pair] and "object_ids" not in result
