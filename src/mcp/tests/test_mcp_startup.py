"""Cold MCP initialization delivers BASIC and every public tool explanation."""
import asyncio
import json
import os
import sys
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from almond_mcp.modeling_guidance import BASIC_GUIDE


def test_cold_stdio_initializes_and_delivers_current_guides(tmp_path):
    environment = dict(os.environ, RHINO_MCP_STATE_DB=str(tmp_path / "state.sqlite3"))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-B", "-X", "utf8", "-u", "-c", "from almond_mcp.server import mcp; mcp.run()"],
        env=environment,
    )

    async def verify():
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=20.0) as client:
                initialized = await client.initialize()
                assert 'get_modeling_guide()' in initialized.instructions
                policy = await client.call_tool("get_modeling_policy", {})
                assert not policy.is_error
                assert json.loads(policy.content[0].text)["policy"]["construction_layer_root"] == "M"
                basic = json.loads((await client.call_tool("get_modeling_guide", {})).content[0].text)
                assert basic["text"] == BASIC_GUIDE.read_text(encoding="utf-8").strip()
                for name in basic["tools"]:
                    result = await client.call_tool("get_modeling_guide", {"tool": name})
                    assert not result.is_error, name
                    guide = json.loads(result.content[0].text)
                    assert guide["tool_name"] == name and guide["text"]
                    assert guide["guide_version"] == basic["guide_version"]

    asyncio.run(verify())
