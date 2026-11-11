"""Exercise the actual cold stdio protocol and external schema composition."""
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from almond_mcp import paths
from almond_mcp.modeling_guidance import BASIC_GUIDE, read_policy, startup_instructions
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def assert_information_placement(tools):
    """Check the user's reading order at the wire boundary, beyond parity."""
    for name, tool in tools.items():
        role = tool.get("description", "")
        assert role.strip(), name
        assert not any(marker in role for marker in ("Args:", "Returns:", "반환:", "선택된 연결에서")), name
        for field in tool["inputSchema"].get("properties", {}).values():
            help_text = field.get("description", "").strip()
            assert not help_text or help_text not in role, name
    detail = tools["get_phase_plan_step"]
    assert "상세 내용의 포함 여부" not in detail["description"]
    assert "상세" in detail["inputSchema"]["properties"]["include_details"]["description"]
    assert "Phase·Scene·상태로" not in tools["list_plans"]["description"]
    phase = tools["create_phase"]["inputSchema"]["properties"]
    assert set(phase["status"]["enum"]) == {"pending", "running", "paused", "completed", "failed", "blocked"}
    assert {option["type"] for option in phase["file_name"]["anyOf"]} == {"string", "array"}
    assert "중 하나" in phase["status"]["description"]
    assert "문자열 배열" in phase["file_name"]["description"]
    scene_file = tools["create_design_scene"]["inputSchema"]["properties"]["file_name"]["description"]
    assert "파일 작업이 아닙니다" not in scene_file and "파일명" in scene_file
    if "execute_looping" in tools:
        loop = tools["execute_looping"]
        assert "회차가 끝나면" not in loop["description"]
        assert "새 회차" in loop["inputSchema"]["properties"]["resume"]["description"]


def assert_documented_schema(schema, path):
    """Every input field, including typed nested edits, must carry callable help."""
    Draft202012Validator.check_schema(schema)

    def visit(node, location, inherited=frozenset()):
        if isinstance(node, dict):
            documented = set(inherited)
            for name, prop in node.get("properties", {}).items():
                if isinstance(prop.get("description"), str) and prop["description"].strip():
                    documented.add(name)
                assert name in documented, (location, name)
            for key, value in node.items():
                # Composition may constrain a field whose help belongs to this object.
                visit(value, f"{location}/{key}", documented if key in {"anyOf", "oneOf", "allOf", "if", "then", "else"} else frozenset())
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{location}/{index}", inherited)

    visit(schema, path)


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
            basic_result = await client.call_tool("get_policy", {})
            assert not basic_result.is_error
            basic = json.loads(basic_result.content[0].text)
            assert "list_project_files" not in tools and "list_project_files" not in basic["tools"]
            assert basic["text"] == BASIC_GUIDE.read_text(encoding="utf-8").strip()
            # The Rhino-bound launcher publishes its first-use guidance through
            # initialize; the shared standalone server remains instruction-free.
            expected_instructions = startup_instructions() if bound else None
            assert initialized.instructions == expected_instructions
            assert initialized.server_info.description is None
            for name, item in tools.items():
                assert_documented_schema(item["inputSchema"], name)
                Draft202012Validator.check_schema(item["outputSchema"])
                assert item["description"].strip(), name
                assert "Almond inspects and edits Rhino" not in item["description"], name
                assert "guide_version=" not in item["description"], name
            scripting_result = await client.call_tool("get_policy", {"policy": "rhino_scripting"})
            assert not scripting_result.is_error
            scripting = json.loads(scripting_result.content[0].text)
            assert scripting == read_policy("rhino_scripting")
            assert scripting["guide_version"] == basic["guide_version"]
            rejected = await client.call_tool("get_policy", {"tool": "get_rhino_context"})
            assert rejected.is_error
            detail_name = "get_phase_plan_step"
            assert detail_name in tools and detail_name in basic["tools"]
            assert tools[detail_name]["title"] == "get_phase·plan·step"
            assert "get_phase·plan·step" not in tools
            assert not {"get_phase", "get_plan", "get_step"}.intersection(tools)

            async def call(name, arguments):
                response = await client.call_tool(name, arguments)
                assert not response.is_error
                value = json.loads(response.content[0].text)
                output = tools[name]["outputSchema"]
                if output.get("x-fastmcp-wrap-result"):
                    output = output["properties"]["result"]["contentSchema"]
                Draft202012Validator(output).validate(value)
                return value

            phase = (await call("create_phase", {"name": "Stdio discovery", "depends_on": ["phase_future"]}))["phase"]
            plan = (await call("create_plan", {"title": "Entrance review", "goal": "Inspect entrance", "phase_id": phase["phase_id"]}))["plan"]
            rows = await call("list_plans", {"phase_id": phase["phase_id"]})
            assert rows["plans"][0]["title"] == "Entrance review"
            assert "goal" not in rows["plans"][0] and detail_name in rows["next_step_guide"]
            detail = await call(detail_name, {"include_details": True, "plan_id": plan["plan_id"]})
            assert detail["id"] == plan["plan_id"] and detail["status"] == "pending"
            assert detail["plan"]["phase"] == {"phase_id": phase["phase_id"], "name": "Stdio discovery"}
            sid = detail["plan"]["steps"][0]["step_id"]
            assert "set_working_plan" in detail["next_step_guide"]
            partial = await call("update_step", {"plan_id": plan["plan_id"], "step_id": sid,
                "output_refs": {"add": ["survey.md", "survey.md"], "remove": ["absent.md"]}})
            assert partial["status"] == "partial_success" and partial["changed"] is True
            assert {issue["reason"] for issue in partial["issues"]} == {"duplicate_input", "not_found"}
            step = await call(detail_name, {"include_details": True, "plan_id": plan["plan_id"], "step_id": sid})
            assert step["step"]["output_refs"] == ["survey.md"]
            assert step["status"] == "pending" and "set_working_plan" in step["next_step_guide"]
            assert step["revision"] == plan["revision"] + 1
            historic = await call(detail_name, {"include_details": True, "plan_id": plan["plan_id"], "step_id": sid, "revision": plan["revision"]})
            assert historic["step"]["output_refs"] == []
            assert "revision을 생략" in historic["next_step_guide"]
            if bound:
                result = await client.call_tool("project_info", {})
                assert not result.is_error
                info = json.loads(result.content[0].text)
                project = info["project"]
                assert project["file_name"] == "disposable.3dm"
                assert project["file_path"] == "disposable.3dm"
                assert project["is_bound_document"] is True
                assert project["files"] == [{"file_name": "disposable.3dm"}]
                assert project["files_page"]["total"] == 1
                assert info["locations"]["database"] == ".almond/scene.sqlite3"
                assert info["locations"]["artifact_dir"] is None
                assert not {"root_variable_set", "root_variable", "database"}.intersection(project)
                assert not {"name", "path", "runtime_serial_number", "live_document_checked", "is_bound_document"}.intersection(info["document"])
                rejected = await client.call_tool("list_project_files", {})
                assert rejected.is_error
                selected = await call("set_working_plan", {"plan_id": plan["plan_id"], "step_id": sid})
                assert selected["revision"] == step["revision"] + 1
                updated = await call("update_step", {"plan_id": plan["plan_id"], "step_id": sid,
                    "output_refs": {"add": ["selected-survey.md"], "remove": ["survey.md"]}, "expected_revision": selected["revision"]})
                assert updated["status"] == "success" and updated["plan"]["revision"] == selected["revision"] + 1
            return initialized.instructions, tools


