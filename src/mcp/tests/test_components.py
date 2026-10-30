"""Component ownership and cross-store failure contracts, using disposable SQLite and native fakes."""
import copy
from contextlib import contextmanager
import sqlite3
import uuid

import pytest

from almond_mcp.retrieval_store import AlmondStore, ComponentReconciliationError


A, B, C = [str(uuid.UUID(int=value)) for value in (1, 2, 3)]
GROUP = str(uuid.UUID(int=100))


@pytest.fixture
def store(tmp_path):
    result = AlmondStore(tmp_path / "state.sqlite3")
    result.fixture_scene_id = result.create_scene("Component fixture")["scene_id"]
    return result


@pytest.fixture
def model(tmp_path):
    return str(tmp_path / "first.3dm")


def object_row(guid, component_id=None):
    return dict(rhino_guid=guid, object_type="InstanceReference" if guid == B else "Brep",
                bounds_mm=[0, 0, 0, 100, 200, 300], component_id=component_id)


def native_component(request):
    return dict(status="success", component=dict(
        complete=True, component_id=request["component_id"],
        model_path=request["expected_model_path"],
        rhino_group_id=request["rhino_group_id"] or str(uuid.uuid5(uuid.NAMESPACE_URL, request["component_id"])),
        name=request["name"], scene_ids=request["scene_ids"],
        objects=[object_row(guid, request["component_id"]) for guid in request["object_ids"]],
    ))


def observe(request, owners=None):
    return dict(status="success", complete=True, model_path=request["expected_model_path"],
                objects=[object_row(guid, (owners or {}).get(guid)) for guid in request["object_ids"]])


def registered(store, model, objects=None, scenes=None, **kwargs):
    return store.upsert_component(
        model, "Assembly", [A, B] if objects is None else objects,
        scene_ids=[store.fixture_scene_id] if scenes is None else scenes,
        native_apply=native_component, **kwargs,
    )


def snapshot(store):
    with store._connect() as connection:
        return {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
                for table in ("scenes", "scene_revisions", "ontological_components", "project_files", "_project_file_locations",
                              "scene_ontological", "ontological_scene_context", "rooms", "instances", "instance_rtree")}


def test_shared_component_routes_to_scenes_without_individual_registration(store, model):
    first=store.create_scene('Facade')['scene_id']; second=store.create_scene('Structure')['scene_id']
    comp=registered(store,model,scenes=[first,second])
    assert store.get_scene(first)['objects']==2 and store.get_scene(second)['objects']==2
    assert not hasattr(store,'register_scene_objects')
    assert store.get_component(comp['component_id'])['geometry_available'] is False




def test_live_owner_conflict_rejects_registration_and_preserves_all_rows(store, model):
    registered(store,model,[A]); before=snapshot(store); calls=[]
    def conflict(request):
        calls.append(request)
        return dict(status='error',message='Object already belongs to another meaning unit',mutation_applied=False)
    with pytest.raises(ValueError,match='already belongs') as failure:
        store.upsert_component(model,'Other',[A],[store.fixture_scene_id],native_apply=conflict)
    assert not isinstance(failure.value,ComponentReconciliationError)
    assert len(calls)==1 and snapshot(store)==before



def test_copied_groups_in_different_documents_keep_distinct_semantic_identity(store,model,tmp_path):
    one=registered(store,model,[A],rhino_group_id=GROUP)
    two=registered(store,str(tmp_path/'copy.3dm'),[A],rhino_group_id=GROUP)
    assert one['component_id']!=two['component_id'] and len(store.list_components())==2
    assert len(store.list_components(model))==1
    with sqlite3.connect(store.database_path) as db:
        assert A not in '\n'.join(db.iterdump())



def test_windows_path_spelling_does_not_create_a_second_group_binding(store):
    registered(store,r'C:\Models\Shared.3dm',[A],rhino_group_id=GROUP)
    calls=[]
    with pytest.raises(ValueError,match='already registered'):
        store.upsert_component('c:/models/shared.3dm','Duplicate',[A],[store.fixture_scene_id],
            rhino_group_id=GROUP,native_apply=lambda request:calls.append(request))
    assert not calls



def test_group_and_component_identity_cannot_be_rebound(store, model, tmp_path):
    comp = registered(store, model, [A], rhino_group_id=GROUP)
    calls = []
    with pytest.raises(ValueError, match="already registered"):
        store.upsert_component(model, "Other", [B], rhino_group_id=GROUP,
                               native_apply=lambda request: calls.append(request))
    with pytest.raises(ValueError, match="different model_path"):
        store.upsert_component(str(tmp_path / "other.3dm"), "Other", [B],
                               component_id=comp["component_id"],
                               native_apply=lambda request: calls.append(request))
    assert calls == []


