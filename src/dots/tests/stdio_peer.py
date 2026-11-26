import json
import os
from pathlib import Path

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


ATTACH = "connect_02-session"
INSPECT = "inspect_fixture"
PIXEL = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
CATALOG = [
    types.Tool(name=ATTACH, inputSchema={"type": "object"}),
    types.Tool(
        name=INSPECT,
        description="Return the selected drawing identifier and thumbnail.",
        inputSchema={
            "type": "object",
            "properties": {"connection_id": {"type": "string"}},
            "required": ["connection_id"],
        },
    ),
]


async def _list_tools(_, params):
    if params and params.cursor == "more":
        return types.ListToolsResult(tools=CATALOG[1:])
    return types.ListToolsResult(tools=CATALOG[:1], nextCursor="more")


async def _call_tool(_, params):
    args = params.arguments or {}
    connection = args.get("connection_id", "")
    with Path(os.environ["DOT_FIXTURE_CALLS"]).open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps([params.name, args]) + "\n")

    if params.name == ATTACH:
        requested = args["model_path"]
        return types.CallToolResult(
            content=[], structuredContent={"connection_id": requested},
            isError=requested == "unavailable",
        )
    if args.get("stall"):
        # Leave the request unanswered after registering it as received.
        await anyio.sleep_forever()
    if not connection:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="connection_id가 지정되지 않았습니다")],
            isError=True,
        )
    return types.CallToolResult(
        content=[types.ImageContent(type="image", mimeType="image/gif", data=PIXEL)],
        structuredContent={"document": connection},
    )


async def main():
    server = Server("disposable-drawing-peer", on_list_tools=_list_tools, on_call_tool=_call_tool)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
