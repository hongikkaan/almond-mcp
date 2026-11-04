"""Public typed list edits, partial success, and whole-request rejection boundaries."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


@pytest.fixture
def context(tmp_path):
    store = AlmondStore(tmp_path / "planning.sqlite3")
    server = FastMCP("planning-update-test")
    register(server, SimpleNamespace(retrieval_store=store))
    def call(name, **arguments):
        async def run():
            async with Client(server) as client:
                return await client.call_tool(name, arguments, raise_on_error=False)
        return asyncio.run(run())
    return store, call


def body(response):
    assert not response.is_error
    return json.loads(response.content[0].text)


def test_step_partial_edits_preserve_other_records_and_make_one_revision(context):
    store, call = context
    plan = store.create_plan("Inspect entrance", scope="component")
    pid = plan["plan_id"]
    before = store.update_plan_step(pid, "design", input_refs=["keep", "old", "conflict"], output_refs=["existing"])
    arguments = dict(plan_id=pid, step_id="design", status="running",
                     input_refs={"add": ["new", "new", " conflict ", " ", "keep"],
                                 "remove": ["old", "absent", "conflict"]},
                     output_refs={"add": ["existing", "out"]})
    result = body(call("update_step", **arguments, expected_revision=before["revision"]))
    after = store.get_plan(pid)
    assert result["status"] == "partial_success" and result["changed"] is True
    assert result["plan"] == {"plan_id": pid, "status": "running", "revision": before["revision"] + 1}
    assert result["step"] == {"step_id": "design", "status": "running"}
    step = store.get_step(pid, "design")["step"]
    assert step["input_refs"] == ["keep", "conflict", "new"]
    assert step["output_refs"] == ["existing", "out"]
    assert len(result["issues"]) == 7
    assert {issue["reason"] for issue in result["issues"]} == {
        "conflicting_operation", "duplicate_input", "already_present", "not_found", "invalid_value"}
    assert {issue["operation"] for issue in result["issues"] if issue["reason"] == "conflicting_operation"} == {"add", "remove"}
    assert all(set(issue) == {"field", "operation", "index", "value", "reason"} for issue in result["issues"])
    assert store.get_plan(pid, before["revision"]) == before
    assert store.list_plan_revisions(pid)["total"] == after["revision"]
    replay = body(call("update_step", **arguments))
    assert replay["status"] == "no_change" and replay["changed"] is False
    assert store.get_plan(pid) == after
    conflict = body(call("update_step", **arguments, expected_revision=before["revision"]))
    assert conflict["status"] == "error" and store.get_plan(pid) == after


@pytest.mark.parametrize("status,inputs,outputs", [
    (True, False, False), (False, True, False), (False, False, True),
    (True, True, False), (True, False, True), (False, True, True), (True, True, True),
])
def test_each_combination_uses_one_revision(context, status, inputs, outputs):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    changes = {}
    if status:
        changes["status"] = "running"
    if inputs:
        changes["input_refs"] = {"add": ["brief"]}
    if outputs:
        changes["output_refs"] = {"add": ["survey"]}
    result = body(call("update_step", plan_id=plan["plan_id"], step_id="design", **changes))
    assert result["status"] == "success" and result["changed"] is True and result["issues"] == []
    assert result["plan"]["revision"] == plan["revision"] + 1
    assert result["step"]["status"] == ("running" if status else "pending")


@pytest.mark.parametrize("patch", [None, {}, {"add": [], "remove": []}])
def test_empty_patch_keeps_records_and_revision(context, patch):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    saved = store.update_plan_step(plan["plan_id"], "design", output_refs=["keep"])
    result = body(call("update_step", plan_id=plan["plan_id"], step_id="design", output_refs=patch))
    assert result["status"] == "success" and result["changed"] is False and result["issues"] == []
    assert store.get_plan(plan["plan_id"]) == saved


@pytest.mark.parametrize("patch", [[], {"add": None}, {"add": ["valid", 42]},
    {"remove": [True]}, {"add": ["valid"], "replace": []}])
def test_schema_errors_reject_whole_request(context, patch):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    response = call("update_step", plan_id=plan["plan_id"], step_id="design",
                    status="running", input_refs={"add": ["valid"]}, output_refs=patch)
    assert response.is_error
    assert store.get_plan(plan["plan_id"]) == plan


@pytest.mark.parametrize("invalid", [{"title": " "}, {"goal": ""}, {"status": "finished"},
    {"phase_id": "phase_unknown"}, {"scene_ids": ["scene_unknown"]},
    {"holon_ids": ["component_unknown"]}, {"artifact_refs": [""]}])
def test_invalid_general_plan_field_prevents_valid_dependency_edit(context, invalid):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    result = body(call("update_plan", plan_id=plan["plan_id"],
                       depends_on={"add": ["plan_future", "phase_wrong"]}, **invalid))
    assert result["status"] == "error"
    assert store.get_plan(plan["plan_id"]) == plan


def test_invalid_step_status_and_phase_status_roll_back_everything(context):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    result = body(call("update_step", plan_id=plan["plan_id"], step_id="design",
                       status="finished", output_refs={"add": ["valid"]}))
    assert result["status"] == "error" and store.get_plan(plan["plan_id"]) == plan
    phase = store.create_phase("Review")
    files = store.list_project_files()
    result = body(call("update_phase", phase_id=phase["phase_id"], status="finished",
                       file_name="should-not-be-registered.3dm", depends_on={"add": ["phase_future"]}))
    assert result["status"] == "error" and store.get_phase(phase["phase_id"]) == phase
    assert store.list_project_files() == files


@pytest.mark.parametrize("kind", ["phase", "plan"])
def test_dependencies_apply_only_same_kind_items_without_execution_gates(context, kind):
    store, call = context
    other = "plan" if kind == "phase" else "phase"
    record = store.create_phase("Review") if kind == "phase" else store.create_plan("Review")
    identifier = record[kind + "_id"]
    result = body(call("update_" + kind, **{kind + "_id": identifier},
                       depends_on={"add": [identifier, kind + "_future", other + "_wrong", kind + "_", ""]}))
    assert result["status"] == "partial_success" and result["changed"] is True
    current = store.get_phase(identifier) if kind == "phase" else store.get_plan(identifier)
    assert current["depends_on"] == [identifier, kind + "_future"]
    assert current["status"] == "pending"
    assert [issue["reason"] for issue in result["issues"]] == ["invalid_reference_kind", "invalid_reference_kind", "invalid_value"]
    if kind == "phase":
        assert "revision" not in result["phase"]
    else:
        assert result["plan"]["revision"] == record["revision"] + 1
    removed = body(call("update_" + kind, **{kind + "_id": identifier},
                        depends_on={"remove": current["depends_on"]}))
    assert removed["status"] == "success"
    current = store.get_phase(identifier) if kind == "phase" else store.get_plan(identifier)
    assert current["depends_on"] == []


def test_revision_recording_failure_rolls_back_valid_partial_edits(context, monkeypatch):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    def fail(*args, **kwargs):
        raise RuntimeError("snapshot failure")
    monkeypatch.setattr(store, "_record_generation_revision", fail)
    result = body(call("update_step", plan_id=plan["plan_id"], step_id="design", status="running",
                       output_refs={"add": ["valid", ""]}))
    assert result["status"] == "error"
    assert store.get_plan(plan["plan_id"]) == plan