def test_membership_update_preserves_omitted_scenes_and_explicit_empty_is_rejected(store, model):
    scene = store.create_scene("Shared")["scene_id"]
    comp = registered(store, model, [A, B], [scene])
    changed = store.upsert_component(model, "Changed", [B, C], component_id=comp["component_id"],
                                     native_apply=native_component)
    assert changed["scene_ids"] == [scene]
    assert changed["rhino_group_id"] == comp["rhino_group_id"]
    assert set(changed["object_ids"]) == {B, C}
    assert store.get_scene(scene)["objects"] == 2
    # Removed members become available without deleting their physical-object identity.
    registered(store, model, [A])
    before = snapshot(store)
    with pytest.raises(ValueError, match="at least one scene"):
        store.upsert_component(model, "Changed", [B, C], scene_ids=[],
                               component_id=comp["component_id"], native_apply=native_component)
    assert snapshot(store) == before
    assert store.get_component(comp["component_id"])["scene_ids"] == [scene]


def test_unknown_scene_and_bad_input_never_call_native(store, model):
    calls = []
    with pytest.raises(KeyError):
        store.upsert_component(model, "Invalid", [A], ["missing"],
                               native_apply=lambda request: calls.append(request))
    with pytest.raises(ValueError, match="duplicate"):
        store.upsert_component(model, "Invalid", [A, A],
                               native_apply=lambda request: calls.append(request))
    assert calls == []
    assert store.list_components() == []


def test_sqlite_write_lock_is_held_while_native_runs_and_uncommitted_rows_are_invisible(store, model):
    def native(request):
        with sqlite3.connect(store.database_path, timeout=0) as peer:
            assert peer.execute("SELECT COUNT(*) FROM ontological_components").fetchone()[0] == 0
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                peer.execute("INSERT INTO scenes(scene_id,name,units,revision,created_at,updated_at) VALUES ('peer','peer','mm',0,'now','now')")
        return native_component(request)
    result = store.upsert_component(model, "Atomic", [A], [store.fixture_scene_id], native_apply=native)
    assert result["object_ids"] == [A]
    assert store.get_scene("peer") is None


@pytest.mark.parametrize("fault", [
    "partial", "truncated", "wrong_document", "wrong_members", "missing_ownership",
    "nonfinite", "inverted", "wrong_scenes", "wrong_component", "wrong_group",
])
def test_bad_native_success_requires_reconciliation_without_partial_commit(store, model, fault):
    scene = store.create_scene("Target")["scene_id"]
    before = snapshot(store)
    calls = []
    def native(request):
        calls.append(request)
        result = native_component(request)
        comp = result["component"]
        if fault == "partial":
            comp["complete"] = False
        elif fault == "truncated":
            comp["truncated"] = True
        elif fault == "wrong_document":
            comp["model_path"] = model + ".other.3dm"
        elif fault == "wrong_members":
            comp["objects"] = [object_row(B, request["component_id"])]
        elif fault == "missing_ownership":
            comp["objects"][0].pop("component_id")
        elif fault == "nonfinite":
            comp["objects"][0]["bounds_mm"][0] = float("nan")
        elif fault == "inverted":
            comp["objects"][0]["bounds_mm"][0] = 101
        elif fault == "wrong_scenes":
            comp["scene_ids"] = []
        elif fault == "wrong_component":
            comp["component_id"] = "another"
        elif fault == "wrong_group":
            comp["rhino_group_id"] = str(uuid.UUID(int=200))
        return result
    with pytest.raises(ComponentReconciliationError) as failure:
        store.upsert_component(model, "Uncertain", [A], [scene], rhino_group_id=GROUP, native_apply=native)
    assert failure.value.requires_reconciliation is True
    assert failure.value.component_id == calls[0]["component_id"]
    assert len(calls) == 1
    assert snapshot(store) == before


def test_timeout_can_be_reconciled_by_observation_without_replaying_mutation(store,model):
    applied={}; calls=[]
    def loses_response(request):
        calls.append(request['action']); applied.update(native_component(request))
        raise TimeoutError('Native result was lost')
    with pytest.raises(ComponentReconciliationError) as failure:
        store.upsert_component(model,'Applied in Rhino',[A],[store.fixture_scene_id],native_apply=loses_response)
    handle=failure.value.component_id
    assert store.get_component(handle) is None
    def inspect(request):
        calls.append(request['action'])
        return dict(status='success',complete=True,model_path=model,editing={'stable':True},
            components=[copy.deepcopy(applied['component'])],problems=[])
    store.align_components(model,[handle],native_inspect=inspect)
    assert store.get_component(handle)['object_count']==1
    assert calls==['upsert','inspect_many']



def test_verified_native_rejection_does_not_claim_ambiguity(store, model):
    before = snapshot(store)
    with pytest.raises(ValueError, match="locked group") as failure:
        store.upsert_component(model, "Rejected", [A], [store.fixture_scene_id], native_apply=lambda request: dict(
            status="error", message="locked group", mutation_applied=False,
        ))
    assert not isinstance(failure.value, ComponentReconciliationError)
    assert snapshot(store) == before


