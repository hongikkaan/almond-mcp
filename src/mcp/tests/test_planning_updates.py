"""Public typed list edits, partial success, and whole-request rejection boundaries."""
import asyncio
import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


PLAN_CLEANUP_GUIDE = "이 Plan 과정에서만 사용했고 이제 필요 없는 객체·레이어·레이아웃·Named View를 정리하세요."


@pytest.fixture
def planning_server(tmp_path):
    store = AlmondStore(tmp_path / "planning.sqlite3")
    server = FastMCP("planning-update-test")
    register(server, SimpleNamespace(retrieval_store=store))
    return store, server


@pytest.fixture
def context(planning_server):
    store, server = planning_server

    def call(name, **arguments):
        async def run():
            async with Client(server) as client:
                return await client.call_tool(name, arguments, raise_on_error=False)
        return asyncio.run(run())
    return store, call


def body(response):
    assert not response.is_error
    return json.loads(response.content[0].text)


def test_saving_the_same_title_twice_returns_the_saved_revision(context):
    _, call = context
    created = body(call("plan_02-create", request={"target": "plan", "title": "검토", "goal": "입구 점검"}))
    request = {"target": "plan", "plan_id": created["plan"]["plan_id"], "title": "입구 검토"}
    updated = body(call("plan_12-update", request=request))
    repeated = body(call("plan_12-update", request=request))
    assert updated["status"] == "updated" and updated["changed"] and updated["issues"] == []
    assert repeated["status"] == "no_change" and not repeated["changed"] and repeated["issues"] == []
    assert updated["plan"] == repeated["plan"]
    assert repeated["plan"]["revision"] == 2 and repeated["plan"]["status"] == "pending"


def test_plan_completion_adds_guidance_only_on_a_saved_transition(context):
    store, call = context
    plan_id = store.create_plan("Review entrance")["plan_id"]

    def update(**fields):
        return body(call("plan_12-update", request={"target": "plan", "plan_id": plan_id, **fields}))

    first = update(status="completed")
    assert first["status"] == "updated" and first["changed"]
    assert first["plan"]["status"] == "completed"
    assert first["next_step_guide"].count(PLAN_CLEANUP_GUIDE) == 1
    assert "plan_05-get" in first["next_step_guide"]
    assert set(first) == {"status", "changed", "issues", "plan", "next_step_guide"}
    assert set(first["plan"]) == {"plan_id", "status", "loop_no", "revision"}

    again = update(status="completed")
    assert again["status"] == "no_change" and not again["changed"] and again["issues"] == []
    assert again["plan"] == first["plan"]
    assert PLAN_CLEANUP_GUIDE not in again["next_step_guide"]

    for fields in ({"title": "Final review"},
                   {"status": "completed", "title": "Approved review"}, {"status": "running"}):
        assert PLAN_CLEANUP_GUIDE not in update(**fields)["next_step_guide"]

    rejected = update(status="completed", expected_revision=first["plan"]["revision"])
    assert rejected["status"] == "error"
    assert PLAN_CLEANUP_GUIDE not in rejected.get("next_step_guide", "")
    partial = update(status="completed", depends_on={"remove": ["plan_absent"]})
    assert partial["status"] == "partial_success" and partial["changed"]
    assert partial["issues"][0]["reason"] == "not_found"
    assert "issues" in partial["next_step_guide"] and "expected_revision" in partial["next_step_guide"]
    assert partial["next_step_guide"].count(PLAN_CLEANUP_GUIDE) == 1
    assert partial["plan"]["status"] == "completed"
    edited = update(status="completed", title="Rechecked", depends_on={"remove": ["plan_absent"]})
    assert edited["status"] == "partial_success" and edited["issues"] == partial["issues"]
    assert "issues" in edited["next_step_guide"] and PLAN_CLEANUP_GUIDE not in edited["next_step_guide"]


