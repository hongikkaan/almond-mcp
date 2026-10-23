"""Single-parent Component hierarchy, recursive Scene context and native contracts."""
import sqlite3
import uuid
from contextlib import closing

import pytest

from almond_mcp.retrieval_store import AlmondStore


A, B, C = [str(uuid.UUID(int=value)) for value in (101, 102, 103)]


@pytest.fixture
def store(tmp_path):
    result = AlmondStore(tmp_path / "hierarchy.sqlite3")
    result.scene_a = result.create_scene("Facade")["scene_id"]
    result.scene_b = result.create_scene("Interior")["scene_id"]
    result.model = result._component_model_path(str(tmp_path / "model.3dm"))
    return result


def object_row(guid, component_id, kind="Brep"):
    return dict(rhino_guid=guid, object_type=kind, component_id=component_id,
                bounds_mm=[0, 0, 0, 100, 200, 300])


def simulated_native(store, calls=None):
    """Return complete direct/recursive snapshots as a hierarchy-aware Rhino Bridge would."""
    def emit(request):
        if calls is not None:
            calls.append(request)
        component_id = request["component_id"]
        existing = store.get_component(component_id)
        direct_ids = request["object_ids"]
        child_ids = request.get("child_component_ids", [])
        child_objects = [obj for child_id in child_ids
                         for obj in store.get_component(child_id)["effective_objects"]]
        direct_objects = [object_row(guid, component_id) for guid in direct_ids]
        effective = {obj["rhino_guid"]: obj for obj in child_objects + direct_objects}
        native = dict(
            complete=True, component_id=component_id, model_path=request["expected_model_path"],
            rhino_group_id=request["rhino_group_id"] or str(uuid.uuid5(uuid.NAMESPACE_URL, component_id)),
            name=request["name"], scene_ids=request["scene_ids"],
            child_component_ids=child_ids, parent_component_id=(
                existing["parent_component_id"] if existing else None),
            objects=direct_objects, effective_objects=[effective[guid] for guid in sorted(effective)],
            effective_object_ids=sorted(effective), pending_objects=[], requires_sync=False,
        )
        prior_branch = set(existing["effective_object_ids"]) if existing else set()
        new_branch = set(effective)
        related = []
        with store._connect() as connection:
            ancestors = store._component_ancestor_ids(connection, component_id)
        for ancestor_id in ancestors:
            ancestor = store.get_component(ancestor_id)
            ancestor_objects = {obj["rhino_guid"]: obj for obj in ancestor["effective_objects"]
                                if obj["rhino_guid"] not in prior_branch}
            ancestor_objects.update(effective)
            related.append(dict(
                complete=True, component_id=ancestor_id, model_path=ancestor["model_path"],
                rhino_group_id=ancestor["rhino_group_id"], name=ancestor["name"],
                scene_ids=ancestor["scene_ids"], parent_component_id=ancestor["parent_component_id"],
                child_component_ids=ancestor["child_component_ids"], objects=[
                    {k: obj[k] for k in ("rhino_guid", "object_type", "component_id", "bounds_mm")}
                    for obj in ancestor["objects"]],
                effective_objects=[ancestor_objects[guid] for guid in sorted(ancestor_objects)],
                effective_object_ids=sorted(ancestor_objects),
            ))
        old_children = set(existing["child_component_ids"]) if existing else set()
        for child_id in old_children ^ set(child_ids):
            child = store.get_component(child_id)
            related.append(dict(child, complete=True,
                                parent_component_id=component_id if child_id in child_ids else None))
        return dict(status="success", component=native, affected_components=related)
    return emit


def create(store, name, direct, scenes=None, children=None, **extra):
    return store.upsert_component(
        store.model, name, direct, scene_ids=scenes or [store.scene_a],
        child_component_ids=children, native_apply=simulated_native(store), **extra,
    )


