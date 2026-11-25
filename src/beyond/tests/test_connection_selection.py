"""Explicit connection routing keeps each document and its recovery evidence isolated."""
import asyncio
import os
from types import SimpleNamespace

import pytest

from external_host import Broker, Connection, StartAttempt, UNBOUND_TOOLS, exposed_tools, json_result


A, B = "a" * 32, "b" * 32


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

    return Connection({"a": A, "b": B}[name], "host-" + name, SimpleNamespace(request=detach, close=close),
                      "token-" + name, binding={"model_path": name + ".3dm", "session_dir": str(root / name)}, state="ready")


def broker_for(tmp_path):
    broker = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None,
                    host_reader=lambda _: [], recovery_store_factory=lambda _: None)
    broker.connections = {conn.connection_id: conn for conn in (connection(name, tmp_path) for name in ("a", "b"))}
    broker.host_connections = {"host-a": A, "host-b": B}
    return broker


def test_routed_schemas_require_connection_ids_and_list_keeps_its_output(tmp_path):
    tools = exposed_tools(CATALOG)
    for tool in tools:
        assert ("connection_id" in tool.input_schema["required"]) == (tool.name not in UNBOUND_TOOLS)
    broker = broker_for(tmp_path)

    async def run():
        await broker.connect("host-a", "a.3dm")
        listing = await broker.list_connections()
        assert listing["selected_connection_id"] is None
        assert {c["connection_id"] for c in listing["connections"]} == {A, B}
        with pytest.raises(RuntimeError, match="different model"):
            await broker.connect("host-b", "a.3dm")
        assert set(broker.connections) == {A, B}

    asyncio.run(run())


def test_queued_calls_remain_bound_to_their_connection(tmp_path):
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
        first = asyncio.create_task(broker.call("observe", {"connection_id": A}))
        await arrived.wait()
        await broker.connect("host-b", "b.3dm")
        second = asyncio.create_task(broker.call("observe", {"connection_id": B}))
        release.set()
        assert not (await first).is_error
        assert not (await second).is_error
        assert observed == [(A, "token-a", {}), (B, "token-b", {})]
        failed = await broker.call("observe", {"connection_id": "a"})
        assert failed.is_error and len(observed) == 2

    asyncio.run(run())


def test_execution_request_requires_its_original_connection_after_restart(tmp_path):
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
    broker.recovery_store.remember(binding, connection_id=A)
    a, b = (connection(name, tmp_path) for name in ("a", "b"))
    a.token, a.binding = token, binding
    broker.connections = {A: a, B: b}
    broker.host_connections = {"host-a": A, "host-b": B}
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
        route = dict(args, connection_id=A)
        live = await broker.call("script_03-get_execution", route)
        assert live.structured_content["connection_state"] == "ready"
        assert calls == [("script_03-get_execution", args)]
        missing = await broker.call("script_03-get_execution", dict(args, connection_id=B))
        assert missing.is_error
        assert calls == [("script_03-get_execution", args)]

        restarted = Broker(CATALOG, data=broker.data, contract_check=lambda _: None)
        retained = await restarted.call("script_03-get_execution", route)
        assert retained.structured_content["request_id"] == request_id
        assert retained.structured_content["target_identity"] == target
        assert retained.structured_content["completion_state"] == "not_started"
        assert retained.structured_content["recovery_only"] is True
        assert not restarted.connections

    asyncio.run(run())


def test_disconnect_releases_only_the_specified_connection(tmp_path):
    broker = broker_for(tmp_path)

    async def run():
        assert (await broker.call("connect_04-disconnect", {})).is_error
        assert set(broker.connections) == {A, B}
        assert not (await broker.call("connect_04-disconnect", {"connection_id": A})).is_error
        assert set(broker.connections) == {B}
        assert (await broker.call("observe", {"connection_id": A})).is_error
        assert (await broker.connect("host-b", "b.3dm"))["connection_id"] == B

    asyncio.run(run())


