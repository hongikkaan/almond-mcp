"""COS consumes engine hooks and native receipts without replacing original functions."""
import asyncio
import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cos_worker
from runtime import WORKER_STATE_TOOL


TOOL = {"name": "fixture", "inputSchema": {"type": "object", "properties": {}}}
CATALOG = {"tools": [TOOL], "packages": {"almond-mcp": "fixture"}}


class FixtureMcp:
    def __init__(self):
        self.registered = {}

    async def list_tools(self):
        return [SimpleNamespace(to_mcp_tool=lambda: SimpleNamespace(model_dump=lambda **_: dict(TOOL)))]

    def tool(self, *, name):
        def register(function):
            self.registered[name] = function
            return function
        return register


class CompletionTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_receipt_and_process_identity_are_preserved(self):
        state = {"pending": True, "uncertain": True, "operation_id": "operation",
                 "native": {"pending": 1, "phase": "running"}}
        runtime = SimpleNamespace(completion=lambda: dict(state))
        mcp = FixtureMcp()
        with patch.object(cos_worker, "process_identity", return_value={"pid": 123, "process_start_ticks": "456"}):
            await cos_worker.configure_cos(mcp, None, {"attachment": "cos", "storage_protocol": 2},
                                           {}, runtime, CATALOG)
        actual = mcp.registered[WORKER_STATE_TOOL]()
        self.assertEqual(actual, dict(state, pid=123, process_start_ticks="456"))
        state.update(pending=False, uncertain=False)
        self.assertFalse(mcp.registered[WORKER_STATE_TOOL]()["pending"])

    async def test_configure_rejects_legacy_and_foreign_bindings(self):
        for binding in ({"attachment": "cos"}, {"attachment": "terminal", "storage_protocol": 2}):
            with self.assertRaisesRegex(RuntimeError, "protocol-2"):
                await cos_worker.configure_cos(FixtureMcp(), None, binding, {}, None, CATALOG)

    def test_post_lease_validation_rejects_a_changed_generation(self):
        binding = {"attachment": "cos", "storage_protocol": 2, "token": "first"}
        args = SimpleNamespace(session="owned/ready.json", token="first")
        entry = SimpleNamespace(read_binding=lambda *_: (dict(binding), {}))
        cos_worker.validate_cos_binding(entry, args, binding, {})
        entry.read_binding = lambda *_: (dict(binding, token="second"), {})
        with self.assertRaisesRegex(RuntimeError, "changed"):
            cos_worker.validate_cos_binding(entry, args, binding, {})

    def test_main_passes_hooks_without_replacing_entry_functions(self):
        binding = {"attachment": "cos", "storage_protocol": 2}
        serve, configure = object(), object()
        captured = {}
        def entry_main(argv, *, validate_binding, configure):
            captured.update(argv=argv, validate=validate_binding, configure=configure)
            validate_binding(SimpleNamespace(session="owned/ready.json", token="token"), binding, {})
            return 17
        entry = SimpleNamespace(main=entry_main, serve=serve, configure_project_context=configure,
                                read_binding=lambda *_: (dict(binding), {}))
        original_path = list(sys.path)
        try:
            with patch.dict(sys.modules, {"mcp_server": entry}), \
                    patch.dict(os.environ, {"ALMONDCOS_SESSION_TOKEN": "token"}), \
                    patch.object(sys, "argv", ["cos_worker", "--session", "owned/ready.json",
                                               "--port", "5501", "--connection-id", "connection"]), \
                    patch.object(cos_worker, "load_catalog", return_value=CATALOG), \
                    patch.object(cos_worker, "check_contract"):
                self.assertEqual(cos_worker.main(), 17)
        finally:
            sys.path[:] = original_path
        self.assertIs(entry.serve, serve)
        self.assertIs(entry.configure_project_context, configure)
        self.assertTrue(callable(captured["configure"]))
        self.assertEqual(captured["argv"][:2], ["--session", "owned/ready.json"])
