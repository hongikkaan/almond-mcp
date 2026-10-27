"""Exercise modeling guidance through MCP without a model, store or personal skill."""
import asyncio
import json
import base64
import hashlib
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError

from fastmcp import Client, FastMCP

from almond_mcp.features.guidance.tools import register


class NoModelContext:
    def __getattr__(self, name):
        raise AssertionError(f"Static guidance accessed model context: {name}")


def test_agent_can_discover_topics_without_reading_a_model():
    mcp = FastMCP("static-guide")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool("get_modeling_guide", {})
            index = json.loads(result.content[0].text)
            assert index["status"] == "success"
            assert len(index["guide_version"]) == 64
            topics = {topic["id"]: topic for topic in index["topics"]}
            assert {"project", "planning", "ontological-component", "blocks", "drafting"} <= topics.keys()
            assert all(topic["when_to_read"] for topic in topics.values())
            assert "text" not in index
            assert len(result.content) == 1

    asyncio.run(run())


def test_topic_and_opt_in_original_images_have_one_version_and_no_model_access():
    mcp = FastMCP("static-guide")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            plain = await client.call_tool("get_modeling_guide", {"topic": "ontological-component-evidence"})
            payload = json.loads(plain.content[0].text)
            assert len(plain.content) == 1 and payload["images_included"] == 0
            assert "사용자 원문 시작" in payload["text"]
            illustrated = await client.call_tool("get_modeling_guide", {
                "topic": "ontological-component-evidence", "include_images": True})
            shown = json.loads(illustrated.content[0].text)
            assert shown["guide_version"] == payload["guide_version"]
            assert shown["images_included"] == 2
            original = Path(__file__).resolve().parents[3] / "skills/rhino-almond/references/assets"
            for content, description in zip(illustrated.content[1:], shown["images_available"], strict=True):
                raw = base64.b64decode(content.data)
                assert content.type == "image" and content.mime_type == "image/png"
                assert raw == (original / Path(description["file"]).name).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == description["sha256"]
            selected = await client.call_tool("get_modeling_guide", {"topic": "drafting"})
            draft = json.loads(selected.content[0].text)
            assert draft["guide_version"] == shown["guide_version"]
            assert "Join" in draft["text"] and "## 교환·외부 발행" not in draft["text"]
            assert len(selected.content) == 1

    asyncio.run(run())


@pytest.mark.parametrize("arguments", [
    {"topic": "../SKILL.md"}, {"topic": "https://example.com"}, {"topic": "missing"},
    {"include_images": "true"}, {"include_images": 1},
])
def test_unknown_topics_and_non_boolean_image_switch_fail_explicitly(arguments):
    mcp = FastMCP("static-guide")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            with pytest.raises(ToolError):
                await client.call_tool("get_modeling_guide", arguments)

    asyncio.run(run())


def test_modeling_tool_has_conditional_topic_hint():
    from almond_mcp.instruction_text import tool_instruction
    source = Path(__file__).resolve().parents[1] / "almond_mcp/features/guidance/tools.py"

    @tool_instruction(str(source), "get_construction_guidance")
    def tool():
        pass

    assert 'When editing construction geometry' in tool.__doc__
    assert 'get_modeling_guide(topic="modeling")' in tool.__doc__