@pytest.mark.parametrize("state", ["recovering", "unconfirmed"])
@pytest.mark.parametrize("route", ["connect", "start_session"])
def test_reconnecting_for_recovery_keeps_normal_calls_blocked(tmp_path, state, route):
    """Reopening a connection for recovery never dispatches new work."""
    broker = broker_for(tmp_path)
    broker.starts["start-a"] = StartAttempt("a.3dm", state="ready", connection_id=A)
    calls = []

    async def worker_call(name, arguments):
        calls.append((name, arguments))
        return json_result({"request_id": "execution-a", "completed": False})

    async def worker_state():
        return {"pending": True, "uncertain": True, "native_uncertain": False}

    async def run():
        a = broker.connections[A]
        a.worker = SimpleNamespace(call=worker_call, state=worker_state)
        await broker.connect("host-a", "a.3dm")
        a.state = state
        await broker.connect("host-b", "b.3dm")
        selected = (await broker.connect("host-a", "a.3dm") if route == "connect"
                    else await broker.start_session("a.3dm", "start-a"))
        assert selected["state"] == state and selected["connection_id"] == A
        assert (await broker.call("observe", {"connection_id": A})).is_error
        result = await broker.call("script_03-get_execution", {"connection_id": A})
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
        locators = {}
        def remember(binding, *, connection_id=None):
            locators[binding["model_path"]] = connection_id

        broker = Broker(CATALOG, data=tmp_path, host_reader=lambda _: records,
                        control_factory=Control, worker_factory=Worker,
                        watcher_factory=Watcher, contract_check=lambda _: None,
                        lease_factory=lambda *_: SimpleNamespace(close=lambda: None),
                        recovery_store_factory=lambda _: SimpleNamespace(remember=remember))
        def routing(connection):
            return {"connection_id": connection["connection_id"]}

        response = await broker.call("connect_02-session", {"host_id": "a", "model_path": "a.3dm"})
        a = response.structured_content
        broker.starts["start-a"] = StartAttempt("a.3dm", state="ready", connection_id=a["connection_id"])
        resumed = await broker.call("connect_03-start_session", {"request_id": "start-a", "model_path": "a.3dm"})
        for result in (a, resumed.structured_content):
            assert (result["model_path"], result["connection_id"]) == ("a.3dm", a["connection_id"])
            assert "현재 대화의 변수에 함께 저장" in result["message"]
            assert "후속 호출마다 connection_id를 전달" in result["message"]
        assert (await broker.call("observe", routing(a))).structured_content == {"model_path": "a.3dm"}
        b = await broker.connect("b", "b.3dm")
        assert (await broker.call("observe", routing(b))).structured_content == {"model_path": "b.3dm"}
        assert locators == {"a.3dm": routing(a).get("connection_id"), "b.3dm": routing(b).get("connection_id")}
        assert a["connection_id"] != b["connection_id"]
        assert controls["a"].token != controls["b"].token
        assert len(workers) == 2
        failed = await broker.call("connect_02-session", {"host_id": "missing", "model_path": "c.3dm"})
        assert failed.is_error and set(broker.connections) == {a["connection_id"], b["connection_id"]}
        for name in ("observe", "connect_04-disconnect", "connect_05-close_session"):
            missing = await broker.call(name, {})
            assert missing.is_error and missing.content[0].text == "connection_id가 지정되지 않았습니다"
        assert (await broker.call("observe", {"connection_id": "f" * 32})).is_error
        results = await asyncio.gather(broker.call("observe", routing(a)), broker.call("observe", routing(b)))
        assert [r.structured_content["model_path"] for r in results] == ["a.3dm", "b.3dm"]
        assert (await broker.connect("a", "a.3dm"))["connection_id"] == a["connection_id"]
        assert len(workers) == 2
        assert (await broker.call("observe", routing(a))).structured_content == {"model_path": "a.3dm"}

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

    broker.connections[A].binding.update(pid=321, model_path='C:\\models\\a.3dm')
    broker.connections[A].control.request = control_request
    broker.connections[A].worker = SimpleNamespace(close=worker_close)

    async def run():
        response = await broker.call('connect_04-disconnect', {'connection_id': A})
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
        assert set(broker.connections) == {B}

    asyncio.run(run())


def test_unconfirmed_disconnect_never_suggests_closing_rhino(tmp_path):
    broker = broker_for(tmp_path)

    async def pending(*args, **kwargs):
        return {'detached': False}

    broker.connections[A].control.request = pending

    async def run():
        result = await broker.call('connect_04-disconnect', {'connection_id': A})
        assert result.is_error
        assert result.structured_content is None
        assert all('_Exit' not in block.text for block in result.content)

    asyncio.run(run())


def test_disconnect_without_process_identity_requires_target_selection_before_close():
    result = json_result({'released': True, 'rhino_closed': False, 'pid': None, 'model_path': None}, 'connect_04-disconnect')
    guide = result.structured_content['next_step_guide']
    assert 'connect_01-list_up' in guide and 'connect_05-close_session' in guide
    assert 'pipeId' not in guide
