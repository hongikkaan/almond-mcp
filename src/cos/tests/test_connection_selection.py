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
