"""Private asset imports preserve native receipt and managed completion guarantees."""
import asyncio
import copy
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
import uuid

from fastmcp import Client, FastMCP
import pytest

from almond_mcp.features.exchange.tools import Exchange, ExchangeReports
from mcp_server import managed_exchange_reports
from project import connection_paths, read_json, write_json
from shared_store import ProjectRuntime


def output_path(script, writer, folder):
    match = re.search(rf'{writer}\(\s*("(?:[^"\\]|\\.)*")\s*,', script)
    assert match, f"Missing {writer} output path"
    path = Path(json.loads(match.group(1)))
    assert path.parent == folder
    return path


class NativeImport:
    """Controlled Rhino transport; the real import helper and receipt reader run unchanged."""
    def __init__(self, folder, *, count=2, receipt=True, count_delta=0, restore_count=None, report=True):
        self.folder = folder
        self.ids = [str(uuid.uuid4()) for _ in range(count)]
        self.receipt = receipt
        self.count_delta = count_delta
        self.restore_count = count if restore_count is None else restore_count
        self.report = report
        self.scripts = []

    def send(self, payload, **kwargs):
        request = json.loads(payload)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        assert request["type"] == "execute"
        self.scripts.append(request["script"])
        if len(self.scripts) == 1:
            if self.receipt:
                output_path(request["script"], "WriteAllLines", self.folder).write_text("\n".join(self.ids), encoding="utf-8")
            return json.dumps({"status": "success", "result": {"imported_count": len(self.ids) + self.count_delta}})
        if self.report:
            output_path(request["script"], "WriteAllText", self.folder).write_text(json.dumps({
                "stamped": len(self.ids), "deduped": 0, "width": 100, "depth": 100, "height": 100}))
        return json.dumps({"status": "success", "result": {"restored_count": self.restore_count}})


def server(native, runtime=None):
    contract = {"asset_id": "import-example", "source_app": "blender", "materials": [],
                "spatial": {"anchor": "bottom_center"}, "_resolved_file": str(native.folder / "model.glb")}
    send = native.send
    reports = lambda: ExchangeReports(native.folder)
    if runtime is not None:
        send = lambda payload, **kwargs: runtime.send(native.send, payload, **kwargs)
        reports = lambda: managed_exchange_reports(runtime)
    exchange = Exchange(send, SimpleNamespace(get=lambda _: None), reports,
                        dimension_report=lambda contract, report: {"status": "match"})
    mcp = FastMCP("exchange-receipt")

    @mcp.tool(name="fixture_01-place_asset")
    def place_asset() -> str:
        return json.dumps(exchange.receive_contract(copy.deepcopy(contract), 0, 0, 0, 0, "fixture"))

    if runtime is not None:
        mcp.add_middleware(runtime)
    return mcp


def call_import(native, runtime=None):
    async def run():
        async with Client(server(native, runtime)) as client:
            reply = await client.call_tool("fixture_01-place_asset", {})
            return json.loads(reply.content[0].text)
    return asyncio.run(run())


class ExchangeReceiptTests(unittest.TestCase):
    def test_structured_completion_returns_receipt_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder))
            result = call_import(native)
            self.assertEqual(result["status"], "success", result)
            self.assertEqual(result["imported_guids"], native.ids)
            self.assertEqual(result["imported_count"], 2)
            self.assertEqual(result["metadata_restored"], 2)

    def test_large_import_does_not_need_native_result_guid_array(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder), count=2000)
            result = call_import(native)
            self.assertEqual(result["status"], "success", result)
            self.assertEqual(result["imported_guids"], native.ids)

    def test_missing_receipt_stops_before_restore_and_reports_uncertainty(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder), receipt=False)
            result = call_import(native)
            self.assertEqual(result["status"], "error")
            self.assertTrue(result["requires_reconciliation"])
            self.assertIsNone(result["mutation_applied"])
            self.assertEqual(len(native.scripts), 1)

    def test_mismatched_receipt_is_not_an_empty_or_successful_import(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder), count_delta=1)
            result = call_import(native)
            self.assertEqual(result["status"], "error")
            self.assertTrue(result["requires_reconciliation"])
            self.assertEqual(len(native.scripts), 1)

    def test_completed_empty_import_cleans_its_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder), count=0)
            result = call_import(native)
            self.assertEqual(result["status"], "error")
            self.assertEqual(len(native.scripts), 1)
            self.assertFalse(list(Path(folder).glob("almond_imported_*.txt")))

    def test_restore_boolean_is_not_a_confirmed_object_count(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder), count=1, restore_count=True)
            result = call_import(native)
            self.assertEqual(result["status"], "error", result)
            self.assertTrue(result["requires_reconciliation"])
            self.assertEqual(result["imported_guids"], native.ids)

    def test_interleaved_imports_restore_their_own_objects(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            ids = {"A": str(uuid.uuid4()), "B": str(uuid.uuid4())}
            restored = {}
            other = {}

            def receive(label):
                contract = {"asset_id": label, "materials": [], "spatial": {},
                            "_resolved_file": str(folder / f"{label}.glb")}
                return exchange.receive_contract(contract, 0, 0, 0, 0, "fixture")

            def send(payload, **kwargs):
                request = json.loads(payload)
                if request["type"] == "get_rhino_context":
                    return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
                script = request["script"]
                if "added.Select" in script:
                    label = "A" if "A.glb" in script else "B"
                    output_path(script, "WriteAllLines", folder).write_text(ids[label], encoding="utf-8")
                    if label == "A":
                        other["result"] = receive("B")
                    return json.dumps({"status": "success", "result": {"imported_count": 1}})
                label = re.search(r'almond:asset_id", "([AB])"', script).group(1)
                selected = re.search(r'foreach \(string s in new\[\] \{([^}]+)\}', script).group(1)
                restored[label] = re.findall(r'"([0-9a-f-]{36})"', selected)
                output_path(script, "WriteAllText", folder).write_text(
                    json.dumps({"stamped": 0, "deduped": 0, "width": 1, "depth": 1, "height": 1}), encoding="utf-8")
                return json.dumps({"status": "success", "result": {"restored_count": 1}})

            exchange = Exchange(send, SimpleNamespace(get=lambda _: None), lambda: ExchangeReports(folder),
                                dimension_report=lambda contract, report: {"status": "match"})
            first = receive("A")
            for label, result in (("A", first), ("B", other["result"])):
                self.assertEqual(result["status"], "success", result)
                self.assertEqual(result["imported_guids"], [ids[label]])
                self.assertEqual(restored[label], [ids[label]])

    def test_lost_import_reply_preserves_receipt_and_reports_uncertainty(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder))
            original_send = native.send

            def lost_reply(payload, **kwargs):
                reply = original_send(payload, **kwargs)
                if json.loads(payload)["type"] == "execute":
                    raise TimeoutError("reply lost after native import")
                return reply

            native.send = lost_reply
            result = call_import(native)
            self.assertEqual(result["status"], "error")
            self.assertTrue(result["requires_reconciliation"])
            self.assertIsNone(result["mutation_applied"])
            self.assertEqual(len(list(Path(folder).glob("almond_imported_*.txt"))), 1)


