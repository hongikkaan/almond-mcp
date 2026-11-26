import asyncio
import json
from types import SimpleNamespace

from offline_rhino import (
    ATTACH, CLOSE, DETACH, LIST, OBSERVE, START, OfflineRhino, broker_for, rejected, value,
)
from session_start import RhinoStart


def test_attachments_route_and_release_by_document(tmp_path):
    async def scenario():
        first = OfflineRhino(tmp_path / "a", "a", pid=2999901)
        second = OfflineRhino(tmp_path / "b", "b", pid=2999902)
        data = tmp_path / "host"
        async with broker_for(data, [first, second]) as broker, broker_for(data, [first, second]) as other:
            a = (await value(broker, ATTACH, **first.attach_args))["connection_id"]
            assert (await value(broker, ATTACH, **first.attach_args))["connection_id"] == a
            assert "owned by another" in await rejected(other, ATTACH, **first.attach_args)
            b = (await value(broker, ATTACH, **second.attach_args))["connection_id"]
            assert b != a
            assert (await value(broker, OBSERVE, connection_id=a))["model"] == "a.3dm"
            assert (await value(broker, OBSERVE, connection_id=b))["model"] == "b.3dm"
            assert "different model" in await rejected(
                broker, ATTACH, host_id="a", model_path=str(second.model),
            )

            released = await value(broker, DETACH, connection_id=a)
            assert released["model_path"] == str(first.model)
            assert released["released"] and released["worker_closed"] and not released["rhino_closed"]
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
            assert "startup not confirmed" in await rejected(broker, START, **arguments)
            assert not (await value(broker, LIST))["connections"]
            advertisements.append(target.advertisement)
            connected = await value(broker, START, **arguments)
            assert connected["host_id"] == "target"
            assert (await value(broker, START, **arguments))["connection_id"] == connected["connection_id"]
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
            assert denied["status"] == "rejected" and not denied["saved"]
            assert target.model.read_bytes() == b"saved model"
            assert target.exit_count == 0

            target.read_only = False
            args = {"connection_id": connection_id, "request_id": "close-model"}
            pending = await value(broker, CLOSE, **args)
            assert pending["status"] == "unconfirmed" and pending["saved"], pending["reason"]
            assert not pending["released"]
            await rejected(broker, DETACH, connection_id=connection_id)
            await rejected(broker, OBSERVE, connection_id=connection_id)
            target.closed = True
            complete = await value(broker, CLOSE, **args)
            assert complete["status"] == "completed"
            assert complete["rhino_closed"] and complete["worker_closed"] and complete["released"]

        async with broker_for(data, [target]) as restarted:
            assert await value(restarted, CLOSE, **args) == complete
            await rejected(restarted, CLOSE, **{**args, "connection_id": "b" * 32})
        assert target.worker.save_count == target.exit_count == 1

    asyncio.run(asyncio.wait_for(scenario(), 10))
