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
                for table in ("scenes", "scene_revisions", "components", "document_objects",
                              "scene_components", "scene_objects", "rooms", "instances", "instance_rtree")}


def test_shared_component_and_direct_membership_form_a_set(store, model):
    first = store.create_scene("Facade")["scene_id"]
    second = store.create_scene("Structure")["scene_id"]
    comp = registered(store, model, scenes=[first, second])
    store.register_scene_objects(first, model, [A, C], native_observe=lambda request: observe(
        request, {A: comp["component_id"]},
    ))
    assert store.get_scene(first)["objects"] == 3
    assert store.get_scene(first)["direct_objects"] == 2
    assert store.get_scene(second)["objects"] == 2
    assert store.get_scene(second)["components"] == 1
    assert {row["rhino_guid"] for row in store.scene_objects(first)} == {A, B, C}
    assert all(row["live_verified"] is False for row in store.scene_objects(first))
    assert comp["live_verified"] is True
    assert store.get_component(comp["component_id"])["live_verified"] is False
    report = store.validate_scene(first)
    assert report["passed_scope"] == "legacy_asset_instances"
    assert report["coverage"]["registered_objects"] == 3
    assert report["coverage"]["registered_object_collisions_checked"] is False


def test_owner_conflict_is_rejected_before_native_and_preserves_all_rows(store, model):
    registered(store, model, [A])
    before = snapshot(store)
    calls = []
    with pytest.raises(ValueError, match="already belongs"):
        store.upsert_component(model, "Other", [A], [store.fixture_scene_id],
                               native_apply=lambda request: calls.append(request))
    assert calls == []
    assert snapshot(store) == before


def test_copied_guids_in_different_documents_are_distinct_and_fk_prevents_cross_document_owner(store, model, tmp_path):
    other_model = str(tmp_path / "copy.3dm")
    one = registered(store, model, [A], rhino_group_id=GROUP)
    two = registered(store, other_model, [A], rhino_group_id=GROUP)
    assert one["component_id"] != two["component_id"]
    assert len(store.list_components()) == 2
    assert len(store.list_components(model)) == 1
    before = snapshot(store)
    with pytest.raises(sqlite3.IntegrityError):
        with store._connect() as connection:
            connection.execute("UPDATE document_objects SET component_id = ? WHERE component_id = ?",
                               (two["component_id"], one["component_id"]))
    assert snapshot(store) == before


def test_windows_path_spelling_does_not_create_a_second_owner(store):
    registered(store, r"C:\Models\Shared.3dm", [A])
    calls = []
    with pytest.raises(ValueError, match="already belongs"):
        store.upsert_component("c:/models/shared.3dm", "Duplicate", [A], [store.fixture_scene_id],
                               native_apply=lambda request: calls.append(request))
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
            assert peer.execute("SELECT COUNT(*) FROM components").fetchone()[0] == 0
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                peer.execute("INSERT INTO scenes VALUES ('peer','peer','mm',0,'now','now')")
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


def test_timeout_can_be_reconciled_by_inspection_without_replaying_mutation(store, model):
    applied = {}
    calls = []
    def loses_response(request):
        calls.append(request)
        applied.update(native_component(request))
        raise TimeoutError("Native result was lost")
    with pytest.raises(ComponentReconciliationError) as failure:
        store.upsert_component(model, "Applied in Rhino", [A], [store.fixture_scene_id],
                               native_apply=loses_response)
    component_id = failure.value.component_id
    assert store.get_component(component_id) is None
    def inspect(request):
        calls.append(request)
        assert request["action"] == "inspect"
        return copy.deepcopy(applied)
    recovered = store.sync_component(model, component_id, native_inspect=inspect)
    assert recovered["object_ids"] == [A]
    assert [call["action"] for call in calls] == ["upsert", "inspect"]


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


def test_explicit_sync_refuses_native_overlap_and_preserves_previous_registration(store, model):
    one = registered(store, model, [A])
    two = registered(store, model, [B])
    before = snapshot(store)
    conflicting = dict(status="success", component=dict(
        complete=True, component_id=two["component_id"], model_path=model,
        rhino_group_id=two["rhino_group_id"], name="Changed", scene_ids=two["scene_ids"],
        objects=[object_row(A, two["component_id"])],
    ))
    with pytest.raises(ValueError, match="already belongs"):
        store.sync_component(model, two["component_id"], native_inspect=lambda request: conflicting)
    assert snapshot(store) == before
    assert store.get_component(one["component_id"])["object_ids"] == [A]


