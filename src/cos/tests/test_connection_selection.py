"""A selected connection removes repeated routing IDs without sharing bindings."""
import asyncio
import os
from types import SimpleNamespace

import pytest

from external_host import Broker, Connection, StartAttempt, exposed_tools, json_result


CATALOG = {"tools": [
    {"name": "observe", "inputSchema": {
        "type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "script_03-get_execution", "inputSchema": {
        "type": "object", "properties": {"request_id": {"type": "string"}}, "additionalProperties": False}},
]}


def connection(name, root):
    async def detach(*_args, **_kwargs):
        return {"detached": True}

    async def close():
        pass

    return Connection(name, "host-" + name, SimpleNamespace(request=detach, close=close),
                      "token-" + name, binding={"model_path": name + ".3dm", "session_dir": str(root / name)}, state="ready")


def broker_for(tmp_path):
    broker = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None,
                    host_reader=lambda _: [], recovery_store_factory=lambda _: None)
    broker.connections = {name: connection(name, tmp_path) for name in ("a", "b")}
    broker.host_connections = {"host-" + name: name for name in ("a", "b")}
    return broker


def test_connection_id_is_output_only_and_selection_is_advertised(tmp_path):
    tools = exposed_tools(CATALOG)
    for tool in tools:
        assert "connection_id" not in tool.input_schema["properties"]
    broker = broker_for(tmp_path)

    async def run():
        await broker.connect("host-a", "a.3dm")
        listing = await broker.list_connections()
        assert listing["selected_connection_id"] == "a"
        assert {c["connection_id"] for c in listing["connections"]} == {"a", "b"}
        with pytest.raises(RuntimeError, match="different model"):
            await broker.connect("host-b", "a.3dm")
        assert broker.selected_connection_id == "a"

    asyncio.run(run())


def test_queued_call_keeps_its_connection_while_selection_changes(tmp_path):
    broker = broker_for(tmp_path)

    async def run():
        arrived, release = asyncio.Event(), asyncio.Event()
        observed = []

        async def invoke(conn, name, args, invocation):
            arrived.set()
            await release.wait()
            observed.append((conn.connection_id, conn.token, args))
            return json_result({"connection": conn.connection_id})

        broker.invoke = invoke
        await broker.connect("host-a", "a.3dm")
        first = asyncio.create_task(broker.call("observe", {}))
        await arrived.wait()
        await broker.connect("host-b", "b.3dm")
        second = asyncio.create_task(broker.call("observe", {}))
        release.set()
        assert not (await first).is_error
        assert not (await second).is_error
        assert observed == [("a", "token-a", {}), ("b", "token-b", {})]
        failed = await broker.call("observe", {"connection_id": "a"})
        assert failed.is_error and len(observed) == 2
        assert broker.selected_connection_id == "b"

    asyncio.run(run())


def test_execution_request_follows_its_binding_after_switch_and_restart(tmp_path):
    from project import STORAGE_PROTOCOL, connection_paths, process_start_ticks, write_json
    from rhinocode import execution_directory

    broker = Broker(CATALOG, data=tmp_path / "broker", contract_check=lambda _: None)
    request_id, token = "1" * 32, "2" * 32
    model = tmp_path / "a.3dm"
    model.touch()
    locations = connection_paths(model, "A", token, create=True)
    target = dict(pid=os.getpid(), process_start_ticks=str(process_start_ticks(os.getpid())),
                  document_serial=1, model_path=str(model))
    binding = dict(locations, **target)
    binding.update(schema="almond-project", storage_protocol=STORAGE_PROTOCOL, label="A", token=token)
    write_json(locations["ready_path"], binding)
    journal = dict(schema="almond-rhinocode-execution", version=1, token=token,
                   operation_id="3" * 32, request_id=request_id, nonce="4" * 32,
                   source_hash="5" * 64, language="python", target=dict(target, pipe_id="fixture"),
                   layout="compact-v1", child=None, not_dispatched=True, dispatch_error="fixture")
    manifest = execution_directory(locations["call_root"], journal) / "request.json"
    manifest.parent.mkdir(parents=True)
    write_json(manifest, journal)
    broker.recovery_store.remember(binding)
    a, b = (connection(name, tmp_path) for name in ("a", "b"))
    a.token, a.binding = token, binding
    broker.connections = {"a": a, "b": b}
    broker.host_connections = {"host-a": "a", "host-b": "b"}
    calls = []

    async def worker_call(name, arguments):
        calls.append((name, arguments))
        return json_result({"request_id": request_id})

    async def worker_state():
        return {"native_uncertain": False}

    async def run():
        a.worker = SimpleNamespace(call=worker_call, state=worker_state)
        await broker.connect("host-a", str(model))
        await broker.connect("host-b", "b.3dm")
        args = {"request_id": request_id}
        live = await broker.call("script_03-get_execution", args)
        assert live.structured_content["connection_state"] == "ready"
        assert calls == [("script_03-get_execution", args)]
        assert broker.selected_connection_id == "b"
        missing = await broker.call("script_03-get_execution", {"request_id": "6" * 32})
        assert missing.is_error
        assert calls == [("script_03-get_execution", args)]

        restarted = Broker(CATALOG, data=broker.data, contract_check=lambda _: None)
        retained = await restarted.call("script_03-get_execution", args)
        assert retained.structured_content["request_id"] == request_id
        assert retained.structured_content["target_identity"] == target
        assert retained.structured_content["completion_state"] == "not_started"
        assert retained.structured_content["recovery_only"] is True
        assert not restarted.connections

    asyncio.run(run())


