"""The beyond MCP host for local AlmondRhino connections."""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
import json
import hashlib
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

sys.dont_write_bytecode = True
import mcp_types as types
from jsonschema import Draft202012Validator
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server
from almond_mcp.modeling_guidance import read_policy, startup_instructions
from almond_mcp.output_contracts import public_tool_contract
from almond_mcp.features.modeling.plan_section import unconfirmed_result as unconfirmed_plan_section

from runtime import (ENGINE, PYTHON, ROOT, VERSION, WORKER_STATE_TOOL, check_contract, catalog_identity,
                     load_catalog, validate_worker_tools)
from winpipe import PipeControl, read_hosts
from binding_watch import BindingWatcher
from capture_menu import apply_menu_schema, common_mode_ids
from execution_recovery import ExecutionRecoveryStore, read_bound_execution
from execution_invocation import GET_EXECUTION, ExecutionInvocations, Invocation, json_result, error_result, result_dict
from session_close import SessionCloser

DESCRIPTION = 'beyond는 AlmondRhino를 통해 Rhino의 건축 설계·모델링·도면 작업과 연결 관리를 제공합니다.'
UNSAVED_DOCUMENT = ("Save this Rhino document as a local .3dm, then refresh "
                    "connect_01-list_up tool before connecting.")
UNBOUND_TOOLS = {"context_01-get_policy", "connect_01-list_up", "connect_02-session", "connect_03-start_session"}
MANAGEMENT_TOOLS = (
    "connect_01-list_up", "connect_02-session", "connect_03-start_session",
    "connect_04-disconnect", "connect_05-close_session",
)
POLICY_TOOL = "context_01-get_policy"
MISSING_CONNECTION = "connection_id가 지정되지 않았습니다"
UNKNOWN_CONNECTION = "이 connection_id의 활성 연결이 없습니다. 대상 문서에 다시 연결하세요."


def exposed_tools(catalog: dict, *, mode_ids=()) -> list[types.Tool]:
    worker_tools = {tool["name"]: tool for tool in catalog["tools"]}
    if worker_tools.keys() & set(MANAGEMENT_TOOLS):
        raise RuntimeError("Management tool name collides with Almond.")
    tools = []
    for name in (*worker_tools, *MANAGEMENT_TOOLS):
        contract = public_tool_contract(name)
        declaration = dict(worker_tools.get(name, {}), name=name,
                           description=contract["description"],
                           inputSchema=contract["input_schema"],
                           outputSchema=contract["output_schema"])
        tool = types.Tool.model_validate(declaration)
        apply_menu_schema(tool, mode_ids)
        tools.append(tool)
    return tools


class HostInUse(RuntimeError):
    pass


def host_lease(data: Path, record: dict):
    """Share the legacy barrier, exclusively own one Rhino control connection.

    An old singleton host still excludes every new active client. New adapters
    coexist while idle and new active clients share the barrier, but never the
    same Rhino pipe. Existing model/slot/role leases remain owned by the RHP.
    """
    sys.path.insert(0, str(ENGINE))
    from project import ExclusiveFile, FileLease
    leases = ExitStack()
    try:
        directory = data / "clients"
        directory.mkdir(parents=True, exist_ok=True)
        try:
            leases.enter_context(FileLease(data / "host.lock", shared=True))
        except OSError as exc:
            if exc.errno not in (32, 33):
                raise
            raise HostInUse("A legacy/previous Almond stdio host is active. Finish its work and restart that MCP client to load the updated adapter.") from exc
        identity = f"{record['pid']}:{record['process_start_ticks']}"
        key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        try:
            leases.enter_context(ExclusiveFile(directory / (key + ".lock")))
        except OSError as exc:
            if exc.errno not in (32, 33):
                raise
            raise HostInUse("This Rhino is owned by another Almond client. Keep that connection, or explicitly start a separate Rhino with connect_03-start_session tool.") from exc
        return leases
    except BaseException:
        leases.close()
        raise


def start_rhino(model_path: str, data: Path):
    from session_start import RhinoStart
    return RhinoStart(model_path, data)


