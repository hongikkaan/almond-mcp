"""One COS stdio entry; independent Almond workers for connected Rhino documents."""
from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import json
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

from runtime import (ENGINE, PREFIX, ROOT, VERSION, WORKER_STATE_TOOL, check_contract,
                     load_catalog, validate_worker_tools)
from winpipe import PipeControl, read_hosts
from binding_watch import BindingWatcher

GUIDANCE = (
    "Use the explicit connection_id from almond_cos_connect for every call. "
    "Call almond_cos_project_info before the first Rhino action and use its artifact_dir "
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


def public_name(name: str) -> str:
    return PREFIX + ("project_info" if name == "almond_project_info" else name)


def exposed_tools(catalog: dict) -> tuple[list[types.Tool], dict[str, str]]:
    tools, mapping = [], {}
    for original in catalog["tools"]:
        tool = json.loads(json.dumps(original))
        name = original["name"]
        tool["name"] = public_name(name)
        description = original.get("description", "")
        if name == "almond_project_info":
            description = "Read this connection's saved model, database and artifact_dir. This metadata does not execute Rhino code."
        tool["description"] = description + "\n\n" + GUIDANCE
        schema = tool["inputSchema"]
        if schema.get("type") != "object" or "connection_id" in schema.get("properties", {}):
            raise RuntimeError(f"Unsupported routing schema: {name}")
        schema.setdefault("properties", {})["connection_id"] = {
            "type": "string", "minLength": 1,
            "description": "Exact live connection ID returned by almond_cos_connect."
        }
        schema["required"] = [*schema.get("required", []), "connection_id"]
        tools.append(types.Tool.model_validate(tool))
        mapping[tool["name"]] = name
    management = [
        ("list_connections", "List available Rhino documents and existing COS connections. Run AlmondCOS in a saved ordinary Rhino to advertise it.",
         {}, []),
        ("connect", "Connect one advertised Rhino/document. Uses an independent A-J slot and session; models in one folder share the existing database and artifact root.",
         {"host_id": {"type": "string"}, "model_path": {"type": "string", "description": "Exact saved model path shown in the listing."}},
         ["host_id", "model_path"]),
        ("disconnect", "Disconnect this COS connection after its calls complete. Never closes or saves Rhino. An unconfirmed native operation can retain its Rhino-side locks.",
         {"connection_id": {"type": "string"}}, ["connection_id"]),
    ]
    for short, description, properties, required in management:
        name = PREFIX + short
        if name in mapping:
            raise RuntimeError("Management tool name collides with Almond.")
        tools.append(types.Tool(name=name, description=description,
                                input_schema={"type": "object", "properties": properties,
                                              "required": required, "additionalProperties": False}))
    return tools, mapping


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
            command=str(ENGINE / ".venv/Scripts/python.exe"),
            args=["-B", "-u", str(ROOT / "cos_worker.py"), "--session",
                  self.binding["ready_path"], "--port", str(self.binding["port"]),
                  "--connection-id", self.connection_id],
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", ALMONDCOS_SESSION_TOKEN=self.binding["token"]),
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

    def public(self):
        b = self.binding
        return dict(connection_id=self.connection_id, host_id=self.host_id, state=self.state,
                    reason=self.reason, model_path=b.get("model_path"), slot=b.get("label"),
                    pid=b.get("pid"), artifact_dir=b.get("call_root"), in_flight=self.in_flight)


class Broker:
    def __init__(self, catalog: dict, data: Path = ROOT / "data", *,
                 control_factory=PipeControl, worker_factory=Worker, host_reader=read_hosts,
                 contract_check=check_contract, call_timeout: float = 300,
                 watcher_factory=BindingWatcher):
        self.catalog, self.data = catalog, data
        self.control_factory, self.worker_factory = control_factory, worker_factory
        self.host_reader, self.contract_check = host_reader, contract_check
        self.call_timeout = call_timeout
        self.tools, self.mapping = exposed_tools(catalog)
        self.connections: dict[str, Connection] = {}
        self.host_connections: dict[str, str] = {}
        self.background: set[asyncio.Task] = set()
        self.closing = False
        self.watcher_factory = watcher_factory
        self.watcher = None

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
            control = self.control_factory(record)
            try:
                target = await control.request("describe")
                targets.append(dict(target, host_id=record["host_id"]))
            except Exception as exc:
                targets.append({"host_id": record["host_id"], "pid": record["pid"],
                                "state": "unavailable", "reason": str(exc)})
            finally:
                await control.close()
        return {"targets": targets, "connections": [c.public() for c in self.connections.values()]}

    async def connect(self, host_id: str, model_path: str):
        if self.closing:
            raise RuntimeError("COS host is closing.")
        self.contract_check(self.catalog)
        if host_id in self.host_connections:
            raise RuntimeError(f"Rhino already has COS connection {self.host_connections[host_id]}.")
        record = next((r for r in self.host_reader(self.data) if r["host_id"] == host_id), None)
        if record is None:
            raise RuntimeError("Rhino advertisement is stale. Run AlmondCOS in the intended saved document.")
        connection_id = uuid4().hex
        conn = Connection(connection_id, host_id, self.control_factory(record), uuid4().hex)
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
        async with conn.lock:
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
            if name == PREFIX + "list_connections":
                return json_result(await self.list_connections())
            if name == PREFIX + "connect":
                return json_result(await asyncio.shield(self.spawn(self.connect(**arguments))))
            if name == PREFIX + "disconnect":
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


async def serve(catalog: dict, data: Path = ROOT / "data"):
    broker = Broker(catalog, data=data)
    schemas = {t.name: t.input_schema for t in broker.tools}

    async def on_list_tools(ctx, params):
        return types.ListToolsResult(tools=broker.tools)

    async def on_call_tool(ctx, params):
        return await broker.call(params.name, params.arguments or {})

    # The worker's initialize instructions do not reach this host's client.
    server = Server("AlmondCOS", version=VERSION, instructions=(GUIDANCE + " " +
                    "Before inspecting or editing existing geometry, call almond_cos_get_rhino_context. "
                    "Use almond_cos_get_rhino_viewport_image when the current view matters. "
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
    check_contract(catalog)
    data.mkdir(exist_ok=True)
    sys.path.insert(0, str(ENGINE))
    from project import ExclusiveFile
    with ExclusiveFile(data / "host.lock"):
        asyncio.run(serve(catalog, data=data))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"[AlmondCOS] {exc}", file=sys.stderr)
        raise SystemExit(1)
