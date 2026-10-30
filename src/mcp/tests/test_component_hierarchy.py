"""Semantic hierarchy persistence with geometry owned by an independent native fake."""
import copy
import sqlite3
import uuid

import pytest

from almond_mcp.retrieval_store import AlmondStore, ComponentReconciliationError

A, B, C = [str(uuid.UUID(int=value)) for value in (101, 102, 103)]


def object_row(guid, component_id, kind="Brep"):
    return dict(rhino_guid=guid,object_type=kind,component_id=component_id,bounds_mm=[0,0,0,100,200,300])


class NativeGroups:
    """External document state: never reconstruct geometry from the SQLite store."""
    def __init__(self):
        self.records={}
        self.calls=[]

    def read(self, handle):
        row=copy.deepcopy(self.records[handle])
        available=row.get('availability','present')=='present'
        direct=row['objects'] if available else []
        effective={o['rhino_guid']:o for o in direct}
        if available:
            for child in row['child_component_ids']:
                effective.update({o['rhino_guid']:o for o in self.read(child)['effective_objects']})
        row.update(objects=direct,object_ids=sorted(o['rhino_guid'] for o in direct),
            effective_objects=[effective[g] for g in sorted(effective)],effective_object_ids=sorted(effective))
        return row

    def __call__(self, request):
        self.calls.append(copy.deepcopy(request))
        action=request['action']
        if action=='inspect_many':
            ids=request.get('component_ids')
            ids=set(ids if ids is not None else [h for h,r in self.records.items() if r['model_path']==request['expected_model_path']])
            if request.get('discover_scene'):
                ids.update(h for h,r in self.records.items() if request['scene_id'] in r['scene_ids'] and r['model_path']==request['expected_model_path'])
            pending=list(ids)
            while pending:
                for child in self.records[pending.pop()]['child_component_ids']:
                    if child not in ids:
                        ids.add(child); pending.append(child)
            return dict(status='success',complete=True,model_path=request['expected_model_path'],editing={'stable':True},
                components=[self.read(h) for h in sorted(ids)],problems=[])
        handle=request['component_id']
        if action=='inspect':
            return dict(status='success',component=self.read(handle))
        if action=='unregister':
            old=self.records[handle]
            children=old['child_component_ids'][:]
            for child in children:
                self.records[child]['parent_component_id']=None
            old['availability']='unregistered'
            old['child_component_ids']=[]
            return dict(status='success',component_id=handle,model_path=old['model_path'],rhino_group_id=old['rhino_group_id'],
                detached_child_component_ids=children,affected_components=[self.read(h) for h in children])
        assert action=='upsert'
        for h,row in self.records.items():
            if h!=handle and row['model_path']==request['expected_model_path'] and row.get('availability','present')=='present':
                if set(request['object_ids']) & {o['rhino_guid'] for o in row['objects']}:
                    return dict(status='error',message='Object is directly owned by another meaning unit.',mutation_applied=False)
        previous=self.records.get(handle)
        old_children=set(previous['child_component_ids']) if previous else set()
        children=request.get('child_component_ids',[])
        row=dict(complete=True,component_id=handle,model_path=request['expected_model_path'],
            rhino_group_id=request.get('rhino_group_id') or str(uuid.uuid5(uuid.NAMESPACE_URL,handle)),
            name=request['name'],scene_ids=request['scene_ids'],child_component_ids=children,
            parent_component_id=previous['parent_component_id'] if previous else None,availability='present',
            objects=[object_row(g,handle) for g in request['object_ids']])
        self.records[handle]=row
        related=set(children)|old_children
        for child in related:
            self.records[child]['parent_component_id']=handle if child in children else None
        parent=row['parent_component_id']
        while parent:
            related.add(parent)
            parent=self.records[parent]['parent_component_id']
        return dict(status='success',component=self.read(handle),affected_components=[self.read(h) for h in sorted(related)])


@pytest.fixture
def store(tmp_path):
    result=AlmondStore(tmp_path/'hierarchy.sqlite3')
    result.scene_a=result.create_scene('Facade')['scene_id']
    result.scene_b=result.create_scene('Interior')['scene_id']
    result.model=result._component_model_path(str(tmp_path/'model.3dm'))
    result.fixture_bridge=NativeGroups()
    return result


def simulated_native(store,calls=None):
    if not hasattr(store,'fixture_bridge'):
        store.fixture_bridge=NativeGroups()
    def emit(request):
        if calls is not None:
            calls.append(request)
        return store.fixture_bridge(request)
    return emit


def create(store,name,direct,scenes=None,children=None,**extra):
    return store.upsert_component(store.model,name,direct,scene_ids=scenes or [store.scene_a],
        child_component_ids=children,native_apply=simulated_native(store),**extra)


def test_parent_with_no_direct_objects_inherits_child_geometry_and_scene_context(store):
    child=create(store,'Panel',[A])
    parent=create(store,'Assembly',[],scenes=[store.scene_b],children=[child['component_id']])
    assert parent['object_ids']==[] and parent['effective_object_ids']==[A]
    cached=store.get_component(child['component_id'])
    assert cached['parent_component_id']==parent['component_id'] and cached['scene_ids']==[store.scene_a]
    assert store.get_scene(store.scene_b)['objects']==1
    rows=store.scene_objects(store.scene_b,store.model,store.fixture_bridge)
    assert [r['rhino_guid'] for r in rows]==[A]
    plan=store.create_plan('Facade',component_ids=[parent['component_id']])
    assert store.resolve_targets(plan['plan_id'])['components'][0]['child_component_ids']==[child['component_id']]


