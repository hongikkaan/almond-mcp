"""Phase filename arrays retain identity and roll back failed edits."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


def test_legacy_file_relation_migrates_without_rewriting_plans(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    store = AlmondStore(path)
    phase = store.create_phase("Existing", file_name="existing.3dm")
    plan = store.create_plan("Existing plan", phase_id=phase["phase_id"])
    with store._connect() as db:
        snapshots = list(map(tuple, db.execute("SELECT * FROM generation_plan_revisions")))
        db.execute("DROP TRIGGER phase_file_legacy_insert")
        db.execute("DROP TRIGGER phase_file_legacy_update")
        db.execute("DROP TABLE generation_phase_files")
    reopened = AlmondStore(path)
    assert reopened.get_phase(phase["phase_id"])["file_names"] == ["existing.3dm"]
    assert reopened.get_phase(phase["phase_id"])["project_file_id"] == phase["project_file_id"]
    assert reopened.get_plan(plan["plan_id"]) == plan
    with reopened._connect() as db:
        assert list(map(tuple, db.execute("SELECT * FROM generation_plan_revisions"))) == snapshots
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert AlmondStore(path).get_phase(phase["phase_id"]) == reopened.get_phase(phase["phase_id"])


def test_phase_array_edits_are_atomic_and_preserve_unrelated_files(tmp_path):
    store = AlmondStore(tmp_path / "files.sqlite3")
    phase = store.create_phase("Work", file_name=["site.3dm", "building.3dm", "SITE.3dm"])
    pid = phase["phase_id"]
    assert phase["file_names"] == ["site.3dm", "building.3dm"]
    assert store.edit_phase(pid, description="Keep both").record["file_names"] == phase["file_names"]
    same = store.edit_phase(pid, file_name=["site.3dm", "building.3dm"])
    assert not same.changed
    files = store.list_project_files()
    with pytest.raises(ValueError):
        store.edit_phase(pid, name="Must roll back", file_name=["new.3dm", "../bad.3dm"])
    assert store.list_project_files() == files
    assert store.get_phase(pid)["name"] == "Work"
    cleared = store.edit_phase(pid, file_name=[])
    assert cleared.changed and cleared.record["file_names"] == []
    assert cleared.record["project_file_id"] is None
    assert store.list_project_files() == files
    assert AlmondStore(store.database_path).get_phase(pid)["file_names"] == []


def test_ambiguous_file_names_never_pick_a_model_or_partially_register(tmp_path):
    store = AlmondStore(tmp_path / "ambiguous.sqlite3")
    phase = store.create_phase("Keep", file_name="old.3dm")
    with store._connect() as db:
        db.executemany("INSERT INTO project_files VALUES(?,?)", [("a", "same.3dm"), ("b", "same.3dm")])
    before = store.list_project_files()
    with pytest.raises(ValueError, match="matches several"):
        store.edit_phase(phase["phase_id"], file_name=["new.3dm", "same.3dm"])
    assert store.get_phase(phase["phase_id"]) == phase
    assert store.list_project_files() == before