class Worker:
    """The same supervisor task enters and exits both AnyIO context managers."""

    def __init__(self, binding: dict, connection_id: str, catalog: dict):
        self.binding, self.connection_id, self.catalog = binding, connection_id, catalog
        self.session = None
        self.stop = asyncio.Event()
        self.ready = asyncio.get_running_loop().create_future()
        self.error = None
        self.owner = None

    async def start(self):
        self.owner = asyncio.create_task(self._own(), name="Almond worker")
        await asyncio.shield(self.ready)

    async def _own(self):
        params = StdioServerParameters(
            command=str(PYTHON),
            args=["-B", "-u", str(ROOT / "external_worker.py"), "--session",
                  self.binding["ready_path"], "--port", str(self.binding["port"]),
                  "--connection-id", self.connection_id],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", ALMONDRHINO_SESSION_TOKEN=self.binding["token"],
                     ALMONDRHINO_CATALOG_ID=catalog_identity(self.catalog)),
            cwd=str(ROOT),
        )
        try:
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer, read_timeout_seconds=600.0) as session:
                    initialization = asyncio.create_task(self._initialize(session))
                    stopped = asyncio.create_task(self.stop.wait())
                    try:
                        done, _ = await asyncio.wait({initialization, stopped}, timeout=60,
                                                     return_when=asyncio.FIRST_COMPLETED)
                        if stopped in done:
                            raise RuntimeError("Worker closed during initialization.")
                        if initialization not in done:
                            raise TimeoutError("Worker initialization timed out.")
                        await initialization
                    finally:
                        initialization.cancel()
                        stopped.cancel()
                        await asyncio.gather(initialization, stopped, return_exceptions=True)
                    self.session = session
                    self.ready.set_result(None)
                    await self.stop.wait()
        except BaseException as exc:
            self.error = exc
            if not self.ready.done():
                self.ready.set_exception(exc)
        finally:
            self.session = None

    async def _initialize(self, session):
        await session.initialize()
        found, cursor = [], None
        while True:
            listing = await session.list_tools(
                params=types.PaginatedRequestParams(cursor=cursor) if cursor else None)
            found.extend(t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in listing.tools)
            cursor = listing.next_cursor
            if not cursor:
                break
            if len(found) > 256:
                raise RuntimeError("Unexpected worker catalog size.")
        validate_worker_tools(self.catalog, found)
        if WORKER_STATE_TOOL not in {t["name"] for t in found}:
            raise RuntimeError("Worker completion tracking is missing.")

    async def call(self, name: str, arguments: dict, *, caller_request_id=None):
        if self.session is None:
            raise RuntimeError("Almond worker is disconnected.")
        meta = {"almond/caller_request_id": caller_request_id} if caller_request_id else None
        return await self.session.call_tool(name, arguments, meta=meta)

    async def state(self):
        return result_dict(await asyncio.wait_for(self.call(WORKER_STATE_TOOL, {}), 10))

    async def close(self):
        self.stop.set()
        if self.owner is not None:
            await asyncio.shield(self.owner)

    def request_stop(self):
        self.stop.set()


@dataclass
class Connection:
    connection_id: str
    host_id: str
    control: object
    token: str
    binding: dict = field(default_factory=dict)
    worker: object = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    state: str = "connecting"
    reason: str = ""
    in_flight: bool = False
    closing: bool = False
    cleanup: dict | None = None
    watch_pending: bool = False
    watch_again: bool = False
    lease: object = None
    recovery_request_id: str = ""
    recovery_execution_id: str = ""
    retained_call: asyncio.Task | None = None

    def session(self):
        reply = {"connection_id": self.connection_id, "state": self.state}
        if self.reason:
            reply["reason"] = self.reason
        return reply

    def target(self):
        reply = dict(self.session(), host_id=self.host_id)
        if self.binding.get("model_path"):
            reply["model_path"] = self.binding["model_path"]
        return reply


@dataclass
class StartAttempt:
    model_path: str
    launch: object = None
    task: asyncio.Task | None = None
    state: str = "starting"
    connection_id: str | None = None
    reason: str = ""


