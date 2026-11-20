"""Two document workers share Plan data but keep independent capture destinations."""
import asyncio
import base64
from contextlib import AsyncExitStack
import json
from pathlib import Path
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from test_stdio_contract import ROOT, isolated_environment


def test_defined_view_keeps_callers_plan_loop_and_step_when_peer_opens_next_loop(tmp_path):
    environment = isolated_environment(tmp_path)
    models = ("low-rise.3dm", "housing.3dm")
    tokens = ("a" * 32, "b" * 32)

    async def call(client, tool, **arguments):
        result = await client.call_tool(tool, arguments)
        assert not result.is_error, result.content
        return json.loads(result.content[0].text)

    async def create_plan(client, model):
        return (await call(client, "plan_02-create", request={
            "target": "plan", "title": model, "goal": "Review the saved view",
        }))["plan"]["plan_id"]

    async def select_step(client, plan, loop):
        step = {"plan_id": plan, "loop_no": loop["loop_no"], "step_id": loop["next_step_id"]}
        selected = await call(client, "plan_10-set_working", **step)
        assert {key: selected[key] for key in step} == step
        return step, selected["artifact_dir"]

    async def step_refs(client, step):
        detail = await call(client, "plan_05-get", request={"target": "step", "include_details": True, **step})
        return detail["step"]["output_refs"]

    async def check():
        sessions = tmp_path / ".almond/.sessions"
        async with AsyncExitStack() as stack:
            clients = []
            for slot, model, token in zip(("A", "B"), models, tokens):
                params = StdioServerParameters(command=sys.executable, args=[
                    "-B", "-X", "utf8", str(ROOT / "tests/integration/bound_server_fixture.py"),
                ], env=dict(environment, ALMOND_TEST_MODEL=model, ALMOND_TEST_TOKEN=token,
                            ALMOND_TEST_SLOT=slot), cwd=ROOT)
                reader, writer = await stack.enter_async_context(stdio_client(params))
                client = await stack.enter_async_context(ClientSession(reader, writer, read_timeout_seconds=45.0))
                await client.initialize()
                clients.append(client)
            low, housing = clients
            bindings = [json.loads((sessions / token / "ready.json").read_bytes()) for token in tokens]
            assert len({binding["pid"] for binding in bindings}) == 2
            assert {binding["document_serial"] for binding in bindings} == {1}
            assert {binding["storage"] for binding in bindings} == {str(tmp_path / ".almond")}
            low_plan, housing_plan = [await create_plan(client, model) for client, model in zip(clients, models)]
            low_loop = await call(low, "plan_03-execute_looping", plan_id=low_plan, artifact_name="261120_low-rise")
            low_step, low_dir = await select_step(low, low_plan, low_loop)
            previous = await call(housing, "plan_03-execute_looping", plan_id=housing_plan, artifact_name="261120_housing")
            housing_loop = await call(housing, "plan_03-execute_looping", plan_id=housing_plan, resume=False)
            housing_step, housing_dir = await select_step(housing, housing_plan, housing_loop)
            assert (low_dir, housing_dir) == (".almond/produced/261120_low-rise/01", ".almond/produced/261120_housing/02")

            captures = []
            for client, model, token, step, directory in zip(clients, models, tokens, (low_step, housing_step), (low_dir, housing_dir)):
                result = await client.call_tool("capture_04-defined_view", {
                    "target_kind": "named_view", "target": "Review", "expected_model_path": model,
                })
                assert not result.is_error, result.content
                image_file = result.structured_content["image_file"]
                assert image_file["status"] == "saved" and image_file["lifetime"] == "plan"
                path = image_file["path"]
                assert Path(path).parent.as_posix() == directory + "/captures"
                png = next(content for content in result.content if content.type == "image")
                assert (tmp_path / path).read_bytes() == base64.b64decode(png.data)
                assert json.loads((sessions / token / "work.json").read_bytes()) == step
                assert await step_refs(client, step) == []
                await call(client, "plan_12-update", request={"target": "step", **step, "output_refs": {"add": [path]}})
                captures.append(path)
            assert await step_refs(housing, low_step) == [captures[0]]
            assert await step_refs(low, housing_step) == [captures[1]]
            assert await step_refs(housing, {**housing_step, "loop_no": previous["loop_no"]}) == []
            assert {path.relative_to(tmp_path).as_posix() for path in (tmp_path / ".almond/produced").rglob("*.png")} == set(captures)

    asyncio.run(check())
