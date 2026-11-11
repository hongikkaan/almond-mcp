"""Public close requests preserve saving, ownership, and non-replay contracts."""
import asyncio
import base64
import json
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace

import pytest

from external_host import Broker, Connection, HostInUse, error_result, exposed_tools, json_result
from session_close import ExitNotDispatched


CATALOG = {"tools": [{"name": "observe", "inputSchema": {"type": "object", "properties": {}}}]}


def fixture(tmp_path):
    actions = []
    binding = dict(pid=123, process_start_ticks="456", document_serial="7",
                   model_path=str(tmp_path / "model.3dm"), token="a" * 32,
                   session_dir=str(tmp_path / "session"), ready_path=str(tmp_path / "ready.json"))
    Path(binding["model_path"]).write_bytes(b"existing model")
    behavior = dict(before={}, after={}, save=dict(completed=True, status="success", request_id="b" * 32,
                    result=dict(command_accepted=True, last_command_result=0)),
                    evidence=dict(guard_state="exit_dispatched", rhino_closed=True, cli_closed=True))
    async def request(action, **_):
        actions.append(action)
        if action == "detach":
            return dict(detached=True)
        value = dict(binding, saved=True, modified="save" not in actions,
                     read_only=False, state="connected")
        value.update(behavior["after"] if "save" in actions else behavior["before"])
        return value
    async def close_worker():
        actions.append("worker_closed")
    async def close_control():
        actions.append("control_closed")
    async def state():
        return dict(pending=False, uncertain=False, native_uncertain=False, pid=321, process_start_ticks="654")
    async def call(name, arguments):
        assert name == "execute_rhino_script"
        assert arguments["language"] == "command" and arguments["script"] == "_-Save"
        actions.append("save")
        # execute_rhino_script has the reviewed wrapped-string MCP schema.
        return json_result({"result": json.dumps(behavior["save"])})
    broker = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None)
    conn = Connection("connection", "host", SimpleNamespace(request=request, close=close_control),
                      binding["token"], binding=binding,
                      worker=SimpleNamespace(close=close_worker, state=state, call=call), state="ready",
                      lease=SimpleNamespace(close=lambda: actions.append("lease_closed")))
    broker.connections[conn.connection_id] = conn
    broker.host_connections[conn.host_id] = conn.connection_id
    broker.selected_connection_id = conn.connection_id
    class Exit:
        def prepare(self, record, directory):
            actions.append("prepare")
        def launch(self, record, directory):
            assert "lease_closed" not in actions and "worker_closed" not in actions
            actions.append("exit")
        def inspect(self, record, directory):
            return behavior["evidence"]
    broker.session_closer.exit_factory = Exit
    broker.session_closer.wait_seconds = 0
    return broker, conn, actions, behavior


def test_close_full_lifecycle_and_restart_only_read_result(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        result = await broker.call("close_session", {"request_id": "close-test"})
        assert not result.is_error
        value = result.structured_content
        assert value["status"] == "completed" and value["saved"]
        assert value["rhino_closed"] and value["worker_closed"] and value["released"]
        assert actions.index("save") < actions.index("exit") < actions.index("worker_closed") < actions.index("lease_closed")
        assert "detach" not in actions
        before = list(actions)
        again = await broker.call("close_session", {"request_id": "close-test"})
        assert again.structured_content == value
        assert actions == before and not broker.connections
        other = await broker.call("close_session", {"request_id": "close-test", "connection_id": "other"})
        assert other.is_error
        restarted = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None)
        assert (await restarted.call("close_session", {"request_id": "close-test"})).structured_content == value
    asyncio.run(run())


@pytest.mark.parametrize("changed", [dict(read_only=True), dict(modified=None), dict(saved=False),
                                     dict(document_serial="8"), dict(process_start_ticks="other"),
                                     dict(model_path="different.3dm")])
def test_preflight_rejection_sends_neither_save_nor_exit(tmp_path, changed):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["before"] = changed
        result = (await broker.call("close_session", {"request_id": "readonly"})).structured_content
        assert result["status"] == "rejected" and not result["saved"]
        assert "save" not in actions and "exit" not in actions and "worker_closed" not in actions
        assert conn.state == "ready" and not conn.closing
    asyncio.run(run())


