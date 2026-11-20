"""Unified public object queries at the fixed native transport boundary.

These tests do not certify live Rhino grouping, transforms or geometry.
"""
import asyncio
import copy
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP
from fastmcp.tools import ToolResult

from almond_mcp.features.context.tools import register


MODEL = r"C:\offline\objects.3dm"
A, B, GROUP = (str(UUID(int=n)) for n in (1, 2, 3))


def tools_for(reply=None, version=4):
    calls = []

    def send(raw):
        request = json.loads(raw)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"object_observation": version}})
        return json.dumps(copy.deepcopy(reply or {"status": "success", "complete": True, "objects": []}))

    server = FastMCP("objects-contract")
    tools = register(server, SimpleNamespace(_send_and_receive=send))
    return tools, calls, server


@pytest.mark.parametrize("arguments", [
    {"scope": "groups"}, {"scope": "groups", "group_ids": ["holon_name"]},
    {"scope": "groups", "group_ids": [GROUP, GROUP.upper()]},
    {"scope": "selected", "group_ids": [GROUP]},
    {"scope": "document", "group_ids": [GROUP], "object_ids": [A]},
    {"scope": "current", "object_ids": [A]},
    {"scope": "document", "selected": True},
    {"scope": "document", "inside_window": True},
    {"selected": True, "inside_window": True},
    {"result_mode": "summary", "recursive": True},
    {"result_mode": "hierarchy", "depth": True},
    {"result_mode": "hierarchy", "depth": 9},
    {"result_mode": "hierarchy", "recursive": 1},
    {"result_mode": "hierarchy", "include_geometry": True},
    {"result_mode": "hierarchy", "fields": ["faces"]},
    {"scope": "document", "object_ids": [A], "face_offset": 1, "fields": ["faces"]},
    {"offset": 1}, {"offset": 1, "expected_snapshot": "bad"},
])
def test_invalid_or_ambiguous_scope_never_dispatches(arguments):
    tools, calls, _ = tools_for()
    result = tools["get_objects"](**arguments)
    assert isinstance(result, ToolResult) and result.is_error
    assert json.loads(result.structured_content["result"])["error_code"] == "invalid_arguments"
    assert not calls


@pytest.mark.parametrize("arguments", [
    {}, {"scope": "document", "group_ids": [GROUP]},
    {"selected": True, "recursive": True, "depth": 3},
])
def test_old_bridge_cannot_silently_ignore_new_scope_or_expansion(arguments):
    tools, calls, _ = tools_for(version=3)
    result = tools["get_objects"](expected_model_path=MODEL, **arguments)
    assert result.is_error
    assert "object_observation>=4" in result.structured_content["result"]
    assert [c["type"] for c in calls] == ["get_rhino_context"]


def test_group_members_use_group_namespace_and_bound_fixed_query_without_selection():
    tools, calls, _ = tools_for()
    tools["get_objects"](scope="document", group_ids=[GROUP], expected_model_path=MODEL, fields=["id"])
    assert len(calls) == 2
    request = calls[1]
    assert request["type"] == "get_rhino_objects"  # Deliberately retained private native route.
    assert request["scope"] == "document" and request["group_ids"] == [GROUP]
    assert request["object_ids"] == []
    assert request["expected_model_path"] == MODEL
    assert not request["recursive"] and not request["selected"] and not request["inside_window"]


