"""Cancellation through the external tool adapter, with transport fixtures."""
import asyncio

import pytest

from external_host import Broker, Connection, SessionAdapter, json_result


TOOL = "fixture_observe"
CATALOG = {"tools": [{"name": TOOL, "inputSchema": {"type": "object", "properties": {}}}]}


class Control:
    def __init__(self):
        self.calls = []
        self.reservation = None
        self.pauses = {}
        self.lost_reply = None
        self.invalidated = False

    def pause(self, action):
        arrived, release = asyncio.Event(), asyncio.Event()
        self.pauses[action] = (arrived, release)
        return arrived, release

    async def request(self, action, **fields):
        self.calls.append(action)
        if action == "begin":
            assert self.reservation is None
            self.reservation = fields["request_id"]
        elif action == "end":
            assert self.reservation == fields["request_id"]
            self.reservation = None
        elif action == "fail":
            self.invalidated = True
        elif action not in {"status", "detach"}:
            raise AssertionError(f"Unexpected control action: {action}")
        if pause := self.pauses.pop(action, None):
            arrived, release = pause
            arrived.set()
            await release.wait()
        if action == self.lost_reply:
            raise TimeoutError(f"Lost {action} acknowledgement")
        if action == "status":
            return {"state": "unconfirmed_or_running", "reason": ""}
        return {"detached": True} if action == "detach" else {"ok": True}

    async def close(self):
        pass


class Worker:
    def __init__(self):
        self.calls = []
        self.pause = False
        self.entered, self.release, self.stopping = (
            asyncio.Event(), asyncio.Event(), asyncio.Event())
        self.completion = {"native_uncertain": False}

    async def call(self, name, args):
        self.calls.append(name)
        self.entered.set()
        if self.pause:
            await self.release.wait()
        return json_result({"status": "ok"})

    async def state(self):
        return self.completion

    def request_stop(self):
        self.stopping.set()

    async def close(self):
        pass


def session(data):
    control, worker = Control(), Worker()
    adapter = SessionAdapter(CATALOG, data=data)
    broker = Broker(CATALOG, data=data)
    conn = Connection("connection", "host", control, "fixture-token", worker=worker, state="ready")
    broker.connections[conn.connection_id] = conn
    broker.host_connections[conn.host_id] = conn.connection_id
    broker.selected_connection_id = conn.connection_id
    adapter.broker = broker
    return adapter, broker, conn, control, worker


async def arrived(event):
    await asyncio.wait_for(event.wait(), 2)


async def abandon(caller):
    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller


async def settle(broker):
    while broker.background:
        await asyncio.wait_for(asyncio.gather(*broker.background, return_exceptions=True), 2)


async def connection_status(adapter):
    result = await adapter.call("connect_01-list_up", {})
    assert not result.is_error
    return result.structured_content["connections"]


async def close_owner(broker, conn, worker, owner_event):
    if owner_event == "shutdown":
        shutdown = asyncio.create_task(broker.close())
        await arrived(worker.stopping)
        return shutdown
    broker.binding_changed(conn.connection_id, "Bound document changed")
    return None


def test_cancel_during_begin_releases_unused_reservation_and_keeps_connection(tmp_path):
    async def run():
        adapter, broker, _, control, worker = session(tmp_path)
        entered, release = control.pause("begin")
        caller = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(entered)
        await abandon(caller)
        release.set()
        await settle(broker)

        state, = await connection_status(adapter)
        assert state["state"] == "ready" and not state["in_flight"]
        assert control.reservation is None and not control.invalidated
        assert worker.calls == []
        assert not (await adapter.call(TOOL, {})).is_error
        assert worker.calls == [TOOL]

    asyncio.run(run())


def test_cancel_while_queued_creates_no_reservation(tmp_path):
    async def run():
        adapter, broker, _, control, worker = session(tmp_path)
        worker.pause = True
        owner = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(worker.entered)
        queued = asyncio.create_task(adapter.call(TOOL, {}))
        # Let the caller reach the shielded queue while the owner holds it.
        await asyncio.sleep(0)
        assert len(broker.background) == 2
        await abandon(queued)
        worker.release.set()
        assert not (await owner).is_error
        await settle(broker)

        assert worker.calls == [TOOL]
        assert control.calls == ["begin", "end"]
        state, = await connection_status(adapter)
        assert state["state"] == "ready"

    asyncio.run(run())