@pytest.mark.parametrize("save,after,expected", [
    (dict(completed=True, status="error"), {}, "save_failed"),
    (dict(completed=False, status="pending", request_id="b" * 32), {}, "unconfirmed"),
    (dict(completed=True, status="success", request_id="b" * 32, result=dict(command_accepted=True, last_command_result=0)), dict(modified=True), "rejected"),
    (dict(completed=True, status="success", request_id="b" * 32, result=dict(command_accepted=True, last_command_result=0)), dict(document_serial="8"), "rejected"),
    (dict(completed=True, status="success", request_id="b" * 32, result=dict(command_accepted=False, last_command_result=0)), {}, "save_failed"),
    (dict(completed=True, status="success", request_id="b" * 32, result=dict(command_accepted=True, last_command_result=2)), {}, "save_failed"),
])
def test_unsuccessful_or_changed_save_never_exits(tmp_path, save, after, expected):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior.update(save=save, after=after)
        result = (await broker.call("close_session", {"request_id": "failed"})).structured_content
        assert result["status"] == expected
        assert "save" in actions and "exit" not in actions and "worker_closed" not in actions
        before = list(actions)
        await broker.call("close_session", {"request_id": "failed"})
        assert actions == before
    asyncio.run(run())


def test_pending_exit_preserves_ownership_blocks_new_work_and_recovers_without_replay(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="exit_dispatched", rhino_closed=False, cli_closed=True)
        first = (await broker.call("close_session", {"request_id": "delayed"})).structured_content
        assert first["status"] == "unconfirmed" and first["saved"]
        assert "worker_closed" not in actions and "lease_closed" not in actions
        for name, args in [("close_session", {"request_id": "different"}), ("disconnect", {}), ("observe", {})]:
            assert (await broker.call(name, args)).is_error
        assert actions.count("save") == actions.count("exit") == 1
        behavior["evidence"]["rhino_closed"] = True
        finished = (await broker.call("close_session", {"request_id": "delayed"})).structured_content
        assert finished["status"] == "completed"
        assert actions.count("save") == actions.count("exit") == 1
    asyncio.run(run())


def test_guard_rejection_releases_close_reservation_but_preserves_open_connection(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="rejected", rhino_closed=False, cli_closed=True, reason="dirty")
        value = (await broker.call("close_session", {"request_id": "guard"})).structured_content
        assert value["status"] == "rejected" and value["reason"] == "dirty"
        assert not conn.closing and conn.state == "ready"
        assert "worker_closed" not in actions and "lease_closed" not in actions
        assert broker.session_closer.pending_for(conn.binding) is None
    asyncio.run(run())


def test_pending_close_after_restart_prevents_attach(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="missing", rhino_closed=False, cli_closed=True)
        await broker.call("close_session", {"request_id": "retained"})
        record = dict(conn.binding, host_id="host")
        restarted = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None,
                           host_reader=lambda _: [record],
                           lease_factory=lambda *_: pytest.fail("must not attach a retained close"))
        result = await restarted.call("connect", {"host_id": "host", "model_path": record["model_path"]})
        assert result.is_error and "retained" in result.content[0].text
        targets = (await restarted.list_connections())["targets"]
        assert targets[0]["state"] == "unavailable" and "retained" in targets[0]["reason"]
    asyncio.run(run())


@pytest.mark.parametrize("difference", ["dirty", "document", "process", "readonly", "worker", "invalid_binding", "not_script_runner", "exit_rejected", None])
def test_exit_guard_checks_live_identity_and_dirty_state_in_same_callback(tmp_path, monkeypatch, difference):
    target = dict(pid=123, process_start_ticks="456", document_serial="7", model_path=str(tmp_path / "model.3dm"))
    Path(target["model_path"]).write_bytes(b"existing model")
    ready = tmp_path / "ready.json"
    ready.write_text(json.dumps(dict(token="a" * 32, valid=difference != "invalid_binding")))
    payload = dict(request_id="guard", nonce="nonce", target=target, receipt_path=str(tmp_path / "guard.json"),
                   ready_path=str(ready), token="a" * 32, worker_identity=dict(pid=321, process_start_ticks="654"))
    doc = SimpleNamespace(RuntimeSerialNumber=8 if difference == "document" else 7,
                          Path=target["model_path"], Modified=difference == "dirty", IsReadOnly=difference == "readonly")
    calls = []
    def run_script(serial, macro, echo):
        armed = json.loads((tmp_path / "guard.json").read_text())
        assert armed["state"] == "exit_dispatched"
        calls.append((serial, macro, echo))
        return difference != "exit_rejected"
    def process(pid, ticks):
        return SimpleNamespace(Id=pid, HasExited=difference == "worker", Dispose=lambda: None,
                               StartTime=SimpleNamespace(ToUniversalTime=lambda: SimpleNamespace(Ticks=ticks)))
    monkeypatch.setitem(sys.modules, "Rhino", SimpleNamespace(
        RhinoDoc=SimpleNamespace(ActiveDoc=doc),
        RhinoApp=SimpleNamespace(IsOnMainThread=True, RunScript=run_script),
        Commands=SimpleNamespace(Command=SimpleNamespace(InScriptRunnerCommand=lambda: difference != "not_script_runner"))))
    monkeypatch.setitem(sys.modules, "System", SimpleNamespace(Diagnostics=SimpleNamespace(Process=SimpleNamespace(
        GetCurrentProcess=lambda: process(124 if difference == "process" else 123, 456),
        GetProcessById=lambda _: process(321, 654)))))
    source = (Path(__file__).parents[1] / "session_close_guard.py.txt").read_text()
    source = source.replace("__PAYLOAD__", base64.b64encode(json.dumps(payload).encode()).decode())
    exec(compile(source, "guard.py", "exec"), {})
    receipt = json.loads((tmp_path / "guard.json").read_text())
    if difference is None:
        assert calls == [(7, "_-Exit", False)] and receipt["state"] == "exit_returned"
    elif difference == "exit_rejected":
        assert calls == [(7, "_-Exit", False)] and receipt["state"] == "rejected"
    else:
        assert calls == [] and receipt["state"] == "rejected"


