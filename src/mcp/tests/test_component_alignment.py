"""BDD at the Component store boundary; the Bridge is an external document source."""
import copy
import uuid

import pytest

from test_components import A, B, C, GROUP, model, object_row, registered, store


def live(component, ids, *, availability="present", name="Edited group"):
    return dict(
        complete=True, component_id=component["component_id"], model_path=component["model_path"],
        rhino_group_id=component["rhino_group_id"], name=name, scene_ids=component["scene_ids"],
        child_component_ids=component["child_component_ids"],
        parent_component_id=component["parent_component_id"], availability=availability,
        objects=[object_row(guid, component["component_id"]) for guid in ids],
        effective_objects=[object_row(guid, component["component_id"]) for guid in ids],
        effective_object_ids=ids, pending_objects=[], requires_sync=False,
    )


def bridge(snapshots, problems=(), *, stable=True):
    def observe(request):
        assert request["action"] == "inspect_many", "Alignment must never ask Rhino to mutate."
        return dict(status="success", complete=True, model_path=request["expected_model_path"],
                    editing=dict(mode="model" if stable else "group", stable=stable),
                    components=copy.deepcopy(snapshots), problems=list(problems))
    return observe


def test_given_manual_group_edits_when_aligned_once_then_ledger_uses_live_members(store, model):
    component = registered(store, model, [A, B], rhino_group_id=GROUP)
    result = store.align_components(model, native_inspect=bridge([live(component, [B, C])]))
    actual = store.get_component(component["component_id"])
    assert result["changed"] == 1 and result["problems"] == []
    assert actual["name"] == "Edited group" and actual["object_ids"] == [B, C]
    revision = store.get_scene(component["scene_ids"][0])["revision"]
    unchanged = store.align_components(model, native_inspect=bridge([live(component, [B, C])]))
    assert unchanged["changed"] == 0
    assert store.get_scene(component["scene_ids"][0])["revision"] == revision


def test_given_missing_group_when_aligning_then_binding_and_other_scene_links_survive(store, model):
    missing = registered(store, model, [A], rhino_group_id=GROUP)
    other = registered(store, model, [B], rhino_group_id=str(uuid.UUID(int=101)))
    store.register_scene_objects(store.fixture_scene_id, model, [B], native_observe=lambda request: dict(
        status="success", complete=True, model_path=request["expected_model_path"], objects=[object_row(B, other["component_id"])]))
    before = store.get_component(other["component_id"])
    store.align_components(model, native_inspect=bridge([
        live(missing, [], availability="missing_group"), live(other, [B], name=before["name"])]))
    unavailable = store.get_component(missing["component_id"])
    assert unavailable["availability"] == "missing_group" and unavailable["object_ids"] == []
    assert store.get_component(other["component_id"])["object_ids"] == [B]
    assert any(row["rhino_guid"] == B and row["direct"] for row in store.scene_objects(store.fixture_scene_id))
    store.align_components(model, native_inspect=bridge([live(missing, [A]), live(other, [B], name=before["name"])]))
    assert store.get_component(missing["component_id"])["availability"] == "present"


