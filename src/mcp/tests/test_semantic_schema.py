"""User-facing semantic relationships and real legacy migration contracts."""
import sqlite3
import uuid

import pytest

from almond_mcp.retrieval_store import AlmondStore
from legacy_db import legacy_store


@pytest.fixture
def store(tmp_path):
    return AlmondStore(tmp_path / 'scene.sqlite3')


def test_file_names_are_readable_stable_references_shared_by_scene_and_phase(store):
    scene = store.create_scene('Building', file_name='building.3dm')
    key = scene['project_file_id']
    uuid.UUID(key)
    phase = store.create_phase('Design', project_file_id=key, status='running')
    assert phase['file_name'] == 'building.3dm' and phase['project_file_id'] == key
    assert store.list_project_files()['files'] == [dict(project_file_id=key,file_name='building.3dm')]
    with store._connect() as db:
        assert {r['name'] for r in db.execute('PRAGMA table_info(project_files)')} == {'file_id','file_name'}
        for table in ('scenes','generation_phases','ontological_components'):
            assert any(r['table']=='project_files' for r in db.execute(f'PRAGMA foreign_key_list({table})'))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM project_files WHERE file_id=?',(key,))
    assert store.update_phase(phase['phase_id'],status='paused')['status']=='paused'
    assert store.update_scene(scene['scene_id'],file_name='')['project_file_id'] is None


def test_duplicate_filenames_require_an_explicit_key_and_never_merge_model_identity(store):
    with store._connect() as db:
        first=store._project_file_reference(db,model_path='C:/one/model.3dm')
        second=store._project_file_reference(db,model_path='C:/two/model.3dm')
        assert first!=second
        assert store._project_file_reference(db,model_path='C:/one/model.3dm')==first
    with pytest.raises(ValueError,match='Several'):
        store.create_scene('Ambiguous',file_name='model.3dm')
    assert store.create_scene('Explicit',project_file_id=second)['project_file_id']==second
    with pytest.raises(ValueError,match='different files'):
        store.create_phase('Wrong',file_name='different.3dm',project_file_id=first)


@pytest.mark.parametrize('name',['C:/models/a.3dm',r'C:\models\a.3dm',r'folder\a.3dm','..','/model.3dm'])
def test_project_file_display_name_does_not_accept_paths(store,name):
    with pytest.raises(ValueError):
        store.create_scene('Bad',file_name=name)
    with store._connect() as db, pytest.raises(sqlite3.IntegrityError):
        db.execute('INSERT INTO project_files VALUES(?,?)',(str(uuid.uuid4()),name))
    assert store.list_project_files()['total']==0


def test_workflow_choices_enforced_in_api_and_sql_and_custom_scope_uses_template(store):
    phase=store.create_phase('Work')
    plan=store.create_plan('Work',scope='component',phase_id=phase['phase_id'])
    for status in ('pending','running','completed','failed','blocked','paused'):
        assert store.update_phase(phase['phase_id'],status=status)['status']==status
    with pytest.raises(ValueError):
        store.update_phase(phase['phase_id'],status='invented')
    with store._connect() as db:
        for table in ('generation_phases','generation_plans','generation_plan_steps'):
            assert any(r['from']=='status' and r['table']=='workflow_statuses' for r in db.execute(f'PRAGMA foreign_key_list({table})'))
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"UPDATE {table} SET status='invented'")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO workflow_statuses VALUES('invented')")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE generation_plans SET scope='invented'")
        db.execute("INSERT INTO planning_scopes VALUES('facade','component')")
    custom=store.create_plan('Facade',scope='facade')
    assert custom['scope']=='facade'
    assert [s['step_id'] for s in custom['steps']]==[s['step_id'] for s in plan['steps']]
    assert len(custom['created_at'])==22 and custom['created_at'][-6:]=='+00:00'
    reopened=AlmondStore(store.database_path)
    assert reopened.get_plan(custom['plan_id'])['scope']=='facade'


def test_user_scope_edits_survive_reopening_and_filename_only_insert_allocates_key(store):
    with store._connect() as db:
        db.execute("DELETE FROM planning_scopes WHERE scope='house'")
        db.execute("UPDATE planning_scopes SET scope='details' WHERE scope='drawing'")
        db.execute("INSERT INTO project_files(file_name) VALUES('manual.3dm')")
        uuid.UUID(db.execute('SELECT file_id FROM project_files').fetchone()[0])
    reopened=AlmondStore(store.database_path)
    with pytest.raises(ValueError,match='Unknown scope'):
        reopened.create_plan('Removed scope',scope='house')
    assert reopened.create_plan('Details',scope='details')['steps'][0]['step_id']=='freeze_scene'


