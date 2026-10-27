"""Run Component contracts through the extracted factory and store mixin."""
import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from fastmcp import Client, FastMCP
import pytest

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.components.store import ComponentsStore
from almond_mcp.features.components.tools import register
from almond_mcp.retrieval_store import AlmondStore


# Before coordinator cutover, override the original methods with the extracted
# mixin. After cutover AlmondStore already includes it, so keep one MRO entry.
if issubclass(AlmondStore, ComponentsStore):
    FeatureStore = AlmondStore
else:
    class FeatureStore(ComponentsStore, AlmondStore):
        pass


TOOL_NAMES = {
    "list_design_components", "get_design_component", "upsert_design_component",
    "sync_design_component", "remove_design_component", "focus_components",
    "get_component_intersections",
}
HELPER_NAMES = {"_component_bridge", "_component_error", "_component_operation_bridge"}


def _server(database):
    namespace = SimpleNamespace(mcp=FastMCP("extracted-components"),
                                retrieval_store=FeatureStore(database))
    namespace._send_and_receive = lambda *_: pytest.fail("Unexpected Rhino call")
    namespace.context = FeatureContext(vars(namespace))
    namespace.exports = register(namespace.mcp, namespace.context)
    vars(namespace).update(namespace.exports)
    return namespace


@pytest.fixture
def server(tmp_path):
    return _server(tmp_path / "factory.sqlite3")


def _regression_suite(filename, class_name, fixtures, excluded=()):
    """Reuse existing cases without changing their original fixture/module state."""
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"_extracted_{path.stem}", path)
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    source.AlmondStore = FeatureStore
    members = {"__module__": __name__}
    for name, value in vars(source).items():
        if (name.startswith("test_") and name not in excluded) or name in fixtures:
            members[name] = staticmethod(value)
    return type(class_name, (), members)


TestExtractedOwnership = _regression_suite(
    "test_components.py", "TestExtractedOwnership", ("store", "model"),
)
TestExtractedHierarchy = _regression_suite(
    "test_component_hierarchy.py", "TestExtractedHierarchy", ("store",),
)
TestExtractedOperations = _regression_suite(
    "test_component_operation_tools.py", "TestExtractedOperations", (),
)
TestExtractedPublicComponents = _regression_suite(
    "test_component_tools.py", "TestExtractedPublicComponents", ("store", "scene", "model", "wire"),
    excluded={
        # These cases also require separately owned Scene/modeling factories.
        # The Component-only lifecycle and actual protocol are covered below.
        "test_public_registration_update_and_cached_reads",
        "test_direct_scene_objects_deduplicate_and_survive_unregister",
        "test_public_component_errors_are_json_without_native_calls",
        "test_actual_mcp_component_schema_and_roundtrip",
    },
)


