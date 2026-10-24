"""Baseline compatibility with unchanged extracted helpers and operation receipts."""
import ast
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
import uuid
import almond_mcp
from almond_mcp import modeling_setup
from uuid import uuid4

from compat_almond import install
from project import connection_paths, process_start_ticks, write_json
from shared_store import ProjectRuntime
from fastmcp.tools.base import ToolResult


TEST_DATA = Path(__file__).resolve().parents[4] / "data/mcp-tests"

G1 = "11111111-1111-1111-1111-111111111111"
G2 = "22222222-2222-2222-2222-222222222222"
REPORT = {"stamped": 2, "deduped": 1, "width": 1200, "depth": 600, "height": 750}


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


class HelperTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(almond_mcp.__file__).with_name("server.py").read_text(encoding="utf-8-sig")
        names = {"_material_groups", "_receive_contract", "_restore_and_place_script"}
        functions = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names]
        assert {n.name for n in functions} == names
        cls.code = compile(ast.Module(body=functions, type_ignores=[]), "<unchanged Almond helper definitions>", "exec")

    def setUp(self):
        fixture_dir = TEST_DATA / "test-fixtures"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="한글 shared fixture ", dir=fixture_dir)
        self.base = Path(self.temp.name)
        model = self.base / "Fixture.3dm"
        model.write_text("Fixture only; never opened by Rhino.", encoding="utf-8")
        self.token = uuid4().hex
        self.locations = connection_paths(model, "A", self.token, create=True)
        self.identity = dict(pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
        binding = dict(self.locations, schema="almond-project", storage_protocol=2, attachment="cos",
                       label="A", port=5501, token=self.token, valid=True, **self.identity)
        write_json(self.locations["ready_path"], binding)
        write_json(Path(self.locations["session_dir"]) / "worker.json",
                   dict(schema="almond-worker", token=self.token, **self.identity))
        args = SimpleNamespace(session=self.locations["ready_path"], token=self.token)
        self.runtime = ProjectRuntime(args, binding, self.locations, check_owner=False)
        self.paths, self.dimension_reports = [], []
        self.material = "fixture-material"
        self.missing_material = False
        self.report_text = json.dumps(REPORT)
        self.native_reply = None
        self.native_sequence = 0
        self.bridge_version = 2
        exchange = SimpleNamespace(dimension_report=lambda contract, report:
                                   self.dimension_reports.append(dict(report)) or {"status": "fixture-match"})

        def bound_sender(payload, *positional, **keywords):
            return self.runtime.send(self.sender, payload, *positional, **keywords)

        namespace = dict(json=json, Path=Path, tempfile=tempfile, uuid=uuid, hashlib=hashlib,
                         material_library=SimpleNamespace(materials={}, get={}.get),
                         modeling_setup=modeling_setup, exchange=exchange, _send_and_receive=bound_sender)
        exec(self.code, namespace)
        self.helpers = SimpleNamespace(**namespace)
        install(self.helpers, self.runtime)
        self.assertIs(self.helpers._send_and_receive, bound_sender)
        self.assertIs(self.helpers._material_groups.__wrapped__, namespace["_material_groups"])
        self.assertIs(self.helpers._receive_contract.__wrapped__, namespace["_receive_contract"])
        self.assertIs(namespace["tempfile"], tempfile)

    def tearDown(self):
        self.temp.cleanup()

    def sender(self, payload, *positional, **kwargs):
        """A fixture endpoint behind the real ProjectRuntime.send/RequestBatch path."""
        operation_path = Path(self.locations["session_dir"]) / "operation.json"
        operation = json.loads(operation_path.read_text(encoding="utf-8"))
        self.assertEqual(operation["state"], "running")
        self.assertEqual(Path(tempfile.gettempdir()), Path(operation["temp"]))
        envelope = json.loads(payload)
        self.assertEqual(envelope["schema"], "almond-native-request")
        self.assertEqual(envelope["storage_protocol"], 2)
        self.assertEqual(envelope["token"], self.token)
        self.assertEqual(envelope["operation_id"], operation["operation_id"])
        self.assertRegex(envelope["request_id"], r"^[0-9a-f]{32}$")
        request = json.loads(envelope["payload"])
        if request.get("type") == "get_rhino_context":
            self.assertEqual(request, {"type": "get_rhino_context", "selection_limit": 0})
            return self.native_response(envelope, operation, {
                "status": "success", "capabilities": {"modeling_materials": self.bridge_version}})
        script = request["script"]
        match = re.search(r'(?:System\.IO\.)?File\.WriteAll(?:Lines|Text)\(\s*@"((?:""|[^"])*)"', script)
        self.assertIsNotNone(match, "Baseline compat must set the actual C# write path.")
        path = Path(match.group(1).replace('""', '"'))
        self.assertEqual(path.parent.parent, Path(operation["temp"]) / "helpers")
        self.assertRegex(path.parent.name, r"^[0-9a-f]{32}$")
        self.assertNotIn("Path.GetTempPath()", script)
        self.paths.append(path)
        if self.native_reply is not None:
            return self.native_reply
        if path.name == "almond_matgroups.txt":
            if not self.missing_material:
                path.write_text(f"{self.material}|{G1}\n", encoding="utf-8")
        elif path.name == "almond_imported.txt":
            path.write_text(f"{G1}\n{G2}\n", encoding="utf-8")
        elif path.name == "almond_import_report.json":
            if self.report_text is not None:
                path.write_text(self.report_text, encoding="utf-8")
        else:
            self.fail("Unexpected helper report")
        return self.native_response(envelope, operation, {"status": "success", "guids": [G1, G2]})

    def native_response(self, envelope, operation, payload):
        self.native_sequence += 1
        identity = dict(token=self.token, operation_id=operation["operation_id"],
                        request_id=envelope["request_id"])
        write_json(Path(self.locations["session_dir"]) / "native.json",
                   dict(schema="almond-native", sequence=self.native_sequence,
                        pending=0, phase="idle", completion_status="completed", **identity))
        return json.dumps(dict(schema="almond-native-response", storage_protocol=2,
                               native_sequence=self.native_sequence, completion_status="completed",
                               payload=json.dumps(payload), **identity))

    async def invoke(self, name, function):
        async def call_next(context):
            return await asyncio.to_thread(function)
        return await self.runtime.on_call_tool(Context(Message(name)), call_next)

    def assert_completion(self, request_count):
        state = self.runtime.completion()
        self.assertFalse(state["pending"], state)
        self.assertFalse(state["uncertain"], state)
        requests = state["transport"]["requests"]
        self.assertEqual(len(requests), request_count)
        self.assertEqual(len({request["request_id"] for request in requests}), request_count)
        self.assertTrue(all(request["acknowledged"] and request["completion_status"] == "completed"
                            for request in requests))
        self.assertEqual(state["native"]["operation_id"], state["operation_id"])
        self.assertEqual(state["native"]["token"], self.token)
        self.assertGreaterEqual(state["native"]["sequence"], state["transport"]["native_sequence"])

    def receive(self):
        contract = {"_resolved_file": str(self.base / "fixture.glb"), "asset_id": "fixture-chair",
                    "source_app": "fixture", "spatial": {"anchor": "bottom_center"}, "materials": [],
                    "dimensions_mm": {"width": 1200, "depth": 600, "height": 750}}
        return self.helpers._receive_contract(contract, 100, 200, 0, 0, "FIXTURE")

    async def test_helper_requires_an_active_operation(self):
        with self.assertRaisesRegex(RuntimeError, "No active operation"):
            self.helpers._material_groups([G1])
        await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        token = self.runtime.scope.set(self.runtime.batch)
        try:
            with self.assertRaisesRegex(RuntimeError, "No active operation"):
                self.helpers._material_groups([G1])
        finally:
            self.runtime.scope.reset(token)
        self.assertEqual(len(self.paths), 1)

    async def test_each_call_reads_its_own_native_helper_report(self):
        original_temp = tempfile.gettempdir()
        first = await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        self.material = "second"
        second = await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        self.assertEqual(first, [{"material_id": "fixture-material", "objects": [G1]}])
        self.assertEqual(second, [{"material_id": "second", "objects": [G1]}])
        self.assertNotEqual(self.paths[0].parent, self.paths[1].parent)
        self.assertEqual(self.paths[0].parent.parent.name, "helpers")
        self.assertEqual(tempfile.gettempdir(), original_temp)
        self.assert_completion(1)

    async def test_import_reads_both_reports_from_the_same_operation(self):
        result = await self.invoke("fixture_receive", self.receive)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["imported_count"], 2)
        self.assertEqual(result["metadata_restored"], 2)
        self.assertEqual(result["materials_deduplicated"], 1)
        self.assertEqual(result["imported_guids"], [G1, G2])
        self.assertEqual(self.dimension_reports, [REPORT])
        self.assertEqual({p.name for p in self.paths}, {"almond_imported.txt", "almond_import_report.json"})
        self.assertEqual(len({p.parent for p in self.paths}), 1)
        self.assertEqual(self.paths[0].parent.parent.name, "helpers")
        self.assert_completion(3)

    async def test_import_checks_bridge_before_mutating_or_writing_reports(self):
        self.bridge_version = 1
        result = await self.invoke("fixture_receive", self.receive)
        self.assertEqual(result["error_code"], "unsupported_materials")
        self.assertEqual(result["mutation_state"], "not_started")
        self.assertEqual(self.paths, [])
        self.assert_completion(1)

    async def test_missing_report_never_reads_an_earlier_operation(self):
        await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        self.missing_material = True
        with self.assertRaisesRegex(RuntimeError, "material report was not received"):
            await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        self.assertTrue(self.paths[0].exists())
        self.assertFalse(self.paths[1].exists())
        self.assertNotEqual(self.paths[0].parent, self.paths[1].parent)
        self.assert_completion(1)

    async def test_missing_material_aborts_before_the_callers_followup_files(self):
        await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        self.missing_material = True
        glb, contract = self.base / "written.glb", self.base / "written.asset.json"

        def followup_files():
            # This checks abort propagation, not the real export tool's ordering:
            # upstream can already have exported a GLB before querying materials.
            self.helpers._material_groups([G1])
            glb.write_text("fixture geometry", encoding="utf-8")
            contract.write_text("fixture metadata", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "material report was not received"):
            await self.invoke("export_asset_contract", followup_files)
        self.assertFalse(glb.exists())
        self.assertFalse(contract.exists())
        self.assertTrue(self.paths[0].is_file())
        self.assertFalse(self.paths[1].exists())
        self.assert_completion(1)

    async def test_public_import_keeps_object_ids_when_its_report_is_missing_or_bad(self):
        await self.invoke("fixture_receive", self.receive)
        old_report = self.paths[-1]

        def original_result():
            payload = self.receive()
            text = json.dumps(payload)
            return ToolResult(content=text, structured_content={"result": text})

        for report in (None, "{bad-json", '{"stamped": 2}'):
            with self.subTest(report=report):
                self.report_text = report
                before = len(self.paths)
                result = await self.invoke("import_asset_contract", original_result)
                payload = json.loads(result.content[0].text)
                self.assertEqual(payload["status"], "error")
                self.assertEqual(payload["imported_guids"], [G1, G2])
                self.assertEqual(Path(payload["report_path"]), self.paths[-1])
                self.assertEqual(len(self.paths) - before, 2)
                self.assertEqual(self.paths[-1].parent, self.paths[-2].parent)
                self.assertNotEqual(old_report.parent, self.paths[-1].parent)
                self.assert_completion(3)
        self.assertEqual(len({path.parent for path in self.paths}), 4)
        self.assertEqual(json.loads(old_report.read_text(encoding="utf-8")), REPORT)

    async def test_caught_native_failure_still_blocks_the_next_operation(self):
        self.native_reply = '{"status":"error","message":"Execution timed out (60s)."}'
        with self.assertRaisesRegex(RuntimeError, "material report was not received"):
            await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        state = self.runtime.completion()
        self.assertTrue(state["uncertain"], state)
        self.assertEqual(len(state["transport"]["requests"]), 1)
        self.assertFalse(state["transport"]["requests"][0]["acknowledged"])
        with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
            await self.invoke("fixture_material", lambda: self.helpers._material_groups([G1]))
        self.assertEqual(len(self.paths), 1)