class Broker:
    def __init__(self, catalog: dict, data: Path = ROOT / "data", *,
                 control_factory=PipeControl, worker_factory=Worker, host_reader=read_hosts,
                 contract_check=check_contract, call_timeout: float = 300,
                 watcher_factory=BindingWatcher, lease_factory=host_lease,
                 starter_factory=start_rhino, queue_timeout: float = 10.0,
                 recovery_store_factory=ExecutionRecoveryStore, read_execution=read_bound_execution):
        self.catalog, self.data = catalog, data
        self.control_factory, self.worker_factory = control_factory, worker_factory
        self.host_reader, self.contract_check = host_reader, contract_check
        self.call_timeout = call_timeout
        self.queue_timeout = queue_timeout
        self.tools = exposed_tools(catalog)
        self.worker_tool_names = frozenset(tool["name"] for tool in catalog["tools"])
        self.connections: dict[str, Connection] = {}
        self.host_connections: dict[str, str] = {}
        self.background: set[asyncio.Task] = set()
        self.closing = False
        self.watcher_factory = watcher_factory
        self.watcher = None
        self.lease_factory, self.starter_factory = lease_factory, starter_factory
        self.starts: dict[str, StartAttempt] = {}
        self.recovery_store = recovery_store_factory(data)
        self.session_closer = SessionCloser(data)
        self._execution_reader = read_execution
        self.invocations = ExecutionInvocations(
            call_timeout=call_timeout, queue_timeout=queue_timeout,
            reject_pending_close=self.session_closer.reject_pending, check_binding=self._binding_status,
            read_execution=read_execution,
            wrapped_tools=[tool.name for tool in self.tools
                           if (tool.output_schema or {}).get("x-fastmcp-wrap-result")])

    def binding_changed(self, connection_id: str, error: str | None):
        conn = self.connections.get(connection_id)
        if conn is None or conn.closing or self.closing:
            return
        if error is not None:
            self.binding_invalidated(connection_id, error)
            return
        conn.watch_again = True
        if not conn.watch_pending:
            conn.watch_pending = True
            self.spawn(self._check_binding(conn))

    async def _binding_status(self, conn: Connection):
        # RHP verifies the same session token before reporting in-memory state.
        # Reading ready.json here could block RHP's atomic file replacement.
        status = await conn.control.request("status", session_token=conn.token)
        reason = status.get("reason")
        if reason or status.get("state") not in ("connected", "unconfirmed_or_running"):
            raise RuntimeError(str(reason or "Rhino disconnected this external binding."))

    async def _check_binding(self, conn: Connection):
        try:
            while conn.watch_again and not conn.closing and not self.closing:
                # Do not send UI status while a native call owns this lock:
                # a long-running Rhino script could otherwise time it out.
                async with conn.lock:
                    if conn.closing or self.closing:
                        return
                    conn.watch_again = False
                    try:
                        await self._binding_status(conn)
                    except Exception as exc:
                        conn.reason = str(exc)
                        # Existing detach still validates the owner and refuses
                        # to release Rhino locks when busy remains unconfirmed.
                        await self._dispose_locked(conn)
                        return
        finally:
            conn.watch_pending = False

    def binding_invalidated(self, connection_id: str, reason: str):
        conn = self.connections.get(connection_id)
        if conn is None or conn.closing or self.closing:
            return
        # Set this before waiting for the connection lock. Already queued calls
        # must not dispatch after the user requested disconnect in Rhino.
        conn.closing = True
        conn.state = "disconnecting"
        conn.reason = reason
        self.spawn(self._dispose(conn))

    def spawn(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.background.add(task)
        def finished(t):
            self.background.discard(t)
            if not t.cancelled():
                t.exception()  # Retrieve errors even if the outer client abandoned its request.
        task.add_done_callback(finished)
        return task

    async def list_connections(self):
        targets = []
        seen = set()
        for record in self.host_reader(self.data):
            host_id = record["host_id"]
            seen.add(host_id)
            existing = self.host_connections.get(host_id)
            if existing:
                targets.append(self.connections[existing].target())
                continue
            control = None
            lease = None
            try:
                self.session_closer.reject_pending(record)
                lease = self.lease_factory(self.data, record)
                control = self.control_factory(record)
                target = await control.request("describe")
                model_path = target.get("model_path")
                if not isinstance(model_path, str) or not model_path.strip():
                    target = {"state": "unavailable", "reason": UNSAVED_DOCUMENT}
                targets.append(dict(host_id=host_id, **{
                    key: target[key] for key in ("model_path", "state", "reason") if target.get(key)
                }))
            except HostInUse as exc:
                targets.append({"host_id": host_id, "state": "in_use", "reason": str(exc)})
            except Exception as exc:
                targets.append({"host_id": host_id, "state": "unavailable", "reason": str(exc)})
            finally:
                try:
                    if control is not None:
                        await control.close()
                finally:
                    if lease is not None:
                        lease.close()
        # Binding validity is tracked independently of the discovery advertisement.
        targets.extend(conn.target() for conn in self.connections.values() if conn.host_id not in seen)
        return {"targets": targets}

    async def start_session(self, model_path: str, request_id: str):
        if self.closing:
            raise RuntimeError("Almond external host is closing.")
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
            raise ValueError("A nonempty request_id of at most 128 characters is required.")
        attempt = self.starts.get(request_id)
        if attempt is not None:
            if os.path.normcase(attempt.model_path) != os.path.normcase(model_path):
                raise RuntimeError("This request_id already names a different model. No new Rhino was started.")
            if attempt.state == "ready":
                conn = self.connections.get(attempt.connection_id)
                if conn is None:
                    raise RuntimeError("This start's connection has ended. No new Rhino was started; list existing Rhino documents before deliberately creating another session.")
                if conn.closing or conn.state not in {"ready", "recovering", "unconfirmed"}:
                    raise RuntimeError(f"Connection is {conn.state}: {conn.reason}.")
                return conn.session()
        else:
            self.contract_check(self.catalog)
            attempt = self.starts[request_id] = StartAttempt(model_path)
        if attempt.task is None or attempt.state == "waiting":
            attempt.state = "starting"
            attempt.task = self.spawn(self._start_session(attempt, request_id))
        return await asyncio.shield(attempt.task)

    async def _start_session(self, attempt: StartAttempt, request_id: str):
        try:
            if attempt.launch is None:
                attempt.launch = self.starter_factory(attempt.model_path, self.data)
            try:
                record = await attempt.launch.discover()
            except TimeoutError as exc:
                attempt.state = "waiting"
                attempt.reason = (f"Rhino startup not confirmed for request_id={request_id}, "
                                  f"PID={attempt.launch.identity['pid']}. Reuse the same request_id to check this process; do not launch a replacement automatically. {exc}")
                raise TimeoutError(attempt.reason) from exc
            if self.closing:
                raise RuntimeError("MCP client closed during startup. Rhino remains open; list its advertisement from the next client.")
            attempt.state = "connecting"
            result = await self.connect(record["host_id"], attempt.launch.model_path)
            attempt.connection_id, attempt.state, attempt.reason = result["connection_id"], "ready", ""
            return result
        except BaseException as exc:
            if attempt.state != "waiting":
                attempt.state, attempt.reason = "failed", str(exc)
            raise

    async def connect(self, host_id: str, model_path: str):
        if self.closing:
            raise RuntimeError("Almond external host is closing.")
        self.contract_check(self.catalog)
        if host_id in self.host_connections:
            conn = self.connections[self.host_connections[host_id]]
            if os.path.normcase(conn.binding.get("model_path", "")) != os.path.normcase(model_path):
                raise RuntimeError("This connection belongs to a different model. Refresh connect_01-list_up tool.")
            # Selection permits recovery reads; invoke still gates ordinary
            # calls on ready and never clears an uncertain native operation.
            if conn.closing or conn.state not in {"ready", "recovering", "unconfirmed"}:
                raise RuntimeError(f"Connection is {conn.state}: {conn.reason}.")
            return conn.session()
        record = next((r for r in self.host_reader(self.data) if r["host_id"] == host_id), None)
        if record is None:
            raise RuntimeError("Rhino advertisement is stale. Run almondconnect in the intended saved document.")
        self.session_closer.reject_pending(record)
        connection_id = uuid4().hex
        lease = self.lease_factory(self.data, record)
        try:
            conn = Connection(connection_id, host_id, self.control_factory(record), uuid4().hex, lease=lease)
        except BaseException:
            lease.close()
            raise
        self.connections[connection_id] = conn
        self.host_connections[host_id] = connection_id
        def ensure_open():
            if self.closing or conn.closing:
                raise RuntimeError("Almond external host closed while this connection was starting.")

        async with conn.lock:
            try:
                description = await conn.control.request("describe")
                ensure_open()
                current_model = description.get("model_path")
                if not isinstance(current_model, str) or not current_model.strip():
                    raise RuntimeError(UNSAVED_DOCUMENT)
                if os.path.normcase(current_model) != os.path.normcase(model_path):
                    raise RuntimeError("Rhino's saved model changed. Refresh the connection list.")
                conn.binding = await conn.control.request(
                    "attach", model_path=model_path, document_serial=description["document_serial"],
                    pid=record["pid"], process_start_ticks=record["process_start_ticks"], session_token=conn.token)
                ensure_open()
                if (conn.binding.get("storage_protocol") != 2 or
                        not conn.binding.get("session_dir") or not conn.binding.get("ready_path")
                        or not conn.binding.get("call_root")):
                    raise RuntimeError("This Rhino plugin does not support shared storage sessions. Load the updated AlmondRhino build.")
                if self.watcher is None:
                    self.watcher = self.watcher_factory(self.binding_changed)
                await self.watcher.add(connection_id, conn.binding)
                ensure_open()
                await self._binding_status(conn)
                ensure_open()
                await asyncio.to_thread(self.recovery_store.remember, conn.binding, connection_id=connection_id)
                ensure_open()
                conn.worker = self.worker_factory(conn.binding, connection_id, self.catalog)
                await conn.worker.start()
                ensure_open()
                state = await conn.worker.state()
                ensure_open()
                if state.get("pending") or state.get("uncertain"):
                    raise RuntimeError("Worker did not start in a clean state.")
                await conn.control.request("worker", session_token=conn.token, pid=state["pid"],
                                           process_start_ticks=state["process_start_ticks"])
                ensure_open()
                conn.state = "ready"
                return conn.session()
            except BaseException:
                await self._dispose_locked(conn)
                raise

    async def invoke(self, conn: Connection, name: str, arguments: dict, invocation: Invocation):
        # The shared runtime remains the admission gate implementation.
        sys.path.insert(0, str(ENGINE))
        return await self.invocations.invoke(conn, name, arguments, invocation)

    async def _dispose(self, conn: Connection):
        conn.closing = True
        async with conn.lock:
            return await self._dispose_locked(conn)

    async def _dispose_closed_rhino(self, conn: Connection):
        """Called only after the close guard and exact process-exit evidence.

        Keep the host lease until worker EOF is complete. A dead process has
        released its OS/native leases; sending detach to a new PID is forbidden.
        """
        if conn.cleanup is not None and conn.cleanup.get("rhino_closed"):
            return
        conn.closing, conn.state = True, "closing"
        if self.watcher is not None:
            self.watcher.remove(conn.connection_id)
        if conn.worker is not None:
            await conn.worker.close()
        await conn.control.close()
        if conn.lease is not None:
            conn.lease.close()
            conn.lease = None
        self.connections.pop(conn.connection_id, None)
        if self.host_connections.get(conn.host_id) == conn.connection_id:
            self.host_connections.pop(conn.host_id, None)
        conn.cleanup = dict(connection_id=conn.connection_id, worker_closed=True,
                            rhino_closed=True, released=True, reason="",
                            pid=conn.binding.get("pid"), model_path=conn.binding.get("model_path"))

    async def _dispose_locked(self, conn: Connection):
        if conn.cleanup is not None:
            return conn.cleanup
        conn.closing = True
        conn.state = "closing"
        if self.watcher is not None:
            self.watcher.remove(conn.connection_id)
        worker_closed = conn.worker is None
        released = False
        errors = []
        try:
            if conn.worker is not None:
                try:
                    await conn.worker.close()
                    worker_closed = True
                except Exception as exc:
                    errors.append("Worker shutdown: " + str(exc))
            try:
                response = await conn.control.request("detach", session_token=conn.token)
                released = response.get("detached") is True
            except Exception as exc:
                errors.append(str(exc))
        finally:
            try:
                await conn.control.close()
            except Exception as exc:
                errors.append("Control shutdown: " + str(exc))
            finally:
                self.connections.pop(conn.connection_id, None)
                if self.host_connections.get(conn.host_id) == conn.connection_id:
                    self.host_connections.pop(conn.host_id, None)
                if conn.lease is not None:
                    conn.lease.close()
                    conn.lease = None
        conn.cleanup = {"connection_id": conn.connection_id, "worker_closed": worker_closed,
                        "rhino_closed": False, "released": released, "reason": "; ".join(errors),
                        "pid": conn.binding.get("pid"), "model_path": conn.binding.get("model_path")}
        return conn.cleanup

    async def disconnect(self, connection_id: str | None):
        conn = self.connections.get(connection_id)
        if conn is None:
            raise RuntimeError(UNKNOWN_CONNECTION)
        self.session_closer.reject_pending(conn.binding)
        if conn.lock.locked() or (conn.in_flight and conn.state == "ready"):
            raise RuntimeError("A call is still running. Wait for its result before disconnecting.")
        result = await self._dispose(conn)
        if not result["released"]:
            raise RuntimeError("Almond worker closed; Rhino is retaining ownership until native work drains. "
                               "Check the document and Almond connection status before reconnecting. " + result["reason"])
        reply = {"released": True}
        if result["reason"]:
            reply["reason"] = result["reason"]
        return reply

    async def call(self, name: str, arguments: dict) -> types.CallToolResult:
        conn = None
        invocation = None
        try:
            connection_id = None
            if name not in UNBOUND_TOOLS:
                arguments = dict(arguments)
                connection_id = arguments.pop("connection_id", None)
                if connection_id is None or connection_id == "":
                    raise ValueError(MISSING_CONNECTION)
                if not isinstance(connection_id, str) or not re.fullmatch(r"[0-9a-f]{32}", connection_id):
                    raise ValueError("connection_id 형식이 올바르지 않습니다")
            elif "connection_id" in arguments:
                raise ValueError(f"{name} does not accept a connection_id.")
            if name == "connect_01-list_up":
                return json_result(await self.list_connections(), name)
            if name == "connect_02-session":
                return json_result(await asyncio.shield(self.spawn(self.connect(**arguments))), name)
            if name == "connect_03-start_session":
                return json_result(await self.start_session(**arguments), name)
            if name == "connect_05-close_session":
                close = self.session_closer.run(self, connection_id, **arguments)
                return json_result(await asyncio.shield(self.spawn(close)), name)
            if name == "connect_04-disconnect":
                if arguments:
                    raise ValueError("connect_04-disconnect tool takes no arguments.")
                return json_result(await asyncio.shield(self.spawn(self.disconnect(connection_id))), name)
            if name not in self.worker_tool_names:
                raise RuntimeError("Unknown Almond tool.")
            if name == "script_03-get_execution" and arguments.get("request_id"):
                binding = await asyncio.to_thread(self.recovery_store.find_binding, arguments["request_id"],
                                                  connection_id=connection_id)
                conn = next((c for c in self.connections.values() if c.binding == binding), None)
                if conn is None:
                    value = await asyncio.to_thread(self._execution_reader, binding, arguments)
                    value.update(connection_state="unbound", requires_reconnect=True, recovery_only=True)
                    return json_result(value, name)
            else:
                conn = self.connections.get(connection_id)
            if conn is None:
                raise RuntimeError(UNKNOWN_CONNECTION)
            invocation = Invocation()
            return await asyncio.shield(self.spawn(self.invoke(conn, name, dict(arguments), invocation)))
        except asyncio.CancelledError:
            if invocation is not None:
                invocation.abandoned = True
            if (conn is not None and invocation is not None and invocation.worker_dispatched
                    and not conn.closing and conn.state == "ready"):
                # The shielded operation may finish. Its completion may clear busy,
                # but a lost caller result does not authorize an automatic retry.
                conn.state, conn.reason = "unconfirmed", "Caller stopped waiting; inspect the operation's outcome."
            raise
        except Exception as exc:
            if name == "drawing_06-generate_plan_section" and invocation is not None and invocation.worker_dispatched:
                response = json_result(unconfirmed_plan_section(arguments.get("clipping_ids"), str(exc)), name,
                                       wrapped=True)
                response.is_error = True
                return response
            return error_result(str(exc))

    async def close(self):
        self.closing = True
        # Discovery may take minutes. Cancel only its wait; never kill the
        # launched Rhino, and let in-progress attach use normal cleanup.
        for attempt in self.starts.values():
            if attempt.state == "starting" and attempt.task is not None:
                attempt.task.cancel()
        current = list(self.connections.values())
        for conn in current:
            conn.closing = True
            if conn.worker is not None:
                conn.worker.request_stop()
        if self.watcher is not None:
            await self.watcher.close()
        await asyncio.gather(*(self._dispose(c) for c in current), return_exceptions=True)
        if self.background:
            await asyncio.gather(*list(self.background), return_exceptions=True)


class SessionAdapter:
    """MCP registration owns a catalog only, until an explicit management call."""

    def __init__(self, catalog, data=ROOT / "data", *, broker_factory=Broker):
        self.catalog, self.data, self.broker_factory = catalog, data, broker_factory
        self.tools = exposed_tools(catalog, mode_ids=common_mode_ids(read_hosts(data)))
        self.local_inputs = {
            tool.name: Draft202012Validator(tool.input_schema) for tool in self.tools
            if tool.name in (POLICY_TOOL, GET_EXECUTION) or tool.name in MANAGEMENT_TOOLS
        }
        self.broker = None

    async def call(self, name, arguments):
        if name not in UNBOUND_TOOLS and not arguments.get("connection_id"):
            return error_result(MISSING_CONNECTION)
        validator = self.local_inputs.get(name)
        if validator is not None:
            failure = next(validator.iter_errors(arguments), None)
            if failure is not None:
                return error_result(f"{failure.json_path}: {failure.message}")
        if name == POLICY_TOOL:
            try:
                return json_result(read_policy(**arguments), name)
            except (TypeError, ValueError, RuntimeError) as exc:
                return error_result(str(exc))
        if self.broker is None:
            if name not in {"connect_01-list_up", "connect_02-session", "connect_03-start_session", "connect_05-close_session", "script_03-get_execution"}:
                return error_result(UNKNOWN_CONNECTION)
            self.broker = self.broker_factory(self.catalog, data=self.data)
        return await self.broker.call(name, arguments)

    async def close(self):
        if self.broker is not None:
            await self.broker.close()


async def serve(catalog: dict, data: Path = ROOT / "data"):
    broker = SessionAdapter(catalog, data=data)
    schemas = {t.name: t.input_schema for t in broker.tools}

    async def on_list_tools(ctx, params):
        return types.ListToolsResult(tools=broker.tools)

    async def on_call_tool(ctx, params):
        return await broker.call(params.name, params.arguments or {})

    # Send the shared introduction before any tool call. Keep it in instructions
    # too for clients that do not display serverInfo.description.
    server = Server("beyond", version=VERSION, description=DESCRIPTION,
                    instructions=DESCRIPTION + "\n\n" + startup_instructions(),
                    get_tool_input_schema=schemas.get,
                    on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    try:
        async with stdio_server() as (reader, writer):
            await server.run(reader, writer, server.create_initialization_options())
    finally:
        await broker.close()


def main(data: Path = ROOT / "data"):
    catalog = load_catalog()
    asyncio.run(serve(catalog, data=data))


def run():
    try:
        from almond_mcp.runtime.desktop_runtime import ensure_desktop_runtime
        ensure_desktop_runtime()
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[beyond MCP] {exc}", file=sys.stderr)
        raise SystemExit(1)
