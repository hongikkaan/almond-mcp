"""Run the real Worker and Broker over MCP stdio without starting Rhino."""
import asyncio
import json
from pathlib import Path
import sys

import jsonschema
import pytest
from mcp.shared.exceptions import MCPError
from mcp_types import CONNECTION_CLOSED

import external_host
from external_host import Broker, Connection, Worker
from fixtures import timeout_fastmcp_worker as fastmcp_fixture
from fixtures import timeout_stdio_worker as fixture


CONNECTION_ID = "1" * 32


class Control:
    """Acknowledge native reservations without a Rhino process."""

    def __init__(self):
        self.actions = []
        self.reservation = None

    async def request(self, action, **fields):
        assert fields["session_token"] == "fixture-token"
        self.actions.append(action)
        if action == "begin":
            assert self.reservation is None
            self.reservation = fields["request_id"]
        elif action == "end":
            assert fields["request_id"] == self.reservation
            self.reservation = None
        elif action == "status":
            return {"state": "connected"}
        elif action == "detach":
            return {"detached": True}
        else:
            raise AssertionError(f"Unexpected native control action: {action}")
        return {"ok": True}

    async def close(self):
        pass


async def wait_exists(path):
    while not path.exists():
        await asyncio.sleep(0.01)


def validate_result(broker, name, result):
    assert not result.is_error, result.content
    schema = next(tool.output_schema for tool in broker.tools if tool.name == name)
    value = result.structured_content
    jsonschema.validate(value, schema)
    if name == fixture.RUN_RHINO:
        assert schema["x-fastmcp-wrap-result"] is True
        value = json.loads(value["result"])
        jsonschema.validate(value, schema["properties"]["result"]["contentSchema"])
    assert json.loads(result.content[0].text) == value
    return value


@pytest.mark.parametrize(("tool", "worker_exits"), [
    (fixture.PROJECT_PYTHON, False),
    (fixture.RUN_RHINO, False),
    (fixture.RUN_RHINO, True),
])
def test_delayed_stdio_script_recovers_the_same_execution(tmp_path, monkeypatch, tool, worker_exits):
    directory = tmp_path / "worker"
    directory.mkdir()
    worker_catalog = fixture.catalog()
    binding = dict(ready_path=str(directory / "mock-ready.json"), port=1, token="fixture-token")
    control = Control()
    durable_reads = []
    original_params = external_host.StdioServerParameters

    def child_params(**parameters):
        # Replace only executable/argv. Worker still owns its real ClientSession
        # and transport, including initialization and schema checks.
        assert Path(parameters["args"][2]).name == "external_worker.py"
        return original_params(**{
            **parameters, "command": sys.executable,
            "args": ["-B", "-u", fixture.__file__, str(directory)],
        })

    def find_binding(request_id, *, connection_id):
        assert connection_id == CONNECTION_ID
        assert fixture.read(directory / "active.json")["request_id"] == request_id
        return binding

    def read_evidence(requested_binding, arguments, *, operation_id=None):
        assert requested_binding is binding
        execution = fixture.read(directory / "active.json")
        assert arguments["request_id"] == execution["request_id"]
        if operation_id is not None:
            assert operation_id == execution["operation_id"]
        durable_reads.append((arguments["request_id"], operation_id))
        return fixture.execution_value(directory, execution,
                                       include_diagnostics=arguments.get("include_diagnostics", False))

    monkeypatch.setattr(external_host, "StdioServerParameters", child_params)

    async def run():
        broker = Broker(worker_catalog, data=tmp_path, call_timeout=0.8, read_execution=read_evidence)
        monkeypatch.setattr(broker.recovery_store, "find_binding", find_binding)
        worker = Worker(binding, CONNECTION_ID, worker_catalog)
        conn = Connection(CONNECTION_ID, "host", control, binding["token"],
                          binding=binding, worker=worker, state="ready")
        broker.connections[conn.connection_id] = conn
        broker.host_connections[conn.host_id] = conn.connection_id

        arguments = {"code": "result = 1"} if tool == fixture.PROJECT_PYTHON else {"script": "result = 1"}
        arguments.update(timeout_seconds=600, connection_id=CONNECTION_ID)
        try:
            await worker.start()
            caller = asyncio.create_task(broker.call(tool, arguments))
            await wait_exists(directory / "active.json")
            execution = fixture.read(directory / "active.json")
            request_id = execution["request_id"]
            initial = validate_result(broker, tool, await caller)
            assert initial["request_id"] == request_id
            assert initial["status"] == "pending" and initial["completed"] is False
            assert "script_03-get_execution" in " ".join(
                initial.get(key, "") for key in ("message", "next_step_guide"))
            assert execution["caller_request_id"] == control.reservation != request_id
            assert conn.state == "recovering" and conn.in_flight
            assert conn.recovery_request_id == control.reservation
            assert durable_reads == [(request_id, execution["operation_id"])]
            retained = conn.retained_call
            assert not retained.done()

            query = {"request_id": request_id, "connection_id": CONNECTION_ID}
            pending = validate_result(broker, fixture.GET_EXECUTION, await broker.call(fixture.GET_EXECUTION, query))
            assert pending["request_id"] == request_id and pending["completed"] is False
            assert pending["connection_state"] == "recovering" and not pending.get("requires_reconnect", False)
            assert len(durable_reads) == 2 and durable_reads[-1][0] == request_id
            assert not (directory / "wire-query").exists()

            fixture.write(directory / (request_id + ".json"),
                          dict(status="executed", completed=True, result={"launch": 1}))
            completed = validate_result(broker, fixture.GET_EXECUTION, await broker.call(fixture.GET_EXECUTION, query))
            assert completed["request_id"] == request_id and completed["completed"] is True
            assert completed["result"] == {"launch": 1}
            assert len(durable_reads) == 3 and not (directory / "wire-query").exists()
            assert not retained.done() and control.actions == ["begin"]
            assert conn.state == "recovering" and conn.in_flight

            if worker_exits:
                (directory / "exit").touch()
                with pytest.raises(MCPError) as error:
                    await asyncio.wait_for(asyncio.shield(retained), 3)
                assert error.value.code == CONNECTION_CLOSED
                assert retained.done() and not retained.cancelled()
                recover = validate_result(broker, fixture.GET_EXECUTION,
                                          await broker.call(fixture.GET_EXECUTION, query))
                assert recover["request_id"] == request_id and recover["completed"] is True
                assert recover["result"] == {"launch": 1}
                assert recover["requires_reconnect"] is True
                assert "end" not in control.actions
                assert not (directory / "wire-return").exists()
                return

            (directory / "release").touch()
            late_reply = validate_result(broker, tool, await asyncio.shield(retained))
            assert late_reply["request_id"] == request_id and late_reply["completed"] is True
            assert (directory / "wire-return").exists() and not (directory / "wire-cancel").exists()
            assert control.actions == ["begin"]

            final = validate_result(broker, fixture.GET_EXECUTION, await broker.call(fixture.GET_EXECUTION, query))
            assert final["request_id"] == request_id and final["completed"] is True
            assert conn.state == "ready" and not conn.in_flight
            assert control.reservation is None and control.actions.count("end") == 1

            fresh = validate_result(broker, tool, await broker.call(tool, arguments))
            assert fresh["request_id"] != request_id and fresh["result"] == {"launch": 2}
            assert conn.state == "ready" and not conn.in_flight
            assert control.actions.count("begin") == control.actions.count("end") == 2
        finally:
            # Stop the worker even when an assertion fails while its gate is held.
            await broker.close()

    asyncio.run(asyncio.wait_for(run(), 12))


