import json
from types import SimpleNamespace

from fastmcp import FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


CREATE = "plan_02-create"
GET = "plan_05-get"
LIST = "plan_08-list"
UPDATE = "plan_12-update"


def planning_server(database, **context):
    server = FastMCP("Planning workflow")
    register(server, SimpleNamespace(retrieval_store=AlmondStore(database), **context))
    return server


def create_step(call_tool, server):
    _, result = call_tool(server, CREATE, request={
        "target": "plan", "scope": "inspection", "title": "Entrance review", "goal": "Review entrance circulation",
    })
    plan = {"plan_id": result["plan"]["plan_id"]}
    _, rows = call_tool(server, LIST, request={"target": "step", **plan})
    step = {**plan, "target": "step", "step_id": rows["steps"][0]["step_id"]}
    return {**plan, "target": "plan"}, step


def test_step_history_and_pause(tmp_path, call_tool):
    database = tmp_path / "project.sqlite3"
    server = planning_server(database)
    plan, step = create_step(call_tool, server)
    _, paused = call_tool(server, UPDATE, request={**plan, "status": "paused"})
    paused_revision = paused["plan"]["revision"]
    _, saved = call_tool(server, UPDATE, request={
        **step, "expected_revision": paused_revision, "status": "running",
        "input_refs": {"add": ["survey.md"]}, "output_refs": {"add": ["entrance.png"]},
    })
    assert saved["plan"]["revision"] == paused_revision + 1

    reopened = planning_server(database)
    _, rejected = call_tool(reopened, UPDATE, request={
        **step, "expected_revision": paused_revision, "output_refs": {"remove": ["entrance.png"]},
    })
    assert rejected["status"] == "error"
    _, current = call_tool(reopened, GET, request={**step, "include_details": True})
    _, previous = call_tool(reopened, GET, request={
        **step, "revision": paused_revision, "include_details": True,
    })
    _, selected_plan = call_tool(reopened, GET, request=plan)

    assert selected_plan["status"] == "paused"
    assert current["status"] == "running" and current["revision"] == paused_revision + 1
    assert current["step"]["input_refs"] == ["survey.md"]
    assert current["step"]["output_refs"] == ["entrance.png"]
    assert previous["read_only"] and previous["step"]["output_refs"] == []


def test_phase_edit_is_atomic(tmp_path, call_tool):
    database = tmp_path / "project.sqlite3"
    catalog = AlmondStore(database)
    for name in ("Existing.3dm", "Proposed.3dm", "Unrelated.3dm"):
        catalog.upsert_project_file(name)
    server = planning_server(database)
    _, created = call_tool(server, CREATE, request={
        "target": "phase", "name": "Survey", "file_name": ["Proposed.3dm", "Existing.3dm"],
    })
    phase = {"target": "phase", "phase_id": created["phase"]["phase_id"]}

    _, rejected = call_tool(server, UPDATE, request={
        **phase, "name": "Rejected name", "file_name": ["Unrelated.3dm", "Missing.3dm"],
    })
    assert rejected["status"] == "error"
    assert "Missing.3dm" in rejected["message"]
    _, saved = call_tool(planning_server(database), GET, request={**phase, "include_details": True})
    assert saved["name"] == "Survey"
    assert saved["phase"]["file_name"] == ["Proposed.3dm", "Existing.3dm"]
    assert len(AlmondStore(database).list_project_files()["files"]) == 3


def test_lost_step_cleanup_reply(tmp_path, monkeypatch, call_tool):
    database = tmp_path / "project.sqlite3"
    model = str(tmp_path / "entrance.3dm")
    monkeypatch.setenv("ALMOND_MODEL_PATH", model)
    observed = []

    def bridge(raw, **_options):
        request = json.loads(raw)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"step_temp_cleanup": 1}})

        assert request["type"] == "cleanup_step_temp"
        assert request["expected_model_path"] == model
        saved = AlmondStore(database).get_step(step["plan_id"], step["step_id"])
        observed.append(saved["step"]["status"])
        raise TimeoutError("Cleanup acknowledgement lost")

    server = planning_server(database, _send_and_receive=bridge)
    _, step = create_step(call_tool, server)
    before = call_tool(server, GET, request=step)[1]["revision"]
    _, result = call_tool(server, UPDATE, request={
        **step, "status": "completed", "takeaways": "Keep the clear path at the entrance",
    })

    assert result["cleanup_state"] == "unknown" and result["requires_reconciliation"]
    assert result["changed"]
    reopened = planning_server(database, _send_and_receive=bridge)
    _, saved = call_tool(reopened, GET, request={**step, "include_details": True})
    assert saved["revision"] == before + 1 and saved["status"] == "completed"
    assert saved["step"]["takeaways"] == "Keep the clear path at the entrance"
    _, retry = call_tool(reopened, UPDATE, request={**step, "status": "completed"})
    assert retry["status"] == "no_change"
    assert observed == ["completed"]
