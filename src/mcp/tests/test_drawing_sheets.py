"""Retired Sheet tables retain rows without constraining current work."""
import sqlite3
import pytest
from almond_mcp.retrieval_store import AlmondStore


def legacy_store(tmp_path):
    store = AlmondStore(tmp_path / "DB")
    scene = store.create_scene("Kept")
    with store._connect() as db:
        db.executescript('''
            CREATE TABLE drawing_sheets(sheet_id TEXT PRIMARY KEY, title TEXT);
            CREATE TABLE drawing_sheet_scenes(
                sheet_id TEXT REFERENCES drawing_sheets(sheet_id) ON DELETE CASCADE,
                scene_id TEXT REFERENCES scenes(scene_id) ON DELETE RESTRICT,
                PRIMARY KEY(sheet_id, scene_id));
            CREATE TABLE drawing_sheet_components(
                sheet_id TEXT REFERENCES drawing_sheets(sheet_id) ON DELETE CASCADE,
                component_id TEXT REFERENCES components(component_id) ON DELETE RESTRICT,
                PRIMARY KEY(sheet_id, component_id));
            INSERT INTO drawing_sheets VALUES('sheet_old', 'Preserve title');
            INSERT INTO components(component_id, model_path, rhino_group_id, name, created_at, updated_at)
                VALUES('component_old', 'C:/model.3dm', 'group-old', 'Old', 'date', 'date');
            INSERT INTO drawing_sheet_components VALUES('sheet_old', 'component_old');
        ''')
        db.execute("INSERT INTO drawing_sheet_scenes VALUES('sheet_old', ?)", (scene['scene_id'],))
    return store, scene


def test_legacy_sheet_rows_survive_and_no_longer_block_components(tmp_path):
    store, scene = legacy_store(tmp_path)
    migrated = AlmondStore(store.database_path)
    with migrated._connect() as db:
        assert tuple(db.execute('SELECT * FROM drawing_sheets').fetchone()) == ('sheet_old', 'Preserve title')
        db.execute("DELETE FROM components WHERE component_id='component_old'")
        assert tuple(db.execute('SELECT * FROM drawing_sheet_components').fetchone()) == ('sheet_old', 'component_old')
        assert tuple(db.execute('SELECT * FROM drawing_sheet_scenes').fetchone()) == ('sheet_old', scene['scene_id'])
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    reopened = AlmondStore(store.database_path)
    assert reopened.get_scene(scene['scene_id'])['name'] == 'Kept'
    assert not hasattr(reopened, 'upsert_drawing_sheet')
    assert not hasattr(reopened, 'sync_drawing_sheet')


def test_fresh_project_does_not_create_sheet_tables(tmp_path):
    store = AlmondStore(tmp_path / 'DB')
    with store._connect() as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'drawing_sheet%'").fetchall() == []


def test_retirement_conflict_preserves_original_rows(tmp_path):
    store, scene = legacy_store(tmp_path)
    with store._connect() as db:
        db.execute('CREATE TABLE drawing_sheet_components_retired_migration(keep TEXT)')
        db.execute("INSERT INTO drawing_sheet_components_retired_migration VALUES('unrelated')")
    with pytest.raises(sqlite3.OperationalError):
        AlmondStore(store.database_path)
    with store._connect() as db:
        assert tuple(db.execute('SELECT * FROM drawing_sheet_components').fetchone()) == ('sheet_old', 'component_old')
        assert db.execute('SELECT keep FROM drawing_sheet_components_retired_migration').fetchone()[0] == 'unrelated'
