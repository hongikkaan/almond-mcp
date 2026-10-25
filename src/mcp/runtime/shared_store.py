"""Coordinate shared SQLite work and per-call files through public MCP middleware.

The reviewed Rhino-only tools may run in parallel in different workers. Operations that can touch SQLite, including
initial indexing, hold one OS file lease through the connection close/checkpoint.
"""
from __future__ import annotations

import asyncio
from contextlib import closing, nullcontext
from contextvars import ContextVar
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

import anyio
from fastmcp.server.middleware import Middleware

from project import (ExclusiveFile, LOCK_WAIT_SECONDS, serial_gate, read_binding,
                     read_json, verify_process, write_json)
from native_request import RequestBatch


# These reviewed tools use the native bridge and files, without opening SQLite.
# All other upstream tools conservatively share the DB gate.
NATIVE_ONLY_TOOLS = frozenset({
    "execute_rhino_script", "capture_conditioning_pass",
    "get_rhino_context", "get_rhino_viewport_image", "get_rhino_probe",
})
BINDING_TOOLS = frozenset({"project_info", "worker_state"})


class StoreGate:
    """A cancellable asynchronous wait, or a bounded startup wait, for an OS lease."""
    def __init__(self, storage: str | Path, timeout: float = LOCK_WAIT_SECONDS):
        self.path = Path(storage) / ".sessions" / "store.lock"
        self.timeout = timeout
        self.lease = None

    def _try_acquire(self) -> bool:
        try:
            self.lease = ExclusiveFile(self.path)
            return True
        except OSError as exc:
            if exc.errno not in (32, 33):
                raise
            return False

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        while not self._try_acquire():
            if time.monotonic() >= deadline:
                raise TimeoutError("Another connection is using the shared DB. No operation was started.")
            time.sleep(0.05)
        return self

    async def __aenter__(self):
        deadline = time.monotonic() + self.timeout
        while not self._try_acquire():
            if time.monotonic() >= deadline:
                raise TimeoutError("Another connection is using the shared DB. No operation was started.")
            await asyncio.sleep(0.05)
        return self

    def close(self):
        if self.lease is not None:
            self.lease.close()
            self.lease = None

    def __exit__(self, *args):
        self.close()

    async def __aexit__(self, *args):
        self.close()


def validate_shared_ids(name: str, arguments: dict, database: str | Path) -> None:
    """Keep a supplied global ledger ID from silently modifying another scene.

    Call only while holding StoreGate. The original schema and transaction body
    remain unchanged; the read-only connection is closed before the tool starts.
    """
    fields = {
        "upsert_design_room": ("rooms", "room_id"),
        "register_scene_instance": ("instances", "instance_id"),
    }
    if name not in fields:
        return
    table, field = fields[name]
    identifier, scene = arguments.get(field), arguments.get("scene_id")
    if not isinstance(identifier, str) or not identifier.strip() or not isinstance(scene, str):
        return  # Preserve the upstream argument validator for all other inputs.
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=15)) as connection:
        row = connection.execute(f"SELECT scene_id FROM {table} WHERE {field} = ?",
                                 (identifier.strip(),)).fetchone()
    if row and row[0] != scene:
        raise ValueError(f"{field} {identifier.strip()!r} already belongs to another scene. "
                         "Use its existing scene or a new ID; no record was changed.")


def output_arguments(name: str, arguments: dict, operation_dir: Path) -> dict:
    """Fill reviewed public output arguments; explicit output paths retain priority."""
    arguments = dict(arguments)
    fields = {
        "export_structural_report": ("path", operation_dir / "reports" / "structural-validation.md"),
        "export_asset_contract": ("output_dir", operation_dir / "exchange"),
        "get_blender_helper_script": ("output_dir", operation_dir / "exchange"),
        "capture_conditioning_pass": ("out_dir", operation_dir / "conditioning"),
    }
    if name not in fields:
        return arguments
    if name == "get_blender_helper_script" and str(arguments.get("action", "")).strip().lower() != "export":
        return arguments
    field, target = fields[name]
    # Conditioning's existing required argument remains required in the schema.
    if name == "capture_conditioning_pass" and field not in arguments:
        return arguments
    if arguments.get(field) == "" or field not in arguments:
        if name == "export_structural_report":
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            target.mkdir(parents=True, exist_ok=True)
        arguments[field] = str(target)
    return arguments


