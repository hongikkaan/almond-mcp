"""BASIC and tool explanations are static, complete and versioned."""
import asyncio
import json
import runpy

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from almond_mcp.features.guidance.tools import register
from almond_mcp.modeling_guidance import BASIC_GUIDE, PACKAGE, project_instructions, read_guide, startup_instructions


class NoModelContext:
    def __getattr__(self, name):
        raise AssertionError(f"Static guidance accessed model context: {name}")


def test_first_use_delivers_basic_without_model_access():
    mcp = FastMCP("static-guide", instructions=startup_instructions())
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool("get_modeling_guide", {})
            payload = json.loads(result.content[0].text)
            assert payload["text"] == BASIC_GUIDE.read_text(encoding="utf-8").strip()
            assert project_instructions() == payload["text"]
            assert 'get_modeling_guide()' in startup_instructions()
            assert payload["text"] not in startup_instructions()
            assert len(payload["guide_version"]) == 64
            assert "assign_material" in payload["tools"]
            assert "topics" not in payload
            assert [part.type for part in result.content] == ["text"]
            assert set(next(t for t in await client.list_tools() if t.name == "get_modeling_guide").input_schema["properties"]) == {"tool"}

    asyncio.run(run())


@pytest.mark.parametrize("arguments", [
    {"topic": "basic"}, {"topic": "drafting"}, {"include_images": True},
    {"tool": "../SKILL.md"}, {"tool": "https://example.com"}, {"tool": "missing"},
])
def test_retired_topic_inputs_and_unknown_tool_names_are_rejected(arguments):
    mcp = FastMCP("static-guide-errors")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            with pytest.raises(ToolError):
                await client.call_tool("get_modeling_guide", arguments)

    asyncio.run(run())


def test_fresh_reader_needs_no_topic_map_or_old_modeling_guide():
    assert not (PACKAGE / "features/guidance/guides/mcp-guide-map.json").exists()
    assert not (PACKAGE / "features/guidance/guides/modeling-guide.md").exists()
    reader = runpy.run_path(str(PACKAGE / "modeling_guidance.py"))
    assert reader["read_guide"]()["text"] == read_guide()["text"]
