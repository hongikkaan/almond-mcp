"""Phase, Plan and Step share four public operations without sharing input fields."""
import asyncio
import json
from types import SimpleNamespace
import pytest
from jsonschema import validate, ValidationError

from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.output_contracts import public_output_schema


@pytest.mark.parametrize("name,payload", [
    ("create_planning", {"status": "success", "phase": []}),
    ("create_planning", {"status": "success", "plan": "bad"}),
    ("list_planning", {"status": "success", "steps": "bad"}),
    ("update_planning", {"status": "success", "step": "bad"}),
])
def test_output_types_are_checked_even_when_another_target_is_possible(name, payload):
    with pytest.raises(ValidationError):
        validate(payload, public_output_schema(name, wrapped=False))


def test_one_crud_surface_lists_automatic_steps_from_the_selected_plan(tmp_path):
    server = FastMCP("planning-crud")
    register(server, SimpleNamespace(retrieval_store=AlmondStore(tmp_path / "planning.sqlite3")))

    async def run():
        async with Client(server) as client:
            async def call(name, request):
                result = await client.call_tool(name, {"request": request})
                return json.loads(result.content[0].text)

            phase = await call("plan_02-create", {"target": "phase", "name": "Entrance"})
            plan = await call("plan_02-create", {"target": "plan", "title": "Review", "goal": "Survey entrance",
                                                  "phase_id": phase["phase"]["phase_id"]})
            pid = plan["plan"]["plan_id"]
            detail = await call("plan_05-get", {"target": "plan", "plan_id": pid, "include_details": True})
            steps = await call("plan_08-list", {"target": "step", "plan_id": pid})
            assert steps["steps"] == detail["plan"]["steps"]
            assert steps["total"] == len(steps["steps"]) > 0
            assert (steps["plan_id"], steps["loop_no"], steps["revision"], steps["read_only"]) == (pid, 0, 1, False)
            assert steps["truncated"] is False
            names = {tool.name for tool in await client.list_tools()}
            assert {"plan_02-create", "plan_05-get", "plan_08-list", "plan_12-update"} <= names
            assert not {"plan_01-create_phase", "plan_06-list_phases", "plan_11-update_phase",
                        "plan_13-update_step", "plan_05-get_phase_plan_step"} & names

    asyncio.run(run())


def test_target_validation_and_step_patch_preserve_plan_and_history(tmp_path):
    server = FastMCP("planning-patch")
    register(server, SimpleNamespace(retrieval_store=AlmondStore(tmp_path / "planning.sqlite3")))

    async def run():
        async with Client(server) as client:
            async def call(name, request):
                response = await client.call_tool(name, {"request": request})
                return json.loads(response.content[0].text)

            created = await call("plan_02-create", {"target": "plan", "title": "Survey", "goal": "Keep the record"})
            pid = created["plan"]["plan_id"]
            original = await call("plan_08-list", {"target": "step", "plan_id": pid})
            sid = original["steps"][0]["step_id"]
            invalid_requests = [
                ("plan_02-create", {"target": "step", "plan_id": pid, "name": "Unrequested step"}),
                ("plan_12-update", {"target": "step", "plan_id": pid, "step_id": sid, "status": "running", "goal": "Wrong target field"}),
                ("plan_12-update", {"target": "step", "plan_id": pid, "step_id": sid, "output_refs": {"add": [123]}}),
                ("plan_05-get", {"target": "phase", "phase_id": "phase_missing", "loop_no": 0}),
                ("plan_08-list", {"target": "step", "plan_id": pid, "limit": True}),
            ]
            for name, request in invalid_requests:
                result = await client.call_tool(name, {"request": request}, raise_on_error=False)
                assert result.is_error
            unchanged = await call("plan_08-list", {"target": "step", "plan_id": pid})
            assert unchanged == original
            edited = await call("plan_12-update", {"target": "step", "plan_id": pid, "step_id": sid,
                "output_refs": {"add": ["survey.md", "survey.md"], "remove": ["absent.md"]}})
            assert edited["changed"] is True and edited["status"] == "partial_success"
            assert {issue["reason"] for issue in edited["issues"]} == {"duplicate_input", "not_found"}
            detail = await call("plan_05-get", {"target": "step", "plan_id": pid, "step_id": sid, "include_details": True})
            assert detail["step"]["output_refs"] == ["survey.md"]
            assert detail["status"] == "pending" and detail["revision"] == original["revision"] + 1
            historical = await call("plan_08-list", {"target": "step", "plan_id": pid,
                "loop_no": original["loop_no"], "revision": original["revision"], "limit": 1})
            assert historical["read_only"] is True and historical["revision"] == original["revision"]
            assert historical["steps"] == original["steps"][:1]
            assert historical["total"] == original["total"] and historical["truncated"] is True
            for request in ({"target": "step", "plan_id": "missing"},
                            {"target": "step", "plan_id": pid, "loop_no": 99},
                            {"target": "step", "plan_id": pid, "revision": 99}):
                missing = await call("plan_08-list", request)
                assert missing["status"] == "error" and "steps" not in missing

    asyncio.run(run())