def test_explicit_scene_context_has_foreign_key_and_cannot_leave_dangling_ids(tmp_path):
    old,scene,_=legacy_store(tmp_path/'scene.sqlite3')
    migrated=AlmondStore(old.database_path)
    with migrated._connect() as db:
        assert 'scene_ids_json' not in {r['name'] for r in db.execute('PRAGMA table_info(ontological_components)')}
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM scenes WHERE scene_id=?',(scene,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO ontological_scene_context VALUES('component_old','unknown')")
    assert migrated.get_component('component_old')['scene_ids']==[scene]


def seed_plan_rows(db,scene):
    db.executescript('''
        CREATE TABLE generation_phases(phase_id TEXT PRIMARY KEY,name TEXT,description TEXT,created_at TEXT,updated_at TEXT,file_name TEXT);
        CREATE TABLE generation_plans(plan_id TEXT PRIMARY KEY,scene_id TEXT REFERENCES scenes(scene_id),scope TEXT NOT NULL,
            goal TEXT,status TEXT NOT NULL,created_at TEXT,updated_at TEXT,phase_id TEXT REFERENCES generation_phases(phase_id));
        CREATE TABLE generation_plan_steps(plan_id TEXT REFERENCES generation_plans(plan_id),step_id TEXT,position INTEGER,
            kind TEXT,status TEXT NOT NULL,depends_on_json TEXT,input_refs_json TEXT,output_refs_json TEXT,PRIMARY KEY(plan_id,step_id));
        CREATE TABLE generation_plan_components(plan_id TEXT REFERENCES generation_plans(plan_id),component_id TEXT REFERENCES components(component_id),position INTEGER,PRIMARY KEY(plan_id,component_id));
        CREATE TABLE generation_step_components(plan_id TEXT,step_id TEXT,component_id TEXT REFERENCES components(component_id),position INTEGER,
            FOREIGN KEY(plan_id,step_id) REFERENCES generation_plan_steps(plan_id,step_id));
        INSERT INTO generation_phases VALUES('phase','Phase','Keep description','2026-01-01T12:34:56+00:00','2026-01-01T12:34:56+00:00','model.3dm');
        INSERT INTO generation_plans VALUES('plan','scene_old','component','Keep goal','paused','2026-01-01T12:34:56+00:00','2026-01-01T12:34:56+00:00','phase');
        INSERT INTO generation_plan_steps VALUES('plan','design',0,'reason','completed','[]','["input"]','["output"]');
        INSERT INTO generation_plan_components VALUES('plan','component_old',0);
        INSERT INTO generation_step_components VALUES('plan','design','component_old',0);
    ''')


def test_legacy_migration_preserves_all_semantic_references_and_has_no_member_tables(tmp_path):
    old,scene,model=legacy_store(tmp_path/'scene.sqlite3')
    with old._connect() as db:
        seed_plan_rows(db,scene)
    migrated=AlmondStore(old.database_path)
    component=migrated.get_component('component_old')
    phase=migrated.get_phase('phase')
    assert phase['status']=='pending' and phase['description']=='Keep description'
    assert phase['created_at']=='2026-01-01T12:34+00:00'
    assert phase['project_file_id']==migrated.get_scene(scene)['project_file_id']
    plan=migrated.get_plan('plan')
    assert plan['phase_id']=='phase' and plan['status']=='paused'
    assert plan['component_ids']==['component_old'] and plan['scene_ids']==[scene]
    assert plan['steps'][0]['component_ids']==['component_old']
    assert plan['steps'][0]['output_refs']==['output']
    with migrated._connect() as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not tables & {'components','scene_components','document_objects','scene_objects','generation_plan_components','generation_step_components'}
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert component['model_path']==migrated._component_model_path(model)
    assert len(list(tmp_path.glob('*.bak')))==1
    AlmondStore(old.database_path)
    assert len(list(tmp_path.glob('*.bak')))==1


def test_invalid_legacy_reference_rolls_back_migration_and_preserves_backup(tmp_path):
    old,scene,model=legacy_store(tmp_path/'scene.sqlite3')
    with old._connect() as db:
        seed_plan_rows(db,scene)
        db.execute("UPDATE generation_plans SET status='not-a-status'")
    with pytest.raises(ValueError,match='invalid relationships'):
        AlmondStore(old.database_path)
    with old._connect() as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='components'").fetchone()
        assert db.execute("SELECT name FROM sqlite_master WHERE name='ontological_components'").fetchone() is None
        assert db.execute('SELECT status FROM generation_plans').fetchone()[0]=='not-a-status'
    assert len(list(tmp_path.glob('*.bak')))==1
