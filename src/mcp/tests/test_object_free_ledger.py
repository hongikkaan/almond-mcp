"""Public ledger behavior and the user-visible SQL storage contract."""
import copy
import json
import sqlite3
import uuid

import pytest

from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.store_common import ComponentReconciliationError

A, B, GROUP = [str(uuid.UUID(int=i)) for i in (1, 2, 100)]


def geometry(guid, owner):
    return dict(rhino_guid=guid, component_id=owner, object_type='Brep', name='Member',
                bounds_mm=[0.0, 0.0, 0.0, 100.0, 200.0, 300.0])


def snapshot(request):
    return dict(complete=True, component_id=request['component_id'],
        model_path=request['expected_model_path'], rhino_group_id=request.get('rhino_group_id') or GROUP,
        name=request['name'], scene_ids=request['scene_ids'], parent_component_id=None,
        child_component_ids=[], availability='present',
        objects=[geometry(guid,request['component_id']) for guid in request['object_ids']])


@pytest.fixture
def project(tmp_path):
    store=AlmondStore(tmp_path/'scene.sqlite3')
    scene=store.create_scene('Dining')['scene_id']
    model=store._component_model_path(str(tmp_path/'Dining.3dm'))
    return store,scene,model


def register(project, ids=None):
    store,scene,model=project
    return store.upsert_component(model,'Table',[A] if ids is None else ids,scene_ids=[scene],
        component_id='table',rhino_group_id=GROUP,native_apply=lambda request: dict(status='success',component=snapshot(request)))


def batch(model, items, **extra):
    return dict(status='success',complete=True,model_path=model,components=items,problems=[],editing={'stable':True},**extra)


