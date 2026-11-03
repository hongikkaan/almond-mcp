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
    ("get_holon_intersections", {"holon_ids": ["holon_existing"]}),
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
    if name in {"edit_planar_face", "edit_planar_faces", "get_holon_intersections"}:
        assert body["mutation_applied"] is False and body["mutation_state"] == "not_started"
