"""Startup uses only a new explicit process; it never saves or kills a model."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from session_start import RhinoStart


class RhinoStartTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.model = self.root / "saved user's model.3dm"
        self.model.write_bytes(b"untouched fixture")
        self.executable = self.root / "Rhino.exe"
        self.executable.touch()
        self.config = self.root / "settings.json"
        self.config.write_text(json.dumps({"rhino_exe": str(self.executable)}), encoding="utf-8")
        self.process = Mock(pid=7123)
        self.process.poll.return_value = None
        self.spawn = Mock(return_value=self.process)
        self.identity = Mock(return_value={"pid": 7123, "process_start_ticks": "12345"})
        self.records = []

    def start(self, **kwargs):
        return RhinoStart(str(self.model), self.root / "data", settings_path=self.config,
                          process_factory=self.spawn, identity_reader=self.identity,
                          host_reader=lambda _: self.records, timeout=0.01, poll_interval=0,
                          **kwargs)

    async def test_explicit_start_passes_model_as_one_argument_and_enables_cos(self):
        with patch.dict("os.environ", {"ALMOND_SESSION_TOKEN": "old", "ALMOND_SESSION_FOLDER": "old",
                                       "ALMONDCOS_SESSION_TOKEN": "old", "RHINO_MCP_LIBRARY_DIR": "custom"}):
            launch = self.start()
        args, kwargs = self.spawn.call_args
        self.assertEqual(args[0], [str(self.executable), str(self.model), "/nosplash", "/runscript=_AlmondCOS"])
        self.assertEqual(kwargs["cwd"], str(self.root))
        self.assertEqual(kwargs["env"]["RHINO_MCP_LIBRARY_DIR"], "custom")
        for key in ("ALMOND_SESSION_TOKEN", "ALMOND_SESSION_FOLDER", "ALMONDCOS_SESSION_TOKEN"):
            self.assertNotIn(key, kwargs["env"])
        self.assertEqual(self.model.read_bytes(), b"untouched fixture")
        self.assertFalse((self.root / ".almond").exists())
        self.assertEqual(launch.identity, self.identity.return_value)

    async def test_only_exact_new_process_advertisement_is_used(self):
        launch = self.start()
        self.records = [{"host_id": "other", "pid": 7124, "process_start_ticks": "12345"},
                        {"host_id": "reused", "pid": 7123, "process_start_ticks": "old"},
                        {"host_id": "owned", "pid": 7123, "process_start_ticks": "12345"}]
        self.assertEqual((await launch.discover())["host_id"], "owned")

    async def test_timeout_then_discovery_reuses_process_without_killing_it(self):
        launch = self.start()
        with self.assertRaises(TimeoutError):
            await launch.discover()
        self.records = [{"host_id": "owned", **launch.identity}]
        self.assertEqual((await launch.discover())["host_id"], "owned")
        self.spawn.assert_called_once()
        self.process.terminate.assert_not_called()
        self.process.kill.assert_not_called()

    async def test_process_exit_or_identity_change_does_not_adopt_another_rhino(self):
        launch = self.start()
        self.process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "exited"):
            await launch.discover()
        self.process.poll.return_value = None
        self.identity.return_value = {"pid": 7123, "process_start_ticks": "changed"}
        with self.assertRaisesRegex(RuntimeError, "identity"):
            await launch.discover()
        self.spawn.assert_called_once()

    async def test_invalid_model_never_starts_a_process(self):
        for model in ("relative.3dm", str(self.root / "missing.3dm"), str(self.executable)):
            with self.subTest(model=model), self.assertRaises((ValueError, OSError)):
                RhinoStart(model, self.root / "data", settings_path=self.config,
                           process_factory=self.spawn, identity_reader=self.identity)
        self.spawn.assert_not_called()

    async def test_cancelled_discovery_does_not_kill_rhino(self):
        launch = self.start()
        task = asyncio.create_task(launch.discover())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.process.terminate.assert_not_called()
        self.process.kill.assert_not_called()
