"""New task templates and additive scope migration without changing existing work."""
import json
import sqlite3

import pytest

from almond_mcp.features.planning.schema import SCOPES
from almond_mcp.retrieval_store import AlmondStore


@pytest.mark.parametrize("scope", SCOPES)
def test_builtin_templates_are_plans_with_ordered_steps_and_no_automatic_execution(tmp_path, scope):
    store = AlmondStore(tmp_path / "templates.sqlite3")
    plan = store.create_plan("Task goal", scope=scope)
    assert plan["scope"] == scope and plan["status"] == "pending"
    assert plan["scene_ids"] == [] and plan["artifact_dir"] == ""
    assert all(s["status"] == "pending" for s in plan["steps"])
    seen = set()
    for step in plan["steps"]:
        assert set(step["depends_on"]) <= seen
        seen.add(step["step_id"])
    if scope == "inspection":
        assert not any(s["kind"] == "execute" for s in plan["steps"])
    if scope != "construction_detail":
        assert "model_detail" not in seen
    assert "construction_detail_enabled" not in plan
    assert store.create_plan("Unspecified scope")["scope"] == "house"


def test_existing_registry_and_plan_history_survive_migration_and_reopen(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    store = AlmondStore(db)
    old_plan = store.create_plan("Existing task", scope="component")
    with store._connect() as con:
        snapshots = [tuple(r) for r in con.execute('SELECT * FROM generation_plan_revisions')]
    # Recreate the real old constraint and retain a custom mapping that collides with a new name.
    with sqlite3.connect(db) as con:
        con.execute('PRAGMA foreign_keys=OFF')
        con.execute('DROP TABLE planning_scopes')
        old_scopes = SCOPES[:5]
        allowed = ','.join(repr(s) for s in old_scopes)
        con.execute(f'''CREATE TABLE planning_scopes(scope TEXT PRIMARY KEY CHECK(length(trim(scope))>0 AND scope=lower(trim(scope))),
                    template_scope TEXT NOT NULL CHECK(template_scope IN ({allowed})))''')
        con.executemany('INSERT INTO planning_scopes VALUES(?,?)', [(s, s) for s in old_scopes])
        con.execute("INSERT INTO planning_scopes VALUES('inspection','component')")
        con.execute("INSERT INTO planning_scopes VALUES('user_scope','drawing')")
        con.execute('CREATE INDEX user_scope_index ON planning_scopes(template_scope)')
    migrated = AlmondStore(db)
    assert migrated.get_plan(old_plan['plan_id']) == old_plan
    assert migrated.create_plan("User mapping", scope="inspection")["steps"][0]["step_id"] == "inspect_context"
    with migrated._connect() as con:
        assert [tuple(r) for r in con.execute('SELECT * FROM generation_plan_revisions WHERE plan_id=?', (old_plan['plan_id'],))] == snapshots
        assert con.execute("SELECT template_scope FROM planning_scopes WHERE scope='user_scope'").fetchone()[0] == 'drawing'
        assert con.execute("SELECT 1 FROM sqlite_master WHERE name='user_scope_index'").fetchone()
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO planning_scopes VALUES('invalid','not_a_template')")
    assert AlmondStore(db).get_plan(old_plan['plan_id']) == old_plan


@pytest.mark.parametrize("scope", ["plan_editing", "custom_editing"])
def test_plan_editing_tool_persists_plan_and_mapped_scope_without_changing_history(tmp_path, scope):
    from types import SimpleNamespace
    from fastmcp import FastMCP
    from almond_mcp.features.planning.tools import register

    db = tmp_path / "plan-editing.sqlite3"
    store = AlmondStore(db)
    existing = store.create_plan("Existing task", scope="component")
    with store._connect() as connection:
        existing_revisions = [tuple(row) for row in connection.execute(
            'SELECT * FROM generation_plan_revisions WHERE plan_id=?', (existing['plan_id'],))]
        if scope == "custom_editing":
            connection.execute("INSERT INTO planning_scopes VALUES('custom_editing','plan_editing')")
    tools = register(FastMCP('plan-editing'), SimpleNamespace(retrieval_store=store))
    result = json.loads(tools['create_plan'](title="Edit plan", goal="Revise the plan", scope=scope))
    assert result['status'] == 'success'
    reopened = AlmondStore(db)
    plan = reopened.get_plan(result['plan']['plan_id'])
    assert plan['scope'] == scope and plan['title'] == 'Edit plan'
    assert plan['status'] == 'pending' and plan['steps']
    assert all(step['status'] == 'pending' for step in plan['steps'])
    assert reopened.get_plan(plan['plan_id'], plan['revision']) == plan
    assert reopened.get_plan(existing['plan_id']) == existing
    with reopened._connect() as connection:
        assert [tuple(row) for row in connection.execute(
            'SELECT * FROM generation_plan_revisions WHERE plan_id=?', (existing['plan_id'],))] == existing_revisions
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()


def test_semantic_exploration_tool_creates_ordered_reasoning_steps(tmp_path):
    from types import SimpleNamespace
    from fastmcp import FastMCP
    from almond_mcp.features.planning.tools import register

    db = tmp_path / "semantic.sqlite3"
    store = AlmondStore(db)
    tools = register(FastMCP('semantic-exploration'), SimpleNamespace(retrieval_store=store))
    result = json.loads(tools['create_plan'](
        title="Explore context", goal="Interpret the spatial context", scope="semantic_exploration"))
    assert result['status'] == 'success', result
    plan = AlmondStore(db).get_plan(result['plan']['plan_id'])
    assert [step['step_id'] for step in plan['steps']] == [
        'inspect_context', 'inspect_surroundings', 'interpret_spatial_context', 'report_findings']
    assert all(step['kind'] == 'reason' and step['status'] == 'pending' for step in plan['steps'])


@pytest.mark.parametrize("custom_semantic_mapping", [False, True])
def test_semantic_scope_migration_preserves_existing_plans_and_custom_registry(tmp_path, custom_semantic_mapping):
    db = tmp_path / "before-semantic.sqlite3"
    store = AlmondStore(db)
    old_plan = store.create_plan("Existing task", scope="component")
    tables = ('generation_plans', 'generation_plan_steps', 'generation_plan_revisions')
    with store._connect() as con:
        before = {table: [tuple(row) for row in con.execute(f'SELECT * FROM {table}')]
                  for table in tables}
    # Use the immediately preceding registry, including all earlier task scopes.
    with sqlite3.connect(db) as con:
        con.execute('PRAGMA foreign_keys=OFF')
        con.execute('DROP TABLE planning_scopes')
        previous_scopes = tuple(scope for scope in SCOPES if scope != 'semantic_exploration')
        allowed = ','.join(repr(scope) for scope in previous_scopes)
        con.execute(f'''CREATE TABLE planning_scopes(
            scope TEXT PRIMARY KEY CHECK(length(trim(scope))>0 AND scope=lower(trim(scope))),
            template_scope TEXT NOT NULL CHECK(template_scope IN ({allowed})))''')
        con.executemany('INSERT INTO planning_scopes VALUES(?,?)', [(s, s) for s in previous_scopes])
        con.execute("INSERT INTO planning_scopes VALUES('custom_house','house')")
        con.execute("INSERT INTO planning_scopes VALUES('custom_interior','interior')")
        if custom_semantic_mapping:
            con.execute("INSERT INTO planning_scopes VALUES('semantic_exploration','component')")
        con.execute('CREATE INDEX custom_scope_index ON planning_scopes(template_scope)')
        con.execute('CREATE TABLE scope_audit(scope TEXT)')
        con.execute('''CREATE TRIGGER custom_scope_trigger AFTER INSERT ON planning_scopes
                       BEGIN INSERT INTO scope_audit VALUES(NEW.scope); END''')
        registry_before = dict(con.execute('SELECT * FROM planning_scopes'))
    migrated = AlmondStore(db)
    assert migrated.get_plan(old_plan['plan_id']) == old_plan
    with migrated._connect() as con:
        assert {table: [tuple(row) for row in con.execute(f'SELECT * FROM {table}')]
                for table in tables} == before
        registry_after = dict(con.execute('SELECT * FROM planning_scopes'))
        assert registry_after == {**registry_before, 'semantic_exploration':
                                  'component' if custom_semantic_mapping else 'semantic_exploration'}
        assert con.execute("SELECT 1 FROM sqlite_master WHERE name='custom_scope_index'").fetchone()
        assert con.execute("SELECT 1 FROM sqlite_master WHERE name='custom_scope_trigger'").fetchone()
        con.execute("INSERT INTO planning_scopes VALUES('custom_semantic','semantic_exploration')")
        assert con.execute("SELECT 1 FROM scope_audit WHERE scope='custom_semantic'").fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO planning_scopes VALUES('invalid','not_a_template')")
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
    reopened = AlmondStore(db)
    assert reopened.get_plan(old_plan['plan_id']) == old_plan
    for scope, expected_first in [('custom_house', 'programme'), ('custom_interior', 'inspect_rooms'),
                                  ('custom_semantic', 'inspect_context')]:
        assert reopened.create_plan('Mapped task', scope=scope)['steps'][0]['step_id'] == expected_first
    semantic_plan = reopened.create_plan('Explore', scope='semantic_exploration')
    assert semantic_plan['steps'][1]['step_id'] == ('design' if custom_semantic_mapping else 'inspect_surroundings')
