"""Exercise the actual cold stdio protocol and external schema composition."""
import asyncio
import json
import os
from pathlib import Path
import re
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from almond_mcp import paths
import ast
from almond_mcp.tool_declarations import declaration_sources, inspect_declarations
from almond_mcp.modeling_guidance import BASIC_SUMMARY, read_policy, startup_instructions
from jsonschema import Draft202012Validator
from render_tool_declarations import render_catalogs

ROOT = Path(__file__).resolve().parents[2]


def request_properties(tool, target):
    request = tool["inputSchema"]["properties"]["request"]
    return next(branch["properties"] for branch in request["oneOf"]
                if branch["properties"]["target"]["const"] == target)


def assert_information_placement(tools):
    """Check the user's reading order at the wire boundary, beyond parity."""
    assert not any(name.startswith("exchange_") for name in tools)
    assert {"export_asset_contract", "get_blender_helper_script", "import_asset_contract",
            "publish_objects_to_chestnut", "publish_to_chestnut"}.isdisjoint(tools)
    for name, tool in tools.items():
        role = tool.get("description", "")
        assert role.strip(), name
        assert not any(marker in role for marker in ("Args:", "Returns:", "반환:", "선택된 연결에서")), name
        for field in tool["inputSchema"].get("properties", {}).values():
            help_text = field.get("description", "").strip()
            assert not help_text or help_text not in role, name
    detail = tools["plan_05-get"]
    assert "상세 내용의 포함 여부" not in detail["description"]
    assert request_properties(detail, "phase")["include_details"] == {"type": "boolean", "default": False}
    assert "Phase·Scene·상태로" not in tools["plan_08-list"]["description"]
    phase = request_properties(tools["plan_02-create"], "phase")
    assert set(phase["status"]["enum"]) == {"pending", "running", "paused", "completed", "failed", "blocked"}
    assert {option["type"] for option in phase["file_name"]["anyOf"]} == {"string", "array"}
    assert phase["status"]["default"] == "pending"
    assert "description" not in phase["status"]
    assert "context_04-get_project_info tool" in phase["file_name"]["description"]
    scene_file = tools["scene_02-create"]["inputSchema"]["properties"]["file_name"]["description"]
    assert "파일 작업이 아닙니다" not in scene_file and "파일명" in scene_file
    if "plan_03-execute_looping" in tools:
        loop = tools["plan_03-execute_looping"]
        assert "회차가 끝나면" not in loop["description"]
        assert "새 회차" in loop["inputSchema"]["properties"]["resume"]["description"]
    assert {"inspect_02-get_objects", "capture_03-current_view", "intersect_02-resolve",
            "model_05-setup", "drawing_06-generate_plan_section", "script_02-run_rhino"} <= tools.keys()
    context = tools["inspect_03-get_document_context"]["outputSchema"]["properties"]["result"]["contentSchema"]["properties"]
    assert "description" not in context["layer_tree"]
    for field in ("named_views", "layouts"):
        assert "description" not in context[field]
        assert all("description" not in prop for prop in context[field]["items"]["properties"].values())
    material = tools["model_01-assign_material"]["outputSchema"]["properties"]["result"]["contentSchema"]
    assert material["properties"]["result_error"] == {"type": "string"}
    for tool_name, field_name, reference in (
        ("drawing_01-apply_style", "recipe_id", "drawing_05-list_recipes"),
        ("drawing_01-apply_style", "recipe_id", "drawing_02-get_recipe"),
        ("drawing_02-get_recipe", "recipe_id", "drawing_05-list_recipes"),
    ):
        assert reference in tools
        assert reference + " tool" in tools[tool_name]["inputSchema"]["properties"][field_name]["description"]
    # Public tool references in all exposed help must retain the AGENTS suffix.
    def assert_tool_reference_suffix(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "description" and isinstance(child, str):
                    for match in re.finditer(r"[a-z]+_\d{2}-[a-z_]+", child):
                        if match.group() in tools:
                            assert child[match.end():].lstrip("`").startswith(" tool"), child
                else:
                    assert_tool_reference_suffix(child)
        elif isinstance(value, list):
            for child in value:
                assert_tool_reference_suffix(child)

    for tool in tools.values():
        assert_tool_reference_suffix(tool)
        published = json.dumps(tool, ensure_ascii=False)
        assert "drawing_01-list_recipes" not in published
        assert "drawing_05-generate_plan_section" not in published


def isolated_environment(tmp_path):
    env = dict(os.environ)
    env["ALMOND_TEST_ROOT"] = str(tmp_path)
    env["RHINO_MCP_STATE_DB"] = str(tmp_path / "direct.sqlite3")
    env["PYTHONPATH"] = os.pathsep.join(str(ROOT / p) for p in ("src/mcp", "src/mcp/runtime", "src/cos"))
    for variable in paths.LIBRARY_DIRS:
        folder = tmp_path / variable
        folder.mkdir()
        env[variable] = str(folder)
    return env


async def collect(params, *, bound):
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
            initialized = await client.initialize()
            tools = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for t in (await client.list_tools()).tools}
            assert_information_placement(tools)
            basic_result = await client.call_tool("context_01-get_policy", {})
            assert not basic_result.is_error
            basic = json.loads(basic_result.content[0].text)
            assert "list_project_files" not in tools and "list_project_files" not in basic["tools"]
            catalog_tool = "context_05-upsert_project_file"
            assert (catalog_tool in tools) == bound
            assert catalog_tool in basic["tools"]
            assert basic["text"] == BASIC_SUMMARY
            policy_input = tools["context_01-get_policy"]["inputSchema"]["properties"]["policy"]
            assert policy_input["default"] == ""
            assert policy_input["enum"] == ["", *basic["available_policies"]]
            # The Rhino-bound launcher publishes its first-use guidance through
            # initialize; the shared standalone server remains instruction-free.
            expected_instructions = startup_instructions() if bound else None
            assert initialized.instructions == expected_instructions
            assert initialized.server_info.description is None
            for name, item in tools.items():
                Draft202012Validator.check_schema(item["inputSchema"])
                Draft202012Validator.check_schema(item["outputSchema"])
                assert item["description"].strip(), name
                assert "Almond inspects and edits Rhino" not in item["description"], name
                assert "guide_version=" not in item["description"], name
            scripting_result = await client.call_tool("context_01-get_policy", {"policy": "rhino_scripting"})
            assert not scripting_result.is_error
            scripting = json.loads(scripting_result.content[0].text)
            assert scripting == read_policy("rhino_scripting")
            assert scripting["guide_version"] == basic["guide_version"]
            activity_result = await client.call_tool("context_01-get_policy", {"policy": "observation"})
            assert activity_result.is_error
            rejected = await client.call_tool("context_01-get_policy", {"tool": "inspect_03-get_document_context"})
            assert rejected.is_error
            detail_name = "plan_05-get"
            assert detail_name in tools and detail_name in basic["tools"]
            retired = {"get_phase", "get_plan", "get_step", "get_phase·plan·step",
                       "plan_01-create_phase", "plan_05-get_phase_plan_step", "plan_06-list_phases",
                       "plan_11-update_phase", "plan_13-update_step"}
            assert retired.isdisjoint(tools) and retired.isdisjoint(basic["tools"])

            async def call(name, arguments):
                response = await client.call_tool(name, arguments)
                assert not response.is_error
                value = json.loads(response.content[0].text)
                output = tools[name]["outputSchema"]
                if output.get("x-fastmcp-wrap-result"):
                    output = output["properties"]["result"]["contentSchema"]
                Draft202012Validator(output).validate(value)
                return value

            phase = (await call("plan_02-create", {"request": {
                "target": "phase", "name": "Stdio discovery", "depends_on": ["phase_future"],
            }}))["phase"]
            plan = (await call("plan_02-create", {"request": {
                "target": "plan", "title": "Entrance review", "goal": "Inspect entrance", "phase_id": phase["phase_id"],
            }}))["plan"]
            pid = plan["plan_id"]
            rows = await call("plan_08-list", {"request": {"target": "plan", "phase_id": phase["phase_id"]}})
            assert rows["plans"][0]["title"] == "Entrance review"
            assert "goal" not in rows["plans"][0] and detail_name in rows["next_step_guide"]
            detail = await call(detail_name, {"request": {"target": "plan", "include_details": True, "plan_id": pid}})
            assert detail["id"] == pid and detail["status"] == "pending"
            assert detail["plan"]["phase"] == {"phase_id": phase["phase_id"], "name": "Stdio discovery"}
            steps = await call("plan_08-list", {"request": {"target": "step", "plan_id": pid}})
            assert steps["steps"] == detail["plan"]["steps"]
            sid = detail["plan"]["steps"][0]["step_id"]
            assert "plan_10-set_working" in detail["next_step_guide"]
            step_request = {"target": "step", "plan_id": pid, "step_id": sid}
            partial = await call("plan_12-update", {"request": {
                **step_request, "output_refs": {"add": ["survey.md", "survey.md"], "remove": ["absent.md"]},
            }})
            assert partial["status"] == "partial_success" and partial["changed"] is True
            assert {issue["reason"] for issue in partial["issues"]} == {"duplicate_input", "not_found"}
            step = await call(detail_name, {"request": {**step_request, "include_details": True}})
            assert step["step"]["output_refs"] == ["survey.md"]
            assert step["status"] == "pending" and "plan_10-set_working" in step["next_step_guide"]
            assert step["revision"] == plan["revision"] + 1
            historic = await call(detail_name, {"request": {
                **step_request, "include_details": True, "revision": plan["revision"],
            }})
            assert historic["step"]["output_refs"] == []
            assert "revision을 생략" in historic["next_step_guide"]
            if bound:
                result = await client.call_tool("context_04-get_project_info", {})
                assert not result.is_error
                info = json.loads(result.content[0].text)
                project = info["project"]
                assert project["file_name"] == "disposable.3dm"
                assert project["file_path"] == "disposable.3dm"
                assert project["is_bound_document"] is True
                assert project["files"] == [{"file_name": "disposable.3dm", "description": None}]
                assert project["worksession_files"] == []
                assert project["files_page"]["total"] == 1
                assert info["locations"]["database"] == ".almond/scene.sqlite3"
                assert info["locations"]["artifact_dir"] is None
                assert not {"root_variable_set", "root_variable", "database"}.intersection(project)
                assert not {"name", "path", "runtime_serial_number", "live_document_checked", "is_bound_document"}.intersection(info["document"])
                rejected = await client.call_tool("list_project_files", {})
                assert rejected.is_error
                catalog = await call("context_05-upsert_project_file", {
                    "file_name": "survey.3dm", "description": "Model used for survey review",
                })
                assert catalog == {"status": "success", "file_name": "survey.3dm",
                                   "description": "Model used for survey review"}
                updated_info = await call("context_04-get_project_info", {})
                assert updated_info["project"]["files"][-1]["file_name"] == "survey.3dm"
                assert updated_info["project"]["worksession_files"] == []
                selected = await call("plan_10-set_working", {"plan_id": pid, "step_id": sid})
                assert selected["revision"] == step["revision"] + 1
                updated = await call("plan_12-update", {"request": {
                    **step_request, "output_refs": {"add": ["selected-survey.md"], "remove": ["survey.md"]},
                    "expected_revision": selected["revision"],
                }})
                assert updated["status"] == "updated" and updated["plan"]["revision"] == selected["revision"] + 1
            return initialized.instructions, tools