class ProjectRuntime(Middleware):
    """Own one logical operation at a time for this immutable connection generation."""
    def __init__(self, args, binding: dict, locations: dict, *, check_owner=True,
                 queue_timeout: float = LOCK_WAIT_SECONDS):
        self.args = args
        self.binding = dict(binding)
        self.locations = dict(locations)
        self.check_owner = check_owner
        self.queue_timeout = queue_timeout
        self.batch = None
        self.scope = ContextVar("almond_operation_" + args.token, default=None)
        self.serial = asyncio.Lock()
        self.worker = read_json(Path(locations["session_dir"]) / "worker.json")
        self.last = {"pending": False, "uncertain": False, "operation_id": None}
        self.unconfirmed = False

    def validate(self):
        current, _ = read_binding(self.args.session, self.args.token)
        if current != self.binding:
            raise RuntimeError("This connection changed. Reconnect before another operation.")
        if self.check_owner:
            verify_process(current)
        if self.unconfirmed:
            raise RuntimeError("The previous native result is unconfirmed. Disconnect and inspect that Rhino before reconnecting.")

    def send(self, sender, payload_bytes: bytes, *positional, **keywords) -> str:
        self.validate()
        batch = self.scope.get()
        if batch is None:
            raise RuntimeError("No active operation; no native request was sent.")
        return batch.call(sender, payload_bytes, *positional, **keywords)

    async def _completion(self, operation_id: str, batch):
        state = batch.finish()
        minimum_sequence = state["native_sequence"]
        receipt_path = Path(self.locations["session_dir"]) / "native.json"
        deadline = time.monotonic() + 2.0
        receipt = None
        while True:
            try:
                candidate = read_json(receipt_path)
                if (candidate.get("schema") == "almond-native"
                        and candidate.get("token") == self.args.token
                        and candidate.get("operation_id") == operation_id
                        and candidate.get("sequence", 0) >= minimum_sequence):
                    receipt = candidate
            except (FileNotFoundError, OSError, ValueError):
                pass
            if receipt and receipt.get("pending") == 0:
                break
            if minimum_sequence == 0 or time.monotonic() >= deadline:
                break
            await asyncio.sleep(0.02)
        pending = bool(state["pending"] or (receipt and receipt.get("pending", 0)))
        # Every forwarded frame must have its own matching native acknowledgement.
        # A prior frame's idle receipt cannot certify a delayed later frame.
        uncertain = (state["uncertain"] or pending or (minimum_sequence > 0 and not receipt)
                     or bool(receipt and receipt.get("completion_status") not in ("completed", "rejected", "failed")))
        return {"pending": pending, "uncertain": uncertain, "operation_id": operation_id,
                "native": receipt, "transport": state}

    def completion(self) -> dict:
        value = dict(self.last)
        if self.batch is not None and value.get("uncertain"):
            state = self.batch.snapshot()
            pending = bool(value.get("pending") or state["pending"])
            try:
                native = read_json(Path(self.locations["session_dir"]) / "native.json")
                if (native.get("schema") == "almond-native" and native.get("token") == self.args.token
                        and native.get("operation_id") == value.get("operation_id")
                        and native.get("sequence", 0) >= state["native_sequence"]):
                    unacknowledged = any(not item["acknowledged"] for item in state["requests"])
                    # Losing a socket cannot certify a still-queued Rhino
                    # command. Missing acknowledgements require native stop/drain.
                    native_pending = bool(native.get("pending")) or (
                        unacknowledged and native.get("phase") not in ("stopped", "faulted"))
                    pending = bool(state["pending"] or native_pending)
                    value["native"] = native
            except (OSError, ValueError, TypeError):
                pass  # Preserve the last known pending state when it cannot be refreshed.
            value.update(pending=pending, transport=state)
        return value

    @staticmethod
    async def _settle(coroutine):
        """Finish owned work despite repeated raw Task.cancel; report caller cancellation."""
        work = asyncio.create_task(coroutine)
        cancellation = None
        while not work.done():
            try:
                await asyncio.shield(work)
            except asyncio.CancelledError as exc:
                if work.cancelled():
                    raise
                cancellation = exc
            except BaseException:
                break
        try:
            result = work.result()
        except BaseException as exc:
            if cancellation is not None:
                raise cancellation from exc
            raise
        return result, cancellation

    async def _run_to_completion(self, context, call_next):
        result, cancellation = await self._settle(call_next(context))
        if cancellation is not None:
            raise cancellation
        return result

    async def _finish_operation(self, operation_id, batch, operation_path, operation):
        self.last = await self._completion(operation_id, batch)
        self.unconfirmed = self.last["uncertain"]
        operation["state"] = "unconfirmed" if self.unconfirmed else "completed"
        write_json(operation_path, operation)

    async def on_call_tool(self, context, call_next):
        name = context.message.name
        if name in BINDING_TOOLS:
            return await call_next(context)
        async with serial_gate(self.serial, self.queue_timeout):
            self.validate()
            gate = (nullcontext() if name in NATIVE_ONLY_TOOLS
                    else StoreGate(self.locations["storage"]))
            # Waiting has no side effects and remains cancellable.
            async with gate:
                self.validate()
                await anyio.lowlevel.checkpoint()
                validate_shared_ids(name, context.message.arguments or {}, self.locations["state_db"])
                operation_id = uuid.uuid4().hex
                operation_dir = Path(self.locations["call_root"]) / operation_id
                operation_dir.mkdir(parents=True, exist_ok=False)
                args = output_arguments(name, context.message.arguments or {}, operation_dir)
                message = context.message.model_copy(update={"arguments": args})
                operation_path = Path(self.locations["session_dir"]) / "operation.json"
                operation = {
                    "schema": "almond-operation", "storage_protocol": 2,
                    "token": self.args.token, "operation_id": operation_id,
                    "worker_pid": self.worker["pid"],
                    "worker_start_ticks": self.worker["process_start_ticks"],
                    "temp": str(operation_dir), "state": "running",
                }
                write_json(operation_path, operation)
                self.last = {"pending": True, "uncertain": False, "operation_id": operation_id}
                previous = {key: os.environ.get(key) for key in ("TEMP", "TMP", "TMPDIR")}
                old_tempdir = tempfile.tempdir
                batch = RequestBatch(self.args.token, operation_id)
                self.batch = batch
                scope_token = self.scope.set(batch)
                # A cancelled caller must not release SQLite/TEMP ownership while
                # an offloaded original function is still running.
                with anyio.CancelScope(shield=True):
                    try:
                        for key in previous:
                            os.environ[key] = str(operation_dir)
                        tempfile.tempdir = str(operation_dir)
                        return await self._run_to_completion(context.copy(message=message), call_next)
                    finally:
                        cleanup_cancellation = None
                        try:
                            _, cleanup_cancellation = await self._settle(
                                self._finish_operation(operation_id, batch, operation_path, operation))
                        except BaseException:
                            self.unconfirmed = True
                            self.last = {"pending": True, "uncertain": True, "operation_id": operation_id}
                            batch.seal()
                            raise
                        finally:
                            self.scope.reset(scope_token)
                            tempfile.tempdir = old_tempdir
                            for key, value in previous.items():
                                if value is None:
                                    os.environ.pop(key, None)
                                else:
                                    os.environ[key] = value
                        if cleanup_cancellation is not None:
                            raise cleanup_cancellation
