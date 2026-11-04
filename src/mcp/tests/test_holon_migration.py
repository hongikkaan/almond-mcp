"""Holon naming migrates persistent identities without rewriting user history."""
import sqlite3

import pytest

from almond_mcp.retrieval_store import AlmondStore


def rows(connection):
    return {
        name.replace('ontological_components', 'ontological_holons'):
            sorted((tuple(row) for row in connection.execute(f'SELECT * FROM "{name}"')), key=repr)
        for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def populated_store(path):
    store = AlmondStore(path)
    scene = store.create_scene('Arrival')
    with store._connect() as con:
        con.execute("INSERT INTO project_files VALUES('file_a','model.3dm')")
        con.execute("INSERT INTO _project_file_locations VALUES('file_a',?)", (r'C:\fixture\model.3dm',))
        for handle in ('component_parent', 'component_child'):
            con.execute('''INSERT INTO ontological_holons
                (ontological_id,project_file_id,rhino_group_id,name,created_at,updated_at)
                VALUES(?,'file_a',?,?,'2026-11-01T00:00:00+00:00','2026-11-01T00:00:00+00:00')''',
                (handle, handle + '_group', handle))
            con.execute('INSERT INTO ontological_scene_context VALUES(?,?)', (handle, scene['scene_id']))
        con.execute("UPDATE ontological_holons SET parent_ontological_id='component_parent' WHERE ontological_id='component_child'")
        con.execute("INSERT INTO scene_ontological VALUES(?,'component_parent')", (scene['scene_id'],))
    plan = store.create_plan('Preserve this recorded goal', title='Arrival', component_ids=['component_child'])
    return store, plan


def test_rename_preserves_every_row_relationship_and_revision(tmp_path):
    path = tmp_path / 'scene.sqlite3'
    store, plan = populated_store(path)
    old_detail = store.get_plan(plan['plan_id'])
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('ALTER TABLE ontological_holons RENAME TO ontological_components')
        before = rows(con)
    reopened = AlmondStore(path)
    with sqlite3.connect(path) as con:
        assert rows(con) == before
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        assert con.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert not con.execute("SELECT name FROM sqlite_master WHERE name='ontological_components'").fetchone()
        assert con.execute("SELECT component_id FROM _component_records ORDER BY component_id").fetchall() == [
            ('component_child',), ('component_parent',)]
        assert con.execute('PRAGMA foreign_key_list(generation_plan_ontological)').fetchall()[0][2] == 'ontological_holons'
    assert reopened.get_plan(plan['plan_id']) == old_detail
    # Reopening must be idempotent, and existing hierarchy guards must survive.
    AlmondStore(path)
    with reopened._connect() as con:
        assert {key: [tuple(row) for row in value] for key, value in rows(con).items()} == before
        with pytest.raises(sqlite3.IntegrityError, match='cycle'):
            con.execute("UPDATE ontological_holons SET parent_ontological_id='component_child' WHERE ontological_id='component_parent'")


def test_mixed_registries_fail_without_merging_or_losing_data(tmp_path):
    path = tmp_path / 'scene.sqlite3'
    populated_store(path)
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE ontological_components AS SELECT * FROM ontological_holons')
        before = rows(con)
    with pytest.raises(RuntimeError, match='Mixed Component/Holon'):
        AlmondStore(path)
    with sqlite3.connect(path) as con:
        assert rows(con) == before
        assert con.execute("SELECT count(*) FROM ontological_components").fetchone() == (2,)


def test_invalid_relationship_rolls_back_the_registry_rename(tmp_path):
    path = tmp_path / 'scene.sqlite3'
    populated_store(path)
    with sqlite3.connect(path) as con:
        con.execute('ALTER TABLE ontological_holons RENAME TO ontological_components')
        con.execute("INSERT INTO ontological_scene_context VALUES('missing','missing')")
        before = rows(con)
    with pytest.raises(ValueError, match='invalid relationship'):
        AlmondStore(path)
    with sqlite3.connect(path) as con:
        assert rows(con) == before
        assert con.execute("SELECT name FROM sqlite_master WHERE name='ontological_components'").fetchone()
        assert not con.execute("SELECT name FROM sqlite_master WHERE name='ontological_holons'").fetchone()