def test_phase_completion_keeps_its_own_guide(context):
    store, call = context
    phase = store.create_phase("Design review")
    result = body(call("plan_12-update", request={"target": "phase", "phase_id": phase["phase_id"],
                                                 "status": "completed"}))
    assert result["status"] == "updated" and result["phase"]["status"] == "completed"
    assert "target='phase'" in result["next_step_guide"] and PLAN_CLEANUP_GUIDE not in result["next_step_guide"]
    repeated = body(call("plan_12-update", request={"target": "phase", "phase_id": phase["phase_id"],
                                                    "status": "completed"}))
    assert repeated["status"] == "no_change" and repeated["changed"] is False and repeated["issues"] == []


def test_concurrent_completed_requests_guide_only_the_first_revision(planning_server):
    store, server = planning_server
    plan = store.create_plan("Check elevations")
    request = {"target": "plan", "plan_id": plan["plan_id"], "status": "completed"}

    async def complete():
        async with Client(server) as client:
            calls = [client.call_tool("plan_12-update", {"request": {**request, "title": title}})
                     for title in ("East elevation", "West elevation")]
            return await asyncio.gather(*calls)

    replies = asyncio.run(complete())
    for reply in replies:
        assert json.loads(reply.structured_content["result"]) == body(reply)
    first, second = sorted(map(body, replies), key=lambda ack: ack["plan"]["revision"])
    assert first["status"] == second["status"] == "updated"
    assert first["changed"] and second["changed"]
    assert first["plan"]["revision"] == plan["revision"] + 1
    assert second["plan"]["revision"] == plan["revision"] + 2
    assert first["next_step_guide"].count(PLAN_CLEANUP_GUIDE) == 1
    assert PLAN_CLEANUP_GUIDE not in second["next_step_guide"]


def test_step_partial_edits_preserve_other_records_and_make_one_revision(context):
    store, call = context
    plan = store.create_plan("Inspect entrance", scope="component")
    pid = plan["plan_id"]
    before = store.update_plan_step(pid, plan["steps"][1]["step_id"], input_refs=["keep", "old", "conflict"], output_refs=["existing"])
    arguments = dict(plan_id=pid, step_id=plan["steps"][1]["step_id"], status="running",
                     input_refs={"add": ["new", "new", " conflict ", " ", "keep"],
                                 "remove": ["old", "absent", "conflict"]},
                     output_refs={"add": ["existing", "out"]})
    result = body(call("plan_12-update", request=dict(target="step", **arguments, expected_revision=before["revision"])))
    after = store.get_plan(pid)
    assert result["status"] == "partial_success" and result["changed"] is True
    assert result["plan"] == {"plan_id": pid, "status": "pending", "loop_no": 0, "revision": before["revision"] + 1}
    assert result["step"] == {"step_id": plan["steps"][1]["step_id"], "status": "running", "loop_no": 0}
    step = store.get_step(pid, plan["steps"][1]["step_id"])["step"]
    assert step["input_refs"] == ["keep", "conflict", "new"]
    assert step["output_refs"] == ["existing", "out"]
    assert len(result["issues"]) == 7
    assert {issue["reason"] for issue in result["issues"]} == {
        "conflicting_operation", "duplicate_input", "already_present", "not_found", "invalid_value"}
    assert {issue["operation"] for issue in result["issues"] if issue["reason"] == "conflicting_operation"} == {"add", "remove"}
    assert all(set(issue) == {"field", "operation", "index", "value", "reason"} for issue in result["issues"])
    assert store.get_plan(pid, before["revision"]) == {**before, "read_only": True}
    assert store.list_plan_revisions(pid)["total"] == after["revision"]
    replay = body(call("plan_12-update", request=dict(target="step", **arguments)))
    assert replay["status"] == "no_change" and replay["changed"] is False
    assert replay["issues"] and "issues" in replay["next_step_guide"]
    assert store.get_plan(pid) == after
    conflict = body(call("plan_12-update", request=dict(target="step", **arguments, expected_revision=before["revision"])))
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
    result = body(call("plan_12-update", request=dict(target="step", plan_id=plan["plan_id"], step_id=plan["steps"][1]["step_id"], **changes)))
    assert result["status"] == "updated" and result["changed"] is True and result["issues"] == []
    assert result["plan"]["revision"] == plan["revision"] + 1
    assert result["step"]["status"] == ("running" if status else "pending")


