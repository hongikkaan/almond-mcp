"""Public import results stay observable without the legacy GUID-list side effects."""
import asyncio
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid

from fastmcp import Client, FastMCP
from almond_mcp.features.exchange import tools as exchange_tools


class NativeImport:
    """Controlled Rhino transport; the real tool and receipt reader run unchanged."""
    def __init__(self, folder, *, count=2, receipt=True, count_delta=0, restore_count=None):
        self.folder = folder
        self.ids = [str(uuid.uuid4()) for _ in range(count)]
        self.receipt = receipt
        self.count_delta = count_delta
        self.restore_count = count if restore_count is None else restore_count
        self.scripts = []

    def send(self, payload, **kwargs):
        request = json.loads(payload)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        assert request["type"] == "execute"
        self.scripts.append(request["script"])
        if len(self.scripts) == 1:
            if self.receipt:
                (self.folder / "almond_imported.txt").write_text("\n".join(self.ids), encoding="utf-8")
            return json.dumps({"status": "success", "result": {"imported_count": len(self.ids) + self.count_delta}})
        (self.folder / "almond_import_report.json").write_text(json.dumps({
            "stamped": len(self.ids), "deduped": 0, "width": 100, "depth": 100, "height": 100}))
        return json.dumps({"status": "success", "result": {"restored_count": self.restore_count}})


def server(native):
    contract = {"asset_id": "import-example", "source_app": "blender", "materials": [],
                "spatial": {"anchor": "bottom_center"}, "_resolved_file": str(native.folder / "model.glb")}
    context = SimpleNamespace(
        exchange=SimpleNamespace(load_contract=lambda _: copy.deepcopy(contract),
                                 dimension_report=lambda contract, report: {"status": "match"}),
        material_library=SimpleNamespace(get=lambda _: None),
        tempfile=SimpleNamespace(gettempdir=lambda: str(native.folder)),
        _send_and_receive=native.send)
    mcp = FastMCP("exchange-receipt")
    context.__dict__.update(exchange_tools.register(mcp, context))
    return mcp


def call_import(native):
    async def run():
        async with Client(server(native)) as client:
            reply = await client.call_tool("import_asset_contract", {"contract_path": "contract.json"})
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

    def test_restore_boolean_is_not_a_confirmed_object_count(self):
        with tempfile.TemporaryDirectory() as folder:
            native = NativeImport(Path(folder), count=1, restore_count=True)
            result = call_import(native)
            self.assertEqual(result["status"], "error", result)
            self.assertTrue(result["requires_reconciliation"])
            self.assertEqual(result["imported_guids"], native.ids)


if __name__ == "__main__":
    unittest.main()
