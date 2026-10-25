"""Original TCP sender + owned request batches; disposable native fixtures only."""
import ast
import asyncio
from contextvars import copy_context
import json
import os
from pathlib import Path
import socket
import socketserver
import struct
import tempfile
import threading
from types import SimpleNamespace
import unittest
import almond_mcp
from uuid import uuid4

from native_request import RequestBatch
from project import connection_paths, process_start_ticks, read_json, write_json


def original_sender(port):
    """Extract the installed function unchanged without importing its DB-owning module."""
    source = Path(almond_mcp.__file__).with_name("server.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_send_and_receive"]
    if len(nodes) != 1:
        raise RuntimeError("Original sender contract changed.")
    namespace = dict(socket=socket, BRIDGE_HOST="127.0.0.1", BRIDGE_PORT=port)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_send_and_receive"]


def read_frame(stream):
    def exact(length):
        data = bytearray()
        while len(data) < length:
            part = stream.recv(length - len(data))
            if not part:
                raise ConnectionError("Incomplete fixture frame.")
            data.extend(part)
        return bytes(data)
    length = struct.unpack("!I", exact(4))[0]
    if not 0 < length <= 64 * 1024 * 1024:
        raise ValueError("Invalid fixture frame.")
    return exact(length).decode("utf-8")


def write_frame(stream, value):
    payload = value.encode("utf-8")
    stream.sendall(struct.pack("!I", len(payload)) + payload)


def payload(tag="fixture"):
    return json.dumps(dict(type="execute", tag=tag, script="// fixture")).encode("utf-8")


class NativeFixture:
    def __init__(self, callback=None):
        self.callback, self.calls = callback, []
        self.entered, self.release = threading.Event(), threading.Event()
        fixture = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    envelope = json.loads(read_frame(self.request))
                    fixture.calls.append(envelope)
                    response = dict(schema="almond-native-response", storage_protocol=2,
                                    token=envelope["token"], operation_id=envelope["operation_id"],
                                    request_id=envelope["request_id"], completion_status="completed",
                                    native_sequence=len(fixture.calls),
                                    payload=json.dumps(dict(status="success", tag=json.loads(envelope["payload"])["tag"])))
                    if fixture.callback:
                        response = fixture.callback(envelope, response)
                    if response is not None:
                        write_frame(self.request, json.dumps(response))
                except (ConnectionError, OSError):
                    pass

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = False

        self.server = Server(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)


class RequestTests(unittest.TestCase):
    def batch(self):
        return RequestBatch(uuid4().hex, uuid4().hex)

    def test_original_framing_and_two_distinct_owned_requests(self):
        with NativeFixture() as native:
            batch, sender = self.batch(), original_sender(native.port)
            self.assertEqual(json.loads(batch.call(sender, payload("one")))["tag"], "one")
            self.assertEqual(json.loads(batch.call(sender, payload("two"), timeout=3))["tag"], "two")
            state = batch.finish()
            self.assertFalse(state["uncertain"], state)
            self.assertEqual(len({call["request_id"] for call in native.calls}), 2)
            self.assertEqual({call["operation_id"] for call in native.calls}, {batch.operation_id})
            self.assertEqual(state["native_sequence"], 2)

    def test_sealed_batch_never_calls_sender(self):
        with NativeFixture() as native:
            batch = self.batch()
            batch.finish()
            with self.assertRaisesRegex(RuntimeError, "ended"):
                batch.call(original_sender(native.port), payload())
            self.assertEqual(native.calls, [])

    def test_registered_but_delayed_connect_keeps_old_identity_and_pending(self):
        with NativeFixture() as native:
            first, second = self.batch(), self.batch()
            sender, entered, release = original_sender(native.port), threading.Event(), threading.Event()
            errors = []
            def delayed(data):
                entered.set()
                release.wait(3)
                return sender(data)
            def send_first():
                try:
                    first.call(delayed, payload("old"))
                except BaseException as exc:
                    errors.append(exc)
            thread = threading.Thread(target=send_first)
            thread.start()
            self.assertTrue(entered.wait(2))
            self.assertEqual(first.finish()["pending"], 1)
            second.call(sender, payload("new"))
            release.set()
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual([x["operation_id"] for x in native.calls], [second.operation_id, first.operation_id])
            self.assertFalse(first.finish()["uncertain"])

    def test_original_timeout_does_not_certify_native_completion(self):
        with NativeFixture() as native:
            def wait(envelope, response):
                native.entered.set()
                native.release.wait(3)
                return response
            native.callback = wait
            batch, sender = self.batch(), original_sender(native.port)
            with self.assertRaises(socket.timeout):
                batch.call(sender, payload(), timeout=0.1)
            self.assertTrue(native.entered.wait(2))
            state = batch.finish()
            self.assertFalse(state["pending"])
            self.assertTrue(state["uncertain"])
            self.assertFalse(state["requests"][0]["acknowledged"])

    def test_wrong_ack_taints_only_its_batch(self):
        def wrong(envelope, response):
            response["request_id"] = uuid4().hex
            return response
        with NativeFixture(wrong) as native:
            batch, sender = self.batch(), original_sender(native.port)
            with self.assertRaisesRegex(RuntimeError, "exact request"):
                batch.call(sender, payload())
            self.assertTrue(batch.finish()["uncertain"])
            native.callback = None
            peer = self.batch()
            self.assertEqual(json.loads(peer.call(sender, payload()))["status"], "success")
            self.assertFalse(peer.finish()["uncertain"])

    def test_disconnect_without_ack_remains_unconfirmed(self):
        with NativeFixture(lambda envelope, response: None) as native:
            batch = self.batch()
            with self.assertRaises(ConnectionError):
                batch.call(original_sender(native.port), payload())
            self.assertTrue(batch.finish()["uncertain"])

    def test_completed_with_zero_sequence_is_rejected(self):
        def zero(envelope, response):
            response["native_sequence"] = 0
            return response
        with NativeFixture(zero) as native:
            batch = self.batch()
            with self.assertRaisesRegex(RuntimeError, "exact request"):
                batch.call(original_sender(native.port), payload())
            self.assertTrue(batch.finish()["uncertain"])