def _call(server, tool_name, **arguments):
    tool = getattr(server, tool_name)
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def test_extracted_factory_protocol_and_complete_component_lifecycle(server, tmp_path):
    scene_id = server.retrieval_store.create_scene("Facade")["scene_id"]
    model_path = str(tmp_path / "model.3dm")
    object_id = "00000000-0000-0000-0000-000000000001"
    group_id = "00000000-0000-0000-0000-000000000064"
    calls = []

    def native(payload):
        request = json.loads(payload)
        calls.append(request)
        if request["type"] == "get_rhino_context":
            result = {"status": "success", "capabilities": {"design_components": 1}}
        elif request["action"] == "upsert":
            result = {"status": "success", "component": {
                "complete": True, "component_id": request["component_id"],
                "model_path": request["expected_model_path"], "rhino_group_id": group_id,
                "name": request["name"], "scene_ids": request["scene_ids"],
                "objects": [{"rhino_guid": object_id, "object_type": "Brep",
                             "component_id": request["component_id"],
                             "bounds_mm": [0, 0, 0, 100, 200, 300]}],
            }}
        elif request["action"] == "inspect":
            result = {"status": "success", "component": dict(
                server.retrieval_store.get_component(request["component_id"]), complete=True)}
        else:
            assert request["action"] == "unregister"
            result = {"status": "success", "component_id": request["component_id"],
                      "model_path": request["expected_model_path"], "rhino_group_id": group_id}
        return json.dumps(result)

    server._send_and_receive = native

    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert tools.keys() == TOOL_NAMES
            for name in ("list_design_components", "get_design_component", "get_component_intersections"):
                assert tools[name]["annotations"]["readOnlyHint"] is True
            for name in ("remove_design_component", "focus_components"):
                assert tools[name]["annotations"]["destructiveHint"] is False
            assert tools["get_component_intersections"]["inputSchema"]["properties"]["max_pairs"]["default"] == 64
            schema = tools["upsert_design_component"]["inputSchema"]
            assert set(schema["required"]) == {"name", "object_ids"}
            assert schema["properties"]["child_component_ids"]["default"] is None
            created = await client.call_tool("upsert_design_component", {
                "expected_model_path": model_path, "name": "Panel", "object_ids": [object_id],
                "scene_ids": [scene_id], "component_id": "panel-1",
            })
            assert json.loads(created.structured_content["result"])["component"]["live_verified"] is True
            read = await client.call_tool("get_design_component", {"component_id": "panel-1", "include_ids": True, "field_groups": ["geometry"]})
            assert json.loads(read.structured_content["result"])["component"]["object_ids"] == [object_id]

    asyncio.run(verify())
    assert [request.get("action") for request in calls] == [None, "upsert"]
    listed = _call(server, "list_design_components", expected_model_path=model_path)
    assert listed["total"] == 1 and listed["live_verified"] is False
    assert "objects" not in listed["components"][0]
    updated = _call(server, "upsert_design_component", expected_model_path=model_path,
                    name="Renamed panel", object_ids=[object_id], component_id="panel-1")
    assert updated["component"]["scene_ids"] == [scene_id]
    revision = server.retrieval_store.get_scene(scene_id)["revision"]
    synced = _call(server, "sync_design_component", expected_model_path=model_path, component_id="panel-1")
    assert synced["component"]["live_verified"] is True
    assert server.retrieval_store.get_scene(scene_id)["revision"] == revision
    removed = _call(server, "remove_design_component", component_id="panel-1")
    assert removed["component"]["status"] == "unregistered"
    assert server.retrieval_store.get_component("panel-1") is None
    with server.retrieval_store._connect() as connection:
        row = connection.execute("SELECT rhino_guid, component_id FROM document_objects").fetchone()
        assert tuple(row) == (object_id, None)
    assert _call(server, "get_design_component", component_id="panel-1")["status"] == "error"


def test_factories_keep_runtime_sender_and_store_rebinding_isolated(tmp_path):
    first = _server(tmp_path / "first.sqlite3")
    second = _server(tmp_path / "second.sqlite3")
    assert set(first.exports) == TOOL_NAMES | HELPER_NAMES
    assert FeatureStore.get_component is ComponentsStore.get_component
    events = []

    class ReboundStore:
        def list_components(self, model_path):
            events.append(model_path)
            return [{"component_id": "rebound"}]

    first.retrieval_store = ReboundStore()
    assert _call(first, "list_design_components", include_ids=True)["components"] == [{"component_id": "rebound"}]
    assert _call(second, "list_design_components")["components"] == []
    assert events == [""]
    first.retrieval_store = FeatureStore(tmp_path / "replacement.sqlite3")

    def sender(marker):
        def send(payload):
            request = json.loads(payload)
            events.append((marker, request["type"]))
            if request["type"] == "get_rhino_context":
                return json.dumps({"status": "success", "capabilities": {"component_operations": 1}})
            return json.dumps({"status": "success", "marker": marker})
        return send

    first._send_and_receive = sender("first")
    second._send_and_receive = sender("second")
    arguments = {"expected_model_path": r"C:\Models\fixture.3dm", "component_ids": ["panel"]}
    assert _call(first, "focus_components", **arguments)["marker"] == "first"
    assert _call(second, "focus_components", **arguments)["marker"] == "second"
    first._send_and_receive = sender("replacement")
    assert _call(first, "focus_components", **arguments)["marker"] == "replacement"
    with first.context.override(_send_and_receive=sender("override")):
        assert _call(first, "focus_components", **arguments)["marker"] == "override"
    assert _call(first, "focus_components", **arguments)["marker"] == "replacement"
    assert len(events) == 11