@pytest.mark.parametrize("patch", [None, {}, {"add": [], "remove": []}])
def test_empty_patch_keeps_records_and_revision(context, patch):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    saved = store.update_plan_step(plan["plan_id"], plan["steps"][1]["step_id"], output_refs=["keep"])
    result = body(call("plan_12-update", request=dict(target="step", plan_id=plan["plan_id"], step_id=plan["steps"][1]["step_id"], output_refs=patch)))
    assert result["status"] == "no_change" and result["changed"] is False and result["issues"] == []
    assert store.get_plan(plan["plan_id"]) == saved


@pytest.mark.parametrize("patch", [[], {"add": None}, {"add": ["valid", 42]},
    {"remove": [True]}, {"add": ["valid"], "replace": []}])
def test_schema_errors_reject_whole_request(context, patch):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    response = call("plan_12-update", request=dict(target="step", plan_id=plan["plan_id"], step_id=plan["steps"][1]["step_id"],
                    status="running", input_refs={"add": ["valid"]}, output_refs=patch))
    assert response.is_error
    assert store.get_plan(plan["plan_id"]) == plan


@pytest.mark.parametrize("invalid", [{"title": " "}, {"goal": ""}, {"status": "finished"},
    {"phase_id": "phase_unknown"}, {"scene_ids": ["scene_unknown"]},
    {"holon_ids": ["component_unknown"]}, {"artifact_refs": [""]}])
def test_invalid_general_plan_field_prevents_valid_dependency_edit(context, invalid):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    result = call("plan_12-update", request=dict(target="plan", plan_id=plan["plan_id"],
                       depends_on={"add": ["plan_future", "phase_wrong"]}, **invalid))
    if "status" in invalid:
        assert result.is_error
    else:
        assert body(result)["status"] == "error"
    assert store.get_plan(plan["plan_id"]) == plan


def test_invalid_step_status_and_phase_status_roll_back_everything(context):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    result = call("plan_12-update", request=dict(target="step", plan_id=plan["plan_id"], step_id=plan["steps"][1]["step_id"],
                       status="finished", output_refs={"add": ["valid"]}))
    assert result.is_error and store.get_plan(plan["plan_id"]) == plan
    phase = store.create_phase("Review")
    files = store.list_project_files()
    result = call("plan_12-update", request=dict(target="phase", phase_id=phase["phase_id"], status="finished",
                       file_name="should-not-be-registered.3dm", depends_on={"add": ["phase_future"]}))
    assert result.is_error and store.get_phase(phase["phase_id"]) == phase
    assert store.list_project_files() == files


@pytest.mark.parametrize("kind", ["phase", "plan"])
def test_dependencies_apply_only_same_kind_items_without_execution_gates(context, kind):
    store, call = context
    other = "plan" if kind == "phase" else "phase"
    record = store.create_phase("Review") if kind == "phase" else store.create_plan("Review")
    identifier = record[kind + "_id"]
    request = {"target": kind, kind + "_id": identifier}
    result = body(call("plan_12-update", request={**request,
                       "depends_on": {"add": [identifier, kind + "_future", other + "_wrong", kind + "_", ""]}}))
    assert result["status"] == "partial_success" and result["changed"] is True
    current = store.get_phase(identifier) if kind == "phase" else store.get_plan(identifier)
    assert current["depends_on"] == [identifier, kind + "_future"]
    assert current["status"] == "pending"
    assert [issue["reason"] for issue in result["issues"]] == ["invalid_reference_kind", "invalid_reference_kind", "invalid_value"]
    if kind == "phase":
        assert "revision" not in result["phase"]
    else:
        assert result["plan"]["revision"] == record["revision"] + 1
    removed = body(call("plan_12-update", request={**request, "depends_on": {"remove": current["depends_on"]}}))
    assert removed["status"] == "updated"
    current = store.get_phase(identifier) if kind == "phase" else store.get_plan(identifier)
    assert current["depends_on"] == []


