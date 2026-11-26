import asyncio
import sys
from uuid import uuid4

import pytest

import codex_host
from codex_host import Worker
from fixtures import worker_stdio


def test_worker_verifies_contract_and_forwards_call_identity(monkeypatch):
    async def scenario():
        parameters = codex_host.StdioServerParameters
        worker_mode = "compatible"

        def launch(**settings):
            return parameters(
                **{**settings, "command": sys.executable,
                   "args": ["-B", "-u", worker_stdio.__file__, worker_mode]},
            )

        monkeypatch.setattr(codex_host, "StdioServerParameters", launch)
        token, connection_id, caller = uuid4().hex, uuid4().hex, uuid4().hex
        binding = {"token": token, "ready_path": "offline-ready.json", "port": 1}
        catalog = {"tools": [{"name": worker_stdio.TOOL, "inputSchema": worker_stdio.INPUT}]}
        worker = Worker(binding, connection_id, catalog)
        try:
            await worker.start()
            result = await worker.call(
                worker_stdio.TOOL, {"code": "result = 42"}, caller_request_id=caller,
            )
            assert not result.is_error
            assert result.structured_content == {"code": "result = 42", "caller": caller, "token": token}
        finally:
            await worker.close()

        worker_mode = "changed"
        incompatible = Worker(binding, connection_id, catalog)
        try:
            with pytest.raises((RuntimeError, ExceptionGroup)) as blocked:
                await incompatible.start()
            if isinstance(blocked.value, ExceptionGroup):
                assert blocked.group_contains(RuntimeError, match="tool schemas changed")
            else:
                assert "tool schemas changed" in str(blocked.value)
        finally:
            await incompatible.close()

    asyncio.run(asyncio.wait_for(scenario(), 20))
