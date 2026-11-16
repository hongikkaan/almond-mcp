"""Exercise the actual cold stdio protocol and external schema composition."""
import asyncio
import json
import ntpath
import os
from pathlib import Path
import re
import sys
import pytest

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from almond_mcp import paths
from almond_mcp.instruction_text import read_tool_instruction
from almond_mcp.modeling_guidance import BASIC_GUIDE, read_policy, startup_instructions
from almond_mcp import modeling_guidance
from almond_mcp.required_guidance import REQUIRED_DOCUMENTS, load_required_guidance
from jsonschema import Draft202012Validator

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
    assert "상세" in request_properties(detail, "phase")["include_details"]["description"]
    assert "Phase·Scene·상태로" not in tools["plan_08-list"]["description"]
    phase = request_properties(tools["plan_02-create"], "phase")
    assert set(phase["status"]["enum"]) == {"pending", "running", "paused", "completed", "failed", "blocked"}
    assert {option["type"] for option in phase["file_name"]["anyOf"]} == {"string", "array"}
    assert phase["status"]["description"] == "생략하면 pending."
    assert phase["file_name"]["description"] == "연결할 파일명 하나 또는 배열. 생략하면 파일 연결 없음."
    scene_file = tools["scene_02-create"]["inputSchema"]["properties"]["file_name"]["description"]
    assert "파일 작업이 아닙니다" not in scene_file and "파일명" in scene_file
    if "plan_03-execute_looping" in tools:
        loop = tools["plan_03-execute_looping"]
        assert "회차가 끝나면" not in loop["description"]
        assert "새 회차" in loop["inputSchema"]["properties"]["resume"]["description"]
    # The reviewed document owns wording; Drawing renumbering remains separate.
    aliases = {"drawing_01-list_recipes": "drawing_05-list_recipes",
               "drawing_03-apply_style": "drawing_01-apply_style",
               "drawing_05-generate_plan_section": "drawing_06-generate_plan_section",
               "drawing_06-get_plan_section_result": "drawing_03-get_plan_section_result"}
    document = (ROOT / "TOOL-DECLARATIONS-CURRENT.md").read_text(encoding="utf-8")
    for section in re.split(r"(?m)^### ", document)[1:]:
        name = section.splitlines()[0].split(". ", 1)[1].replace("\\_", "_")
        name = aliases.get(name, name)
        if name in tools:
            description = re.search(r"```txt\n(.*?)\n```", section, re.S).group(1)
            assert tools[name]["description"] == description, name
    for tool_name, field_name, reference in (
        ("drawing_01-apply_style", "recipe_id", "drawing_05-list_recipes"),
        ("drawing_01-apply_style", "recipe_id", "drawing_02-get_recipe"),
        ("drawing_02-get_recipe", "recipe_id", "drawing_05-list_recipes"),
        ("drawing_03-get_plan_section_result", "result_id", "drawing_06-generate_plan_section"),
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


@pytest.fixture
def required_sources(tmp_path, monkeypatch):
    """Explicit test content; final production documents remain a release gate."""
    folder = tmp_path / "required-guidance-fixture"
    folder.mkdir()
    sources = {name: folder / name for name in REQUIRED_DOCUMENTS}
    for name, path in sources.items():
        if name == "BASIC-INSTRUCTIONS.md":
            path.write_bytes(BASIC_GUIDE.read_bytes())
        else:
            path.write_text(f"{name}: first\n" + "한글 전달 검증 " * 20_000 + f"\n{name}: last\n", encoding="utf-8")
    monkeypatch.setattr(modeling_guidance, "REQUIRED_GUIDE_SOURCES", sources)
    monkeypatch.delenv("ALMOND_GUIDANCE_FORMAT", raising=False)
    return sources


def assert_full_guidance(instructions, sources, delivery):
    """Inspect the entire initialize payload, including the JSON representation."""
    bundle = load_required_guidance(sources)
    if delivery == "fields":
        fields = json.loads(instructions)
        assert set(fields) == {*REQUIRED_DOCUMENTS, "_metadata"}
        assert fields["_metadata"]["required_guidance_version"] == bundle.version
        assert fields["_metadata"]["guide_version"] == read_policy()["guide_version"]
        for document in bundle.documents:
            assert fields[document.name] == document.text
            assert fields["_metadata"]["sha256"][document.name] == document.sha256
            assert instructions.count(json.dumps(document.text, ensure_ascii=False)) == 1
    else:
        assert bundle.instructions() in instructions
        for document in bundle.documents:
            assert instructions.count(document.text) == 1
        assert instructions.index("BEGIN REQUIRED DOCUMENT BASIC-INSTRUCTIONS.md") < instructions.index("BEGIN REQUIRED DOCUMENT design_judgment.md")


def isolated_environment(tmp_path, required_sources=None):
    env = dict(os.environ)
    env["ALMOND_TEST_ROOT"] = str(tmp_path)
    env["RHINO_MCP_STATE_DB"] = str(tmp_path / "direct.sqlite3")
    env["PYTHONPATH"] = os.pathsep.join(str(ROOT / p) for p in ("src/mcp", "src/mcp/runtime", "src/cos"))
    if required_sources is not None:
        env["ALMOND_TEST_GUIDANCE_DIR"] = str(next(iter(required_sources.values())).parent)
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
            assert basic["text"] == BASIC_GUIDE.read_text(encoding="utf-8").strip()
            policy_input = tools["context_01-get_policy"]["inputSchema"]["properties"]["policy"]
            assert policy_input["default"] == ""
            assert policy_input["enum"] == ["", *basic["available_policies"]]
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
            scripting_result = await client.call_tool("context_01-get_policy", {"policy": "rhino_scripting"})
            assert not scripting_result.is_error
            scripting = json.loads(scripting_result.content[0].text)
            assert scripting == read_policy("rhino_scripting")
            assert scripting["guide_version"] == basic["guide_version"]
            activity_result = await client.call_tool("context_01-get_policy", {"policy": "observation"})
            assert not activity_result.is_error
            assert json.loads(activity_result.content[0].text) == activity_result.structured_content == read_policy("observation")
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
                assert project["files"] == [{"file_name": "disposable.3dm", "filename": "disposable.3dm", "description": ""}]
                assert project["files_page"]["total"] == 1
                assert info["named_views"] == [{"name": "Arrival", "id": "fixture-view"}]
                assert info["layouts"] == []
                assert info["layers"] == "- Building\n  - Wall"
                assert info["worksession"] == {"attachments": [{"filename": "reference.3dm", "path": "reference.3dm"}]}
                sections = ["named_views", "layouts", "layers", "worksession"]
                inspected = await call("inspect_03-get_document_context", {"sections": sections})
                assert {key: info[key] for key in sections} == {key: inspected[key] for key in sections}
                assert info["locations"]["database"] == ".almond/scene.sqlite3"
                assert info["locations"]["artifact_dir"] is None
                assert not {"root_variable_set", "root_variable", "database"}.intersection(project)
                assert not {"name", "path", "runtime_serial_number", "live_document_checked", "is_bound_document"}.intersection(info["document"])
                rejected = await client.call_tool("list_project_files", {})
                assert rejected.is_error
                selected = await call("plan_10-set_working", {"plan_id": pid, "step_id": sid})
                assert selected["revision"] == step["revision"] + 1
                updated = await call("plan_12-update", {"request": {
                    **step_request, "output_refs": {"add": ["selected-survey.md"], "remove": ["survey.md"]},
                    "expected_revision": selected["revision"],
                }})
                assert updated["status"] == "success" and updated["plan"]["revision"] == selected["revision"] + 1
            return initialized.instructions, tools


def test_cold_direct_full_descriptions_and_basic_scripting_guide(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c",
        "from almond_mcp.server import mcp; mcp.run()"], env=isolated_environment(tmp_path))
    instructions, tools = asyncio.run(collect(params, bound=False))
    assert "inspect_03-get_document_context" in tools
    assert not instructions
    assert "context_01-get_policy" in tools


