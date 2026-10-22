"""Windows shared-store contracts using fresh paths and the unchanged AlmondStore.

No Rhino port, installed MCP server, user model, or library is accessed. The .3dm
files are explicitly path fixtures, not geometry. Each run retains one dedicated
data directory for inspection. Two owned Python children exercise the real OS
gate and SQLite store; public FastMCP dispatch exercises middleware cancellation.
"""
from __future__ import annotations

import asyncio
from contextlib import closing, suppress
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
import uuid

from almond_mcp.retrieval_store import AlmondStore
from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware

from project import (ExclusiveFile, LEGACY_LOCKS, SharedStorageLease,
                     connection_paths, process_start_ticks, read_binding,
                     read_json, write_json)
from shared_store import ProjectRuntime, StoreGate


ENGINE = Path(__file__).resolve().parent
FIXTURE_ROOT = None
TEMP_KEYS = ("TEMP", "TMP", "TMPDIR")


def no_original_server():
    if "almond_mcp.server" in sys.modules:
        raise AssertionError("These fixtures must not import the installed MCP server.")


def setUpModule():
    global FIXTURE_ROOT
    no_original_server()
    (ENGINE.parent / "data").mkdir(parents=True, exist_ok=True)
    FIXTURE_ROOT = Path(tempfile.mkdtemp(prefix="_shared_store_", dir=ENGINE.parent / "data"))
    print("Shared-store fixtures retained at:", FIXTURE_ROOT, flush=True)


def tearDownModule():
    no_original_server()


def workspace(name):
    # Keep the fixture itself below Windows' ordinary path limit after two tokens.
    root = FIXTURE_ROOT / (name.removeprefix("test_")[:20] + "-" + uuid.uuid4().hex[:12])
    root.mkdir()
    return root


