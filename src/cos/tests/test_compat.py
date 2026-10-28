"""COS worker configuration through the common engine entry point."""
import asyncio
import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ConfigureCompatTests(unittest.TestCase):
    def test_main_configures_worker_state_through_the_common_engine(self):
        import external_worker
        from runtime import WORKER_STATE_TOOL

        tool = {"name": "fixture", "inputSchema": {"type": "object", "properties": {}}}
        catalog = {"tools": [tool], "packages": {"almond-mcp": "fixture"}}
        binding = {"attachment": "cos", "storage_protocol": 2}
        locations = {"call_root": "fixture/calls/token"}
        args = SimpleNamespace(session="fixture/ready.json", token="token")
        state = {"pending": False, "uncertain": False, "native": {"pending": 0}}
        runtime = SimpleNamespace(completion=lambda: dict(state))
        bound_sender = object()
        server = SimpleNamespace(_send_and_receive=bound_sender)
        registered = {}

        async def list_tools():
            return [SimpleNamespace(to_mcp_tool=lambda: SimpleNamespace(model_dump=lambda **_: dict(tool)))]

        def register_tool(*, name):
            def register(function):
                registered[name] = function
                return function
            return register

        mcp = SimpleNamespace(list_tools=list_tools, tool=register_tool)

        def entry_main(argv, *, validate_binding, configure):
            validate_binding(args, binding, locations)
            asyncio.run(configure(mcp, args, binding, locations, runtime))
            return 17

        entry = SimpleNamespace(main=entry_main, read_binding=lambda *_: (dict(binding), locations))
        original_path = list(sys.path)
        try:
            with patch.dict(sys.modules, {"mcp_server": entry, "almond_mcp": SimpleNamespace(server=server)}), \
                    patch.dict(os.environ, {"ALMONDRHINO_SESSION_TOKEN": "token", "ALMONDRHINO_CATALOG_ID": external_worker.catalog_identity(catalog)}), \
                    patch.object(sys, "argv", ["external_worker", "--session", args.session, "--port", "5501",
                                               "--connection-id", "connection"]), \
                    patch.object(external_worker, "load_catalog", return_value=catalog), \
                    patch.object(external_worker, "check_contract"), \
                    patch.object(external_worker, "process_identity", return_value={"pid": 123}):
                self.assertEqual(external_worker.main(), 17)
        finally:
            sys.path[:] = original_path
        self.assertIs(server._send_and_receive, bound_sender)
        self.assertEqual(registered[WORKER_STATE_TOOL](), dict(state, pid=123))