@pytest.mark.parametrize("route", ["bound", "codex", "cos"])
@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_package_sources_initialize_without_guidance_override(tmp_path, monkeypatch, route, delivery):
    """The actual checkout's mandatory files must initialize every client route."""
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)
    env = isolated_environment(tmp_path)
    env.pop("ALMOND_TEST_GUIDANCE_DIR", None)
    if route == "bound":
        args = ["-B", "-X", "utf8", "-u", str(ROOT / "tests/integration/bound_server_fixture.py")]
        introduction = ""
    else:
        from external_host import server_description
        code = ("import os; from pathlib import Path; from external_host import main; "
                f"main(Path(os.environ['ALMOND_TEST_ROOT']), client='{route}')")
        args = ["-B", "-X", "utf8", "-u", "-c", code]
        introduction = server_description(route)
    params = StdioServerParameters(command=sys.executable, args=args, env=env)

    async def initialize():
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                return await client.initialize()

    initialized = asyncio.run(initialize())
    assert initialized.instructions == startup_instructions(delivery, introduction=introduction)
    sources = {name: ROOT / "src/mcp" / name for name in REQUIRED_DOCUMENTS}
    assert_full_guidance(initialized.instructions, sources, delivery)


def test_bound_worksession_paths_survive_the_final_response_middleware(tmp_path):
    root = str(tmp_path)
    other_drive = "Z:" if ntpath.splitdrive(root)[0].casefold() != "z:" else "Y:"
    references = [str(tmp_path / "reference.3dm"), str(tmp_path.parent / "survey" / "reference.3dm"),
                  other_drive + "\\survey\\reference.3dm", "\\\\server\\share\\reference.3dm"]
    env = isolated_environment(tmp_path)
    env.pop("ALMOND_TEST_GUIDANCE_DIR", None)
    env["ALMOND_TEST_REFERENCE_PATHS"] = json.dumps(references)
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=env)

    async def discover():
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                await client.initialize()
                values = []
                for name in ("context_04-get_project_info", "inspect_03-get_document_context",
                             "inspect_03-get_document_context"):
                    result = await client.call_tool(name, {"sections": ["worksession"]})
                    assert not result.is_error
                    values.append(json.loads(result.content[0].text)["worksession"])
                    structured = result.structured_content
                    if name.startswith("inspect_"):
                        structured = json.loads(structured["result"])
                    assert structured["worksession"] == values[-1]
                return values

    project, inspected, repeated = asyncio.run(discover())
    assert project == inspected == repeated
    rows = inspected["attachments"]
    assert rows[0]["path"] == "reference.3dm"
    assert rows[1]["path"].startswith("../")
    assert [row["path"] for row in rows[2:]] == references[2:]
    for row, original in zip(rows, references):
        assert ntpath.normcase(ntpath.normpath(ntpath.join(root, row["path"]))) == ntpath.normcase(ntpath.normpath(original))


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_bound_serve_and_external_catalog_identity(tmp_path, required_sources, delivery, monkeypatch):
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=isolated_environment(tmp_path, required_sources))
    instructions, worker = asyncio.run(collect(params, bound=True))
    assert_full_guidance(instructions, required_sources, delivery)
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
    exposed, mapping = exposed_tools(catalog)
    external = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in exposed}
    policy_instruction = read_tool_instruction(str(ROOT / "src/mcp/features/guidance/tools.py"), "get_policy")
    role, arguments = policy_instruction.split("\n\nArgs:\n", 1)
    policy_tool = external["context_01-get_policy"]
    assert policy_tool["description"] == role
    assert set(policy_tool["inputSchema"]["properties"]) == {"policy"}
    assert policy_tool["inputSchema"]["properties"]["policy"]["description"] == arguments.strip().removeprefix("policy: ")
    for name in worker:
        assert mapping[name] == name
        assert external[name]["description"] == worker[name]["description"]
        assert external[name]["inputSchema"] == worker[name]["inputSchema"]


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_both_external_host_routes_publish_same_real_stdio_schemas(tmp_path, required_sources, delivery, monkeypatch):
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)
    from runtime import load_catalog
    from external_host import exposed_tools
    expected_tools, _ = exposed_tools(load_catalog())
    expected = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in expected_tools}

    async def inspect(client_name):
        code = ("import os; from pathlib import Path; from external_host import main; "
                "from almond_mcp import modeling_guidance as guide; "
                "guide.REQUIRED_GUIDE_SOURCES = {name: Path(os.environ['ALMOND_TEST_GUIDANCE_DIR']) / name "
                f"for name in {REQUIRED_DOCUMENTS!r}}}; "
                f"main(Path(os.environ['ALMOND_TEST_ROOT']), client='{client_name}')")
        params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c", code],
                                       env=isolated_environment(tmp_path / client_name, required_sources))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                initialized = await client.initialize()
                tools = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                         for t in (await client.list_tools()).tools}
                assert_information_placement(tools)
                assert initialized.instructions  # External-host instructions are a separate contract.
                assert_full_guidance(initialized.instructions, required_sources, delivery)
                if delivery == "fields":
                    assert json.loads(initialized.instructions)["_metadata"]["introduction"].startswith(initialized.server_info.description)
                for text in (initialized.instructions, initialized.server_info.description):
                    assert not any(name in text for name in ("host_id", "model_path", "connection_id", "request_id"))
                assert tools == expected
                for name, tool in tools.items():
                    assert "connection_id" not in tool["inputSchema"].get("properties", {})
                    assert_documented_schema(tool["inputSchema"], name)
                assert tools["connect_04-disconnect"]["inputSchema"]["properties"] == {}
                rejected = await client.call_tool("context_04-get_project_info", {"connection_id": "old"})
                assert rejected.is_error
                return initialized.server_info.name

    for name, label in (("codex", "beyond"), ("cos", "CoS")):
        (tmp_path / name).mkdir()
        assert asyncio.run(inspect(name)) == label


