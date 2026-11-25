"""Verify guidance delivery at each supported Python MCP initialization boundary."""
import asyncio
import json
import shutil
import subprocess
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import pytest

from render_tool_declarations import ROOT, isolated_environment, read_catalog, stdio_parameters


@pytest.fixture
def guidance_checkout(tmp_path):
    checkout = tmp_path / "checkout"
    for module in ("mcp", "beyond"):
        shutil.copytree(ROOT / "src" / module, checkout / "src" / module,
                        ignore=shutil.ignore_patterns("data", "tests", "bin", "obj", "__pycache__", "*.3dm"))
    shutil.copy2(ROOT / "uv.lock", checkout)
    return checkout


def guidance_directory(checkout):
    return checkout / "src/mcp"


RETIRED_NAMES = ("BASIC-INSTRUCTIONS.md", "design_judgment.md", "About Rhino.md")


def test_existing_codex_registration_starts_the_same_beyond_server(guidance_checkout, tmp_path):
    previous_entry = guidance_checkout / "src/cos/codex_host.py"
    previous_entry.parent.mkdir()
    shutil.copy2(ROOT / "src/cos/codex_host.py", previous_entry)
    env = isolated_environment(tmp_path / "libraries", guidance_checkout)
    env.pop("PYTHONPATH", None)

    async def start(script):
        params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", str(script)],
                                       cwd=tmp_path, env=env)
        return await read_catalog(params)

    current, current_tools = asyncio.run(start(guidance_checkout / "src/beyond/codex_host.py"))
    previous, previous_tools = asyncio.run(start(previous_entry))
    assert current.server_info.name == "beyond"
    assert previous.server_info == current.server_info
    assert previous.instructions == current.instructions
    assert previous_tools == current_tools


@pytest.mark.parametrize("route", ["terminal", "beyond"])
def test_legacy_guidance_and_global_skill_are_not_read(guidance_checkout, tmp_path, route, monkeypatch):
    guide_dir = guidance_directory(guidance_checkout)
    for name in RETIRED_NAMES:
        # Deliberately unreadable as UTF-8; a lingering fingerprint or delivery
        # dependency would also break an external host before initialization.
        (guide_dir / name).write_bytes(b"legacy-sentinel-\xff\xfe")
    home = tmp_path / "profile"
    skill = home / ".agents/skills/rhinobeyond/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("global-skill-sentinel", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    async def inspect():
        params = stdio_parameters(route, tmp_path / "project", guidance_checkout)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                initialized = await client.initialize()
                instructions = initialized.instructions
                assert "context_01-get_policy tool" in instructions
                assert "Use tools/list to see the tools available on this connection." in instructions
                if route == "beyond":
                    assert instructions.startswith(initialized.server_info.description)
                tools = await client.list_tools()
                basic_calls = []
                for explicit in ({}, {"policy": ""}, {"policy": "basic"}):
                    result = await client.call_tool("context_01-get_policy", explicit)
                    assert not result.is_error
                    basic_calls.append(result.structured_content)
                basic = basic_calls[0]
                assert basic == basic_calls[1] == basic_calls[2]
                assert basic["selected_policy"] == "basic"
                assert "공통 도구 참고 목록" in basic["text"] and "tools/list" in basic["text"]
                assert "context_01-get_policy" in basic["tools"]
                assert "connect_01-list_up" not in basic["tools"]
                assert ("connect_01-list_up" in {tool.name for tool in tools.tools}) == (route == "beyond")
                assert basic["source_refs"][0]["path"] == "src/mcp/modeling_guidance.py"
                assert guide_version(instructions) == basic["guide_version"]
                for name in ("rhino_scripting", "rhinocode"):
                    result = await client.call_tool("context_01-get_policy", {"policy": name})
                    assert not result.is_error
                    value = result.structured_content
                    assert value["guide_version"] == basic["guide_version"]
                    if name == "rhinocode":
                        assert "script_02-run_rhino" in value["text"]
                    else:
                        assert value["scripting_skill"]["name"] == "rhino3d-scripts"
                        assert all(source["text"] for source in value["scripting_skill"]["sources"])
                published = json.dumps([initialized.model_dump(), tools.model_dump(), basic], ensure_ascii=False)
                assert not any(name in published for name in RETIRED_NAMES)
                assert "legacy-sentinel" not in published and "global-skill-sentinel" not in published
    asyncio.run(inspect())


@pytest.mark.parametrize("route", ["terminal", "beyond"])
def test_metadata_policy_is_discoverable_and_readable_on_a_new_session(guidance_checkout, tmp_path, route):
    params = stdio_parameters(route, tmp_path / "project", guidance_checkout)
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
                assert value["policy"]["internal_object_keys"]["component_id"] == "component_id"
                assert value["policy"]["construction_layer_root"] == "M"
                for group in ("public_object_keys", "internal_object_keys"):
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
                if route == "beyond":
                    blocked = await client.call_tool("inspect_02-get_objects", {})
                    assert blocked.is_error
                    assert "connection_id" in blocked.content[0].text

    asyncio.run(inspect())


def startup_response(checkout, project, route):
    async def initialize():
        params = stdio_parameters(route, project, checkout)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
                return await client.initialize()

    return asyncio.run(initialize())


def guide_version(instructions):
    return instructions.split("guide_version=", 1)[1].splitlines()[0]


@pytest.mark.parametrize("route", ["terminal", "beyond"])
def test_guide_version_tracks_only_retained_sources(guidance_checkout, tmp_path, route):
    guide_dir = guidance_directory(guidance_checkout)
    original = startup_response(guidance_checkout, tmp_path / "before", route).instructions
    for name in RETIRED_NAMES:
        (guide_dir / name).write_bytes(b"old-sentinel-\xff")
    with_stale_files = startup_response(guidance_checkout, tmp_path / "stale-files", route).instructions
    assert original == with_stale_files

    notes = guide_dir / "RHINOCODE-INSTRUCTIONS.md"
    notes.write_text(notes.read_text(encoding="utf-8") + "\nRetained reference fixture.\n", encoding="utf-8")
    updated = startup_response(guidance_checkout, tmp_path / "updated", route).instructions
    assert "Retained reference fixture." not in updated
    assert guide_version(original) != guide_version(updated)


def test_external_host_rejects_installed_metadata_from_a_different_release(guidance_checkout, tmp_path):
    (guidance_directory(guidance_checkout) / "__init__.py").write_text('__version__ = "123.4.5"\n', encoding="utf-8")
    params = stdio_parameters("beyond", tmp_path / "stale", guidance_checkout)
    result = subprocess.run(
        [params.command, *params.args], env=params.env, cwd=params.cwd,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=45,
    )
    assert result.returncode != 0
    assert "Runtime expects almond-mcp version ['123.4.5'] from the current checkout; installed:" in result.stderr


def test_unbound_standalone_keeps_initialize_free_of_document_guidance(guidance_checkout, tmp_path):
    guide_dir = guidance_directory(guidance_checkout)
    for name in RETIRED_NAMES:
        (guide_dir / name).write_text("Legacy fixture.", encoding="utf-8")
    result = startup_response(guidance_checkout, tmp_path / "standalone", "standalone")
    assert result.instructions is None
