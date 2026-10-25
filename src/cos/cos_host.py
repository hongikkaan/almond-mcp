"""Lazy per-client stdio adapters; independent workers for explicitly bound Rhino."""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
import json
import hashlib
import os
from pathlib import Path
import sys
from uuid import uuid4

sys.dont_write_bytecode = True
import mcp_types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server

from runtime import (ENGINE, PYTHON, ROOT, VERSION, WORKER_STATE_TOOL, check_contract, catalog_identity,
                     load_catalog, validate_worker_tools)
from winpipe import PipeControl, read_hosts
from binding_watch import BindingWatcher

GUIDANCE = (
    "Initialization only advertises tools; it does not start Rhino or a modeling worker. "
    "To open a separate Rhino for a saved .3dm, explicitly call start_session "
    "with a unique request_id. Reuse that request_id to check a delayed start; never "
    "automatically repeat it with a new ID. Otherwise list and connect an advertised Rhino. "
    "Use the explicit connection_id from connect for every call. "
    "Call project_info before the first Rhino action and use its artifact_dir "
    "as an explicit absolute path for task files in Rhino C# and subsequent file reads. "
    "Rhino TEMP may differ. Document changes require disconnect/reconnect. "
    "A timeout is not a rollback; inspect Rhino before repeating a mutation."
)


def json_result(value: dict) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(value, ensure_ascii=False))],
                                structured_content=value)


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


def exposed_tools(catalog: dict) -> tuple[list[types.Tool], dict[str, str]]:
    tools, mapping = [], {}
    for original in catalog["tools"]:
        tool = json.loads(json.dumps(original))
        name = original["name"]
        description = original.get("description", "")
        if name == "project_info":
            description = "Read this connection's saved model, database and artifact_dir. This metadata does not execute Rhino code."
        tool["description"] = description + "\n\n" + GUIDANCE
        schema = tool["inputSchema"]
        if schema.get("type") != "object" or "connection_id" in schema.get("properties", {}):
            raise RuntimeError(f"Unsupported routing schema: {name}")
        schema.setdefault("properties", {})["connection_id"] = {
            "type": "string", "minLength": 1,
            "description": "Exact live connection ID returned by connect."
        }
        schema["required"] = [*schema.get("required", []), "connection_id"]
        tools.append(types.Tool.model_validate(tool))
        mapping[tool["name"]] = name
    management = [
        ("list_connections", "List available Rhino documents and this client's connections. Run almondconnect in a saved ordinary Rhino to advertise it to Codex or CoS.",
         {}, []),
        ("connect", "Connect one advertised Rhino/document. Uses an independent A-J slot and session; models in one folder share the existing database and artifact root.",
         {"host_id": {"type": "string"}, "model_path": {"type": "string", "description": "Exact saved model path shown in the listing."}},
         ["host_id", "model_path"]),
        ("start_session", "Explicitly open a saved .3dm in a new visible Rhino, advertise it with almondconnect, and connect its own A-J slot/worker. Does not save or close Rhino. Reuse the same request_id after a startup timeout; a new ID deliberately opens another Rhino.",
         {"model_path": {"type": "string", "description": "Absolute path of an existing saved local .3dm; opened without saving."},
          "request_id": {"type": "string", "minLength": 1, "maxLength": 128,
                         "description": "Unique ID for this deliberate start; keep it unchanged when checking the same attempt."}},
         ["model_path", "request_id"]),
        ("disconnect", "Disconnect this client's connection after its calls complete. Never closes or saves Rhino. An unconfirmed native operation can retain its Rhino-side locks.",
         {"connection_id": {"type": "string"}}, ["connection_id"]),
    ]
    for name, description, properties, required in management:
        if name in mapping:
            raise RuntimeError("Management tool name collides with Almond.")
        tools.append(types.Tool(name=name, description=description,
                                input_schema={"type": "object", "properties": properties,
                                              "required": required, "additionalProperties": False}))
    return tools, mapping


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
            raise HostInUse("This Rhino is owned by another Almond client. Keep that connection, or explicitly start a separate Rhino with start_session.") from exc
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
        self.owner = asyncio.create_task(self._own(), name="AlmondCOS worker")
        await asyncio.shield(self.ready)

    async def _own(self):
        params = StdioServerParameters(
            command=str(PYTHON),
            args=["-B", "-u", str(ROOT / "cos_worker.py"), "--session",
                  self.binding["ready_path"], "--port", str(self.binding["port"]),
                  "--connection-id", self.connection_id],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", ALMONDCOS_SESSION_TOKEN=self.binding["token"],
                     ALMONDCOS_CATALOG_ID=catalog_identity(self.catalog)),
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

    async def call(self, name: str, arguments: dict):
        if self.session is None:
            raise RuntimeError("Almond worker is disconnected.")
        return await self.session.call_tool(name, arguments)

    async def state(self):
        return result_dict(await asyncio.wait_for(self.call(WORKER_STATE_TOOL, {}), 10))

    async def close(self):
        self.stop.set()
        if self.owner is not None:
            await asyncio.shield(self.owner)

    def request_stop(self):
        self.stop.set()