def test_cold_direct_full_descriptions_and_basic_scripting_guide(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c",
        "from almond_mcp.server import mcp; mcp.run()"], env=isolated_environment(tmp_path))
    instructions, tools = asyncio.run(collect(params, bound=False))
    assert "get_rhino_context" in tools
    assert not instructions
    assert "get_policy" in tools


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
    assert worker["get_phase_plan_step"]["title"] == expected["get_phase_plan_step"]["title"] == "get_phase·plan·step"
    exposed, mapping = exposed_tools(catalog)
    external = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in exposed}
    for name in worker:
        assert mapping[name] == name
        assert external[name]["description"] == worker[name]["description"]
        routed = external[name]["inputSchema"]
        assert routed["properties"]["connection_id"]["type"] == "string"
        assert all(routed["properties"][key] == value for key, value in worker[name]["inputSchema"].get("properties", {}).items())


def test_both_external_host_routes_publish_same_real_stdio_schemas(tmp_path):
    from runtime import load_catalog
    from external_host import exposed_tools
    expected_tools, _ = exposed_tools(load_catalog())
    expected = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in expected_tools}

    async def inspect(client_name):
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
                assert initialized.instructions  # External-host instructions are a separate contract.
                for text in (initialized.instructions, initialized.server_info.description):
                    assert not any(name in text for name in ("host_id", "model_path", "connection_id", "request_id"))
                assert "connection_id" not in tools["disconnect"]["inputSchema"]["required"]
                assert "생략" in tools["disconnect"]["inputSchema"]["properties"]["connection_id"]["description"]
                assert tools == expected
                for name, tool in tools.items():
                    assert_documented_schema(tool["inputSchema"], name)
                return initialized.server_info.name

    for name, label in (("codex", "beyond"), ("cos", "CoS")):
        (tmp_path / name).mkdir()
        assert asyncio.run(inspect(name)) == label


def test_plan_section_bound_schema_and_external_argument_routing(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=isolated_environment(tmp_path))
    _, worker = asyncio.run(collect(params, bound=True))
    from runtime import load_catalog, schema_identity
    from external_host import Broker, json_result
    from types import SimpleNamespace
    catalog = next(t for t in load_catalog()["tools"] if t["name"] == "plan_section")
    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf-8"))["plan_section"]
    assert schema_identity(worker["plan_section"]) == schema_identity(catalog) == baseline
    arguments = dict(connection_id="fixture", operation="Create", clipping_ids=["00000000-0000-0000-0000-000000000001"])
    observed = []

    async def invoke(conn, name, payload, invocation):
        observed.append((conn, name, payload))
        return json_result({"status": "success"})

    async def route():
        broker = SimpleNamespace(mapping={"plan_section": "plan_section"}, connections={"fixture": "bound"},
                                 invoke=invoke, spawn=asyncio.create_task, selected_connection_id=None)
        response = await Broker.call(broker, "plan_section", arguments)
        assert not response.is_error

    asyncio.run(route())
    assert observed == [("bound", "plan_section", {key: value for key, value in arguments.items() if key != "connection_id"})]
    assert arguments["connection_id"] == "fixture"