def test_failure_at_commit_after_native_does_not_retry_or_leak_rows(store, model, monkeypatch):
    original_connect = store._connect
    before = snapshot(store)
    calls = []
    @contextmanager
    def failed_commit():
        with original_connect() as connection:
            yield connection
            raise sqlite3.OperationalError("fixture commit failure")
    def native(request):
        calls.append(request)
        return native_component(request)
    with monkeypatch.context() as patch:
        patch.setattr(store, "_connect", failed_commit)
        with pytest.raises(ComponentReconciliationError, match="commit failure"):
            store.upsert_component(model, "Native changed", [A], [store.fixture_scene_id], native_apply=native)
    assert len(calls) == 1
    assert snapshot(store) == before


def test_alignment_commit_failure_rolls_back_without_claiming_native_mutation(store,model,monkeypatch):
    comp=registered(store,model,[A]); before=snapshot(store); calls=[]; original=store._connect
    @contextmanager
    def failed_commit():
        with original() as connection:
            yield connection
            raise sqlite3.OperationalError('fixture commit failure')
    changed=dict(comp,complete=True,name='Edited')
    def inspect(request):
        calls.append(request['action'])
        return dict(status='success',complete=True,model_path=model,editing={'stable':True},components=[changed],problems=[])
    with monkeypatch.context() as patch:
        patch.setattr(store,'_connect',failed_commit)
        with pytest.raises(sqlite3.OperationalError,match='commit failure'):
            store.align_components(model,native_inspect=inspect)
    assert calls==['inspect_many'] and snapshot(store)==before



def test_alignment_refuses_contradictory_live_ownership_and_preserves_registration(store,model):
    one=registered(store,model,[A]); two=registered(store,model,[B]); before=snapshot(store)
    changed=dict(two,complete=True,objects=[object_row(A,two['component_id'])],object_ids=[A],
        effective_objects=[object_row(A,two['component_id'])],effective_object_ids=[A])
    reply=dict(status='success',complete=True,model_path=model,editing={'stable':True},
        components=[dict(one,complete=True),changed],problems=[])
    with pytest.raises(ValueError,match='unrelated'):
        store.align_components(model,native_inspect=lambda _:reply)
    assert snapshot(store)==before


















def test_planar_object_bounds_are_valid_without_inventing_volume(store, model):
    def native(request):
        result = native_component(request)
        result["component"]["objects"][0]["bounds_mm"] = [0, 0, 5, 100, 200, 5]
        return result
    result = store.upsert_component(model, "Surface", [A], [store.fixture_scene_id], native_apply=native)
    assert result["objects"][0]["bounds_mm"] == [0, 0, 5, 100, 200, 5]


@pytest.mark.parametrize("reference_kind", ["plan", "step"])
def test_plan_references_block_unregister_before_any_native_mutation(store, model, reference_kind):
    comp = registered(store, model, [A])
    plan = store.create_plan(
        "Retain target", scope="component",
        component_ids=[comp["component_id"]] if reference_kind == "plan" else [],
    )
    if reference_kind == "step":
        store.update_plan_step(plan["plan_id"], plan["steps"][0]["step_id"], "pending",
                               component_ids=[comp["component_id"]])
    before = snapshot(store)
    calls = []
    with pytest.raises(ValueError, match="referenced by"):
        store.unregister_component(comp["component_id"], native_apply=lambda request: calls.append(request))
    assert calls == []
    assert snapshot(store) == before


def test_existing_registration_passes_group_identity_without_cached_member_preconditions(store,model):
    comp=registered(store,model,[A,B]); requests=[]
    def native(request):
        requests.append(request); return native_component(request)
    store.upsert_component(model,'Changed',[B],component_id=comp['component_id'],native_apply=native)
    assert requests[0]['rhino_group_id']==comp['rhino_group_id']
    assert 'expected_object_ids' not in requests[0]



@pytest.mark.parametrize("scene_ids", [None, []])
def test_new_component_requires_a_scene_before_calling_native(store, model, scene_ids):
    before = snapshot(store)
    calls = []
    with pytest.raises(ValueError, match="at least one scene"):
        store.upsert_component(model, "Orphan", [A], scene_ids=scene_ids,
                               native_apply=lambda request: calls.append(request))
    assert calls == []
    assert snapshot(store) == before


def test_alignment_cannot_leave_component_without_scene(store,model):
    comp=registered(store,model,[A]); before=snapshot(store)
    reply=dict(status='success',complete=True,model_path=model,editing={'stable':True},
        components=[dict(comp,complete=True,scene_ids=[])],problems=[])
    with pytest.raises(ValueError,match='at least one scene'):
        store.align_components(model,native_inspect=lambda _:reply)
    assert snapshot(store)==before






















def test_alignment_updates_summary_after_consistent_native_membership_change(store,model):
    comp=registered(store,model,[A,B])
    observed=dict(comp,complete=True,objects=[object_row(A,comp['component_id'])],object_ids=[A],
        effective_objects=[object_row(A,comp['component_id'])],effective_object_ids=[A])
    reply=dict(status='success',complete=True,model_path=model,editing={'stable':True},components=[observed],problems=[])
    store.align_components(model,native_inspect=lambda _:reply)
    assert store.get_component(comp['component_id'])['object_count']==1
