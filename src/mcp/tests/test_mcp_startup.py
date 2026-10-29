"""Cold MCP initialization must load the shipped policy and every guide topic."""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def test_cold_stdio_initializes_and_delivers_current_guides(tmp_path):
    environment = dict(os.environ, RHINO_MCP_STATE_DB=str(tmp_path / "state.sqlite3"))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-B", "-X", "utf8", "-u", "-c",
              "from almond_mcp.server import mcp; mcp.run()"],
        env=environment,
    )

    async def verify():
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=20.0) as client:
                initialized = await client.initialize()
                assert 'get_modeling_guide(topic="basic")' in initialized.instructions
                policy = await client.call_tool("get_modeling_policy", {})
                assert not policy.is_error
                assert json.loads(policy.content[0].text)["policy"]["construction_layer_root"] == "M"
                index = await client.call_tool("get_modeling_guide", {})
                assert not index.is_error
                topics = json.loads(index.content[0].text)
                for topic in topics["topics"]:
                    result = await client.call_tool("get_modeling_guide", {"topic": topic["id"]})
                    assert not result.is_error, topic["id"]
                    guide = json.loads(result.content[0].text)
                    assert guide["text"]
                    assert guide["guide_version"] == topics["guide_version"]
                    assert all(not ref["path"].endswith("/modeling-guide.md")
                               for ref in guide["source_refs"])
                    if topic["id"] == "basic":
                        source = Path(__file__).resolve().parents[1] / "BASIC-INSTRUCTIONS.md"
                        assert guide["text"] == source.read_text(encoding="utf-8").strip()

    asyncio.run(verify())


def test_section_heading_accepts_editorial_comment_but_rejects_duplicates():
    import pytest
    from almond_mcp.modeling_guidance import _section

    text = "### Group %% edit note %%\nCurrent text.\n### Next\nOther text.\n"
    assert "Current text." in _section(text, "### Group")
    assert "Other text." not in _section(text, "### Group")
    with pytest.raises(ValueError, match="Missing or duplicate"):
        _section(text + "### Group\nDuplicate.\n", "### Group")
