"""Public predecessor persistence across restarts/history."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP
from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore
from test_planning_details import request_branch


def test_previous_survives_restart_and_revision_without_changing_dependencies(tmp_path):
    path = tmp_path / 'planning.db'
    store = AlmondStore(path)
    first = store.create_plan('First')
    second = store.create_plan('Next', previous_id=first['plan_id'], depends_on=['plan_reference'])
    pid = second['plan_id']
    phase = store.create_phase('Later phase', previous_id='phase_previous')
    assert store.update_phase(phase['phase_id'], description='detail')['previous_id'] == 'phase_previous'
    assert not store.edit_phase(phase['phase_id'], previous_id='phase_previous').changed
    assert store.update_phase(phase['phase_id'], previous_id='')['previous_id'] is None
    assert not store.edit_plan(pid, previous_id=first['plan_id']).changed
    revised = store.update_plan(pid, previous_id='', expected_revision=second['revision'])
    assert revised['revision'] == second['revision'] + 1
    assert revised['depends_on'] == ['plan_reference']
    restarted = AlmondStore(path)
    assert restarted.get_plan(pid)['previous_id'] is None
    assert restarted.get_plan(pid, second['revision'])['previous_id'] == first['plan_id']
    with pytest.raises(ValueError):
        restarted.update_plan(pid, previous_id='phase_wrong', title='must rollback')
    assert restarted.get_plan(pid)['title'] == revised['title']
    with pytest.raises(ValueError):
        restarted.update_phase(phase['phase_id'], previous_id='plan_wrong')
    # Read compatibility must not rewrite immutable older snapshots.
    with restarted._connect() as connection:
        row = connection.execute('SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=? AND revision=1', (pid,)).fetchone()[0]
        old = json.loads(row)
        old.pop('previous_id')
        raw = json.dumps(old)
        connection.execute('UPDATE generation_plan_revisions SET snapshot_json=? WHERE plan_id=? AND revision=1', (raw, pid))
    assert AlmondStore(path).get_plan(pid, 1)['previous_id'] is None
    with restarted._connect() as connection:
        assert connection.execute('SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=? AND revision=1', (pid,)).fetchone()[0] == raw


def test_public_tools_expose_and_round_trip_previous(tmp_path):
    store = AlmondStore(tmp_path / 'planning.db')
    server = FastMCP('shared-contracts')
    register(server, SimpleNamespace(retrieval_store=store))

    async def run():
        async with Client(server) as client:
            tools = {t.name:t for t in await client.list_tools()}
            for name in ['plan_02-create', 'plan_12-update']:
                for target in ['phase', 'plan']:
                    assert 'previous_id' in request_branch(tools[name].input_schema, target)['properties']
            result = await client.call_tool('plan_02-create', {'request': {'target': 'plan', 'title':'Next', 'goal':'Next task', 'previous_id':'plan_prior'}})
            pid = json.loads(result.content[0].text)['plan']['plan_id']
            result = await client.call_tool('plan_05-get', {'request': {'target': 'plan', "include_details": True, 'plan_id':pid}})
            assert json.loads(result.content[0].text)['plan']['previous_id'] == 'plan_prior'
            result = await client.call_tool('plan_02-create', {'request': {'target': 'phase', 'name':'Next phase', 'previous_id':'phase_prior'}})
            phase_id = json.loads(result.content[0].text)['phase']['phase_id']
            result = await client.call_tool('plan_05-get', {'request': {'target': 'phase', "include_details": True, 'phase_id':phase_id}})
            assert json.loads(result.content[0].text)['phase']['previous_id'] == 'phase_prior'
    asyncio.run(run())


def test_nullable_migration_preserves_old_records_and_history(tmp_path):
    path = tmp_path / 'old.db'
    store = AlmondStore(path)
    phase = store.create_phase('Existing phase', depends_on=['phase_reference'])
    plan = store.create_plan('Existing plan', phase_id=phase['phase_id'], depends_on=['plan_reference'])
    with store._connect() as connection:
        connection.execute('ALTER TABLE generation_phases DROP COLUMN previous_id')
        connection.execute('ALTER TABLE generation_plans DROP COLUMN previous_id')
        before = connection.execute('SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=?', (plan['plan_id'],)).fetchone()[0]
    migrated = AlmondStore(path)
    assert migrated.get_phase(phase['phase_id'])['previous_id'] is None
    assert migrated.get_plan(plan['plan_id']) == plan
    with migrated._connect() as connection:
        assert connection.execute('SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=?', (plan['plan_id'],)).fetchone()[0] == before