def test_plan_section_bound_schema_and_external_argument_routing(tmp_path, required_sources):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u",
        str(ROOT / "tests/integration/bound_server_fixture.py")], env=isolated_environment(tmp_path, required_sources))
    _, worker = asyncio.run(collect(params, bound=True))
    from runtime import load_catalog, schema_identity
    from external_host import Broker, json_result
    from types import SimpleNamespace
    catalog = next(t for t in load_catalog()["tools"] if t["name"] == "drawing_06-generate_plan_section")
    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf-8"))["drawing_06-generate_plan_section"]
    assert schema_identity(worker["drawing_06-generate_plan_section"]) == schema_identity(catalog) == baseline
    arguments = dict(operation="Create", clipping_ids=["00000000-0000-0000-0000-000000000001"])
    observed = []

    async def invoke(conn, name, payload, invocation):
        observed.append((conn, name, payload))
        return json_result({"status": "success"})

    async def route():
        broker = SimpleNamespace(mapping={"drawing_06-generate_plan_section": "drawing_06-generate_plan_section"}, connections={"fixture": "bound"},
                                 invoke=invoke, spawn=asyncio.create_task, selected_connection_id="fixture")
        response = await Broker.call(broker, "drawing_06-generate_plan_section", arguments)
        assert not response.is_error

    asyncio.run(route())
    assert observed == [("bound", "drawing_06-generate_plan_section", arguments)]
