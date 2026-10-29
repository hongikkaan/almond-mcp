"""Actual broker lifecycle with delayed official-CLI completion, no Rhino."""
import asyncio
import unittest

from external_host import json_result, result_dict
from test_broker import CATALOG, Rig


class CliRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        catalog = {"tools": [*CATALOG["tools"], {
            "name": "get_rhino_execution", "description": "Read execution",
            "inputSchema": {"type": "object", "properties": {"request_id": {"type": "string"}}}}]}
        self.rig = Rig(catalog)
        self.connection = await self.rig.connect()
        self.conn = self.rig.broker.connections[self.connection["connection_id"]]
        self.worker = self.rig.workers[0]
        self.worker.result = json_result({"status": "pending", "request_id": "cli-fixture"})
        self.worker.external_state = {
            "pending": True, "uncertain": True, "native_uncertain": False,
            "external_pending": True, "external_uncertain": True,
            "external_requests": [{"request_id": "cli-fixture", "pending": True, "uncertain": True}],
        }

    async def asyncTearDown(self):
        await asyncio.wait_for(self.rig.broker.close(), 3)

    async def recover(self):
        return await self.rig.broker.call("get_rhino_execution", {"connection_id": self.conn.connection_id})

    def complete(self):
        self.worker.external_state.update(pending=False, uncertain=False,
                                          external_pending=False, external_uncertain=False)
        self.worker.external_state["external_requests"][0].update(pending=False, uncertain=False, completed=True)

    async def test_late_exact_result_releases_original_reservation_without_replay(self):
        self.worker.release.set()
        original = await self.rig.call(self.connection)
        self.assertFalse(original.is_error)
        self.assertEqual(self.conn.state, "recovering")
        self.assertTrue(self.conn.control.busy)
        self.assertNotIn("fail", self.conn.control.actions)
        rejected = await self.rig.call(self.connection)
        self.assertTrue(rejected.is_error)
        self.assertEqual(self.worker.calls, 1)
        pending = result_dict(await self.recover())
        self.assertEqual(pending["connection_state"], "recovering")
        self.complete()
        confirmed = result_dict(await self.recover())
        self.assertEqual(confirmed["connection_state"], "ready")
        self.assertFalse(self.conn.control.busy)
        self.assertEqual(self.worker.calls, 1)
        begin = next(fields for action, fields in self.conn.control.fields if action == "begin")
        end = next(fields for action, fields in self.conn.control.fields if action == "end")
        self.assertEqual(begin["request_id"], end["request_id"])
        self.assertEqual(self.worker.recovery_calls, 2)

    async def test_outer_timeout_retains_worker_and_allows_late_result_read(self):
        self.rig.broker.call_timeout = 0.02
        result = await self.rig.call(self.connection)
        self.assertTrue(result.is_error)
        self.assertEqual(self.conn.state, "recovering")
        self.assertEqual(self.worker.closed, 0)
        self.assertNotIn("fail", self.conn.control.actions)
        self.complete()
        self.assertEqual(result_dict(await self.recover())["connection_state"], "ready")

    async def test_native_uncertainty_cannot_be_reconciled_by_cli_result(self):
        self.worker.release.set()
        self.worker.external_state["native_uncertain"] = True
        result = await self.rig.call(self.connection)
        self.assertTrue(result.is_error)
        self.assertEqual(self.conn.state, "unconfirmed")
        self.assertIn("fail", self.conn.control.actions)
        self.complete()
        self.worker.external_state["uncertain"] = True
        recovered = result_dict(await self.recover())
        self.assertTrue(recovered['requires_reconnect'])
        self.assertEqual(self.conn.state, "unconfirmed")
        self.assertNotIn("end", self.conn.control.actions)

    async def test_receipt_file_notifications_do_not_dispose_recovering_connection(self):
        self.worker.release.set()
        await self.rig.call(self.connection)
        self.rig.broker.binding_changed(self.conn.connection_id, None)
        await self.conn.control.wait_for("status")
        await asyncio.sleep(0)
        self.assertIn(self.conn.connection_id, self.rig.broker.connections)
        self.assertEqual(self.worker.closed, 0)
        self.assertEqual(self.conn.state, "recovering")

    async def test_disconnect_retains_recovery_descriptor_after_worker_exit(self):
        self.worker.release.set()
        await self.rig.call(self.connection)
        await self.rig.broker.call("disconnect", {"connection_id": self.conn.connection_id})
        self.assertNotIn(self.conn.connection_id, self.rig.broker.connections)
        self.assertIn(self.conn.connection_id, self.rig.broker.recovery_bindings)
        self.rig.broker._read_execution_files = lambda binding, arguments: {
            "status": "pending", "request_id": "cli-fixture", "completed": False}
        value = result_dict(await self.recover())
        self.assertEqual(value["connection_state"], "disconnected")
        self.assertTrue(value["requires_reconnect"])
        self.assertEqual(self.worker.calls, 1)

    async def test_cancelled_caller_can_recover_the_same_execution(self):
        running = asyncio.create_task(self.rig.call(self.connection))
        await self.worker.entered.wait()
        running.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await running
        self.worker.release.set()
        for _ in range(30):
            if self.conn.state == "recovering":
                break
            await asyncio.sleep(0.01)
        self.assertEqual(self.conn.state, "recovering")
        self.complete()
        self.assertEqual(result_dict(await self.recover())["connection_state"], "ready")
        self.assertEqual(self.worker.calls, 1)

    async def test_worker_crash_keeps_receipt_readable_without_releasing_native_reservation(self):
        self.worker.release.set()
        await self.rig.call(self.connection)
        async def stopped_worker(*args):
            raise RuntimeError('Fixture worker exited')
        self.worker.call = stopped_worker
        self.rig.broker._read_execution_files = lambda binding, arguments: {
            'status': 'success', 'request_id': 'cli-fixture', 'completed': True,
            'pending': False, 'uncertain': False, 'result': {'answer': 42}}
        recovered = result_dict(await self.recover())
        self.assertEqual(recovered['result'], {'answer': 42})
        self.assertTrue(recovered['requires_reconnect'])
        self.assertEqual(recovered['connection_state'], 'recovering')
        self.assertTrue(self.conn.control.busy)
        self.assertNotIn('end', self.conn.control.actions)
