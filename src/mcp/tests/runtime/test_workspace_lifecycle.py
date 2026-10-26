"""Real SQLite/filesystem checks for reusable work folders and owned cleanup."""
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import uuid

import pytest

from almond_mcp.retrieval_store import AlmondStore
from project import connection_paths, process_start_ticks, write_json, ExclusiveFile
from storage_cleanup import cleanup_retired_sessions, migrate_database, remove_owned_tree
from workspace import Workspace


@pytest.fixture
def work(tmp_path, monkeypatch):
    model = tmp_path / "test.3dm"
    model.write_bytes(b"PATH FIXTURE ONLY")
    locations = connection_paths(model, "A", uuid.uuid4().hex, create=True)
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    store = AlmondStore(locations["state_db"])
    return Workspace(locations, store)


def test_two_workers_reuse_plan_folder_and_rename_current_refs_only(work):
    plan = work.store.create_plan("Grid", scope="component")
    first = work.select(plan["plan_id"], "model", "261026_grid")
    original = work.root / first["artifact_dir"]
    assert not original.exists()
    locations = connection_paths(work.locations["model_path"], "B", uuid.uuid4().hex, create=True)
    other = Workspace(locations, work.store)
    assert other.select(plan["plan_id"])["artifact_dir"] == first["artifact_dir"]
    original.mkdir(parents=True)
    (original / "result.txt").write_text("keep", encoding="utf-8")
    snapshot = work.store.update_plan_step(plan["plan_id"], "model", "paused", output_refs=[first["artifact_dir"] + "/result.txt"])
    referenced = work.store.create_plan("Other task", depends_on=[plan["plan_id"]])
    work.store.update_plan(referenced["plan_id"], artifact_refs=[first["artifact_dir"] + "/result.txt"])
    changed = work.rename("261026_review")
    assert changed["artifact_dir"] == "tmp/261026_review"
    assert (work.root / "tmp/261026_review/result.txt").read_text() == "keep"
    assert not original.exists()
    assert other.current()["artifact_dir"] == "tmp/261026_review"
    assert work.store.get_plan(plan["plan_id"])["steps"][2]["output_refs"] == ["tmp/261026_review/result.txt"]
    assert work.store.get_plan(referenced["plan_id"])["artifact_refs"] == ["tmp/261026_review/result.txt"]
    assert work.store.get_plan(plan["plan_id"], snapshot["revision"]) == snapshot


def test_failed_ref_update_rolls_back_folder_move_and_metadata(work, monkeypatch):
    plan = work.store.create_plan("Grid")
    selected = work.select(plan["plan_id"], artifact_name="261026_original")
    directory = work.artifact_path()
    directory.mkdir(parents=True)
    (directory / "keep.txt").write_text("keep")
    def fail(*args):
        raise RuntimeError("revision write failed")
    monkeypatch.setattr(work.store, "_record_generation_revision", fail)
    with pytest.raises(RuntimeError, match="revision write"):
        work.rename("261026_destination")
    assert (directory / "keep.txt").read_text() == "keep"
    assert not (directory.parent / "261026_destination").exists()
    assert work.current() == selected


@pytest.mark.parametrize("reference", [
    "./tmp/261026_original/result.txt", "TMP/261026_ORIGINAL/result.txt",
    r".\tmp\261026_original\result.txt", "tmp/261026_original/sub/../result.txt",
])
def test_rename_normalizes_windows_file_refs_and_preserves_nonfile_refs(work, reference):
    plan = work.store.create_plan("Grid", scope="component")
    work.select(plan["plan_id"], "model", "261026_original")
    original = work.artifact_path()
    original.mkdir(parents=True)
    (original / "result.txt").write_text("keep")
    unchanged = ["https://example.com/tmp/261026_original/result.txt",
                 "almond://tmp/261026_original/result.txt", "component:part",
                 "tmp/261026_original-extra/result.txt"]
    absolute = str(original / "result.txt").upper()
    work.store.update_plan(plan["plan_id"], artifact_refs=[reference, absolute, *unchanged])
    work.store.update_plan_step(plan["plan_id"], "model", "paused",
                               input_refs=[reference], output_refs=[reference])
    work.rename("261026_renamed")
    updated = work.store.get_plan(plan["plan_id"])
    assert updated["artifact_refs"] == ["tmp/261026_renamed/result.txt",
                                        "tmp/261026_renamed/RESULT.TXT", *unchanged]
    step = next(item for item in updated["steps"] if item["step_id"] == "model")
    assert step["input_refs"] == step["output_refs"] == ["tmp/261026_renamed/result.txt"]


