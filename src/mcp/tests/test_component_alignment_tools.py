"""Agent-facing BDD: one safe alignment and compact acknowledgements."""
import json

from test_component_tools import A, B, GROUP, call, model, register, scene, server, store, wire
from test_component_alignment import live


def test_given_manual_group_change_when_agent_aligns_then_one_compact_ack(server, store, scene, model, wire):
    wire()
    created = register(server, model, scene, component_id="meaning", rhino_group_id=GROUP)
    assert created["status"] == "success" and created["component"]["component_id"] == "meaning"
    assert "objects" not in created["component"] and "scene_ids" not in created["component"]
    prior = store.get_component("meaning")
    def document(request):
        assert request["action"] == "inspect_many"
        return dict(status="success", complete=True, model_path=model, editing=dict(mode="model", stable=True),
                    components=[live(prior, [B])], problems=[])
    requests = wire(document, context=dict(status="success", capabilities=dict(design_components=1, component_registry=2)))
    result = call(server, "sync_ontological_component", expected_model_path=model)
    assert result["status"] == "success" and result["changed"] == 1
    assert not {"components", "objects", "effective_objects"}.intersection(result)
    assert A not in json.dumps(result) and B not in json.dumps(result)
    assert store.get_component("meaning")["object_count"] == 1
    assert [request.get("action") for request in requests] == [None, "inspect_many"]


def test_given_old_bridge_when_agent_aligns_then_no_observation_or_write(server, store, scene, model, wire):
    wire()
    register(server, model, scene, component_id="meaning", rhino_group_id=GROUP)
    requests = wire(context=dict(status="success", capabilities=dict(design_components=1)))
    result = call(server, "sync_ontological_component", component_id="meaning", expected_model_path=model)
    assert result["status"] == "error" and "component_registry=2" in result["message"]
    assert len(requests) == 1
    assert store.get_component("meaning")["object_count"] == 2


def test_given_active_group_editor_when_agent_aligns_then_mode_evidence_is_preserved(server, store, scene, model, wire):
    wire()
    register(server, model, scene, component_id="meaning", rhino_group_id=GROUP)
    wire(lambda request: dict(status="error", error_code="unstable_editing_scope", mutation_applied=False,
         message="Finish group editing.", editing=dict(mode="group", stable=False, target=dict(name="Panel"))),
         context=dict(status="success", capabilities=dict(design_components=1, component_registry=2)))
    result = call(server, "sync_ontological_component", expected_model_path=model)
    assert result["status"] == "error" and result["editing"]["mode"] == "group"
    assert result["mutation_applied"] is False
    assert store.get_component("meaning")["object_count"] == 2


def test_given_target_binding_failure_when_agent_aligns_then_cached_data_is_not_live_proof(server, store, scene, model, wire):
    wire()
    register(server, model, scene, component_id="meaning", rhino_group_id=GROUP)
    wire(lambda request: dict(status="success", complete=True, model_path=model,
         editing=dict(mode="model", stable=True), components=[],
         problems=[dict(component_id="meaning", code="invalid_binding")]),
         context=dict(status="success", capabilities=dict(design_components=1, component_registry=2)))
    result = call(server, "sync_ontological_component", expected_model_path=model, component_id="meaning")
    assert result["checked"] == 0 and result["problems"][0]["component_id"] == "meaning"
    assert "component" not in result and result["live_verified"] is False
    assert store.get_component("meaning")["object_count"] == 2


def test_given_native_group_rename_refusal_when_agent_updates_then_db_and_scene_are_untouched(server, store, scene, model, wire):
    wire()
    register(server, model, scene, component_id="meaning", rhino_group_id=GROUP)
    before, scene_before = store.get_component("meaning"), store.get_scene(scene)
    wire(lambda request: dict(status="error", error_code="component_error", mutation_applied=False,
         message="Use the current Rhino group name; group-table renames are not Undo-tracked."))
    result = call(server, "upsert_ontological_component", expected_model_path=model, component_id="meaning",
                  name="Different group name", object_ids=[A, B], scene_ids=[scene])
    assert result["status"] == "error" and result["mutation_applied"] is False
    assert store.get_component("meaning") == before and store.get_scene(scene) == scene_before


def test_given_conflicting_scene_and_target_when_agent_aligns_then_no_false_live_ack(server, store, scene, model, wire):
    wire()
    register(server, model, scene, component_id="meaning", rhino_group_id=GROUP)
    other = store.create_scene("Other Scene")["scene_id"]
    requests = wire()
    result = call(server, "sync_ontological_component", component_id="meaning", scene_id=other, expected_model_path=model)
    assert result["status"] == "error" and "component" not in result and requests == []


def test_given_native_child_without_cached_parent_when_aligning_scene_then_actionable_scope_failure_and_no_db_change(server, store, scene, model, wire):
    from test_components import snapshot
    child = dict(component_id="native-child", model_path=model, rhino_group_id=GROUP, scene_ids=[scene],
                 child_component_ids=[], parent_component_id="native-parent")
    from test_component_alignment import bridge
    wire(bridge([live(child, [A])]))
    before = snapshot(store)
    result = call(server, "sync_ontological_component", scene_id=scene, expected_model_path=model)
    assert result["status"] == "error" and result["error_code"] == "component_scope_incomplete"
    assert result["missing_parent_component_ids"] == ["native-parent"] and result["next_action"]
    assert result["mutation_applied"] is False and "component" not in result
    assert snapshot(store) == before


def test_given_native_group_name_collision_when_agent_registers_new_meaning_then_db_is_untouched(server, store, scene, model, wire):
    from test_components import snapshot
    wire(lambda request:dict(status="error",error_code="component_name_collision",mutation_applied=False,
         message="An ordinary Rhino group already uses this name. Review that group in Rhino or explicitly choose another name."))
    before=snapshot(store)
    result=register(server,model,scene,component_id="new-meaning")
    assert result["status"]=="error" and result["error_code"]=="component_name_collision" and result["mutation_applied"] is False
    assert snapshot(store)==before
