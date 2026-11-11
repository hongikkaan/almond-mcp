"""Save and close one owned Rhino; retained request IDs never replay mutations.

Exit cannot use the ordinary script completion receipt: Rhino may terminate
before its finally block. A tiny identity/dirty guard arms Exit on the UI
thread, then the external owner proves target and CLI process termination.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from runtime import ENGINE

sys.path.insert(0, str(ENGINE))
from project import ExclusiveFile, read_json, write_json
from rhinocode import find_binary, discover_instances, select_instance, child_process_identity
from storage_cleanup import plain_descendant, process_identity_alive
from execution_recovery import read_bound_execution


TERMINAL = {"completed", "rejected", "save_failed"}
IDENTITY = ("pid", "process_start_ticks", "document_serial", "model_path")
SAVE_COMMAND = "_Save"  # The verified bound document already has its saved filename.


class ExitNotDispatched(RuntimeError):
    pass


def same_document(binding, status):
    return (status.get("pid") == binding["pid"]
            and str(status.get("process_start_ticks")) == str(binding["process_start_ticks"])
            and str(status.get("document_serial")) == str(binding["document_serial"])
            and os.path.normcase(str(status.get("model_path", ""))) == os.path.normcase(binding["model_path"]))


class RhinoExit:
    def __init__(self):
        self.process = None

    def prepare(self, record, directory):
        binary = find_binary()
        instance = select_instance(record["target"], discover_instances(binary))
        record["pipe_id"] = instance["pipeId"]
        record["executable"] = str(binary)
        payload = {key: record[key] for key in ("request_id", "nonce", "target", "worker_identity")}
        payload.update(ready_path=record["binding"]["ready_path"], token=record["binding"]["token"])
        payload["receipt_path"] = str(directory / "guard.json")
        template = Path(__file__).with_name("session_close_guard.py.txt").read_text(encoding="utf-8")
        encoded = base64.b64encode(json.dumps(payload, ensure_ascii=True).encode("ascii")).decode("ascii")
        (directory / "guard.py").write_text(template.replace("__PAYLOAD__", encoded), encoding="utf-8")

    def launch(self, record, directory):
        try:
            instance = select_instance(record["target"], discover_instances(record["executable"]))
            if instance["pipeId"] != record["pipe_id"]:
                raise RuntimeError("Rhino ScriptServer changed before close; no Exit was sent.")
            macro = '_-ScriptEditor _Run "' + str(directory / "guard.py") + '"'
            self.process = subprocess.Popen(
                [record["executable"], "--rhino", record["pipe_id"], "command", macro],
                shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        except Exception as exc:
            raise ExitNotDispatched(str(exc)) from exc
        record["child"] = child_process_identity(self.process)

    def inspect(self, record, directory):
        state = {"guard_state": "missing", "rhino_closed": process_identity_alive(record["target"]) is False,
                 "cli_closed": ((self.process.poll() is not None) if self.process is not None else
                                process_identity_alive(record.get("child", {})) is False)}
        try:
            path = directory / "guard.json"
            if path.stat().st_size > 32768:
                raise ValueError("Close guard receipt exceeds its limit.")
            guard = read_json(path)
        except FileNotFoundError:
            return state
        if (guard.get("schema") != "almond-close-guard" or any(
                guard.get(key) != record[key] for key in ("request_id", "nonce", "target"))
                or guard.get("state") not in {"rejected", "exit_dispatched", "exit_returned"}):
            raise RuntimeError("Close guard receipt does not match this exact request.")
        state.update(guard_state=guard["state"], reason=guard.get("reason", ""))
        return state


class SessionCloser:
    def __init__(self, data, *, exit_factory=RhinoExit, wait_seconds=30.0):
        self.root = Path(data).absolute() / "session-closes"
        self.exit_factory, self.wait_seconds = exit_factory, wait_seconds
        self.exits = {}
        self.running = set()

    def directory(self, request_id):
        if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
            raise ValueError("close_session requires a nonempty request_id of at most 128 characters.")
        key = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
        return plain_descendant(self.root / key, self.root.parent)

    def load(self, request_id):
        path = self.directory(request_id) / "request.json"
        if not path.exists():
            return None
        if path.stat().st_size > 65536:
            raise ValueError("Close request exceeds its retained limit.")
        record = read_json(path)
        if record.get("schema") != "almond-session-close" or record.get("request_id") != request_id:
            raise ValueError("Retained close request identity is invalid.")
        return record

    def persist(self, record, *, claim=False):
        directory = self.directory(record["request_id"])
        directory.mkdir(parents=True, exist_ok=True)
        write_json(directory / "request.json", record)
        if claim:
            # Publish the target fence once, before any Save dispatch. Reading
            # an older orphan request must never overwrite a newer target fence.
            marker = self.target_path(record["target"])
            marker.parent.mkdir(parents=True, exist_ok=True)
            write_json(marker, dict(request_id=record["request_id"], target=record["target"]))

    def target_path(self, target):
        identity = str(target.get("pid")) + ":" + str(target.get("process_start_ticks"))
        key = hashlib.sha256(identity.encode("ascii")).hexdigest()
        return plain_descendant(self.root / "targets" / (key + ".json"), self.root.parent)

    def pending_for(self, target):
        """A restarted host must not attach while a retained Exit can still run."""
        path = self.target_path(target)
        if not path.is_file():
            return None
        marker = read_json(path)
        other = marker["target"]
        if (other.get("pid") != target.get("pid") or
                str(other.get("process_start_ticks")) != str(target.get("process_start_ticks"))):
            raise RuntimeError("The retained close target index is invalid.")
        value = self.load(marker["request_id"])
        if value is None:
            raise RuntimeError("The indexed close request is missing; inspect this target before reconnecting.")
        if value.get("status") not in TERMINAL:
            return value["request_id"]
        return None

    @staticmethod
    def public(record):
        return {key: value for key, value in record.items() if key in {
            "request_id", "connection_id", "status", "stage", "saved", "modified_before",
            "modified_after", "rhino_closed", "worker_closed", "released", "reason",
            "save_request_id", "pid", "model_path"}}

    async def inspect(self, broker, record, *, locked=False):
        conn = broker.connections.get(record["connection_id"])
        if conn is not None and conn.token != record["binding"]["token"]:
            raise RuntimeError("The retained close belongs to another connection generation.")
        if conn is not None and not locked:
            async with conn.lock:
                return await self.inspect(broker, record, locked=True)
        if record["status"] in TERMINAL:
            if record["stage"] == "guard_rejected":
                await self._restore_connection(broker, conn)
            return self.public(record)
        if record["stage"] in {"preflight", "save_settled", "save_confirmed"}:
            record.update(status="rejected", reason="The previous host stopped before Exit dispatch. No close was resumed.")
            self.persist(record)
            return self.public(record)
        if record["stage"] not in {"exit_dispatching", "exit_waiting"}:
            # Saving may have completed after the caller/host stopped. Reading
            # this close request never resumes it or dispatches an Exit.
            if record["stage"] == "saving":
                await self._inspect_save(broker, record)
            return self.public(record)
        exit_run = self.exits.get(record["request_id"]) or self.exit_factory()
        evidence = await asyncio.to_thread(exit_run.inspect, record, self.directory(record["request_id"]))
        if evidence["rhino_closed"] and evidence["cli_closed"] and evidence["guard_state"] in {"exit_dispatched", "exit_returned"}:
            record.update(rhino_closed=True, status="closing", reason="")
            if conn is not None:
                await broker._dispose_closed_rhino(conn)
                record.update(worker_closed=conn.cleanup["worker_closed"], released=conn.cleanup["released"])
            else:
                # After a host restart, prove the former worker's exit too.
                record["worker_closed"] = process_identity_alive(record.get("worker_identity", {})) is False
                record["released"] = False
                if record["worker_closed"]:
                    try:
                        probe = broker.lease_factory(broker.data, record["target"])
                        probe.close()
                        record["released"] = True
                    except (OSError, RuntimeError):
                        record["reason"] = "The previous host still owns this connection; its cleanup is not confirmed."
            if record["worker_closed"] and record["released"]:
                record.update(status="completed", stage="completed")
            self.persist(record)
        elif evidence["guard_state"] == "rejected" and evidence["cli_closed"]:
            record.update(status="rejected", stage="guard_rejected", reason=evidence.get("reason", "Exit guard rejected this request."))
            await self._restore_connection(broker, conn)
            self.persist(record)
        return self.public(record)

    @staticmethod
    async def _restore_connection(broker, conn):
        if conn is not None and conn.closing and not broker.closing:
            conn.closing = False
            try:
                await broker._binding_status(conn)
                conn.state, conn.reason = "ready", ""
            except Exception as exc:
                conn.state, conn.reason = "unconfirmed", str(exc)

    async def _inspect_save(self, broker, record):
        # Recover only the Save issued after this request's persisted baseline.
        # This is a read, never permission to continue into Exit.
        try:
            path = Path(record["binding"]["session_dir"]) / "rhinocode.json"
            journal = read_json(path) if path.is_file() else None
            unchanged = ((journal is None and record.get("save_baseline") is None) or
                         (journal is not None and journal.get("request_id") == record.get("save_baseline")))
            if unchanged and process_identity_alive(record.get("worker_identity", {})) is False:
                record.update(status="rejected", stage="save_not_dispatched",
                              reason="The former worker exited without publishing a new Save execution. No Exit was sent.")
                self.persist(record)
                return
            if journal is None:
                return
            if (journal.get("request_id") == record.get("save_baseline")
                    or journal.get("source_hash") != hashlib.sha256(SAVE_COMMAND.encode("utf-8")).hexdigest()
                    or journal.get("token") != record["binding"]["token"]
                    or not same_document(record["target"], journal.get("target", {}))):
                return
            request_id = journal["request_id"]
            if record.get("save_request_id") and record["save_request_id"] != request_id:
                return
            record["save_request_id"] = request_id
            result = await asyncio.to_thread(read_bound_execution, record["binding"], {"request_id": request_id})
            if result.get("completed") is not True:
                self.persist(record)
                return
            conn = broker.connections.get(record["connection_id"])
            if conn is not None and conn.state == "recovering":
                await broker.recover_execution(conn, {"request_id": request_id})
            success = result.get("status") == "success"
            record.update(status="rejected" if success else "save_failed", stage="save_completed_without_exit",
                          reason="The retained Save finished. This close did not send Exit; submit a new close request only when you intend to close now.")
            self.persist(record)
        except (OSError, ValueError, RuntimeError, KeyError):
            return  # Missing or corrupt completion remains unconfirmed.

    async def run(self, broker, request_id, connection_id=None):
        directory = self.directory(request_id)
        directory.mkdir(parents=True, exist_ok=True)
        try:
            reservation = ExclusiveFile(directory / "request.lock")
        except OSError as exc:
            if exc.errno not in (32, 33):
                raise
            record = self.load(request_id)
            if record is None:
                raise RuntimeError("This close request is being initialized; query the same request_id again.") from exc
            if connection_id is not None and connection_id != record["connection_id"]:
                raise RuntimeError("This close request_id belongs to a different connection.")
            return self.public(record)
        try:
            return await self._run_reserved(broker, request_id, connection_id)
        finally:
            reservation.close()

    async def _run_reserved(self, broker, request_id, connection_id):
        record = self.load(request_id)
        if record is not None:
            if connection_id is not None and connection_id != record["connection_id"]:
                raise RuntimeError("This close request_id belongs to a different connection.")
            if request_id in self.running:
                return self.public(record)
            return await self.inspect(broker, record)
        selected = connection_id or broker.selected_connection_id
        conn = broker.connections.get(selected)
        if conn is None:
            raise RuntimeError("No selected live connection. Connect before closing a new session.")
        if conn.lock.locked() or conn.in_flight or conn.closing or conn.state != "ready":
            raise RuntimeError("Rhino has active or unconfirmed work; no save or Exit was sent.")
        broker.contract_check(broker.catalog)
        pending = self.pending_for(conn.binding)
        if pending:
            raise RuntimeError("A previous close is retained. Read close_session with request_id=" + pending)
        self.running.add(request_id)
        try:
            return await self._run_new(broker, conn, request_id)
        finally:
            self.running.discard(request_id)

    async def _run_new(self, broker, conn, request_id):
        from external_host import Invocation, result_dict
        async with conn.lock:
            record = dict(schema="almond-session-close", version=1, request_id=request_id,
                          nonce=uuid4().hex, connection_id=conn.connection_id,
                          binding=dict(conn.binding),
                          target={key: conn.binding[key] for key in IDENTITY},
                          pid=conn.binding["pid"], model_path=conn.binding["model_path"],
                          status="closing", stage="preflight", saved=False,
                          rhino_closed=False, worker_closed=False, released=False, reason="")
            self.persist(record, claim=True)
            exit_run = self.exit_factory()
            self.exits[request_id] = exit_run
            try:
                state = await conn.worker.state()
                if state.get("pending") or state.get("uncertain"):
                    raise RuntimeError("The worker still has unconfirmed work; no save or Exit was sent.")
                record["worker_identity"] = {key: state.get(key) for key in ("pid", "process_start_ticks")}
                before = await conn.control.request("status", session_token=conn.token)
                self._document(conn.binding, before)
                record["modified_before"] = before["modified"]
                await asyncio.to_thread(exit_run.prepare, record, self.directory(request_id))
                baseline = Path(conn.binding["session_dir"]) / "rhinocode.json"
                record["save_baseline"] = read_json(baseline)["request_id"] if baseline.is_file() else None
                record["stage"] = "saving"
                self.persist(record)  # Fence precedes the first possible save dispatch.
                response = await broker._invoke_locked(conn, "execute_rhino_script",
                    dict(script=SAVE_COMMAND, language="command", timeout_seconds=60), Invocation())
                if conn.state == "ready" and not conn.in_flight:
                    record["stage"] = "save_settled"
                    self.persist(record)
                saved = result_dict(response)
                # This particular tool's public output is a JSON string wrapped
                # by FastMCP, unlike get_rhino_execution and worker state.
                if isinstance(saved.get("result"), str):
                    saved = json.loads(saved["result"])
                if not isinstance(saved, dict):
                    raise RuntimeError("Save returned an invalid execution result; Exit was not sent.")
                record["save_request_id"] = saved.get("request_id", "")
                if saved.get("completed") is not True:
                    record.update(status="unconfirmed", stage="saving", reason="Save completion is retained. Read get_rhino_execution; Exit was not sent.")
                    self.persist(record)
                    return self.public(record)
                command = saved.get("result", {})
                if (saved.get("status") != "success" or not isinstance(command, dict)
                        or command.get("command_accepted") is not True or command.get("last_command_result") != 0
                        or not saved.get("request_id") or saved.get("result_error") or saved.get("result_display_error")):
                    record.update(status="save_failed", reason="Save did not complete successfully; Rhino remains open.")
                    self.persist(record)
                    return self.public(record)
                record["stage"] = "save_confirmed"
                self.persist(record)
                after = await conn.control.request("status", session_token=conn.token)
                self._document(conn.binding, after)
                if after["modified"]:
                    raise RuntimeError("The document remains modified after Save; Exit was not sent.")
                if broker.closing or conn.closing:
                    raise RuntimeError("The MCP host is closing; no Exit was sent.")
                record.update(saved=True, modified_after=False, stage="exit_dispatching")
                conn.closing, conn.state = True, "closing"
                self.persist(record)  # Survives a host crash around CreateProcess.
                await asyncio.to_thread(exit_run.launch, record, self.directory(request_id))
                record["stage"] = "exit_waiting"
                self.persist(record)
                deadline = time.monotonic() + self.wait_seconds
                while True:
                    result = await self.inspect(broker, record, locked=True)
                    if record["status"] in TERMINAL:
                        return result
                    if time.monotonic() >= deadline:
                        record.update(status="unconfirmed", reason="Exit outcome is retained. Repeat this request_id to read it; do not submit another close.")
                        self.persist(record)
                        return self.public(record)
                    await asyncio.sleep(0.1)
            except Exception as exc:
                # Once dispatch might have happened, an exception is not proof
                # that work stopped. Keep the retained request and ownership.
                uncertain = record["stage"] in {"saving", "exit_dispatching", "exit_waiting"} and not isinstance(exc, ExitNotDispatched)
                if not uncertain and conn.closing and not broker.closing:
                    conn.closing, conn.state = False, "ready"
                record.update(status="unconfirmed" if uncertain else "rejected", reason=str(exc)[:2000])
                self.persist(record)
                return self.public(record)

    @staticmethod
    def _document(binding, status):
        if (not same_document(binding, status) or status.get("saved") is not True
                or status.get("state") != "connected"):
            raise RuntimeError("The saved Rhino document or binding changed; Exit was not sent.")
        if status.get("read_only") is not False or type(status.get("modified")) is not bool:
            raise RuntimeError("Writable document state is unavailable. Load the updated AlmondRhino; no Exit was sent.")