def test_fastmcp_wire_meta_reaches_the_owned_runtime_operation(tmp_path, monkeypatch):
    directory = tmp_path / "worker"
    directory.mkdir()
    binding = dict(ready_path=str(directory / "mock-ready.json"), port=1, token="fixture-token")
    control = Control()
    native_operation = directory / ".sessions" / "fixture-token" / "operation.json"
    original_params = external_host.StdioServerParameters

    def child_params(**parameters):
        return original_params(**{
            **parameters, "command": sys.executable,
            "args": ["-B", "-u", fastmcp_fixture.__file__, str(directory)],
        })

    def read_evidence(requested_binding, arguments, *, operation_id=None):
        assert requested_binding is binding
        execution = fixture.read(directory / "active.json")
        assert arguments["request_id"] == execution["request_id"]
        if operation_id is not None:
            assert operation_id == execution["operation_id"]
        return fixture.execution_value(directory, execution, include_diagnostics=operation_id is not None)

    monkeypatch.setattr(external_host, "StdioServerParameters", child_params)

    async def run():
        catalog = await fastmcp_fixture.catalog(directory)
        broker = Broker(catalog, data=tmp_path, call_timeout=0.8, read_execution=read_evidence)
        monkeypatch.setattr(broker.recovery_store, "find_binding", lambda _, *, connection_id: binding)
        worker = Worker(binding, CONNECTION_ID, catalog)
        conn = Connection(CONNECTION_ID, "host", control, binding["token"],
                          binding=binding, worker=worker, state="ready")
        broker.connections[conn.connection_id] = conn
        broker.host_connections[conn.host_id] = conn.connection_id

        try:
            await worker.start()
            caller = asyncio.create_task(broker.call(fixture.PROJECT_PYTHON, {"code": "result = 1", "connection_id": CONNECTION_ID}))
            await wait_exists(directory / "active.json")
            execution = fixture.read(directory / "active.json")
            request_id, operation_id = execution["request_id"], execution["operation_id"]
            value = validate_result(broker, fixture.PROJECT_PYTHON, await caller)
            assert value["request_id"] == request_id and value["completed"] is False
            operation = fixture.read(native_operation)
            assert operation["caller_request_id"] == control.reservation
            assert operation["operation_id"] == operation_id and operation["state"] == "running"
            state = await worker.state()
            assert state["caller_request_id"] == control.reservation
            assert state["operation_id"] == operation_id and state["operation_active"]
            assert conn.state == "recovering" and conn.in_flight
            retained = conn.retained_call
            assert not retained.done()

            fixture.write(directory / (request_id + ".json"), dict(status="executed", completed=True))
            query = {"request_id": request_id, "connection_id": CONNECTION_ID}
            reply = await asyncio.wait_for(broker.call(fixture.GET_EXECUTION, query), 2)
            completed = validate_result(broker, fixture.GET_EXECUTION, reply)
            assert completed["request_id"] == request_id and completed["completed"] is True
            assert not (directory / "wire-query").exists()
            assert not retained.done() and control.actions == ["begin"]

            (directory / "release").touch()
            late = validate_result(broker, fixture.PROJECT_PYTHON, await asyncio.shield(retained))
            assert late["request_id"] == request_id and late["completed"] is True
            assert fixture.read(native_operation)["state"] == "completed"
            settled = await worker.state()
            assert settled["caller_request_id"] == control.reservation
            assert not settled.get("operation_active")

            recovered = validate_result(broker, fixture.GET_EXECUTION, await broker.call(fixture.GET_EXECUTION, query))
            assert recovered["request_id"] == request_id
            assert conn.state == "ready" and not conn.in_flight and control.reservation is None
            assert control.actions == ["begin", "status", "end"]
        finally:
            (directory / "release").touch()
            await broker.close()

    asyncio.run(asyncio.wait_for(run(), 12))