def test_disconnect_clears_selection_without_falling_back(tmp_path):
    broker = broker_for(tmp_path)

    async def run():
        await broker.connect("host-a", "a.3dm")
        assert (await broker.call("connect_04-disconnect", {"connection_id": "b"})).is_error
        assert set(broker.connections) == {"a", "b"}
        assert not (await broker.call("connect_04-disconnect", {})).is_error
        assert broker.selected_connection_id is None
        assert set(broker.connections) == {"b"}
        assert (await broker.call("observe", {})).is_error
        await broker.connect("host-b", "b.3dm")
        assert broker.selected_connection_id == "b"

    asyncio.run(run())


@pytest.mark.parametrize("state", ["recovering", "unconfirmed"])
@pytest.mark.parametrize("route", ["connect", "start_session"])
def test_reselect_for_recovery_keeps_normal_calls_blocked(tmp_path, state, route):
    """A -> B -> A recovery needs no routing ID and never dispatches new work."""
    broker = broker_for(tmp_path)
    broker.starts["start-a"] = StartAttempt("a.3dm", state="ready", connection_id="a")
    calls = []

    async def worker_call(name, arguments):
        calls.append((name, arguments))
        return json_result({"request_id": "execution-a", "completed": False})

    async def worker_state():
        return {"pending": True, "uncertain": True, "native_uncertain": False}

    async def run():
        a = broker.connections["a"]
        a.worker = SimpleNamespace(call=worker_call, state=worker_state)
        await broker.connect("host-a", "a.3dm")
        a.state = state
        await broker.connect("host-b", "b.3dm")
        selected = (await broker.connect("host-a", "a.3dm") if route == "connect"
                    else await broker.start_session("a.3dm", "start-a"))
        assert selected["state"] == state and broker.selected_connection_id == "a"
        assert (await broker.call("observe", {})).is_error
        result = await broker.call("script_03-get_execution", {})
        assert not result.is_error
        assert result.structured_content["connection_state"] == state
        assert calls == [("script_03-get_execution", {})]
        assert a.state == state
        a.closing = True
        with pytest.raises(RuntimeError):
            await broker.connect("host-a", "a.3dm")

    asyncio.run(run())