def test_parent_with_no_direct_objects_inherits_child_geometry_and_scene_context(store):
    child = create(store, "Facade panel", [A])
    parent = create(store, "Facade assembly", [], scenes=[store.scene_b],
                    children=[child["component_id"]])
    assert parent["object_ids"] == []
    assert parent["direct_object_ids"] == []
    assert parent["child_component_ids"] == [child["component_id"]]
    assert parent["effective_object_ids"] == [A]
    updated_child = store.get_component(child["component_id"])
    assert updated_child["parent_component_id"] == parent["component_id"]
    assert updated_child["scene_ids"] == [store.scene_a]
    assert store.get_scene(store.scene_b)["objects"] == 1
    assert store.scene_objects(store.scene_b)[0]["component_id"] == child["component_id"]
    assert store.get_scene(store.scene_a)["objects"] == 1
    plan = store.create_generation_plan("Model facade", scope="component",
                                        scene_ids=[store.scene_b], component_ids=[parent["component_id"]])
    targets = store.resolve_generation_targets(plan["plan_id"])
    assert targets["component_ids"] == [parent["component_id"]]
    assert targets["components"][0]["child_component_ids"] == [child["component_id"]]
    assert targets["components"][0]["effective_object_ids"] == [A]
    assert targets["live_verified"] is False


def test_explicit_reparent_requires_detach_and_cycle_is_rejected_before_native(store):
    child = create(store, "Panel", [A])
    parent = create(store, "Parent", [], children=[child["component_id"]])
    calls = []
    with pytest.raises(ValueError, match="cycle"):
        store.upsert_component(store.model, "Loop", [A], component_id=child["component_id"],
                               child_component_ids=[parent["component_id"]],
                               native_apply=lambda request: calls.append(request))
    with pytest.raises(ValueError, match="direct object or"):
        store.upsert_component(store.model, "Orphan", [], scene_ids=[store.scene_a],
                               native_apply=lambda request: calls.append(request))
    with pytest.raises(ValueError, match="direct object or"):
        store.upsert_component(store.model, "Empty parent", [], component_id=parent["component_id"],
                               child_component_ids=[], native_apply=lambda request: calls.append(request))
    # A second owner must detach the child from the first parent explicitly.
    with pytest.raises(ValueError, match="detach"):
        store.upsert_component(store.model, "Second parent", [], scene_ids=[store.scene_a],
                               child_component_ids=[child["component_id"]],
                               native_apply=lambda request: calls.append(request))
    assert calls == []
    assert store.get_component(child["component_id"])["parent_component_id"] == parent["component_id"]


def test_direct_sql_cannot_add_cross_document_parent_or_cycle(store, tmp_path):
    leaf = create(store, "Leaf", [A])
    parent = create(store, "Parent", [], children=[leaf["component_id"]])
    other = store.upsert_component(
        str(tmp_path / "other.3dm"), "Other", [B], [store.scene_a],
        native_apply=lambda request: dict(status="success", component=dict(
            complete=True, component_id=request["component_id"],
            model_path=request["expected_model_path"],
            rhino_group_id=str(uuid.uuid5(uuid.NAMESPACE_URL, request["component_id"])),
            name=request["name"], scene_ids=request["scene_ids"],
            objects=[object_row(B, request["component_id"])],
        )),
    )
    with pytest.raises(sqlite3.IntegrityError), store._connect() as connection:
        connection.execute("UPDATE components SET parent_component_id = ? WHERE component_id = ?",
                           (leaf["component_id"], parent["component_id"]))
    with pytest.raises(sqlite3.IntegrityError), store._connect() as connection:
        connection.execute("UPDATE components SET parent_component_id = ? WHERE component_id = ?",
                           (other["component_id"], parent["component_id"]))
    with store._connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_child_update_propagates_recursive_objects_without_changing_direct_ownership(store):
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [], scenes=[store.scene_b], children=[child["component_id"]])
    old_scene_revision = store.get_scene(store.scene_b)["revision"]
    plan = store.create_generation_plan("Roof", scope="component", component_ids=[parent["component_id"]])
    frozen = store.get_generation_plan(plan["plan_id"], revision=1)
    changed = store.upsert_component(store.model, "Panel revised", [A, C],
                                     component_id=child["component_id"],
                                     native_apply=simulated_native(store))
    assert changed["object_ids"] == [A, C]
    assert store.get_component(parent["component_id"])["effective_object_ids"] == [A, C]
    assert store.get_scene(store.scene_b)["objects"] == 2
    assert store.get_scene(store.scene_b)["revision"] > old_scene_revision
    assert all(obj["component_id"] == child["component_id"] for obj in store.scene_objects(store.scene_b))
    assert store.get_generation_plan(plan["plan_id"], revision=1) == frozen
    assert store.get_generation_plan(plan["plan_id"]) == frozen


