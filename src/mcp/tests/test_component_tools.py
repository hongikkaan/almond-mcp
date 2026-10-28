"""Public Component tools against real temporary ledgers and a bounded fake Bridge."""
import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import uuid

import pytest
from fastmcp import Client

from almond_mcp.retrieval_store import AlmondStore


A, B = [str(uuid.UUID(int=value)) for value in (1, 2)]
GROUP = str(uuid.UUID(int=100))
COMPONENT_TOOLS = {
    "upsert_design_component", "get_design_component", "list_design_components",
    "sync_design_component", "remove_design_component", "register_scene_objects",
    "get_scene_objects", "get_modeling_policy",
}


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("component-tools")
    source = Path(__file__).resolve().parents[3] / "src/mcp/server.py"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RHINO_MCP_STATE_DB", str(root / "state.sqlite3"))
        for suffix in ("LIBRARY", "DRAWING_ASSET", "DIAGRAM_ASSET", "GENERATED_ASSET",
                       "DRAWING_RECIPE", "DRAFTING", "CAPSULE", "MATERIAL", "CONSTRUCTION"):
            patch.setenv(f"RHINO_MCP_{suffix}_DIR", str(root / suffix.lower()))
        spec = importlib.util.spec_from_file_location(f"component_server_{uuid.uuid4().hex}", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


@pytest.fixture
def store(server, tmp_path, monkeypatch):
    result = AlmondStore(tmp_path / "components.sqlite3")
    monkeypatch.setattr(server, "retrieval_store", result)
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected Rhino call"))
    return result


@pytest.fixture
def scene(store):
    return store.create_scene("Component context")["scene_id"]


@pytest.fixture
def model(store, tmp_path):
    return store._component_model_path(str(tmp_path / "fixture.3dm"))


def object_row(guid, owner=None):
    return dict(rhino_guid=guid, object_type="Brep", bounds_mm=[0, 0, 0, 100, 200, 300],
                component_id=owner)


def native_component(request):
    return dict(status="success", component=dict(
        complete=True, component_id=request["component_id"],
        model_path=request["expected_model_path"], rhino_group_id=request["rhino_group_id"] or GROUP,
        name=request["name"], scene_ids=request["scene_ids"],
        objects=[object_row(guid, request["component_id"]) for guid in request["object_ids"]],
    ))


@pytest.fixture
def wire(server, monkeypatch):
    def install(handler=native_component, context=None):
        requests = []
        def send(payload):
            request = json.loads(payload)
            requests.append(request)
            if request["type"] == "get_rhino_context":
                response = (dict(status="success", capabilities={"design_components": 1, "component_registry": 2})
                            if context is None else context)
            else:
                response = handler(request)
            if isinstance(response, Exception):
                raise response
            return response if isinstance(response, str) else json.dumps(response)
        monkeypatch.setattr(server, "_send_and_receive", send)
        return requests
    return install


def call(server, tool_name, **arguments):
    tool = getattr(server, tool_name)
    result = getattr(tool, "fn", tool)(**arguments)
    return json.loads(result) if isinstance(result, str) else result


def register(server, model, scene, **extra):
    arguments = dict(expected_model_path=model, name="Panel", object_ids=[A, B], scene_ids=[scene])
    arguments.update(extra)
    return call(server, "upsert_design_component", **arguments)


@pytest.mark.parametrize("change", ["name", "type", "direct_count", "effective_count", "legacy_type", "unchanged"])
def test_live_default_summary_uses_observed_objects_without_writing_cache(server, store, scene, model, wire, change):
    from test_components import snapshot

    def initial(request):
        reply = native_component(request)
        for index, obj in enumerate(reply["component"]["objects"]):
            obj["name"] = ["Old A", "Old B"][index]
        return reply
    wire(initial)
    register(server, model, scene, component_id="live-summary", rhino_group_id=GROUP)
    cached = store.get_component("live-summary")
    observed = {key: deepcopy(cached[key]) for key in (
        "component_id", "model_path", "rhino_group_id", "name", "scene_ids", "child_component_ids",
        "parent_component_id", "objects", "effective_objects", "effective_object_ids")}
    observed.update(complete=True, pending_objects=[], requires_sync=False)
    expected_names, expected_types, counts = ["Old A", "Old B"], {"Brep": 2}, (2, 2)
    if change == "name":
        observed["objects"][0]["name"] = observed["effective_objects"][0]["name"] = "New A"
        expected_names = ["New A", "Old B"]
    elif change in {"type", "legacy_type"}:
        observed["objects"][0]["object_type"] = observed["effective_objects"][0]["object_type"] = "Extrusion"
        expected_types = {"Brep": 1, "Extrusion": 1}
        if change == "legacy_type":
            observed.pop("effective_objects")
            observed.pop("effective_object_ids")
    elif change == "direct_count":
        observed["objects"] = observed["objects"][1:]
        observed["effective_objects"] = observed["effective_objects"][1:]
        observed["effective_object_ids"] = [B]
        expected_names, expected_types, counts = ["Old B"], {"Brep": 1}, (1, 1)
    elif change == "effective_count":
        descendant = dict(object_row(str(uuid.UUID(int=3)), "native-child"), name="Child")
        observed["effective_objects"].append(descendant)
        observed["effective_object_ids"].append(descendant["rhino_guid"])
        observed["child_component_ids"] = ["native-child"]
        counts = (2, 3)
    requests = wire(lambda request: dict(status="success", component=deepcopy(observed)))
    before = snapshot(store)
    summary = call(server, "get_design_component", component_id="live-summary", live=True)["component"]
    detailed = call(server, "get_design_component", component_id="live-summary", live=True,
                    recursive=True, include_ids=True, field_groups=["geometry"])["component"]
    assert summary["live_verified"] is True and summary["requires_sync"] is (change != "unchanged")
    assert summary["object_names"] == detailed["object_names"] == expected_names
    assert summary["object_types"] == detailed["object_types"] == expected_types
    assert (summary["object_count"], summary["effective_object_count"]) == counts
    assert summary["object_count"] == len(detailed["objects"]) == len(detailed["object_ids"])
    assert summary["effective_object_count"] == len(detailed["effective_objects"]) == len(detailed["effective_object_ids"])
    assert "objects" not in summary and "effective_objects" not in summary
    assert all(request.get("action") in {None, "inspect"} for request in requests)
    assert snapshot(store) == before and store.get_component("live-summary") == cached


def test_live_parent_reports_descendant_name_drift_without_changing_cache(server, store, scene, model, wire):
    from test_component_hierarchy import create
    from test_components import snapshot

    store.scene_a, store.model = scene, model
    child = create(store, "Leaf", [A])
    parent = create(store, "Assembly", [B], children=[child["component_id"]])
    cached = store.get_component(parent["component_id"])
    observed = dict(deepcopy(cached), complete=True)
    next(obj for obj in observed["effective_objects"] if obj["rhino_guid"] == A)["name"] = "Renamed leaf"
    wire(lambda request: dict(status="success", component=deepcopy(observed)))
    before = snapshot(store)
    summary = call(server, "get_design_component", component_id=parent["component_id"], live=True)["component"]
    detailed = call(server, "get_design_component", component_id=parent["component_id"], live=True,
                    recursive=True, include_ids=True, field_groups=["geometry"])["component"]
    assert summary["requires_sync"] is True and summary["object_names"] == []
    assert (summary["object_count"], summary["effective_object_count"]) == (1, 2)
    assert next(obj for obj in detailed["effective_objects"] if obj["rhino_guid"] == A)["name"] == "Renamed leaf"
    assert snapshot(store) == before and store.get_component(parent["component_id"]) == cached


def test_public_registration_update_and_cached_reads(server, store, scene, model, wire, monkeypatch):
    requests = wire()
    created = register(server, model, scene, component_id="panel-1", rhino_group_id=GROUP)
    component = created["component"]
    assert created["status"] == "success" and component["live_verified"] is True
    assert component["component_id"] == "panel-1" and component["rhino_group_id"] == GROUP
    assert "scene_ids" not in component and "object_ids" not in component
    assert store.get_component("panel-1")["scene_ids"] == [scene] and store.get_component("panel-1")["object_ids"] == [A, B]
    assert [request["type"] for request in requests] == ["get_rhino_context", "design_component"]
    assert requests[1]["expected_model_path"] == model and requests[1]["action"] == "upsert"
    changed = call(server, "upsert_design_component", expected_model_path=model, component_id="panel-1",
                   name="Smaller panel", object_ids=[B])
    assert store.get_component("panel-1")["scene_ids"] == [scene]
    assert requests[-1]["expected_object_ids"] == [A, B]
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Cached read called Rhino"))
    cached = call(server, "get_design_component", component_id="panel-1", include_ids=True, field_groups=["geometry"])["component"]
    assert cached["live_verified"] is False and cached["object_ids"] == [B]
    listed = call(server, "list_design_components", expected_model_path=model, include_ids=True)
    assert listed["total"] == 1 and listed["live_verified"] is False
    assert listed["components"][0]["name"] == "Smaller panel"
    assert "objects" not in listed["components"][0]
    assert call(server, "get_modeling_policy")["policy"] == server.modeling_policy.POLICY


@pytest.mark.parametrize("scene_ids", [None, [], ["missing-scene"]])
def test_invalid_scene_membership_is_rejected_before_bridge(server, store, scene, model, wire, scene_ids):
    requests = wire()
    response = register(server, model, scene, scene_ids=scene_ids)
    assert response["status"] == "error" and response["message"]
    assert requests == [] and store.list_components() == []


@pytest.mark.parametrize("context", [
    {"status": "success", "capabilities": {}},
    {"status": "error", "message": "offline"},
    "invalid JSON",
    TimeoutError("context unavailable"),
])
def test_capability_preflight_never_mutates_on_old_or_unreachable_bridge(
    server, store, scene, model, wire, context,
):
    before = store.get_scene(scene)
    requests = wire(context=context)
    response = register(server, model, scene)
    assert response["status"] == "error" and response["message"]
    assert "requires_reconciliation" not in response
    assert requests == [{"type": "get_rhino_context", "selection_limit": 0}]
    assert store.list_components() == [] and store.get_scene(scene) == before


def test_timeout_is_one_mutation_and_explicit_inspect_recovers(server, store, scene, model, wire):
    native_success = []
    def lost_response(request):
        native_success.append(native_component(request))
        raise TimeoutError("Native reply was lost")
    before = store.get_scene(scene)
    requests = wire(lost_response)
    response = register(server, model, scene)
    assert response["status"] == "error"
    assert response["error_code"] == "component_reconciliation_required"
    assert response["requires_reconciliation"] is True
    assert response["component_id"] == requests[1]["component_id"]
    assert response["expected_model_path"] == model
    assert [r.get("action") for r in requests] == [None, "upsert"]
    assert len(native_success) == 1 and store.list_components() == []
    assert store.get_scene(scene) == before
    inspections = wire(lambda request: dict(status="success", complete=True, model_path=model,
        editing=dict(mode="model", stable=True), components=[native_success[0]["component"]], problems=[]),
        context=dict(status="success", capabilities=dict(design_components=1, component_registry=2)))
    recovered = call(server, "sync_design_component", expected_model_path=model,
                     component_id=response["component_id"], rhino_group_id=GROUP)
    assert recovered["status"] == "success" and recovered["component"]["live_verified"] is True
    assert "object_ids" not in recovered["component"]
    assert store.get_component(response["component_id"])["scene_ids"] == [scene]
    assert [r.get("action") for r in inspections] == [None, "inspect_many"]
    assert inspections[1]["component_ids"] == [response["component_id"]]


@pytest.mark.parametrize("reply,requires_reconciliation", [
    ({"status": "error", "mutation_applied": False, "message": "Wrong document"}, False),
    ({"status": "error", "rolled_back": True, "message": "Rolled back"}, False),
    ("invalid JSON", True),
    ({"status": "success", "component": {"complete": False}}, True),
])
def test_native_rejection_and_uncertain_success_have_distinct_errors(
    server, store, scene, model, wire, reply, requires_reconciliation,
):
    requests = wire(lambda request: reply)
    response = register(server, model, scene)
    assert response["status"] == "error" and response["message"]
    assert response.get("requires_reconciliation", False) is requires_reconciliation
    assert [r.get("action") for r in requests] == [None, "upsert"]
    assert store.list_components() == []


def test_direct_scene_objects_deduplicate_and_survive_unregister(server, store, scene, model, wire):
    wire()
    component = register(server, model, scene, object_ids=[A])["component"]
    def observe(request):
        return dict(status="success", complete=True, model_path=request["expected_model_path"],
                    objects=[object_row(guid, component["component_id"] if guid == A else None)
                             for guid in request["object_ids"]])
    requests = wire(observe)
    linked = call(server, "register_scene_objects", scene_id=scene, expected_model_path=model,
                  object_ids=[A, B], mode="replace")
    assert linked["status"] == "success" and "object_ids" not in linked
    assert linked["direct_objects"] == 2 and linked["live_verified"] is True
    assert [r.get("action") for r in requests] == [None, "objects"]
    assert requests[1]["object_ids"] == [A, B] and "scene_ids" not in requests[1]
    rows = call(server, "get_scene_objects", scene_id=scene, include_ids=True, field_groups=["geometry"])
    assert rows["total"] == 2 and rows["live_verified"] is False
    assert all(row["direct"] for row in rows["objects"])
    def unregister(request):
        return dict(status="success", component_id=request["component_id"],
                    model_path=request["expected_model_path"], rhino_group_id=request["rhino_group_id"])
    requests = wire(unregister)
    removed = call(server, "remove_design_component", component_id=component["component_id"])
    assert removed["status"] == "success" and removed["component"]["status"] == "unregistered"
    assert [r.get("action") for r in requests] == [None, "unregister"]
    assert requests[1]["expected_object_ids"] == [A]
    rows = call(server, "get_scene_objects", scene_id=scene, include_ids=True, field_groups=["geometry"])
    assert rows["total"] == 2 and all(row["component_id"] is None for row in rows["objects"])
    assert store.get_component(component["component_id"]) is None


@pytest.mark.parametrize("reference_kind", ["plan", "step"])
def test_plan_references_block_public_unregister_before_bridge(server, store, scene, model, wire, reference_kind):
    wire()
    component = register(server, model, scene)["component"]
    plan = store.create_plan("Retain", scope="component",
        component_ids=[component["component_id"]] if reference_kind == "plan" else [])
    if reference_kind == "step":
        store.update_plan_step(plan["plan_id"], "inspect_context", "pending",
                               component_ids=[component["component_id"]])
    requests = wire()
    response = call(server, "remove_design_component", component_id=component["component_id"])
    assert response["status"] == "error" and "referenced" in response["message"]
    assert requests == [] and store.get_component(component["component_id"]) is not None


@pytest.mark.parametrize("tool_name,arguments", [
    ("get_design_component", {"component_id": "missing"}),
    ("list_design_components", {"expected_model_path": "relative.3dm"}),
    ("sync_design_component", {"expected_model_path": "relative.3dm", "component_id": "missing"}),
    ("remove_design_component", {"component_id": "missing"}),
    ("get_scene_objects", {"scene_id": "missing"}),
])
def test_public_component_errors_are_json_without_native_calls(server, store, wire, tool_name, arguments):
    requests = wire()
    response = call(server, tool_name, **arguments)
    assert response["status"] == "error" and response["message"]
    assert requests == [] and store.list_components() == []


def test_actual_mcp_component_schema_and_roundtrip(server, store, scene, model, wire):
    requests = wire()
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert COMPONENT_TOOLS <= tools.keys()
            schema = tools["upsert_design_component"]["inputSchema"]
            assert {"name", "object_ids"} == set(schema["required"])
            assert schema["properties"]["expected_model_path"]["default"] == ""
            assert {"scene_ids", "component_id", "rhino_group_id"} <= schema["properties"].keys()
            for name in ("get_design_component", "list_design_components", "get_scene_objects", "get_modeling_policy"):
                assert tools[name]["annotations"]["readOnlyHint"] is True
            for name in ("remove_design_component", "register_scene_objects"):
                assert tools[name]["annotations"]["destructiveHint"] is False
            policy = await client.call_tool("get_modeling_policy", {})
            assert policy.structured_content["policy"] == server.modeling_policy.POLICY
            created = await client.call_tool("upsert_design_component", dict(
                expected_model_path=model, name="Protocol panel", object_ids=[A], scene_ids=[scene],
            ))
            component = json.loads(created.structured_content["result"])["component"]
            read = await client.call_tool("get_design_component", {"component_id": component["component_id"]})
            assert json.loads(read.structured_content["result"])["component"]["live_verified"] is False
            assert store.get_component(component["component_id"])["object_ids"] == [A]
    asyncio.run(verify())
    assert [r.get("action") for r in requests] == [None, "upsert"]
