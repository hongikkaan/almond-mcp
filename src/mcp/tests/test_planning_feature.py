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
import test_drawing_sheets as _sheets
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


def test_tool_registration_and_full_plan_lifecycle_over_mcp(server):
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == set(server.tools) == {
                "create_generation_phase", "get_generation_phase", "list_generation_phases",
                "update_generation_phase", "create_generation_plan", "get_generation_plan",
                "list_generation_plans", "update_generation_plan", "list_generation_plan_revisions",
                "update_generation_step", "resolve_generation_targets",
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

            phase = (await call("create_generation_phase", name="Envelope", description="Scheme"))["phase"]
            phase_id = phase["phase_id"]
            assert (await call("get_generation_phase", phase_id=phase_id))["phase"] == phase
            renamed = await call("update_generation_phase", phase_id=phase_id, name="Detail")
            assert renamed["phase"]["description"] == "Scheme"
            assert (await call("list_generation_phases", limit=1))["total"] == 1
            original = (await call("create_generation_plan", goal="Inspect facade", scope="component",
                                   phase_id=phase_id))["plan"]
            plan_id = original["plan_id"]
            assert original["revision"] == 1
            assert (await call("list_generation_plans", phase_id=phase_id))["total"] == 1
            changed = (await call("update_generation_plan", plan_id=plan_id, goal="Refine facade",
                                  expected_revision=1))["plan"]
            completed = (await call("update_generation_step", plan_id=plan_id, step_id="inspect_context",
                                    status="completed", output_refs=["observation"],
                                    expected_revision=changed["revision"]))["plan"]
            assert completed["revision"] == 3
            assert completed["steps"][0]["output_refs"] == ["observation"]
            assert (await call("get_generation_plan", plan_id=plan_id, revision=1))["plan"] == original
            history = await call("list_generation_plan_revisions", plan_id=plan_id, limit=2)
            assert history["total"] == 3 and history["truncated"]
            assert [item["operation"] for item in history["revisions"]] == [
                "update_step:inspect_context", "update_plan",
            ]
            targets = await call("resolve_generation_targets", plan_id=plan_id, step_id="inspect_context")
            assert targets["source"] == "plan" and targets["component_ids"] == []
            assert targets["live_verified"] is False

            stale = await client.call_tool("update_generation_plan", {
                "plan_id": plan_id, "goal": "Stale writer", "expected_revision": 1,
            })
            assert "revision conflict" in json.loads(stale.content[0].text)["message"]
            assert (await call("get_generation_plan", plan_id=plan_id))["plan"] == completed
            missing = await client.call_tool("get_generation_plan", {"plan_id": plan_id, "revision": 100})
            assert "Unknown saved revision 100" in json.loads(missing.content[0].text)["message"]
            for name, arguments in (
                ("list_generation_phases", {"limit": True}),
                ("list_generation_plans", {"limit": "1"}),
                ("get_generation_plan", {"plan_id": plan_id, "revision": 1.0}),
                ("update_generation_plan", {"plan_id": plan_id, "expected_revision": False}),
                ("update_generation_step", {"plan_id": plan_id, "step_id": "inspect_context",
                                             "status": "completed", "expected_revision": "3"}),
                ("list_generation_plan_revisions", {"plan_id": plan_id, "limit": 1.0}),
            ):
                result = await client.call_tool(name, arguments, raise_on_error=False)
                assert result.is_error

    asyncio.run(verify())


def test_factories_keep_current_store_bindings_and_server_instances_isolated(server, tmp_path):
    first = json.loads(server.tools["create_generation_phase"]("First"))["phase"]
    rebound = PlanningAlmondStore(tmp_path / "rebound.sqlite3")
    other_namespace = {"retrieval_store": PlanningAlmondStore(tmp_path / "other.sqlite3")}
    other = register(FastMCP("other-planning"), FeatureContext(other_namespace))
    other_phase = json.loads(other["create_generation_phase"]("Other"))["phase"]
    server.namespace["retrieval_store"] = rebound
    assert json.loads(server.tools["list_generation_phases"]())["total"] == 0
    rebound_phase = json.loads(server.tools["create_generation_phase"]("Rebound"))["phase"]
    assert rebound.get_generation_phase(rebound_phase["phase_id"]) == rebound_phase
    assert rebound.get_generation_phase(first["phase_id"]) is None
    assert json.loads(other["get_generation_phase"](other_phase["phase_id"]))["phase"] == other_phase
    assert json.loads(other["list_generation_phases"]())["total"] == 1


def test_sheet_rules_consume_planning_helpers_without_rewriting_plan_revisions(tmp_path):
    store = PlanningAlmondStore(tmp_path / "shared-sheet.sqlite3")
    model = store._component_model_path(str(tmp_path / "drawing.3dm"))
    _sheets.test_sheet_context_wrapup_and_updates_do_not_rewrite_plan_snapshots(store, model)