def test_selected_hierarchy_retains_parent_relationships_and_distinguishes_occurrence_handles():
    reply = {"status": "success", "complete": True, "source_count": 2, "matched_count": 2,
             "hierarchy_count": 3, "depth_limited": True, "nodes": [
        {"number": 1, "parent_number": None, "entity_kind": "group", "id": GROUP, "children_state": "expanded"},
        {"number": 2, "parent_number": 1, "entity_kind": "block", "id": A,
         "root_object_id": A, "block_path_ids": [], "document_object": True},
        {"number": 3, "parent_number": 2, "entity_kind": "object", "id": B,
         "root_object_id": A, "block_path_ids": [B], "document_object": False, "visible": None}]}
    tools, calls, _ = tools_for(reply)
    options = dict(scope="current", selected=True, recursive=True,
                   depth=3, expected_model_path=MODEL)
    compact = json.loads(tools["get_objects"](**options))
    assert compact["depth_limited"] is True
    assert [n["parent_number"] for n in compact["nodes"]] == [None, 1, 2]
    assert "id" not in compact["nodes"][0]
    assert compact["nodes"][2]["document_object"] is False
    identified = json.loads(tools["get_objects"](**options, include_ids=True))
    assert identified == reply
    assert calls[-1]["scope"] == "current" and calls[-1]["depth"] == 3
    assert calls[-1]["recursive"] and calls[-1]["selected"]
    assert calls[-1]["result_mode"] == "hierarchy"


def test_face_page_identity_and_crc_contract_survives_public_rename():
    reply = {"status": "success", "complete": True, "objects": [
        {"id": A, "geometry_crc": 42, "faces": [{"face_index": 128}],
         "face_page": {"complete": False, "offset": 128, "next_offset": 129}}]}
    tools, calls, _ = tools_for(reply)
    result = json.loads(tools["get_objects"](scope="document", object_ids=[A], fields=["faces"],
        face_offset=128, expected_geometry_crcs={A: 42}, expected_model_path=MODEL))
    assert "face_offset" in result.pop("next_step_guide")
    assert result == reply
    assert calls[-1]["expected_geometry_crcs"] == {A: 42}
    assert calls[-1]["face_offset"] == 128


def test_incomplete_hierarchy_preserves_out_of_page_parent_and_diagnostics():
    reply = {"status": "success", "complete": False, "next_offset": 3, "depth_limited": True,
             "nodes": [{"number": 3, "parent_number": 1, "id": A, "children_state": "depth_limit"}]}
    tools, _, _ = tools_for(reply)
    result = json.loads(tools["get_objects"](selected=True, result_mode="hierarchy", offset=2,
                                            limit=1, expected_model_path=MODEL, expected_snapshot="a" * 64))
    assert "expected_snapshot" in result.pop("next_step_guide")
    assert result == {**reply, "nodes": [{k: v for k, v in reply["nodes"][0].items() if k != "id"}]}
    assert result["complete"] is False and result["nodes"][0]["parent_number"] == 1


@pytest.mark.parametrize("complete", [True, False])
def test_public_object_output_omits_document_metadata_without_losing_coverage(complete):
    reply = {"status": "success", "complete": complete, "objects": [], "next_offset": 50,
             "warnings": ["depth limited"], "schema": "native/v1", "model_path": MODEL,
             "document_units": "Millimeters", "tolerance_model_units": 0.001}
    tools, calls, _ = tools_for(reply)
    result = json.loads(tools["get_objects"](expected_model_path=MODEL))
    assert result == {key: value for key, value in reply.items()
                      if key not in {"schema", "model_path", "document_units", "tolerance_model_units"}}
    assert calls[-1]["expected_model_path"] == MODEL  # Binding remains an internal native requirement.


def test_real_mcp_discovery_exposes_one_query_and_strict_expansion_inputs():
    _, calls, server = tools_for()

    async def exercise():
        async with Client(server) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert "inspect_02-get_objects" in names
            assert not {"get_rhino_objects", "get_rhino_selection"}.intersection(names)
            result = await client.call_tool("inspect_02-get_objects", {"result_mode": "hierarchy", "depth": True}, raise_on_error=False)
            assert result.is_error

    asyncio.run(exercise())
    assert not calls


def test_dictionary_filter_rejects_a_single_object_with_a_copyable_array_example():
    _, calls, server = tools_for()
    condition = {"source": "attributes", "key": "brief_probe", "any_of": ["yes"]}

    async def call():
        async with Client(server) as client:
            return await client.call_tool(
                "inspect_02-get_objects",
                {"filters": {"user_dictionary": condition}},
                raise_on_error=False,
            )

    result = asyncio.run(call())
    assert result.is_error
    detail = json.loads(result.structured_content["result"])
    assert detail["error_code"] == "invalid_arguments"
    assert "filters.user_dictionary" in detail["message"]
    assert "JSON array" in detail["message"]
    assert json.dumps({"user_dictionary": [condition]}, separators=(",", ":")) in detail["message"]
    assert not calls