def test_child_name_only_update_requires_no_unchanged_ancestor_proof(store):
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [], children=[child["component_id"]])
    def native(request):
        response = simulated_native(store)(request)
        response["affected_components"] = []
        return response
    result = store.upsert_component(store.model, "Renamed panel", [A],
                                    component_id=child["component_id"], native_apply=native)
    assert result["name"] == "Renamed panel"
    assert store.get_component(parent["component_id"])["effective_object_ids"] == [A]


def test_child_recovery_inspects_ancestor_before_committing_live_change(store):
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [], scenes=[store.scene_b], children=[child["component_id"]])
    calls = []
    def inspect(request):
        assert request["action"] == "inspect"
        calls.append(request["component_id"])
        if request["component_id"] == child["component_id"]:
            return simulated_native(store)(dict(request, object_ids=[A, C], child_component_ids=[],
                                                name=child["name"], scene_ids=child["scene_ids"]))
        response = simulated_native(store)(dict(request, object_ids=[],
                                                child_component_ids=[child["component_id"]],
                                                name=parent["name"], scene_ids=parent["scene_ids"]))
        response["component"]["effective_objects"] = [
            object_row(A, child["component_id"]), object_row(C, child["component_id"])]
        response["component"]["effective_object_ids"] = [A, C]
        return response
    updated = store.sync_component(store.model, child["component_id"], native_inspect=inspect)
    assert calls == [child["component_id"], parent["component_id"]]
    assert updated["object_ids"] == [A, C]
    assert store.get_component(parent["component_id"])["effective_object_ids"] == [A, C]
    assert store.get_scene(store.scene_b)["objects"] == 2


def detached_ack(store, request):
    children = store.get_component(request["component_id"])["child_component_ids"]
    affected = []
    for child_id in children:
        row = store.get_component(child_id)
        observed = dict(row, complete=True, parent_component_id=None)
        affected.append(observed)
    return dict(status="success", component_id=request["component_id"],
                model_path=request["expected_model_path"], rhino_group_id=request["rhino_group_id"],
                detached_child_component_ids=children, affected_components=affected)


def test_root_parent_unregister_detaches_children_but_child_cannot_unregister_until_detached(store):
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [], scenes=[store.scene_b], children=[child["component_id"]])
    plan = store.create_generation_plan("Protect child", scope="component",
                                        component_ids=[child["component_id"]])
    immutable = store.get_generation_plan(plan["plan_id"], 1)
    calls = []
    with pytest.raises(ValueError, match="Detach"):
        store.unregister_component(child["component_id"],
                                   native_apply=lambda request: calls.append(request))
    assert calls == []
    def native(request):
        calls.append(request)
        return detached_ack(store, request)
    removed = store.unregister_component(parent["component_id"], native_apply=native)
    assert removed["status"] == "unregistered" and len(calls) == 1
    assert calls[0]["expected_effective_object_ids"] == [A]
    assert calls[0]["expected_child_component_ids"] == [child["component_id"]]
    assert store.get_component(parent["component_id"]) is None
    still_owned = store.get_component(child["component_id"])
    assert still_owned["parent_component_id"] is None
    assert still_owned["object_ids"] == [A]
    assert still_owned["scene_ids"] == [store.scene_a]
    assert store.get_scene(store.scene_b)["objects"] == 0
    assert store.get_scene(store.scene_a)["objects"] == 1
    assert store.get_generation_plan(plan["plan_id"], 1) == immutable


def test_unregistered_parent_inspection_recovers_lost_ack_without_native_retry(store):
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [], children=[child["component_id"]])
    calls = []
    def lose_response(request):
        calls.append(request["action"])
        raise TimeoutError("Native group unlink reply lost")
    with pytest.raises(Exception, match="reply lost"):
        store.unregister_component(parent["component_id"], native_apply=lose_response)
    assert calls == ["unregister"]
    assert store.get_component(child["component_id"])["parent_component_id"] == parent["component_id"]
    def inspect(request):
        calls.append(request["action"])
        assert request["action"] == "inspect"
        assert request["expected_object_ids"] == []
        assert request["expected_effective_object_ids"] == [A]
        response = detached_ack(store, request)
        proof = dict(complete=True, registration_status="unregistered",
                     component_id=parent["component_id"], model_path=store.model,
                     rhino_group_id=parent["rhino_group_id"], scene_ids=[], objects=[],
                     effective_object_ids=[A],
                     detached_child_component_ids=[child["component_id"]])
        return dict(status="success", component=proof,
                    affected_components=response["affected_components"])
    recovered = store.sync_component(store.model, parent["component_id"], native_inspect=inspect)
    assert calls == ["unregister", "inspect"]
    assert recovered["status"] == "unregistered"
    assert store.get_component(parent["component_id"]) is None
    assert store.get_component(child["component_id"])["parent_component_id"] is None
    assert store.get_component(child["component_id"])["object_ids"] == [A]


