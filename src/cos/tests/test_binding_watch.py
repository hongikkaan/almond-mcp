"""Real Windows notifications on disposable files, with the actual broker."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from binding_watch import BindingWatcher
from runtime import ROOT
from test_broker import Rig


def replace_ready(directory, **content):
    path = Path(directory) / "ready.json"
    temporary = path.with_name(uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(content), encoding="utf-8")
    # Match the real RHP publisher (SessionFiles.WriteJson): Windows can briefly
    # block replacement even without a watcher. A held destination still fails.
    deadline = time.monotonic() + 0.2
    try:
        while True:
            try:
                os.replace(temporary, path)
                return
            except OSError as exc:
                if exc.winerror not in (5, 32, 33) or time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
    finally:
        temporary.unlink(missing_ok=True)


@unittest.skipUnless(os.name == "nt", "Windows notification integration")
class BindingNotificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="binding-notify-", dir=ROOT / "data")
        self.events = asyncio.Queue()
        self.watcher = BindingWatcher(lambda key, reason: self.events.put_nowait((key, reason)))

    async def asyncTearDown(self):
        await asyncio.wait_for(self.watcher.close(), 2)
        self.assertFalse(self.watcher.thread.is_alive())
        self.temp.cleanup()

    async def event_for(self, expected):
        while True:
            key, error = await self.events.get()
            self.assertIsNone(error)
            if key == expected:
                return

    async def test_atomic_replacements_are_not_blocked_and_route_to_each_directory(self):
        first, second = (Path(self.temp.name) / name for name in ("문서 A", "문서 B"))
        for key, directory in (("one", first), ("two", second)):
            directory.mkdir()
            replace_ready(directory, valid=True)
            await self.watcher.add(key, {"storage": self.temp.name, "session_dir": str(directory)})
        # Former implementations held ready.json open and failed this sequence
        # with WinError 5. The watcher now owns directory handles only.
        for _ in range(16):
            replace_ready(first, valid=True)
        replace_ready(first, valid=False)
        await asyncio.wait_for(self.event_for("one"), 2)
        replace_ready(second, valid=False)
        await asyncio.wait_for(self.event_for("two"), 2)

    async def test_close_wakes_idle_os_wait_and_repeated_close_is_safe(self):
        await self.watcher.add("idle", {"session_dir": self.temp.name})
        await asyncio.wait_for(self.watcher.close(), 2)
        self.assertFalse(self.watcher.thread.is_alive())
        await self.watcher.close()
        self.assertTrue(self.events.empty())

    async def test_publisher_recovers_after_transient_destination_lock(self):
        replace_ready(self.temp.name, valid=True)
        path = Path(self.temp.name) / "ready.json"
        original_replace = os.replace
        with path.open(encoding="utf-8") as held:
            def release_after_blocked_attempt(source, destination):
                try:
                    return original_replace(source, destination)
                except PermissionError:
                    held.close()
                    raise

            with patch.object(os, "replace", side_effect=release_after_blocked_attempt):
                replace_ready(self.temp.name, valid=False)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"valid": False})

    async def test_publisher_does_not_hide_persistent_destination_lock(self):
        replace_ready(self.temp.name, valid=True)
        path = Path(self.temp.name) / "ready.json"
        with path.open(encoding="utf-8"):
            with self.assertRaises(PermissionError):
                replace_ready(self.temp.name, valid=False)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"valid": True})
        self.assertEqual(list(Path(self.temp.name).glob("*.tmp")), [])

    async def test_removed_generation_does_not_receive_new_generation_events(self):
        await self.watcher.add("old", {"session_dir": self.temp.name})
        self.watcher.remove("old")
        await self.watcher.add("new", {"session_dir": self.temp.name})
        replace_ready(self.temp.name, valid=False)
        key, error = await asyncio.wait_for(self.events.get(), 2)
        self.assertEqual(key, "new")
        self.assertIsNone(error)

    async def test_real_notification_drives_broker_cleanup_without_another_mcp_call(self):
        rig = Rig()
        rig.broker.watcher_factory = BindingWatcher
        original_factory = rig.control

        def control_factory(record):
            control = original_factory(record)
            original_request = control.request

            async def request(action, **fields):
                result = await original_request(action, **fields)
                if action == "attach":
                    result["session_dir"] = self.temp.name
                    result["ready_path"] = str(Path(self.temp.name) / "ready.json")
                    replace_ready(self.temp.name, valid=True)
                return result
            control.request = request
            return control

        rig.broker.control_factory = control_factory
        try:
            one = await rig.connect()
            conn = rig.broker.connections[one["connection_id"]]
            conn.control.invalid = True
            replace_ready(self.temp.name, valid=False)
            await asyncio.wait_for(rig.workers[0].stop.wait(), 2)
            await asyncio.gather(*list(rig.broker.background))
            self.assertTrue(conn.cleanup["released"])
            self.assertFalse(rig.broker.connections)
            self.assertEqual(rig.workers[0].closed, 1)
        finally:
            await rig.broker.close()
            self.assertFalse(rig.broker.watcher.thread.is_alive())
