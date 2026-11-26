import asyncio
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import codex_host
from codex_host import SessionAdapter
from offline_rhino import (
    ATTACH, CATALOG, CLOSE, DETACH, LIST, OBSERVE, RECOVER, START, OfflineRhino, broker_for, rejected, value,
)
from session_start import RhinoStart
from tools import verify_integration_connection


def test_attachments_route_and_release_by_document(tmp_path):
    async def scenario():
        first = OfflineRhino(tmp_path / "a", "a", pid=2999901)
        second = OfflineRhino(tmp_path / "b", "b", pid=2999902)
        data = tmp_path / "host"
        async with broker_for(data, [first, second]) as broker, broker_for(data, [first, second]) as other:
            assert await value(broker, LIST) == {"targets": [
                {"state": "available", **first.attach_args},
                {"state": "available", **second.attach_args},
            ]}
            connection = await value(broker, ATTACH, **first.attach_args)
            a = connection["connection_id"]
            assert connection == {"connection_id": a, "state": "ready"}
            assert (await value(broker, ATTACH, **first.attach_args))["connection_id"] == a
            assert "owned by another" in await rejected(other, ATTACH, **first.attach_args)
            b = (await value(broker, ATTACH, **second.attach_args))["connection_id"]
            assert b != a
            assert (await value(broker, OBSERVE, connection_id=a))["model"] == "a.3dm"
            assert (await value(broker, OBSERVE, connection_id=b))["model"] == "b.3dm"
            assert "different model" in await rejected(
                broker, ATTACH, host_id="a", model_path=str(second.model),
            )
            broker.connections[a].state = "unconfirmed"
            broker.connections[a].reason = "Inspect the retained execution."
            retained = await value(broker, ATTACH, **first.attach_args)
            assert retained == {"connection_id": a, "state": "unconfirmed", "reason": "Inspect the retained execution."}
            assert (await value(broker, LIST))["targets"][0] == {**retained, **first.attach_args}
            await rejected(broker, OBSERVE, connection_id=a)

            assert await value(broker, DETACH, connection_id=a) == {"released": True}
            assert not first.closed and first.binding is None
            await rejected(broker, OBSERVE, connection_id=a)
            assert (await value(broker, OBSERVE, connection_id=b))["model"] == "b.3dm"
            fresh = await value(other, ATTACH, **first.attach_args)
            assert fresh["connection_id"] != a

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_start_retry_attaches_only_to_launched_process(tmp_path):
    async def scenario():
        target = OfflineRhino(tmp_path / "model", "target", pid=2999903)
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"rhino_exe": str(target.model)}), encoding="utf-8")
        launched = []
        stale = {**target.advertisement, "host_id": "stale", "process_start_ticks": "2"}
        advertisements = [stale]

        def launch(arguments, *, startup_script, **_):
            launched.append((arguments[-1], startup_script))
            return SimpleNamespace(pid=target.advertisement["pid"], poll=lambda: None)

        def starter(model_path, data):
            return RhinoStart(
                model_path, data, settings_path=settings, process_factory=launch,
                host_reader=lambda _: advertisements,
                identity_reader=lambda pid: {"pid": pid, "process_start_ticks": "1"},
                timeout=0,
            )

        async with broker_for(tmp_path / "host", [target], starter_factory=starter) as broker:
            arguments = {"model_path": str(target.model), "request_id": "start-model"}
            pending = await rejected(broker, START, **arguments)
            assert "startup not confirmed" in pending and "request_id=start-model" in pending
            assert all("connection_id" not in row for row in (await value(broker, LIST))["targets"])
            advertisements.append(target.advertisement)
            connected = await value(broker, START, **arguments)
            assert set(connected) == {"connection_id", "state"} and connected["state"] == "ready"
            assert await value(broker, START, **arguments) == connected
            assert launched == [(str(target.model), "_almondconnect")]
            assert target.model.read_bytes() == b"saved model"

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_close_requires_writable_document_and_never_replays_exit(tmp_path):
    async def scenario():
        target = OfflineRhino(tmp_path / "model", "drawing", pid=2999904)
        target.read_only = True
        data = tmp_path / "host"
        async with broker_for(data, [target]) as broker:
            broker.session_closer.exit_factory = target.exit_boundary
            broker.session_closer.wait_seconds = 0
            connected = await value(broker, ATTACH, **target.attach_args)
            connection_id = connected["connection_id"]

            denied = await value(broker, CLOSE, connection_id=connection_id, request_id="read-only")
            assert denied["status"] == "rejected" and set(denied) == {"status", "reason"}
            assert target.model.read_bytes() == b"saved model"
            assert target.exit_count == 0

            target.read_only = False
            args = {"connection_id": connection_id, "request_id": "close-model"}
            pending = await value(broker, CLOSE, **args)
            assert pending["status"] == "unconfirmed" and set(pending) == {"status", "reason"}
            await rejected(broker, DETACH, connection_id=connection_id)
            await rejected(broker, OBSERVE, connection_id=connection_id)
            target.closed = True
            complete = await value(broker, CLOSE, **args)
            assert complete == {"status": "completed"}

        async with broker_for(data, [target]) as restarted:
            assert await value(restarted, CLOSE, **args) == complete
            await rejected(restarted, CLOSE, **{**args, "connection_id": "b" * 32})
        assert target.worker.save_count == target.exit_count == 1

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_display_mode_menu_keeps_fields_available(monkeypatch, tmp_path):
    current_view = "capture_03-current_view"
    inspection = "capture_02-inspection"
    catalog = {"tools": [*CATALOG["tools"], *(
        {"name": name, "inputSchema": {"type": "object", "properties": {
            "views": {"items": {}}} if name == inspection else {}}}
        for name in (current_view, inspection)
    )]}
    initial_guid, later_guid = uuid4().hex, str(uuid4())
    hosts = []
    monkeypatch.setattr(codex_host, "read_hosts", lambda _: hosts)
    adapter = SessionAdapter(catalog, data=tmp_path)
    fields = {tool.name: tool.input_schema["properties"] for tool in adapter.tools}
    assert fields[current_view]["display_mode"]["type"] == "string"
    assert fields[inspection]["views"]["items"]["properties"]["display_mode"]["type"] == "string"

    async def check_new_mode():
        async def accept(name, args):
            assert name == current_view and args["display_mode"] == later_guid
            return SimpleNamespace(is_error=False)

        adapter.broker = SimpleNamespace(call=accept)
        assert not (await adapter.call(current_view, {
            "connection_id": uuid4().hex, "display_mode": later_guid,
        })).is_error

    hosts.append({"display_mode_ids": [initial_guid]})
    next_adapter = SessionAdapter(catalog, data=tmp_path)
    next_fields = next(tool.input_schema["properties"] for tool in next_adapter.tools
                       if tool.name == current_view)
    assert next_fields["display_mode"]["examples"] == [str(UUID(initial_guid))]
    assert "enum" not in next_fields["display_mode"]
    asyncio.run(check_new_mode())