@pytest.mark.parametrize("conditions", [
    [{"source": "attributes", "key": "brief_probe", "any_of": ["yes"]}],
    [
        {"source": "attributes", "key": "brief_probe", "any_of": ["yes", "maybe"]},
        {"source": "geometry", "key": "phase", "any_of": [True, 2, 3.5]},
    ],
])
def test_dictionary_filter_accepts_one_or_more_conditions(conditions):
    _, calls, server = tools_for()

    async def call():
        async with Client(server) as client:
            return await client.call_tool(
                "inspect_02-get_objects",
                {"filters": {"user_dictionary": conditions}, "expected_model_path": MODEL},
            )

    result = asyncio.run(call())
    assert json.loads(result.structured_content["result"])["status"] == "success"
    transmitted = calls[-1]["filters"]["user_dictionary"]
    assert json.dumps(transmitted, sort_keys=True) == json.dumps(conditions, sort_keys=True)


def test_dictionary_filter_shape_and_example_are_discoverable():
    _, _, server = tools_for()

    async def list_tools():
        async with Client(server) as client:
            return await client.list_tools()

    tools = asyncio.run(list_tools())
    get_objects = next(tool for tool in tools if tool.name == "inspect_02-get_objects")
    assert '{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}' in (
        get_objects.description
    )
    filters_description = get_objects.input_schema["properties"]["filters"]["description"]
    assert "조건 객체 1개도 배열로 지정" in filters_description


@pytest.mark.parametrize("mode", ["objects", "hierarchy"])
def test_attribute_text_is_independent_of_dictionary(mode):
    tools, calls, _ = tools_for(version=5)
    filters = {"user_text": [{"key": "floor", "any_of": ["2F"]}],
               "user_dictionary": [{"source": "geometry", "key": "floor", "any_of": [2]}]}
    result = tools["get_objects"](expected_model_path=MODEL, result_mode=mode,
                                  fields=["user_text", "user_dictionary"], filters=filters)
    assert calls[-1]["filters"] == filters
    assert calls[-1]["fields"] == ["user_text", "user_dictionary"]
    assert not isinstance(result, ToolResult) or not result.is_error


@pytest.mark.parametrize("args", [{"fields": ["user_text"]}, {"filters": {"user_text": [{"key": "floor", "any_of": ["2F"]}]}}])
def test_old_bridge_rejects_text_before_observation(args):
    tools, calls, _ = tools_for(version=4)
    assert tools["get_objects"](expected_model_path=MODEL, **args).is_error
    assert [call["type"] for call in calls] == ["get_rhino_context"]


@pytest.mark.parametrize("condition", [{"key": "floor", "any_of": [2]}, {"key": "floor", "any_of": []},
                                       {"source": "geometry", "key": "floor", "any_of": ["2F"]}])
def test_text_rejects_dictionary_types_and_sources(condition):
    tools, calls, _ = tools_for(version=5)
    assert tools["get_objects"](filters={"user_text": [condition]}).is_error
    assert not calls


@pytest.mark.parametrize("include_ids", [False, True])
def test_stored_text_keys_and_path_like_values_are_verbatim(include_ids):
    projection = {"values": {"asset_id": "chair", "path": r"C:\archive\linked.3dm", "id": "owner"},
                  "total_keys": 3, "truncated": False}
    tools, _, _ = tools_for({"status": "success", "objects": [{"id": A, "user_text": projection}]}, version=5)
    result = json.loads(tools["get_objects"](expected_model_path=MODEL, fields=["user_text"], include_ids=include_ids))
    assert result["objects"][0]["user_text"] == projection
    assert ("id" in result["objects"][0]) == include_ids
