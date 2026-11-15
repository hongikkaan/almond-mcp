"""Step decisions remain separate from file refs and local to a Plan Loop."""
import json
import sqlite3

import pytest

from almond_mcp.features.planning.updates import StringListPatch
from almond_mcp.retrieval_store import AlmondStore


@pytest.fixture
def record(tmp_path):
    path = tmp_path / "decisions.sqlite3"
    store = AlmondStore(path)
    plan = store.create_plan("Review entrance alternatives", scope="component")
    return path, store, plan["plan_id"], plan["steps"][1]["step_id"]


def test_empty_creation_persisted_text_and_explicit_clear(record):
    path, store, pid, sid = record
    plan = store.get_plan(pid)
    assert all((step["takeaways"], step["design_rationale"]) == ("", "") for step in plan["steps"])
    text = "  Keep the entrance accessible.\nAvoid the rejected stair option.\n"
    saved = store.update_plan_step(pid, sid, takeaways=text, design_rationale="Level entry preserves access.")
    assert saved["revision"] == plan["revision"] + 1
    reopened = AlmondStore(path)
    step = reopened.get_step(pid, sid)["step"]
    assert step["takeaways"] == text
    assert step["design_rationale"] == "Level entry preserves access."
    assert step["input_refs"] == step["output_refs"] == []
    assert reopened.update_plan_step(pid, sid, takeaways=None, design_rationale=None) == saved
    assert reopened.update_plan_step(pid, sid) == saved
    assert reopened.update_plan_step(pid, sid, takeaways=text)["revision"] == saved["revision"]
    cleared = reopened.update_plan_step(pid, sid, takeaways="")
    current = reopened.get_step(pid, sid)["step"]
    assert current["takeaways"] == "" and current["design_rationale"] == step["design_rationale"]
    assert cleared["revision"] == saved["revision"] + 1
    assert reopened.get_step(pid, sid, revision=saved["revision"])["step"]["takeaways"] == text


def test_mixed_status_refs_and_decisions_make_one_revision(record):
    _, store, pid, sid = record
    before = store.update_plan_step(pid, sid, input_refs=["brief.txt"], output_refs=["old.png"])
    update = store.edit_step(pid, sid, status="running", takeaways="Read brief and compared options.",
        design_rationale="Preserve the accepted level entrance.",
        input_refs=StringListPatch(add=["survey.txt", "brief.txt"]),
        output_refs=StringListPatch(add=["entrance.png"], remove=["old.png"]),
        expected_revision=before["revision"])
    after = store.get_step(pid, sid)["step"]
    assert update.changed is True and len(update.issues) == 1
    assert update.record["revision"] == before["revision"] + 1
    assert after["status"] == "running"
    assert after["input_refs"] == ["brief.txt", "survey.txt"]
    assert after["output_refs"] == ["entrance.png"]
    assert after["takeaways"] == "Read brief and compared options."
    assert after["design_rationale"] == "Preserve the accepted level entrance."
    assert store.list_plan_revisions(pid, step_id=sid)["revisions"][0]["revision"] == update.record["revision"]
    assert store.get_plan(pid, revision=before["revision"]) == {**before, "read_only": True}


@pytest.mark.parametrize("field", ["takeaways", "design_rationale"])
@pytest.mark.parametrize("invalid", [False, 17, [], {}, ["text"]])
def test_wrong_decision_type_rejects_all_changes(record, field, invalid):
    _, store, pid, sid = record
    before = store.get_plan(pid)
    revisions = store.list_plan_revisions(pid)
    with pytest.raises(ValueError, match=field):
        store.edit_step(pid, sid, status="running", input_refs=StringListPatch(add=["source.txt"]),
                        **{field: invalid})
    assert store.get_plan(pid) == before
    assert store.list_plan_revisions(pid) == revisions


def test_snapshot_failure_rolls_back_decisions_and_refs(record, monkeypatch):
    _, store, pid, sid = record
    before = store.get_plan(pid)
    revisions = store.list_plan_revisions(pid)
    original = store._record_generation_revision
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("after snapshot")
    monkeypatch.setattr(store, "_record_generation_revision", fail)
    with pytest.raises(RuntimeError, match="after snapshot"):
        store.update_plan_step(pid, sid, status="running", output_refs=["result.txt"],
                               takeaways="Important", design_rationale="Reason")
    assert store.get_plan(pid) == before
    assert store.list_plan_revisions(pid) == revisions


def test_completion_hook_runs_once_after_validation_and_only_on_transition(record):
    _, store, pid, sid = record
    before = store.get_plan(pid)
    calls = []
    def cleanup():
        # A separate reader can still observe the unchanged Step before cleanup.
        calls.append(store.get_step(pid, sid)["step"]["status"])
    for invalid in ({"takeaways": False}, {"output_refs": [17]}, {"expected_revision": 0}):
        with pytest.raises(ValueError):
            store.update_plan_step(pid, sid, status="completed", _before_complete=cleanup, **invalid)
        assert calls == [] and store.get_plan(pid) == before
    saved = store.update_plan_step(pid, sid, status="completed", takeaways="Reviewed", _before_complete=cleanup)
    assert calls == ["pending"] and saved["revision"] == before["revision"] + 1
    assert store.update_plan_step(pid, sid, status="completed", _before_complete=cleanup) == saved
    changed = store.update_plan_step(pid, sid, status="completed", takeaways="Reviewed again", _before_complete=cleanup)
    assert calls == ["pending"] and changed["revision"] == saved["revision"] + 1


