"""Plan folder tools keep durable files separate from connection scratch."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from almond_mcp.retrieval_store import AlmondStore
from project import connection_paths, write_json
from workspace import Workspace


@pytest.fixture
def workspace(tmp_path):
    model = tmp_path / "model.3dm"
    model.touch()
    locations = connection_paths(model, "A", "a" * 32, create=True)
    return Workspace(locations, AlmondStore(locations["state_db"]))


def test_select_and_rename_keep_file_and_current_references_together(workspace):
    store = workspace.store
    owner = store.create_plan(goal="Entrance", scope="component")
    selected = workspace.select(owner["plan_id"], artifact_name="261104_entrance")
    original = ".almond/produced/261104_entrance"
    assert selected["artifact_dir"] == original
    folder = workspace.artifact_path()
    folder.mkdir(parents=True)
    (folder / "drawing.pdf").write_bytes(b"drawing")
    peer = store.create_plan(goal="Reference", scope="component")
    with store._connect() as db:
        db.execute("UPDATE generation_plans SET artifact_refs_json=? WHERE plan_id=?",
                   (json.dumps([original + "/drawing.pdf", "https://example.com/" + original]), peer["plan_id"]))
        db.execute("UPDATE generation_loop_steps SET input_refs_json=?,output_refs_json=? WHERE plan_id=? AND loop_no=0 AND step_id=?",
                   (json.dumps([str(folder / "drawing.pdf")]), json.dumps([original.upper() + "/drawing.pdf"]), peer["plan_id"], peer["steps"][1]["step_id"]))
        store._record_generation_revision(db, peer["plan_id"], "test_reference")
        history = list(map(tuple, db.execute("SELECT * FROM generation_plan_revisions")))
    renamed = workspace.rename("261104_review")
    target = ".almond/produced/261104_review"
    assert renamed == {"artifact_dir": target, "previous_artifact_dir": original}
    assert not folder.exists()
    assert (workspace.root / target / "drawing.pdf").read_bytes() == b"drawing"
    current = store.get_plan(peer["plan_id"])
    assert current["artifact_refs"] == [target + "/drawing.pdf", "https://example.com/" + original]
    step = next(s for s in current["steps"] if s["step_id"] == peer["steps"][1]["step_id"])
    assert step["input_refs"] == step["output_refs"] == [target + "/drawing.pdf"]
    with store._connect() as db:
        assert set(history) <= set(map(tuple, db.execute("SELECT * FROM generation_plan_revisions")))
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert workspace.select(owner["plan_id"], artifact_name="261104_review")["artifact_dir"] == target


@pytest.mark.parametrize("legacy", ["tmp", ".almond/tmp"])
def test_explicit_rename_migrates_legacy_folder_before_writing(workspace, legacy):
    plan = workspace.store.create_plan(goal="Legacy", scope="component")
    old = legacy + "/261104_legacy"
    folder = workspace.root / old
    folder.mkdir(parents=True)
    (folder / "report.json").write_text("{}")
    with workspace.store._connect() as db:
        db.execute("UPDATE generation_plans SET artifact_dir=? WHERE plan_id=?", (old, plan["plan_id"]))
    write_json(workspace.state_path, {"plan_id": plan["plan_id"]})
    with pytest.raises(ValueError, match="produced"):
        workspace.select(plan["plan_id"])
    with pytest.raises(ValueError, match="produced"):
        workspace.artifact_path()
    result = workspace.rename("261104_legacy", plan["plan_id"])
    assert result["artifact_dir"] == ".almond/produced/261104_legacy"
    assert (workspace.artifact_path() / "report.json").read_text() == "{}"
    assert not folder.exists()


@pytest.mark.parametrize("name", ["../escape", "nested/folder", r"nested\folder", "C:/tmp", "/tmp", ".", "..", "bad:"])
def test_folder_tools_reject_paths(workspace, name):
    plan = workspace.store.create_plan(goal="Validate name")
    with pytest.raises(ValueError):
        workspace.select(plan["plan_id"], artifact_name=name)
    workspace.select(plan["plan_id"], artifact_name="261104_original")
    with pytest.raises(ValueError):
        workspace.rename(name)
    assert workspace.store.get_plan(plan["plan_id"])["artifact_dir"] == ".almond/produced/261104_original"


def test_rename_failure_restores_files_and_database(workspace, monkeypatch):
    plan = workspace.store.create_plan(goal="Rollback")
    before = workspace.select(plan["plan_id"], artifact_name="261104_original")
    folder = workspace.artifact_path()
    folder.mkdir(parents=True)
    (folder / "report.txt").write_text("preserve")
    with workspace.store._connect() as db:
        snapshot = list(db.iterdump())
    def fail(*args):
        raise RuntimeError("injected revision failure")
    monkeypatch.setattr(workspace.store, "_record_generation_revision", fail)
    with pytest.raises(RuntimeError, match="injected"):
        workspace.rename("261104_failed")
    assert (folder / "report.txt").read_text() == "preserve"
    assert not (workspace.root / ".almond/produced/261104_failed").exists()
    with workspace.store._connect() as db:
        assert list(db.iterdump()) == snapshot
    assert workspace.current()["artifact_dir"] == before["artifact_dir"]


@pytest.mark.parametrize("interruption", ["after_move", "after_commit", "conflicting_paths"])
def test_reopen_recovers_rename_after_process_dies_between_move_and_commit(workspace, interruption):
    plan = workspace.store.create_plan(goal="Crash recovery")
    workspace.select(plan["plan_id"], artifact_name="261117_before")
    folder = workspace.artifact_path()
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("preserve")
    code = '''
import json, os, sys
from pathlib import Path
from almond_mcp.retrieval_store import AlmondStore
from workspace import Workspace
locations = json.loads(sys.argv[1])
workspace = Workspace(locations, AlmondStore(locations["state_db"]))
rename = Path.rename
unlink = Path.unlink
def interrupted(source, target):
    result = rename(source, target)
    if source.name == "261117_before" and sys.argv[2] == "after_move":
        os._exit(73)
    return result
def interrupted_unlink(path, *args, **kwargs):
    if path.name == "workspace-rename.json" and sys.argv[2] == "after_commit":
        os._exit(73)
    return unlink(path, *args, **kwargs)
Path.rename = interrupted
Path.unlink = interrupted_unlink
workspace.rename("261117_after")
'''
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    boundary = "after_move" if interruption == "conflicting_paths" else interruption
    child = subprocess.run([sys.executable, "-c", code, json.dumps(workspace.locations), boundary], env=environment)
    assert child.returncode == 73
    other = connection_paths(workspace.locations["model_path"], "B", "b" * 32, create=True)
    reopened = Workspace(other, AlmondStore(other["state_db"]))
    if interruption == "conflicting_paths":
        folder.mkdir()
        (folder / "new.txt").write_text("new external data")
        with pytest.raises(ValueError, match="exactly one owned folder"):
            reopened.select(plan["plan_id"])
        assert (folder / "new.txt").read_text() == "new external data"
        assert (folder.with_name("261117_after") / "keep.txt").read_text() == "preserve"
        return
    expected = "261117_before" if interruption == "after_move" else "261117_after"
    assert reopened.select(plan["plan_id"])["artifact_dir"] == ".almond/produced/" + expected
    assert (reopened.artifact_path() / "keep.txt").read_text() == "preserve"
    assert reopened.rename("261117_after")["artifact_dir"] == ".almond/produced/261117_after"


def test_uncommitted_loop_intent_cannot_claim_another_sessions_committed_loop(workspace, monkeypatch):
    plan = workspace.store.create_plan(goal="Two sessions")
    execute = workspace.store.execute_looping
    def fail_before_commit(*args, **kwargs):
        raise RuntimeError("injected transaction failure")
    monkeypatch.setattr(workspace.store, "execute_looping", fail_before_commit)
    with pytest.raises(RuntimeError, match="transaction failure"):
        workspace.execute_looping(plan["plan_id"], feedback="same feedback")
    monkeypatch.setattr(workspace.store, "execute_looping", execute)
    other = connection_paths(workspace.locations["model_path"], "B", "b" * 32, create=True)
    peer = Workspace(other, AlmondStore(other["state_db"]))
    assert peer.execute_looping(plan["plan_id"], feedback="same feedback")["loop_no"] == 1
    assert workspace.execute_looping(plan["plan_id"], feedback="same feedback")["loop_no"] == 2


@pytest.mark.parametrize("interruption", ["io_error", "process_exit"])
def test_retry_loop_after_selection_publication_failure_does_not_advance_twice(workspace, monkeypatch, interruption):
    import workspace as module
    plan = workspace.store.create_plan(goal="Durable Loop")
    publish = module.write_json
    def fail_selection(path, value):
        if path == workspace.state_path and value.get("loop_no") == 1:
            raise OSError("injected work.json failure")
        publish(path, value)
    if interruption == "io_error":
        monkeypatch.setattr(module, "write_json", fail_selection)
        with pytest.raises(OSError, match="work.json failure"):
            workspace.execute_looping(plan["plan_id"], feedback="review")
        monkeypatch.setattr(module, "write_json", publish)
    else:
        code = '''
import json, os, sys, workspace
from almond_mcp.retrieval_store import AlmondStore
locations = json.loads(sys.argv[1])
work = workspace.Workspace(locations, AlmondStore(locations["state_db"]))
publish = workspace.write_json
def interrupted(path, value):
    if path == work.state_path and value.get("loop_no") == 1:
        os._exit(75)
    publish(path, value)
workspace.write_json = interrupted
work.execute_looping(sys.argv[2], feedback="review")
'''
        child = subprocess.run([sys.executable, "-c", code, json.dumps(workspace.locations), plan["plan_id"]],
            env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)))
        assert child.returncode == 75
    reopened = Workspace(workspace.locations, AlmondStore(workspace.locations["state_db"]))
    result = reopened.execute_looping(plan["plan_id"], feedback="review")
    assert result["loop_no"] == 1
    assert reopened.current()["loop_no"] == 1
    assert reopened.store.get_plan(plan["plan_id"])["loop_no"] == 1


def test_folder_names_cannot_claim_another_plans_folder(workspace):
    first = workspace.store.create_plan(goal="First")
    second = workspace.store.create_plan(goal="Second")
    workspace.select(first["plan_id"], artifact_name="261104_Reserved")
    with pytest.raises(ValueError, match="already in use"):
        workspace.select(second["plan_id"], artifact_name="261104_reserved")
    workspace.select(second["plan_id"], artifact_name="261104_second")
    with pytest.raises(ValueError, match="belongs to another"):
        workspace.rename("261104_reserved")


def test_legacy_plan_does_not_block_bound_model_save(workspace):
    import asyncio
    from types import SimpleNamespace
    from shared_store import ProjectRuntime

    plan = workspace.store.create_plan(goal="Legacy")
    with workspace.store._connect() as db:
        db.execute("UPDATE generation_plans SET artifact_dir='tmp/legacy' WHERE plan_id=?", (plan["plan_id"],))
    write_json(workspace.state_path, {"plan_id": plan["plan_id"]})
    write_json(workspace.state_path.with_name("worker.json"), {"pid": 1, "process_start_ticks": "1"})
    runtime = ProjectRuntime(SimpleNamespace(token="a" * 32), {}, workspace.locations, check_owner=False)
    runtime.workspace = workspace
    runtime.validate = lambda: None  # No live Rhino in this fixture.
    class Message:
        name = "script_04-save_document"
        arguments = {}
        def model_copy(self, update):
            return self
    class Context:
        message = Message()
        def copy(self, **updates):
            return self
    called = []
    async def save(context):
        called.append(context.message.name)
        return {"status": "success"}
    assert asyncio.run(runtime.on_call_tool(Context(), save)) == {"status": "success"}
    assert called == ["script_04-save_document"]