def test_cold_direct_full_descriptions_and_basic_scripting_guide(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c",
        "from almond_mcp.server import mcp; mcp.run()"], env=isolated_environment(tmp_path))
    instructions, tools = asyncio.run(collect(params, bound=False))
    assert "inspect_03-get_document_context" in tools
    assert not instructions
    assert "context_01-get_policy" in tools


def test_bound_worker_reads_checkout_recipes_with_legacy_launcher_path(tmp_path):
    env = isolated_environment(tmp_path)
    key = paths.DRAWING_RECIPE_ENV
    env[key] = str(paths.user_data_dir() / "DrawingRecipes")
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=env)
    directory = ROOT / "asset/drawing/DrawingRecipes"

    async def check():
        async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as client:
            await client.initialize()
            worker = json.loads(next(tmp_path.rglob("worker.json")).read_text(encoding="utf-8"))
            assert Path(worker["library_dirs"][key]) == directory
            listed = await client.call_tool("drawing_05-list_recipes", {"include_ids": True})
            ids = {row["recipe_id"] for row in json.loads(listed.content[0].text)["recipes"]}
            recipes = sorted(directory.glob("*.json"))
            assert recipes
            expected_ids = set()
            for recipe_path in recipes:
                recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
                recipe_id = recipe.pop("recipe_id")
                expected_ids.add(recipe_id)
                detail = await client.call_tool("drawing_02-get_recipe", {
                    "recipe_id": recipe_id, "field_groups": ["all"]})
                assert json.loads(detail.content[0].text)["recipe"] == recipe
            assert ids == expected_ids

    asyncio.run(check())


