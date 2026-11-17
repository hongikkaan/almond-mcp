"""FastMCP child with real ProjectRuntime middleware and an offline execution."""
import asyncio
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

from fastmcp import FastMCP

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixtures.timeout_stdio_worker import GET_EXECUTION, PROJECT_PYTHON, WORKER_STATE, execution_value, read, write


def server_for(directory, runtime=None):
    mcp = FastMCP("almond-offline-project-runtime")
    if runtime is not None:
        mcp.add_middleware(runtime)

    @mcp.tool(name=PROJECT_PYTHON)
    async def run_project_python(code: str, timeout_seconds: int = 60) -> dict:
        batch = runtime.scope.get()
        execution = dict(request_id=uuid4().hex, operation_id=batch.operation_id)

        def snapshot():
            value = execution_value(directory, execution, include_diagnostics=True)
            value.update(pending=not value["completed"], uncertain=not value["completed"])
            return value

        batch.register_external(SimpleNamespace(snapshot=snapshot))
        write(directory / "active.json", execution)
        while not (directory / "release").exists():
            await asyncio.sleep(0.01)
        return execution_value(directory, execution)

    @mcp.tool(name=GET_EXECUTION)
    async def get_execution(request_id: str) -> dict:
        (directory / "wire-query").touch()
        execution = read(directory / "active.json")
        assert request_id == execution["request_id"]
        return execution_value(directory, execution)

    @mcp.tool(name=WORKER_STATE)
    def worker_state() -> dict:
        return runtime.completion()

    return mcp


async def catalog(directory):
    tools = await server_for(directory).list_tools()
    return {"tools": [tool.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
                      for tool in tools if tool.name != WORKER_STATE]}


async def run(directory):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src/mcp/runtime"))
    from shared_store import ProjectRuntime

    session = directory / ".sessions" / "fixture-token"
    session.mkdir(parents=True)
    write(session / "worker.json", {"pid": os.getpid(), "process_start_ticks": "1"})
    locations = dict(storage=directory, session_dir=session, call_root=directory / "calls", temp=directory)
    runtime = ProjectRuntime(SimpleNamespace(token="fixture-token"), {}, locations, check_owner=False)
    runtime.validate = lambda: None  # Substitute the live binding check only.
    await server_for(directory, runtime).run_async(transport="stdio", show_banner=False)


if __name__ == "__main__":
    asyncio.run(run(Path(sys.argv[1])))
