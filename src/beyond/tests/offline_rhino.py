"""External host boundaries that substitute for a running Rhino."""

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

from codex_host import Broker
from execution_invocation import json_result
from project import connection_paths, write_json
from rhinocode import execution_directory


OBSERVE = "context_04-get_project_info"
EXECUTE = "script_01-run_project_python"
SAVE = "script_02-run_rhino"
RECOVER = "script_03-get_execution"
LIST = "connect_01-list_up"
ATTACH = "connect_02-session"
START = "connect_03-start_session"
DETACH = "connect_04-disconnect"
CLOSE = "connect_05-close_session"

CATALOG = {
    "tools": [
        {"name": name, "inputSchema": {"type": "object"}}
        for name in (OBSERVE, EXECUTE, SAVE, RECOVER)
    ]
}


class OfflineRhino:
    """Own a saved document, answer control requests, and record effects."""

    def __init__(self, root, name, pid):
        root.mkdir(parents=True)
        self.model = root / (name + ".3dm")
        self.model.write_bytes(b"saved model")
        self.advertisement = {"host_id": name, "pid": pid, "process_start_ticks": "1"}
        self.serial = 8
        self.read_only = False
        self.binding = None
        self.reservation = None
        self.worker = None
        self.begin_gate = None
        self.begin_received = asyncio.Event()
        self.closed = False
        self.exit_count = 0

    @property
    def attach_args(self):
        return {"host_id": self.advertisement["host_id"], "model_path": str(self.model)}

    def status(self):
        return dict(
            self.advertisement, model_path=str(self.model), document_serial=self.serial,
            state="connected", saved=True, read_only=self.read_only, modified=False,
        )

    async def request(self, action, **fields):
        if action == "describe":
            return dict(self.status(), state="available" if self.binding is None else "connected")
        if action == "attach":
            for key in ("model_path", "document_serial", "pid", "process_start_ticks"):
                assert fields[key] == self.status()[key]
            token = fields["session_token"]
            paths = connection_paths(self.model, "A", token, create=True)
            self.binding = dict(self.status(), **{
                "schema": "almond-project", "storage_protocol": 2,
                "token": token, "label": "A", "port": 1, **paths,
            })
            write_json(paths["ready_path"], self.binding)
            return dict(self.binding)
        if action == "detach":
            if self.reservation:
                return {"detached": False}
            self.binding = None
            return {"detached": True}
        assert fields["session_token"] == self.binding["token"]
        if action == "status":
            return self.status()
        if action == "begin":
            assert self.reservation is None
            self.reservation = fields["request_id"]
            self.begin_received.set()
            if self.begin_gate is not None:
                await self.begin_gate.wait()
        elif action == "end":
            assert self.reservation == fields["request_id"]
            self.reservation = None
        else:
            assert action in ("worker", "fail"), action
        return {}

    async def close(self):
        pass

    def exit_boundary(self):
        def launch(record, _):
            assert self.reservation is None
            assert self.model.read_bytes() == b"saved by worker"
            assert record["target"]["model_path"] == str(self.model)
            self.exit_count += 1

        def inspect(_, __):
            return {"guard_state": "exit_dispatched", "rhino_closed": self.closed, "cli_closed": True}

        return SimpleNamespace(prepare=lambda *_: None, launch=launch, inspect=inspect)


