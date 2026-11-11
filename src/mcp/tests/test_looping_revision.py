"""User-visible Plan, Loop and Step identity and history contracts."""
import asyncio
import json
import sqlite3
import uuid
from types import SimpleNamespace

from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


def test_mcp_step_identity_is_independent_of_template_type(tmp_path):
    store = AlmondStore(tmp_path / "planning.db")
    server = FastMCP("looping-contracts")
    register(server, SimpleNamespace(retrieval_store=store))

    async def run():
        async with Client(server) as client:
            async def call(name, **arguments):
                result = await client.call_tool(name, arguments)
                return json.loads(result.content[0].text)
            first = await call("create_plan", title="First", goal="Inspect", scope="inspection")
            second = await call("create_plan", title="Second", goal="Inspect", scope="inspection")
            details = [await call("get_phase_plan_step", include_details=True, plan_id=item["plan"]["plan_id"])
                       for item in (first, second)]
            a, b = [detail["plan"]["steps"] for detail in details]
            assert [step["step_type"] for step in a] == [step["step_type"] for step in b]
            assert not {step["step_id"] for step in a} & {step["step_id"] for step in b}
            for step in a:
                uuid.UUID(step["step_id"].removeprefix("step_"))
                assert step["step_id"] != step["step_type"]
                detail = await call("get_phase_plan_step", include_details=True, plan_id=first["plan"]["plan_id"], step_id=step["step_id"])
                assert detail["step"]["step_type"] == step["step_type"]
    asyncio.run(run())


def test_legacy_step_identity_migration_preserves_history_and_dependencies(tmp_path):
    path = tmp_path / "legacy.db"
    store = AlmondStore(path)
    plan = store.create_plan("Existing work", scope="inspection")
    pid = plan["plan_id"]
    old_ids = {step["step_id"]: step["step_type"] for step in plan["steps"]}
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        for step in plan["steps"]:
            db.execute("UPDATE generation_plan_steps SET step_id=?,depends_on_json=? WHERE plan_id=? AND step_id=?",
                (step["step_type"], json.dumps([old_ids[v] for v in step["depends_on"]]), pid, step["step_id"]))
            db.execute("UPDATE generation_loop_steps SET step_id=? WHERE plan_id=? AND step_id=?",
                       (step["step_type"],pid,step["step_id"]))
        db.execute("ALTER TABLE generation_plan_steps DROP COLUMN step_type")
        db.execute("ALTER TABLE generation_plan_steps DROP COLUMN name")
        snapshot = json.loads(db.execute("SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=?", (pid,)).fetchone()[0])
        for step in snapshot["steps"]:
            step["step_id"] = old_ids[step["step_id"]]
            step["depends_on"] = [old_ids[v] for v in step["depends_on"]]
            step.pop("step_type")
        raw = json.dumps(snapshot)
        db.execute("UPDATE generation_plan_revisions SET snapshot_json=? WHERE plan_id=?", (raw, pid))
    migrated = AlmondStore(path)
    current = migrated.get_plan(pid)
    assert current["revision"] == plan["revision"]
    assert current["updated_at"] == plan["updated_at"]
    for step in current["steps"]:
        uuid.UUID(step["step_id"].removeprefix("step_"))
        assert step["step_type"] == step["name"]
        assert migrated.get_step(pid, step["step_id"], revision=1)["step"] == step
    assert [s["depends_on"] for s in current["steps"]] == [
        [], [current["steps"][0]["step_id"]], [current["steps"][1]["step_id"]], [current["steps"][2]["step_id"]]]
    assert AlmondStore(path).get_plan(pid) == current
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=?", (pid,)).fetchone()[0] == raw
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_step_progress_does_not_overwrite_explicit_plan_status(tmp_path):
    store = AlmondStore(tmp_path / "status.db")
    server = FastMCP("plan-status-contracts")
    register(server, SimpleNamespace(retrieval_store=store))

    async def run():
        async with Client(server) as client:
            async def call(name, **arguments):
                result = await client.call_tool(name, arguments)
                return json.loads(result.content[0].text)
            created = await call("create_plan", title="Review", goal="Review", scope="inspection")
            pid = created["plan"]["plan_id"]
            await call("update_plan", plan_id=pid, status="paused")
            detail = await call("get_phase_plan_step", include_details=True, plan_id=pid)
            for step in detail["plan"]["steps"]:
                changed = await call("update_step", plan_id=pid, step_id=step["step_id"], status="completed")
                assert changed["plan"]["status"] == "paused"
            assert (await call("get_phase_plan_step", include_details=True, plan_id=pid))["status"] == "paused"
            await call("update_plan", plan_id=pid, status="completed")
            assert (await call("get_phase_plan_step", include_details=True, plan_id=pid))["status"] == "completed"
    asyncio.run(run())


