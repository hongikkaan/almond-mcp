"""Context catalogues and selection keep distinct public contracts."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from almond_mcp.features.context.tools import register


def fixture_tools():
    calls = []
    response = {"status": "success", "capabilities": {"context_sections": 2}, "warnings": [],
                "document": {"name": "private.3dm", "path": "private/path.3dm", "runtime_serial_number": 42,
                             "units": "Millimeters", "absolute_tolerance": .01, "angle_tolerance_radians": .02,
                             "modified": True, "object_count": 7, "layer_count": 3},
                "editor": {"mode": "block", "stable": False, "target": {"id": "target", "name": "Block"},
                           "warnings": ["Editing is active."], "evidence": {"providers": ["verified"], "document_serial_number": 42}},
                "viewport": {"id": "viewport", "name": "Perspective"},
                "viewports": [{"id": "viewport", "name": "Perspective"}],
                "named_views": [{"id": "named", "name": "Entrance"}],
                "layouts": [{"id": "layout", "name": "A3"}],
                "display_modes": [{"id": "mode", "name": "Shaded"}],
                "selection": {"total": 2, "returned": 1, "truncated": True, "depth_limited": False,
                              "selected_object_count": 4, "objects": [{"id": "selected", "name": "Group"}]},
                "image": {"data": "must never escape the context projection"}}

    def send(payload):
        calls.append(json.loads(payload))
        return json.dumps(response)

    server = FastMCP("context-sections-test")
    return register(server, SimpleNamespace(_send_and_receive=send)), calls, response, server


@pytest.mark.parametrize("options", [{}, {"include_ids": True}, {"include_editor_details": True}])
def test_default_only_hint_catalogue_ids_and_document_projection(options):
    tools, calls, _, _ = fixture_tools()
    result = json.loads(tools["get_rhino_context"](**options))
    assert set(result) == {"status", "warnings", "document", "named_views", "layouts", "display_modes", "next_step_guide"}
    assert "get_current_viewcapture" in result["next_step_guide"]
    assert result["document"] == {"units": "Millimeters", "absolute_tolerance": .01, "angle_tolerance": .02,
                                  "modified": True, "object_count": 7, "layer_count": 3}
    for section in ("named_views", "layouts", "display_modes"):
        assert "id" in result[section][0]
    assert calls == [{"type": "get_rhino_context", "public_context": True,
                      "sections": ["document", "named_views", "layouts", "display_modes"]}]


@pytest.mark.parametrize("sections", [[], ["document"], ["viewport"], ["named_views", "layouts"], ["display_modes"]])
def test_explicit_sections_do_not_add_editor_images_or_hint(sections):
    tools, calls, _, _ = fixture_tools()
    result = json.loads(tools["get_rhino_context"](sections=sections))
    assert set(result) == {"status", "warnings", *sections}
    assert calls[0]["sections"] == sections


def test_editor_warning_and_unknown_state_survive_compaction_but_details_are_opt_in():
    tools, _, response, _ = fixture_tools()
    response["editor"].update(mode="unknown", stable=False, target=None)
    compact = json.loads(tools["get_rhino_context"](sections=["editor"]))["editor"]
    assert compact == {"mode": "unknown", "stable": False, "target": None, "warnings": ["Editing is active."]}
    detailed = json.loads(tools["get_rhino_context"](sections=["editor"], include_editor_details=True))["editor"]
    assert detailed["evidence"] == {"providers": ["verified"]}
    identified = json.loads(tools["get_rhino_context"](sections=["editor"], include_editor_details=True, include_ids=True))["editor"]
    assert identified["evidence"]["document_serial_number"] == 42


def test_other_ids_still_follow_include_ids():
    tools, _, _, _ = fixture_tools()
    without = json.loads(tools["get_rhino_context"](sections=["viewport", "editor", "viewports"]))
    assert "id" not in without["viewport"] and "id" not in without["editor"]["target"]
    assert "id" not in without["viewports"][0]
    with_ids = json.loads(tools["get_rhino_context"](sections=["viewport"], include_ids=True))
    assert with_ids["viewport"]["id"] == "viewport"


@pytest.mark.parametrize("name, options", [
    ("get_rhino_context", {"sections": ["selection"]}),
    ("get_rhino_context", {"sections": [None]}),
    ("get_rhino_context", {"include_editor_details": 1}),
    ("get_objects", {"limit": True}),
    ("get_objects", {"depth": 9}),
])
def test_invalid_inputs_do_not_dispatch_and_have_mcp_error_flag(name, options):
    tools, calls, _, _ = fixture_tools()
    result = tools[name](**options)
    assert isinstance(result, ToolResult) and result.is_error
    assert json.loads(result.structured_content["result"])["error_code"] == "invalid_arguments"
    assert calls == []


def test_old_bridge_or_missing_observations_are_errors_not_empty_catalogues():
    tools, _, response, _ = fixture_tools()
    response["capabilities"]["context_sections"] = 1
    result = tools["get_rhino_context"]()
    assert result.is_error and "unsupported_context" in result.structured_content["result"]
    response["capabilities"]["context_sections"] = 2
    del response["named_views"]
    result = tools["get_rhino_context"]()
    assert result.is_error and "omitted requested sections" in result.structured_content["result"]


def test_native_errors_and_unavailable_observations_are_preserved():
    tools, _, response, _ = fixture_tools()
    response["named_views"] = None
    response["warnings"] = ["named_views: unavailable"]
    result = json.loads(tools["get_rhino_context"](sections=["named_views"]))
    assert result["named_views"] is None and result["warnings"] == response["warnings"]
    response.clear()
    response.update(status="error", error_code="no_document", warnings=["Disconnected"])
    for name in ("get_rhino_context",):
        result = tools[name]()
        assert result.is_error and json.loads(result.structured_content["result"]) == response


def test_public_schema_removes_image_and_selection_arguments_from_context():
    _, _, _, server = fixture_tools()
    tools = {t.name: t.to_mcp_tool().model_dump(mode="json", by_alias=True) for t in asyncio.run(server.list_tools())}
    assert set(tools["get_rhino_context"]["inputSchema"]["properties"]) == {"sections", "include_ids", "include_editor_details"}
    assert "get_objects" in tools
    assert not {"get_rhino_selection", "get_rhino_objects"}.intersection(tools)