def test_bound_serve_and_external_catalog_identity(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=isolated_environment(tmp_path))
    _, worker = asyncio.run(collect(params, bound=True))
    from runtime import load_catalog, schema_identity, validate_worker_tools
    from external_host import exposed_tools
    catalog = load_catalog()
    expected = {tool["name"]: tool for tool in catalog["tools"]}
    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf-8"))
    assert set(worker) == set(expected)
    assert {name: schema_identity(tool) for name, tool in worker.items()} == baseline
    validate_worker_tools(catalog, list(worker.values()))
    assert all(schema_identity(worker[n]) == schema_identity(expected[n]) for n in worker)
    assert all(worker[n]["description"] == expected[n]["description"] for n in worker)
    assert worker["plan_05-get"]["title"] == expected["plan_05-get"]["title"] == "Plan 05 Get"
    exposed = exposed_tools(catalog)
    external = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in exposed}
    policy_declaration = next(item for item in inspect_declarations(declaration_sources())
                              if item.name == "context_01-get_policy")
    policy_instruction = ast.get_docstring(policy_declaration.node)
    role, arguments = policy_instruction.split("\n\nArgs:\n", 1)
    policy_tool = external["context_01-get_policy"]
    assert policy_tool["description"] == role
    assert set(policy_tool["inputSchema"]["properties"]) == {"policy"}
    assert policy_tool["inputSchema"]["properties"]["policy"]["description"] == arguments.strip().removeprefix("policy: ")
    for name in worker:
        assert external[name]["description"] == worker[name]["description"]
        assert external[name]["inputSchema"] == worker[name]["inputSchema"]