def test_close_schema_is_explicit():
    tool = next(t for t in exposed_tools(CATALOG)[0] if t.name == "close_session")
    assert tool.input_schema["required"] == ["request_id"]
    assert set(tool.input_schema["properties"]) == {"request_id", "connection_id"}
    assert "saved" in tool.output_schema["properties"]


def test_concurrent_brokers_cannot_reuse_request_id_for_another_rhino(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        entered, finish = asyncio.Event(), asyncio.Event()
        original = conn.worker.call
        async def saving(name, arguments):
            entered.set()
            await finish.wait()
            return await original(name, arguments)
        conn.worker.call = saving
        first = asyncio.create_task(broker.call("close_session", {"request_id": "same-id"}))
        await entered.wait()
        second, other, other_actions, _ = fixture(tmp_path)
        other.binding.update(pid=999, process_start_ticks="999")
        other.connection_id = "different-connection"
        second.connections = {other.connection_id: other}
        second.selected_connection_id = other.connection_id
        result = await second.call("close_session", {"request_id": "same-id"})
        assert result.structured_content["connection_id"] == conn.connection_id
        assert other_actions == []
        conflict = await second.call("close_session", {"request_id": "same-id", "connection_id": other.connection_id})
        assert conflict.is_error and other_actions == []
        finish.set()
        assert (await first).structured_content["status"] == "completed"
        assert actions.count("save") == actions.count("exit") == 1
    asyncio.run(run())


@pytest.mark.parametrize("stage", ["preflight", "save_confirmed"])
def test_interrupted_before_exit_is_rejected_on_read_without_replay(tmp_path, stage):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="missing", rhino_closed=False, cli_closed=False)
        await broker.call("close_session", {"request_id": "interrupted"})
        record = broker.session_closer.load("interrupted")
        record.update(stage=stage, status="closing")
        broker.session_closer.persist(record)
        restarted = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None)
        value = (await restarted.call("close_session", {"request_id": "interrupted"})).structured_content
        assert value["status"] == "rejected"
        assert restarted.session_closer.pending_for(conn.binding) is None
        assert actions.count("save") == actions.count("exit") == 1
    asyncio.run(run())


def test_exit_known_not_dispatched_preserves_open_connection(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        base = broker.session_closer.exit_factory
        class FailedLaunch(base):
            def launch(self, record, directory):
                raise ExitNotDispatched("CreateProcess failed before dispatch")
        broker.session_closer.exit_factory = FailedLaunch
        value = (await broker.call("close_session", {"request_id": "no-dispatch"})).structured_content
        assert value["status"] == "rejected" and value["saved"]
        assert conn.state == "ready" and not conn.closing
        assert "exit" not in actions and "worker_closed" not in actions
        assert broker.session_closer.pending_for(conn.binding) is None
    asyncio.run(run())


def test_foreign_recovery_does_not_claim_release_while_previous_host_owns_lease(tmp_path, monkeypatch):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="exit_dispatched", rhino_closed=False, cli_closed=True)
        await broker.call("close_session", {"request_id": "owner-held"})
        behavior["evidence"]["rhino_closed"] = True
        def held(*_):
            raise HostInUse("original host still owns this Rhino")
        restarted = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None, lease_factory=held)
        restarted.session_closer.exit_factory = broker.session_closer.exit_factory
        monkeypatch.setattr("session_close.process_identity_alive", lambda _: False)
        result = (await restarted.call("close_session", {"request_id": "owner-held"})).structured_content
        assert result["rhino_closed"] and result["worker_closed"] and not result["released"]
        assert result["status"] == "closing"
        assert "lease_closed" not in actions
        final = (await broker.call("close_session", {"request_id": "owner-held"})).structured_content
        assert final["status"] == "completed" and final["released"]
    asyncio.run(run())