def test_loop_role_and_input_options_do_not_include_post_execution_reporting():
    from almond_mcp.instruction_text import read_tool_instruction
    import mcp_server
    text = read_tool_instruction(mcp_server.__file__, "execute_looping")
    role, inputs = text.split("Args:", 1)
    assert "사용자가 결정" not in role
    assert "시각적 근거" not in role
    assert "재개" in inputs and "현재 회차를 먼저 확인" in inputs
    assert "Args:" in text and "resume:" in text
    assert "get_looping_policy" not in text
    assert "반환:" not in text
    from almond_mcp.tool_guidance import guide_payload
    guide = guide_payload("execute_looping", {"status": "success"})["next_step_guide"]
    assert "update_step" in guide and "시각적 근거" in guide
    assert "next_step_guide" not in guide_payload("execute_looping", {"status": "error"})


def test_execute_looping_advances_and_resumes_with_independent_history(tmp_path, monkeypatch):
    import mcp_server
    from project import connection_paths
    from workspace import Workspace

    model = tmp_path / "fixture.3dm"
    model.touch()
    locations = connection_paths(model, "A", "a" * 32, create=True)
    store = AlmondStore(locations["state_db"])
    workspace = Workspace(locations, store)
    binding = {"label": "A", "port": 5501}
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(mcp_server, "read_binding", lambda *_: (binding, locations))
    monkeypatch.setattr(mcp_server, "verify_process", lambda _: None)
    server = FastMCP("looping-public-contract")
    register(server, SimpleNamespace(retrieval_store=store))
    asyncio.run(mcp_server.configure_project_context(server,
        SimpleNamespace(session="unused", token="a" * 32), binding, locations,
        sender=lambda _: "{}", runtime=SimpleNamespace(workspace=workspace)))

    async def run():
        async with Client(server) as client:
            async def call(name, **arguments):
                result = await client.call_tool(name, arguments)
                return json.loads(result.content[0].text)
            created = await call("create_plan", title="Review", goal="Inspect", scope="inspection")
            pid = created["plan"]["plan_id"]
            assert created["plan"]["loop_no"] == 0
            await call("update_plan", plan_id=pid, goal="Inspect access")
            before = await call("get_phase_plan_step", include_details=True, plan_id=pid)
            sid = before["plan"]["steps"][0]["step_id"]
            first = await call("execute_looping", plan_id=pid, feedback="Review access", artifact_name="review")
            assert (first["loop_no"], first["revision"]) == (1, 1)
            assert first["artifact_dir"].endswith("/01")
            assert first["feedback"] == "Review access"
            assert "완료한 작업은 반복하지 않고" in first["next_step_guide"]
            assert "시각적 근거" in first["next_step_guide"]
            assert "policy_tool" not in first
            assert all(s["status"] == "pending" for s in first["steps"])
            updated = await call("update_step", plan_id=pid, step_id=sid, loop_no=1,
                                 status="completed", output_refs={"add": [first["artifact_dir"] + "/result.json"]})
            assert updated["plan"]["revision"] == 2
            resumed = await call("execute_looping", plan_id=pid, resume=True)
            assert (resumed["loop_no"], resumed["revision"]) == (1, 2)
            assert "사용자가 결정" in resumed["policy_reminder"]
            assert "시각적 근거" in resumed["next_step_guide"]
            second = await call("execute_looping", plan_id=pid)
            assert (second["loop_no"], second["revision"]) == (2, 1)
            assert second["artifact_dir"].endswith("/02")
            assert second["steps"][0]["step_id"] == sid
            assert second["steps"][0]["status"] == "pending"
            assert second["steps"][0]["output_refs"] == []
            old = await call("get_phase_plan_step", include_details=True, plan_id=pid, step_id=sid, loop_no=1)
            assert old["status"] == "completed" and old["loop_no"] == 1
            assert old["step"]["output_refs"] == [first["artifact_dir"] + "/result.json"]
            refused = await call("update_step", plan_id=pid, step_id=sid, loop_no=1, status="running")
            assert refused["status"] == "error"
            history = await call("list_plan_revisions", plan_id=pid, loop_no=1, step_id=sid)
            assert [(r["loop_no"],r["revision"]) for r in history["revisions"]] == [(1,2)]
            baseline = await call("get_phase_plan_step", include_details=True, plan_id=pid, loop_no=0, revision=1)
            assert baseline["plan"]["goal"] == "Inspect"
    asyncio.run(run())