@pytest.mark.parametrize("lost_reply", ["begin", "end"])
def test_cancel_keeps_reservation_unconfirmed_when_acknowledgement_is_lost(tmp_path, lost_reply):
    async def run():
        adapter, broker, _, control, worker = session(tmp_path)
        control.lost_reply = lost_reply
        entered, release = control.pause("begin")
        caller = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(entered)
        await abandon(caller)
        release.set()
        await settle(broker)

        state, = await connection_status(adapter)
        assert state["state"] == "unconfirmed"
        assert control.invalidated and worker.calls == []
        assert (await adapter.call(TOOL, {})).is_error
        assert worker.calls == []

    asyncio.run(run())


def test_cancel_during_binding_status_prevents_dispatch(tmp_path):
    async def run():
        adapter, broker, conn, control, worker = session(tmp_path)
        in_begin, release_begin = control.pause("begin")
        in_status, release_status = control.pause("status")
        caller = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(in_begin)
        broker.binding_changed(conn.connection_id, None)
        release_begin.set()
        await arrived(in_status)
        await abandon(caller)
        release_status.set()
        await settle(broker)

        assert worker.calls == []
        state, = await connection_status(adapter)
        assert state["state"] == "ready" and not state["in_flight"]
        assert control.reservation is None and not control.invalidated

    asyncio.run(run())


@pytest.mark.parametrize("owner_event", ["shutdown", "document_changed"])
def test_cancel_does_not_reopen_connection_while_reservation_release_is_in_flight(tmp_path, owner_event):
    async def run():
        adapter, broker, conn, control, worker = session(tmp_path)
        in_begin, release_begin = control.pause("begin")
        in_end, release_end = control.pause("end")
        in_detach, release_detach = control.pause("detach")
        caller = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(in_begin)
        await abandon(caller)
        release_begin.set()
        await arrived(in_end)
        shutdown = await close_owner(broker, conn, worker, owner_event)
        assert conn.closing
        release_end.set()
        await arrived(in_detach)

        follow_up = asyncio.create_task(adapter.call(TOOL, {}))
        try:
            state, = await connection_status(adapter)
            assert state["state"] != "ready"
            assert worker.calls == []
            assert not control.invalidated
        finally:
            release_detach.set()
            if shutdown:
                await asyncio.wait_for(shutdown, 2)
            await settle(broker)
            assert (await asyncio.wait_for(follow_up, 2)).is_error
        assert await connection_status(adapter) == []

    asyncio.run(run())


@pytest.mark.parametrize("owner_event", ["shutdown", "document_changed"])
def test_cancel_after_owner_starts_closing_preserves_owner_state(tmp_path, owner_event):
    async def run():
        adapter, broker, conn, control, worker = session(tmp_path)
        worker.pause = True
        caller = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(worker.entered)
        shutdown = await close_owner(broker, conn, worker, owner_event)
        owner_state, owner_reason = conn.state, conn.reason
        await abandon(caller)
        state, = await connection_status(adapter)
        assert (state["state"], state["reason"]) == (owner_state, owner_reason)
        worker.release.set()
        if shutdown:
            await asyncio.wait_for(shutdown, 2)
        await settle(broker)
        assert worker.calls == [TOOL]
        assert await connection_status(adapter) == []

    asyncio.run(run())


@pytest.mark.parametrize("native_unknown", [False, True])
def test_cancel_after_dispatch_keeps_unseen_outcome_from_being_replayed(tmp_path, native_unknown):
    async def run():
        adapter, broker, _, control, worker = session(tmp_path)
        if native_unknown:
            worker.pause = True
            worker.completion = {"pending": True, "native_uncertain": True}
            entered, release = worker.entered, worker.release
        else:
            entered, release = control.pause("end")
        caller = asyncio.create_task(adapter.call(TOOL, {}))
        await arrived(entered)
        await abandon(caller)
        release.set()
        await settle(broker)

        state, = await connection_status(adapter)
        assert state["state"] == "unconfirmed"
        assert control.invalidated is native_unknown
        assert (await adapter.call(TOOL, {})).is_error
        assert worker.calls == [TOOL]

    asyncio.run(run())