def test_new_connections_bind_independent_workers_and_keep_previous_on_failure(tmp_path):
    """Given two advertised models, connect/observe/switch retains each binding."""
    records = [{"host_id": name, "pid": pid, "process_start_ticks": str(pid)}
               for name, pid in (("a", 101), ("b", 202))]
    controls, workers = {}, {}

    class Control:
        def __init__(self, record):
            self.record = record
            controls[record["host_id"]] = self
            self.token = None

        async def request(self, action, **args):
            name = self.record["host_id"]
            if action == "describe":
                return {"model_path": name + ".3dm", "document_serial": self.record["pid"]}
            if action == "attach":
                assert args["pid"] == self.record["pid"]
                self.token = args["session_token"]
                return {"storage_protocol": 2, "session_dir": str(tmp_path / name),
                        "ready_path": str(tmp_path / name / "ready.json"),
                        "call_root": str(tmp_path / name / "calls"), "port": self.record["pid"],
                        "model_path": name + ".3dm", "pid": self.record["pid"]}
            assert args["session_token"] == self.token
            return {"state": "connected", "detached": True}

        async def close(self):
            pass

    class Worker:
        def __init__(self, binding, connection_id, catalog):
            self.binding = binding
            workers[connection_id] = self

        async def start(self):
            pass

        async def state(self):
            return {"pid": self.binding["pid"] + 1000, "process_start_ticks": "1"}

        async def call(self, name, args):
            assert name == "observe" and args == {}
            return json_result({"model_path": self.binding["model_path"]})

    class Watcher:
        def __init__(self, callback):
            pass

        async def add(self, connection_id, binding):
            pass

        def remove(self, connection_id):
            pass

    async def run():
        broker = Broker(CATALOG, data=tmp_path, host_reader=lambda _: records,
                        control_factory=Control, worker_factory=Worker,
                        watcher_factory=Watcher, contract_check=lambda _: None,
                        lease_factory=lambda *_: SimpleNamespace(close=lambda: None),
                        recovery_store_factory=lambda _: SimpleNamespace(remember=lambda _: None))
        a = await broker.connect("a", "a.3dm")
        assert (await broker.call("observe", {})).structured_content == {"model_path": "a.3dm"}
        b = await broker.connect("b", "b.3dm")
        assert (await broker.call("observe", {})).structured_content == {"model_path": "b.3dm"}
        assert a["connection_id"] != b["connection_id"]
        assert controls["a"].token != controls["b"].token
        assert len(workers) == 2
        failed = await broker.call("connect_02-session", {"host_id": "missing", "model_path": "c.3dm"})
        assert failed.is_error and broker.selected_connection_id == b["connection_id"]
        assert (await broker.connect("a", "a.3dm"))["connection_id"] == a["connection_id"]
        assert len(workers) == 2
        assert (await broker.call("observe", {})).structured_content == {"model_path": "a.3dm"}

    asyncio.run(run())


def test_disconnect_returns_save_exit_guidance_for_the_released_target(tmp_path):
    """Detach reports how to close the right Rhino, without dispatching Save/Exit."""
    from jsonschema import validate
    broker = broker_for(tmp_path)
    calls = []

    async def control_request(name, **kwargs):
        calls.append((name, kwargs))
        return {"detached": True}

    async def worker_close():
        calls.append(("worker_close", {}))

    broker.connections['a'].binding.update(pid=321, model_path='C:\\models\\a.3dm')
    broker.connections['a'].control.request = control_request
    broker.connections['a'].worker = SimpleNamespace(close=worker_close)
    broker.selected_connection_id = 'a'

    async def run():
        response = await broker.call('connect_04-disconnect', {})
        assert not response.is_error
        result = response.structured_content
        output = next(t.output_schema for t in exposed_tools(CATALOG) if t.name == 'connect_04-disconnect')
        validate(result, output)
        assert result['pid'] == 321 and result['model_path'] == 'C:\\models\\a.3dm'
        assert result['released'] is True and result['rhino_closed'] is False
        assert result['worker_closed'] is True
        guide = result['next_step_guide']
        assert 'connect_01-list_up' in guide and 'connect_02-session' in guide and 'connect_05-close_session' in guide
        assert '_Exit' not in guide
        assert calls == [('worker_close', {}), ('detach', {'session_token': 'token-a'})]
        assert broker.selected_connection_id is None and set(broker.connections) == {'b'}

    asyncio.run(run())


def test_unconfirmed_disconnect_never_suggests_closing_rhino(tmp_path):
    broker = broker_for(tmp_path)

    async def pending(*args, **kwargs):
        return {'detached': False}

    broker.connections['a'].control.request = pending
    broker.selected_connection_id = 'a'

    async def run():
        result = await broker.call('connect_04-disconnect', {})
        assert result.is_error
        assert result.structured_content is None
        assert all('_Exit' not in block.text for block in result.content)

    asyncio.run(run())


def test_disconnect_without_process_identity_requires_target_selection_before_close():
    result = json_result({'released': True, 'rhino_closed': False, 'pid': None, 'model_path': None}, 'connect_04-disconnect')
    guide = result.structured_content['next_step_guide']
    assert 'connect_01-list_up' in guide and 'connect_05-close_session' in guide
    assert 'pipeId' not in guide
