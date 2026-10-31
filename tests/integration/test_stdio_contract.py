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
from almond_mcp.modeling_guidance import BASIC_GUIDE, read_guide

ROOT = Path(__file__).resolve().parents[2]


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


def first_sentence(text):
    prose = re.split(r"^(?:Args|Arguments|Returns|Raises|Yields):\s*$", text, maxsplit=1, flags=re.M)[0]
    return re.split(r"(?<=[.!?])\s+", " ".join(prose.split()), maxsplit=1)[0]


async def collect(params, *, bound):
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
            initialized = await client.initialize()
            tools = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for t in (await client.list_tools()).tools}
            basic_result = await client.call_tool("get_modeling_guide", {})
            assert not basic_result.is_error
            basic = json.loads(basic_result.content[0].text)
            assert basic["text"] == BASIC_GUIDE.read_text(encoding="utf-8").strip()
            # Codex CodeMode appends this namespace-level field to every tool.
            # Keep the guide discoverable on its own tool, without a shared suffix.
            assert not initialized.instructions, "namespace instructions would be appended to every CodeMode tool"
            for name, item in tools.items():
                result = await client.call_tool("get_modeling_guide", {"tool": name})
                assert not result.is_error, name
                guide = json.loads(result.content[0].text)
                assert guide["text"] == read_guide(name)["text"], name
                assert guide["guide_version"] == basic["guide_version"], name
                assert item["description"] == first_sentence(guide["text"]), name
                assert "Almond inspects and edits Rhino" not in item["description"], name
                assert "guide_version=" not in item["description"], name
            if bound:
                result = await client.call_tool("project_info", {"sections": ["project"]})
                assert not result.is_error
                project = json.loads(result.content[0].text)["project"]
                assert project["file_name"] == "disposable.3dm"
                assert project["database"] == ".almond/scene.sqlite3"
                assert project["root_variable_set"] is True
            return initialized.instructions, tools


def test_cold_direct_descriptions_and_explicit_full_guides(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c",
        "from almond_mcp.server import mcp; mcp.run()"], env=isolated_environment(tmp_path))
    instructions, tools = asyncio.run(collect(params, bound=False))
    assert "get_rhino_context" in tools
    assert not instructions
    assert "get_modeling_guide" in tools


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
                assert initialized.instructions  # External-host instructions are a separate contract.
                assert tools == expected
                return initialized.server_info.name

    for name, label in (("codex", "beyond"), ("cos", "CoS")):
        (tmp_path / name).mkdir()
        assert asyncio.run(inspect(name)) == label
