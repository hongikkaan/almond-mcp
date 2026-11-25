"""Offline MCP child. Reproduce the runtime's serial gate and receipt ordering."""
import asyncio
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from mcp import types
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server


PROJECT_PYTHON = "script_01-run_project_python"
RUN_RHINO = "script_02-run_rhino"
GET_EXECUTION = "script_03-get_execution"
WORKER_STATE = "worker_state"


def catalog():
    repo = Path(__file__).resolve().parents[4]
    schemas = json.loads((repo / "tests/integration/tool_schemas.json").read_text(encoding="utf-8"))
    return {"tools": [schemas[name] for name in (PROJECT_PYTHON, RUN_RHINO, GET_EXECUTION)]}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    temporary.replace(path)


def execution_value(directory, execution, *, include_diagnostics=False):
    path = directory / (execution["request_id"] + ".json")
    if path.exists():
        value = read(path)
    else:
        value = dict(
            status="pending", completed=False, pending=True, uncertain=True,
            completion_state="awaiting_receipt", mutation_state="unknown",
            message="Execution is still running. Read script_03-get_execution tool with request_id.",
        )
    value["request_id"] = execution["request_id"]
    if include_diagnostics:
        value["operation_id"] = execution["operation_id"]
    return value


def response(name, value):
    serialized = json.dumps(value)
    structured = {"result": serialized} if name == RUN_RHINO else value
    return types.CallToolResult(content=[types.TextContent(type="text", text=serialized)],
                                structured_content=structured)


async def run(directory):
    tools = [types.Tool.model_validate(tool) for tool in catalog()["tools"]]
    tools.append(types.Tool(name=WORKER_STATE, input_schema={"type": "object"}))
    serial = asyncio.Lock()
    execution = {}
    operation_active = False
    launches = 0

    async def list_tools(ctx, params):
        return types.ListToolsResult(tools=tools)

    async def call_tool(ctx, params):
        nonlocal execution, operation_active, launches
        name, args = params.name, params.arguments or {}
        if name == WORKER_STATE:
            pending = bool(execution and not execution_value(directory, execution)["completed"])
            return response(name, dict(
                caller_request_id=execution.get("caller_request_id"),
                operation_id=execution.get("operation_id"),
                external_requests=[dict(execution, pending=pending, uncertain=pending)] if execution else [],
                native_uncertain=False, native_pending=False,
                operation_active=operation_active, pending=operation_active or pending, uncertain=pending,
            ))
        if name == GET_EXECUTION:
            # Record attempts before acquiring the gate, so a recovery routed
            # to this child while the original call is active cannot pass unnoticed.
            (directory / "wire-query").touch()
            async with serial:
                assert args["request_id"] == execution["request_id"]
                return response(name, execution_value(directory, execution,
                                                       include_diagnostics=args.get("include_diagnostics", False)))
        async with serial:
            assert name in (PROJECT_PYTHON, RUN_RHINO)
            assert args["timeout_seconds"] == 600
            launches += 1
            execution = dict(
                request_id=uuid4().hex, operation_id=uuid4().hex,
                caller_request_id=(params.meta or {}).get("almond/caller_request_id"),
                launches=launches,
            )
            operation_active = True
            write(directory / "active.json", execution)
            try:
                # A separate receipt may become visible before worker cleanup.
                # The test releases the reply explicitly; no guessed delay.
                while not (directory / "release").exists():
                    if (directory / "exit").exists():
                        os._exit(17)
                    await asyncio.sleep(0.01)
                if launches > 1:
                    write(directory / (execution["request_id"] + ".json"),
                          dict(status="executed", completed=True, result={"launch": launches}))
                value = execution_value(directory, execution)
                assert value["completed"] is True
                (directory / "wire-return").touch()
                return response(name, value)
            except asyncio.CancelledError:
                (directory / "wire-cancel").touch()
                raise
            finally:
                operation_active = False

    server = Server("almond-offline-timeout-fixture", on_list_tools=list_tools, on_call_tool=call_tool,
                    get_tool_input_schema={tool.name: tool.input_schema for tool in tools}.get)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(run(Path(sys.argv[1])))