def test_external_host_routes_publish_their_real_stdio_schemas(tmp_path):
    from runtime import load_catalog
    from external_host import exposed_tools
    catalog = load_catalog()
    unrouted = {"context_01-get_policy", "connect_01-list_up", "connect_02-session", "connect_03-start_session"}

    async def inspect(client_name, label):
        explicit = client_name == "codex"
        expected_tools = exposed_tools(catalog, explicit_connections=explicit)
        expected = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in expected_tools}
        code = ("import os; from pathlib import Path; from external_host import main; "
                f"main(Path(os.environ['ALMOND_TEST_ROOT']), client='{client_name}')")
        params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c", code],
                                       env=isolated_environment(tmp_path / client_name))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                initialized = await client.initialize()
                tools = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                         for t in (await client.list_tools()).tools}
                assert_information_placement(tools)
                assert startup_instructions() in initialized.instructions
                for text in (initialized.instructions, initialized.server_info.description):
                    assert not any(name in text for name in ("host_id", "model_path", "connection_id", "request_id"))
                assert tools == expected
                for name in ("connect_02-session", "connect_03-start_session"):
                    field = tools[name]["outputSchema"]["properties"]["connection_id"]
                    assert ("현재 대화의 변수에 함께 저장" in field.get("description", "")) == explicit
                for name, tool in tools.items():
                    schema = tool["inputSchema"]
                    routed = explicit and name not in unrouted
                    assert ("connection_id" in schema.get("properties", {})) == routed, name
                    assert ("connection_id" in schema.get("required", [])) == routed, name
                    Draft202012Validator.check_schema(tool["inputSchema"])
                if explicit:
                    for name in ("context_04-get_project_info", "connect_05-close_session"):
                        missing = await client.call_tool(name, {})
                        assert missing.is_error
                        assert [item.text for item in missing.content] == ["connection_id가 지정되지 않았습니다"]
                rejected = await client.call_tool("context_04-get_project_info", {"connection_id": "old"})
                assert rejected.is_error
                assert initialized.server_info.name == label
                return tools

    catalogs = {}
    for name, label in (("codex", "beyond"), ("cos", "CoS")):
        (tmp_path / name).mkdir()
        catalogs[label] = asyncio.run(inspect(name, label))
    assert (ROOT / "TOOL-DECLARATIONS-CURRENT.md").read_text(encoding="utf-8") == render_catalogs(catalogs["CoS"], catalogs["beyond"])


