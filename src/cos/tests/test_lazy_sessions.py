"""Lazy stdio initialization and isolated, explicitly requested Rhino sessions."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import cos_host
from test_broker import CATALOG, Rig


class LazyStartupTests(unittest.TestCase):
    def test_main_only_reads_catalog_without_owning_runtime_or_creating_data(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "not-created"
            with patch.object(cos_host, "load_catalog", return_value=CATALOG), \
                    patch.object(cos_host, "check_contract", side_effect=AssertionError("eager source scan")), \
                    patch.object(cos_host, "serve", new_callable=AsyncMock) as serve:
                cos_host.main(data)
            serve.assert_awaited_once_with(CATALOG, data=data)
            self.assertFalse(data.exists())


class LazyAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_and_stale_call_do_not_create_a_broker(self):
        factory = unittest.mock.Mock(side_effect=AssertionError("eager broker"))
        adapter = cos_host.SessionAdapter(CATALOG, broker_factory=factory)
        self.assertTrue(adapter.tools)
        result = await adapter.call("execute", {"connection_id": "stale", "script": "x"})
        self.assertTrue(result.is_error)
        await adapter.close()
        factory.assert_not_called()


class ClientIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.one, self.two = Rig(), Rig()
        for rig in (self.one, self.two):
            rig.broker.data = Path(self.directory.name)
            rig.broker.lease_factory = cos_host.host_lease
            self.addAsyncCleanup(rig.broker.close)

    async def test_two_clients_can_own_different_rhinos_but_not_the_same_rhino(self):
        first = await self.one.connect()
        second = await self.two.connect("two")
        self.assertNotEqual(first["connection_id"], second["connection_id"])
        with self.assertRaisesRegex(RuntimeError, "another.*client"):
            await self.two.connect()
        self.assertNotIn("one", self.two.controls)
        self.assertEqual(len(self.two.workers), 1)
        result = await self.two.call(first)
        self.assertTrue(result.is_error)
        await self.one.broker.disconnect(first["connection_id"])
        await self.two.connect()

    async def test_listing_busy_rhino_does_not_touch_its_pipe(self):
        await self.one.connect()
        listing = await self.two.broker.list_connections()
        busy = next(t for t in listing["targets"] if t["host_id"] == "one")
        self.assertEqual(busy["state"], "in_use")
        self.assertNotIn("one", self.two.controls)
        self.assertFalse(self.two.workers)

    async def test_legacy_singleton_is_respected_until_it_exits(self):
        from project import ExclusiveFile
        with ExclusiveFile(Path(self.directory.name) / "host.lock"):
            with self.assertRaisesRegex(RuntimeError, "legacy|previous"):
                await self.one.connect()
        self.assertFalse(self.one.controls)
        await self.one.connect()

    async def test_released_adapter_lease_does_not_release_uncertain_native_owner(self):
        first = await self.one.connect()
        native_owner = self.one.controls["one"]
        self.one.broker.call_timeout = 0.01
        self.assertTrue((await self.one.call(first)).is_error)
        with self.assertRaisesRegex(RuntimeError, "retaining ownership"):
            await self.one.broker.disconnect(first["connection_id"])
        self.assertTrue(native_owner.busy)
        # The real RHP's retained binding refuses attach, independently of the
        # now-released adapter lease. HostLifecycle exercises that native guard.
        original = self.two.control

        def control(record):
            candidate = original(record)
            request = candidate.request

            async def guarded(action, **fields):
                if action == "attach" and native_owner.busy:
                    raise RuntimeError("native owner retained")
                return await request(action, **fields)

            candidate.request = guarded
            return candidate

        self.two.broker.control_factory = control
        with self.assertRaisesRegex(RuntimeError, "native owner retained"):
            await self.two.connect()
        self.assertFalse(self.two.workers)
        self.assertTrue(native_owner.busy)


class FakeLaunch:
    def __init__(self):
        self.model_path = "one.3dm"
        self.identity = {"pid": 1, "process_start_ticks": "1"}
        self.waits = 0
        self.time_out_once = False
        self.gate = None

    async def discover(self):
        self.waits += 1
        if self.gate is not None:
            await self.gate.wait()
        if self.time_out_once:
            self.time_out_once = False
            raise TimeoutError("Rhino startup not confirmed")
        return {"host_id": "one", **self.identity}


class StartSessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.rig = Rig()
        self.addAsyncCleanup(self.rig.broker.close)
        self.launches = []
        self.launch = FakeLaunch()

        def start(model, data):
            self.launches.append((model, data))
            return self.launch

        self.rig.broker.starter_factory = start

    async def test_start_request_is_idempotent_and_binds_only_its_new_rhino(self):
        first = await self.rig.broker.start_session("one.3dm", "request-one")
        second = await self.rig.broker.start_session("one.3dm", "request-one")
        self.assertEqual(first, second)
        self.assertEqual(len(self.launches), 1)
        self.assertEqual(len(self.rig.workers), 1)
        self.assertEqual(first["host_id"], "one")
        self.assertEqual(first["model_filename"], "one.3dm")
        with self.assertRaisesRegex(RuntimeError, "different model"):
            await self.rig.broker.start_session("two.3dm", "request-one")

    async def test_connect_uses_the_validated_canonical_model_path(self):
        self.launch.model_path = "one.3dm"
        result = await self.rig.broker.start_session("folder/../one.3dm", "request-one")
        self.assertEqual(result["model_path"], "one.3dm")

    async def test_timeout_retry_only_rediscovers_the_original_process(self):
        self.launch.time_out_once = True
        with self.assertRaisesRegex(TimeoutError, "startup"):
            await self.rig.broker.start_session("one.3dm", "request-one")
        self.assertFalse(self.rig.workers)
        result = await self.rig.broker.start_session("one.3dm", "request-one")
        self.assertEqual(result["host_id"], "one")
        self.assertEqual(len(self.launches), 1)
        self.assertEqual(self.launch.waits, 2)

    async def test_cancelled_call_keeps_attempt_and_does_not_launch_twice(self):
        self.launch.gate = asyncio.Event()
        arguments = {"model_path": "one.3dm", "request_id": "request-one"}
        caller = asyncio.create_task(self.rig.broker.call("start_session", arguments))
        for _ in range(20):
            await asyncio.sleep(0)
            if self.launches:
                break
        self.assertEqual(len(self.launches), 1)
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        self.launch.gate.set()
        result = await self.rig.broker.call("start_session", arguments)
        self.assertFalse(result.is_error)
        self.assertEqual(len(self.launches), 1)
        self.assertEqual(len(self.rig.workers), 1)

    async def test_failed_attach_is_not_repeated_by_reusing_request_id(self):
        with patch.object(self.rig.broker, "connect", new_callable=AsyncMock,
                          side_effect=RuntimeError("attach outcome uncertain")) as connect:
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError, "uncertain"):
                    await self.rig.broker.start_session("one.3dm", "request-one")
            self.assertEqual(connect.await_count, 1)
        self.assertEqual(len(self.launches), 1)

    async def test_ended_request_does_not_reopen_a_rhino(self):
        result = await self.rig.broker.start_session("one.3dm", "request-one")
        await self.rig.broker.disconnect(result["connection_id"])
        with self.assertRaisesRegex(RuntimeError, "ended"):
            await self.rig.broker.start_session("one.3dm", "request-one")
        self.assertEqual(len(self.launches), 1)

    async def test_client_close_stops_discovery_without_attaching_or_relaunching(self):
        self.launch.gate = asyncio.Event()
        caller = asyncio.create_task(self.rig.broker.start_session("one.3dm", "request-one"))
        for _ in range(20):
            await asyncio.sleep(0)
            if self.launches:
                break
        self.assertEqual(len(self.launches), 1)
        await asyncio.wait_for(self.rig.broker.close(), 1)
        with self.assertRaises(asyncio.CancelledError):
            await caller
        self.assertFalse(self.rig.workers)
        self.assertEqual(len(self.launches), 1)
