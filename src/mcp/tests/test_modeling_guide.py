"""Exercise modeling guidance through MCP without a model, store or personal skill."""
import asyncio
import json
import base64
import hashlib
import runpy
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError

from fastmcp import Client, FastMCP

from almond_mcp.features.guidance.tools import register


class NoModelContext:
    def __getattr__(self, name):
        raise AssertionError(f"Static guidance accessed model context: {name}")


@pytest.mark.parametrize('filename', ['FUNDAMENTAL-INSTRUCTIONS.md', 'MODEL-CONTEXT-INSTRUCTIONS.md'])
def test_new_reader_rejects_instructions_from_another_bundle_version(filename, monkeypatch):
    from almond_mcp.modeling_guidance import PACKAGE
    reader = runpy.run_path(str(PACKAGE / 'modeling_guidance.py'))
    original_read = Path.read_bytes
    target = PACKAGE / filename

    def changed_read(path):
        raw = original_read(path)
        return raw + b'\nChanged guidance.\n' if path == target else raw

    monkeypatch.setattr(Path, 'read_bytes', changed_read)
    with pytest.raises(ValueError, match='guidance changed'):
        reader['read_guide']()


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


def test_startup_gives_topic_summaries_for_direct_access_without_an_index_call():
    from almond_mcp.modeling_guidance import project_instructions, startup_instructions

    startup = startup_instructions()
    assert 'call get_modeling_guide(topic="index") and select' not in startup
    assert 'same guide_version' in startup
    mcp = FastMCP("direct-guide", instructions=startup)
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            # Given a known topic, When startup supplies its purpose, Then its
            # first request can be the topic itself without a model/index query.
            result = await client.call_tool("get_modeling_guide", {"topic": "planning"})
            assert json.loads(result.content[0].text)["topic_id"] == "planning"
            index = await client.call_tool("get_modeling_guide", {})
            for topic in json.loads(index.content[0].text)["topics"]:
                assert topic["summary"]
                assert f'{topic["id"]}: {topic["summary"]}' in startup

    asyncio.run(run())
    assert project_instructions().startswith(startup)


def test_planning_topic_delivers_instruction_routing_before_tool_selection():
    mcp = FastMCP("task-routing")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool("get_modeling_guide", {"topic": "planning"})
            text = json.loads(result.content[0].text)["text"]
            for scenario in ("진행 중 Task의 보완", "다른 과업으로 전환", "맥락이 부족", "일회성 조회"):
                assert scenario in text
            assert text.index("도구 선택 전에") < text.index("| 도구 |")
            assert "완료한 Task" in text and "의미 있는 상태" in text

    asyncio.run(run())


@pytest.mark.parametrize("topic, required, obsolete", [
    ("project", ("첫 연결·재연결", "새 메시지", "별도 백업"), ()),
    ("ontological-component", ("Scene 맥락을 반드시 지정", "여러 Scene에 참여", "Almond 관리 UserStrings",
                                "한 번 정합", "물리적 group/block 해체와 별개"),
     ("특정 Scene에 종속되지 않", "아직 연결되지 않은 상태")),
    ("blocks", ("같은 block 정의를 재사용", "단일 객체 group", "짧은 종류·기능 이름"), ()),
    ("modeling", ("ontological_component마다 별도 레이어를 만들지",), ()),
    ("model-review", ("남은 불확실성의 영향", "미검사 범위", "재현하지 않은 오류"), ()),
])
def test_published_topics_retain_authorized_behavior_boundaries(topic, required, obsolete):
    """Content contracts guard delivery; they do not prove an agent followed it."""
    mcp = FastMCP("behavior-guidance")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool("get_modeling_guide", {"topic": topic})
            text = json.loads(result.content[0].text)["text"]
            assert all(fragment in text for fragment in required)
            assert not any(fragment in text for fragment in obsolete)

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
            original = Path(__file__).resolve().parents[3] / "docs/modeling/guidance/references/assets"
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
    source = Path(__file__).resolve().parents[1] / "features/guidance/tools.py"

    @tool_instruction(str(source), "get_construction_guidance")
    def tool():
        pass

    assert 'When editing construction geometry' in tool.__doc__
    assert 'get_modeling_guide(topic="modeling")' in tool.__doc__
