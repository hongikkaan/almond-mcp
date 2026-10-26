"""Disposable workers only: exercise the actual broker's concurrency and teardown."""
import asyncio
from contextlib import ExitStack
import unittest

import mcp_types as types
from cos_host import Broker


CATALOG = {"tools": [{
    "name": "execute", "description": "Fixture",
    "inputSchema": {"type": "object", "properties": {"script": {"type": "string"}},
                    "required": ["script"]},
}]}


class Rig:
    def __init__(self):
        self.records = [{"host_id": name, "pid": index, "process_start_ticks": str(index)}
                        for index, name in enumerate(("one", "two"), 1)]
        self.controls = {}
        self.workers = []
        self.control_gates = {}
        self.start_gate = None
        self.invalidate_on_watch = False
        self.broker = Broker(CATALOG, control_factory=self.control,
                             worker_factory=self.worker, host_reader=lambda _: self.records,
                             contract_check=lambda _: None, call_timeout=1,
                             lease_factory=lambda *_: ExitStack(),
                             watcher_factory=lambda notify: FakeWatcher(self, notify))

    def control(self, record):
        control = FakeControl(self, record["host_id"])
        self.controls[control.host] = control
        return control

    def worker(self, binding, connection_id, catalog):
        worker = FakeWorker(self)
        self.workers.append(worker)
        return worker

    async def connect(self, name="one"):
        return await self.broker.connect(name, name + ".3dm")

    async def call(self, connection):
        return await self.broker.call("execute",
                                      {"connection_id": connection["connection_id"], "script": "fixture"})

    def invalidate(self, connection):
        conn = self.broker.connections.get(connection["connection_id"])
        if conn is not None:
            conn.control.invalid = True
        self.broker.watcher.notify(connection["connection_id"], None)


class FakeWatcher:
    def __init__(self, rig, notify):
        self.rig, self.notify = rig, notify
        self.bindings = {}
        self.closed = False

    async def add(self, key, binding):
        self.bindings[key] = binding
        if self.rig.invalidate_on_watch:
            self.notify(key, "Invalidated during attach")

    def remove(self, key):
        self.bindings.pop(key, None)

    async def close(self):
        self.closed = True
        self.bindings.clear()


class FakeControl:
    def __init__(self, rig, host):
        self.rig, self.host = rig, host
        self.actions = []
        self.seen = {}
        self.closed = 0
        self.busy = False
        self.invalid = False

    async def request(self, action, **fields):
        self.actions.append(action)
        self.seen.setdefault(action, asyncio.Event()).set()
        if action == "begin":
            if self.invalid:
                raise RuntimeError("Rhino binding invalidated before dispatch.")
            self.busy = True
        if action in self.rig.control_gates:
            await self.rig.control_gates[action].wait()
        if action == "describe":
            return {"model_path": self.host + ".3dm", "document_serial": "42"}
        if action == "attach":
            return {"storage_protocol": 2, "storage": "fixture", "temp": "fixture/tmp",
                    "session_dir": "fixture/.sessions/" + fields["session_token"],
                    "ready_path": "fixture/.sessions/" + fields["session_token"] + "/ready.json",
                    "call_root": "fixture/tmp/calls/" + fields["session_token"],
                    "model_path": self.host + ".3dm",
                    "label": self.host, "pid": 1, "port": 1, "token": fields["session_token"]}
        if action == "detach":
            if self.busy:
                raise RuntimeError("Fixture Rhino retains locks: outcome unconfirmed.")
            return {"detached": True}
        if action == "status":
            return {"state": "unconfirmed_or_running" if self.busy else "cleanup_pending" if self.invalid else "connected",
                    "reason": "Rhino disconnect fixture" if self.invalid else ""}
        if action == "end":
            self.busy = False
        return {"accepted": True}

    async def close(self):
        self.closed += 1

    async def wait_for(self, action):
        await asyncio.wait_for(self.seen.setdefault(action, asyncio.Event()).wait(), 2)