def test_rename_does_not_equate_different_windows_unicode_names(work):
    plan = work.store.create_plan("Unicode folder")
    work.select(plan["plan_id"], artifact_name="261026_straße")
    directory = work.artifact_path()
    directory.mkdir(parents=True)
    assert not (directory.parent / "261026_strasse").exists()
    distinct = "tmp/261026_strasse/result.txt"
    work.store.update_plan(plan["plan_id"], artifact_refs=[distinct])
    work.rename("261026_renamed")
    assert work.store.get_plan(plan["plan_id"])["artifact_refs"] == [distinct]


@pytest.mark.parametrize("name", ["../escape", "C:/escape", "foo/bar", "bad:name", ".."])
def test_folder_names_cannot_escape_project(work, name):
    plan = work.store.create_plan("Grid")
    with pytest.raises(ValueError):
        work.select(plan["plan_id"], artifact_name=name)
    assert work.store.get_plan(plan["plan_id"])["artifact_dir"] == ""


def test_db_rename_preserves_wal_data_without_creating_copies(tmp_path):
    storage = tmp_path / ".almond"
    (storage / ".sessions").mkdir(parents=True)
    old = storage / "scene.sqlite3"
    with closing(sqlite3.connect(old)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE evidence(value TEXT)")
        db.execute("INSERT INTO evidence VALUES('retain')")
        db.commit()
    assert migrate_database({"storage": str(storage)}, "own")
    assert not old.exists()
    with closing(sqlite3.connect(storage / "DB")) as db:
        assert db.execute("SELECT value FROM evidence").fetchone()[0] == "retain"
    assert not migrate_database({"storage": str(storage)}, "own")


def test_db_conflict_or_live_worker_blocks_migration_without_touching_either_file(tmp_path):
    storage = tmp_path / ".almond"
    session = storage / ".sessions" / uuid.uuid4().hex
    session.mkdir(parents=True)
    old, target = storage / "scene.sqlite3", storage / "DB"
    old.write_bytes(b"old-marker")
    target.write_bytes(b"new-marker")
    with pytest.raises(RuntimeError, match="Both"):
        migrate_database({"storage": str(storage)}, "own")
    assert old.read_bytes() == b"old-marker" and target.read_bytes() == b"new-marker"
    target.unlink()
    write_json(session / "worker.json", {"pid": os.getpid(), "process_start_ticks": process_start_ticks(os.getpid())})
    with pytest.raises(RuntimeError, match="Another worker"):
        migrate_database({"storage": str(storage)}, "own")
    assert old.read_bytes() == b"old-marker" and not target.exists()


def test_cleanup_uses_connection_and_lock_lifetimes_not_work_status(work):
    storage = Path(work.locations["storage"])
    session = Path(work.locations["session_dir"])
    token = session.name
    identity = {"pid": os.getpid(), "process_start_ticks": process_start_ticks(os.getpid())}
    write_json(session / "ready.json", {**identity, "valid": False})
    write_json(session / "native.json", {"phase": "stopped", "pending": 0})
    write_json(session / "worker.json", {**identity, "closed": True})
    write_json(session / "launch.json", identity)
    write_json(session / "operation.json", {"state": "unconfirmed"})
    plan = work.store.create_plan("Never completed")
    scratch = Path(work.locations["call_root"]) / uuid.uuid4().hex
    scratch.mkdir(parents=True)
    (scratch / "temporary.txt").write_text("scratch")
    with ExclusiveFile(session / "rhino.lock"):
        assert cleanup_retired_sessions(storage) == []
        assert session.exists()
    assert cleanup_retired_sessions(storage) == [token]
    assert not session.exists() and not scratch.exists()
    assert work.store.get_plan(plan["plan_id"])["status"] == "pending"


def test_active_owner_and_unknown_files_are_retained(work):
    storage = Path(work.locations["storage"])
    session = Path(work.locations["session_dir"])
    write_json(session / "ready.json", {"pid": os.getpid(), "process_start_ticks": process_start_ticks(os.getpid()), "valid": True})
    assert cleanup_retired_sessions(storage) == []
    write_json(session / "ready.json", {"valid": False})
    (session / "user-notes.txt").write_text("keep")
    assert cleanup_retired_sessions(storage) == []
    assert (session / "user-notes.txt").read_text() == "keep"
    with pytest.raises(ValueError):
        remove_owned_tree(storage, storage)


def test_orphan_destination_sidecars_block_database_migration(tmp_path):
    storage = tmp_path / ".almond"
    storage.mkdir()
    (storage / "scene.sqlite3").write_bytes(b"preserve old")
    (storage / "DB-wal").write_bytes(b"preserve journal")
    with pytest.raises(RuntimeError, match="sidecar"):
        migrate_database({"storage": str(storage)}, "own")
    assert (storage / "scene.sqlite3").read_bytes() == b"preserve old"
    assert (storage / "DB-wal").read_bytes() == b"preserve journal"
