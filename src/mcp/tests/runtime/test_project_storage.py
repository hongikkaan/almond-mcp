from contextlib import closing
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

import pytest

from almond_mcp.retrieval_store import AlmondStore
from project import ExclusiveFile, SharedStorageLease, connection_paths, write_json
from shared_store import StoreGate
from storage_cleanup import cleanup_retired_sessions, migrate_database
from workspace import Workspace


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Almond runtime uses Windows file leases")


def _connect(root, model_name, slot):
    model = root / model_name
    model.touch()
    token = uuid4().hex
    return token, connection_paths(model, slot, token, create=True)


def test_retiring_one_connection_keeps_the_other_and_shared_work(tmp_path):
    token_a, paths_a = _connect(tmp_path, "Lobby.3dm", "A")
    _, paths_b = _connect(tmp_path, "Courtyard.3dm", "B")
    storage = Path(paths_a["storage"])
    proof = "the drawing belongs to this Loop"

    with SharedStorageLease(storage), SharedStorageLease(storage), StoreGate(storage):
        first = Workspace(paths_a, AlmondStore(paths_a["state_db"]))
        second = Workspace(paths_b, AlmondStore(paths_b["state_db"]))
        plan_id = first.store.create_plan(goal="Record the lobby proposal")["plan_id"]
        first.select(plan_id, artifact_name="261126_lobby")
        second.select(plan_id)
        first.execute_looping(plan_id)

        drawing = first.artifact_path() / "section.txt"
        drawing.parent.mkdir(parents=True)
        drawing.write_text(proof, encoding="utf-8")
        assert second.store.get_plan(plan_id)["loop_no"] == 1
        assert second.current()["loop_no"] == 0
        with pytest.raises(ValueError, match="read-only"):
            second.artifact_path()

        scratch_a, scratch_b = Path(paths_a["call_root"]), Path(paths_b["call_root"])
        for scratch in (scratch_a, scratch_b):
            scratch.mkdir(parents=True)
            (scratch / "operation.txt").write_text(scratch.name, encoding="utf-8")
        write_json(paths_a["ready_path"], {"valid": False})
        assert cleanup_retired_sessions(storage) == [token_a]

        assert not scratch_a.exists()
        assert (scratch_b / "operation.txt").read_text(encoding="utf-8") == scratch_b.name
        assert drawing.read_text(encoding="utf-8") == proof
        second.select(plan_id)
        assert second.artifact_path() == drawing.parent


def test_conflicting_artifact_rename_preserves_both_folders_and_references(tmp_path):
    _, paths = _connect(tmp_path, "Study.3dm", "A")
    store = AlmondStore(paths["state_db"])
    workspace = Workspace(paths, store)
    owner = store.create_plan(goal="Prepare the drawing")["plan_id"]
    reader = store.create_plan(goal="Review the drawing")["plan_id"]
    original = workspace.select(owner, artifact_name="261126_draft")["artifact_dir"]
    folder = workspace.artifact_path()
    folder.mkdir(parents=True)
    (folder / "section.txt").write_text("owned drawing", encoding="utf-8")
    reference = f"{original}/section.txt"
    store.update_plan(reader, artifact_refs=[reference])

    destination = folder.with_name("261126_review")
    destination.mkdir()
    (destination / "notes.txt").write_text("existing review", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        workspace.rename(destination.name)
    assert store.get_plan(reader)["artifact_refs"] == [reference]
    assert (folder / "section.txt").read_text(encoding="utf-8") == "owned drawing"
    assert (destination / "notes.txt").read_text(encoding="utf-8") == "existing review"

    renamed = workspace.rename("261126_issued")["artifact_dir"]
    assert not folder.exists()
    assert (tmp_path / renamed / "section.txt").read_text(encoding="utf-8") == "owned drawing"
    assert store.get_plan(reader)["artifact_refs"] == [f"{renamed}/section.txt"]


def test_legacy_database_migrates_exclusively_and_refuses_a_collision(tmp_path):
    token, paths = _connect(tmp_path, "Existing.3dm", "A")
    storage = Path(paths["storage"])
    legacy, current = storage / "DB", Path(paths["state_db"])
    with closing(sqlite3.connect(legacy)) as writer, writer:
        writer.execute('CREATE TABLE notes(label TEXT)')
        writer.execute('INSERT INTO notes VALUES ("existing survey")')

    with SharedStorageLease(storage), StoreGate(storage):
        with pytest.raises(OSError):
            ExclusiveFile(storage / "mcp.lock")
        with pytest.raises(TimeoutError):
            with StoreGate(storage, timeout=0):
                pytest.fail("A second connection entered the project write gate")
        assert not current.exists()

    with StoreGate(storage, timeout=0):
        assert migrate_database(paths, token)
        assert not legacy.exists()
        with closing(sqlite3.connect(current)) as migrated:
            assert migrated.execute("SELECT label FROM notes").fetchall() == [("existing survey",)]

        legacy.write_bytes(b"conflicting old database")
        before = current.read_bytes()
        with pytest.raises(RuntimeError, match="Both scene.sqlite3 and DB exist"):
            migrate_database(paths, token)
        assert legacy.read_bytes() == b"conflicting old database"
        assert current.read_bytes() == before
