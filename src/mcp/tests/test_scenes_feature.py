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
SCENE_TOOLS = {"list_design_scenes", "update_design_scene", "create_design_scene", "get_design_scene", "get_scene_objects"}


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


def test_factory_reads_store_sender_and_cross_feature_helpers_at_call_time(feature,store,model,tmp_path):
    scene_id=store.fixture_scene_id
    component=component_contracts.registered(store,model,[A])
    def observed(request):
        return dict(status='success',complete=True,model_path=model,editing={'stable':True},problems=[],
            components=[dict(component,complete=True)])
    first=install_sender(feature,observed)
    assert call(feature,'get_scene_objects',scene_id=scene_id,expected_model_path=model)['total']==1
    second=install_sender(feature,observed)
    assert call(feature,'get_scene_objects',scene_id=scene_id,expected_model_path=model)['total']==1
    assert len(first)==len(second)==1 and first[0]['action']=='inspect_many'
    assert 'register_scene_objects' not in feature.tools
    replacement=ExtractedScenesStore(tmp_path/'replacement.sqlite3')
    feature.namespace['retrieval_store']=replacement
    assert call(feature,'get_scene_objects',scene_id=scene_id,expected_model_path=model)['status']=='error'
    feature.namespace['_component_error']=lambda exc:json.dumps({'status':'error','marker':'replacement'})
    assert call(feature,'get_scene_objects',scene_id=scene_id,expected_model_path=model)['marker']=='replacement'


@pytest.mark.parametrize('failure',['incomplete','wrong_document','ownership','timeout'])
def test_failed_live_scene_observation_preserves_registration_and_revisions(feature,store,model,failure):
    component=component_contracts.registered(store,model,[A])
    before=component_contracts.snapshot(store)
    def observed(request):
        if failure=='timeout': raise TimeoutError('Read timed out')
        reply=dict(status='success',complete=True,model_path=model,editing={'stable':True},problems=[],
            components=[dict(component,complete=True)])
        if failure=='incomplete': reply['complete']=False
        if failure=='wrong_document': reply['model_path']=model+'.other.3dm'
        if failure=='ownership': reply['components'][0]['objects'][0]['component_id']='unrelated'
        return reply
    install_sender(feature,observed)
    result=call(feature,'get_scene_objects',scene_id=store.fixture_scene_id,expected_model_path=model)
    assert result['status']=='error'
    assert component_contracts.snapshot(store)==before


def test_actual_mcp_scene_schema_and_roundtrip(feature,store,model):
    snapshots=[]
    requests=install_sender(feature,lambda request:dict(status='success',complete=True,model_path=model,
        editing={'stable':True},components=snapshots,problems=[]))
    async def verify():
        async with Client(feature.mcp) as client:
            tools={tool.name:tool.model_dump(mode='json',by_alias=True,exclude_none=True) for tool in await client.list_tools()}
            assert set(tools)==SCENE_TOOLS and 'register_scene_objects' not in tools
            schema=tools['get_scene_objects']['inputSchema']
            assert set(schema['required'])=={'scene_id'}
            assert tools['get_scene_objects']['annotations']['readOnlyHint'] is True
            created=await client.call_tool('create_design_scene',{'name':'Protocol scene'})
            scene=json.loads(created.structured_content['result'])['scene']
            component=component_contracts.registered(store,model,[A],scenes=[scene['scene_id']])
            snapshots.append(dict(component,complete=True))
            read=await client.call_tool('get_scene_objects',{'scene_id':scene['scene_id'],'expected_model_path':model,'include_ids':True})
            result=json.loads(read.structured_content['result'])
            assert result['total']==1 and result['live_verified'] is True
            assert result['objects'][0]['rhino_guid']==A
            assert 'direct_objects' not in store.get_scene(scene['scene_id'])
    asyncio.run(verify())
    assert [r['action'] for r in requests]==['inspect_many']
