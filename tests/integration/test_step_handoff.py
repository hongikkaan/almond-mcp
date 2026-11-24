"""Recover Step handoff evidence across separate bound stdio workers."""
import asyncio
import json
from pathlib import Path
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from test_stdio_contract import ROOT, isolated_environment


def test_new_bound_worker_reads_prior_loop_judgments_and_actual_files(tmp_path):
    env = isolated_environment(tmp_path)
    input_file = tmp_path / "survey.md"
    input_file.write_text("Existing north entrance.\n", encoding="utf-8")
    # Absolute-looking prose is still a judgment, while file paths are normalized.
    notes = {"takeaways": f"{tmp_path} is the source of record.",
             "design_rationale": "Preserve the north approach.\nKeep the existing public axis."}

    async def connect(token, action):
        params = StdioServerParameters(
            command=sys.executable,
            args=["-B", "-X", "utf8", "-u", str(ROOT / "tests/integration/bound_server_fixture.py")],
            env={**env, "ALMOND_TEST_TOKEN": token},
        )
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()

                async def call(name, arguments):
                    result = await client.call_tool(name, arguments)
                    assert not result.is_error, result.content
                    return json.loads(result.content[0].text)

                return await action(call)

    async def first(call):
        created = await call("plan_02-create", {"request": {
            "target": "plan", "title": "Entrance", "goal": "Design a usable north approach",
        }})
        plan_id = created["plan"]["plan_id"]
        await call("plan_03-execute_looping", {"plan_id": plan_id})
        listing = await call("plan_08-list", {"request": {"target": "step", "plan_id": plan_id}})
        step_id = listing["steps"][0]["step_id"]
        selected = await call("plan_10-set_working", {"plan_id": plan_id, "step_id": step_id})
        output_file = tmp_path / selected["artifact_dir"] / "recommendation.md"
        output_file.parent.mkdir(parents=True)
        output_file.write_text("Keep the approach at grade.\n", encoding="utf-8")
        step = {"target": "step", "plan_id": plan_id, "step_id": step_id, "loop_no": 1}
        saved = await call("plan_12-update", {"request": {
            **step, **notes, "expected_revision": selected["revision"],
            "input_refs": {"add": [str(input_file)]}, "output_refs": {"add": [str(output_file)]},
        }})
        assert saved["status"] == "updated"
        revision = saved["plan"]["revision"]
        next_loop = await call("plan_03-execute_looping", {"plan_id": plan_id})
        assert next_loop["loop_no"] == 2
        assert next_loop["previous_loop"]["steps"][0]["takeaways"] == notes["takeaways"]
        return step, revision, output_file.relative_to(tmp_path).as_posix()

    async def run():
        step, revision, output_path = await connect("a" * 32, first)

        async def second(call):
            request = {**step, "include_details": True, "revision": revision}
            record = await call("plan_05-get", {"request": request})
            assert record["read_only"] is True and record["loop_no"] == 1
            detail = record["step"]
            assert {key: detail[key] for key in notes} == notes
            assert detail["input_refs"] == ["survey.md"]
            assert detail["output_refs"] == [output_path]
            assert (tmp_path / Path(detail["input_refs"][0])).read_text(encoding="utf-8") == "Existing north entrance.\n"
            assert (tmp_path / Path(detail["output_refs"][0])).read_text(encoding="utf-8") == "Keep the approach at grade.\n"

            current = await call("plan_05-get", {"request": {**step, "loop_no": 2, "include_details": True}})
            assert {key: current["step"][key] for key in notes} == {key: "" for key in notes}
            assert current["step"]["input_refs"] == current["step"]["output_refs"] == []

        await connect("b" * 32, second)

    asyncio.run(run())
