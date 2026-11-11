"""Planning discovery, one-Step reads and lossless legacy-data migration."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.planning.output import kst_minute
from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore

DETAIL = "get_phase_plan_step"
PUBLIC_DETAIL = "plan_05-get_phase_plan_step"


@pytest.fixture
def store(tmp_path):
    return AlmondStore(tmp_path / "planning.sqlite3")


def test_empty_discovery_does_not_offer_missing_detail_or_working_handles(store):
    tools = register(FastMCP("empty-planning"), SimpleNamespace(retrieval_store=store))
    for name, collection in (("list_phases", "phases"), ("list_plans", "plans")):
        value = json.loads(tools[name]())
        assert value[collection] == []
        assert "next_step_guide" not in value


def test_discovery_title_edits_and_single_step_reads(store, monkeypatch):
    phase = store.create_phase("Entrance", depends_on=["phase_future"])
    plan = store.create_plan("Review access and circulation", scope="component", phase_id=phase["phase_id"], title="Entrance access")
    pid = plan["plan_id"]
    tools = register(FastMCP("planning"), SimpleNamespace(retrieval_store=store))
    phases = json.loads(tools["list_phases"]())
    assert phases["phases"][0]["phase_id"] == phase["phase_id"]
    assert "plan_08-list" in phases["next_step_guide"]
    assert PUBLIC_DETAIL in phases["next_step_guide"]
    rows = json.loads(tools["list_plans"](phase_id=phase["phase_id"]))
    assert rows["plans"] == [{"plan_id": pid, "title": "Entrance access", "scope": "component", "status": "pending", "loop_no": 0, "revision": 1}]
    assert PUBLIC_DETAIL in rows["next_step_guide"]
    ph = json.loads(tools[DETAIL](include_details=True, phase_id=phase["phase_id"]))
    assert (ph["id"], ph["type"], ph["status"]) == (phase["phase_id"], "phase", "pending")
    assert ph["phase"]["plan_titles"] == ["Entrance access"]
    assert ph["phase"]["depends_on"] == ["phase_future"]
    assert "plan_count" not in ph["phase"]
    detail = json.loads(tools[DETAIL](plan_id=pid, include_details=True))
    assert "plan_10-set_working" in detail["next_step_guide"]
    assert detail["plan"]["phase"] == {"phase_id": phase["phase_id"], "name": "Entrance"}
    assert detail["plan"]["holon_ids"] == []
    assert detail["plan"]["created_at"] == kst_minute(plan["created_at"])
    renamed = store.update_plan(pid, title="Accessible entrance", expected_revision=plan["revision"])
    assert renamed["goal"] == plan["goal"] and renamed["revision"] == 2
    assert store.update_plan(pid, title=renamed["title"]) == renamed
    with pytest.raises(ValueError):
        store.update_plan(pid, title=" ")
    assert store.get_plan(pid, 1)["title"] == "Entrance access"
    store.update_plan_step(pid, plan["steps"][0]["step_id"], "pending", input_refs=["brief"], output_refs=["survey"])
    store.update_plan_step(pid, plan["steps"][1]["step_id"], "pending", output_refs=["another Step's long record"])
    # The current Step path must not fetch the whole Plan and its other records.
    monkeypatch.setattr(store, "get_plan", lambda *args, **kwargs: pytest.fail("unbounded Plan read"))
    step = json.loads(tools[DETAIL](include_details=True, plan_id=pid, step_id=plan["steps"][0]["step_id"]))
    assert "plan_10-set_working" in step.pop("next_step_guide")
    assert step == {"id": plan["steps"][0]["step_id"], "type": "step", "name": "inspect_context", "status": "pending", "read_only": False,
        "plan_id": pid, "loop_no": 0, "revision": 4,
        "step": {"step_type": "inspect_context", "input_refs": ["brief"], "output_refs": ["survey"]}}



@pytest.mark.parametrize("arguments", [{}, {"phase_id": "phase_a", "plan_id": "plan_a"},
    {"step_id": "design"}, {"phase_id": "phase_a", "revision": 1},
    {"phase_id": "phase_a", "loop_no": 0},
    {"phase_id": "phase_a", "step_id": "design"}])
def test_invalid_detail_selection_is_an_error(store, arguments):
    tools = register(FastMCP("planning"), SimpleNamespace(retrieval_store=store))
    assert json.loads(tools[DETAIL](**arguments))["status"] == "error"


def test_saved_revision_navigation_keeps_history_separate_from_current_work(store):
    plan = store.create_plan("Review entrance", scope="component")
    current = store.update_plan_step(plan["plan_id"], plan["steps"][1]["step_id"], output_refs=["new design"])
    tools = register(FastMCP("planning"), SimpleNamespace(retrieval_store=store))
    historic = json.loads(tools[DETAIL](include_details=True, plan_id=plan["plan_id"], revision=plan["revision"]))
    assert historic["revision"] == 1 and historic["read_only"] is True
    assert "revision을 생략" in historic["next_step_guide"]
    historic_step = json.loads(tools[DETAIL](include_details=True, plan_id=plan["plan_id"], step_id=plan["steps"][1]["step_id"], revision=plan["revision"]))
    assert historic_step["step"]["output_refs"] == []
    assert "revision을 생략" in historic_step["next_step_guide"]
    latest_step = json.loads(tools[DETAIL](include_details=True, plan_id=plan["plan_id"], step_id=plan["steps"][1]["step_id"]))
    assert latest_step["step"]["output_refs"] == ["new design"]
    assert "revision을 생략" not in latest_step["next_step_guide"]
    assert store.get_plan(plan["plan_id"]) == current


def test_dependency_kinds_are_not_execution_gates(store):
    phase = store.create_phase("Future relationship", depends_on=["phase_missing"])
    assert store.update_phase(phase["phase_id"], depends_on=[phase["phase_id"]])["depends_on"] == [phase["phase_id"]]
    first = store.create_plan("First", depends_on=["plan_missing"])
    second = store.create_plan("Second", depends_on=[first["plan_id"]])
    refs = [second["plan_id"], first["plan_id"]]
    assert store.update_plan(first["plan_id"], depends_on=refs, status="completed")["depends_on"] == refs
    assert store.update_plan(first["plan_id"], depends_on=[])["depends_on"] == []
    for bad in ([phase["phase_id"]], ["scene_a"], ["plan_"], ["arbitrary"]):
        with pytest.raises(ValueError, match="plan_ IDs"):
            store.update_plan(first["plan_id"], depends_on=bad)
    with pytest.raises(ValueError, match="phase_ IDs"):
        store.update_phase(phase["phase_id"], depends_on=[first["plan_id"]])


def test_public_schema_and_ascii_name_with_middle_dot_title(store):
    server = FastMCP("planning")
    register(server, SimpleNamespace(retrieval_store=store))

    async def run():
        async with Client(server) as client:
            tools = {t.name: t for t in await client.list_tools()}
            assert PUBLIC_DETAIL in tools and not {"get_phase", "get_plan", "get_step"}.intersection(tools)
            assert "get_phase·plan·step" not in tools
            assert tools[PUBLIC_DETAIL].title == "get_phase·plan·step"
            assert {"plan_12-update", "plan_13-update_step"}.issubset(tools)
            schemas = {n: t.model_dump(by_alias=True)["inputSchema"] for n, t in tools.items()}
            assert all("include_ids" not in s["properties"] for s in schemas.values())
            assert "field_groups" not in schemas["plan_08-list"]["properties"]
            assert set(schemas["plan_02-create"]["required"]) == {"title", "goal"}
            assert "component_ids" not in schemas["plan_13-update_step"]["properties"]
            assert set(schemas["plan_13-update_step"]["required"]) == {"plan_id", "step_id"}
            result = await client.call_tool("plan_02-create", {"title": "Survey", "goal": "Inspect entrance"})
            pid = json.loads(result.content[0].text)["plan"]["plan_id"]
            result = await client.call_tool(PUBLIC_DETAIL, {"plan_id": pid})
            assert json.loads(result.content[0].text)["id"] == pid
            for name, args in [(PUBLIC_DETAIL, {"plan_id": pid, "include_ids": True}),
                               ("plan_13-update_step", {"plan_id": pid, "step_id": "inspect_context", "status": "pending", "component_ids": []})]:
                result = await client.call_tool(name, args, raise_on_error=False)
                assert result.is_error

    asyncio.run(run())


def _legacy_data(store):
    phase = store.create_phase("Legacy")
    affected = store.create_plan("Legacy target", scope="component", phase_id=phase["phase_id"])
    label_only = store.create_plan("Legacy\nFull goal preserved")
    with store._connect() as con:
        con.execute("INSERT INTO project_files(file_id,file_name) VALUES('file_test','test.3dm')")
        con.execute("""INSERT INTO ontological_holons(ontological_id,project_file_id,rhino_group_id,name,created_at,updated_at)
            VALUES('component_old','file_test','group_test','Old target','2026-01-01T00:00+00:00','2026-01-01T00:00+00:00')""")
        con.execute("INSERT INTO generation_step_ontological VALUES(?,?,?,0)", (affected["plan_id"], affected["steps"][1]["step_id"], "component_old"))
        con.execute("UPDATE generation_plan_steps SET component_refs_set=1 WHERE plan_id=? AND step_id=?", (affected["plan_id"], affected["steps"][1]["step_id"]))
        con.execute("UPDATE generation_plans SET title=''")
        con.execute("UPDATE generation_plans SET depends_on_json=? WHERE plan_id=?", (json.dumps(["phase_other", "plan_missing"]), affected["plan_id"]))
        con.execute("UPDATE generation_phases SET depends_on_json=?", (json.dumps(["plan_other", "phase_missing"]),))
        con.execute("DELETE FROM _schema_migrations WHERE name='planning_details_v1'")
        # Preserve a genuinely old snapshot, including its retired Step target.
        old = dict(affected)
        old.pop("title")
        old.pop("phase")
        old["steps"][1]["component_ids"] = ["component_old"]
        old["depends_on"] = ["phase_other", "plan_missing"]
        con.execute("UPDATE generation_plan_revisions SET snapshot_json=? WHERE plan_id=?", (json.dumps(old), affected["plan_id"]))
        snapshots = [tuple(r) for r in con.execute("SELECT * FROM generation_plan_revisions ORDER BY plan_id,revision")]
    return affected, label_only, snapshots


def test_migration_retires_targets_without_rewriting_history(store):
    affected, label_only, old_snapshots = _legacy_data(store)
    migrated = AlmondStore(store.database_path)
    pid = affected["plan_id"]
    current = migrated.get_plan(pid)
    assert current["depends_on"] == ["plan_missing"] and current["revision"] == affected["revision"] + 1
    assert migrated.get_phase(affected["phase_id"])["depends_on"] == ["phase_missing"]
    assert migrated.resolve_targets(pid, affected["steps"][1]["step_id"])["source"] == "plan"
    assert migrated.resolve_targets(pid, affected["steps"][1]["step_id"])["component_ids"] == []
    assert migrated.get_plan(label_only["plan_id"]) == label_only
    with migrated._connect() as con:
        assert [tuple(r) for r in con.execute("SELECT * FROM _retired_step_targets")] == [(pid, affected["steps"][1]["step_id"], '["component_old"]')]
        assert con.execute("SELECT COUNT(*) FROM generation_step_ontological").fetchone()[0] == 0
        assert con.execute("SELECT SUM(component_refs_set) FROM generation_plan_steps").fetchone()[0] == 0
        for old in old_snapshots:
            assert tuple(con.execute("SELECT * FROM generation_plan_revisions WHERE plan_id=? AND revision=?", old[:2]).fetchone()) == old
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    tools = register(FastMCP("planning"), SimpleNamespace(retrieval_store=migrated))
    historic = json.loads(tools[DETAIL](include_details=True, plan_id=pid, revision=1))
    assert historic["plan"]["depends_on"] == ["plan_missing"]
    assert historic["plan"]["phase"]["name"] is None
    assert all("component_ids" not in s for s in historic["plan"]["steps"])
    assert AlmondStore(store.database_path).get_plan(pid) == current


def test_migration_rolls_back_when_revision_recording_fails(store, monkeypatch):
    affected, _, _ = _legacy_data(store)
    def fail(*args, **kwargs):
        raise RuntimeError("snapshot failed")
    monkeypatch.setattr(AlmondStore, "_record_generation_revision", fail)
    with pytest.raises(RuntimeError, match="snapshot failed"):
        AlmondStore(store.database_path)
    with store._connect() as con:
        assert con.execute("SELECT title FROM generation_plans WHERE plan_id=?", (affected["plan_id"],)).fetchone()[0] == ""
        assert con.execute("SELECT COUNT(*) FROM generation_step_ontological").fetchone()[0] == 1
        assert not con.execute("SELECT 1 FROM _schema_migrations WHERE name='planning_details_v1'").fetchone()


def test_kst_minute_rolls_into_the_next_day():
    assert kst_minute("2026-01-31T16:45:59+00:00") == "2026-02-01-01:45"


@pytest.mark.parametrize("name,args", [("list_phases", {}), ("list_plan_revisions", {"plan_id": "plan_a"}),
    ("resolve_targets", {"plan_id": "plan_a"}), ("get_selection_references", {})])
def test_invalid_groups_keep_the_existing_error_contract_before_any_io(name, args):
    # No store or native context is available: validation must run first.
    tools = register(FastMCP("planning"), SimpleNamespace())
    response = tools[name](**args, field_groups=["unknown"])
    if name == "get_selection_references":
        assert response.is_error
        response = response.structured_content["result"]
    result = json.loads(response)
    assert result["status"] == "error" and result["error_code"] == "invalid_arguments"