class WorkerDouble:
    """Publish RhinoCode receipts as an offline worker would."""

    def __init__(self, target):
        self.target = target
        self.calls = []
        self.save_count = 0
        self.gate = None
        self.entered = asyncio.Event()
        self.returned = asyncio.Event()
        self.execution = None
        self.caller_request_id = None
        self.publish_manifest = True
        self.stale_operation = False

    async def start(self):
        pass

    async def state(self):
        active = bool(self.execution and not self.returned.is_set())
        result = dict(pid=2999981, process_start_ticks="1", pending=active,
                      uncertain=False, native_uncertain=False, operation_active=active)
        if self.execution:
            result.update(caller_request_id=self.caller_request_id,
                          operation_id=uuid4().hex if self.stale_operation else self.execution.operation_id,
                          external_requests=[{"request_id": self.execution.request_id}])
        return result

    async def call(self, name, arguments, *, caller_request_id=None):
        if name == OBSERVE:
            self.calls.append(arguments)
            return json_result({"model": self.target.model.name})
        if name == SAVE:
            assert arguments["language"] == "command" and arguments["script"] == "_Save"
            self.target.model.write_bytes(b"saved by worker")
            self.save_count += 1
            return json_result({
                "completed": True, "status": "executed", "request_id": uuid4().hex,
                "result": {"command_accepted": True, "last_command_result": 0},
            }, wrapped=True)
        if name == RECOVER:
            from execution_recovery import read_bound_execution

            assert self.returned.is_set(), "Live worker read would wait behind the original execution."
            return json_result(read_bound_execution(self.target.binding, arguments))

        assert name == EXECUTE
        assert self.execution is None, "Original execution was replayed."
        self.caller_request_id = caller_request_id
        self.execution = Execution(self.target.binding, publish=self.publish_manifest)
        self.entered.set()
        if self.gate is not None:
            await self.gate.wait()
        self.returned.set()
        return json_result({"request_id": self.execution.request_id})

    def request_stop(self):
        if self.gate is not None:
            self.gate.set()
        if self.target.begin_gate is not None:
            self.target.begin_gate.set()

    async def close(self):
        self.request_stop()


class Execution:
    def __init__(self, binding, *, publish):
        self.operation_id = uuid4().hex
        self.request_id = uuid4().hex
        self.identity = dict(
            token=binding["token"], operation_id=self.operation_id,
            request_id=self.request_id, nonce=uuid4().hex, source_hash="e" * 64,
            target={**{key: binding[key] for key in (
                "pid", "process_start_ticks", "document_serial", "model_path",
            )}, "pipe_id": "fixture"},
        )
        journal = dict(
            self.identity, schema="almond-rhinocode-execution", version=1, layout="compact-v1",
            language="python", child={"pid": 2999982, "process_start_ticks": "1"},
        )
        self.directory = execution_directory(binding["call_root"], journal)
        if publish:
            self.directory.mkdir(parents=True)
            write_json(self.directory / "request.json", journal)

    def finish(self, result):
        payload = json.dumps(result).encode("utf-8")
        (self.directory / "result.json").write_bytes(payload)
        write_json(self.directory / "complete.json", dict(
            self.identity, schema="almond-rhinocode-completion", version=1, layout="compact-v1",
            status="success", mutation_state="completed", execution_complete=True,
            result_available=True, result_bytes=len(payload),
            result_sha256=hashlib.sha256(payload).hexdigest(),
        ))


class NoWatcher:
    """Discovery is fixed for the scenario. No OS advertisements are opened."""

    def __init__(self, callback):
        pass

    async def add(self, connection_id, binding):
        pass

    def remove(self, connection_id):
        pass

    async def close(self):
        pass


@asynccontextmanager
async def broker_for(data, targets, **options):
    def target_for(model_path):
        return next(target for target in targets if str(target.model) == model_path)

    def worker_for(binding, connection_id, catalog):
        target = target_for(binding["model_path"])
        target.worker = WorkerDouble(target)
        return target.worker

    broker = Broker(
        CATALOG, data=data, host_reader=lambda _: [target.advertisement for target in targets],
        control_factory=lambda record: next(
            target for target in targets if target.advertisement == record
        ),
        worker_factory=worker_for, watcher_factory=NoWatcher,
        contract_check=lambda _: None, **options,
    )
    try:
        yield broker
    finally:
        await broker.close()


async def value(broker, name, **arguments):
    result = await broker.call(name, arguments)
    assert not result.is_error, result.content
    return result.structured_content


async def rejected(broker, name, **arguments):
    result = await broker.call(name, arguments)
    assert result.is_error, result.structured_content
    return result.content[0].text