@pytest.mark.parametrize("outcome", ["confirmed", "lost-reply", "missing-report"])
def test_managed_import_owns_receipts_until_native_completion(outcome):
    with tempfile.TemporaryDirectory(prefix="한글 작업-") as folder:
        model = Path(folder) / "fixture.3dm"
        model.touch()
        token = uuid.uuid4().hex
        locations = connection_paths(model, "A", token, create=True)
        ready = Path(locations["ready_path"])
        binding = {**locations, "schema": "almond-project", "storage_protocol": 2,
                   "token": token, "label": "A", "port": 5501, "valid": True}
        write_json(ready, binding)
        write_json(ready.with_name("worker.json"), {"pid": 1, "process_start_ticks": "1"})
        runtime = ProjectRuntime(SimpleNamespace(token=token, session=str(ready)),
                                 binding, locations, check_owner=False)
        native = NativeImport(model.parent, report=outcome != "missing-report")
        respond = native.send
        requests = []

        def send(payload, **kwargs):
            envelope = json.loads(payload)
            assert envelope["schema"] == "almond-native-request"
            assert envelope["storage_protocol"] == 2 and envelope["token"] == token
            requests.append(envelope)
            assert len({request["request_id"] for request in requests}) == len(requests)
            operation = read_json(ready.with_name("operation.json"))
            assert envelope["operation_id"] == operation["operation_id"]
            native.folder = Path(locations["call_root"]) / operation["operation_id"]
            assert native.folder.is_dir()
            if len(requests) == 1:
                assert not list(native.folder.iterdir())
            sequence = len(requests)
            reply = respond(envelope["payload"], **kwargs)
            if outcome == "lost-reply" and sequence == 2:
                raise TimeoutError("reply lost after native import")
            write_json(ready.with_name("native.json"), {
                "schema": "almond-native", "token": token, "operation_id": operation["operation_id"],
                "sequence": sequence, "pending": 0, "completion_status": "completed",
            })
            return json.dumps({
                **envelope, "schema": "almond-native-response", "payload": reply,
                "completion_status": "completed", "native_sequence": sequence,
            })

        native.send = send
        result = call_import(native, runtime)
        state = read_json(ready.with_name("operation.json"))["state"]
        receipt = output_path(native.scripts[0], "WriteAllLines", native.folder)
        if outcome == "lost-reply":
            assert result["status"] == "error" and result["requires_reconciliation"], result
            assert result["mutation_applied"] is None
            assert state == "unconfirmed" and runtime.completion()["native_uncertain"]
            assert receipt.read_text(encoding="utf-8").splitlines() == native.ids
            assert len(requests) == 2
        else:
            assert result["imported_guids"] == native.ids
            if outcome == "missing-report":
                assert result["status"] == "error" and "report is unverified" in result["message"], result
            else:
                assert result["status"] == "success" and result["metadata_restored"] == len(native.ids), result
            assert state == "completed" and not runtime.completion()["native_uncertain"]
            assert len(requests) == 3 and not native.folder.exists()


if __name__ == "__main__":
    unittest.main()
