"""Plan folder tools keep durable files separate from connection scratch."""
import json

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
        name = "save_rhino_document"
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
    assert called == ["save_rhino_document"]
