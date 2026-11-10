"""Behavior at selection, argument entry, and result consumption boundaries."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP
from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from jsonschema import validate

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.tool_guidance import guide_payload, guide_result


def test_public_phase_input_and_optional_details_survive_restart(tmp_path):
    path = tmp_path / 'planning.sqlite3'
    store = AlmondStore(path)
    server = FastMCP('phase-flow')
    register(server, SimpleNamespace(retrieval_store=store))

    async def run():
        async with Client(server) as client:
            tools = {t.name:t for t in await client.list_tools()}
            create = tools['create_phase'].input_schema['properties']
            assert create['status']['enum'] == ['pending','running','paused','completed','failed','blocked']
            assert {item['type'] for item in create['file_name']['anyOf']} == {'string','array'}
            assert 'project_file_id' not in create
            assert 'include_details' in tools['get_phase_plan_step'].input_schema['properties']
            result = await client.call_tool('create_phase', {'name':'Site and building', 'file_name':['site.3dm','building.3dm']})
            value = json.loads(result.content[0].text)
            pid = value['phase']['phase_id']
            for details in (False, True):
                result = await client.call_tool('get_phase_plan_step', {'phase_id':pid,'include_details':details})
                value = json.loads(result.content[0].text)
                assert value['name'] == 'Site and building' and ('phase' in value) == details
                if details:
                    assert value['phase']['file_name'] == ['site.3dm','building.3dm']
                    assert 'project_file_id' not in value['phase']
                output = tools['get_phase_plan_step'].output_schema['properties']['result']['contentSchema']
                validate(value, output)
            await client.call_tool('update_phase', {'phase_id': pid, 'status': 'failed'})
            failed_phase = await client.call_tool('get_phase_plan_step', {'phase_id': pid})
            failed_record = json.loads(failed_phase.content[0].text)
            assert failed_record['status'] == 'failed'
            assert 'include_details=true' in failed_record['next_step_guide']
            result = await client.call_tool('update_phase', {'phase_id':pid,'status':'finished','file_name':['should-not-exist.3dm']}, raise_on_error=False)
            assert result.is_error
            reopened = AlmondStore(path)
            assert reopened.get_phase(pid)['file_names'] == ['site.3dm','building.3dm']
            assert len(reopened.list_project_files()['files']) == 2
    asyncio.run(run())


@pytest.mark.parametrize('payload', [
    {'status':'error','message':'failed'}, {'status':'success','complete':False},
    {'status':'success','mutation_state':'uncertain'}, {'status':'success','mutation_applied':None},
])
def test_failed_or_incomplete_work_has_no_success_suggestion(payload):
    assert guide_payload('edit_planar_faces', payload) == payload


def test_history_partial_updates_empty_lists_and_execution_recovery():
    past = guide_payload('get_phase_plan_step', {'status':'completed','type':'plan','read_only':True}, {'include_details':True})
    assert '생략' in past['next_step_guide'] and 'set_working_plan' not in past['next_step_guide']
    partial = guide_payload('update_step', {'status':'partial_success','issues':[{'reason':'missing'}]})
    assert 'issues' in partial['next_step_guide'] and 'set_working_plan' not in partial['next_step_guide']
    empty = guide_payload('list_plans', {'status':'success','plans':[]})
    assert 'next_step_guide' not in empty
    pending = guide_payload('execute_rhino_script', {'status':'timeout','completed':False,'request_id':'saved'})
    assert 'get_rhino_execution' in pending['next_step_guide'] and '다시 제출하지' in pending['next_step_guide']


def test_capture_guidance_keeps_binary_content_and_error_flags():
    payload = {'status':'success','complete':True,'image_file':{'status':'saved','path':'.almond/produced/report.png','lifetime':'plan'}}
    picture = ImageContent(type='image', data='AA==', mimeType='image/png')
    original = ToolResult(content=[TextContent(type='text',text=json.dumps(payload)),picture], structured_content=payload, meta={'trace':'test'})
    result = guide_result('capture_rhino_inspection', original,{})
    assert result.content[1] == picture and result.meta == original.meta
    assert 'output_refs' in result.structured_content['next_step_guide']
    assert json.loads(result.content[0].text) == result.structured_content
    error = original.model_copy(update={'is_error':True})
    assert guide_result('capture_rhino_inspection',error,{}) is error
    assert original.structured_content == payload


def test_user_script_result_keys_are_not_rewritten():
    payload = {'status':'success','completed':True,'result':{'next_step':'user data','status':'unfinished'}}
    assert guide_payload('execute_rhino_script',payload) == payload


def test_execution_page_guidance_uses_runtime_field_map():
    from almond_mcp.runtime.rhinocode import _result_page
    rows, page = _result_page({'items': list(range(5))}, None, 0, 2)
    result = guide_payload('get_rhino_execution', {
        'status': 'success', 'completed': True, 'request_id': 'saved',
        'result': rows, 'result_page': page,
    })
    assert 'next_offset' in result['next_step_guide']
    _, last_page = _result_page({'items': list(range(5))}, None, 4, 2)
    result = guide_payload('get_rhino_execution', {
        'status': 'success', 'completed': True, 'request_id': 'saved', 'result_page': last_page,
    })
    assert 'next_step_guide' not in result


def test_guidance_does_not_reference_absent_result_fields():
    assert 'next_step_guide' not in guide_payload('apply_drawing_style', {'status': 'success', 'layers': []})
    assert 'next_step_guide' not in guide_payload('get_objects', {'status': 'success', 'objects': [{'name': 'Wall'}]})
    assert 'include_ids=true' in guide_payload('list_design_codes', {'profiles': [{'name': 'Example'}]}, {'include_ids': False})['next_step_guide']
    assert 'next_step_guide' not in guide_payload('get_diagram_asset', {'status': 'success', 'asset': {'file_available': False}}, {'asset_id': 'missing-file'})
    assert 'next_step_guide' not in guide_payload('generate_asset_drawing_views', {'status': 'success', 'package_dir': '../drawing-runs/new-package'})


def test_unconfirmed_asset_publication_preserves_nullable_contract(tmp_path, monkeypatch):
    from almond_mcp.features.assets import drawing_assets
    from almond_mcp.features.assets.tools import register as assets

    def unconfirmed(*args, **kwargs):
        raise drawing_assets.PublicationUnconfirmed('Source edit requires reconciliation')

    monkeypatch.setattr(drawing_assets, 'register_prepared_3dm', unconfirmed)
    context = SimpleNamespace(
        DRAWING_LIBRARY_DIR=str(tmp_path),
        diagram_asset_indexer=SimpleNamespace(assets={}),
        generated_asset_indexer=SimpleNamespace(get=lambda _: None),
        drawing_asset_indexer=SimpleNamespace(get=lambda _: None),
    )
    server = FastMCP('uncertain-publication')
    assets(server, context)

    async def run():
        async with Client(server) as client:
            schemas = {t.name: t.output_schema for t in await client.list_tools()}
            response = await client.call_tool('register_drawing_asset', {
                'source_3dm': str(tmp_path / 'source.3dm'), 'asset_id': 'asset', 'name': 'Fixture',
            })
            value = json.loads(response.content[0].text)
            assert value['registration_applied'] is None and value['requires_reconciliation'] is True
            assert 'next_step_guide' not in value
            validate(value, schemas['register_drawing_asset'])

    asyncio.run(run())
