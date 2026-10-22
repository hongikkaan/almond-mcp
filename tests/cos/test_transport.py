import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from runtime import ROOT, load_catalog
from winpipe import ControlError, PipeControl, process_identity

TESTS = Path(__file__).resolve().parent


class PipeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.process = subprocess.Popen(
            [os.environ["ALMONDCOS_TEST_DOTNET"],
             str(TESTS / "bin/Release/net8.0-windows/PipeFixture.dll")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW,
        )
        line = await asyncio.wait_for(asyncio.to_thread(self.process.stdout.readline), 5)
        if not line:
            raise RuntimeError(self.process.stderr.read())
        self.record = json.loads(line)
        self.controls = []

    def control(self, record=None):
        control = PipeControl(record or self.record, timeout=3)
        self.controls.append(control)
        return control

    async def stop_fixture(self):
        if self.process.poll() is None:
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            await asyncio.wait_for(asyncio.to_thread(self.process.wait), 5)
        self.assertEqual(self.process.returncode, 0, self.process.stderr.read())

    async def asyncTearDown(self):
        for control in self.controls:
            await control.close()
        try:
            await self.stop_fixture()
        finally:
            if self.process.poll() is None:
                self.process.kill()  # Only this directly started disposable console fixture.
                self.process.wait(timeout=3)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                stream.close()

    async def test_message_mode_unicode_large_reply_and_connection_reuse(self):
        control = self.control()
        text = r"C:\fixture\한글 공백\model.3dm"
        self.assertEqual(await control.request("echo", text=text), {"text": text})
        handle = control.connection.fileno()
        self.assertEqual((await control.request("large"))["text"], "한" * 10000)
        self.assertEqual(control.connection.fileno(), handle)
        self.assertEqual(process_identity(self.record["pid"])["process_start_ticks"],
                         self.record["process_start_ticks"])

    async def test_bad_access_token_and_stale_process_identity_are_rejected(self):
        bad = self.control(dict(self.record, access_token="bad-fixture-token"))
        with self.assertRaises(ControlError):
            await bad.request("describe")
        await bad.close()
        stale = self.control(dict(self.record, process_start_ticks="0"))
        with self.assertRaisesRegex(ControlError, "process has changed"):
            await stale.request("describe")

    async def test_failed_owner_change_does_not_lose_original_eof_cleanup(self):
        control = self.control()
        await control.request("attach", session_token="fixture-A")
        with self.assertRaisesRegex(ControlError, "cannot change"):
            await control.request("attach", session_token="fixture-B")
        await control.close()
        response = await self.control().request("describe")
        self.assertEqual(response, {"attached": "", "released": ["fixture-A"]})

    async def test_detach_clears_owner_before_eof(self):
        control = self.control()
        await control.request("attach", session_token="fixture-A")
        await control.request("detach", session_token="fixture-A")
        await control.close()
        self.assertEqual((await self.control().request("describe"))["released"], [])

    async def test_lost_attach_reply_still_cleans_committed_owner(self):
        control = self.control()
        await asyncio.to_thread(control._open)
        raw = control.connection
        try:
            raw.send_bytes(json.dumps(dict(id=1, action="attach", session_token="fixture-A",
                                           access_token=self.record["access_token"], hold=True)).encode())
            event = await asyncio.wait_for(asyncio.to_thread(self.process.stdout.readline), 3)
            self.assertEqual(event.strip(), "ATTACHED")
        finally:
            raw.close()
        self.process.stdin.write("go\n")
        self.process.stdin.flush()
        self.assertEqual((await self.control().request("describe"))["released"], ["fixture-A"])

    async def test_server_dispose_completes_while_waiting_for_connection(self):
        await self.stop_fixture()

    async def test_server_dispose_completes_while_idle_client_is_attached(self):
        control = self.control()
        await control.request("attach", session_token="fixture-A")
        await self.stop_fixture()


class StdioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.data = tempfile.TemporaryDirectory(prefix="stdio-fixture-", dir=ROOT / "data")

    async def asyncTearDown(self):
        self.data.cleanup()

    async def test_real_host_handshake_catalog_and_stale_call_without_rhino(self):
        # Exercise the same main(), contract check and singleton lock in an
        # empty private data directory, including while the COS host is live.
        entry = "from pathlib import Path; from cos_host import main; main(Path(" + repr(self.data.name) + "))"
        params = StdioServerParameters(command=sys.executable,
                                       args=["-B", "-u", "-c", entry],
                                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), cwd=str(ROOT))
        started = time.monotonic()
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=15.0) as session:
                await session.initialize()
                listing = await session.list_tools()
                self.assertEqual(len(listing.tools), 60)
                self.assertEqual(len({t.name for t in listing.tools}), 60)
                original = load_catalog()["tools"]
                public = {t.name: t for t in listing.tools}
                for tool in original:
                    name = "almond_cos_" + ("project_info" if tool["name"] == "almond_project_info" else tool["name"])
                    self.assertIn("connection_id", public[name].input_schema["required"])
                wire = listing.model_dump(mode="json", by_alias=True, exclude_none=True)
                size = len(json.dumps(wire, ensure_ascii=False).encode("utf-8"))
                self.assertLess(size, 250000)
                result = await session.call_tool("almond_cos_project_info", {"connection_id": "never-created"})
                self.assertTrue(result.is_error)
                self.assertIn("No Rhino request was sent", result.content[0].text)
                print(json.dumps({"stdio_tool_count": len(listing.tools), "catalog_wire_bytes": size,
                                  "startup_and_check_seconds": round(time.monotonic() - started, 3)}))