def test_invalid_local_input_never_opens_broker(monkeypatch, tmp_path):
    monkeypatch.setattr(codex_host, "read_hosts", lambda _: [])
    adapter = SessionAdapter(CATALOG, data=tmp_path)
    disallowed = asyncio.run(rejected(adapter, LIST, host_id="unexpected"))
    assert "host_id" in disallowed and adapter.broker is None
    private_flag = asyncio.run(rejected(adapter, RECOVER, connection_id="a" * 32, _initial_result=True))
    assert "_initial_result" in private_flag and adapter.broker is None


def test_integration_probe_uses_exact_advertisement(monkeypatch, tmp_path):
    async def scenario():
        prior = OfflineRhino(tmp_path / "prior", "prior", pid=2999905)
        target = OfflineRhino(tmp_path / "model", "drawing", pid=2999906)
        # A listing can include other Rhino windows; only the exact start identity qualifies.
        monkeypatch.setattr(verify_integration_connection, "read_hosts", lambda _: [
            {**prior.advertisement, "pid": 2999906, "process_start_ticks": "0"},
            target.advertisement,
        ])
        async with broker_for(tmp_path / "host", [prior, target]) as broker:
            client = SimpleNamespace(call_tool=broker.call)
            result = await verify_integration_connection.verify_connection(
                client, target.advertisement["pid"], target.advertisement["process_start_ticks"], target.model,
            )
            assert result["host_id"] == target.advertisement["host_id"] and result["released"]
            assert target.worker is not None and target.binding is None and prior.worker is None

    asyncio.run(asyncio.wait_for(scenario(), 10))