def test_given_group_editor_when_aligning_then_existing_records_are_untouched(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    with pytest.raises(ValueError, match="editing"):
        store.align_components(model, native_inspect=bridge([live(component, [])], stable=False))
    assert store.get_component(component["component_id"])["object_ids"] == [A]


def test_given_one_invalid_registration_when_aligning_then_valid_registration_is_observable(store, model):
    invalid = registered(store, model, [A], rhino_group_id=GROUP)
    valid = registered(store, model, [B], rhino_group_id=str(uuid.UUID(int=101)))
    result = store.align_components(model, native_inspect=bridge([live(valid, [B, C])], [
        dict(component_id=invalid["component_id"], code="invalid_binding")]))
    assert len(result["problems"]) == 1
    assert store.get_component(valid["component_id"])["object_ids"] == [B, C]
    assert store.get_component(invalid["component_id"])["object_ids"] == [A]


def test_given_incomplete_observation_when_aligning_then_ledger_is_not_erased(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    with pytest.raises(ValueError, match="omitted"):
        store.align_components(model, native_inspect=bridge([]))
    assert store.get_component(component["component_id"])["object_ids"] == [A]


def test_given_agent_needs_one_scene_when_listing_then_scope_is_not_document_wide(store, model):
    first = registered(store, model, [A], rhino_group_id=GROUP)
    scene = store.create_scene("Other context")["scene_id"]
    registered(store, model, [B], scenes=[scene], rhino_group_id=str(uuid.UUID(int=101)))
    rows = store.list_components(scene_id=first["scene_ids"][0])
    assert [row["component_id"] for row in rows] == [first["component_id"]]


def test_given_parent_and_child_when_referenced_then_only_requested_ancestor_is_stored(store, model):
    from test_component_hierarchy import create
    store.scene_a, store.scene_b, store.model = store.fixture_scene_id, store.create_scene("Parent context")["scene_id"], model
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [B], scenes=[store.scene_a, store.scene_b], children=[child["component_id"]])
    plan = store.create_plan("Work on assembly", scope="component", component_ids=[child["component_id"], parent["component_id"]])
    assert plan["component_ids"] == [parent["component_id"]]
    step = store.update_plan_step(plan["plan_id"], "inspect_context", "running",
                                  component_ids=[parent["component_id"], child["component_id"]])
    assert step["steps"][0]["component_ids"] == [parent["component_id"]]
    assert store.get_scene(store.scene_a)["components"] == 1
    assert store.get_component(child["component_id"])["scene_ids"] == [store.scene_a]
    assert store.get_scene(store.scene_b)["components"] == 1


@pytest.mark.parametrize("gap_at", ["parent", "middle"])
@pytest.mark.parametrize("availability", ["missing_group", "unregistered"])
def test_given_unavailable_ancestor_when_aligning_then_present_child_keeps_its_scene_route(store, model, gap_at, availability):
    from test_component_hierarchy import create
    store.scene_a, store.model = store.fixture_scene_id, model
    child = create(store, "Panel", [A])
    middle = create(store, "Frame", [B], children=[child["component_id"]])
    parent = create(store, "Assembly", [C], children=[middle["component_id"]]) if gap_at == "middle" else middle
    missing = middle if gap_at == "middle" else parent
    assert store.get_scene(store.scene_a)["objects"] == (3 if gap_at == "middle" else 2)

    snapshots = []
    for component in (child, middle, parent) if gap_at == "middle" else (child, parent):
        component = store.get_component(component["component_id"])
        ids = [] if component["component_id"] == missing["component_id"] else component["object_ids"]
        snapshots.append(live(component, ids, availability=(
            availability if component["component_id"] == missing["component_id"] else "present")))
        if gap_at == "middle" and component["component_id"] == parent["component_id"]:
            snapshots[-1]["effective_objects"] = [object_row(A, child["component_id"]), object_row(C, parent["component_id"])]
            snapshots[-1]["effective_object_ids"] = [A, C]
    store.align_components(model, native_inspect=bridge(snapshots))

    expected_ids = {A, C} if gap_at == "middle" else {A}
    assert {row["rhino_guid"] for row in store.scene_objects(store.scene_a)} == expected_ids
    assert store.get_scene(store.scene_a)["objects"] == len(expected_ids)
    assert store.get_component(child["component_id"])["scene_ids"] == [store.scene_a]


def test_given_missing_middle_group_when_aligning_then_root_and_scene_keep_live_descendant_geometry(store, model):
    from test_component_hierarchy import create
    store.scene_a, store.scene_b, store.model = store.fixture_scene_id, store.create_scene("Assembly context")["scene_id"], model
    child = create(store, "Panel", [A])
    middle = create(store, "Frame", [B], scenes=[store.scene_b], children=[child["component_id"]])
    parent = create(store, "Assembly", [C], scenes=[store.scene_b], children=[middle["component_id"]])
    child = store.get_component(child["component_id"])
    middle = store.get_component(middle["component_id"])
    root = live(parent, [B, C], name="Assembly")
    root["effective_objects"] = [object_row(A, child["component_id"]), object_row(B, parent["component_id"]), object_row(C, parent["component_id"])]
    root["effective_object_ids"] = [A, B, C]
    store.align_components(model, native_inspect=bridge([
        root, live(middle, [], availability="missing_group"), live(child, [A], name="Panel")]))
    assert store.get_component(parent["component_id"])["effective_object_ids"] == [A, B, C]
    assert store.get_component(middle["component_id"])["effective_object_ids"] == []
    assert {row["rhino_guid"] for row in store.scene_objects(store.scene_b)} == {A, B, C}
    assert store.get_scene(store.scene_b)["objects"] == 3
    assert store.get_component(child["component_id"])["scene_ids"] == [store.scene_a]


def test_given_scene_parent_when_aligning_then_descendant_geometry_updates_without_context_inheritance(store, model):
    from test_component_hierarchy import create
    store.scene_a, store.scene_b, store.model = store.fixture_scene_id, store.create_scene("Assembly context")["scene_id"], model
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [B], scenes=[store.scene_b], children=[child["component_id"]])
    parent_snapshot = live(parent, [B], name="Assembly")
    parent_snapshot["effective_objects"] = [object_row(B, parent["component_id"]), object_row(C, child["component_id"])]
    parent_snapshot["effective_object_ids"] = [B, C]
    child_snapshot = live(store.get_component(child["component_id"]), [C], name="Panel")
    snapshots = [parent_snapshot, child_snapshot]
    def observed_scope(request):
        selected = [item for item in snapshots if item["component_id"] in request["component_ids"]]
        return bridge(selected)(request)
    store.align_components(model, scene_id=store.scene_b, native_inspect=observed_scope)
    assert store.get_component(child["component_id"])["object_ids"] == [C]
    assert store.get_component(child["component_id"])["scene_ids"] == [store.scene_a]
    assert {item["rhino_guid"] for item in store.scene_objects(store.scene_b)} == {B, C}