def test_group_added_textdot_is_visible_before_sync_and_adopted_once(store):
    child = create(store, "Notes", [A])
    id_ = child["component_id"]
    calls = []
    def native(request):
        calls.append(request["action"])
        original = simulated_native(store)(dict(
            request, name=child["name"], scene_ids=child["scene_ids"],
            object_ids=[A], child_component_ids=[],
        ))
        if request["action"] == "inspect":
            original["component"].update(
                pending_objects=[object_row(B, None, "TextDot")], requires_sync=True,
            )
        elif request["action"] == "sync":
            original["component"].update(
                objects=[object_row(A, id_), object_row(B, id_, "TextDot")],
                effective_objects=[object_row(A, id_), object_row(B, id_, "TextDot")],
                effective_object_ids=[A, B], pending_objects=[], requires_sync=False,
            )
        return original
    live = store.get_component(id_, live=True, native_inspect=native)
    assert live["requires_sync"] is True and live["pending_objects"][0]["object_type"] == "TextDot"
    assert store.get_component(id_)["object_ids"] == [A]
    assert calls == ["inspect"]
    synced = store.sync_component(store.model, id_, native_inspect=native)
    assert calls == ["inspect", "inspect", "sync"]
    assert synced["object_ids"] == [A, B]
    assert [row["object_type"] for row in store.scene_objects(store.scene_a)] == ["Brep", "TextDot"]


def test_existing_unchanged_sync_does_not_create_spurious_scene_revisions(store):
    child = create(store, "Panel", [A])
    before = store.get_scene(store.scene_a)["revision"]
    calls = []
    def native(request):
        calls.append(request["action"])
        return simulated_native(store)(dict(request, name=child["name"],
            object_ids=[A], scene_ids=child["scene_ids"], child_component_ids=[]))
    observed = store.sync_component(store.model, child["component_id"], native_inspect=native)
    assert observed["live_verified"] is True
    assert store.get_scene(store.scene_a)["revision"] == before
    assert calls == ["inspect"]


def test_legacy_flat_component_migration_defaults_to_root_without_changing_owner(store):
    child = create(store, "Original", [A])
    with store._connect() as connection:
        connection.execute("UPDATE components SET parent_component_id = NULL WHERE component_id = ?",
                           (child["component_id"],))
    reopened = AlmondStore(store.database_path)
    cached = reopened.get_component(child["component_id"])
    assert cached["parent_component_id"] is None
    assert cached["child_component_ids"] == []
    assert cached["object_ids"] == cached["effective_object_ids"] == [A]


def test_old_component_table_adds_parent_column_without_rewriting_rows(tmp_path):
    database = tmp_path / "legacy-before-parent.sqlite3"
    old_model = str(tmp_path / "legacy.3dm")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("""
            CREATE TABLE components(
                component_id TEXT PRIMARY KEY, model_path TEXT NOT NULL,
                rhino_group_id TEXT NOT NULL, name TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(component_id, model_path), UNIQUE(model_path, rhino_group_id)
            )
        """)
        connection.execute("INSERT INTO components VALUES (?, ?, ?, ?, ?, ?)",
                           ("legacy", old_model, str(uuid.UUID(int=90)), "Existing group", "old", "old"))
        connection.commit()
    store = AlmondStore(database)
    with store._connect() as connection:
        columns = [row["name"] for row in connection.execute("PRAGMA table_info(components)")]
        row = connection.execute("SELECT * FROM components WHERE component_id = 'legacy'").fetchone()
        assert "parent_component_id" in columns
        assert row["parent_component_id"] is None
        assert row["name"] == "Existing group" and row["created_at"] == "old"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
