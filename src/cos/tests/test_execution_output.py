"""Public output choices must not weaken retained-file recovery or rerun Rhino."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from execution_recovery import read_bound_execution
from runtime import ENGINE


class RetainedExecutionOutputTests(unittest.TestCase):
    def setUp(self):
        original_path = sys.path[:]
        sys.path.insert(0, str(ENGINE))
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), original_path))
        from project import connection_paths, write_json
        base = Path(__file__).resolve().parents[3] / "data"
        base.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="_execution_output_", dir=base)
        self.addCleanup(self.directory.cleanup)
        model = Path(self.directory.name) / "fixture.3dm"
        model.write_bytes(b"PATH FIXTURE; NEVER OPENED BY RHINO")
        self.locations = connection_paths(model, "A", "a" * 32, create=True)
        self.binding = dict(self.locations, schema="almond-project", storage_protocol=2, token="a" * 32,
            label="A", pid=123, process_start_ticks="456", document_serial=7)
        write_json(self.locations["ready_path"], self.binding)
        self.raw = dict(request_id="b" * 32, completed=True, status="success",
            mutation_state="completed", operation_id="c" * 32,
            result={"layers": [{"name": "Glass", "count": 18}]},
            result_page={"type": "object", "pages": {"layers": {
                "total": 21, "offset": 20, "returned": 1, "next_offset": None}}},
            result_file="retained/result.json", result_sha256="d" * 64,
            completion_state="completed", native_completed=True)
        self.start_patch("storage_cleanup.process_identity_alive", return_value=False)
        self.adapter = self.start_patch("rhinocode.RhinocodeExecution").return_value
        self.adapter.get_execution.side_effect = lambda **_: deepcopy(self.raw)
        self.adapter.execute = Mock(side_effect=AssertionError("Recovery dispatched Rhino work"))

    def start_patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def test_retained_page_is_compact_but_keeps_target_and_page_evidence(self):
        arguments = dict(request_id=self.raw["request_id"], offset=20, limit=5,
                         result_fields=["layers"], include_diagnostics=False)
        original = deepcopy(arguments)
        result = read_bound_execution(self.binding, arguments)
        self.assertEqual(result["result"], self.raw["result"])
        self.assertEqual(result["result_page"], self.raw["result_page"])
        self.assertEqual(result["target_identity"], {key: self.binding[key] for key in
            ("pid", "process_start_ticks", "document_serial", "model_path")})
        self.assertFalse(result["rhino_process_alive"])
        self.assertNotIn("result_file", result)
        self.assertNotIn("operation_id", result)
        self.assertEqual(arguments, original)
        self.adapter.get_execution.assert_called_once_with(request_id=self.raw["request_id"],
            offset=20, limit=5, result_fields=["layers"])
        self.adapter.execute.assert_not_called()

    def test_explicit_diagnostics_keeps_all_original_evidence(self):
        result = read_bound_execution(self.binding,
            dict(request_id=self.raw["request_id"], include_diagnostics=True))
        for key, value in self.raw.items():
            self.assertEqual(result[key], value)
        self.assertEqual(result["target_identity"]["model_path"], self.binding["model_path"])
        self.assertFalse(result["rhino_process_alive"])
        self.adapter.get_execution.assert_called_once_with(request_id=self.raw["request_id"])
        self.adapter.execute.assert_not_called()

    def test_pending_partial_and_result_errors_keep_details_without_opt_in(self):
        original = deepcopy(self.raw)
        for changes in ({"completed": False, "status": "pending", "pending": True},
                        {"status": "error", "mutation_state": "partial", "error": "Script failed"},
                        {"exit_code": 1},
                        {"result_display_error": "Retained result no longer matches its completion receipt"}):
            with self.subTest(changes=changes):
                self.raw = dict(original, **changes)
                result = read_bound_execution(self.binding, {"request_id": self.raw["request_id"]})
                for key, value in self.raw.items():
                    self.assertEqual(result[key], value)
        self.adapter.execute.assert_not_called()

    def test_diagnostics_option_does_not_bypass_exact_target_validation(self):
        from project import read_json, write_json
        changed = read_json(self.locations["ready_path"])
        changed["document_serial"] = 8
        write_json(self.locations["ready_path"], changed)
        for include_diagnostics in (False, True):
            with self.subTest(include_diagnostics=include_diagnostics):
                with self.assertRaisesRegex(ValueError, "target changed"):
                    read_bound_execution(self.binding, dict(request_id=self.raw["request_id"],
                        include_diagnostics=include_diagnostics))
        self.adapter.get_execution.assert_not_called()
        self.adapter.execute.assert_not_called()

    def test_non_boolean_diagnostics_is_rejected_before_reading_the_binding(self):
        with patch("execution_recovery._locations", side_effect=AssertionError("Read an invalid request")) as locate:
            for flag in (None, 0, 1, "true", []):
                with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "boolean"):
                    read_bound_execution(self.binding, dict(include_diagnostics=flag))
            locate.assert_not_called()
        self.adapter.get_execution.assert_not_called()


if __name__ == "__main__":
    unittest.main()
