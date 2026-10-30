"""Tool instructions are opt-in static reads, never calls to the named tool."""
import asyncio
import json
from pathlib import Path
import runpy

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from almond_mcp.features.guidance.tools import register
from almond_mcp.instruction_text import read_instruction
from almond_mcp.modeling_guidance import PACKAGE


class NoModelContext:
    def __getattr__(self, name):
        raise AssertionError(f"Tool guidance accessed model context: {name}")


@pytest.mark.parametrize("name, source", [
    ("assign_material", "features/modeling/tools.py"),
    ("execute_rhino_script", "features/modeling/tools.py"),
    ("execute_project_python", "runtime/mcp_server.py"),
    ("get_modeling_guide", "features/guidance/tools.py"),
])
def test_tool_lookup_delivers_original_explanation_without_execution(name, source):
    mcp = FastMCP("static-tool-guidance")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            schema = next(t for t in await client.list_tools() if t.name == "get_modeling_guide")
            assert schema.input_schema["properties"]["tool"]["default"] == ""
            index = json.loads((await client.call_tool("get_modeling_guide", {})).content[0].text)
            result = await client.call_tool("get_modeling_guide", {"tool": name})
            payload = json.loads(result.content[0].text)
            assert payload["status"] == "success" and payload["tool_name"] == name
            assert payload["guide_version"] == index["guide_version"]
            assert payload["text"] == read_instruction(str(PACKAGE / source), name)
            assert payload["source_refs"][0]["path"] == "src/mcp/" + source.replace(".py", "-explain.md")
            assert [part.type for part in result.content] == ["text"]
            assert name in index["tools"]
            assert not any(name.startswith("response-") or name.startswith("_") for name in index["tools"])

    asyncio.run(run())


@pytest.mark.parametrize("arguments", [
    {"tool": "../modeling_policy.py"}, {"tool": "https://example.com"},
    {"tool": "missing"}, {"tool": "response-750"}, {"tool": "_material_script"},
    {"tool": "assign_material", "topic": "modeling"}, {"include_images": True},
])
def test_unknown_tools_and_combined_selectors_fail_explicitly(arguments):
    mcp = FastMCP("static-tool-errors")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            with pytest.raises(ToolError):
                await client.call_tool("get_modeling_guide", arguments)

    asyncio.run(run())


@pytest.mark.parametrize("relative", ["features/modeling/tools-explain.md", "features/modeling/tools.py"])
def test_tool_sources_participate_in_guide_version(relative, monkeypatch):
    reader = runpy.run_path(str(PACKAGE / "modeling_guidance.py"))
    original = Path.read_bytes
    target = PACKAGE / relative
    before = reader["read_guide"]()["guide_version"]
    reader["_snapshot"].cache_clear()

    def changed(path):
        raw = original(path)
        return raw + b"\n# Source changed.\n" if path == target else raw

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert reader["read_guide"]()["guide_version"] != before