def test_codex_first_tools_list_contains_only_the_common_advertised_capture_guids(tmp_path):
    from uuid import uuid4
    from winpipe import process_identity

    shared, only_first, only_second = (str(uuid4()) for _ in range(3))
    directory = tmp_path / "hosts"
    directory.mkdir()
    for ids in ([shared, only_first], [only_second, shared]):
        host_id = uuid4().hex
        advertisement = dict(schema="almond-rhino-host", protocol=1, host_id=host_id,
                             **process_identity(os.getpid()), display_mode_ids=ids)
        (directory / (host_id + ".json")).write_text(json.dumps(advertisement), encoding="utf8")
    code = ("import os; from pathlib import Path; from external_host import main; "
            "main(Path(os.environ['ALMOND_TEST_ROOT']), client='codex')")
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c", code],
                                   env=isolated_environment(tmp_path))

    async def inspect():
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                await client.initialize()
                schemas = {tool.name: tool.input_schema["properties"] for tool in (await client.list_tools()).tools}
                assert schemas["capture_01-conditioning_pass"]["rgb_mode"]["enum"] == [shared]
                assert schemas["capture_01-conditioning_pass"]["edge_mode"]["enum"] == [shared]
                tile = schemas["capture_02-inspection"]["views"]["items"]["properties"]
                assert tile["display_mode"]["enum"] == [shared]
                for name in ("capture_03-current_view", "capture_04-defined_view"):
                    assert schemas[name]["display_mode"]["enum"] == [shared]
                rejected = await client.call_tool("capture_03-current_view", {
                    "connection_id": uuid4().hex, "display_mode": only_first})
                assert rejected.is_error

    asyncio.run(inspect())


def test_plan_section_bound_schema_and_external_argument_routing(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=isolated_environment(tmp_path))
    _, worker = asyncio.run(collect(params, bound=True))
    from runtime import load_catalog, schema_identity
    from external_host import Broker, json_result
    from types import SimpleNamespace
    catalog = next(t for t in load_catalog()["tools"] if t["name"] == "drawing_06-generate_plan_section")
    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf-8"))["drawing_06-generate_plan_section"]
    assert schema_identity(worker["drawing_06-generate_plan_section"]) == schema_identity(catalog) == baseline
    assert "drawing_03-get_plan_section_result" not in worker
    clipping_id = "00000000-0000-0000-0000-000000000001"
    arguments = dict(operation="Move", clipping_ids=[clipping_id], points={clipping_id: [0, 0, -10]})
    observed = []

    async def invoke(conn, name, payload, invocation):
        observed.append((conn, name, payload))
        return json_result({"status": "success"})

    async def route():
        broker = SimpleNamespace(worker_tool_names={"drawing_06-generate_plan_section"}, connections={"fixture": "bound"},
                                 explicit_connections=False, invoke=invoke, spawn=asyncio.create_task, selected_connection_id="fixture")
        response = await Broker.call(broker, "drawing_06-generate_plan_section", arguments)
        assert not response.is_error

    asyncio.run(route())
    assert observed == [("bound", "drawing_06-generate_plan_section", arguments)]
