"""Persistent, explicit JSON-line MCP client for dot. No Codex configuration edits."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp.client.session import ClientSession
from mcp.types import PaginatedRequestParams
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[2]
USAGE = {
    "help": {"op": "help"},
    "catalog": {"op": "catalog"},
    "describe": {"op": "describe", "names": ["connect_01-list_up", "connect_02-session"]},
    "call": {"op": "call", "name": "connect_01-list_up", "arguments": {}},
    "shutdown": {"op": "shutdown"},
}


def dump(value):
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


class DotClient:
    """Own one initialized MCP session and its pinned tool catalog."""

    def __init__(self, session, tools):
        self.session = session
        self.tools = {tool.name: tool for tool in tools}

    def catalog(self):
        return {"count": len(self.tools), "names": list(self.tools), "usage": USAGE}

    async def dispatch(self, request):
        if not isinstance(request, dict):
            raise ValueError("Request must be a JSON object.")
        op = request.get("op")
        if op == "help":
            return {"usage": USAGE,
                    "connection": "Call connect_01-list_up tool, then connect_02-session tool with its exact host_id/model_path. Use the returned connection_id in subsequent calls in THIS session. Use connect_04-disconnect tool when finished; shutdown closes this client's MCP session, not Rhino.",
                    "errors": "Calls are never retried automatically. A timeout or error does not prove rollback."}
        if op == "catalog":
            return self.catalog()
        if op == "describe":
            names = request.get("names")
            if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names):
                raise ValueError("names must be a nonempty array of exact tool names.")
            missing = [n for n in names if n not in self.tools]
            if missing:
                raise ValueError("Unknown tools: " + ", ".join(missing))
            return {"tools": [dump(self.tools[n]) for n in names]}
        if op == "call":
            name = request.get("name")
            if not isinstance(name, str) or name not in self.tools:
                raise ValueError("name must be an exact name from catalog.")
            arguments = request.get("arguments", {})
            if not isinstance(arguments, dict):
                raise ValueError("arguments must be a JSON object.")
            # Preserve text, images, structuredContent and isError. No parsing,
            # summarization, implicit connection, or automatic mutation retries.
            return {"tool_result": dump(await self.session.call_tool(name, arguments))}
        raise ValueError("Unknown op. Use help, catalog, describe, call or shutdown.")


def error_text(exc):
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(error_text(child) for child in exc.exceptions)
    return f"{type(exc).__name__}: {exc}"


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


async def run(args):
    parameters = StdioServerParameters(
        command=str(args.server_python),
        args=["-B", "-X", "utf8", "-u", str(args.server_entry)],
        env=dict(os.environ),
        cwd=str(ROOT),
    )
    # The public host entry owns its normal desktop-runtime preparation.
    # Closing these contexts terminates only the server launched by this client.
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=args.timeout) as session:
            initialization = await session.initialize()
            tools = []
            cursor = None
            seen = set()
            while True:
                page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor) if cursor else None)
                tools.extend(page.tools)
                cursor = page.next_cursor
                if not cursor:
                    break
                if cursor in seen:
                    raise RuntimeError("Server repeated a catalog cursor.")
                seen.add(cursor)
            client = DotClient(session, tools)
            emit({"event": "ready", "client_pid": os.getpid(),
                  "initialization": dump(initialization), "catalog": client.catalog()})
            while True:
                line = await asyncio.to_thread(sys.stdin.readline)
                if not line:
                    break
                if not line.strip():
                    continue
                request = None
                try:
                    request = json.loads(line)
                    if isinstance(request, dict) and request.get("op") == "shutdown":
                        break
                    response = await client.dispatch(request)
                    emit({"id": request.get("id"), "ok": True, **response})
                except Exception as exc:
                    emit({"id": request.get("id") if isinstance(request, dict) else None,
                          "ok": False, "error": error_text(exc), "error_type": type(exc).__name__,
                          "note": "No automatic retry. If a tool call was sent, verify its outcome before retrying."})
    emit({"event": "closed"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python", type=Path, default=ROOT / "src/engine/.venv/Scripts/python.exe")
    parser.add_argument("--server-entry", type=Path, default=ROOT / "src/cos/codex_host.py")
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        emit({"event": "fatal", "error": error_text(exc), "error_type": type(exc).__name__})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