def test_completion_hook_failure_preserves_unfinished_step_and_revision(record):
    _, store, pid, sid = record
    before = store.update_plan_step(pid, sid, status="running")
    revisions = store.list_plan_revisions(pid)
    def fail():
        raise RuntimeError("cleanup cancelled or failed")
    with pytest.raises(RuntimeError, match="cleanup cancelled or failed"):
        store.edit_step(pid, sid, status="completed", takeaways="Pending review", output_refs=["report.txt"],
                        _before_complete=fail)
    assert store.get_plan(pid) == before
    assert store.list_plan_revisions(pid) == revisions


def test_loop_reset_resume_history_and_revision_guards(record):
    _, store, pid, sid = record
    pre_loop = store.update_plan_step(pid, sid, takeaways="Preflight", design_rationale="Initial intent")
    first = store.execute_looping(pid)
    assert first["steps"][1]["takeaways"] == first["steps"][1]["design_rationale"] == ""
    saved = store.update_plan_step(pid, sid, takeaways="Keep the level entrance.",
        design_rationale="Stair alternative rejected for access.", input_refs=["prior-brief.txt"],
        output_refs=["level-entry.png"], loop_no=1, expected_revision=first["revision"])
    step = store.get_step(pid, sid)["step"]
    assert store.execute_looping(pid, resume=True) == saved
    resumed = store.execute_looping(pid, resume=True, feedback="Confirm the decision")
    assert resumed["steps"][1]["takeaways"] == step["takeaways"]
    second = store.execute_looping(pid)
    assert second["steps"][1]["takeaways"] == second["steps"][1]["design_rationale"] == ""
    old = store.get_step(pid, sid, loop_no=1)
    assert old["read_only"] is True and old["step"] == step
    assert store.get_plan(pid, loop_no=1)["steps"][1]["design_rationale"] == step["design_rationale"]
    assert store.get_step(pid, sid, loop_no=1, revision=saved["revision"])["step"] == saved["steps"][1]
    assert store.get_plan(pid, loop_no=0) == {**pre_loop, "read_only": True}
    for arguments, error in [({"loop_no": 1}, "Only current"),
                             ({"expected_revision": 1}, "Supply loop_no"),
                             ({"loop_no": 2, "expected_revision": 0}, "revision conflict")]:
        with pytest.raises(ValueError, match=error):
            store.update_plan_step(pid, sid, takeaways="Must not overwrite", **arguments)
    assert store.get_plan(pid) == second
    assert store.get_step(pid, sid, loop_no=1) == old


@pytest.mark.parametrize("pre_loop_schema", [False, True])
def test_additive_migration_preserves_refs_and_raw_legacy_snapshots(record, pre_loop_schema):
    path, store, pid, sid = record
    original_refs = ["../source/brief.txt", "C:/External/source.txt", "legacy reference text"]
    saved = store.update_plan_step(pid, sid, input_refs=original_refs, output_refs=["old/report.txt"])
    with sqlite3.connect(path) as db:
        db.execute("ALTER TABLE generation_loop_steps DROP COLUMN takeaways")
        db.execute("ALTER TABLE generation_loop_steps DROP COLUMN design_rationale")
        if pre_loop_schema:
            for column, default in (("status", "pending"), ("input_refs_json", "[]"), ("output_refs_json", "[]")):
                db.execute(f"ALTER TABLE generation_plan_steps ADD COLUMN {column} TEXT NOT NULL DEFAULT '{default}'")
                db.execute(f"""UPDATE generation_plan_steps SET {column}=(
                    SELECT {column} FROM generation_loop_steps r
                    WHERE r.plan_id=generation_plan_steps.plan_id AND r.step_id=generation_plan_steps.step_id)""")
            db.execute("DROP TABLE generation_loop_steps")
        for revision, raw in db.execute("SELECT revision,snapshot_json FROM generation_plan_revisions WHERE plan_id=?", (pid,)).fetchall():
            snapshot = json.loads(raw)
            for step in snapshot["steps"]:
                step.pop("takeaways", None)
                step.pop("design_rationale", None)
            db.execute("UPDATE generation_plan_revisions SET snapshot_json=? WHERE plan_id=? AND revision=?",
                       (json.dumps(snapshot), pid, revision))
        immutable = db.execute("SELECT * FROM generation_plan_revisions ORDER BY revision").fetchall()
        refs_before = db.execute("SELECT input_refs_json,output_refs_json FROM " +
            ("generation_plan_steps" if pre_loop_schema else "generation_loop_steps") +
            " WHERE plan_id=? AND step_id=?", (pid, sid)).fetchone()
    migrated = AlmondStore(path)
    assert migrated.get_plan(pid) == saved
    assert migrated.get_step(pid, sid)["step"]["input_refs"] == original_refs
    snapshot = migrated.get_plan(pid, revision=saved["revision"])
    assert snapshot == {**saved, "read_only": True}
    assert migrated.get_step(pid, sid, revision=saved["revision"])["step"] == saved["steps"][1]
    assert AlmondStore(path).get_plan(pid) == saved
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM generation_plan_revisions ORDER BY revision").fetchall() == immutable
        assert db.execute("SELECT input_refs_json,output_refs_json FROM generation_loop_steps WHERE plan_id=? AND step_id=?",
                          (pid, sid)).fetchone() == refs_before
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
