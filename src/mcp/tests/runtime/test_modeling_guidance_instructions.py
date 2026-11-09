"""RhinoTerminal's session-bound MCP publishes its modeling-guide entry point."""
import asyncio

from fastmcp import Client, FastMCP

import mcp_server
from almond_mcp.modeling_guidance import startup_instructions


def test_rhino_session_instructions_are_discoverable_without_a_server_description():
    async def discover():
        server = FastMCP("Almond")
        assert server.instructions is None

        mcp_server.configure_rhino_session_instructions(server)

        async with Client(server) as client:
            assert client.instructions == startup_instructions()
            assert "On first use, call get_modeling_guide()" in client.instructions
            assert "BASIC-INSTRUCTIONS.md" in client.instructions
            assert "guide_version=" in client.instructions
            assert client.server_info.description is None

    asyncio.run(discover())
