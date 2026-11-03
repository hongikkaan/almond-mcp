"""New task templates and additive scope migration without changing existing work."""
import json
import sqlite3

import pytest

from almond_mcp.features.planning.schema import SCOPES, TASK_SCOPES
from almond_mcp.retrieval_store import AlmondStore


@pytest.mark.parametrize("scope", TASK_SCOPES)
def test_new_templates_are_plans_with_ordered_steps_and_no_automatic_execution(tmp_path, scope):
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
