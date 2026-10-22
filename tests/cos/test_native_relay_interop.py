"""Unchanged original sender and RequestBatch against a disposable native host PID."""
import ast
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
import almond_mcp

from runtime import ENGINE

sys.path.insert(0, str(ENGINE))
from native_request import RequestBatch
from project import process_start_ticks, read_json


REPO = Path(__file__).resolve().parents[2]
NATIVE_FIXTURE = REPO / "tests/engine/native/bin/Release/net8.0-windows/Almond.NativeFixture.dll"
ORIGINAL_RESPONSE = '{"status":"success","objects":["one","two"],"extra":{"kept":true}}'


class NativeRequestInteropTests(unittest.IsolatedAsyncioTestCase):
    async def test_original_sender_and_native_bridge_share_bound_acknowledgements(self):
        dotnet = os.environ.get("ALMONDCOS_TEST_DOTNET",
                                str(REPO / "src/rhp/RhinoTerminal/data/sdk/dotnet.exe"))
        self.assertTrue(NATIVE_FIXTURE.is_file(), "Build the native fixture with run_tests.ps1.")
        identity = dict(pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
        host = subprocess.Popen([dotnet, str(NATIVE_FIXTURE), "--relay-host",
                                 str(identity["pid"]), identity["process_start_ticks"]],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
        batch = None
        try:
            line = await asyncio.wait_for(asyncio.to_thread(host.stdout.readline), timeout=10)
            binding = json.loads(line)
            self.assertEqual(binding["schema"], "almond-native-fixture")
            self.assertNotEqual(binding["host_pid"], identity["pid"])
            self.assertEqual(binding["worker_pid"], identity["pid"])
            source = Path(almond_mcp.__file__).with_name("server.py").read_text(encoding="utf-8-sig")
            functions = [node for node in ast.parse(source).body
                         if isinstance(node, ast.FunctionDef) and node.name == "_send_and_receive"]
            self.assertEqual(len(functions), 1)
            namespace = dict(socket=socket, BRIDGE_HOST="127.0.0.1", BRIDGE_PORT=binding["port"])
            exec(compile(ast.Module(body=functions, type_ignores=[]),
                         "<unchanged Almond sender definition>", "exec"), namespace)
            sender = namespace["_send_and_receive"]
            batch = RequestBatch(binding["token"], binding["operation_id"])
            payload = json.dumps(dict(type="execute", script="// fixture 한글"),
                                 ensure_ascii=False).encode("utf-8")

            for positional, keywords in (((5.0,), {}), ((), {"timeout": 5.0})):
                response = await asyncio.wait_for(
                    asyncio.to_thread(batch.call, sender, payload, *positional, **keywords), timeout=10)
                self.assertEqual(response, ORIGINAL_RESPONSE)

            state = batch.finish()
            self.assertEqual(state["operation_id"], binding["operation_id"])
            self.assertEqual(state["pending"], 0, state)
            self.assertFalse(state["uncertain"], state)
            self.assertEqual(len(state["requests"]), 2)
            self.assertEqual(len({request["request_id"] for request in state["requests"]}), 2)
            self.assertTrue(all(request["acknowledged"] and request["completion_status"] == "completed"
                                for request in state["requests"]))
            self.assertGreater(state["native_sequence"], 0)
            receipt = None
            for _ in range(100):
                receipt = read_json(binding["native_path"])
                if receipt.get("pending") == 0:
                    break
                await asyncio.sleep(0.02)
            self.assertEqual(receipt["token"], binding["token"])
            self.assertEqual(receipt["operation_id"], binding["operation_id"])
            self.assertIn(receipt["request_id"], {request["request_id"] for request in state["requests"]})
            self.assertEqual(receipt["pending"], 0)
            self.assertGreaterEqual(receipt["sequence"], state["native_sequence"])
            self.assertEqual(receipt["completion_status"], "completed")
        finally:
            if batch is not None:
                batch.finish()
            try:
                _, errors = await asyncio.to_thread(host.communicate, "stop\n", timeout=10)
            except subprocess.TimeoutExpired:
                host.kill()  # Only the disposable process created by this test.
                _, errors = await asyncio.to_thread(host.communicate, timeout=5)
                self.fail("The temporary native fixture did not drain: " + errors)
            self.assertEqual(host.returncode, 0, errors)