class Message:
    def __init__(self, name, arguments=None):
        self.name, self.arguments = name, arguments or {}

    def model_copy(self, *, update):
        return Message(update.get("name", self.name), update.get("arguments", self.arguments))


class Context:
    def __init__(self, message):
        self.message = message

    def copy(self, **update):
        return Context(update.get("message", self.message))


class RuntimeRequestTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Keep atomic operation filenames below Windows MAX_PATH even when a
        # developer checkout is nested under Documents/Codex/<date>/<task>.
        data = Path(__file__).resolve().parents[4] / "data"
        data.mkdir(parents=True, exist_ok=True)
        cls.fixture_root = Path(tempfile.mkdtemp(prefix="_native_", dir=data))
        print("Native request fixture retained for recoverable cleanup:", cls.fixture_root)

    def runtime(self, native):
        from shared_store import ProjectRuntime
        folder = self.fixture_root / uuid4().hex
        folder.mkdir()
        model = folder / "Request-Fixture.3dm"
        model.write_bytes(b"PATH FIXTURE ONLY; NOT A RHINO MODEL")
        token = uuid4().hex
        paths = connection_paths(model, "A", token, create=True)
        identity = dict(pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
        binding = dict(paths, **identity, schema="almond-project", storage_protocol=2,
                       label="A", port=5501, token=token, valid=True)
        write_json(paths["ready_path"], binding)
        write_json(Path(paths["session_dir"]) / "worker.json",
                   dict(identity, schema="almond-worker", storage_protocol=2, token=token))
        args = SimpleNamespace(session=paths["ready_path"], token=token, port=native.port)
        runtime = ProjectRuntime(args, binding, paths)
        def receipt(envelope, response):
            write_json(Path(paths["session_dir"]) / "native.json",
                       dict(schema="almond-native", storage_protocol=2, token=token,
                            operation_id=envelope["operation_id"], pending=0, phase="listening",
                            sequence=response["native_sequence"], completion_status="completed"))
            return response
        native.callback = receipt
        return runtime, original_sender(native.port), paths, receipt

    async def invoke(self, runtime, sender, tag="fixture", timeout=3):
        async def call_next(context):
            return await asyncio.to_thread(runtime.send, sender, payload(tag), timeout=timeout)
        return await runtime.on_call_tool(Context(Message("execute_rhino_script")), call_next)

    async def test_public_middleware_preserves_operation_ids_and_restores_temp(self):
        before = tempfile.gettempdir()
        with NativeFixture() as native:
            runtime, sender, paths, _ = self.runtime(native)
            await self.invoke(runtime, sender, "first")
            first = runtime.completion()["operation_id"]
            await self.invoke(runtime, sender, "second")
            second = runtime.completion()["operation_id"]
            self.assertNotEqual(first, second)
            self.assertEqual([x["operation_id"] for x in native.calls], [first, second])
            self.assertFalse(runtime.completion()["uncertain"], runtime.completion())
            self.assertIsNone(runtime.scope.get())
            self.assertEqual(tempfile.gettempdir(), before)
            self.assertEqual(read_json(Path(paths["session_dir"]) / "operation.json")["state"], "completed")

    async def test_missing_context_and_late_copied_context_fail_before_send(self):
        with NativeFixture() as native:
            runtime, sender, _, _ = self.runtime(native)
            with self.assertRaisesRegex(RuntimeError, "No active operation"):
                runtime.send(sender, payload())
            copied = []
            async def capture(context):
                copied.append(copy_context())
            await runtime.on_call_tool(Context(Message("execute_rhino_script")), capture)
            await self.invoke(runtime, sender, "new")
            with self.assertRaisesRegex(RuntimeError, "ended"):
                copied[0].run(runtime.send, sender, payload("old"))
            self.assertEqual(len(native.calls), 1)
            self.assertEqual(json.loads(native.calls[0]["payload"])["tag"], "new")

    async def test_pre_socket_validation_failure_can_retry(self):
        with NativeFixture() as native:
            runtime, sender, _, _ = self.runtime(native)
            async def invalid(context):
                raise ValueError("Invalid fixture input.")
            with self.assertRaises(ValueError):
                await runtime.on_call_tool(Context(Message("execute_rhino_script")), invalid)
            self.assertFalse(runtime.completion()["uncertain"], runtime.completion())
            await self.invoke(runtime, sender)
            self.assertEqual(len(native.calls), 1)

    async def test_raw_cancellation_waits_for_actual_native_reply(self):
        with NativeFixture() as native:
            runtime, sender, _, receipt = self.runtime(native)
            def wait(envelope, response):
                native.entered.set()
                native.release.wait(3)
                return receipt(envelope, response)
            native.callback = wait
            task = asyncio.create_task(self.invoke(runtime, sender))
            self.assertTrue(await asyncio.to_thread(native.entered.wait, 2))
            task.cancel()
            await asyncio.sleep(0.03)
            self.assertFalse(task.done())
            native.release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertFalse(runtime.completion()["uncertain"], runtime.completion())

    async def test_repeated_cancellation_finishes_receipt_and_metadata(self):
        with NativeFixture() as native:
            runtime, sender, paths, _ = self.runtime(native)
            returned = asyncio.Event()
            receipt_path = Path(paths["session_dir"]) / "native.json"
            def waiting_receipt(envelope, response):
                native.entered.set()
                native.release.wait(3)
                write_json(receipt_path, dict(schema="almond-native", storage_protocol=2,
                           token=envelope["token"], operation_id=envelope["operation_id"],
                           sequence=response["native_sequence"], pending=1, phase="sending",
                           completion_status="running"))
                return response
            native.callback = waiting_receipt
            async def call_next(context):
                result = await asyncio.to_thread(runtime.send, sender, payload())
                returned.set()
                return result
            task = asyncio.create_task(runtime.on_call_tool(Context(Message("execute_rhino_script")), call_next))
            self.assertTrue(await asyncio.to_thread(native.entered.wait, 2))
            task.cancel()
            native.release.set()
            await asyncio.wait_for(returned.wait(), 3)
            for _ in range(100):
                if runtime.batch.sealed:
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(runtime.batch.sealed)
            task.cancel()
            await asyncio.sleep(0.03)
            self.assertFalse(task.done())
            receipt = read_json(receipt_path)
            receipt.update(sequence=receipt["sequence"] + 1, pending=0, phase="listening",
                           completion_status="completed")
            write_json(receipt_path, receipt)
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertFalse(runtime.completion()["uncertain"], runtime.completion())
            self.assertEqual(read_json(Path(paths["session_dir"]) / "operation.json")["state"], "completed")

    async def test_cancel_then_function_failure_still_cleans_and_reports_cancellation(self):
        with NativeFixture() as native:
            runtime, _, paths, _ = self.runtime(native)
            entered, release = asyncio.Event(), asyncio.Event()
            async def failing(context):
                entered.set()
                await release.wait()
                raise ValueError("Original function failed after cancellation.")
            task = asyncio.create_task(runtime.on_call_tool(Context(Message("execute_rhino_script")), failing))
            try:
                await asyncio.wait_for(entered.wait(), 3)
            except TimeoutError:
                if task.done():
                    await task  # Surface setup failures instead of waiting forever.
                task.cancel()
                raise
            task.cancel()
            await asyncio.sleep(0.01)
            self.assertFalse(task.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError) as caught:
                await task
            self.assertIsInstance(caught.exception.__cause__, ValueError)
            self.assertFalse(runtime.completion()["uncertain"], runtime.completion())
            self.assertEqual(read_json(Path(paths["session_dir"]) / "operation.json")["state"], "completed")

    async def test_missing_ack_cannot_hide_native_pending_after_socket_ends(self):
        with NativeFixture() as native:
            runtime, sender, paths, _ = self.runtime(native)
            receipt_path = Path(paths["session_dir"]) / "native.json"
            def lost(envelope, response):
                write_json(receipt_path, dict(schema="almond-native", storage_protocol=2,
                           token=envelope["token"], operation_id=envelope["operation_id"],
                           sequence=1, pending=1, phase="queued", completion_status="running"))
                return None
            native.callback = lost
            with self.assertRaises(ConnectionError):
                await self.invoke(runtime, sender)
            state = runtime.completion()
            self.assertTrue(state["uncertain"])
            self.assertTrue(state["pending"], state)
            self.assertEqual(state["transport"]["pending"], 0)
            receipt = read_json(receipt_path)
            receipt.update(sequence=2, pending=0, phase="stopped", completion_status="rejected")
            write_json(receipt_path, receipt)
            self.assertFalse(runtime.completion()["pending"])
            self.assertTrue(runtime.completion()["uncertain"])
            with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
                await self.invoke(runtime, sender)


if __name__ == "__main__":
    unittest.main()