def test_given_semantic_undo_when_aligning_then_references_and_history_survive(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    plan = store.create_plan("Keep meaning reference", scope="component", component_ids=[component["component_id"]])
    store.align_components(model, native_inspect=bridge([live(component, [], availability="unregistered")]))
    assert store.get_component(component["component_id"])["availability"] == "unregistered"
    assert store.get_scene(store.fixture_scene_id)["components"] == 0
    assert store.get_plan(plan["plan_id"])["component_ids"] == [component["component_id"]]
    store.align_components(model, native_inspect=bridge([live(component, [A])]))
    assert store.get_component(component["component_id"])["availability"] == "present"
    assert store.get_plan(plan["plan_id"])["component_ids"] == [component["component_id"]]


def test_given_explicit_unregister_when_aligning_tombstone_then_registration_is_not_recreated(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    store.unregister_component(component["component_id"], native_apply=lambda request: dict(
        status="success", component_id=component["component_id"], model_path=component["model_path"], rhino_group_id=GROUP))
    store.align_components(model, native_inspect=bridge([live(component, [], availability="unregistered")]))
    assert store.get_component(component["component_id"]) is None


def test_given_deleted_member_with_direct_scene_link_when_aligned_then_only_proven_missing_guid_is_removed(store, model):
    component = registered(store, model, [A, B], rhino_group_id=GROUP)
    store.register_scene_objects(store.fixture_scene_id, model, [A, B], native_observe=lambda request: dict(
        status="success", complete=True, model_path=request["expected_model_path"],
        objects=[object_row(A, component["component_id"]), object_row(B, component["component_id"])]))
    def observed(request):
        result = bridge([live(component, [B])])(request)
        result["presence_complete"] = True
        result["absent_object_ids"] = [A]
        return result
    store.align_components(model, native_inspect=observed)
    rows = store.scene_objects(store.fixture_scene_id)
    assert [row["rhino_guid"] for row in rows] == [B] and rows[0]["direct"] is True


def test_given_live_detached_member_when_aligned_then_direct_scene_link_and_geometry_survive(store, model):
    component = registered(store, model, [A, B], rhino_group_id=GROUP)
    store.register_scene_objects(store.fixture_scene_id, model, [A], native_observe=lambda request: dict(
        status="success", complete=True, model_path=request["expected_model_path"],
        objects=[object_row(A, component["component_id"])]))
    moved = object_row(A, None)
    moved["name"] = "User moved item"
    moved["bounds_mm"] = [20, 20, 20, 30, 30, 30]
    def observed(request):
        assert A in request["prior_object_ids"]
        result = bridge([live(component, [B])])(request)
        result.update(presence_complete=True, absent_object_ids=[], detached_objects=[moved])
        return result
    result = store.align_components(model, native_inspect=observed)
    row = next(item for item in store.scene_objects(store.fixture_scene_id) if item["rhino_guid"] == A)
    assert row["direct"] and row["name"] == moved["name"] and row["component_id"] is None
    assert result["removed_objects"] == 0 and result["refreshed_objects"] == 1


@pytest.mark.parametrize("proof", [dict(absent_object_ids=[C]), dict(absent_object_ids=[A], presence_complete=False),
                                    dict(absent_object_ids=[B], presence_complete=True)])
def test_given_incomplete_or_contradictory_presence_when_aligned_then_cache_is_untouched(store, model, proof):
    component = registered(store, model, [A, B], rhino_group_id=GROUP)
    def observed(request):
        result = bridge([live(component, [B])])(request)
        result.update(proof)
        return result
    with pytest.raises(ValueError, match="presence"):
        store.align_components(model, native_inspect=observed)
    assert store.get_component(component["component_id"])["object_ids"] == [A, B]


def test_given_archived_handle_from_another_model_when_aligned_then_existing_binding_is_untouched(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    store.align_components(model, native_inspect=bridge([live(component, [], availability="missing_group")]))
    component = store.get_component(component["component_id"])
    snapshot = live(component, [], availability="missing_group")
    second_model = model + ".copy.3dm"
    snapshot["model_path"] = second_model
    with pytest.raises(ValueError, match="another model"):
        store.align_components(second_model, native_inspect=bridge([snapshot]))
    assert store.get_component(component["component_id"]) == component


def test_given_inactive_cached_binding_when_registered_again_then_status_and_scene_are_present(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    store.align_components(model, native_inspect=bridge([live(component, [], availability="unregistered")]))
    restored = registered(store, model, [A], component_id=component["component_id"], rhino_group_id=GROUP)
    assert restored["availability"] == "present" and restored["object_ids"] == [A]
    assert store.get_scene(store.fixture_scene_id)["components"] == 1


def test_given_native_only_scene_registration_when_aligning_scene_then_it_is_discovered(store, model):
    component = registered(store, model, [A], rhino_group_id=GROUP)
    native_only = dict(component, component_id="native-only", rhino_group_id=str(uuid.UUID(int=101)))
    def observed(request):
        assert request["discover_scene"] is True
        return bridge([live(component, [A]), live(native_only, [B])])(request)
    result = store.align_components(model, scene_id=store.fixture_scene_id, native_inspect=observed)
    assert result["checked"] == 2 and store.get_component("native-only")["object_ids"] == [B]


def test_given_scene_root_when_listing_recursively_then_children_keep_their_own_context(store, model):
    from test_component_hierarchy import create
    store.scene_a, store.scene_b, store.model = store.fixture_scene_id, store.create_scene("Assembly context")["scene_id"], model
    child = create(store, "Panel", [A])
    parent = create(store, "Assembly", [B], scenes=[store.scene_a, store.scene_b], children=[child["component_id"]])
    assert {row["component_id"] for row in store.list_components(scene_id=store.scene_a, recursive=True)} == {parent["component_id"], child["component_id"]}
    rows = store.list_components(scene_id=store.scene_b, recursive=True)
    assert {row["component_id"] for row in rows} == {parent["component_id"], child["component_id"]}
    assert next(row for row in rows if row["component_id"] == child["component_id"])["scene_ids"] == [store.scene_a]


def test_given_child_bounds_change_when_aligning_child_then_parent_scene_revision_advances(store, model):
    from test_component_hierarchy import create
    store.scene_a, store.scene_b, store.model = store.fixture_scene_id, store.create_scene("Assembly context")["scene_id"], model
    child = create(store, "Panel", [A])
    create(store, "Assembly", [B], scenes=[store.scene_b], children=[child["component_id"]])
    before = store.get_scene(store.scene_b)["revision"]
    snapshot = live(store.get_component(child["component_id"]), [A], name="Panel")
    snapshot["objects"][0]["bounds_mm"] = snapshot["effective_objects"][0]["bounds_mm"] = [1, 2, 3, 10, 20, 30]
    result = store.align_components(model, component_ids=[child["component_id"]], native_inspect=bridge([snapshot]))
    assert result["scene_revisions"][store.scene_b] > before


def test_given_native_only_parent_scope_when_recovering_then_its_descendant_and_original_scenes_are_imported(store, model):
    scene_b=store.create_scene("Assembly context")["scene_id"]
    child=dict(component_id="native-child",model_path=model,rhino_group_id=GROUP,scene_ids=[store.fixture_scene_id],
               child_component_ids=[],parent_component_id="native-parent")
    parent=dict(component_id="native-parent",model_path=model,rhino_group_id=str(uuid.UUID(int=101)),scene_ids=[scene_b],
                child_component_ids=["native-child"],parent_component_id=None)
    root=live(parent,[B]);root["effective_objects"]=[object_row(A,"native-child"),object_row(B,"native-parent")]
    root["effective_object_ids"]=[A,B]
    store.align_components(model,component_ids=["native-parent"],native_inspect=bridge([root,live(child,[A])]))
    assert store.get_component("native-child")["scene_ids"] == [store.fixture_scene_id]
    assert store.get_component("native-child")["parent_component_id"] == "native-parent"


@pytest.mark.parametrize("cached_parent",[True,False])
def test_given_new_native_child_with_old_cached_members_when_aligning_parent_then_missing_presence_scope_is_explicit(store, model,cached_parent):
    from test_components import snapshot
    child=registered(store,model,[A],rhino_group_id=GROUP)
    parent_scene=store.create_scene("Parent context")["scene_id"]
    parent=registered(store,model,[B],scenes=[parent_scene],rhino_group_id=str(uuid.UUID(int=101))) if cached_parent else dict(
        component_id="native-parent",model_path=model,rhino_group_id=str(uuid.UUID(int=101)),scene_ids=[parent_scene],
        child_component_ids=[],parent_component_id=None)
    store.register_scene_objects(store.fixture_scene_id,model,[A],native_observe=lambda request:dict(
        status="success",complete=True,model_path=request["expected_model_path"],objects=[object_row(A,child["component_id"])]))
    root=live(parent,[B]);root["child_component_ids"]=[child["component_id"]]
    leaf=live(child,[]);leaf["parent_component_id"]=parent["component_id"]
    before=snapshot(store)
    with pytest.raises(ValueError,match="presence scope") as error:
        store.align_components(model,native_inspect=bridge([root,leaf]),**(
            dict(component_ids=[parent["component_id"]]) if cached_parent else dict(scene_id=parent_scene)))
    assert error.value.native_result["error_code"]=="component_scope_incomplete"
    assert error.value.native_result["required_component_ids"]==sorted([parent["component_id"],child["component_id"]])
    assert snapshot(store)==before
    def expanded(request):
        assert A in request["prior_object_ids"]
        result=bridge([root,leaf])(request);result.update(presence_complete=True,absent_object_ids=[A])
        return result
    store.align_components(model,component_ids=[parent["component_id"],child["component_id"]],native_inspect=expanded)
    assert store.scene_objects(store.fixture_scene_id)==[]
