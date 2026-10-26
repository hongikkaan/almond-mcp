"""Unchanged original sender and RequestBatch against a disposable native host PID."""
import ast
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import almond_mcp
from fastmcp import Client, FastMCP

from runtime import ENGINE

sys.path.insert(0, str(ENGINE))
from native_request import RequestBatch
from project import connection_paths, process_start_ticks, read_json
from shared_store import ProjectRuntime


REPO = Path(__file__).resolve().parents[3]
NATIVE_FIXTURE = REPO / "src/rhp/Engine/tests/bin/Release/net8.0-windows/Almond.NativeFixture.dll"
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
            await self.check_runtime_operations(binding, sender)
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

    async def check_runtime_operations(self, host, sender):
        binding = read_json(host["ready_path"])
        locations = connection_paths(binding["model_path"], binding["label"], binding["token"])
        args = SimpleNamespace(session=host["ready_path"], token=host["token"])
        runtime = ProjectRuntime(args, binding, locations)
        server = FastMCP("native-operation-directory-contract")
        server.add_middleware(runtime)
        operation_path = Path(host["session_dir"]) / "operation.json"

        async def observe():
            operation = read_json(operation_path)
            scratch = Path(operation["temp"])
            self.assertFalse(scratch.exists(), "Do not allocate scratch before a native request.")
            # Both frames must pass the real BoundBridge.ReadOperation check.
            for _ in range(2):
                response = await asyncio.to_thread(runtime.send, sender, b'{"type":"execute","script":"// fixture"}', 5.0)
                self.assertEqual(response, ORIGINAL_RESPONSE)
                self.assertTrue(scratch.is_dir())
            return json.loads(response)

        names = ("get_rhino_context", "get_rhino_viewport_image", "execute_rhino_script")
        for name in names:
            server.tool(name=name)(observe)
        # The disposable native fixture deliberately listens on an ephemeral
        # port, outside production A-J slots. Adapt only that locator check;
        # worker/host PID checks, TCP sender, operation files, native ownership
        # validation and completion receipts all use production implementations.
        with patch("shared_store.read_binding", side_effect=lambda *_: (read_json(host["ready_path"]), locations)):
            async with Client(server) as client:
                for name in names:
                    with self.subTest(tool=name):
                        result = await client.call_tool(name, {})
                        self.assertEqual(json.loads(result.content[0].text)["status"], "success")
                        self.assertFalse(runtime.completion()["uncertain"])
                        operation = read_json(operation_path)
                        self.assertEqual(operation["state"], "completed")
                        self.assertFalse(Path(operation["temp"]).exists())
                        self.assertTrue(all(item["completion_status"] == "completed"
                                            for item in runtime.last["transport"]["requests"]))
                        # A background task retaining an ended operation must
                        # not recreate its scratch directory before rejection.
                        scope = runtime.scope.set(runtime.batch)
                        try:
                            with self.assertRaisesRegex(RuntimeError, "operation has ended"):
                                runtime.send(sender, b'{"type":"execute"}', 5.0)
                        finally:
                            runtime.scope.reset(scope)
                        self.assertFalse(Path(operation["temp"]).exists())