def connection(root, name="A", slot="A"):
    model = root / (name + ".3dm")
    with model.open("xb") as stream:
        stream.write(b"PATH FIXTURE ONLY; NOT A RHINO DOCUMENT")
    token = uuid.uuid4().hex
    locations = connection_paths(model, slot, token, create=True)
    identity = dict(pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
    binding = dict(locations, **identity, schema="almond-project", storage_protocol=2,
                   attachment="fixture", valid=True, label=slot,
                   port=5501 + "ABCDEFGHIJ".index(slot), token=token)
    ready = Path(locations["ready_path"])
    write_json(ready, binding)
    write_json(Path(locations["session_dir"]) / "worker.json",
               dict(identity, schema="almond-worker", storage_protocol=2, token=token))
    return SimpleNamespace(locations=locations, binding=binding, token=token,
                           ready=ready, args=SimpleNamespace(session=ready, token=token,
                                                             port=binding["port"]))


def temp_state():
    return ({key: os.environ.get(key) for key in TEMP_KEYS}, tempfile.tempdir)


def result_json(result):
    return json.loads(result.content[0].text)


def database_snapshot(database):
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        return {table: db.execute("SELECT * FROM " + table + " ORDER BY 1").fetchall()
                for table in ("scenes", "rooms", "instances", "scene_revisions", "instance_rtree")}


def wait_until(predicate, message, timeout=15):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise TimeoutError(message)
        time.sleep(0.02)


class LeaseAssertions:
    def assert_locked(self, path):
        with self.assertRaises(OSError) as caught:
            with ExclusiveFile(path):
                pass
        self.assertIn(caught.exception.errno, (32, 33))

    def assert_free(self, path):
        with ExclusiveFile(path):
            pass


@unittest.skipUnless(sys.platform == "win32", "Windows file-sharing contract")
class GenerationAndLeaseTests(LeaseAssertions, unittest.TestCase):
    def setUp(self):
        self.root = workspace(self._testMethodName)
        self.a = connection(self.root, "first", "A")
        self.b = connection(self.root, "second", "B")
        self.storage = Path(self.a.locations["storage"])

    def test_shared_paths_fresh_tokens_and_peer_invalidation(self):
        for field in ("storage", "state_db", "temp"):
            self.assertEqual(self.a.locations[field], self.b.locations[field])
        for field in ("session_dir", "ready_path", "call_root"):
            self.assertNotEqual(self.a.locations[field], self.b.locations[field])
        self.assertNotEqual(self.a.token, self.b.token)
        peer = self.b.ready.read_bytes()
        write_json(self.a.ready, dict(self.a.binding, valid=False))
        with self.assertRaisesRegex(RuntimeError, "connection ended or changed"):
            read_binding(self.a.ready, self.a.token)
        self.assertEqual(read_binding(self.b.ready, self.b.token)[0], self.b.binding)
        self.assertEqual(peer, self.b.ready.read_bytes())
        with self.assertRaises(FileExistsError):
            connection_paths(self.a.locations["model_path"], "A", self.a.token, create=True)
        self.assertEqual(peer, self.b.ready.read_bytes())

    def test_shared_legacy_handles_exclude_old_owners_both_directions(self):
        for name in LEGACY_LOCKS:
            (self.storage / name).write_bytes(("retained " + name).encode())
        with SharedStorageLease(self.storage), SharedStorageLease(self.storage):
            for name in LEGACY_LOCKS:
                with self.subTest(new_owner_blocks_old=name):
                    self.assert_locked(self.storage / name)
        for name in LEGACY_LOCKS:
            with self.subTest(old_owner_blocks_new=name):
                with ExclusiveFile(self.storage / name):
                    with self.assertRaises(OSError):
                        with SharedStorageLease(self.storage):
                            pass
            self.assertEqual((self.storage / name).read_bytes(), ("retained " + name).encode())
            self.assert_free(self.storage / name)

    def test_partial_shared_acquisition_releases_prior_handles(self):
        for index in (1, 2):
            with self.subTest(failing_lock=LEGACY_LOCKS[index]):
                with ExclusiveFile(self.storage / LEGACY_LOCKS[index]):
                    with self.assertRaises(OSError):
                        SharedStorageLease(self.storage)
                    for earlier in LEGACY_LOCKS[:index]:
                        self.assert_free(self.storage / earlier)

    def test_session_mcp_is_exclusive_while_peer_remains_usable(self):
        a_lock = Path(self.a.locations["session_dir"]) / "mcp.lock"
        b_lock = Path(self.b.locations["session_dir"]) / "mcp.lock"
        peer = self.b.ready.read_bytes()
        with SharedStorageLease(self.storage), SharedStorageLease(self.storage):
            with ExclusiveFile(b_lock):
                with ExclusiveFile(a_lock):
                    self.assert_locked(a_lock)
                    self.assert_locked(b_lock)
                self.assert_free(a_lock)
                self.assert_locked(b_lock)
                self.assertEqual(read_binding(self.b.ready, self.b.token)[0], self.b.binding)
                self.assertEqual(peer, self.b.ready.read_bytes())
        self.assert_free(b_lock)


def store_child(root, label):
    """Only called by this test's directly owned children, using fixture paths."""
    no_original_server()
    job = read_json(root / "job.json")
    locations = job["connections"][label]

    def await_flag(name):
        def ready():
            if (root / "abort.json").exists():
                raise RuntimeError("Fixture controller aborted.")
            return (root / name).exists()
        wait_until(ready, "Fixture controller did not publish " + name)

    with SharedStorageLease(locations["storage"]), ExclusiveFile(Path(locations["session_dir"]) / "mcp.lock"):
        write_json(root / (label + "-ready.json"), dict(pid=os.getpid()))
        await_flag("begin-init.json")
        write_json(root / (label + "-attempt.json"), dict(pid=os.getpid()))
        with StoreGate(locations["storage"], timeout=10):
            store = AlmondStore(locations["state_db"])
        write_json(root / (label + "-initialized.json"), dict(pid=os.getpid()))
        await_flag("begin-work.json")
        scene = read_json(root / "begin-work.json")["scene_id"]
        rooms = []
        for index in range(job["iterations"]):
            with StoreGate(locations["storage"], timeout=10):
                common = store.upsert_room(scene, "Shared Room", [0, 0, 0, 1000, 1000, 3000],
                                          metadata=dict(writer=label, iteration=index))
                unique = store.upsert_room(scene, label + "-" + str(index), [0, 0, 0, 1000, 1000, 3000],
                                          metadata=dict(writer=label, iteration=index))
                rooms.append(dict(common=common, unique=unique))
        no_original_server()
        write_json(root / (label + "-result.json"), dict(pid=os.getpid(), rooms=rooms))


@unittest.skipUnless(sys.platform == "win32", "Windows file-sharing contract")
class ProcessStoreTests(unittest.TestCase):
    def test_two_process_initialization_and_same_name_room_upserts(self):
        root = workspace("two-processes")
        a, b = connection(root, "left", "A"), connection(root, "right", "B")
        iterations = 8
        write_json(root / "job.json",
                   dict(connections=dict(A=a.locations, B=b.locations), iterations=iterations))
        children = []

        def both(suffix):
            for label, process in children:
                if process.poll() is not None and process.returncode != 0:
                    raise RuntimeError(label + " fixture child exited early.")
            return all((root / (label + suffix)).exists() for label in ("A", "B"))

        try:
            for label in ("A", "B"):
                process = subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                                            "--store-child", str(root), label],
                                           cwd=ENGINE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, encoding="utf-8")
                children.append((label, process))
            wait_until(lambda: both("-ready.json"), "Two children did not become ready.")
            self.assertNotEqual(children[0][1].pid, children[1][1].pid)
            with StoreGate(a.locations["storage"]):
                write_json(root / "begin-init.json", dict(start=True))
                wait_until(lambda: both("-attempt.json"), "Two children did not attempt initialization.")
                self.assertFalse((root / "A-initialized.json").exists())
                self.assertFalse((root / "B-initialized.json").exists())
            wait_until(lambda: both("-initialized.json"), "Concurrent initialization did not complete.")
            with StoreGate(a.locations["storage"]):
                scene = AlmondStore(a.locations["state_db"]).create_scene("Shared fixture scene")
            write_json(root / "begin-work.json", dict(scene_id=scene["scene_id"]))
            for label, process in children:
                output, error = process.communicate(timeout=30)
                self.assertEqual(process.returncode, 0, label + "\n" + output + error)
            with closing(sqlite3.connect(a.locations["state_db"])) as db:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                rows = db.execute("SELECT name, metadata_json FROM rooms WHERE scene_id = ?",
                                  (scene["scene_id"],)).fetchall()
                self.assertEqual(len(rows), 2 * iterations + 1)
                common = [json.loads(meta) for name, meta in rows if name == "Shared Room"]
                self.assertEqual(len(common), 1)
                self.assertEqual(common[0]["iteration"], iterations - 1)
                self.assertIn(common[0]["writer"], ("A", "B"))
                for label in ("A", "B"):
                    expected = {(label + "-" + str(index), index) for index in range(iterations)}
                    actual = {(name, json.loads(meta)["iteration"]) for name, meta in rows
                              if name.startswith(label + "-")}
                    self.assertEqual(actual, expected)
                revisions = [row[0] for row in db.execute(
                    "SELECT revision FROM scene_revisions WHERE scene_id = ? ORDER BY revision",
                    (scene["scene_id"],))]
                self.assertEqual(revisions, list(range(1, 4 * iterations + 1)))
                self.assertEqual(db.execute("SELECT revision FROM scenes WHERE scene_id = ?",
                                            (scene["scene_id"],)).fetchone()[0], 4 * iterations)
            results = [read_json(root / (label + "-result.json")) for label in ("A", "B")]
            common_ids = {room["common"]["room_id"] for result in results for room in result["rooms"]}
            self.assertEqual(len(common_ids), 1)
            write_json(root / "verified.json", dict(database=a.locations["state_db"],
                       worker_pids=[item["pid"] for item in results], rooms=len(rows),
                       revision_count=len(revisions), integrity="ok", foreign_key_errors=[]))
        finally:
            write_json(root / "abort.json", dict(stop=True))
            for label, process in children:
                if process.poll() is None:
                    try:
                        process.communicate(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.kill()  # Only this test's directly started child.
                        process.communicate()


class ObserveEntry(Middleware):
    def __init__(self):
        self.entered = asyncio.Event()
        self.task = None

    async def on_call_tool(self, context, call_next):
        self.task = asyncio.current_task()
        self.entered.set()
        return await call_next(context)


@unittest.skipUnless(sys.platform == "win32", "Windows file-sharing contract")
class MiddlewareTests(LeaseAssertions, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = workspace(self._testMethodName)
        self.session = connection(self.root)
        self.paths = self.session.locations
        self.observer = ObserveEntry()
        self.runtime = ProjectRuntime(self.session.args, self.session.binding, self.paths)
        self.mcp = FastMCP("Shared-store fixture")
        self.mcp.add_middleware(self.observer)
        self.mcp.add_middleware(self.runtime)
        self.gate_path = Path(self.paths["storage"]) / ".sessions" / "store.lock"
        self.operation_path = Path(self.paths["session_dir"]) / "operation.json"
        self.calls = []

    def assert_operation_completed(self):
        operation = read_json(self.operation_path)
        self.assertEqual(operation["token"], self.session.token)
        self.assertEqual(operation["state"], "completed")
        self.assertEqual(Path(operation["temp"]).parent, Path(self.paths["call_root"]))
        self.assert_free(self.gate_path)
        return operation

    def report_tool(self):
        @self.mcp.tool()
        def export_structural_report(path: str = "") -> dict:
            observed = dict(path=path, env={key: os.environ.get(key) for key in TEMP_KEYS},
                            temp=tempfile.gettempdir())
            self.calls.append(observed)
            Path(path).write_text("fixture report", encoding="utf-8")
            return observed

    async def test_protocol_calls_get_unique_output_and_temp_then_restore(self):
        self.report_tool()
        async with Client(self.mcp) as client:
            before = temp_state()
            results = [result_json(await client.call_tool("export_structural_report", {"path": ""}))
                       for _ in range(2)]
            self.assertEqual(temp_state(), before)
        self.assertNotEqual(results[0]["path"], results[1]["path"])
        for result in results:
            operation_dir = Path(result["path"]).parent.parent
            self.assertEqual(operation_dir.parent, Path(self.paths["call_root"]))
            self.assertEqual(Path(result["temp"]), operation_dir)
            self.assertEqual(set(result["env"].values()), {str(operation_dir)})
            self.assertEqual(Path(result["path"]).read_text(encoding="utf-8"), "fixture report")
        self.assert_operation_completed()

    async def test_explicit_public_output_path_is_preserved(self):
        self.report_tool()
        explicit = self.root / "explicit-user-report.md"
        before = temp_state()
        result = result_json(await self.mcp.call_tool("export_structural_report", {"path": str(explicit)}))
        self.assertEqual(result["path"], str(explicit))
        self.assertEqual(explicit.read_text(encoding="utf-8"), "fixture report")
        self.assertNotEqual(Path(result["temp"]), explicit.parent)
        self.assertEqual(temp_state(), before)
        self.assert_operation_completed()

    async def test_raw_repeated_cancel_keeps_gate_until_sync_body_and_cleanup_end(self):
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        observations = []

        @self.mcp.tool()
        def held_write() -> str:
            observations.append(temp_state())
            started.set()
            try:
                if not release.wait(10):
                    raise TimeoutError("Fixture controller did not release the body.")
                observations.append(temp_state())
                Path(tempfile.gettempdir(), "body-finished.txt").write_text("finished", encoding="utf-8")
                return "finished"
            finally:
                finished.set()

        before = temp_state()
        task = asyncio.create_task(self.mcp.call_tool("held_write", {}))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 3))
            self.assertIs(self.observer.task, task)
            for _ in range(2):
                task.cancel()
                await asyncio.sleep(0)  # Let each cancellation reach the runtime separately.
                self.assertFalse(task.done())
                self.assertFalse(finished.is_set())
                self.assert_locked(self.gate_path)
                self.assertEqual(temp_state(), observations[0])
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(task), 5)
        finally:
            release.set()
            with suppress(asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(task), 5)
            self.assertTrue(await asyncio.to_thread(finished.wait, 3))
        self.assertEqual(observations, [observations[0], observations[0]])
        self.assertEqual(temp_state(), before)
        operation = self.assert_operation_completed()
        self.assertTrue((Path(operation["temp"]) / "body-finished.txt").is_file())

    async def test_cancel_while_waiting_has_no_call_or_operation_side_effect(self):
        @self.mcp.tool()
        def never_started() -> str:
            self.calls.append("unexpected")
            return "unexpected"

        before = temp_state()
        before_dirs = set(Path(self.paths["call_root"]).iterdir())
        with StoreGate(self.paths["storage"]):
            task = asyncio.create_task(self.mcp.call_tool("never_started", {}))
            try:
                await asyncio.wait_for(self.observer.entered.wait(), 3)
                self.assertIs(self.observer.task, task)
                self.assertFalse(task.done())
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 3)
            finally:
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
            self.assert_locked(self.gate_path)
            self.assertFalse(self.operation_path.exists())
            self.assertEqual(set(Path(self.paths["call_root"]).iterdir()), before_dirs)
            self.assertEqual(self.calls, [])
            self.assertEqual(temp_state(), before)
        self.assert_free(self.gate_path)
        self.assertEqual(self.calls, [])

    async def test_tool_failure_still_restores_temp_and_releases_gate(self):
        @self.mcp.tool()
        def failed_write() -> str:
            raise ValueError("fixture body failed")

        before = temp_state()
        with self.assertRaisesRegex(Exception, "fixture body failed"):
            await self.mcp.call_tool("failed_write", {})
        self.assertEqual(temp_state(), before)
        self.assert_operation_completed()

    async def test_explicit_room_id_cannot_modify_another_scene(self):
        with StoreGate(self.paths["storage"]):
            store = AlmondStore(self.paths["state_db"])
            a = store.create_scene("first")["scene_id"]
            b = store.create_scene("second")["scene_id"]
            store.upsert_room(a, "owned", [0, 0, 0, 1000, 1000, 3000], room_id="owned-room")
        before = database_snapshot(self.paths["state_db"])

        @self.mcp.tool()
        def upsert_design_room(scene_id: str, room_id: str, name: str) -> dict:
            self.calls.append(scene_id)
            return store.upsert_room(scene_id, name, [0, 0, 0, 2000, 2000, 3000], room_id=room_id)

        with self.assertRaisesRegex(ValueError, "already belongs to another scene"):
            await self.mcp.call_tool("upsert_design_room",
                                     dict(scene_id=b, room_id="owned-room", name="wrong-scene"))
        self.assertEqual(self.calls, [])
        self.assertEqual(database_snapshot(self.paths["state_db"]), before)
        self.assertFalse(self.operation_path.exists())
        result = result_json(await self.mcp.call_tool(
            "upsert_design_room", dict(scene_id=a, room_id="owned-room", name="same-scene")))
        self.assertEqual(result["scene_id"], a)
        self.assertEqual(result["revision"], 2)
        self.assertEqual(self.calls, [a])
        self.assert_operation_completed()

    async def test_explicit_instance_id_cannot_modify_another_scene(self):
        with StoreGate(self.paths["storage"]):
            store = AlmondStore(self.paths["state_db"])
            store.sync_assets([dict(asset_id="fixture-cube", dimensions_mm=dict(width=100, depth=100, height=100))],
                              library_id="fixture")
            a = store.create_scene("first")["scene_id"]
            b = store.create_scene("second")["scene_id"]
            store.upsert_instance(a, "fixture-cube", 0, 0, instance_id="owned-instance")
        before = database_snapshot(self.paths["state_db"])

        @self.mcp.tool()
        def register_scene_instance(scene_id: str, instance_id: str, x_mm: float) -> dict:
            self.calls.append(scene_id)
            return store.upsert_instance(scene_id, "fixture-cube", x_mm, 0, instance_id=instance_id)

        with self.assertRaisesRegex(ValueError, "already belongs to another scene"):
            await self.mcp.call_tool("register_scene_instance",
                                     dict(scene_id=b, instance_id="owned-instance", x_mm=700))
        self.assertEqual(self.calls, [])
        self.assertEqual(database_snapshot(self.paths["state_db"]), before)
        self.assertFalse(self.operation_path.exists())
        result = result_json(await self.mcp.call_tool(
            "register_scene_instance", dict(scene_id=a, instance_id="owned-instance", x_mm=700)))
        self.assertEqual(result["scene_id"], a)
        self.assertEqual(result["revision"], 2)
        self.assertEqual(self.calls, [a])
        self.assert_operation_completed()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--store-child":
        store_child(Path(sys.argv[2]).resolve(strict=True), sys.argv[3])
    else:
        unittest.main(verbosity=2)
