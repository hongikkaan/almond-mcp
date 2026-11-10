"""Editor refusals must reach MCP clients as errors with the original evidence."""
import asyncio
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.components.tools import register as components
from almond_mcp.features.modeling.tools import register as modeling
from almond_mcp.features.planning.tools import register as planning
from almond_mcp.features.scenes.tools import register as scenes
from almond_mcp.features.context.tools import register as observations

MODEL = r"C:\offline\editor.3dm"
OBJECT = str(UUID(int=1))
EDIT = {"object_id": OBJECT, "face_index": 0, "expected_geometry_crc": 42, "translation": [1, 0, 0]}


@pytest.mark.parametrize("name,args", [
    ("edit_planar_face", EDIT), ("edit_planar_faces", {"edits": [EDIT]}),
    ("get_ontological_holon", {"holon_id": "holon_existing", "live": True}),
    ("get_scene_objects", {"scene_id": "scene_existing"}),
    ("get_selection_references", {}),
    ("analyze_block_reculviely", {"mode": "resolve-block", "options": {"path": [OBJECT]}}),
])
def test_editor_failure_sets_mcp_error_and_preserves_native_evidence(monkeypatch, name, args):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    failure = {"status": "error", "message": "Editing membership is unavailable.",
               "error_code": "unstable_editing_scope", "mutation_state": "not_started",
               "mutation_applied": False}
    calls = []
    def send(raw, **kwargs):
        request = json.loads(raw)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {
                "face_edit": 1, "face_edit_batch": 1, "component_operations": 1, "intersection_queries": 1, "block_analysis": 1},
                "document": {"path": MODEL}, "selection": {"objects": [{"id": OBJECT}], "total": 1, "truncated": False}})
        return json.dumps(failure)
    def refused(*args, **kwargs):
        raise ValueError(failure["message"])
    store = SimpleNamespace(get_component=refused, scene_objects=refused, selection_references=refused,
                            _generation_limit=lambda *_: None, _component_model_path=lambda value: value)
    context = SimpleNamespace(_send_and_receive=send, retrieval_store=store)
    server = FastMCP("editor-errors")
    for key, value in components(server, context).items():
        setattr(context, key, value)
    modeling(server, context)
    scenes(server, context)
    planning(server, context)
    observations(server, context)

    async def call():
        async with Client(server) as client:
            return await client.call_tool(name, args, raise_on_error=False)
    response = asyncio.run(call())
    assert response.is_error
    serialized = response.structured_content["result"]
    body = json.loads(serialized)
    assert body["status"] == "error" and body["message"] == failure["message"]
    assert response.content[0].text == serialized
    if name in {"edit_planar_face", "edit_planar_faces"}:
        assert body["mutation_applied"] is False and body["mutation_state"] == "not_started"


def test_native_editor_guidance_survives_real_store_and_public_query_errors(tmp_path, monkeypatch):
    from almond_mcp.retrieval_store import AlmondStore
    from test_component_group_inference import snapshot, MODEL as SAVED_MODEL, GROUP, COMPONENT, OBJECT as MEMBER

    monkeypatch.setenv("ALMOND_MODEL_PATH", SAVED_MODEL)
    store = AlmondStore(tmp_path / "editor-guidance.sqlite3")
    scene = store.create_scene("Arrival")
    reply = {"status": "success", "component": snapshot(scene["scene_id"])}
    def send(raw, **kwargs):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {
                "design_components": 1, "component_registry": 2, "component_group_inference": 1},
                "document": {"path": SAVED_MODEL}, "selection": {"objects": [{"id": MEMBER}], "total": 1, "truncated": False}})
        return json.dumps(reply)
    context = SimpleNamespace(retrieval_store=store, _send_and_receive=send)
    server = FastMCP("native-editor-guidance")
    registered = components(server, context)
    for key, value in registered.items():
        setattr(context, key, value)
    registered["upsert_ontological_holon"](name="Arrival", holon_id=COMPONENT,
        expected_model_path=SAVED_MODEL, rhino_group_id=GROUP, scene_ids=[scene["scene_id"]])
    scenes(server, context)
    planning(server, context)
    before = store.get_component(COMPONENT)
    reply = {"status": "error", "error_code": "unstable_editing_scope", "message": "Ownership unverified",
             "editing": {"mode": "group", "stable": False}, "mutation_applied": False,
             "membership_available": False, "next_step_guide": 'Use get_objects(scope="current", include_ids=true); working IDs are not component ownership proof.'}

    async def run():
        async with Client(server) as client:
            for name, arguments in [
                ("get_ontological_holon", {"holon_id": COMPONENT, "live": True}),
                ("get_scene_objects", {"scene_id": scene["scene_id"]}),
                ("get_selection_references", {}),
            ]:
                result = await client.call_tool(name, arguments, raise_on_error=False)
                assert result.is_error
                body = json.loads(result.content[0].text)
                assert body.get("error_code") == "unstable_editing_scope", (name, body)
                assert body["membership_available"] is False and body["mutation_applied"] is False
                assert "get_objects" in body["next_step_guide"] and "holon ownership" in body["next_step_guide"]
                assert body["editing"] == reply["editing"]
    asyncio.run(run())
    assert store.get_component(COMPONENT) == before
