"""Planning behavior through the store facade and public tool entry points."""
import json
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP
from pydantic import TypeAdapter

from almond_mcp.features.planning.requests import GetRequest
from almond_mcp.features.planning.schema import STATUSES
from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore

parse_get = TypeAdapter(GetRequest).validate_python


@pytest.fixture
def store(tmp_path):
    return AlmondStore(tmp_path / "planning.sqlite3")


@pytest.mark.parametrize("plan_status", ["paused", "completed"])
def test_step_refs_do_not_resume_an_explicitly_stopped_plan(store, plan_status):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    step_id = plan["steps"][0]["step_id"]
    store.update_plan_step(plan_id, step_id, "running")
    stopped = store.update_plan(plan_id, status=plan_status)

    updated = store.update_plan_step(
        plan_id, step_id, "running",
        input_refs=["brief.md"], output_refs=["entrance.png"],
        expected_revision=stopped["revision"],
    )

    assert updated["status"] == plan_status
    assert updated["revision"] == stopped["revision"] + 1
    assert updated["steps"][0]["input_refs"] == ["brief.md"]
    assert updated["steps"][0]["output_refs"] == ["entrance.png"]
    assert store.get_plan(plan_id) == updated
    assert store.get_plan(plan_id, revision=stopped["revision"]) == {**stopped, "read_only": True}


def test_step_details_include_refs_without_expanding_the_plan_summary(store):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    step_id = plan["steps"][0]["step_id"]
    store.update_plan_step(
        plan_id, step_id, "running",
        input_refs=["brief.md"], output_refs=["entrance.png"],
    )
    tools = register(FastMCP("planning-test"), SimpleNamespace(retrieval_store=store))

    detailed = json.loads(tools["get_planning"](parse_get(dict(
        target="step", include_details=True, plan_id=plan_id, step_id=step_id,
    ))))["step"]
    assert detailed["input_refs"] == ["brief.md"]
    assert detailed["output_refs"] == ["entrance.png"]
    summary = json.loads(tools["get_planning"](parse_get(dict(target="plan", include_details=True, plan_id=plan_id))))["plan"]
    assert summary["steps"][0] == {"step_id": step_id, "step_type": "inspect_context", "name": "inspect_context", "status": "running", "loop_no": 0}
    assert summary["scene_ids"] == [] and summary["artifact_refs"] == []
    assert "component_ids" not in summary


def test_refs_replacement_and_clear_preserve_pause_and_revision_guards(store):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    step_id = plan["steps"][0]["step_id"]
    store.update_plan_step(plan_id, step_id, "running", output_refs=["old.png"])
    paused = store.update_plan(plan_id, status="paused")
    replaced = store.update_plan_step(
        plan_id, step_id, "running", output_refs=["new.png"],
        expected_revision=paused["revision"],
    )
    assert replaced["status"] == "paused"
    with pytest.raises(ValueError):
        store.update_plan_step(
            plan_id, step_id, "running", output_refs=[],
            expected_revision=paused["revision"],
        )
    assert store.get_plan(plan_id) == replaced

    cleared = store.update_plan_step(
        plan_id, step_id, "running", output_refs=[],
        expected_revision=replaced["revision"],
    )
    assert cleared["status"] == "paused"
    assert cleared["steps"][0]["output_refs"] == []
    assert "component_ids" not in cleared["steps"][0]
    assert store.update_plan_step(
        plan_id, step_id, "running", output_refs=[],
        expected_revision=cleared["revision"],
    ) == cleared
    assert store.list_plan_revisions(plan_id)["total"] == cleared["revision"]


@pytest.mark.parametrize("plan_status", STATUSES)
def test_actual_step_status_changes_preserve_explicit_plan_status(store, plan_status):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    step_id = plan["steps"][0]["step_id"]
    store.update_plan(plan_id, status=plan_status)
    assert store.update_plan_step(plan_id, step_id, "running")["status"] == plan_status
    assert store.get_step(plan_id, step_id)["step"]["status"] == "running"
    assert store.update_plan_step(plan_id, step_id, "blocked")["status"] == plan_status
    assert store.get_step(plan_id, step_id)["step"]["status"] == "blocked"


@pytest.mark.parametrize("status,inputs,outputs", [
    (True, False, False), (False, True, False), (False, False, True),
    (True, True, False), (True, False, True), (False, True, True), (True, True, True),
])
def test_independent_step_fields_change_one_revision_per_request(store, status, inputs, outputs):
    plan = store.create_plan("Review entrance", scope="component")
    changes = {}
    if status:
        changes["status"] = "running"
    if inputs:
        changes["input_refs"] = ["brief.md"]
    if outputs:
        changes["output_refs"] = ["survey.md"]
    updated = store.update_plan_step(plan["plan_id"], plan["steps"][0]["step_id"], **changes)
    assert updated["revision"] == plan["revision"] + 1
    step = updated["steps"][0]
    assert step["status"] == ("running" if status else "pending")
    assert step["input_refs"] == (["brief.md"] if inputs else [])
    assert step["output_refs"] == (["survey.md"] if outputs else [])
    assert store.update_plan_step(plan["plan_id"], plan["steps"][0]["step_id"], **changes) == updated
    assert store.update_plan_step(plan["plan_id"], plan["steps"][0]["step_id"]) == updated
    with pytest.raises(ValueError):
        store.update_plan_step(plan["plan_id"], plan["steps"][0]["step_id"], output_refs=["stale"], expected_revision=plan["revision"])
    assert store.get_plan(plan["plan_id"]) == updated


@pytest.mark.parametrize("plan_status", ["paused", "completed"])
def test_omitted_step_status_preserves_stopped_plan(store, plan_status):
    plan = store.create_plan("Review entrance", scope="component")
    paused = store.update_plan(plan["plan_id"], status=plan_status)
    updated = store.update_plan_step(plan["plan_id"], plan["steps"][0]["step_id"], output_refs=["survey"])
    assert updated["status"] == plan_status
    assert updated["steps"][0]["status"] == "pending"
    assert updated["revision"] == paused["revision"] + 1


def test_reference_artifact_and_saved_revision_selection_remain_available(store):
    plan = store.create_plan("Review the entrance", scope="component", depends_on=["plan_related"])
    plan_id = plan["plan_id"]
    step_id = plan["steps"][0]["step_id"]
    saved = store.update_plan(plan_id, artifact_refs=["report.md"])
    store.update_plan_step(plan_id, step_id, "running", output_refs=["entrance.png"])
    tools = register(FastMCP("planning-test"), SimpleNamespace(retrieval_store=store))

    selected = json.loads(tools["get_planning"](parse_get(dict(target="plan", include_details=True, plan_id=plan_id))))["plan"]
    assert selected["depends_on"] == ["plan_related"]
    assert selected["artifact_refs"] == ["report.md"]
    assert "output_refs" not in selected["steps"][0]
    historical = json.loads(tools["get_planning"](parse_get(dict(target="plan", include_details=True, plan_id=plan_id, revision=saved["revision"]))))
    assert historical["status"] == "pending"
    assert historical["plan"]["artifact_refs"] == ["report.md"]
    old_step = json.loads(tools["get_planning"](parse_get(dict(
        target="step", include_details=True, plan_id=plan_id, revision=saved["revision"], step_id=step_id))))
    assert old_step["step"]["output_refs"] == []