def test_child_only_alignment_hides_stale_parent_summary_until_parent_observed(store):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    store.fixture_bridge.records[child['component_id']]['objects'].append(object_row(C,child['component_id']))
    store.align_components(store.model,[child['component_id']],native_inspect=store.fixture_bridge)
    stale=store.get_component(parent['component_id'])
    assert stale['requires_sync'] is True
    assert stale['effective_object_count'] is None and stale['bounds_mm'] is None
    assert stale['object_count']==1
    live=store.get_component(parent['component_id'],live=True,native_inspect=store.fixture_bridge)
    assert live['effective_object_count']==3 and live['requires_sync'] is True
    assert store.get_component(parent['component_id'])['effective_object_count'] is None
    store.align_components(store.model,[parent['component_id']],native_inspect=store.fixture_bridge)
    assert store.get_component(parent['component_id'])['effective_object_count']==3
    assert not store.get_component(parent['component_id']).get('requires_sync')
    assert store.align_components(store.model,[parent['component_id']],native_inspect=store.fixture_bridge)['changed']==0


def test_explicit_reparent_requires_detach_and_cycle_is_rejected_before_native(store):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    before=len(store.fixture_bridge.calls)
    with pytest.raises(ValueError,match='detach'):
        create(store,'Other',[C],children=[child['component_id']])
    with pytest.raises(ValueError,match='cycle'):
        create(store,'Panel',[A],component_id=child['component_id'],children=[parent['component_id']])
    assert len(store.fixture_bridge.calls)==before


def test_direct_sql_cannot_add_cross_document_parent_or_cycle(store,tmp_path):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    other=store.upsert_component(str(tmp_path/'other.3dm'),'Other',[C],scene_ids=[store.scene_a],native_apply=store.fixture_bridge)
    for node,ancestor in [(parent['component_id'],child['component_id']),(child['component_id'],other['component_id'])]:
        with pytest.raises(sqlite3.IntegrityError):
            with store._connect() as db:
                db.execute('UPDATE ontological_components SET parent_ontological_id=? WHERE ontological_id=?',(ancestor,node))


def test_child_update_propagates_group_summaries_without_persisting_members(store):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    create(store,'Panel',[A,C],component_id=child['component_id'])
    assert store.get_component(parent['component_id'])['effective_object_count']==3
    assert 'objects' not in store.get_component(child['component_id'])
    observed=store.get_component(parent['component_id'],True,store.fixture_bridge)
    assert observed['effective_object_ids']==[A,B,C]


def test_root_parent_unregister_detaches_children_but_child_cannot_unregister_until_detached(store):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    with pytest.raises(ValueError,match='Detach'):
        store.unregister_component(child['component_id'],store.fixture_bridge)
    store.unregister_component(parent['component_id'],store.fixture_bridge)
    assert store.get_component(parent['component_id']) is None
    assert store.get_component(child['component_id'])['parent_component_id'] is None
    assert store.get_component(child['component_id'])['object_count']==1


@pytest.mark.parametrize('change',['bounds','object_type','name','identity'])
def test_live_parent_reports_descendant_drift_without_changing_saved_summary(store,change):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    before=store.get_component(parent['component_id'])
    obj=store.fixture_bridge.records[child['component_id']]['objects'][0]
    if change=='bounds': obj['bounds_mm']=[5,0,0,105,200,300]
    if change=='object_type': obj['object_type']='TextDot'
    if change=='name': obj['name']='Changed annotation'
    if change=='identity': obj['rhino_guid']=C
    observed=store.get_component(parent['component_id'],True,store.fixture_bridge)
    assert observed['requires_sync'] and observed['live_verified']
    assert store.get_component(parent['component_id'])==before


def test_parent_alignment_rejects_contradictory_child_geometry_atomically(store):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    before=store.get_component(parent['component_id'])
    def bad(request):
        response=store.fixture_bridge(request)
        root=next(r for r in response['components'] if r['component_id']==parent['component_id'])
        root['effective_objects'][0]['bounds_mm']=[10,0,0,110,200,300]
        return response
    with pytest.raises(ValueError,match='geometry|membership'):
        store.align_components(store.model,[parent['component_id']],native_inspect=bad)
    assert store.get_component(parent['component_id'])==before


def test_existing_unchanged_alignment_does_not_create_spurious_scene_revisions(store):
    child=create(store,'Panel',[A]); parent=create(store,'Assembly',[B],children=[child['component_id']])
    before=store.get_scene(store.scene_a)['revision']
    assert store.align_components(store.model,[parent['component_id']],native_inspect=store.fixture_bridge)['changed']==0
    assert store.get_scene(store.scene_a)['revision']==before


def test_old_component_table_adds_parent_column_without_rewriting_identity(tmp_path):
    path=tmp_path/'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE components(component_id TEXT PRIMARY KEY,model_path TEXT NOT NULL,rhino_group_id TEXT NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(component_id,model_path),UNIQUE(model_path,rhino_group_id))')
        db.execute('INSERT INTO components VALUES(?,?,?,?,?,?)',('legacy',str(tmp_path/'model.3dm'),str(uuid.UUID(int=88)),'Old','old','old'))
    migrated=AlmondStore(path).get_component('legacy')
    assert migrated['name']=='Old' and migrated['parent_component_id'] is None
    assert migrated['created_at']=='old' and 'objects' not in migrated