def test_direct_scene_membership_is_document_scoped_and_native_read_only(store, model, tmp_path):
    scene = store.create_scene("Multi-document")["scene_id"]
    other_model = str(tmp_path / "other.3dm")
    requests = []
    def read(request):
        requests.append(request)
        assert request["action"] == "objects"
        assert "scene_ids_by_object" not in request
        return observe(request)
    store.register_scene_objects(scene, model, [A, B], native_observe=read)
    store.register_scene_objects(scene, other_model, [A], native_observe=read)
    store.register_scene_objects(scene, model, [C], mode="replace", native_observe=read)
    rows = store.scene_objects(scene)
    assert len(rows) == 2
    assert {row["rhino_guid"] for row in rows} == {A, C}
    assert requests[-1]["object_ids"] == [A, B, C]
    store.register_scene_objects(scene, model, [C], mode="remove", native_observe=read)
    assert len(store.scene_objects(scene)) == 1
    assert store.get_scene(scene)["direct_objects"] == 1


def test_incomplete_direct_observation_rolls_back_membership(store, model):
    scene = store.create_scene("Raw")["scene_id"]
    before = snapshot(store)
    with pytest.raises(ValueError, match="complete"):
        store.register_scene_objects(scene, model, [A], native_observe=lambda request: dict(
            status="success", complete=False, model_path=model, objects=[object_row(A)],
        ))
    assert snapshot(store) == before