def test_unrelated_corrupt_close_record_does_not_block_this_rhino(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        unrelated = broker.session_closer.directory("another-target")
        unrelated.mkdir(parents=True)
        (unrelated / "request.json").write_text("broken unrelated JSON")
        result = (await broker.call("close_session", {"request_id": "valid-target"})).structured_content
        assert result["status"] == "completed"
    asyncio.run(run())


def test_old_orphan_request_query_cannot_replace_new_target_fence(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="missing", rhino_closed=False, cli_closed=False)
        await broker.call("close_session", {"request_id": "new-active"})
        orphan = broker.session_closer.load("new-active")
        orphan.update(request_id="older-orphan", stage="preflight", status="closing")
        broker.session_closer.persist(orphan)  # Crash had occurred before its index publication.
        value = (await broker.call("close_session", {"request_id": "older-orphan"})).structured_content
        assert value["status"] == "rejected"
        assert broker.session_closer.pending_for(conn.binding) == "new-active"
        assert actions.count("save") == actions.count("exit") == 1
    asyncio.run(run())


def test_foreign_guard_rejection_still_restores_original_owner_on_its_later_read(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["evidence"] = dict(guard_state="missing", rhino_closed=False, cli_closed=False)
        await broker.call("close_session", {"request_id": "foreign-rejection"})
        assert conn.closing
        behavior["evidence"] = dict(guard_state="rejected", rhino_closed=False, cli_closed=True, reason="dirty")
        reader = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None)
        reader.session_closer.exit_factory = broker.session_closer.exit_factory
        assert (await reader.call("close_session", {"request_id": "foreign-rejection"})).structured_content["status"] == "rejected"
        assert conn.closing
        assert (await broker.call("close_session", {"request_id": "foreign-rejection"})).structured_content["status"] == "rejected"
        assert not conn.closing and conn.state == "ready"
    asyncio.run(run())


def test_settled_worker_error_before_save_journal_does_not_strand_connection(tmp_path):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        async def fail_before_execution(name, arguments):
            return error_result("ScriptServer unavailable before dispatch")
        conn.worker.call = fail_before_execution
        value = (await broker.call("close_session", {"request_id": "save-not-dispatched"})).structured_content
        assert value["status"] == "rejected"
        assert broker.session_closer.pending_for(conn.binding) is None
        assert not conn.in_flight and conn.state == "ready"
        assert "save" not in actions and "exit" not in actions
        assert not (await broker.call("disconnect", {})).is_error
    asyncio.run(run())


def test_exact_late_save_completion_is_read_without_automatically_exiting(tmp_path, monkeypatch):
    async def run():
        broker, conn, actions, behavior = fixture(tmp_path)
        behavior["save"] = dict(completed=False, status="pending", request_id="b" * 32)
        value = (await broker.call("close_session", {"request_id": "late-save"})).structured_content
        assert value["status"] == "unconfirmed" and "exit" not in actions
        import hashlib
        folder = Path(conn.binding["session_dir"])
        folder.mkdir()
        (folder / "rhinocode.json").write_text(json.dumps(dict(
            request_id="b" * 32, token=conn.token, source_hash=hashlib.sha256(b"_-Save").hexdigest(),
            target=conn.binding)))
        monkeypatch.setattr("session_close.read_bound_execution", lambda *_: dict(completed=True, status="success"))
        value = (await broker.call("close_session", {"request_id": "late-save"})).structured_content
        assert value["status"] == "rejected" and value["stage"] == "save_completed_without_exit"
        assert actions.count("save") == 1 and "exit" not in actions
        assert broker.session_closer.pending_for(conn.binding) is None
    asyncio.run(run())


def test_owned_cli_identity_survives_a_child_that_already_exited():
    from rhinocode import child_process_identity
    child = subprocess.Popen([sys.executable, "-B", "-c", "pass"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    assert child.wait(timeout=10) == 0
    identity = child_process_identity(child)
    assert identity["pid"] == child.pid
    assert identity["process_start_ticks"].isdigit() and int(identity["process_start_ticks"]) > 0
