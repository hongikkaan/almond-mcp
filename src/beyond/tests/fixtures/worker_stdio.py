"""Small MCP counterpart for the external supervisor's stdio contract."""

import asyncio
import os
import sys

from mcp import types
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server


TOOL = "script_01-run_project_python"
STATE = "worker_state"
INPUT = {
    "type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"],
}


async def run(changed):
    async def list_tools(ctx, params):
        schema = {**INPUT, "required": []} if changed else INPUT
        return types.ListToolsResult(tools=[
            types.Tool(name=TOOL, input_schema=schema),
            types.Tool(name=STATE, input_schema={"type": "object"}),
        ])

    async def call_tool(ctx, params):
        result = {
            "code": params.arguments["code"],
            "caller": (params.meta or {}).get("almond/caller_request_id"),
            "token": os.environ["ALMONDRHINO_SESSION_TOKEN"],
        }
        return types.CallToolResult(content=[], structured_content=result)

    server = Server("offline-worker", on_list_tools=list_tools, on_call_tool=call_tool)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] == "changed"))
