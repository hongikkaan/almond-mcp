import json
from types import SimpleNamespace
from fastmcp import FastMCP
from almond_mcp.features.scenes.tools import register


def test_scene_membership_public_tools_return_indices_only():
    requests = []
    class Store:
        def change_scene_objects(self, scene, model, ids, add, native_inspect, native_objects):
            requests.append((scene, model, ids, add))
            return {'failed_indices': [1], ('already_present_indices' if add else 'already_absent_indices'): [2]}
    context = SimpleNamespace(retrieval_store=Store(), _component_bridge=lambda _: None,
                              _component_error=lambda error: json.dumps({'status': 'error', 'message': str(error)}),
                              _send_and_receive=lambda _: '')
    tools = register(FastMCP('scene-test'), context)
    ids = ['00000000-0000-0000-0000-000000000001', 'bad', '00000000-0000-0000-0000-000000000003']
    for name, field in [('add_scene_objects', 'already_present_indices'), ('remove_scene_objects', 'already_absent_indices')]:
        output = tools[name](scene_id='scene_test', object_ids=ids, expected_model_path=r'C:\\fixture\\model.3dm')
        assert json.loads(output) == {'status': 'success', 'failed_indices': [1], field: [2]}
        assert all(guid not in output for guid in ids)
    assert [r[3] for r in requests] == [True, False]


def test_scene_membership_whole_batch_errors_are_mcp_errors():
    class Store:
        def change_scene_objects(self, *args):
            raise ValueError('document mismatch')
    context = SimpleNamespace(retrieval_store=Store(), _component_bridge=lambda _: None,
                              _component_error=lambda error: json.dumps({'status': 'error', 'message': str(error)}),
                              _send_and_receive=lambda _: '')
    tools = register(FastMCP('scene-errors'), context)
    for name in ('add_scene_objects', 'remove_scene_objects'):
        result = tools[name](scene_id='scene_test', object_ids=[], expected_model_path=r'C:\fixture\model.3dm')
        assert result.is_error is True
        assert 'document mismatch' in result.content[0].text


def test_live_scene_resolution_combines_holon_members_and_direct_objects(tmp_path):
    from almond_mcp.retrieval_store import AlmondStore
    from test_component_group_inference import snapshot, COMPONENT, GROUP, OBJECT, MODEL
    store = AlmondStore(tmp_path / 'mixed-scene.sqlite3')
    scene = store.create_scene('Mixed scene')['scene_id']
    component = snapshot(scene)
    store.upsert_component(MODEL, 'Arrival', [OBJECT], [scene], COMPONENT, GROUP,
                           native_apply=lambda _: {'status': 'success', 'component': component})
    clip = '00000000-0000-0000-0000-000000000209'
    def inspect(request):
        assert request['action'] == 'inspect_many'
        assert request['component_ids'] == [COMPONENT]
        return {'status': 'success', 'complete': True, 'model_path': MODEL,
                'editing': {'stable': True}, 'components': [component], 'problems': []}
    def objects(model, ids):
        return ({guid: {'rhino_guid': guid, 'object_type': 'ClipPlane', 'name': 'Section'}
                 for guid in ids}, set())
    result = store.change_scene_objects(scene, MODEL, [clip, OBJECT], True, inspect, objects)
    assert result == {'failed_indices': [], 'already_present_indices': [1]}
    assert {x['rhino_guid'] for x in store.scene_objects(scene, MODEL, inspect, objects)} == {clip, OBJECT}
    store.change_scene_objects(scene, MODEL, [OBJECT], False, inspect, objects)
    assert [x['rhino_guid'] for x in store.scene_objects(scene, MODEL, inspect, objects)] == [clip]
    assert store.get_component(COMPONENT)['object_count'] == 1
    store.change_scene_objects(scene, MODEL, [OBJECT], True, inspect, objects)
    assert {x['rhino_guid'] for x in store.scene_objects(scene, MODEL, inspect, objects)} == {clip, OBJECT}
