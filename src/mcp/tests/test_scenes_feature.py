"""Extracted Scene factory and store contracts with temporary SQLite and fake native IO."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.scenes.tools import register
from almond_mcp.retrieval_store import AlmondStore
import test_components as component_contracts


ExtractedScenesStore = AlmondStore


A, B = component_contracts.A, component_contracts.B
SCENE_TOOLS = {"list_design_scenes", "update_design_scene", "create_design_scene", "get_design_scene", "register_scene_objects", "get_scene_objects"}


@pytest.fixture
def store(tmp_path):
    result = ExtractedScenesStore(tmp_path / "scenes.sqlite3")
    result.fixture_scene_id = result.create_scene("Scene fixture")["scene_id"]
    return result


@pytest.fixture
def model(store, tmp_path):
    return store._component_model_path(str(tmp_path / "fixture.3dm"))


def unexpected_native(*_):
    pytest.fail("A cached read or rejected request called native IO")


def test_agent_can_list_project_scene_names_without_plan_or_document_lookup(feature, store):
    """Given scenes in several files, one names query returns a bounded project page."""
    store.create_scene("Courtyard", file_name="site.3dm")
    store.create_scene("Kitchen", file_name="house.3dm")
    result = call(feature, "list_design_scenes", limit=2)
    assert result["total"] == 3 and result["truncated"] is True
    assert [item["name"] for item in result["scenes"]] == ["Courtyard", "Kitchen"]
    assert all(set(item) == {"name"} for item in result["scenes"])
    filtered = call(feature, "list_design_scenes", name="court", file_name="site.3dm",
                    field_groups=["scope"], include_ids=True)
    assert filtered["total"] == 1
    assert filtered["scenes"][0]["file_name"] == "site.3dm"
    assert filtered["scenes"][0]["scene_id"]
    exhausted = call(feature, "list_design_scenes", offset=99)
    assert exhausted["total"] == 3 and exhausted["scenes"] == [] and exhausted["truncated"] is False
    rejected = call(feature, "list_design_scenes", field_groups=["unknown"])
    assert rejected["status"] == "error" and rejected["error_code"] == "invalid_arguments"


@pytest.fixture
def feature(store):
    namespace = {"retrieval_store": store, "_send_and_receive": unexpected_native}
    context = FeatureContext(namespace)

    def native_bridge(request):
        # Component owns capability checks; this fake keeps the sender replaceable.
        return json.loads(context._send_and_receive(json.dumps(request).encode("utf-8")))

    namespace.update(
        _component_bridge=native_bridge,
        _component_error=lambda exc: json.dumps({"status": "error", "message": str(exc)}),
    )
    mcp = FastMCP("Extracted Scene fixture")
    exported = register(mcp, context)
    return SimpleNamespace(mcp=mcp, tools=exported, namespace=namespace, context=context)


def call(feature, tool_name, **arguments):
    tool = feature.tools[tool_name]
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def install_sender(feature, handler=component_contracts.observe):
    requests = []

    def send(payload):
        request = json.loads(payload)
        requests.append(request)
        response = handler(request)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response)

    feature.namespace["_send_and_receive"] = send
    return requests


def test_scene_metadata_normalization_errors_and_cached_reads(feature, store):
    scene = call(feature, "create_design_scene", name="  Facade  ", units=" CM ")["scene"]
    summary = call(feature, "get_design_scene", scene_id=scene["scene_id"])["scene"]
    assert summary["name"] == "Facade" and summary["units"] == "cm"
    assert scene["revision"] == 0 and summary["objects"] == 0
    assert scene["live_verified"] is False
    read = call(feature, "get_design_scene", scene_id=scene["scene_id"], include_ids=True, field_groups=["all"])
    assert read["scene"] == {k: v for k, v in store.get_scene(scene["scene_id"]).items() if k != "scene_id"}
    unnamed = call(feature, "create_design_scene", name=" ")["scene"]
    assert call(feature, "get_design_scene", scene_id=unnamed["scene_id"])["scene"]["name"] == "Untitled scene"
    invalid = call(feature, "create_design_scene", name="invalid", units="yards")
    assert invalid["status"] == "error" and "units" in invalid["message"]
    missing = call(feature, "get_design_scene", scene_id="missing", include_ids=True)
    assert missing == {"status": "error", "message": "Unknown scene_id: missing"}


def test_factory_reads_store_sender_and_cross_feature_helpers_at_call_time(feature, store, model, tmp_path):
    scene_id = store.fixture_scene_id
    first_requests = install_sender(feature)
    assert call(feature, "register_scene_objects", scene_id=scene_id,
                expected_model_path=model, object_ids=[A])["status"] == "success"
    second_requests = install_sender(feature)
    assert call(feature, "register_scene_objects", scene_id=scene_id,
                expected_model_path=model, object_ids=[B])["direct_objects"] == 2
    assert [obj["rhino_guid"] for obj in store.scene_objects(scene_id)] == [A, B]
    assert len(first_requests) == len(second_requests) == 1

    other_store = ExtractedScenesStore(tmp_path / "other.sqlite3")
    feature.namespace["retrieval_store"] = other_store
    assert call(feature, "get_design_scene", scene_id=scene_id, include_ids=True)["status"] == "error"
    other_scene = call(feature, "create_design_scene", name="Isolated")["scene"]
    assert store.get_scene(other_scene["scene_id"]) is None
    assert other_store.get_scene(other_scene["scene_id"]) is not None

    feature.namespace["_component_error"] = lambda exc: json.dumps({"new_error_handler": str(exc)})
    missing = call(feature, "get_scene_objects", scene_id=scene_id, include_ids=True)
    assert "new_error_handler" in missing
    feature.namespace["retrieval_store"] = store
    feature.namespace["_component_bridge"] = lambda request: (_ for _ in ()).throw(ValueError("new bridge"))
    rejected = call(feature, "register_scene_objects", scene_id=scene_id,
                    expected_model_path=model, object_ids=[A])
    assert rejected == {"new_error_handler": "new bridge"}


def test_factory_contexts_keep_separate_ledgers(feature, tmp_path):
    other_store = ExtractedScenesStore(tmp_path / "isolated.sqlite3")
    other = SimpleNamespace(tools=register(FastMCP("Other Scene fixture"), FeatureContext({
        "retrieval_store": other_store,
    })))
    created = call(other, "create_design_scene", name="Other server")["scene"]
    assert call(feature, "get_design_scene", scene_id=created["scene_id"], include_ids=True)["status"] == "error"
    assert call(other, "get_design_scene", scene_id=created["scene_id"], include_ids=True)["scene"]["name"] == "Other server"


@pytest.mark.parametrize("mode,object_ids", [("remove", [A]), ("replace", [])])
def test_unlink_last_object_needs_no_native_observation(feature, store, model, mode, object_ids):
    requests = install_sender(feature)
    duplicate = call(feature, "register_scene_objects", scene_id=store.fixture_scene_id,
                     expected_model_path=model, object_ids=[A, A])
    assert duplicate["status"] == "error" and requests == []
    linked = call(feature, "register_scene_objects", scene_id=store.fixture_scene_id,
                  expected_model_path=model, object_ids=[A])
    assert linked["direct_objects"] == 1 and linked["live_verified"] is True
    assert "object_ids" not in linked
    assert requests[0]["action"] == "objects" and requests[0]["object_ids"] == [A]
    feature.namespace["_send_and_receive"] = unexpected_native
    removed = call(feature, "register_scene_objects", scene_id=store.fixture_scene_id,
                   expected_model_path=model, object_ids=object_ids, mode=mode)
    assert removed["direct_objects"] == 0
    assert removed["scene_revisions"][store.fixture_scene_id] == 2
    cached = call(feature, "get_scene_objects", scene_id=store.fixture_scene_id, include_ids=True)
    assert cached["objects"] == [] and cached["live_verified"] is False


@pytest.mark.parametrize("failure", ["incomplete", "wrong_document", "ownership", "timeout"])
def test_failed_observation_preserves_membership_and_revisions(feature, store, model, failure):
    install_sender(feature)
    call(feature, "register_scene_objects", scene_id=store.fixture_scene_id,
         expected_model_path=model, object_ids=[A])
    before = component_contracts.snapshot(store)

    def fail(request):
        if failure == "timeout":
            return TimeoutError("Native read timed out")
        result = component_contracts.observe(request)
        if failure == "incomplete":
            result["complete"] = False
        elif failure == "wrong_document":
            result["model_path"] = model + ".other.3dm"
        else:
            result["objects"][0]["component_id"] = "unregistered-owner"
        return result

    requests = install_sender(feature, fail)
    result = call(feature, "register_scene_objects", scene_id=store.fixture_scene_id,
                  expected_model_path=model, object_ids=[B], mode="replace")
    assert result["status"] == "error" and result["message"]
    assert len(requests) == 1
    assert component_contracts.snapshot(store) == before


def test_actual_mcp_scene_schema_and_roundtrip(feature, store, model):
    requests = install_sender(feature)

    async def verify():
        async with Client(feature.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert set(tools) == SCENE_TOOLS
            schema = tools["register_scene_objects"]["inputSchema"]
            assert set(schema["required"]) == {"scene_id", "object_ids"}
            assert schema["properties"]["mode"]["default"] == "add"
            assert tools["get_scene_objects"]["annotations"]["readOnlyHint"] is True
            assert tools["register_scene_objects"]["annotations"]["destructiveHint"] is False
            created = await client.call_tool("create_design_scene", {"name": "Protocol scene"})
            scene = json.loads(created.structured_content["result"])["scene"]
            linked = await client.call_tool("register_scene_objects", {
                "scene_id": scene["scene_id"], "expected_model_path": model, "object_ids": [A],
            })
            assert json.loads(linked.structured_content["result"])["status"] == "success"
            read = await client.call_tool("get_scene_objects", {"scene_id": scene["scene_id"], "include_ids": True})
            objects = json.loads(read.structured_content["result"])
            assert objects["total"] == 1 and objects["live_verified"] is False
            assert objects["objects"][0]["rhino_guid"] == A
            assert store.get_scene(scene["scene_id"])["direct_objects"] == 1

    asyncio.run(verify())
    assert [request["action"] for request in requests] == ["objects"]
