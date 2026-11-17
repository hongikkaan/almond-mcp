"""The project file catalog is authored explicitly and keyed by filename."""
import sqlite3
from contextlib import closing

import pytest

from almond_mcp.retrieval_store import AlmondStore


def test_catalog_upsert_persists_description_under_the_same_filename(tmp_path):
    path = tmp_path / "scene.sqlite3"
    store = AlmondStore(path)
    assert store.upsert_project_file("Site.3dm", "Survey before renovation") == {
        "file_name": "Site.3dm", "description": "Survey before renovation",
    }
    store.upsert_project_file("site.3DM", "Verified boundary survey")
    store.upsert_project_file("SITE.3dm")

    reopened = AlmondStore(path)
    assert reopened.list_project_files()["files"] == [
        {"file_name": "Site.3dm", "description": "Verified boundary survey"},
    ]
    assert reopened.upsert_project_file("site.3dm", "")["description"] is None


def _legacy_database(path):
    """Pre-migration schema with explicit, ordered Phase and Scene file keys."""
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE project_files(file_id TEXT PRIMARY KEY, file_name TEXT NOT NULL);
            CREATE TABLE _project_file_locations(file_id TEXT PRIMARY KEY REFERENCES project_files(file_id), model_path TEXT NOT NULL UNIQUE);
            CREATE TABLE scenes(scene_id TEXT PRIMARY KEY,name TEXT NOT NULL,units TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                project_file_id TEXT REFERENCES project_files(file_id) ON DELETE RESTRICT);
            CREATE TABLE generation_phases(phase_id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                project_file_id TEXT REFERENCES project_files(file_id) ON DELETE RESTRICT);
            CREATE TABLE generation_phase_files(phase_id TEXT REFERENCES generation_phases(phase_id),
                file_id TEXT REFERENCES project_files(file_id),position INTEGER,PRIMARY KEY(phase_id,file_id), UNIQUE(phase_id,position));
            CREATE TABLE scene_object_membership(scene_id TEXT REFERENCES scenes(scene_id),
                project_file_id TEXT REFERENCES project_files(file_id),rhino_guid TEXT,included INTEGER,
                PRIMARY KEY(scene_id,project_file_id,rhino_guid));
            CREATE TABLE ontological_holons(
                ontological_id TEXT PRIMARY KEY,project_file_id TEXT NOT NULL REFERENCES project_files(file_id),
                rhino_group_id TEXT NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                parent_ontological_id TEXT REFERENCES ontological_holons(ontological_id),
                availability TEXT NOT NULL DEFAULT 'present',geometry_digest TEXT NOT NULL DEFAULT '',
                object_count INTEGER NOT NULL DEFAULT 0,effective_object_count INTEGER NOT NULL DEFAULT 0,
                effective_summary_stale INTEGER NOT NULL DEFAULT 0 CHECK(effective_summary_stale IN (0,1)),
                object_types_json TEXT NOT NULL DEFAULT '{}',bounds_json TEXT NOT NULL DEFAULT 'null',
                UNIQUE(project_file_id,rhino_group_id));
            INSERT INTO project_files VALUES ('old_site','Site.3dm'),('old_bldg','Building.3dm');
            INSERT INTO scenes VALUES ('scene_existing','Existing scene','mm',0,'2026-11-01','2026-11-01','old_site');
            INSERT INTO generation_phases VALUES ('phase_existing','Existing phase','','2026-11-01','2026-11-01','old_site');
            INSERT INTO generation_phase_files VALUES ('phase_existing','old_site',0),('phase_existing','old_bldg',1);
            INSERT INTO scene_object_membership VALUES ('scene_existing','old_site','shape_guid',1);
            INSERT INTO ontological_holons(ontological_id,project_file_id,rhino_group_id,name,created_at,updated_at)
                VALUES ('old_holon','old_site','group_guid','Existing holon','2026-11-01','2026-11-01');
        """)
        db.execute("INSERT INTO _project_file_locations VALUES(?,?)", ("old_site", r"C:\old\Site.3dm"))


def test_legacy_catalog_and_ordered_file_links_migrate_to_the_canonical_names(tmp_path):
    path = tmp_path / "scene.sqlite3"
    _legacy_database(path)
    for _ in range(2):
        store = AlmondStore(path)
        assert store.list_project_files()["files"] == [
            {"file_name": "Building.3dm", "description": None},
            {"file_name": "Site.3dm", "description": None},
        ]
        assert store.get_phase("phase_existing")["file_names"] == ["Site.3dm", "Building.3dm"]
        assert store.get_scene("scene_existing")["file_name"] == "Site.3dm"
        assert store.get_scene("scene_existing")["direct_objects"] == 1
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT * FROM _project_file_locations").fetchall() == [("Site.3dm", r"C:\old\Site.3dm")]
        assert db.execute("SELECT file_name, rhino_group_id FROM ontological_holons WHERE ontological_id='old_holon'").fetchone() == (
            "Site.3dm", "group_guid",
        )
        assert db.execute("SELECT file_name,rhino_guid,included FROM scene_object_membership").fetchall() == [
            ("Site.3dm", "shape_guid", 1),
        ]
        assert all("file_id" not in row[1] for table in (
            "project_files", "_project_file_locations", "scenes", "generation_phases",
            "generation_phase_files", "ontological_holons", "scene_object_membership"
        ) for row in db.execute(f"PRAGMA table_info({table})"))


def _database_snapshot(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        schema = db.execute("SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name").fetchall()
        rows = {
            name: sorted(db.execute(f'SELECT * FROM "{name}"').fetchall(), key=repr)
            for kind, name, _, _ in schema if kind == "table"
        }
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        return schema, rows


@pytest.mark.parametrize("failure", ["file-key-update", "final-foreign-key-check"])
def test_failed_initialization_preserves_committed_schema_and_rows(tmp_path, failure):
    path = tmp_path / "legacy.sqlite3"
    _legacy_database(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE validation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT NOT NULL, structure_type TEXT NOT NULL,
                material TEXT NOT NULL, load_kn REAL NOT NULL, member_count INTEGER NOT NULL,
                analysis_method TEXT NOT NULL, confidence TEXT NOT NULL, passed INTEGER NOT NULL,
                span_m REAL NOT NULL, max_deflection_mm REAL NOT NULL, deflection_limit_mm REAL NOT NULL,
                utilization_ratio REAL NOT NULL, max_stress_mpa REAL NOT NULL, yield_stress_mpa REAL NOT NULL,
                reactions_kn REAL NOT NULL, verdict TEXT NOT NULL, warnings_json TEXT NOT NULL, guids_json TEXT NOT NULL
            );
            INSERT INTO validation_runs VALUES
                (13, '2026-11-10', 'beam', 'Steel', 10, 1, 'native', 'high', 1,
                 2, 0.5, 8, 0.2, 20, 235, 10, 'old verdict', '["warning"]', '["shape_guid"]');
            UPDATE sqlite_sequence SET seq = 89 WHERE name = 'validation_runs';
        """)
        # file_name first exists during the file-key migration, after structural,
        # semantic and Plan initialization. Use real SQLite faults at that point.
        if failure == "file-key-update":
            db.execute("""
                CREATE TRIGGER migration_fixture AFTER UPDATE OF file_name ON generation_phases
                BEGIN SELECT RAISE(ABORT, 'fixture failed during file-key migration'); END
            """)
            error, message = sqlite3.IntegrityError, "fixture failed during file-key migration"
        else:
            db.executescript("""
                CREATE TABLE fixture_parent(id INTEGER PRIMARY KEY);
                CREATE TABLE fixture_child(id INTEGER REFERENCES fixture_parent(id));
                CREATE TRIGGER migration_fixture AFTER UPDATE OF file_name ON generation_phases
                BEGIN INSERT INTO fixture_child VALUES (99); END;
            """)
            error, message = ValueError, "DB migration found invalid relationships"

    before = _database_snapshot(path)
    assert before[1]["sqlite_sequence"] == [("validation_runs", 89)]
    for _ in range(2):
        with pytest.raises(error, match=message):
            AlmondStore(path)
        assert _database_snapshot(path) == before

    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DROP TRIGGER migration_fixture")
    store = AlmondStore(path)
    assert store.get_phase("phase_existing")["file_names"] == ["Site.3dm", "Building.3dm"]
    assert [(run["id"], run["status"]) for run in store.list_validation_runs()] == [(13, "pass")]
    after = _database_snapshot(path)
    assert after[1]["sqlite_sequence"] == [("validation_runs", 89)]
    AlmondStore(path)
    assert _database_snapshot(path) == after