class FakeWorker:
    def __init__(self, rig):
        self.rig = rig
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.stop = asyncio.Event()
        self.started = asyncio.Event()
        self.active = self.maximum = self.calls = self.closed = 0
        self.uncertain = False
        self.result = types.CallToolResult.model_validate({
            "content": [
                {"type": "text", "text": "fixture"},
                {"type": "image", "mimeType": "image/png",
                 "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="},
            ],
            "structuredContent": {"fixture": 7}, "isError": True, "_meta": {"fixture": "preserved"},
        })

    async def start(self):
        self.started.set()
        if self.rig.start_gate is not None:
            await self.stop.wait()
            raise RuntimeError("Fixture stopped during startup.")

    async def call(self, name, arguments):
        self.active += 1
        self.calls += 1
        self.maximum = max(self.maximum, self.active)
        self.entered.set()
        ready = asyncio.create_task(self.release.wait())
        stopped = asyncio.create_task(self.stop.wait())
        try:
            done, _ = await asyncio.wait({ready, stopped}, return_when=asyncio.FIRST_COMPLETED)
            if stopped in done:
                raise RuntimeError("Fixture worker stopped.")
            return self.result
        finally:
            ready.cancel()
            stopped.cancel()
            await asyncio.gather(ready, stopped, return_exceptions=True)
            self.active -= 1

    async def state(self):
        return {"pending": self.active > 0, "uncertain": self.uncertain,
                "pid": 123, "process_start_ticks": "123"}

    def request_stop(self):
        self.stop.set()

    async def close(self):
        self.request_stop()
        self.closed += 1


class BrokerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.rig = Rig()

    async def asyncTearDown(self):
        await asyncio.wait_for(self.rig.broker.close(), 3)

    async def test_selection_and_connection_return_the_model_filename(self):
        listing = await self.rig.broker.list_connections()
        self.assertIn("Use the explicit connection_id from connect", listing["instructions"])
        target = next(t for t in listing["targets"] if t["host_id"] == "one")
        self.assertEqual(target["model_path"], "one.3dm")
        self.assertEqual(target["model_filename"], "one.3dm")

        connection = await self.rig.connect()
        self.assertEqual(connection["model_path"], target["model_path"])
        self.assertEqual(connection["model_filename"], target["model_filename"])
        active = await self.rig.broker.list_connections()
        self.assertEqual(active["connections"][0]["model_filename"], "one.3dm")

    async def test_different_connections_execute_in_parallel_and_preserve_results(self):
        one, two = await self.rig.connect(), await self.rig.connect("two")
        self.assertNotEqual(one["artifact_dir"], two["artifact_dir"])
        for connection in (one, two):
            self.assertTrue(connection["artifact_dir"].startswith("fixture/tmp/calls/"))
        tasks = [asyncio.create_task(self.rig.call(c)) for c in (one, two)]
        await asyncio.wait_for(asyncio.gather(*(w.entered.wait() for w in self.rig.workers)), 1)
        self.assertEqual([w.active for w in self.rig.workers], [1, 1])
        for worker in self.rig.workers:
            worker.release.set()
        results = await asyncio.gather(*tasks)
        for result, worker in zip(results, self.rig.workers):
            self.assertIs(result, worker.result)
            self.assertTrue(result.is_error)
            self.assertEqual(len(result.content), 2)

    async def test_one_connection_serializes_calls(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        first = asyncio.create_task(self.rig.call(one))
        await worker.entered.wait()
        second = asyncio.create_task(self.rig.call(one))
        await asyncio.sleep(0)
        self.assertEqual(worker.calls, 1)
        worker.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(worker.calls, 2)
        self.assertEqual(worker.maximum, 1)

    async def test_queue_timeout_does_not_dispatch_or_poison_the_running_call(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        self.rig.broker.queue_timeout = 0.02
        first = asyncio.create_task(self.rig.call(one))
        await worker.entered.wait()
        try:
            result = await asyncio.wait_for(self.rig.call(one), 0.3)
            self.assertTrue(result.is_error)
            self.assertIn("No operation", result.content[0].text)
            self.assertEqual(worker.calls, 1)
            self.assertEqual(self.rig.broker.connections[one["connection_id"]].state, "ready")
            self.assertNotIn("fail", self.rig.controls["one"].actions)
        finally:
            worker.release.set()
            await first

    async def test_stale_id_never_creates_a_worker_or_control(self):
        result = await self.rig.call({"connection_id": "expired"})
        self.assertTrue(result.is_error)
        self.assertFalse(self.rig.controls)
        self.assertFalse(self.rig.workers)

    async def test_timeout_retains_busy_and_blocks_following_call(self):
        one = await self.rig.connect()
        self.rig.broker.call_timeout = 0.03
        result = await self.rig.call(one)
        self.assertTrue(result.is_error)
        self.assertNotIn("end", self.rig.controls["one"].actions)
        self.assertIn("fail", self.rig.controls["one"].actions)
        self.assertTrue((await self.rig.call(one)).is_error)
        self.assertEqual(self.rig.workers[0].calls, 1)

    async def test_uncertain_native_reply_never_clears_busy(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        worker.uncertain = True
        worker.release.set()
        self.assertTrue((await self.rig.call(one)).is_error)
        self.assertNotIn("end", self.rig.controls["one"].actions)

    async def test_canceled_caller_keeps_real_call_until_completion(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        call = asyncio.create_task(self.rig.call(one))
        await worker.entered.wait()
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call
        self.assertEqual(worker.active, 1)
        worker.release.set()
        await asyncio.gather(*list(self.rig.broker.background))
        conn = self.rig.broker.connections[one["connection_id"]]
        self.assertEqual(conn.state, "unconfirmed")
        self.assertFalse(conn.in_flight)
        self.assertIn("end", self.rig.controls["one"].actions)
        self.assertTrue((await self.rig.call(one)).is_error)
        self.assertEqual(worker.calls, 1)

    async def test_cancel_during_begin_does_not_dispatch(self):
        one = await self.rig.connect()
        gate = self.rig.control_gates["begin"] = asyncio.Event()
        call = asyncio.create_task(self.rig.call(one))
        await self.rig.controls["one"].wait_for("begin")
        call.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await call
        gate.set()
        await asyncio.gather(*list(self.rig.broker.background), return_exceptions=True)
        self.assertEqual(self.rig.workers[0].calls, 0)
        self.assertIn("end", self.rig.controls["one"].actions)

    async def test_canceled_queued_call_never_dispatches_or_poison_running_call(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        first = asyncio.create_task(self.rig.call(one))
        await worker.entered.wait()
        second = asyncio.create_task(self.rig.call(one))
        await asyncio.sleep(0)
        second.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await second
        worker.release.set()
        await first
        await asyncio.gather(*list(self.rig.broker.background), return_exceptions=True)
        self.assertEqual(worker.calls, 1)
        self.assertEqual(self.rig.broker.connections[one["connection_id"]].state, "ready")
        await self.rig.call(one)
        self.assertEqual(worker.calls, 2)

    async def test_close_during_attach_cannot_leave_orphan_worker(self):
        gate = self.rig.control_gates["attach"] = asyncio.Event()
        connecting = asyncio.create_task(self.rig.connect())
        await asyncio.sleep(0)
        control = self.rig.controls["one"]
        await control.wait_for("attach")
        closing = asyncio.create_task(self.rig.broker.close())
        await asyncio.sleep(0)
        gate.set()
        results = await asyncio.wait_for(asyncio.gather(connecting, closing, return_exceptions=True), 2)
        self.assertIsInstance(results[0], RuntimeError)
        self.assertFalse(self.rig.workers)
        self.assertFalse(self.rig.broker.connections)
        self.assertEqual(control.actions.count("detach"), 1)
        self.assertEqual(control.closed, 1)

    async def test_close_during_worker_start_cannot_leave_orphan_worker(self):
        self.rig.start_gate = True
        connecting = asyncio.create_task(self.rig.connect())
        await asyncio.sleep(0)
        worker = self.rig.workers[0]
        await worker.started.wait()
        closing = asyncio.create_task(self.rig.broker.close())
        results = await asyncio.wait_for(asyncio.gather(connecting, closing, return_exceptions=True), 2)
        self.assertIsInstance(results[0], RuntimeError)
        self.assertEqual(worker.closed, 1)
        self.assertFalse(self.rig.broker.connections)
        self.assertEqual(self.rig.controls["one"].actions.count("detach"), 1)

    async def test_close_during_native_call_stops_worker_before_dispose_lock(self):
        one = await self.rig.connect()
        call = asyncio.create_task(self.rig.call(one))
        await self.rig.workers[0].entered.wait()
        await asyncio.wait_for(self.rig.broker.close(), 2)
        self.assertTrue((await call).is_error)
        self.assertEqual(self.rig.workers[0].closed, 1)
        self.assertNotIn("end", self.rig.controls["one"].actions)
        self.assertFalse(self.rig.broker.connections)

    async def test_disconnect_refuses_active_work(self):
        one = await self.rig.connect()
        call = asyncio.create_task(self.rig.call(one))
        await self.rig.workers[0].entered.wait()
        with self.assertRaisesRegex(RuntimeError, "still running"):
            await self.rig.broker.disconnect(one["connection_id"])
        self.assertEqual(self.rig.workers[0].closed, 0)
        self.rig.workers[0].release.set()
        await call
        result = await self.rig.broker.disconnect(one["connection_id"])
        self.assertTrue(result["released"])
        self.assertFalse(result["rhino_closed"])

    async def test_rhino_disconnect_cleans_idle_connection_without_another_tool_call(self):
        one, two = await self.rig.connect(), await self.rig.connect("two")
        conn = self.rig.broker.connections[one["connection_id"]]
        self.rig.invalidate(one)
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertTrue(conn.cleanup["released"])
        self.assertEqual(self.rig.workers[0].closed, 1)
        self.assertEqual(self.rig.workers[1].closed, 0)
        self.assertIn(two["connection_id"], self.rig.broker.connections)
        self.assertFalse(self.rig.workers[0].calls)

    async def test_unrelated_file_events_are_coalesced_and_do_not_disconnect(self):
        one = await self.rig.connect()
        control = self.rig.controls["one"]
        control.actions.clear()
        for _ in range(20):
            self.rig.broker.watcher.notify(one["connection_id"], None)
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertEqual(control.actions, ["status"])
        self.assertEqual(self.rig.workers[0].closed, 0)
        self.assertIn(one["connection_id"], self.rig.broker.connections)

    async def test_file_notification_waits_until_native_call_finishes_before_status(self):
        one = await self.rig.connect()
        control = self.rig.controls["one"]
        control.actions.clear()
        call = asyncio.create_task(self.rig.call(one))
        await self.rig.workers[0].entered.wait()
        self.rig.broker.watcher.notify(one["connection_id"], None)
        await asyncio.sleep(0)
        self.assertNotIn("status", control.actions)
        self.rig.workers[0].release.set()
        await call
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertLess(control.actions.index("end"), control.actions.index("status"))
        self.assertEqual(self.rig.workers[0].closed, 0)

    async def test_rhino_disconnect_drains_current_call_and_rejects_queued_work(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        first = asyncio.create_task(self.rig.call(one))
        await worker.entered.wait()
        queued = asyncio.create_task(self.rig.call(one))
        await asyncio.sleep(0)
        conn = self.rig.broker.connections[one["connection_id"]]
        self.rig.invalidate(one)
        self.assertFalse(worker.stop.is_set())
        worker.release.set()
        self.assertIs(await first, worker.result)
        self.assertTrue((await queued).is_error)
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertEqual(worker.calls, 1)
        self.assertEqual(worker.closed, 1)
        self.assertTrue(conn.cleanup["released"])
        self.assertEqual(self.rig.controls["one"].actions.count("end"), 1)

    async def test_rhino_disconnect_during_begin_does_not_dispatch(self):
        one = await self.rig.connect()
        gate = self.rig.control_gates["begin"] = asyncio.Event()
        call = asyncio.create_task(self.rig.call(one))
        await self.rig.controls["one"].wait_for("begin")
        conn = self.rig.broker.connections[one["connection_id"]]
        self.rig.invalidate(one)
        gate.set()
        self.assertTrue((await call).is_error)
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertEqual(self.rig.workers[0].calls, 0)
        self.assertEqual(self.rig.controls["one"].actions.count("end"), 1)
        self.assertTrue(conn.cleanup["released"])

    async def test_rhino_disconnect_after_uncertain_result_retains_native_locks(self):
        one = await self.rig.connect()
        worker = self.rig.workers[0]
        worker.uncertain = True
        worker.release.set()
        self.assertTrue((await self.rig.call(one)).is_error)
        conn = self.rig.broker.connections[one["connection_id"]]
        self.rig.invalidate(one)
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertTrue(conn.cleanup["worker_closed"])
        self.assertFalse(conn.cleanup["released"])
        self.assertIn("unconfirmed", conn.cleanup["reason"])
        self.assertNotIn("end", self.rig.controls["one"].actions)

    async def test_rhino_disconnect_after_timeout_does_not_clear_native_busy(self):
        one = await self.rig.connect()
        self.rig.broker.call_timeout = 0.03
        self.assertTrue((await self.rig.call(one)).is_error)
        conn = self.rig.broker.connections[one["connection_id"]]
        self.rig.invalidate(one)
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertFalse(conn.cleanup["released"])
        self.assertTrue(self.rig.controls["one"].busy)

    async def test_repeated_rhino_and_cos_disconnect_cleanup_once(self):
        one = await self.rig.connect()
        self.rig.invalidate(one)
        self.rig.invalidate(one)
        result = await self.rig.broker.disconnect(one["connection_id"])
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertTrue(result["released"])
        self.assertEqual(self.rig.workers[0].closed, 1)
        self.assertEqual(self.rig.controls["one"].actions.count("detach"), 1)
        self.rig.invalidate(one)  # A late old-generation event is harmless.
        self.assertFalse(self.rig.broker.background)

    async def test_invalidation_during_watch_registration_never_starts_worker(self):
        self.rig.invalidate_on_watch = True
        with self.assertRaises(RuntimeError):
            await self.rig.connect()
        await asyncio.gather(*list(self.rig.broker.background))
        self.assertFalse(self.rig.workers)
        self.assertFalse(self.rig.broker.connections)
        self.assertFalse(self.rig.broker.watcher.bindings)
