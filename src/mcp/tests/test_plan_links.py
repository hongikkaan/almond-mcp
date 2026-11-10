"""Plan parent/child arrays are stored references, not a managed hierarchy."""
import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


def test_plan_links_round_trip_and_history(tmp_path):
    path = tmp_path / "planning.db"
    store = AlmondStore(path)
    plan = store.create_plan("Task", parent_plan=["plan_parent", "plan_parent"],
                             child_plan=["plan_child"], depends_on=["plan_dependency"],
                             previous_id="plan_previous")
    pid = plan["plan_id"]
    assert plan["parent_plan"] == ["plan_parent", "plan_parent"]
    assert plan["child_plan"] == ["plan_child"]
    assert not store.edit_plan(pid, parent_plan=plan["parent_plan"]).changed
    assert store.update_plan(pid, parent_plan=None, child_plan=None) == plan
    updated = store.update_plan(pid, parent_plan=["plan_other"], child_plan=[],
                                expected_revision=plan["revision"])
    assert updated["revision"] == plan["revision"] + 1
    assert updated["depends_on"] == plan["depends_on"]
    assert updated["previous_id"] == plan["previous_id"]
    reopened = AlmondStore(path)
    assert reopened.get_plan(pid)["parent_plan"] == ["plan_other"]
    assert reopened.get_plan(pid)["child_plan"] == []
    assert reopened.get_plan(pid, plan["revision"])["parent_plan"] == plan["parent_plan"]
    assert reopened.get_plan(pid, plan["revision"])["child_plan"] == ["plan_child"]
    assert reopened.update_plan(pid, parent_plan=[])["parent_plan"] == []


def test_plan_links_do_not_validate_or_synchronize_relationships(tmp_path):
    store = AlmondStore(tmp_path / "planning.db")
    first = store.create_plan("First")
    second = store.create_plan("Second", parent_plan=[first["plan_id"], "plan_not_created"])
    assert store.get_plan(first["plan_id"]) == first
    # Contradiction, self-reference, cycles and duplicate references remain authored data.
    updated = store.update_plan(first["plan_id"],
        parent_plan=[second["plan_id"], first["plan_id"]],
        child_plan=[second["plan_id"], second["plan_id"]])
    assert updated["parent_plan"] == [second["plan_id"], first["plan_id"]]
    assert updated["child_plan"] == [second["plan_id"], second["plan_id"]]
    assert store.get_plan(second["plan_id"]) == second
    assert updated["status"] == first["status"]


def test_legacy_columns_and_snapshots_are_preserved(tmp_path):
    path = tmp_path / "old.db"
    store = AlmondStore(path)
    plan = store.create_plan("Existing", depends_on=["plan_reference"])
    pid = plan["plan_id"]
    with store._connect() as connection:
        old = json.loads(connection.execute(
            "SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id=?", (pid,)).fetchone()[0])
        old.pop("parent_plan")
        old.pop("child_plan")
        raw = json.dumps(old)
        connection.execute("UPDATE generation_plan_revisions SET snapshot_json=? WHERE plan_id=?", (raw, pid))
        connection.execute("ALTER TABLE generation_plans DROP COLUMN parent_plan_json")
        connection.execute("ALTER TABLE generation_plans DROP COLUMN child_plan_json")
        before = list(map(tuple, connection.execute("SELECT * FROM generation_plan_revisions")))
    migrated = AlmondStore(path)
    assert migrated.get_plan(pid) == plan
    assert migrated.get_plan(pid, plan["revision"])["parent_plan"] == []
    assert migrated.get_plan(pid, plan["revision"])["child_plan"] == []
    with migrated._connect() as connection:
        assert list(map(tuple, connection.execute("SELECT * FROM generation_plan_revisions"))) == before


def test_public_plan_links_schema_create_update_and_details(tmp_path):
    store = AlmondStore(tmp_path / "planning.db")
    server = FastMCP("plan-link-contracts")
    register(server, SimpleNamespace(retrieval_store=store))

    async def run():
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            for name in ("create_plan", "update_plan"):
                for field in ("parent_plan", "child_plan"):
                    schema = tools[name].input_schema["properties"][field]
                    assert {"items": {"type": "string"}, "type": "array"} in schema["anyOf"]
            async def call(name, **args):
                result = await client.call_tool(name, args)
                return json.loads(result.content[0].text)
            created = await call("create_plan", title="Task", goal="Task",
                parent_plan=["plan_parent"], child_plan=["plan_child"])
            pid = created["plan"]["plan_id"]
            detail = await call("get_phase_plan_step", include_details=True, plan_id=pid)
            assert detail["plan"]["parent_plan"] == ["plan_parent"]
            assert detail["plan"]["child_plan"] == ["plan_child"]
            kept = await call("update_plan", plan_id=pid, parent_plan=None, child_plan=None)
            assert not kept["changed"]
            updated = await call("update_plan", plan_id=pid,
                parent_plan=[], child_plan=[pid, "plan_not_created"])
            assert updated["changed"]
            detail = await call("get_phase_plan_step", include_details=True, plan_id=pid)
            assert detail["plan"]["parent_plan"] == []
            assert detail["plan"]["child_plan"] == [pid, "plan_not_created"]
            historic = await call("get_phase_plan_step", include_details=True, plan_id=pid, revision=created["plan"]["revision"])
            assert historic["plan"]["parent_plan"] == ["plan_parent"]
            assert historic["plan"]["child_plan"] == ["plan_child"]
            listed = await call("list_plans")
            assert "parent_plan" not in listed["plans"][0]
    asyncio.run(run())
