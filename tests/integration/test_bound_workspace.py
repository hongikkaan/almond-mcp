"""Exercise shared Plan records and separate capture folders across bound workers."""
import asyncio
import base64
from contextlib import AsyncExitStack
import json
from pathlib import Path

from render_tool_declarations import open_stdio, stdio_parameters


async def call(client, name, **arguments):
    result = await client.call_tool(name, arguments)
    assert not result.is_error, result.content
    value = json.loads(result.content[0].text)
    assert value["status"] != "error", value
    return value


async def start_plan(client, model, folder):
    created = await call(client, "plan_02-create", request={
        "target": "plan", "title": model, "goal": "Review the entrance",
    })
    plan_id = created["plan"]["plan_id"]
    return plan_id, await call(client, "plan_03-execute_looping", plan_id=plan_id, artifact_name=folder)


async def select_step(client, plan_id, loop):
    step = {"plan_id": plan_id, "loop_no": loop["loop_no"], "step_id": loop["next_step_id"]}
    await call(client, "plan_10-set_working", **step)
    return step


async def save_capture(client, model, directory, step, root):
    result = await client.call_tool("capture_04-defined_view", {
        "target_kind": "named_view", "target": "Entrance", "scale_percent": 100, "expected_model_path": model,
    })
    assert not result.is_error, result.content
    saved = result.structured_content["image_file"]
    assert saved["status"] == "saved" and saved["lifetime"] == "plan"
    path = saved["path"]
    assert Path(path).parent.as_posix() == f".almond/produced/{directory}/captures"
    image = next(content for content in result.content if content.type == "image")
    assert (root / path).read_bytes() == base64.b64decode(image.data)
    await call(client, "plan_12-update", request={
        "target": "step", **step, "output_refs": {"add": [path]},
    })
    return path


async def step_refs(client, step):
    result = await call(client, "plan_05-get", request={"target": "step", **step, "include_details": True})
    return result["step"]["output_refs"]


def test_bound_workspace_isolation(tmp_path):
    async def run():
        models = ("entrance.3dm", "courtyard.3dm")
        folders = ("261126_entrance", "261126_courtyard")
        async with AsyncExitStack() as stack:
            clients = []
            for model, slot, prefix in zip(models, ("A", "B"), ("a", "b"), strict=True):
                params = stdio_parameters("terminal", tmp_path, model_name=model)
                params.env.update(ALMOND_TEST_SLOT=slot, ALMOND_TEST_TOKEN=prefix * 32)
                client, _ = await stack.enter_async_context(open_stdio(params))
                clients.append(client)

            entrance, courtyard = clients
            entrance_step = await select_step(entrance, *await start_plan(entrance, models[0], folders[0]))
            courtyard_plan, _ = await start_plan(courtyard, models[1], folders[1])
            next_loop = await call(courtyard, "plan_03-execute_looping", plan_id=courtyard_plan)
            courtyard_step = await select_step(courtyard, courtyard_plan, next_loop)
            first = await save_capture(entrance, models[0], f"{folders[0]}/01", entrance_step, tmp_path)
            second = await save_capture(courtyard, models[1], f"{folders[1]}/02", courtyard_step, tmp_path)
            assert await step_refs(courtyard, entrance_step) == [first]
            assert await step_refs(entrance, courtyard_step) == [second]
            assert await step_refs(entrance, {**courtyard_step, "loop_no": 1}) == []
            assert (tmp_path / first).read_bytes() != (tmp_path / second).read_bytes()

    asyncio.run(run())
