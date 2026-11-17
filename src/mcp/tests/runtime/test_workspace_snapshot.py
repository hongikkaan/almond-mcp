"""Workspace-dependent dispatch uses one locked selection per public call."""
import asyncio
import json
import os
from types import SimpleNamespace

from fastmcp.server.middleware import MiddlewareContext
from mcp import types
import pytest

from almond_mcp.retrieval_store import AlmondStore
from project import connection_paths, write_json
from shared_store import ProjectRuntime, StoreGate
from workspace import Workspace


@pytest.fixture
def runtime(tmp_path):
    model = tmp_path / "model.3dm"
    model.touch()
    locations = connection_paths(model, "A", "a" * 32, create=True)
    write_json(tmp_path / ".almond/.sessions" / ("a" * 32) / "worker.json", {"pid": 1, "process_start_ticks": "2"})
    runtime = ProjectRuntime(SimpleNamespace(token="a" * 32), {}, locations, check_owner=False)
    runtime.validate = lambda: None  # Transport fixture has no live Rhino binding.
    runtime.workspace = Workspace(locations, AlmondStore(locations["state_db"]))
    return runtime


def test_artifact_dispatch_holds_store_gate_and_keeps_one_selection(runtime):
    plan = runtime.workspace.store.create_plan(goal="Snapshot")
    chosen = runtime.workspace.select(plan["plan_id"])
    observed = []
    def transport(raw):
        envelope = json.loads(raw)
        observed.append(json.loads(envelope["payload"])["artifact_dir"])
        return json.dumps(dict(envelope, schema="almond-native-response", native_sequence=0,
                               completion_status="rejected", payload='{"status":"error"}'))
    async def call(context):
        with pytest.raises(TimeoutError):
            with StoreGate(runtime.locations["storage"], timeout=0):
                pass
        assert os.environ["ALMOND_ARTIFACT_DIR"] == chosen["artifact_dir"]
        # An explicit connection-local selection update cannot change the admitted call.
        write_json(runtime.workspace.state_path, {"plan_id": "no-such-plan"})
        runtime.send(transport, b'{"type":"execute"}')
        return {"status": "success"}
    context = MiddlewareContext(message=types.CallToolRequestParams(name="script_02-run_rhino", arguments={}))
    asyncio.run(runtime.on_call_tool(context, call))
    assert observed == [chosen["artifact_dir"]]


def test_fixed_native_observation_does_not_read_workspace_database(runtime, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("workspace database unavailable")
    monkeypatch.setattr(runtime.workspace.store, "_connect", unavailable)
    async def call(context):
        return {"status": "success"}
    context = MiddlewareContext(message=types.CallToolRequestParams(name="inspect_03-get_document_context", arguments={}))
    assert asyncio.run(runtime.on_call_tool(context, call)) == {"status": "success"}
