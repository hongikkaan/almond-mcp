"""Verify guidance delivery at each supported Python MCP initialization boundary."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import pytest

from test_stdio_contract import ROOT, isolated_environment


@pytest.fixture
def guidance_checkout(tmp_path):
    checkout = tmp_path / "checkout"
    for module in ("mcp", "cos"):
        shutil.copytree(ROOT / "src" / module, checkout / "src" / module,
                        ignore=shutil.ignore_patterns("data", "tests", "__pycache__", "*.3dm"))
    shutil.copy2(ROOT / "uv.lock", checkout)
    return checkout


def guidance_directory(checkout):
    return checkout / "src/mcp"


def session_params(checkout, project, route):
    project.mkdir()
    env = isolated_environment(project)
    env["PYTHONPATH"] = os.pathsep.join(str(checkout / part) for part in ("src/mcp", "src/mcp/runtime", "src/cos"))
    if route == "bound":
        entry = [str(ROOT / "tests/integration/bound_server_fixture.py")]
    elif route == "standalone":
        entry = ["-c", "from almond_mcp.server import mcp; mcp.run()"]
    else:
        entry = ["-c", "import os; from pathlib import Path; from external_host import main; "
                       f"main(Path(os.environ['ALMOND_TEST_ROOT']), client={route!r})"]
    return StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", *entry],
                                 env=env, cwd=checkout)


@pytest.mark.parametrize("route", ["bound", "codex", "cos"])
def test_delivers_both_guidance_bodies_once(guidance_checkout, tmp_path, route):
    basic = "# 업무 fixture\n\n  작업 내용.\n"
    design = "# 판단 fixture\n\n" + "설계 판단 검증 문단\n" * 5700 + "마지막 단락.\n"
    guide_dir = guidance_directory(guidance_checkout)
    (guide_dir / "BASIC-INSTRUCTIONS.md").write_text(basic, encoding="utf-8", newline="\n")
    (guide_dir / "design_judgment.md").write_text(design, encoding="utf-8", newline="\n")

    async def inspect():
        params = session_params(guidance_checkout, tmp_path / "project", route)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                initialized = await client.initialize()
                instructions = initialized.instructions
                assert instructions.count(basic) == 1
                assert instructions.count(design) == 1
                assert "context_01-get_policy tool" in instructions
                assert "On first use, call" not in instructions
                if route != "bound":
                    description = initialized.server_info.description
                    assert description in instructions
                    assert basic not in description and design not in description
                tools = await client.list_tools()
                assert all(basic not in tool.description and design not in tool.description
                           for tool in tools.tools if tool.description)
                if route == "bound":
                    basic_policy = await client.call_tool("context_01-get_policy", {})
                    assert not basic_policy.is_error
                    assert basic_policy.structured_content["text"] == basic.strip()
                    assert design not in basic_policy.structured_content["text"]
                    assert guide_version(instructions) == basic_policy.structured_content["guide_version"]

    asyncio.run(inspect())

@pytest.mark.parametrize("route", ["bound", "codex", "cos"])
def test_metadata_policy_is_discoverable_and_readable_on_a_new_session(guidance_checkout, tmp_path, route):
    params = session_params(guidance_checkout, tmp_path / "project", route)
    guide_dir = guidance_directory(guidance_checkout)
    expected_keys = json.loads((guide_dir / "modeling_policy.json").read_text(encoding="utf-8"))

    async def inspect():
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                instructions = (await client.initialize()).instructions
                assert 'policy="metadata"' in instructions
                tools = {tool.name: tool for tool in (await client.list_tools()).tools}
                assert {"model_01-assign_material", "inspect_02-get_objects"} <= tools.keys()
                assert "User Text" in tools["context_01-get_policy"].description

                result = await client.call_tool("context_01-get_policy", {"policy": "metadata"})
                assert not result.is_error
                value = result.structured_content
                assert json.loads(result.content[0].text) == value
                assert "text" not in value
                assert value["policy"] == expected_keys
                assert value["policy"]["public_object_keys"]["floor"] == "floor"
                assert value["policy"]["internal_object_keys"]["section"] == "section"
                for group in ("public_object_keys", "internal_object_keys", "group_keys"):
                    assert all(not key.startswith("almond:") for key in value["policy"][group].values())
                assert value["guide_version"] == guide_version(instructions)
                assert {ref["path"] for ref in value["source_refs"]} == {
                    "src/mcp/modeling_policy.json",
                }
                basic = await client.call_tool("context_01-get_policy", {})
                assert basic.structured_content["selected_policy"] == "basic"
                assert basic.structured_content["guide_version"] == value["guide_version"]
                rejected = await client.call_tool("context_01-get_policy", {"unexpected": "metadata"})
                assert rejected.is_error
                retired = await client.call_tool("context_01-get_policy", {"policy": "drawing"})
                assert retired.is_error
                if route != "bound":
                    blocked = await client.call_tool("inspect_02-get_objects", {})
                    assert blocked.is_error
                    assert "No selected live connection" in blocked.content[0].text

    asyncio.run(inspect())


def startup_response(checkout, project, route):
    async def initialize():
        params = session_params(checkout, project, route)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                return await client.initialize()

    return asyncio.run(initialize())


def guide_version(instructions):
    return instructions.split("guide_version=", 1)[1].splitlines()[0]


@pytest.mark.parametrize("route", ["bound", "codex", "cos"])
def test_reports_missing_document_and_loads_versions_in_new_sessions(guidance_checkout, tmp_path, route):
    guide_dir = guidance_directory(guidance_checkout)
    basic = "첫 번째 문서입니다.\n마지막 줄입니다.\n"
    design = guide_dir / "design_judgment.md"
    (guide_dir / "BASIC-INSTRUCTIONS.md").write_bytes(b"\xef\xbb\xbf" + basic.replace("\n", "\r\n").encode("utf-8"))
    design.unlink(missing_ok=True)

    original = startup_response(guidance_checkout, tmp_path / "before", route).instructions
    assert basic in original
    assert "Startup guidance unavailable: design_judgment.md (file missing)." in original

    design.write_text("첫 설계 판단.", encoding="utf-8")
    added = startup_response(guidance_checkout, tmp_path / "added", route).instructions
    assert "첫 설계 판단." in added and basic in added
    assert "Startup guidance unavailable:" not in added
    assert guide_version(original) != guide_version(added)

    design.write_text("갱신한 설계 판단.", encoding="utf-8")
    updated = startup_response(guidance_checkout, tmp_path / "updated", route).instructions
    assert "갱신한 설계 판단." in updated and "첫 설계 판단." not in updated
    assert guide_version(added) != guide_version(updated)


def test_external_host_reports_invalid_and_empty_documents(guidance_checkout, tmp_path):
    guide_dir = guidance_directory(guidance_checkout)
    (guide_dir / "BASIC-INSTRUCTIONS.md").write_bytes(b"\xff\xfe")
    (guide_dir / "design_judgment.md").write_bytes(b"\t\r\n ")
    result = startup_response(guidance_checkout, tmp_path / "invalid", "codex")
    assert "Startup guidance unavailable: BASIC-INSTRUCTIONS.md (invalid UTF-8)." in result.instructions
    assert "Startup guidance unavailable: design_judgment.md (empty document)." in result.instructions
    assert result.server_info.description in result.instructions


def test_external_host_rejects_installed_metadata_from_a_different_release(guidance_checkout, tmp_path):
    (guidance_directory(guidance_checkout) / "__init__.py").write_text('__version__ = "123.4.5"\n', encoding="utf-8")
    params = session_params(guidance_checkout, tmp_path / "stale", "codex")
    result = subprocess.run(
        [params.command, *params.args], env=params.env, cwd=params.cwd,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=45,
    )
    assert result.returncode != 0
    assert "Runtime expects almond-mcp version ['123.4.5'] from the current checkout; installed:" in result.stderr


def test_unbound_standalone_keeps_initialize_free_of_document_guidance(guidance_checkout, tmp_path):
    guide_dir = guidance_directory(guidance_checkout)
    (guide_dir / "BASIC-INSTRUCTIONS.md").write_text("Basic fixture.", encoding="utf-8")
    (guide_dir / "design_judgment.md").write_text("Design fixture.", encoding="utf-8")
    result = startup_response(guidance_checkout, tmp_path / "standalone", "standalone")
    assert result.instructions is None
