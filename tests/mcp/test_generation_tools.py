"""Public Plan/Phase arguments, errors and MCP schema against isolated stores."""
import asyncio
import importlib.util
import json
from pathlib import Path
import uuid

import pytest
from fastmcp import Client

from almond_mcp.retrieval_store import AlmondStore


PLAN_TOOLS = {
    "create_generation_phase", "get_generation_phase", "list_generation_phases", "update_generation_phase",
    "create_generation_plan", "get_generation_plan", "list_generation_plans", "update_generation_plan",
    "list_generation_plan_revisions", "update_generation_step", "resolve_generation_targets",
}


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("generation-tools")
    source = Path(__file__).resolve().parents[2] / "src/mcp/almond_mcp/server.py"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RHINO_MCP_STATE_DB", str(root / "state.sqlite3"))
        for suffix in ("LIBRARY", "DRAWING_ASSET", "DIAGRAM_ASSET", "GENERATED_ASSET",
                       "DRAWING_RECIPE", "DRAFTING", "CAPSULE", "MATERIAL", "CONSTRUCTION"):
            patch.setenv(f"RHINO_MCP_{suffix}_DIR", str(root / suffix.lower()))
        spec = importlib.util.spec_from_file_location(f"generation_server_{uuid.uuid4().hex}", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


@pytest.fixture
def store(server, tmp_path, monkeypatch):
    store = AlmondStore(tmp_path / "plans.sqlite3")
    monkeypatch.setattr(server, "retrieval_store", store)
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Plan tools must not call Rhino"))
    component_scene = store.create_scene("Registered component context")["scene_id"]
    with store._connect() as connection:
        connection.executemany("""
            INSERT INTO components(component_id, model_path, rhino_group_id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (component, store._component_model_path(str(tmp_path / "fixture.3dm")), str(uuid.uuid4()),
             component, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")
            for component in ("component_a", "component_b")
        ])
        connection.executemany(
            "INSERT INTO scene_components(scene_id, component_id) VALUES (?, ?)",
            [(component_scene, component) for component in ("component_a", "component_b")],
        )
    return store


def call(server, tool_name, **arguments):
    tool = getattr(server, tool_name)
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def test_public_phase_and_plan_metadata_arguments(server, store):
    phase = call(server, "create_generation_phase", name="Scheme", description="Envelope")["phase"]
    renamed = call(server, "update_generation_phase", phase_id=phase["phase_id"], name="Detail")["phase"]
    assert renamed["description"] == "Envelope"
    scene_a, scene_b = (store.create_scene(name)["scene_id"] for name in ("A", "B"))
    plan = call(server, "create_generation_plan", goal="Facade", scope="component", phase_id=phase["phase_id"],
                scene_id=scene_a, scene_ids=[scene_a, scene_b], component_ids=["component_a"])["plan"]
    assert plan["phase_id"] == phase["phase_id"]
    assert plan["scene_ids"] == [scene_a, scene_b]
    assert plan["component_ids"] == ["component_a"]
    assert call(server, "get_generation_phase", phase_id=phase["phase_id"])["phase"]["plan_count"] == 1
    assert call(server, "list_generation_phases", limit=1)["total"] == 1
    assert call(server, "list_generation_plans", phase_id=phase["phase_id"], scene_id=scene_b, status="pending")["total"] == 1
    changed = call(server, "update_generation_plan", plan_id=plan["plan_id"], goal="Roof", phase_id="",
                   scene_ids=[scene_b], component_ids=["component_b"], expected_revision=plan["revision"])["plan"]
    assert changed["goal"] == "Roof"
    assert changed["phase_id"] is None
    assert changed["scene_id"] == scene_b
    assert changed["component_ids"] == ["component_b"]


def test_public_step_refs_cas_and_explicit_empty_target(server, store):
    plan = call(server, "create_generation_plan", goal="Facade", scope="component", component_ids=["component_a"])["plan"]
    plan_id = plan["plan_id"]
    changed = call(server, "update_generation_step", plan_id=plan_id, step_id="inspect_context", status="running",
                   input_refs=["observation"], output_refs=["evidence"], component_ids=["component_b"],
                   expected_revision=plan["revision"])["plan"]
    completed = call(server, "update_generation_step", plan_id=plan_id, step_id="inspect_context",
                     status="completed", expected_revision=changed["revision"])["plan"]
    assert completed["steps"][0]["input_refs"] == ["observation"]
    assert completed["steps"][0]["output_refs"] == ["evidence"]
    assert completed["steps"][0]["component_ids"] == ["component_b"]
    stale = call(server, "update_generation_step", plan_id=plan_id, step_id="inspect_context",
                 status="completed", output_refs=["stale"], expected_revision=changed["revision"])
    assert stale["status"] == "error" and "revision conflict" in stale["message"]
    assert store.get_generation_plan(plan_id) == completed
    call(server, "update_generation_step", plan_id=plan_id, step_id="inspect_context", status="completed",
         component_ids=[], output_refs=[], expected_revision=completed["revision"])
    targets = call(server, "resolve_generation_targets", plan_id=plan_id, step_id="inspect_context")
    assert targets["status"] == "success"
    assert targets["source"] == "step"
    assert targets["components"] == []
    assert targets["live_verified"] is False


def test_public_historical_get_never_falls_back_to_current(server, store):
    old = call(server, "create_generation_plan", goal="Original", scope="component")["plan"]
    plan_id = old["plan_id"]
    current = call(server, "update_generation_plan", plan_id=plan_id, goal="Current", expected_revision=1)["plan"]
    assert call(server, "get_generation_plan", plan_id=plan_id)["plan"] == current
    assert call(server, "get_generation_plan", plan_id=plan_id, revision=1)["plan"] == old
    history = call(server, "list_generation_plan_revisions", plan_id=plan_id, limit=1)
    assert history["total"] == 2 and history["truncated"] is True
    assert history["revisions"][0]["revision"] == 2
    for revision in (0, 999):
        missing = call(server, "get_generation_plan", plan_id=plan_id, revision=revision)
        assert missing["status"] == "error" and "plan" not in missing
        assert str(revision) in missing["message"]


def test_public_revision_zero_is_forwarded_as_a_requested_baseline(server, store, monkeypatch):
    observed = []

    def get(plan_id, revision=None):
        observed.append((plan_id, revision))
        return {"plan_id": plan_id, "revision": revision, "goal": "Migrated baseline"}

    monkeypatch.setattr(store, "get_generation_plan", get)
    result = call(server, "get_generation_plan", plan_id="legacy", revision=0)
    assert result["plan"]["revision"] == 0
    assert observed == [("legacy", 0)]


@pytest.mark.parametrize("name,arguments", [
    ("create_generation_phase", {"name": ""}),
    ("get_generation_phase", {"phase_id": "missing"}),
    ("list_generation_phases", {"limit": 0}),
    ("update_generation_phase", {"phase_id": "missing", "name": "Changed"}),
    ("create_generation_plan", {"goal": "Goal", "scope": "unknown"}),
    ("get_generation_plan", {"plan_id": "missing"}),
    ("list_generation_plans", {"status": "unknown"}),
    ("update_generation_plan", {"plan_id": "missing", "goal": "Changed"}),
    ("list_generation_plan_revisions", {"plan_id": "missing"}),
    ("update_generation_step", {"plan_id": "missing", "step_id": "inspect_context", "status": "completed"}),
    ("resolve_generation_targets", {"plan_id": "missing"}),
])
def test_public_errors_are_explicit_without_creating_plans(server, store, name, arguments):
    response = call(server, name, **arguments)
    assert response["status"] == "error" and response["message"]
    assert store.list_generation_plans()["total"] == 0


def test_actual_mcp_schema_and_plan_roundtrip(server, store):
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert PLAN_TOOLS <= tools.keys()
            assert {"phase_id", "scene_ids", "component_ids"} <= tools["create_generation_plan"]["inputSchema"]["properties"].keys()
            assert {"component_ids", "expected_revision"} <= tools["update_generation_step"]["inputSchema"]["properties"].keys()
            assert "revision" in tools["get_generation_plan"]["inputSchema"]["properties"]
            for name in ("get_generation_phase", "list_generation_phases", "get_generation_plan",
                         "list_generation_plans", "list_generation_plan_revisions", "resolve_generation_targets"):
                assert tools[name]["annotations"]["readOnlyHint"] is True
            created = await client.call_tool("create_generation_plan", {"goal": "Protocol fixture", "scope": "component"})
            payload = json.loads(created.structured_content["result"])
            plan_id = payload["plan"]["plan_id"]
            read = await client.call_tool("get_generation_plan", {"plan_id": plan_id, "revision": 1})
            assert json.loads(read.structured_content["result"])["plan"] == payload["plan"]
            assert store.get_generation_plan(plan_id)["scope"] == "component"
    asyncio.run(verify())


@pytest.mark.parametrize("value", [True, "1", 1.0])
def test_mcp_rejects_coercible_revision_types_before_mutation(server, store, value):
    plan = store.create_generation_plan("Keep unchanged", scope="component")

    async def verify():
        async with Client(server.mcp) as client:
            for name, arguments in (
                ("get_generation_plan", {"plan_id": plan["plan_id"], "revision": value}),
                ("update_generation_plan", {"plan_id": plan["plan_id"], "goal": "Invalid", "expected_revision": value}),
                ("update_generation_step", {"plan_id": plan["plan_id"], "step_id": "inspect_context",
                                            "status": "completed", "expected_revision": value}),
            ):
                result = await client.call_tool(name, arguments, raise_on_error=False)
                assert result.is_error
    asyncio.run(verify())
    assert store.get_generation_plan(plan["plan_id"]) == plan