@pytest.mark.parametrize("target", ["plan", "step"])
def test_revision_recording_failure_rolls_back_valid_partial_edits(context, monkeypatch, target):
    store, call = context
    plan = store.create_plan("Review", scope="component")
    def fail(*args, **kwargs):
        raise RuntimeError("snapshot failure")
    monkeypatch.setattr(store, "_record_generation_revision", fail)
    if target == "plan":
        fields = {"status": "completed", "depends_on": {"add": ["plan_valid", ""]}}
    else:
        fields = {"step_id": plan["steps"][1]["step_id"], "status": "running", "output_refs": {"add": ["valid", ""]}}
    result = body(call("plan_12-update", request={"target": target, "plan_id": plan["plan_id"], **fields}))
    assert result["status"] == "error"
    assert PLAN_CLEANUP_GUIDE not in result.get("next_step_guide", "")
    assert store.get_plan(plan["plan_id"]) == plan


def test_step_handoff_records_decisions_separately_from_file_refs(context):
    store, call = context
    plan = store.create_plan("Review entrance")
    plan_id = plan["plan_id"]
    current = store.execute_looping(plan_id)
    step = {"target": "step", "plan_id": plan_id, "step_id": current["steps"][0]["step_id"], "loop_no": 1}
    notes = {"takeaways": "북쪽 출입구의 동선을 유지한다.",
             "design_rationale": "기존 보행 축을 살린다.\n후속 도면에서도 이를 확인한다."}
    result = body(call("plan_12-update", request={
        **step, **notes, "expected_revision": current["revision"],
        "input_refs": {"add": ["source/survey.md"]},
        "output_refs": {"add": [".almond/produced/261116_review/01/entry.md"]},
    }))
    assert result["plan"]["revision"] == current["revision"] + 1
    detail = body(call("plan_05-get", request={**step, "include_details": True}))
    assert detail["status"] == "pending"
    assert detail["step"] == {
        "step_type": current["steps"][0]["step_type"], **notes,
        "input_refs": ["source/survey.md"],
        "output_refs": [".almond/produced/261116_review/01/entry.md"],
    }
    unchanged = body(call("plan_12-update", request={**step, "takeaways": None,
                                                     "design_rationale": notes["design_rationale"]}))
    assert unchanged["changed"] is False
    assert unchanged["plan"]["revision"] == detail["revision"]
    cleared = body(call("plan_12-update", request={**step, "takeaways": ""}))
    assert cleared["plan"]["revision"] == detail["revision"] + 1
    current = body(call("plan_05-get", request={**step, "include_details": True}))
    assert current["step"] == {**detail["step"], "takeaways": ""}


def test_reopening_pre_handoff_database_preserves_step_files_and_revision(tmp_path):
    db = tmp_path / "legacy-handoff.sqlite3"
    store = AlmondStore(db)
    plan = store.create_plan("Check entrance")
    plan_id = plan["plan_id"]
    step_id = plan["steps"][0]["step_id"]
    store.execute_looping(plan_id)
    saved = store.update_plan_step(plan_id, step_id, "running",
                                   input_refs=["source/survey.md"], output_refs=["result/entrance.pdf"])
    # Prepare a pre-handoff database without the new columns or snapshot keys.
    with sqlite3.connect(db) as connection:
        for field in ("takeaways", "design_rationale"):
            connection.execute(f"ALTER TABLE generation_loop_steps DROP COLUMN {field}")
        for loop_no, revision, raw in connection.execute(
            "SELECT loop_no, revision, snapshot_json FROM generation_plan_revisions"
        ).fetchall():
            snapshot = json.loads(raw)
            for step in snapshot["steps"]:
                step.pop("takeaways")
                step.pop("design_rationale")
            connection.execute("""UPDATE generation_plan_revisions SET snapshot_json = ?
                                  WHERE plan_id = ? AND loop_no = ? AND revision = ?""",
                               (json.dumps(snapshot), plan_id, loop_no, revision))

    reopened = AlmondStore(db)
    current = reopened.get_step(plan_id, step_id, loop_no=1)
    past = reopened.get_step(plan_id, step_id, loop_no=1, revision=saved["revision"])
    assert current["revision"] == saved["revision"]
    assert current["read_only"] is False and past["read_only"] is True
    for record in (current, past):
        assert record["step"]["status"] == "running"
        assert record["step"]["input_refs"] == ["source/survey.md"]
        assert record["step"]["output_refs"] == ["result/entrance.pdf"]
        assert record["step"]["takeaways"] == record["step"]["design_rationale"] == ""
