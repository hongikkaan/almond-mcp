"""Coordinate shared SQLite work and per-call files through public MCP middleware.

The reviewed Rhino-only tools may run in parallel in different workers. Operations that can touch SQLite, including
initial indexing, hold one OS file lease through the connection close/checkpoint.
"""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

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
from almond_mcp.managed_paths import project_path, relative_output
from storage_cleanup import remove_owned_tree

import anyio
from fastmcp.server.middleware import Middleware
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from project import (ExclusiveFile, LOCK_WAIT_SECONDS, serial_gate, read_binding,
                     read_json, verify_process, write_json)
from native_request import RequestBatch


# These reviewed tools use the native bridge and files, without opening SQLite.
# All other upstream tools conservatively share the DB gate.
NATIVE_ONLY_TOOLS = frozenset({
    "execute_rhino_script", "capture_conditioning_pass",
    "get_rhino_context", "get_rhino_viewport_image", "get_rhino_probe",
})
BINDING_TOOLS = frozenset({"worker_state"})
FILE_TOOLS = frozenset({"execute_rhino_script", "execute_project_python", "export_structural_report",
    "export_asset_contract", "get_blender_helper_script", "capture_conditioning_pass",
    "import_asset_contract", "rename_artifact_folder"})
OUTPUT_TOOLS = frozenset({"execute_project_python", "export_structural_report", "export_asset_contract",
                         "get_blender_helper_script", "capture_conditioning_pass"})


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
        raise ValueError(read_instruction(__file__, 'response-155').format(field, identifier.strip()))


def output_arguments(name: str, arguments: dict, operation_dir: Path, *, relative_only=False) -> dict:
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
    if arguments.get(field) and relative_only:
        target = project_path(arguments[field], base=operation_dir)
    if arguments.get(field) == "" or field not in arguments or relative_only:
        if name == "export_structural_report":
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            target.mkdir(parents=True, exist_ok=True)
        arguments[field] = str(target)
    return arguments


def public_result(result, name):
    if name == "project_info" or not os.environ.get("ALMOND_PROJECT_ROOT"):
        return result

    def convert(value):
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except (ValueError, TypeError):
                return relative_output(value)
            if isinstance(decoded, (dict, list)):
                return json.dumps(relative_output(decoded), ensure_ascii=False)
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        return relative_output(value)

    if isinstance(result, ToolResult):
        content = [TextContent(type="text", text=convert(item.text)) if isinstance(item, TextContent) else item
                   for item in result.content]
        return ToolResult(content=content, structured_content=convert(result.structured_content), is_error=result.is_error)
    return convert(result)


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
        self.workspace = None

    def validate(self):
        current, _ = read_binding(self.args.session, self.args.token)
        if current != self.binding:
            raise RuntimeError(read_instruction(__file__, 'response-156'))
        if self.check_owner:
            verify_process(current)
        if self.unconfirmed:
            raise RuntimeError(read_instruction(__file__, 'response-157'))

    def send(self, sender, payload_bytes: bytes, *positional, **keywords) -> str:
        self.validate()
        batch = self.scope.get()
        if batch is None:
            raise RuntimeError("No active operation; no native request was sent.")
        request = json.loads(payload_bytes)
        if request.get("type") == "execute" and self.workspace is not None:
            work = self.workspace.current()
            request["project_root"] = self.locations["project_dir"]
            request["artifact_dir"] = work["artifact_dir"]
            payload_bytes = json.dumps(request).encode("utf-8")
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
                artifact_gate = StoreGate(self.locations["storage"])
                artifact_gate.path = Path(self.locations["storage"]) / ".sessions" / "artifacts.lock"
                if name in FILE_TOOLS:
                    await artifact_gate.__aenter__()
                try:
                    return await self._owned_call(context, call_next, name)
                finally:
                    artifact_gate.close()

    async def _owned_call(self, context, call_next, name):
        operation_id = uuid.uuid4().hex
        operation_dir = Path(self.locations["call_root"]) / operation_id
        # File-free observations have no scratch directory at all.
        args = dict(context.message.arguments or {})
        work = self.workspace.current() if self.workspace is not None else {"artifact_dir": ""}
        if name in OUTPUT_TOOLS and (name != "get_blender_helper_script" or str(args.get("action", "")).lower() == "export"):
            artifact_dir = self.workspace.artifact_path() if self.workspace is not None else operation_dir
            args = output_arguments(name, args, artifact_dir, relative_only=self.workspace is not None)
        if self.workspace is not None:
            input_fields = {"register_drawing_asset": ("source_3dm",),
                            "import_asset_contract": ("contract_path",),
                            "audit_asset_drawing": ("package_dir", "source_glb"),
                            "generate_asset_drawing_views": ("source_glb",)}
            for field in input_fields.get(name, ()):
                if args.get(field):
                    args[field] = str(project_path(args[field], base=Path(self.locations["project_dir"])))
        if name in {"execute_project_python", "publish_objects_to_chestnut"}:
            operation_dir.mkdir(parents=True, exist_ok=False)
        # Bound document expectations are supplied internally. Optional
        # public arguments remain available to standalone consumers.
        if self.workspace is not None and name in {"get_rhino_probe", "upsert_design_component", "sync_design_component",
                    "register_scene_objects", "get_component_intersections", "focus_components",
                    "list_design_components"} and not args.get("expected_model_path"):
            args["expected_model_path"] = self.locations["model_path"]
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
        previous = {key: os.environ.get(key) for key in ("TEMP", "TMP", "TMPDIR", "ALMOND_ARTIFACT_DIR")}
        old_tempdir = tempfile.tempdir
        batch = RequestBatch(self.args.token, operation_id)
        self.batch = batch
        scope_token = self.scope.set(batch)
        # A cancelled caller must not release SQLite/TEMP ownership while
        # an offloaded original function is still running.
        with anyio.CancelScope(shield=True):
            try:
                for key in ("TEMP", "TMP", "TMPDIR"):
                    os.environ[key] = str(operation_dir)
                os.environ["ALMOND_ARTIFACT_DIR"] = work["artifact_dir"]
                tempfile.tempdir = str(operation_dir)
                return public_result(await self._run_to_completion(context.copy(message=message), call_next), name)
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
                if not self.unconfirmed:
                    remove_owned_tree(operation_dir, Path(self.locations["temp"]))
                if cleanup_cancellation is not None:
                    raise cleanup_cancellation
