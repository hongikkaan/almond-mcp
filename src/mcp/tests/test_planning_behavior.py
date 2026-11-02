"""Planning behavior through the store facade and public tool entry points."""
import json
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


@pytest.fixture
def store(tmp_path):
    return AlmondStore(tmp_path / "planning.sqlite3")


@pytest.mark.parametrize("plan_status", ["paused", "completed"])
def test_step_refs_do_not_resume_an_explicitly_stopped_plan(store, plan_status):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    store.update_plan_step(plan_id, "inspect_context", "running")
    stopped = store.update_plan(plan_id, status=plan_status)

    updated = store.update_plan_step(
        plan_id, "inspect_context", "running",
        input_refs=["brief.md"], output_refs=["entrance.png"],
        expected_revision=stopped["revision"],
    )

    assert updated["status"] == plan_status
    assert updated["revision"] == stopped["revision"] + 1
    assert updated["steps"][0]["input_refs"] == ["brief.md"]
    assert updated["steps"][0]["output_refs"] == ["entrance.png"]
    assert store.get_plan(plan_id) == updated
    assert store.get_plan(plan_id, revision=stopped["revision"]) == stopped


def test_step_details_include_refs_without_expanding_the_plan_summary(store):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    store.update_plan_step(
        plan_id, "inspect_context", "running",
        input_refs=["brief.md"], output_refs=["entrance.png"],
    )
    tools = register(FastMCP("planning-test"), SimpleNamespace(retrieval_store=store))

    detailed = json.loads(tools["get_plan"](
        plan_id, include_ids=True, field_groups=["steps"],
    ))["plan"]
    assert detailed["steps"][0]["input_refs"] == ["brief.md"]
    assert detailed["steps"][0]["output_refs"] == ["entrance.png"]
    assert "scene_ids" not in detailed
    assert "artifact_refs" not in detailed
    summary = json.loads(tools["get_plan"](plan_id))["plan"]
    assert "steps" not in summary
    assert "artifact_refs" not in summary


def test_refs_replacement_clear_and_target_override_preserve_pause_and_revision_guards(store):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    store.update_plan_step(plan_id, "inspect_context", "running", output_refs=["old.png"])
    paused = store.update_plan(plan_id, status="paused")
    replaced = store.update_plan_step(
        plan_id, "inspect_context", "running", output_refs=["new.png"],
        expected_revision=paused["revision"],
    )
    assert replaced["status"] == "paused"
    with pytest.raises(ValueError):
        store.update_plan_step(
            plan_id, "inspect_context", "running", output_refs=[],
            expected_revision=paused["revision"],
        )
    assert store.get_plan(plan_id) == replaced

    cleared = store.update_plan_step(
        plan_id, "inspect_context", "running", output_refs=[], component_ids=[],
        expected_revision=replaced["revision"],
    )
    assert cleared["status"] == "paused"
    assert cleared["steps"][0]["output_refs"] == []
    assert cleared["steps"][0]["component_ids"] == []
    assert store.update_plan_step(
        plan_id, "inspect_context", "running", output_refs=[], component_ids=[],
        expected_revision=cleared["revision"],
    ) == cleared
    assert store.list_plan_revisions(plan_id)["total"] == cleared["revision"]


def test_actual_step_status_changes_still_recalculate_the_plan(store):
    plan = store.create_plan("Review the entrance", scope="component")
    plan_id = plan["plan_id"]
    store.update_plan(plan_id, status="completed")
    assert store.update_plan_step(plan_id, "inspect_context", "running")["status"] == "running"
    assert store.update_plan_step(plan_id, "inspect_context", "blocked")["status"] == "blocked"


def test_reference_artifact_and_saved_revision_selection_remain_available(store):
    plan = store.create_plan("Review the entrance", scope="component", depends_on=["related-plan"])
    plan_id = plan["plan_id"]
    saved = store.update_plan(plan_id, artifact_refs=["report.md"])
    store.update_plan_step(plan_id, "inspect_context", "running", output_refs=["entrance.png"])
    tools = register(FastMCP("planning-test"), SimpleNamespace(retrieval_store=store))

    selected = json.loads(tools["get_plan"](
        plan_id, include_ids=True, field_groups=["steps", "references", "artifacts"],
    ))["plan"]
    assert selected["depends_on"] == ["related-plan"]
    assert selected["artifact_refs"] == ["report.md"]
    assert selected["steps"][0]["output_refs"] == ["entrance.png"]
    historical = json.loads(tools["get_plan"](
        plan_id, revision=saved["revision"], include_ids=True, field_groups=["all"],
    ))["plan"]
    assert historical["status"] == "pending"
    assert historical["steps"][0]["output_refs"] == []
    assert historical["artifact_refs"] == ["report.md"]