def test_unregister_releases_owner_but_retains_direct_scene_object(store, model):
    scene = store.create_scene("Direct survives")["scene_id"]
    comp = registered(store, model, [A], [scene])
    store.register_scene_objects(scene, model, [A],
                                 native_observe=lambda request: observe(request, {A: comp["component_id"]}))
    def unregister(request):
        assert request["action"] == "unregister"
        return dict(status="success", component_id=request["component_id"],
                    model_path=request["expected_model_path"], rhino_group_id=request["rhino_group_id"])
    removed = store.unregister_component(comp["component_id"], native_apply=unregister)
    assert removed["status"] == "unregistered"
    assert store.get_component(comp["component_id"]) is None
    rows = store.scene_objects(scene)
    assert len(rows) == 1 and rows[0]["rhino_guid"] == A and rows[0]["component_id"] is None
    registered(store, model, [A])


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
    plan = store.create_generation_plan(
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


def test_existing_registration_passes_previous_members_to_native_preflight(store, model):
    comp = registered(store, model, [A, B])
    requests = []
    def native(request):
        requests.append(request)
        return native_component(request)
    store.upsert_component(model, "Changed", [B], component_id=comp["component_id"], native_apply=native)
    assert requests[0]["expected_object_ids"] == [A, B]


@pytest.mark.parametrize("scene_ids", [None, []])
def test_new_component_requires_a_scene_before_calling_native(store, model, scene_ids):
    before = snapshot(store)
    calls = []
    with pytest.raises(ValueError, match="at least one scene"):
        store.upsert_component(model, "Orphan", [A], scene_ids=scene_ids,
                               native_apply=lambda request: calls.append(request))
    assert calls == []
    assert snapshot(store) == before


def test_explicit_sync_cannot_leave_component_without_scene(store, model):
    comp = registered(store, model, [A])
    before = snapshot(store)
    observed = dict(comp, complete=True, scene_ids=[])
    with pytest.raises(ValueError, match="at least one scene"):
        store.sync_component(model, comp["component_id"],
                             native_inspect=lambda request: dict(status="success", component=observed))
    assert snapshot(store) == before


def test_additive_component_schema_preserves_legacy_rooms_instances_and_revisions(store):
    scene = store.create_scene("Legacy")["scene_id"]
    room = store.upsert_room(scene, "L1", [0, 0, 18000, 1000, 1000, 21000])
    store.sync_assets([dict(asset_id="fixture-cube", dimensions_mm=dict(width=100, depth=100, height=100))],
                      library_id="fixture")
    instance = store.upsert_instance(scene, "fixture-cube", 500, 500, room_id=room["room_id"])
    tables = ("scenes", "rooms", "instances", "scene_revisions", "instance_rtree", "assets")
    with sqlite3.connect(store.database_path) as connection:
        before = {table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() for table in tables}
        for table in ("scene_objects", "scene_components", "document_objects", "components"):
            connection.execute(f"DROP TABLE {table}")
    migrated = AlmondStore(store.database_path)
    with sqlite3.connect(store.database_path) as connection:
        after = {table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() for table in tables}
    assert after == before
    assert migrated.list_components() == []
    assert migrated.scene_instances(scene)[0]["instance_id"] == instance["instance_id"]
    assert migrated.validate_scene(scene)["passed"] is True


def test_direct_store_legacy_ids_cannot_cross_scenes_and_instance_delete_cleans_rtree(store):
    first = store.create_scene("First")["scene_id"]
    second = store.create_scene("Second")["scene_id"]
    room = store.upsert_room(first, "Owned", [0, 0, 0, 1000, 1000, 1000])
    store.sync_assets([dict(asset_id="cube", dimensions_mm=dict(width=100, depth=100, height=100))],
                      library_id="fixture")
    instance = store.upsert_instance(first, "cube", 500, 500, room_id=room["room_id"])
    before = snapshot(store)
    with pytest.raises(ValueError, match="another scene"):
        store.upsert_room(second, "Wrong", [0, 0, 0, 100, 100, 100], room_id=room["room_id"])
    with pytest.raises(ValueError, match="another scene"):
        store.upsert_instance(second, "cube", 0, 0, instance_id=instance["instance_id"])
    assert snapshot(store) == before
    store.remove_instance(first, instance["instance_id"])
    with store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM instance_rtree").fetchone()[0] == 0


def unregistered_proof(component):
    return dict(status="success", component=dict(
        complete=True, registration_status="unregistered", component_id=component["component_id"],
        model_path=component["model_path"], rhino_group_id=component["rhino_group_id"], scene_ids=[],
        objects=[object_row(guid) for guid in component["object_ids"]],
    ))


def test_sync_recovers_lost_unregister_with_read_only_proof(store, model):
    comp = registered(store, model, [A, B])
    scene = comp["scene_ids"][0]
    store.register_scene_objects(scene, model, [A],
        native_observe=lambda request: observe(request, {A: comp["component_id"]}))
    before = snapshot(store)
    calls = []
    def lost_reply(request):
        calls.append(request["action"])
        raise TimeoutError("Unregistration succeeded but its reply was lost")
    with pytest.raises(ComponentReconciliationError):
        store.unregister_component(comp["component_id"], native_apply=lost_reply)
    assert snapshot(store) == before and calls == ["unregister"]
    def inspect(request):
        calls.append(request["action"])
        assert request["expected_object_ids"] == [A, B]
        return unregistered_proof(comp)
    recovered = store.sync_component(model, comp["component_id"], native_inspect=inspect)
    assert recovered["status"] == "unregistered" and recovered["live_verified"] is True
    assert calls == ["unregister", "inspect"]
    assert store.get_component(comp["component_id"]) is None
    rows = store.scene_objects(scene)
    assert len(rows) == 1 and rows[0]["rhino_guid"] == A and rows[0]["component_id"] is None


@pytest.mark.parametrize("reference_kind", ["plan", "step"])
def test_unregistered_sync_proof_cannot_release_referenced_component(store, model, reference_kind):
    comp = registered(store, model, [A])
    plan = store.create_generation_plan("Retain", scope="component",
        component_ids=[comp["component_id"]] if reference_kind == "plan" else [])
    if reference_kind == "step":
        store.update_plan_step(plan["plan_id"], "inspect_context", "pending", component_ids=[comp["component_id"]])
    before = snapshot(store)
    with pytest.raises(ValueError, match="referenced"):
        store.sync_component(model, comp["component_id"], native_inspect=lambda request: unregistered_proof(comp))
    assert snapshot(store) == before


@pytest.mark.parametrize("failure", ["incomplete", "members", "owned", "missing_owner", "scenes", "group", "identity"])
def test_unregistered_sync_requires_exact_complete_unowned_snapshot(store, model, failure):
    comp = registered(store, model, [A, B])
    proof = unregistered_proof(comp)
    observed = proof["component"]
    if failure == "incomplete":
        observed["complete"] = False
    elif failure == "members":
        observed["objects"].pop()
    elif failure == "owned":
        observed["objects"][0]["component_id"] = comp["component_id"]
    elif failure == "missing_owner":
        observed["objects"][0].pop("component_id")
    elif failure == "scenes":
        observed["scene_ids"] = comp["scene_ids"]
    elif failure == "group":
        observed["rhino_group_id"] = str(uuid.uuid4())
    else:
        observed["component_id"] = "other"
    before = snapshot(store)
    with pytest.raises(ValueError):
        store.sync_component(model, comp["component_id"], native_inspect=lambda request: proof)
    assert snapshot(store) == before


def test_unregistered_sync_requires_an_existing_registration(store, model):
    proof = dict(status="success", component=dict(complete=True, registration_status="unregistered"))
    with pytest.raises(ValueError, match="existing"):
        store.sync_component(model, "missing", native_inspect=lambda request: proof)


def test_registered_sync_can_accept_changed_consistent_membership(store, model):
    comp = registered(store, model, [A, B])
    def inspect(request):
        assert request["expected_object_ids"] == [A, B]
        return dict(status="success", component=dict(comp, complete=True,
            objects=[object_row(A, comp["component_id"])], object_ids=[A],
            direct_object_ids=[A], effective_objects=[object_row(A, comp["component_id"])],
            effective_object_ids=[A]))
    result = store.sync_component(model, comp["component_id"], native_inspect=inspect)
    assert result["object_ids"] == [A]