@dataclass
class Invocation:
    abandoned: bool = False
    started: bool = False


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

    def public(self):
        b = self.binding
        return dict(connection_id=self.connection_id, host_id=self.host_id, state=self.state,
                    reason=self.reason, model_path=b.get("model_path"), slot=b.get("label"),
                    pid=b.get("pid"), artifact_dir=b.get("call_root"), in_flight=self.in_flight)


@dataclass
class StartAttempt:
    model_path: str
    launch: object = None
    task: asyncio.Task | None = None
    state: str = "starting"
    connection_id: str | None = None
    reason: str = ""

    def public(self, request_id):
        return dict(request_id=request_id, model_path=self.model_path, state=self.state,
                    connection_id=self.connection_id, reason=self.reason,
                    **(self.launch.identity if self.launch is not None else {}))


class Broker:
    def __init__(self, catalog: dict, data: Path = ROOT / "data", *,
                 control_factory=PipeControl, worker_factory=Worker, host_reader=read_hosts,
                 contract_check=check_contract, call_timeout: float = 300,
                 watcher_factory=BindingWatcher, lease_factory=host_lease,
                 starter_factory=start_rhino, queue_timeout: float = 10.0):
        self.catalog, self.data = catalog, data
        self.control_factory, self.worker_factory = control_factory, worker_factory
        self.host_reader, self.contract_check = host_reader, contract_check
        self.call_timeout = call_timeout
        self.queue_timeout = queue_timeout
        self.tools, self.mapping = exposed_tools(catalog)
        self.connections: dict[str, Connection] = {}
        self.host_connections: dict[str, str] = {}
        self.background: set[asyncio.Task] = set()
        self.closing = False
        self.watcher_factory = watcher_factory
        self.watcher = None
        self.lease_factory, self.starter_factory = lease_factory, starter_factory
        self.starts: dict[str, StartAttempt] = {}

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
            raise RuntimeError(str(reason or "Rhino disconnected this COS binding."))

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
        for record in self.host_reader(self.data):
            existing = self.host_connections.get(record["host_id"])
            if existing:
                targets.append(self.connections[existing].public())
                continue
            control = None
            lease = None
            try:
                lease = self.lease_factory(self.data, record)
                control = self.control_factory(record)
                target = await control.request("describe")
                targets.append(dict(target, host_id=record["host_id"]))
            except HostInUse as exc:
                targets.append({"host_id": record["host_id"], "pid": record["pid"],
                                "state": "in_use", "reason": str(exc)})
            except Exception as exc:
                targets.append({"host_id": record["host_id"], "pid": record["pid"],
                                "state": "unavailable", "reason": str(exc)})
            finally:
                try:
                    if control is not None:
                        await control.close()
                finally:
                    if lease is not None:
                        lease.close()
        return {"targets": targets, "connections": [c.public() for c in self.connections.values()],
                "starts": [attempt.public(key) for key, attempt in self.starts.items()]}

    async def start_session(self, model_path: str, request_id: str):
        if self.closing:
            raise RuntimeError("COS host is closing.")
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
                return dict(conn.public(), request_id=request_id)
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
            return dict(result, request_id=request_id)
        except BaseException as exc:
            if attempt.state != "waiting":
                attempt.state, attempt.reason = "failed", str(exc)
            raise

    async def connect(self, host_id: str, model_path: str):
        if self.closing:
            raise RuntimeError("COS host is closing.")
        self.contract_check(self.catalog)
        if host_id in self.host_connections:
            raise RuntimeError(f"Rhino already has COS connection {self.host_connections[host_id]}.")
        record = next((r for r in self.host_reader(self.data) if r["host_id"] == host_id), None)
        if record is None:
            raise RuntimeError("Rhino advertisement is stale. Run almondconnect in the intended saved document.")
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
                raise RuntimeError("COS host closed while this connection was starting.")

        async with conn.lock:
            try:
                description = await conn.control.request("describe")
                ensure_open()
                if os.path.normcase(description.get("model_path", "")) != os.path.normcase(model_path):
                    raise RuntimeError("Rhino's saved model changed. Refresh the connection list.")
                conn.binding = await conn.control.request(
                    "attach", model_path=model_path, document_serial=description["document_serial"],
                    pid=record["pid"], process_start_ticks=record["process_start_ticks"], session_token=conn.token)
                ensure_open()
                if (conn.binding.get("storage_protocol") != 2 or
                        not conn.binding.get("session_dir") or not conn.binding.get("ready_path")
                        or not conn.binding.get("call_root")):
                    raise RuntimeError("This Rhino plugin does not support shared storage sessions. Load the updated AlmondCOS build.")
                if self.watcher is None:
                    self.watcher = self.watcher_factory(self.binding_changed)
                await self.watcher.add(connection_id, conn.binding)
                ensure_open()
                await self._binding_status(conn)
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
                return conn.public()
            except BaseException:
                await self._dispose_locked(conn)
                raise

    async def _fail(self, conn: Connection, reason: str):
        conn.state, conn.reason = "unconfirmed", reason
        with suppress(Exception):
            await conn.control.request("fail", session_token=conn.token, reason=reason[:300])

    async def invoke(self, conn: Connection, name: str, arguments: dict, invocation: Invocation):
        # Runtime owns the queue-wait contract. Import it only for an active
        # call; cleanup/watch locks intentionally keep their drain semantics.
        sys.path.insert(0, str(ENGINE))
        from project import serial_gate
        async with serial_gate(conn.lock, self.queue_timeout):
            if invocation.abandoned:
                raise RuntimeError("Caller stopped while this request was queued. No Rhino request was sent.")
            if conn.closing or conn.state != "ready":
                raise RuntimeError(f"Connection is {conn.state}: {conn.reason}. Inspect Rhino before reconnecting.")
            request_id = uuid4().hex
            invocation.started = True
            conn.in_flight = True
            try:
                await conn.control.request("begin", session_token=conn.token, request_id=request_id)
                if invocation.abandoned or conn.closing or conn.state != "ready":
                    # No worker request was dispatched. Clear only this reservation.
                    await conn.control.request("end", session_token=conn.token, request_id=request_id)
                    conn.in_flight = False
                    raise RuntimeError("Caller stopped before Rhino execution began.")
                if conn.watch_again:
                    conn.watch_again = False
                    try:
                        await self._binding_status(conn)
                    except Exception:
                        # The RHP may have disconnected while begin's reply was
                        # in transit. No worker call has been dispatched yet.
                        await conn.control.request("end", session_token=conn.token, request_id=request_id)
                        conn.in_flight = False
                        raise
                result = await asyncio.wait_for(conn.worker.call(name, arguments), self.call_timeout)
                state = await conn.worker.state()
                if state.get("pending") or state.get("uncertain"):
                    raise RuntimeError("Rhino execution outcome is unconfirmed. Do not repeat the operation automatically.")
                await conn.control.request("end", session_token=conn.token, request_id=request_id)
                conn.in_flight = False
                return result
            except BaseException as exc:
                await self._fail(conn, str(exc) or "Caller canceled while Rhino might still be executing.")
                raise

    async def _dispose(self, conn: Connection):
        conn.closing = True
        async with conn.lock:
            return await self._dispose_locked(conn)

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
                        "rhino_closed": False, "released": released, "reason": "; ".join(errors)}
        return conn.cleanup

    async def disconnect(self, connection_id: str):
        conn = self.connections.get(connection_id)
        if conn is None:
            raise RuntimeError("Unknown or stale connection_id.")
        if conn.lock.locked() or (conn.in_flight and conn.state == "ready"):
            raise RuntimeError("A call is still running. Wait for its result before disconnecting.")
        result = await self._dispose(conn)
        if not result["released"]:
            raise RuntimeError("COS worker closed; Rhino is retaining ownership until native work drains. "
                               "Check the document and AlmondCOS connection status before reconnecting. " + result["reason"])
        return result

    async def call(self, name: str, arguments: dict) -> types.CallToolResult:
        conn = None
        invocation = None
        try:
            if name == "list_connections":
                return json_result(await self.list_connections())
            if name == "connect":
                return json_result(await asyncio.shield(self.spawn(self.connect(**arguments))))
            if name == "start_session":
                return json_result(await self.start_session(**arguments))
            if name == "disconnect":
                return json_result(await asyncio.shield(self.spawn(self.disconnect(**arguments))))
            if name not in self.mapping:
                raise RuntimeError("Unknown AlmondCOS tool.")
            arguments = dict(arguments)
            connection_id = arguments.pop("connection_id", None)
            conn = self.connections.get(connection_id)
            if conn is None:
                raise RuntimeError("Unknown or stale connection_id. No Rhino request was sent.")
            invocation = Invocation()
            return await asyncio.shield(self.spawn(self.invoke(conn, self.mapping[name], arguments, invocation)))
        except asyncio.CancelledError:
            if invocation is not None:
                invocation.abandoned = True
            if conn is not None and invocation is not None and invocation.started:
                # The shielded operation may finish. Its completion may clear busy,
                # but a lost caller result does not authorize an automatic retry.
                conn.state, conn.reason = "unconfirmed", "Caller stopped waiting; inspect the operation's outcome."
            raise
        except Exception as exc:
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
        self.tools, self.mapping = exposed_tools(catalog)
        self.broker = None

    async def call(self, name, arguments):
        if self.broker is None:
            if name not in {"list_connections", "connect", "start_session"}:
                return error_result("Unknown or stale connection_id. No Rhino request was sent.")
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

    # The worker's initialize instructions do not reach this host's client.
    server = Server("AlmondCOS", version=VERSION, instructions=(GUIDANCE + " " +
                    "Before inspecting or editing existing geometry, call get_rhino_context. "
                    "Use get_rhino_viewport_image when the current view matters. "
                    "Inspect relevant objects and validate proposed geometry against the task before replacing originals. "
                    "Execution success and a viewport image do not establish geometric correctness."),
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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[AlmondCOS] {exc}", file=sys.stderr)
        raise SystemExit(1)
