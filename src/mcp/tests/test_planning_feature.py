"""Exercise extracted planning registration, SQL and shared reference contracts."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.planning.store import PlanningStore
from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore
import test_generation_plans as _plans


# Before cutover, put extracted methods ahead of the unchanged facade. After
# cutover, use the facade directly so this suite never creates a duplicate MRO.
if issubclass(AlmondStore, PlanningStore):
    PlanningAlmondStore = AlmondStore
else:
    class PlanningAlmondStore(PlanningStore, AlmondStore):
        pass


@pytest.fixture(autouse=True)
def use_extracted_plan_store(monkeypatch):
    # The established cases also construct stores for concurrent writers and
    # migration reopen checks; those must exercise the extracted mixin too.
    monkeypatch.setattr(_plans, "AlmondStore", PlanningAlmondStore)


class TestPlanningStore(_plans.GenerationPlanTests):
    """Run existing revision, target, dependency and rollback regressions."""


class TestPlanningStoreMigration(_plans.GenerationPlanMigrationTests):
    """Run the published legacy-schema migration through the moved initializer."""


@pytest.fixture
def server(tmp_path):
    namespace = {
        "retrieval_store": PlanningAlmondStore(tmp_path / "first.sqlite3"),
    }
    mcp = FastMCP("planning-feature")
    exports = register(mcp, FeatureContext(namespace))
    return SimpleNamespace(mcp=mcp, tools=exports, namespace=namespace)


def test_agent_reads_plan_summary_then_requests_steps_without_audit_or_ids(server):
    """Given a known Task, summary is enough until the agent chooses step details."""
    plan = server.namespace["retrieval_store"].create_plan("Inspect courtyard")
    read = lambda **kwargs: json.loads(server.tools["get_plan"](plan["plan_id"], **kwargs))
    summary = read()["plan"]
    assert summary == {"goal": "Inspect courtyard", "scope": "house", "status": "pending", "revision": 1}
    detail = read(field_groups=["steps"])["plan"]
    assert detail["steps"][0]["name"] == "programme"
    assert "step_id" not in detail["steps"][0] and "created_at" not in detail
    identified = read(include_ids=True)["plan"]
    assert "steps" not in identified and "created_at" not in identified
    full = read(field_groups=["all"], include_ids=True)["plan"]
    assert full["created_at"] and full["steps"][0]["step_id"]
    rejected = read(field_groups=["unexpected"])
    assert rejected["error_code"] == "invalid_arguments"


def test_agent_can_continue_writing_with_compact_revision_ack_and_visible_conflict(server):
    """Given a completed write, its handle/revision is sufficient for the next guarded write."""
    created = json.loads(server.tools["create_plan"]("Inspect courtyard"))
    assert set(created["plan"]) == {"plan_id", "revision", "status"}
    plan = created["plan"]
    updated = json.loads(server.tools["update_plan"](plan["plan_id"], goal="Refine courtyard",
                                                   expected_revision=plan["revision"]))
    assert updated["plan"] == {"plan_id": plan["plan_id"], "revision": 2, "status": "pending"}
    stale = json.loads(server.tools["update_plan"](plan["plan_id"], goal="Stale",
                                                 expected_revision=1))
    assert stale["status"] == "error" and "revision conflict" in stale["message"]
    assert server.namespace["retrieval_store"].get_plan(plan["plan_id"])["goal"] == "Refine courtyard"


def test_tool_registration_and_full_plan_lifecycle_over_mcp(server):
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == set(server.tools) == {
                "create_phase", "get_phase", "list_phases",
                "update_phase", "create_plan", "get_plan",
                "list_plans", "update_plan", "list_plan_revisions",
                "update_step", "resolve_targets", "get_selection_references",
            }
            for name, tool in tools.items():
                assert "context" not in tool.input_schema["properties"]
                if name.startswith(("get_", "list_", "resolve_")):
                    assert tool.annotations.read_only_hint is True
                    assert tool.annotations.destructive_hint is False

            async def call(tool_name, **arguments):
                response = await client.call_tool(tool_name, arguments)
                assert not response.is_error
                payload = json.loads(response.content[0].text)
                assert payload["status"] == "success"
                return payload

            phase = (await call("create_phase", name="Envelope", description="Scheme"))["phase"]
            phase_id = phase["phase_id"]
            assert (await call("get_phase", phase_id=phase_id))["phase"] == {"name": "Envelope", "plan_count": 0}
            renamed = await call("update_phase", phase_id=phase_id, name="Detail")
            assert renamed["phase"] == {"phase_id": phase_id}
            assert (await call("get_phase", phase_id=phase_id, field_groups=["description"]))["phase"]["description"] == "Scheme"
            assert (await call("list_phases", limit=1))["total"] == 1
            original = (await call("create_plan", goal="Inspect facade", scope="component",
                                   phase_id=phase_id))["plan"]
            plan_id = original["plan_id"]
            assert original["revision"] == 1
            saved_original = server.namespace["retrieval_store"].get_plan(plan_id)
            assert (await call("list_plans", phase_id=phase_id))["total"] == 1
            changed = (await call("update_plan", plan_id=plan_id, goal="Refine facade",
                                  expected_revision=1))["plan"]
            completed = (await call("update_step", plan_id=plan_id, step_id="inspect_context",
                                    status="completed", output_refs=["observation"],
                                    expected_revision=changed["revision"]))["plan"]
            assert completed["revision"] == 3
            saved_completed = server.namespace["retrieval_store"].get_plan(plan_id)
            assert saved_completed["steps"][0]["output_refs"] == ["observation"]
            assert (await call("get_plan", plan_id=plan_id, revision=1, include_ids=True, field_groups=["all"]))["plan"] == {k: v for k, v in saved_original.items() if k != "plan_id"}
            history = await call("list_plan_revisions", plan_id=plan_id, limit=2)
            assert history["total"] == 3 and history["truncated"]
            assert [item["operation"] for item in history["revisions"]] == [
                "update_step:inspect_context", "update_plan",
            ]
            targets = await call("resolve_targets", plan_id=plan_id, step_id="inspect_context", include_ids=True)
            assert targets["source"] == "plan" and targets["component_ids"] == []
            assert targets["live_verified"] is False

            stale = await client.call_tool("update_plan", {
                "plan_id": plan_id, "goal": "Stale writer", "expected_revision": 1,
            })
            assert "revision conflict" in json.loads(stale.content[0].text)["message"]
            assert (await call("get_plan", plan_id=plan_id, include_ids=True, field_groups=["all"]))["plan"] == {k: v for k, v in saved_completed.items() if k != "plan_id"}
            missing = await client.call_tool("get_plan", {"plan_id": plan_id, "revision": 100})
            assert "Unknown saved revision 100" in json.loads(missing.content[0].text)["message"]
            for name, arguments in (
                ("list_phases", {"limit": True}),
                ("list_plans", {"limit": "1"}),
                ("get_plan", {"plan_id": plan_id, "revision": 1.0}),
                ("update_plan", {"plan_id": plan_id, "expected_revision": False}),
                ("update_step", {"plan_id": plan_id, "step_id": "inspect_context",
                                             "status": "completed", "expected_revision": "3"}),
                ("list_plan_revisions", {"plan_id": plan_id, "limit": 1.0}),
            ):
                result = await client.call_tool(name, arguments, raise_on_error=False)
                assert result.is_error

    asyncio.run(verify())


def test_factories_keep_current_store_bindings_and_server_instances_isolated(server, tmp_path):
    first = json.loads(server.tools["create_phase"]("First"))["phase"]
    rebound = PlanningAlmondStore(tmp_path / "rebound.sqlite3")
    other_namespace = {"retrieval_store": PlanningAlmondStore(tmp_path / "other.sqlite3")}
    other = register(FastMCP("other-planning"), FeatureContext(other_namespace))
    other_phase = json.loads(other["create_phase"]("Other"))["phase"]
    server.namespace["retrieval_store"] = rebound
    assert json.loads(server.tools["list_phases"]())["total"] == 0
    rebound_phase = json.loads(server.tools["create_phase"]("Rebound"))["phase"]
    assert rebound.get_phase(rebound_phase["phase_id"])["name"] == "Rebound"
    assert rebound.get_phase(first["phase_id"]) is None
    assert json.loads(other["get_phase"](other_phase["phase_id"]))["phase"] == {"name": "Other", "plan_count": 0}
    assert json.loads(other["list_phases"]())["total"] == 1
