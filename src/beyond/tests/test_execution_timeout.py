"""Reject stale timeout recovery without canceling or replaying the worker."""
import asyncio
import copy
import json

import pytest

from external_host import Broker, Connection, UNKNOWN_CONNECTION, json_result


CONNECTION_ID = "1" * 32
TOOL = "script_01-run_project_python"
OPERATION = "a" * 32
EXECUTION = "b" * 32
CATALOG = {"tools": [{"name": TOOL, "inputSchema": {"type": "object", "properties": {}}}]}


class Control:
    def __init__(self):
        self.actions = []

    async def request(self, action, **fields):
        self.actions.append(action)
        return {"state": "connected"}


class DelayedWorker:
    def __init__(self, variation):
        self.variation = variation
        self.release = asyncio.Event()
        self.entered = asyncio.Event()
        self.cancelled = False
        self.caller = None
        self.calls = 0

    async def call(self, name, arguments, *, caller_request_id=None):
        self.calls += 1
        self.caller = caller_request_id
        self.entered.set()
        try:
            await self.release.wait()
            return json_result({"status": "executed", "completed": True, "request_id": EXECUTION})
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def state(self):
        value = dict(caller_request_id=self.caller, operation_id=OPERATION, operation_active=True,
                     pending=True, uncertain=True, native_uncertain=False, native_pending=False,
                     external_requests=[dict(request_id=EXECUTION, operation_id=OPERATION)])
        if self.variation == "stale_caller":
            value["caller_request_id"] = "c" * 32
        elif self.variation == "missing_request":
            value["external_requests"] = []
        elif self.variation == "multiple_requests":
            value["external_requests"] *= 2
        elif self.variation == "native_uncertain":
            value["native_uncertain"] = True
        elif self.variation == "native_pending":
            value["native_pending"] = True
        elif self.variation == "wrong_operation":
            value["external_requests"][0]["operation_id"] = "d" * 32
        return value


async def timeout_after_dispatch(broker, worker, name=TOOL, arguments=None):
    """Advance the real asyncio timer only after the intended worker boundary."""
    loop = asyncio.get_running_loop()
    real_time, now = loop.time, [0.0]
    loop.time = lambda: now[0]
    try:
        routed = dict(arguments if arguments is not None else {"timeout_seconds": 600}, connection_id=CONNECTION_ID)
        caller = asyncio.create_task(broker.call(name, routed))
        for _ in range(100):
            if worker.entered.is_set() or caller.done():
                break
            await asyncio.sleep(0)
        assert worker.entered.is_set(), "The test request never reached its worker boundary."
        now[0] = broker.call_timeout + 1
        return await caller
    finally:
        loop.time = real_time


def test_plan_section_broker_timeout_returns_unknown_cuts_only_after_dispatch(tmp_path):
    async def run():
        from jsonschema import validate
        from almond_mcp.output_contracts import public_output_schema
        name = "drawing_06-generate_plan_section"
        args = {"operation":"Create", "clipping_ids":["00000000-0000-0000-0000-000000000001"]}
        worker, control = DelayedWorker("native_pending"), Control()
        broker = Broker({"tools":[{"name":name, "inputSchema":{"type":"object","properties":{}}}]}, data=tmp_path)
        before = await broker.call(name, dict(args, connection_id=CONNECTION_ID))
        assert before.is_error and before.content[0].text == UNKNOWN_CONNECTION
        conn = Connection(CONNECTION_ID, "host", control, "fixture-token", worker=worker, state="ready")
        broker.connections[conn.connection_id] = conn

        response = await timeout_after_dispatch(broker, worker, name, args)
        assert response.is_error and response.structured_content == {"result":response.content[0].text}
        value = json.loads(response.content[0].text)
        validate(value, public_output_schema("plan_section", wrapped=False))
        assert value["status"] == "error" and value["mutation_state"] == "unknown"
        assert value["unconfirmed_clipping_ids"] == args["clipping_ids"] and "중단" in value["next_step_guide"]
        assert worker.calls == 1 and control.actions == ["begin", "fail"]
        assert conn.state == "unconfirmed" and conn.in_flight
    asyncio.run(run())


@pytest.mark.parametrize("variation", ["stale_caller", "missing_request", "multiple_requests",
    "native_uncertain", "native_pending", "wrong_operation", "missing_file", "wrong_return_id"])
def test_timeout_never_uses_stale_or_unproven_identity(tmp_path, variation):
    async def run():
        worker, control = DelayedWorker(variation), Control()
        broker = Broker(CATALOG, data=tmp_path)
        conn = Connection(CONNECTION_ID, "host", control, "fixture-token", worker=worker, state="ready")
        broker.connections[conn.connection_id] = conn

        reads = []

        def read(binding, arguments, *, operation_id=None):
            reads.append((copy.deepcopy(arguments), operation_id))
            if variation == "missing_file":
                raise FileNotFoundError("The durable request has not been published.")
            return dict(status="pending", completed=False, pending=True,
                        request_id="e" * 32 if variation == "wrong_return_id" else EXECUTION)

        broker._read_execution_files = read
        result = await timeout_after_dispatch(broker, worker)
        assert result.is_error and "outcome is unknown" in result.content[0].text
        assert EXECUTION not in result.content[0].text
        assert conn.state == "unconfirmed" and conn.in_flight
        assert control.actions == ["begin", "fail"]
        assert worker.calls == 1 and not worker.cancelled and not conn.retained_call.done()
        assert bool(reads) == (variation in {"missing_file", "wrong_return_id"})
        worker.release.set()
        await conn.retained_call
        assert conn.state == "unconfirmed" and conn.in_flight
        assert control.actions == ["begin", "fail"]
    asyncio.run(run())


def test_closing_during_durable_read_cannot_resurrect_connection(tmp_path):
    async def run():
        worker, control = DelayedWorker("valid"), Control()
        broker = Broker(CATALOG, data=tmp_path)
        conn = Connection(CONNECTION_ID, "host", control, "fixture-token", worker=worker, state="ready")
        broker.connections[conn.connection_id] = conn


        def read(binding, arguments, *, operation_id=None):
            conn.closing, conn.state, conn.reason = True, "disconnecting", "Owner changed"
            return dict(status="pending", completed=False, pending=True, request_id=EXECUTION)

        broker._read_execution_files = read
        result = await timeout_after_dispatch(broker, worker)
        assert result.is_error and conn.state == "disconnecting" and conn.reason == "Owner changed"
        assert "end" not in control.actions and not worker.cancelled
        worker.release.set()
        await conn.retained_call
        assert conn.state == "disconnecting" and conn.in_flight
    asyncio.run(run())


def test_broker_301_returns_exact_pending_without_cancelling_worker(tmp_path):
    async def run():
        worker, control = DelayedWorker("valid"), Control()
        broker = Broker(CATALOG, data=tmp_path)
        conn = Connection(CONNECTION_ID, "host", control, "fixture-token", worker=worker, state="ready")
        broker.connections[conn.connection_id] = conn

        broker._read_execution_files = lambda *_, **__: dict(
            status="pending", pending=True, completed=False, request_id=EXECUTION)
        assert broker.call_timeout == 300
        result = await timeout_after_dispatch(broker, worker)
        assert not result.is_error and result.structured_content["request_id"] == EXECUTION
        assert f"request_id={EXECUTION}" in result.structured_content["message"]
        assert "original connection_id" in result.structured_content["message"]
        assert result.structured_content["pending"] and not worker.cancelled
        assert control.actions == ["begin"] and conn.state == "recovering" and conn.in_flight
        worker.release.set()
        await conn.retained_call
    asyncio.run(run())
