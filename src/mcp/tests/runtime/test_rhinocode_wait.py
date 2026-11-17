"""First response budgets never change the exact RhinoCode completion fence."""
import json
import asyncio
from types import SimpleNamespace

import pytest

import rhinocode


@pytest.fixture
def execution(tmp_path, monkeypatch):
    operation_id = "1" * 32
    operation = tmp_path / operation_id
    operation.mkdir()
    session = tmp_path / "session"
    session.mkdir()
    binding = dict(pid=1, process_start_ticks="2", document_serial=3,
                   model_path=str(tmp_path / "fixture.3dm"), token="a" * 32)
    locations = dict(session_dir=str(session), project_dir=str(tmp_path), call_root=str(tmp_path))
    clock = [0.0]
    handles, launches = [], []
    monkeypatch.setattr(rhinocode, "time", SimpleNamespace(
        monotonic=lambda: clock[0], sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds)))
    monkeypatch.setattr(rhinocode, "find_binary", lambda _: tmp_path / "fixture-cli")
    monkeypatch.setattr(rhinocode, "discover_instances", lambda _: [])
    monkeypatch.setattr(rhinocode, "select_instance", lambda *_: {"pipeId": "fixture"})
    monkeypatch.setattr(rhinocode, "_process_alive", lambda _: False)

    def launch(handle, *_):
        launches.append(handle.request_id)
        handle.journal["child"] = {"pid": 5, "process_start_ticks": "6"}
        (handle.directory / "child.json").write_text(json.dumps({
            "schema": "almond-owned-process", "owner": {key: handle.journal[key] for key in rhinocode._IDENTITY},
            "child": handle.journal["child"]}), encoding="utf-8")
        handle.publish()
        handle.dispatching = False

    monkeypatch.setattr(rhinocode._Execution, "launch", launch)
    runner = rhinocode.RhinocodeExecution(binding, locations)
    return SimpleNamespace(runner=runner, clock=clock, handles=handles, launches=launches,
                           options=dict(operation_id=operation_id, operation_dir=operation,
                                        register=handles.append))


@pytest.mark.parametrize("requested,cap,expected", [(600, 60, 60), (60, 60, 60), (5, 60, 5), (1, 60, 1), (600, None, 600)])
def test_first_wait_cap_preserves_short_requests_and_dedicated_runtime(execution, requested, cap, expected):
    result = execution.runner.execute("pass", "python", requested,
                                      wait_cap_seconds=cap, **execution.options)
    assert execution.clock[0] == expected
    assert result["pending"] and result["timed_out"] and not result["completed"]
    assert execution.launches == [result["request_id"]]
    handle = execution.handles[0]
    journal = json.loads((handle.directory / "request.json").read_text(encoding="utf-8"))
    assert journal["request_id"] == result["request_id"]


def test_capped_pending_uses_same_id_for_late_exact_completion(execution):
    result = execution.runner.execute("pass", "python", 600,
                                      wait_cap_seconds=60, **execution.options)
    handle = execution.handles[0]
    receipt = {key: handle.journal[key] for key in rhinocode._IDENTITY}
    receipt.update(schema="almond-rhinocode-completion", version=1, layout="compact-v1",
                   status="success", mutation_state="completed", execution_complete=True)
    (handle.directory / "complete.json").write_text(json.dumps(receipt), encoding="utf-8")
    finishing = rhinocode.inspect_execution(handle.journal,
        receipt_path=handle.directory / "complete.json", process_inspector=lambda _: True)
    assert finishing["completion_state"] == "finishing" and not finishing["completed"]
    late = execution.runner.get_execution(result["request_id"])
    assert late["request_id"] == result["request_id"] and late["completed"]
    assert late["status"] == "success" and execution.launches == [result["request_id"]]


def test_external_wait_policy_is_explicit_runtime_configuration():
    from shared_store import ProjectRuntime
    runtime = object.__new__(ProjectRuntime)
    runtime.operation_active = False
    runtime.configure_rhinocode_wait(60)
    assert runtime.rhinocode_wait_cap == 60
    runtime.operation_active = True
    with pytest.raises(RuntimeError, match="active"):
        runtime.configure_rhinocode_wait(1)


def test_runtime_correlates_current_and_finished_operation_without_changing_arguments(tmp_path):
    from fastmcp.server.middleware import MiddlewareContext
    from mcp import types
    from project import write_json, read_json
    from shared_store import ProjectRuntime

    session, temp = tmp_path / "session", tmp_path / "temp"
    session.mkdir()
    temp.mkdir()
    write_json(session / "worker.json", dict(pid=1, process_start_ticks="2"))
    locations = dict(session_dir=str(session), temp=str(temp), call_root=str(temp / "calls"),
                     project_dir=str(tmp_path))
    runtime = ProjectRuntime(SimpleNamespace(token="a" * 32), {}, locations, check_owner=False)
    assert runtime.rhinocode_wait_cap is None
    correlation = "b" * 32
    arguments = {"code": "pass"}
    context = MiddlewareContext(message=types.CallToolRequestParams(
        name="fixture", arguments=arguments, _meta={"almond/caller_request_id": correlation}))
    seen = []

    async def next_call(current):
        state = runtime.completion()
        assert state["caller_request_id"] == correlation and state["operation_active"]
        record = read_json(session / "operation.json")
        assert record["operation_id"] == state["operation_id"] != correlation
        assert record["caller_request_id"] == correlation
        assert current.message.arguments == arguments
        seen.append(record["operation_id"])
        return {"status": "success"}

    asyncio.run(runtime._owned_call(context, next_call, "fixture", False, ""))
    finished = runtime.completion()
    assert finished["caller_request_id"] == correlation
    assert finished["operation_id"] == seen[0] and not finished["pending"]
    assert not runtime.operation_active


def test_fastmcp_transport_metadata_reaches_the_owned_runtime_operation(tmp_path):
    from fastmcp import Client, FastMCP
    from project import write_json
    from shared_store import ProjectRuntime

    session, temp, storage = tmp_path / "session", tmp_path / "temp", tmp_path / "storage"
    session.mkdir()
    temp.mkdir()
    (storage / ".sessions").mkdir(parents=True)
    write_json(session / "worker.json", dict(pid=1, process_start_ticks="2"))
    locations = dict(session_dir=str(session), temp=str(temp), call_root=str(temp / "calls"),
                     project_dir=str(tmp_path), storage=str(storage))
    runtime = ProjectRuntime(SimpleNamespace(token="a" * 32), {}, locations, check_owner=False)
    runtime.validate = lambda: None  # No live process or document in this transport fixture.
    server = FastMCP("runtime-correlation-fixture")
    server.add_middleware(runtime)

    @server.tool(name="fixture_probe")
    def probe() -> dict:
        return runtime.completion()

    async def run():
        async with Client(server) as client:
            response = await client.call_tool("fixture_probe", {}, meta={"almond/caller_request_id": "b" * 32})
            assert response.data.get("caller_request_id") == "b" * 32
            assert response.data["operation_id"] != "b" * 32
            assert runtime.completion()["caller_request_id"] == "b" * 32
            plain = await client.call_tool("fixture_probe", {})
            assert "caller_request_id" not in plain.data
            assert plain.data["operation_id"] != response.data["operation_id"]
        assert "caller_request_id" not in runtime.completion()

    asyncio.run(run())
