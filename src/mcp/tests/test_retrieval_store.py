import json
import tempfile
import unittest
from pathlib import Path

from almond_mcp.retrieval_store import AlmondStore


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class RetrievalStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = AlmondStore(Path(self.temp_dir.name) / "state.sqlite3")
        ikea_manifest = json.loads(
            (PROJECT_ROOT / "asset" / "models" / "IkeaFurniturefiles" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        drawing_manifest = json.loads(
            (PROJECT_ROOT / "asset" / "drawing" / "DrawingAssetfiles" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for asset in ikea_manifest["assets"]:
            asset["file_available"] = (
                PROJECT_ROOT / "asset" / "models" / "IkeaFurniturefiles" / asset["file"]
            ).is_file()
        for asset in drawing_manifest["assets"]:
            asset["file_available"] = (
                PROJECT_ROOT / "asset" / "drawing" / "DrawingAssetfiles" / asset["file"]
            ).is_file()
        # Both libraries grow over time; keep the manifest counts so the
        # assertions below track the data instead of hardcoding totals.
        self.ikea_asset_count = len(ikea_manifest["assets"])
        self.drawing_asset_count = len(drawing_manifest["assets"])
        self.store.sync_assets(
            drawing_manifest["assets"],
            library_id="drawing_assets",
        )
        self.store.sync_assets(ikea_manifest["assets"], library_id="ikea")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fts_and_structured_filters_return_compact_cards(self):
        chairs = self.store.search_assets(
            query="reading chair",
            library_id="ikea",
            category="chair",
        )
        self.assertGreaterEqual(chairs["total"], 1)
        self.assertTrue(all("asset_id" in asset for asset in chairs["assets"]))
        self.assertTrue(all("warehouse_url" not in asset for asset in chairs["assets"]))

        compact_sofa = self.store.search_assets(
            query="compact living room",
            library_id="ikea",
            category="sofa",
            max_width_mm=2000,
            exact_dimensions_only=True,
        )
        self.assertEqual(
            [asset["asset_id"] for asset in compact_sofa["assets"]],
            ["ikea-sg-klippan-s49010615"],
        )

        context_tree = self.store.search_assets(
            query="landscape tree",
            library_id="drawing_assets",
            category="tree",
        )
        self.assertGreaterEqual(context_tree["total"], 1)
        self.assertEqual(context_tree["assets"][0]["source_class"], "drawing_asset")
        self.assertEqual(context_tree["assets"][0]["brand"], "Generic")
        self.assertEqual(context_tree["assets"][0]["library_id"], "drawing_assets")

        ikea_tree = self.store.search_assets(
            query="landscape tree",
            library_id="ikea",
        )
        self.assertEqual(ikea_tree["total"], 0)
        self.assertEqual(
            self.store.asset_stats("ikea")["total"], self.ikea_asset_count
        )
        self.assertEqual(
            self.store.asset_stats("drawing_assets")["total"],
            self.drawing_asset_count,
        )


    def test_plan_records_dependencies_without_enforcing_order(self):
        plan = self.store.create_plan(
            "Furnish a compact apartment",
            scope="interior",
        )
        plan_id = plan["plan_id"]
        self.store.update_plan_step(plan_id, "retrieve_assets", "completed")

        self.store.update_plan_step(plan_id, "inspect_rooms", "completed")
        updated = self.store.update_plan_step(
            plan_id,
            "retrieve_assets",
            "completed",
            output_refs=["ikea-sg-klippan-s49010615"],
        )
        steps = {step["step_id"]: step for step in updated["steps"]}
        self.assertEqual(steps["retrieve_assets"]["status"], "completed")
        self.assertEqual(
            steps["retrieve_assets"]["output_refs"],
            ["ikea-sg-klippan-s49010615"],
        )

        drawing_plan = self.store.create_plan(
            "Produce a technical axonometric",
            scope="drawing",
        )
        self.assertEqual(
            drawing_plan["steps"][0]["step_id"],
            "freeze_scene",
        )
        self.assertEqual(
            drawing_plan["steps"][-1]["step_id"],
            "validate_drawing",
        )


class SceneLedgerFixesTests(RetrievalStoreTests):
    """Regressions from the 2026-07-14 stress test (issues #3 and #4)."""






class ValidationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = AlmondStore(Path(self.temp_dir.name) / "state.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_list_validation_runs(self):
        request = {"structure_type": "truss", "load_kn": 25.0, "material": "S355"}
        result = {
            "status": "pass",
            "passed": True,
            "confidence": "high",
            "verdict": "[KARAMBA 3.1 API, HIGH CONFIDENCE] PASSED",
            "warnings": ["No anchor points declared; supporting 3 lowest-Z node(s)."],
            "results": {
                "analysis_method": "api",
                "span_m": 6.0,
                "max_deflection_mm": 0.4,
                "deflection_limit_mm": 24.0,
                "utilization_ratio": 0.01,
                "max_stress_mpa": 7.5,
                "yield_stress_mpa": 355.0,
                "reactions_kn": 25.002,
            },
        }
        run_id = self.store.record_validation_run(request, result, ["guid-a", "guid-b"])
        self.assertGreater(run_id, 0)

        runs = self.store.list_validation_runs()
        self.assertEqual(len(runs), 1)
        run = runs[0]
        self.assertEqual(run["structure_type"], "truss")
        self.assertEqual(run["material"], "S355")
        self.assertEqual(run["analysis_method"], "api")
        self.assertEqual(run["confidence"], "high")
        self.assertTrue(run["passed"])
        self.assertEqual(run["member_count"], 2)
        self.assertAlmostEqual(run["reactions_kn"], 25.002)
        self.assertEqual(len(run["warnings"]), 1)
        self.assertEqual(run["guids"], ["guid-a", "guid-b"])

        # newest first
        self.store.record_validation_run(request, result, ["guid-c"])
        runs = self.store.list_validation_runs()
        self.assertEqual(runs[0]["member_count"], 1)


if __name__ == "__main__":
    unittest.main()
