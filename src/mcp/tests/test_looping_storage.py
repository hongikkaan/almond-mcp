"""Loop history, atomic numbering and managed file isolation through public facades."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.managed_paths import project_path
from project import connection_paths
from workspace import Workspace


@pytest.fixture
def workspace(tmp_path):
    model = tmp_path / "model.3dm"
    model.touch()
    locations = connection_paths(model, "A", "a" * 32, create=True)
    return Workspace(locations, AlmondStore(locations["state_db"]))


def test_zero_is_not_a_synthetic_loop_and_resume_requires_execution(workspace):
    store = workspace.store
    plan = store.create_plan("Prepare")
    pid = plan["plan_id"]
    with store._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM generation_plan_loops").fetchone()[0] == 0
    with pytest.raises(ValueError, match="No Loop"):
        workspace.execute_looping(pid, resume=True)
    assert store.get_plan(pid) == plan
    assert not workspace.state_path.exists()
    store.update_plan(pid, goal="Prepare updated")
    selected = workspace.select(pid)
    assert selected["loop_no"] == 0 and not selected["artifact_dir"].endswith("/00")
    before = store.list_plan_revisions(pid)["revisions"]
    first = workspace.execute_looping(pid)
    assert (first["loop_no"], first["revision"]) == (1, 1)
    assert store.list_plan_revisions(pid, loop_no=0)["revisions"] == before
    with store._connect() as db:
        assert list(map(tuple, db.execute("SELECT loop_no FROM generation_plan_loops"))) == [(1,)]


def test_revision_numbers_are_transactional_and_loop_scoped(workspace, monkeypatch):
    store = workspace.store
    plan = store.create_plan("Numbering")
    pid, sid = plan["plan_id"], plan["steps"][0]["step_id"]
    workspace.execute_looping(pid)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda index: store.update_plan(pid, goal=f"Change {index}"), range(8)))
    assert sorted(r["revision"] for r in results) == list(range(2, 10))
    current = store.get_plan(pid)
    assert store.update_plan(pid, goal=current["goal"])["revision"] == 9
    with pytest.raises(ValueError, match="Supply loop_no"):
        store.update_plan(pid, expected_revision=9, goal="Must reject")
    store.update_plan(pid, expected_revision=9, loop_no=1, goal="Guarded")
    original = store._record_generation_revision
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("after snapshot")
    with monkeypatch.context() as patch:
        patch.setattr(store, "_record_generation_revision", fail)
        with pytest.raises(RuntimeError, match="after snapshot"):
            store.update_plan_step(pid, sid, status="running")
        with pytest.raises(RuntimeError, match="after snapshot"):
            store.execute_looping(pid)
    assert store.get_step(pid, sid)["step"]["status"] == "pending"
    assert store.get_plan(pid)["revision"] == 10
    assert store.get_plan(pid)["loop_no"] == 1
    assert store.execute_looping(pid)["revision"] == 1
    with pytest.raises(ValueError, match="Only current"):
        store.update_plan(pid, loop_no=1, expected_revision=1, goal="Stale")
    history = store.list_plan_revisions(pid)["revisions"]
    assert len({(r["loop_no"], r["revision"]) for r in history}) == len(history)
    with store._connect() as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_current_loop_overwrites_but_prior_paths_and_selection_are_read_only(workspace):
    store = workspace.store
    pid = store.create_plan("Files")["plan_id"]
    first = workspace.execute_looping(pid)
    old = workspace.artifact_path()
    old.mkdir(parents=True)
    (old / "result.txt").write_text("draft", encoding="utf-8")
    (workspace.artifact_path() / "result.txt").write_text("reviewed", encoding="utf-8")
    assert (old / "result.txt").read_text(encoding="utf-8") == "reviewed"
    store.execute_looping(pid)
    assert workspace.current()["read_only"] is True
    with pytest.raises(ValueError, match="read-only"):
        workspace.artifact_path()
    with pytest.raises(ValueError, match="Only current"):
        workspace.select(pid, loop_no=1)
    second = workspace.select(pid, loop_no=2)
    assert second["artifact_dir"].endswith("/02")
    new = workspace.artifact_path()
    new.mkdir()
    (new / "result.txt").write_text("new pass", encoding="utf-8")
    assert (old / "result.txt").read_text(encoding="utf-8") == "reviewed"
    for value in ("../01/result.txt", str(old / "result.txt")):
        with pytest.raises(ValueError, match="relative path"):
            project_path(value, base=new)
    with pytest.raises(ValueError, match="Cannot rename"):
        workspace.rename("renamed", pid)
    assert store.get_plan(pid, loop_no=1)["loop_artifact_dir"] == first["artifact_dir"]


def test_resume_records_changed_feedback_only_and_preserves_progress(workspace):
    store = workspace.store
    plan = store.create_plan("Feedback", scope="inspection")
    pid, sid = plan["plan_id"], plan["steps"][0]["step_id"]
    workspace.execute_looping(pid, feedback="First")
    store.update_plan(pid, status="paused")
    store.update_plan_step(pid, sid, status="completed", output_refs=["report done"])
    revision = store.get_plan(pid)["revision"]
    resumed = workspace.execute_looping(pid, resume=True, feedback="Clarification")
    assert resumed["loop_no"] == 1 and resumed["revision"] == revision + 1
    assert resumed["plan_status"] == "paused"
    assert resumed["steps"][0]["output_refs"] == ["report done"]
    assert resumed["next_step_id"] == plan["steps"][1]["step_id"]
    assert workspace.execute_looping(pid, resume=True)["revision"] == revision + 1
    assert workspace.execute_looping(pid, resume=True, feedback="Clarification")["revision"] == revision + 1
    next_loop = workspace.execute_looping(pid)
    assert next_loop["feedback"] == "" and next_loop["plan_status"] == "paused"
    assert next_loop["previous_loop"]["steps"][0]["output_refs"] == ["report done"]
    assert next_loop["steps"][0]["output_refs"] == []


def test_renaming_a_pre_execution_folder_cannot_break_other_past_loops(workspace):
    store = workspace.store
    owner = store.create_plan("Source")
    workspace.select(owner["plan_id"])
    folder = workspace.artifact_path()
    folder.mkdir(parents=True)
    (folder / "input.txt").write_text("source", encoding="utf-8")
    peer = store.create_plan("Consumer")
    pid, sid = peer["plan_id"], peer["steps"][0]["step_id"]
    workspace.execute_looping(pid)
    store.update_plan_step(pid, sid, input_refs=[str(folder / "input.txt")])
    workspace.execute_looping(pid)
    with pytest.raises(ValueError, match="past Loop"):
        workspace.rename("new_source", owner["plan_id"])
    assert (folder / "input.txt").read_text(encoding="utf-8") == "source"


def test_new_loop_does_not_reuse_an_unowned_existing_numbered_folder(workspace):
    plan = workspace.store.create_plan("Existing files")
    pid = plan["plan_id"]
    workspace.select(pid)
    folder = workspace.artifact_path() / "01"
    folder.mkdir(parents=True)
    (folder / "result.txt").write_text("pre-execution evidence", encoding="utf-8")
    before = workspace.store.get_plan(pid)
    with pytest.raises(ValueError, match="already exists"):
        workspace.execute_looping(pid)
    assert workspace.store.get_plan(pid) == before
    assert (folder / "result.txt").read_text(encoding="utf-8") == "pre-execution evidence"


def test_loop_advance_waits_for_existing_native_artifact_completion(workspace):
    import asyncio
    from types import SimpleNamespace
    from project import write_json
    from shared_store import ProjectRuntime

    pid = workspace.store.create_plan("Pending writer")["plan_id"]
    workspace.execute_looping(pid)
    before = workspace.store.get_plan(pid)
    write_json(workspace.state_path.with_name("worker.json"), {"pid": 1, "process_start_ticks": "1"})
    peer = workspace.state_path.parent.parent / ("b" * 32) / "artifact-write.json"
    peer.parent.mkdir()
    operation = {"token": "b" * 32, "artifact_write": True, "state": "unconfirmed"}
    write_json(peer, operation)
    runtime = ProjectRuntime(SimpleNamespace(token="a" * 32), {}, workspace.locations, check_owner=False)
    runtime.workspace = workspace
    runtime.validate = lambda: None  # Disposable fixture, no live Rhino ownership.
    class Message:
        name = "plan_03-execute_looping"
        arguments = {"plan_id": pid}
        def model_copy(self, update):
            return self
    class Context:
        message = Message()
        def copy(self, **updates):
            return self
    async def start(context):
        return workspace.execute_looping(pid)
    with pytest.raises(RuntimeError, match="artifact write"):
        asyncio.run(runtime.on_call_tool(Context(), start))
    assert workspace.store.get_plan(pid) == before
    write_json(peer, dict(operation, state="completed"))
    assert asyncio.run(runtime.on_call_tool(Context(), start))["loop_no"] == 2
