"""BDD for reading useful retained results without repeating execution evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from mcp_server import configure_project_context


def completed_page():
    """A final two-row page like the live layers_by_count design query."""
    return {
        "request_id": "a" * 32,
        "completed": True,
        "status": "success",
        "mutation_state": "completed",
        "pending": False,
        "uncertain": False,
        "completion_state": "completed",
        "native_completed": True,
        "operation_id": "b" * 32,
        "language": "python",
        "native_status": "success",
        "exit_code": 0,
        "execution_complete": True,
        "undo": {"owned": True, "closed": True},
        "user_code_started": True,
        "user_code_completed": True,
        "result_available": True,
        "result_bytes": 14000,
        "result_sha256": "c" * 64,
        "result_file": "C:/project/.almond/tmp/python/" + "d" * 32 + "/" + "b" * 32 + "/rc-aaaaaaaaaaaa/result.json",
        "result": {"layers_by_count": [
            {"name": "M::Glass", "count": 18},
            {"name": "M::Steel", "count": 12},
        ]},
        "result_page": {
            "type": "object", "available_fields": ["layers_by_count", "visibility"],
            "field_count": 2, "fields_truncated": False,
            "pages": {"layers_by_count": {"total": 22, "offset": 20,
                "returned": 2, "next_offset": None}},
        },
        "runtime_completion": {
            "operation_id": "b" * 32, "pending": False, "uncertain": False,
            "native_pending": False, "native_uncertain": False,
            "external_pending": False, "external_uncertain": False,
        },
    }


class ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self, **_):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


class ExecutionOutputTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.raw = completed_page()
        self.runtime = SimpleNamespace(
            get_rhino_execution=Mock(side_effect=lambda *args: deepcopy(self.raw)),
            execute_rhinocode=Mock(side_effect=AssertionError("A result read dispatched Rhino work")),
        )
        collector = ToolCollector()
        await configure_project_context(collector, SimpleNamespace(), {}, {}, runtime=self.runtime)
        self.read = collector.tools["get_rhino_execution"]

    def test_final_page_is_useful_without_repeated_execution_diagnostics(self):
        before = deepcopy(self.raw)
        result = self.read(request_id=self.raw["request_id"], result_fields=["layers_by_count"],
                           offset=20, limit=5, include_ids=False)
        self.assertEqual(result["result"], before["result"])
        self.assertEqual(result["result_page"], before["result_page"])
        self.assertEqual(result["request_id"], before["request_id"])
        self.assertTrue(result["completed"])
        self.assertEqual(result["mutation_state"], "completed")
        self.assertNotIn("runtime_completion", result)
        self.assertNotIn("result_file", result)
        self.assertNotIn("result_sha256", result)
        self.assertNotIn("undo", result)
        self.assertLess(len(json.dumps(result)), len(json.dumps(before)) / 2)
        self.assertEqual(self.raw, before)
        self.runtime.get_rhino_execution.assert_called_once_with(
            before["request_id"], 20, 5, True, False, ["layers_by_count"], False)
        self.runtime.execute_rhinocode.assert_not_called()

    def test_diagnostics_are_available_on_explicit_request(self):
        result = self.read(request_id=self.raw["request_id"], include_diagnostics=True)
        self.assertEqual(result, self.raw)
        self.runtime.get_rhino_execution.assert_called_once_with(
            self.raw["request_id"], 0, 100, True, False, None, True)
        self.runtime.execute_rhinocode.assert_not_called()

    def test_non_boolean_diagnostics_is_rejected_before_runtime_reconciliation(self):
        for flag in (None, 0, 1, "true", []):
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "boolean"):
                self.read(include_diagnostics=flag)
        self.runtime.get_rhino_execution.assert_not_called()
        self.runtime.execute_rhinocode.assert_not_called()

    def test_requested_logs_keep_text_capture_warnings_and_byte_pages(self):
        self.raw.update(stdout="next chunk", stdout_page={"offset": 256, "returned_bytes": 10,
            "retained_bytes": 266, "next_offset": None},
            stderr="", stderr_page={"offset": 0, "returned_bytes": 0,
            "retained_bytes": 0, "next_offset": None},
            cli_stdout="CLI response", cli_stdout_page={"offset": 0, "returned_bytes": 12,
            "retained_bytes": 12, "next_offset": None},
            cli_stderr_display_error="Cannot read the CLI diagnostic file",
            stdout_capture={"truncated": True}, stderr_capture={"truncated": False},
            log_capture={"cli_stdout": {"bytes": 12, "total_bytes": 12, "truncated": False}})
        result = self.read(include_stdout=True)
        for name in ("stdout", "stderr", "cli_stdout", "cli_stderr_display_error",
                     "stdout_page", "stderr_page", "cli_stdout_page", "stdout_capture",
                     "stderr_capture", "log_capture"):
            self.assertEqual(result[name], self.raw[name])

    def test_pending_failed_and_partial_outcomes_keep_their_evidence(self):
        for changes in (
            {"completed": False, "status": "pending", "pending": True},
            {"completed": False, "status": "unconfirmed", "uncertain": True},
            {"status": "error", "error": "User code failed", "mutation_state": "partial"},
            {"status": "rejected", "mutation_state": "not_started"},
            {"mutation_state": "partial"},
            {"mutation_state": "unknown"},
        ):
            with self.subTest(changes=changes):
                self.raw = dict(completed_page(), **changes)
                self.assertEqual(self.read(), self.raw)

    def test_native_or_external_uncertainty_is_not_hidden_by_a_completed_receipt(self):
        for flag in ("pending", "uncertain", "native_pending", "native_uncertain",
                     "external_pending", "external_uncertain"):
            with self.subTest(flag=flag):
                self.raw = completed_page()
                self.raw["runtime_completion"][flag] = True
                self.assertEqual(self.read(), self.raw)

    def test_native_success_keeps_a_nonzero_cli_exit_visible(self):
        for exit_code in (1, -1):
            with self.subTest(exit_code=exit_code):
                self.raw = dict(completed_page(), exit_code=exit_code)
                self.assertEqual(self.read(), self.raw)
        for exit_code in (0, None):
            with self.subTest(exit_code=exit_code):
                self.raw = dict(completed_page(), exit_code=exit_code)
                self.assertNotIn("runtime_completion", self.read())
        self.raw.pop("exit_code")
        self.assertNotIn("runtime_completion", self.read())

    def test_result_errors_keep_original_file_and_hash_fallback(self):
        for changes in (
            {"result_display_error": "This page exceeds 65536 bytes"},
            {"result_display_error": "Retained result no longer matches its completion receipt"},
            {"result_error": "Could not serialize the script result"},
            {"cleanup_errors": ["Could not close Undo record"]},
        ):
            with self.subTest(changes=changes):
                self.raw = dict(completed_page(), **changes)
                self.assertEqual(self.read(), self.raw)

    def test_next_page_remains_discoverable_without_a_long_retained_file_path(self):
        self.raw["result_page"]["pages"]["layers_by_count"].update(total=25, next_offset=22)
        result = self.read(offset=20, limit=2)
        self.assertEqual(result["result_page"]["pages"]["layers_by_count"]["next_offset"], 22)
        self.assertNotIn("result_file", result)

    def test_status_only_read_reports_whether_a_result_can_be_requested(self):
        self.raw.pop("result")
        self.raw.pop("result_page")
        result = self.read(include_result=False)
        self.assertTrue(result["result_available"])
        self.assertNotIn("result", result)
        self.assertNotIn("result_file", result)

    def test_recovery_target_and_reconnect_information_remain_visible(self):
        self.raw.update(target_identity={"pid": 123, "process_start_ticks": "456",
            "document_serial": 7, "model_path": "C:/project/model.3dm"},
            rhino_process_alive=False, connection_state="unbound", requires_reconnect=True,
            recovery_only=True)
        result = self.read()
        for name in ("target_identity", "rhino_process_alive", "connection_state",
                     "requires_reconnect", "recovery_only"):
            self.assertEqual(result[name], self.raw[name])


if __name__ == "__main__":
    unittest.main()
