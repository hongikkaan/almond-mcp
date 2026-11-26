import sqlite3
from contextlib import closing

import pytest

from almond_mcp.retrieval_store import AlmondStore


def test_legacy_ledger_backup(tmp_path):
    database = tmp_path / "project.sqlite3"
    model = str(tmp_path / "Hall.3dm")
    # Legacy registries stored geometry on individual rows beside component identities.
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE components (
                component_id TEXT PRIMARY KEY, model_path TEXT NOT NULL,
                rhino_group_id TEXT NOT NULL, name TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                parent_component_id TEXT REFERENCES components(component_id) ON DELETE RESTRICT,
                UNIQUE(component_id, model_path), UNIQUE(model_path, rhino_group_id)
            );
            CREATE TABLE document_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, model_path TEXT NOT NULL,
                rhino_guid TEXT NOT NULL, component_id TEXT, object_type TEXT NOT NULL,
                min_x REAL NOT NULL, max_x REAL NOT NULL, min_y REAL NOT NULL, max_y REAL NOT NULL,
                min_z REAL NOT NULL, max_z REAL NOT NULL, observed_at TEXT NOT NULL,
                UNIQUE(model_path, rhino_guid),
                FOREIGN KEY(component_id, model_path) REFERENCES components(component_id, model_path)
            );
        """)
        db.execute("INSERT INTO components VALUES('hall',?,'hall-group','Entrance hall','2026','2026',NULL)", (model,))
        db.execute("""INSERT INTO document_objects VALUES
                   (7,?,'legacy-object','hall','Brep',0,1100,0,2400,0,3500,'2026')""", (model,))

    migrated = AlmondStore(database).get_component("hall")
    assert migrated["name"] == "Entrance hall"
    assert migrated["object_count"] == 1
    assert migrated["bounds_mm"] == [0, 0, 0, 1100, 2400, 3500]
    backup, = tmp_path.glob("project.sqlite3.before-object-retirement-*.bak")
    with closing(sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)) as db:
        assert db.execute("SELECT name FROM components").fetchall() == [("Entrance hall",)]
        assert db.execute("SELECT id, rhino_guid, component_id FROM document_objects").fetchall() == [(7, "legacy-object", "hall")]
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert AlmondStore(database).get_component("hall") == migrated
    assert list(tmp_path.glob("*.bak")) == [backup]


def test_filename_collision(tmp_path):
    database = tmp_path / "project.sqlite3"
    original = r"C:\original\Hall.3dm"
    duplicate = r"D:\relocated\HALL.3dm"
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("CREATE TABLE components(component_id TEXT PRIMARY KEY, model_path TEXT NOT NULL)")
        db.executemany("INSERT INTO components VALUES(?,?)", [("hall", original), ("separate-hall", duplicate)])
    before = database.read_bytes()

    with pytest.raises(ValueError, match="unique filenames") as error:
        AlmondStore(database)

    assert original in str(error.value) and duplicate in str(error.value)
    assert database.read_bytes() == before