def test_object_free_registration_survives_reopen_without_member_ids(project):
    store,scene,model=project
    registered=register(project,[A,B])
    assert registered['object_count']==2
    assert registered['object_ids']==[A,B]  # transient native response remains usable
    reopened=AlmondStore(store.database_path)
    cached=reopened.get_component('table')
    assert cached['object_count']==2 and cached['geometry_available'] is False
    assert 'object_ids' not in cached and 'objects' not in cached
    assert reopened.get_scene(scene)['objects']==2
    with sqlite3.connect(store.database_path) as db:
        schema={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        assert not {'document_objects','scene_objects'} & schema
        dump='\n'.join(db.iterdump())
        assert A not in dump and B not in dump


def test_object_free_live_read_does_not_change_saved_summary(project):
    store,scene,model=project
    registered=register(project)
    observed=dict(registered,complete=True,objects=[geometry(B,'table')],object_ids=[B],direct_object_ids=[B],
        effective_objects=[geometry(B,'table')],effective_object_ids=[B])
    result=store.get_component('table',live=True,native_inspect=lambda _:dict(status='success',component=observed))
    assert result['object_ids']==[B] and result['requires_sync']
    assert store.get_component('table')['object_count']==1
    with sqlite3.connect(store.database_path) as db:
        assert B not in '\n'.join(db.iterdump())


def test_object_free_alignment_tracks_group_change_and_is_idempotent(project):
    store,scene,model=project
    registered=register(project)
    observed=dict(registered,complete=True,objects=[geometry(A,'table'),geometry(B,'table')],
        object_ids=[A,B],effective_objects=[geometry(A,'table'),geometry(B,'table')],effective_object_ids=[A,B])
    def inspect(request):
        assert 'prior_object_ids' not in request
        return batch(model,[observed])
    result=store.align_components(model,native_inspect=inspect)
    assert result['changed']==1 and store.get_component('table')['object_count']==2
    revision=store.get_scene(scene)['revision']
    assert store.align_components(model,native_inspect=inspect)['changed']==0
    assert store.get_scene(scene)['revision']==revision


@pytest.mark.parametrize('failure',['unstable','incomplete','wrong_model','missing','duplicate','wrong_owner'])
def test_object_free_invalid_observation_preserves_existing_registration(project,failure):
    store,scene,model=project
    registered=register(project)
    reply=batch(model,[dict(registered,complete=True)])
    if failure=='unstable': reply['editing']['stable']=False
    if failure=='incomplete': reply['complete']=False
    if failure=='wrong_model': reply['model_path']=model.replace('dining.3dm','other.3dm').replace('Dining.3dm','Other.3dm')
    if failure=='missing': reply['components']=[]
    if failure=='duplicate': reply['components']*=2
    if failure=='wrong_owner': reply['components'][0]['objects'][0]['component_id']='other'
    before=store.get_component('table')
    with pytest.raises(ValueError):
        store.align_components(model,native_inspect=lambda _:reply)
    assert store.get_component('table')==before


def test_object_free_scene_geometry_is_live_and_has_no_direct_registration(project):
    store,scene,model=project
    registered=register(project)
    assert not hasattr(store,'register_scene_objects')
    rows=store.scene_objects(scene,model,native_inspect=lambda _:batch(model,[dict(registered,complete=True)]))
    assert [row['rhino_guid'] for row in rows]==[A]
    assert rows[0]['live_verified'] is True
    with pytest.raises(ValueError,match='live'):
        store.scene_objects(scene)


def test_object_free_selection_uses_current_native_owner(project):
    store,scene,model=project
    register(project)
    plan=store.create_plan('Adjust table',scope='component',component_ids=['table'])
    result=store.selection_references(model,[A,B],native_observe=lambda _:dict(status='success',complete=True,
        model_path=model,objects=[geometry(A,'table'),geometry(B,None)]))
    assert [p['plan_id'] for p in result['plans']]==[plan['plan_id']]
    assert result['objects'][0]['registered'] is True
    assert result['objects'][1]['registered'] is False
    assert result['ownership_live_verified'] is True
    assert result['references_live_verified'] is False
    targets=store.resolve_targets(plan['plan_id'])
    assert targets['components'][0]['rhino_group_id']==GROUP
    assert 'direct_object_ids' not in targets['components'][0]


def test_object_free_unregister_preserves_native_group_and_never_replays(project):
    store,scene,model=project
    register(project)
    calls=[]
    def remove(request):
        calls.append(request)
        assert request['action']=='unregister'
        assert 'object_ids' not in request
        return dict(status='success',component_id='table',model_path=model,rhino_group_id=GROUP)
    result=store.unregister_component('table',native_apply=remove)
    assert result['status']=='unregistered' and len(calls)==1
    assert store.get_component('table') is None
    register(project)
    def uncertain(request):
        calls.append(request)
        raise TimeoutError('Lost native reply')
    with pytest.raises(ComponentReconciliationError):
        store.unregister_component('table',native_apply=uncertain)
    assert len(calls)==2 and store.get_component('table') is not None


def test_object_free_migration_backs_up_legacy_objects_then_retires_tables(tmp_path):
    from legacy_db import legacy_store
    store, scene, model = legacy_store(tmp_path / 'scene.sqlite3')
    with store._connect() as db:
        db.executescript('''CREATE TABLE document_objects(id INTEGER PRIMARY KEY,model_path TEXT,rhino_guid TEXT,
            component_id TEXT,object_type TEXT,name TEXT,min_x REAL,min_y REAL,min_z REAL,max_x REAL,max_y REAL,max_z REAL);
            CREATE TABLE scene_objects(scene_id TEXT,object_rowid INTEGER REFERENCES document_objects(id));
            CREATE TABLE scene_revisions(scene_id TEXT,revision INTEGER,operation TEXT,patch_json TEXT,created_at TEXT,PRIMARY KEY(scene_id,revision));''')
        db.execute('INSERT INTO document_objects VALUES(1,?,?,?,?,?,0,0,0,100,200,300)',(model,A,'component_old','Brep','Member'))
        db.execute('INSERT INTO scene_objects VALUES(?,1)',(scene,))
        db.execute("INSERT INTO scene_revisions VALUES(?,1,'legacy',?,'old')",(scene,json.dumps({'object_ids':[A],'component_id':'component_old'})))
    migrated=AlmondStore(store.database_path)
    assert migrated.get_component('component_old')['object_count']==1
    backups=list(store.database_path.parent.glob('scene.sqlite3.before-object-retirement-*.bak'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute('SELECT rhino_guid FROM document_objects').fetchone()[0]==A
    with sqlite3.connect(store.database_path) as db:
        assert A not in '\n'.join(db.iterdump())
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    AlmondStore(store.database_path)
    assert list(store.database_path.parent.glob('scene.sqlite3.before-object-retirement-*.bak'))==backups
