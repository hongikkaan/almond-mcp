"""Exercise shared Plan records and separate capture folders across bound workers."""
import asyncio
import base64
from contextlib import AsyncExitStack
import json
from pathlib import Path

from render_tool_declarations import open_stdio, stdio_parameters


CAPTURE_SIZE = 128
FULL_SCALE = 100


async def call(client, name, **arguments):
    result = await client.call_tool(name, arguments)
    assert not result.is_error, result.content
    text = result.content[0].text
    value = json.loads(text)
    if name in {"plan_02-create", "plan_05-get", "plan_12-update", "inspect_03-get_document_context"}:
        assert result.structured_content == {"result": text}
    else:
        assert result.structured_content == value
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
    view = await call(client, "inspect_03-get_document_context", sections=["display_modes"])
    result = await client.call_tool("capture_04-defined_view", {
        "target_kind": "named_view", "target": "Entrance", "scale_percent": FULL_SCALE, "expected_model_path": model,
        "display_mode": view["display_modes"][0]["id"], "include_usage": True,
    })
    assert not result.is_error, result.content
    saved = result.structured_content["image_file"]
    assert saved["status"] == "saved" and saved["lifetime"] == "plan"
    path = saved["path"]
    assert Path(path).parent.as_posix() == f".almond/produced/{directory}/captures"
    image = next(content for content in result.content if content.type == "image")
    assert (root / path).read_bytes() == base64.b64decode(image.data)
    metadata, usage = [json.loads(block.text) for block in result.content if block.type == "text"]
    assert metadata == result.structured_content == {"status": "success", "image_file": saved}
    assert usage["width"] == usage["height"] == CAPTURE_SIZE
    await call(client, "plan_12-update", request={
        "target": "step", **step, "output_refs": {"add": [path]},
    })
    return path


async def step_refs(client, step):
    result = await call(client, "plan_05-get", request={"target": "step", **step, "include_details": True})
    return result["step"]["output_refs"]


async def assert_project_page(client, models, step, folder):
    for model in models:
        result = await call(client, "context_05-upsert_project_file", file_name=model)
        assert result == {"status": "success", "file_name": model, "description": None}

    query = {"sections": ["project", "document", "locations"], "files_limit": 1}
    first = await call(client, "context_04-get_project_info", **query)
    second = await call(client, "context_04-get_project_info", **query, files_offset=1, include_ids=True)
    assert set(first) == set(second) == {"status", "project", "document", "locations"}
    for offset, (page, model) in enumerate(zip((first, second), sorted(models), strict=True)):
        assert page["project"]["files"] == [{"file_name": model, "description": None}]
        assert page["project"]["files_page"] == {"total": len(models), "offset": offset}
        assert page["project"]["worksession_files"] == []
    assert "runtime_serial_number" not in first["document"]
    assert second["document"]["runtime_serial_number"] == 1
    assert {key: second["locations"][key] for key in step} == step
    assert not {"plan_id", "step_id"} & first["locations"].keys()
    assert first["locations"]["artifact_dir"] == f".almond/produced/{folder}"


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
            await assert_project_page(entrance, models, entrance_step, f"{folders[0]}/01")
            user_data = {"reference": r"Z:\catalog\A.3dm", "nested": [{"object_id": "custom"}]}
            for tool, field in (("script_01-run_project_python", "code"), ("script_02-run_rhino", "script")):
                receipt = await entrance.call_tool(tool, {field: json.dumps(user_data)})
                assert not receipt.is_error, receipt.content
                assert json.loads(receipt.content[0].text)["result"] == user_data
            invalid = await entrance.call_tool("analysis_04-export_structural_report", {
                "path": "rejected/report.md", "unknown_field": True,
            })
            assert invalid.is_error
            assert not (tmp_path / ".almond" / "produced" / folders[0] / "01" / "rejected").exists()
            first = await save_capture(entrance, models[0], f"{folders[0]}/01", entrance_step, tmp_path)
            second = await save_capture(courtyard, models[1], f"{folders[1]}/02", courtyard_step, tmp_path)
            assert await step_refs(courtyard, entrance_step) == [first]
            assert await step_refs(entrance, courtyard_step) == [second]
            assert await step_refs(entrance, {**courtyard_step, "loop_no": 1}) == []
            assert (tmp_path / first).read_bytes() != (tmp_path / second).read_bytes()

            rejected = await entrance.call_tool("capture_04-defined_view", {
                "target_kind": "layout", "target": "Entrance", "scale_percent": FULL_SCALE,
                "width": CAPTURE_SIZE, "height": CAPTURE_SIZE,
            })
            assert rejected.is_error
            value = rejected.structured_content
            assert set(value) == {"status", "message", "error_code"}
            assert value["status"] == "error" and value["error_code"] == "invalid_arguments"
            assert json.loads(rejected.content[0].text) == value

    asyncio.run(run())
