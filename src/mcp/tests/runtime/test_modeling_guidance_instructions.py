"""RhinoTerminal's session-bound MCP publishes its modeling-guide entry point."""
import asyncio

from fastmcp import Client, FastMCP

import mcp_server
from almond_mcp.modeling_guidance import BASIC_GUIDE, startup_instructions


def test_rhino_session_instructions_are_discoverable_without_a_server_description():
    async def discover():
        server = FastMCP("Almond")
        assert server.instructions is None

        mcp_server.configure_rhino_session_instructions(server)

        async with Client(server) as client:
            assert client.instructions == startup_instructions()
            assert "Use context_01-get_policy tool for bundled guidance" in client.instructions
            assert client.instructions.count(BASIC_GUIDE.read_text(encoding="utf-8-sig")) == 1
            assert "guide_version=" in client.instructions
            assert client.server_info.description is None

    asyncio.run(discover())
