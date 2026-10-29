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


@pytest.mark.parametrize('filename', ['BASIC-INSTRUCTIONS.md'])
def test_new_reader_versions_instruction_edits_without_a_build(filename, monkeypatch):
    from almond_mcp.modeling_guidance import PACKAGE
    reader = runpy.run_path(str(PACKAGE / 'modeling_guidance.py'))
    original_read = Path.read_bytes
    target = PACKAGE / filename

    def changed_read(path):
        raw = original_read(path)
        return raw + b'\nChanged guidance.\n' if path == target else raw

    before = reader['read_guide']()[0]['guide_version']
    reader['_snapshot'].cache_clear()
    monkeypatch.setattr(Path, 'read_bytes', changed_read)
    assert reader['read_guide']()[0]['guide_version'] != before


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


def test_startup_points_to_basic_instruction_load():
    from almond_mcp.modeling_guidance import project_instructions, startup_instructions

    startup = startup_instructions()
    assert 'call get_modeling_guide(topic="index") and select' not in startup
    assert 'get_modeling_guide(topic="basic")' in startup
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
                assert topic["when_to_read"]

    asyncio.run(run())
    from almond_mcp.modeling_guidance import read_guide, PACKAGE
    basic = (PACKAGE / "BASIC-INSTRUCTIONS.md").read_text(encoding="utf-8").strip()
    assert basic not in startup
    assert read_guide("basic")[0]["text"] == basic
    assert project_instructions() == basic


def test_planning_topic_delivers_instruction_routing_before_tool_selection():
    mcp = FastMCP("task-routing")
    register(mcp, NoModelContext())

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool("get_modeling_guide", {"topic": "planning"})
            text = json.loads(result.content[0].text)["text"]
            for scenario in ("기존 Task의 연속", "다른 과업이면", "부족한 맥락만", "일회성 조회"):
                assert scenario in text
            assert text.index("해당 Task를 재사용") < text.index("| 도구 |")
            assert "요청한 실행과 필요한 검수가 끝나면 완료" in text

    asyncio.run(run())


@pytest.mark.parametrize("topic, required, obsolete", [
    ("project", ("최초 연결·재연결", "이미 확인한 문서 상태는 재사용", "백업을 만들지"), ()),
    ("ontological-component", ("기존 Scene을 한 개 이상 지정", "여러 Scene에 참여",
                                "편집 묶음을 마치고", "물리적 group/block 해체는 별개"),
     ("특정 Scene에 종속되지 않", "아직 연결되지 않은 상태")),
    ("blocks", ("같은 정의를 재사용", "단일 객체만 감싸는 group은 만들지", "짧은 종류·기능 이름",
                 "Almond 관리용 UserStrings를 자동 생성하지"), ()),
    ("modeling", ("시스템의 텍토닉", "요소역할 하위 레이어", "초기 설계 참고값"), ()),
    ("model-review", ("불확실성은 필요한 수치·단면으로 확인", "미검사 범위", "잔존 문제"), ()),
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
            original = Path(__file__).resolve().parents[3] / "src/mcp/features/guidance/guides/references/assets"
            for content, description in zip(illustrated.content[1:], shown["images_available"], strict=True):
                raw = base64.b64decode(content.data)
                assert content.type == "image" and content.mime_type == "image/png"
                assert raw == (original / Path(description["file"]).name).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == description["sha256"]
            selected = await client.call_tool("get_modeling_guide", {"topic": "drafting"})
            draft = json.loads(selected.content[0].text)
            assert draft["guide_version"] == shown["guide_version"]
            assert "도면을 공간과 의미로 읽기" in draft["text"] and "설계와 도면의 발전" in draft["text"] and "## 교환·외부 발행" not in draft["text"]
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


def test_modeling_tool_keeps_full_explanation_without_injected_topic_hint():
    from almond_mcp.instruction_text import tool_instruction, read_instruction
    source = Path(__file__).resolve().parents[1] / "features/guidance/tools.py"

    @tool_instruction(str(source), "get_construction_guidance")
    def tool():
        pass

    assert 'When editing construction geometry' not in tool.__doc__
    assert 'get_modeling_guide(topic="modeling")' not in tool.__doc__
    assert 'Call this BEFORE generating structural geometry' in read_instruction(
        str(source), 'get_construction_guidance')
