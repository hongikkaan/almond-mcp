import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from jsonschema import validate

from almond_mcp.features.components.public_contract import public_result
from almond_mcp.features.components.tools import register as register_holons
from almond_mcp.features.planning.tools import register as register_planning
from almond_mcp.features.scenes.tools import register as register_scenes
from test_component_group_inference import NativeBoundary, snapshot, MODEL, GROUP, COMPONENT
from almond_mcp.retrieval_store import AlmondStore


def test_all_holon_boundaries_use_new_keys_and_preserve_native_identity(tmp_path):
    store = AlmondStore(tmp_path / 'scene.sqlite3')
    scene = store.create_scene('Arrival')
    native = NativeBoundary({'status': 'success', 'component': snapshot(scene['scene_id'])})
    context = SimpleNamespace(retrieval_store=store, _send_and_receive=native.send)
    server = FastMCP('holon-contract')
    tools = register_holons(server, context)
    context._component_bridge = tools['_component_bridge']
    context._component_error = tools['_component_error']
    register_planning(server, context)
    register_scenes(server, context)

    async def run():
        async with Client(server) as client:
            listed_tools = await client.list_tools()
            schemas = {tool.name: tool.input_schema for tool in listed_tools}
            outputs = {tool.name: tool.output_schema for tool in listed_tools}
            assert {'focus_holons', 'upsert_ontological_holon'} <= schemas.keys()
            assert 'get_holon_intersections' not in schemas
            for name, schema in schemas.items():
                assert 'ontological_component' not in name
                assert not any('component' in key for key in schema['properties']), (name, schema)

            async def call(name, arguments):
                result = await client.call_tool(name, arguments)
                assert not result.is_error
                value = json.loads(result.content[0].text)
                output = outputs[name]
                if output.get('x-fastmcp-wrap-result'):
                    output = output['properties']['result']['contentSchema']
                validate(value, output)
                return value

            ack = await call('upsert_ontological_holon', dict(name='Arrival', holon_id=COMPONENT,
                expected_model_path=MODEL, rhino_group_id=GROUP, scene_ids=[scene['scene_id']]))
            assert ack['holon']['holon_id'] == COMPONENT
            assert native.requests[-1]['component_id'] == COMPONENT
            assert 'holon_id' not in native.requests[-1]
            listed = await call('list_ontological_holons', {'include_ids': True, 'field_groups': ['references']})
            assert listed['holons'][0]['holon_id'] == COMPONENT
            assert 'child_holon_ids' in listed['holons'][0]
            detail = await call('get_ontological_holon', {'holon_id': COMPONENT, 'field_groups': ['references']})
            assert 'holon_id' not in detail['holon']
            assert 'child_holon_count' in detail['holon']
            native.reply = {'status': 'success', 'complete': True, 'model_path': MODEL,
                            'editing': {'stable': True}, 'components': [snapshot(scene['scene_id'])], 'problems': []}
            synced = await call('sync_ontological_holon', {'holon_id': COMPONENT, 'expected_model_path': MODEL})
            assert synced['checked'] == 1 and synced['changed'] == 0
            cached_scene = await call('get_design_scene', {'scene_id': scene['scene_id'], 'include_ids': True})
            assert 'holons' in cached_scene['scene']
            plan = (await call('create_plan', {'title': 'component_id literal', 'goal': 'Keep component text',
                'holon_ids': [COMPONENT]}))['plan']
            plan_detail = await call('get_phase_plan_step', {'plan_id': plan['plan_id'], 'include_details': True})
            assert plan_detail['plan']['holon_ids'] == [COMPONENT]
            assert plan_detail['name'] == 'component_id literal'
            assert plan_detail['plan']['goal'] == 'Keep component text'
            assert 'plan' not in (await call('get_phase_plan_step', {'plan_id': plan['plan_id']}))
            invalid = await call('update_plan', {'plan_id': plan['plan_id'], 'holon_ids': ['component_unknown']})
            assert invalid['status'] == 'error' and 'component_id' not in invalid['message']
            rejected = await client.call_tool('upsert_ontological_holon', {'name': 'Arrival', 'component_id': COMPONENT}, raise_on_error=False)
            assert rejected.is_error
    asyncio.run(run())


def test_public_projection_preserves_recorded_text_and_id_values():
    value = {'component_id': 'component_old', 'name': 'Components', 'input_refs': ['component_id: original'],
             'affected_components': [{'parent_component_id': 'component_parent'}],
             'message': 'Unknown component_id: component_old'}
    result = public_result(value)
    assert result == {'holon_id': 'component_old', 'name': 'Components', 'input_refs': ['component_id: original'],
                      'affected_holons': [{'parent_holon_id': 'component_parent'}],
                      'message': 'Unknown holon_id: component_old'}
    assert value['component_id'] == 'component_old'
