"""A selected connection removes repeated routing IDs without sharing bindings."""
import asyncio
from types import SimpleNamespace

import pytest

from external_host import Broker, Connection, exposed_tools, json_result


CATALOG = {"tools": [{"name": "observe", "inputSchema": {
    "type": "object", "properties": {}, "additionalProperties": False}}]}


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


def test_ids_are_optional_and_selection_is_advertised(tmp_path):
    tools, _ = exposed_tools(CATALOG)
    for tool in tools:
        assert "connection_id" not in tool.input_schema.get("required", [])
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
        await broker.call("observe", {"connection_id": "a"})
        assert observed[-1][0] == "a"
        assert broker.selected_connection_id == "b"
        failed = await broker.call("observe", {"connection_id": "stale"})
        assert failed.is_error and len(observed) == 3

    asyncio.run(run())


def test_disconnect_clears_selection_without_falling_back(tmp_path):
    broker = broker_for(tmp_path)

    async def run():
        await broker.connect("host-a", "a.3dm")
        await broker.disconnect()
        assert broker.selected_connection_id is None
        assert set(broker.connections) == {"b"}
        assert (await broker.call("observe", {})).is_error
        await broker.connect("host-b", "b.3dm")
        assert broker.selected_connection_id == "b"

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
        failed = await broker.call("connect", {"host_id": "missing", "model_path": "c.3dm"})
        assert failed.is_error and broker.selected_connection_id == b["connection_id"]
        assert (await broker.connect("a", "a.3dm"))["connection_id"] == a["connection_id"]
        assert len(workers) == 2
        assert (await broker.call("observe", {})).structured_content == {"model_path": "a.3dm"}

    asyncio.run(run())
