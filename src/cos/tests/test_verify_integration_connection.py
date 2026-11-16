"""Check receipt matching and release using Beyond's public tool responses."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


PROBE = Path(__file__).resolve().parents[1] / "tools/verify_integration_connection.py"
spec = importlib.util.spec_from_file_location("verify_integration_connection", PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize(("discovery", "ready", "released", "error", "tools"), [
    ({}, {}, True, "", 3),
    ({"model_path": "other.3dm"}, {}, True, "wrong Rhino process or model", 1),
    ({"process_start_ticks": "999"}, {}, True, "wrong Rhino process or model", 1),
    ({}, {"pid": 999}, True, "did not bind the intended Rhino PID", 3),
    ({}, {"model_path": "other.3dm"}, True, "did not bind the intended Rhino PID", 3),
    ({}, {"state": "recovering"}, True, "did not bind the intended Rhino PID", 3),
    ({}, {}, False, "did not release", 3),
])
def test_verifies_only_the_intended_live_document_and_releases_connection(
        tmp_path, discovery, ready, released, error, tools):
    model = tmp_path / "test.3dm"
    identity = {"pid": 42, "model_path": str(model), "host_id": "verified-host"}
    targets = [{**identity, "pid": 41, "host_id": "other-host"},
               {**identity, "state": "available", "process_start_ticks": "123", **discovery}]
    responses = [{"targets": targets}, {**identity, "state": "ready", **ready}, {"released": released}]
    client = SimpleNamespace(call_tool=AsyncMock(side_effect=[
        SimpleNamespace(is_error=False, structured_content=response) for response in responses
    ]))

    request = probe.verify_connection(client, 42, "123", model)
    if error:
        with pytest.raises(RuntimeError, match=error):
            asyncio.run(request)
    else:
        assert asyncio.run(request) == {
            **identity, "process_start_ticks": "123", "state": "ready", "released": True,
        }
    expected = [("connect_01-list_up", {}),
                ("connect_02-session", {"host_id": "verified-host", "model_path": str(model)}),
                ("connect_04-disconnect", {})]
    assert [requested.args for requested in client.call_tool.await_args_list] == expected[:tools]
