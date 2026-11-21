"""Own one external invocation's admission, wait and exact result recovery.

The connection broker chooses a connection and owns its lifetime. This owner
never discovers, attaches, detaches, launches or replays a Rhino operation.
ProjectRuntime remains the authority for native and retained CLI completion.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
import json
from uuid import uuid4

import mcp_types as types
from almond_mcp.tool_guidance import guide_payload


SCRIPT_TOOLS = frozenset({"script_01-run_project_python", "script_02-run_rhino"})
RECOVERY_TIMEOUT = 10.0


def json_result(value: dict, name: str = "", *, wrapped=False) -> types.CallToolResult:
    value = guide_payload(name, value) if name else value
    serialized = json.dumps(value, ensure_ascii=False)
    return types.CallToolResult(content=[types.TextContent(type="text", text=serialized)],
                                structured_content={"result": serialized} if wrapped else value)


def error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=message)], is_error=True)


def result_dict(result: types.CallToolResult) -> dict:
    if result.is_error:
        raise RuntimeError("Almond worker state is unavailable.")
    value = result.structured_content
    if value is None:
        value = json.loads(next(c.text for c in result.content if c.type == "text"))
    if not isinstance(value, dict):
        raise RuntimeError("Invalid Almond worker state.")
    return value


def _identity(value):
    return (isinstance(value, str) and len(value) == 32
            and all(char in "0123456789abcdef" for char in value))


@dataclass
class Invocation:
    abandoned: bool = False
    worker_dispatched: bool = False


class ExecutionInvocations:
    """Operate an already selected connection through narrow lifecycle ports."""

    def __init__(self, *, call_timeout, queue_timeout, reject_pending_close, check_binding,
                 read_execution, wrapped_tools=()):
        self.call_timeout, self.queue_timeout = call_timeout, queue_timeout
        self.reject_pending_close, self.check_binding = reject_pending_close, check_binding
        self.read_execution = read_execution
        self.wrapped_tools = frozenset(wrapped_tools)

    async def _fail(self, conn, reason):
        if not conn.closing:
            conn.state, conn.reason = "unconfirmed", reason
        with suppress(Exception):
            await conn.control.request("fail", session_token=conn.token, reason=reason[:300])

    @staticmethod
    def _cli_only(state):
        return (bool(state.get("external_requests")) and state.get("native_uncertain") is False
                and not state.get("native_pending"))

    @staticmethod
    def _current(state, caller_request_id):
        return (state.get("caller_request_id") == caller_request_id
                and _identity(state.get("operation_id")))

    @staticmethod
    def _retain_cli(conn, reservation_id):
        if conn.closing:
            return False
        conn.state = "recovering"
        conn.reason = "RhinoCode outcome is being tracked. Read script_03-get_execution tool; do not repeat the work."
        conn.recovery_request_id = reservation_id
        conn.in_flight = True
        return True

    @staticmethod
    def _observe_task(task):
        if not task.cancelled():
            task.exception()  # A returned pending response must not orphan a late transport error.

    async def _read(self, conn, arguments, *, operation_id=None):
        options = {} if operation_id is None else {"operation_id": operation_id}
        return await asyncio.wait_for(asyncio.to_thread(
            self.read_execution, conn.binding, arguments, **options), RECOVERY_TIMEOUT)

    async def _pending_result(self, conn, name, reservation_id):
        state = await asyncio.wait_for(conn.worker.state(), RECOVERY_TIMEOUT)
        if (not self._current(state, reservation_id) or not self._cli_only(state)
                or conn.closing):
            raise RuntimeError("No current CLI-only execution evidence is available.")
        requests = state.get("external_requests")
        if not isinstance(requests, list) or len(requests) != 1:
            raise RuntimeError("The current operation has no unique RhinoCode request.")
        request = requests[0]
        if (not isinstance(request, dict) or not _identity(request.get("request_id"))
                or request.get("operation_id", state["operation_id"]) != state["operation_id"]):
            raise RuntimeError("RhinoCode request identity does not match the current operation.")
        request_id = request["request_id"]
        # register_external precedes publish: an in-memory ID is not evidence
        # until the existing recovery reader validates the durable exact file.
        value = await self._read(conn, {"request_id": request_id, "include_diagnostics": True},
                                 operation_id=state["operation_id"])
        if value.get("request_id") != request_id:
            raise RuntimeError("The retained execution returned a different request identity.")
        if not self._retain_cli(conn, reservation_id):
            raise RuntimeError("The connection closed while execution evidence was being read.")
        conn.recovery_execution_id = request_id
        value["connection_state"] = conn.state
        value["message"] = (
            "The first response wait ended. The original operation is retained. "
            f"Read script_03-get_execution tool with request_id={request_id}. "
            "For beyond, also pass the original connection_id. Do not repeat the Rhino work.")
        if not value.get("completed"):
            value["timed_out"] = True
        return json_result(value, name, wrapped=name in self.wrapped_tools)

    async def recover_execution(self, conn, arguments):
        active_call = conn.retained_call is not None and not conn.retained_call.done()
        state = None
        if conn.retained_call is not None:
            try:
                state = await asyncio.wait_for(conn.worker.state(), RECOVERY_TIMEOUT)
            except Exception:
                value = await self._read(conn, arguments)
                value.update(connection_state=conn.state, requires_reconnect=True)
                return json_result(value)
            if active_call or state.get("operation_active"):
                # script03 in the worker shares the running tool's serial gate.
                # Files can be observed without releasing its TEMP/DB ownership.
                requested = dict(arguments)
                if not requested.get("request_id") and conn.recovery_execution_id:
                    requested["request_id"] = conn.recovery_execution_id
                value = await self._read(conn, requested)
                value["connection_state"] = conn.state
                if state.get("native_uncertain"):
                    value["requires_reconnect"] = True
                return json_result(value)
        try:
            result = await asyncio.wait_for(conn.worker.call("script_03-get_execution", arguments), RECOVERY_TIMEOUT)
            value = result_dict(result)
            state = await asyncio.wait_for(conn.worker.state(), RECOVERY_TIMEOUT)
        except Exception:
            value = await self._read(conn, arguments)
            value.update(connection_state=conn.state, requires_reconnect=True)
            return json_result(value)
        settled_call = conn.retained_call is None or conn.retained_call.done()
        if (conn.state == "recovering" and not conn.closing and settled_call
                and not state.get("operation_active") and not state.get("pending")
                and not state.get("uncertain") and state.get("native_uncertain") is False):
            try:
                await self.check_binding(conn)
                if conn.closing or conn.state != "recovering":
                    raise RuntimeError("Connection changed while recovery was checking the binding.")
                await conn.control.request("end", session_token=conn.token,
                                           request_id=conn.recovery_request_id)
                conn.in_flight = False
                if not conn.closing and conn.state == "recovering":
                    conn.state, conn.reason = "ready", ""
                    conn.recovery_request_id = ""
                    conn.recovery_execution_id = ""
                    conn.retained_call = None
            except Exception as exc:
                await self._fail(conn, str(exc))
                value["requires_reconnect"] = True
        value["connection_state"] = conn.state
        if state.get("native_uncertain") or conn.closing:
            value["requires_reconnect"] = True
        return json_result(value)

    async def invoke(self, conn, name, arguments, invocation):
        from project import serial_gate
        # The outer first-response budget includes admission/control time for
        # scripts. The separate bounded evidence reads have ample margin to600.
        deadline = asyncio.get_running_loop().time() + self.call_timeout if name in SCRIPT_TOOLS else None
        async with serial_gate(conn.lock, self.queue_timeout):
            if name != "script_03-get_execution":
                self.reject_pending_close(conn.binding)
            return await self.invoke_locked(conn, name, arguments, invocation, deadline=deadline)

    async def invoke_locked(self, conn, name, arguments, invocation, *, deadline=None):
        if name == "script_03-get_execution":
            if conn.closing:
                value = await self._read(conn, arguments)
                value.update(connection_state=conn.state, requires_reconnect=True)
                return json_result(value)
            return await self.recover_execution(conn, arguments)
        if invocation.abandoned:
            raise RuntimeError("Caller stopped while this request was queued. No Rhino request was sent.")
        if conn.closing or conn.state != "ready":
            raise RuntimeError(f"Connection is {conn.state}: {conn.reason}. Inspect Rhino before reconnecting.")
        scripted = name in SCRIPT_TOOLS
        if scripted and deadline is None:
            deadline = asyncio.get_running_loop().time() + self.call_timeout
        reservation_id = uuid4().hex
        conn.in_flight = True
        try:
            await conn.control.request("begin", session_token=conn.token, request_id=reservation_id)
            if (conn.watch_again and not invocation.abandoned and not conn.closing
                    and conn.state == "ready"):
                conn.watch_again = False
                try:
                    await self.check_binding(conn)
                except Exception:
                    await conn.control.request("end", session_token=conn.token, request_id=reservation_id)
                    conn.in_flight = False
                    raise
            stop_before_dispatch = (invocation.abandoned or conn.closing or conn.state != "ready"
                                    or (scripted and asyncio.get_running_loop().time() >= deadline))
            if stop_before_dispatch:
                await conn.control.request("end", session_token=conn.token, request_id=reservation_id)
                conn.in_flight = False
        except BaseException as exc:
            await self._fail(conn, str(exc) or "Rhino reservation could not be confirmed.")
            raise
        if stop_before_dispatch:
            raise RuntimeError("Caller stopped or its first-response budget expired before Rhino execution began.")

        invocation.worker_dispatched = True
        try:
            if scripted:
                task = asyncio.create_task(conn.worker.call(name, arguments, caller_request_id=reservation_id))
                task.add_done_callback(self._observe_task)
                conn.retained_call = task
                try:
                    result = await asyncio.wait_for(asyncio.shield(task),
                        max(0, deadline - asyncio.get_running_loop().time()))
                except TimeoutError:
                    if task.done():
                        result = task.result()
                    else:
                        try:
                            return await self._pending_result(conn, name, reservation_id)
                        except Exception as exc:
                            if task.done():
                                result = task.result()
                            else:
                                reason = ("The first response wait ended, but exact current execution recovery is unavailable. "
                                          "The outcome is unknown; do not repeat the Rhino work. " + str(exc))
                                await self._fail(conn, reason)
                                return error_result(reason)
            else:
                result = await asyncio.wait_for(conn.worker.call(name, arguments), self.call_timeout)
            state = await conn.worker.state()
            if state.get("pending") or state.get("uncertain"):
                if (self._cli_only(state) and not conn.closing
                        and (not scripted or self._current(state, reservation_id))):
                    self._retain_cli(conn, reservation_id)
                    return result
                raise RuntimeError("Rhino execution outcome is unconfirmed. Do not repeat the operation automatically.")
            if invocation.abandoned and self._cli_only(state) and not conn.closing:
                self._retain_cli(conn, reservation_id)
                return result
            await conn.control.request("end", session_token=conn.token, request_id=reservation_id)
            conn.in_flight = False
            if scripted:
                conn.retained_call = None
            return result
        except BaseException as exc:
            state = None
            if not conn.closing:
                with suppress(Exception):
                    state = await conn.worker.state()
            if (state is not None and self._cli_only(state) and not conn.closing
                    and (not scripted or self._current(state, reservation_id))):
                self._retain_cli(conn, reservation_id)
                raise RuntimeError(conn.reason) from exc
            await self._fail(conn, str(exc) or "Caller canceled while Rhino might still be executing.")
            raise