def test_legacy_case_collision_reports_both_paths_and_does_not_modify_database(tmp_path):
    path = tmp_path / "scene.sqlite3"
    _legacy_database(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("INSERT INTO project_files VALUES('old_other','SITE.3dm')")
        db.execute("INSERT INTO _project_file_locations VALUES(?,?)", ("old_other", r"D:\other\SITE.3dm"))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="unique filenames") as exc:
        AlmondStore(path)
    assert r"C:\old\Site.3dm" in str(exc.value)
    assert r"D:\other\SITE.3dm" in str(exc.value)
    assert path.read_bytes() == before


def test_pre_catalog_holon_paths_are_checked_before_any_schema_write(tmp_path):
    path = tmp_path / "scene.sqlite3"
    source = r"C:\one\Hall.3dm"
    duplicate = r"D:\two\HALL.3dm"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE components(component_id TEXT,model_path TEXT)")
        db.executemany("INSERT INTO components VALUES(?,?)", [("a", source), ("b", duplicate)])
    before = path.read_bytes()
    with pytest.raises(ValueError, match="unique filenames") as exc:
        AlmondStore(path)
    assert source in str(exc.value) and duplicate in str(exc.value)
    assert path.read_bytes() == before


def test_scene_can_select_registered_file_or_leave_it_empty(tmp_path):
    store = AlmondStore(tmp_path / "scene.sqlite3")
    with pytest.raises(ValueError, match="not registered"):
        store.create_scene("Reject unregistered filename", file_name="site.3dm")
    assert store.list_project_files()["files"] == []
    store.upsert_project_file("Site.3dm", "Survey")
    scene = store.create_scene("Site scene", file_name="SITE.3dm")
    assert scene["file_name"] == "Site.3dm"
    assert [row["scene_id"] for row in store.list_scenes(file_name="site.3DM")["scenes"]] == [scene["scene_id"]]
    assert store.update_scene(scene["scene_id"], "")["file_name"] == ""
