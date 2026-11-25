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
    store.upsert_project_file("existing.3dm")
    phase = store.create_phase("Existing", file_name="existing.3dm")
    plan = store.create_plan("Existing plan", phase_id=phase["phase_id"])
    with store._connect() as db:
        snapshots = list(map(tuple, db.execute("SELECT * FROM generation_plan_revisions")))
        db.execute("DROP TABLE generation_phase_files")
    reopened = AlmondStore(path)
    assert reopened.get_phase(phase["phase_id"])["file_names"] == ["existing.3dm"]
    assert reopened.get_phase(phase["phase_id"])["file_name"] == phase["file_name"]
    assert reopened.get_plan(plan["plan_id"]) == plan
    with reopened._connect() as db:
        assert list(map(tuple, db.execute("SELECT * FROM generation_plan_revisions"))) == snapshots
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert AlmondStore(path).get_phase(phase["phase_id"]) == reopened.get_phase(phase["phase_id"])


def test_phase_array_edits_are_atomic_and_preserve_unrelated_files(tmp_path):
    store = AlmondStore(tmp_path / "files.sqlite3")
    for name in ("site.3dm", "building.3dm", "new.3dm"):
        store.upsert_project_file(name)
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
    assert cleared.record["file_name"] == ""
    assert store.list_project_files() == files
    assert AlmondStore(store.database_path).get_phase(pid)["file_names"] == []


def test_unknown_file_name_cannot_partially_replace_phase_links_or_register_itself(tmp_path):
    store = AlmondStore(tmp_path / "ambiguous.sqlite3")
    store.upsert_project_file("old.3dm")
    store.upsert_project_file("new.3dm")
    phase = store.create_phase("Keep", file_name="old.3dm")
    before = store.list_project_files()
    with pytest.raises(ValueError, match="not registered"):
        store.edit_phase(phase["phase_id"], file_name=["new.3dm", "absent.3dm"])
    assert store.get_phase(phase["phase_id"]) == phase
    assert store.list_project_files() == before


def test_phase_files_use_first_windows_name_match_and_request_error_order(tmp_path):
    store = AlmondStore(tmp_path / "files.sqlite3")
    store.upsert_project_file("Site.3dm")
    with store._connect() as db:
        db.execute("INSERT INTO project_files(file_name,registered) VALUES ('Å.3dm',0),('å.3dm',1)")

    # SQLite NOCASE permits both spellings, but the first Windows match decides.
    with pytest.raises(ValueError, match=r"Project file 'å\.3dm' is not registered"):
        store.create_phase("First match", file_name=["site.3dm", "å.3dm", "../bad.3dm"])
    assert store.upsert_project_file("å.3dm")["file_name"] == "Å.3dm"

    phase = store.create_phase("Files", file_name=[" å.3dm ", "site.3dm", "Å.3dm"])
    assert phase["file_names"] == ["Å.3dm", "Site.3dm"]
    with pytest.raises(ValueError, match="filename string or an array"):
        store.edit_phase(phase["phase_id"], file_name=["missing.3dm", " "])
    assert store.get_phase(phase["phase_id"]) == phase


