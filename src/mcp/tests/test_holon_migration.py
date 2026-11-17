"""Holon naming migrates persistent identities without rewriting user history."""
import sqlite3
from contextlib import closing

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
        con.execute("INSERT INTO project_files(file_name,registered) VALUES('model.3dm',1)")
        con.execute("INSERT INTO _project_file_locations VALUES('model.3dm',?)", (r'C:\fixture\model.3dm',))
        for handle in ('component_parent', 'component_child'):
            con.execute('''INSERT INTO ontological_holons
                (ontological_id,file_name,rhino_group_id,name,created_at,updated_at)
                VALUES(?,'model.3dm',?,?,'2026-11-01T00:00:00+00:00','2026-11-01T00:00:00+00:00')''',
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


def test_object_ledger_backup_keeps_committed_rows_across_reopens(tmp_path):
    path = tmp_path / 'scene.sqlite3'
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE components (
                component_id TEXT PRIMARY KEY, model_path TEXT NOT NULL, rhino_group_id TEXT NOT NULL,
                name TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                parent_component_id TEXT REFERENCES components(component_id) ON DELETE RESTRICT,
                UNIQUE(component_id, model_path), UNIQUE(model_path, rhino_group_id)
            );
            CREATE TABLE document_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, model_path TEXT NOT NULL, rhino_guid TEXT NOT NULL,
                component_id TEXT, object_type TEXT NOT NULL,
                min_x REAL NOT NULL, max_x REAL NOT NULL, min_y REAL NOT NULL, max_y REAL NOT NULL,
                min_z REAL NOT NULL, max_z REAL NOT NULL, observed_at TEXT NOT NULL,
                UNIQUE(model_path, rhino_guid),
                FOREIGN KEY(component_id, model_path) REFERENCES components(component_id, model_path)
            );
        """)
        model = r'C:\fixture\retired.3dm'
        db.execute("INSERT INTO components VALUES('old-id',?,'old-group','Original name','created','updated',NULL)", (model,))
        db.execute("INSERT INTO document_objects VALUES(7,?,'old-object','old-id','Brep',0,1,0,2,0,3,'observed')", (model,))
    with closing(sqlite3.connect(path)) as db:
        legacy_dump = list(db.iterdump())

    migrated = AlmondStore(path)
    holon = migrated.get_component('old-id')
    assert holon['name'] == 'Original name'
    assert holon['object_count'] == 1
    archives = list(tmp_path.glob('scene.sqlite3.before-object-retirement-*.bak'))
    assert len(archives) == 1
    with closing(sqlite3.connect(archives[0].as_uri() + '?mode=ro', uri=True)) as db:
        assert list(db.iterdump()) == legacy_dump
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    with closing(sqlite3.connect(path)) as db:
        assert not db.execute("SELECT name FROM sqlite_schema WHERE name IN ('components', 'document_objects')").fetchall()
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []

    assert AlmondStore(path).get_component('old-id') == holon
    assert list(tmp_path.glob('scene.sqlite3.before-object-retirement-*.bak')) == archives
