"""Dedicated PlanSection transport, schema and completion contracts; no live Rhino."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import Client, FastMCP
from jsonschema import validate
from almond_mcp.output_contracts import public_output_schema

from almond_mcp.features.modeling import plan_section
from almond_mcp.features.modeling.tools import register

ID = str(UUID(int=1))
OTHER = str(UUID(int=2))
MODEL = r"C:\offline\model.3dm"


def request(**changes):
    values = dict(operation="Create", clipping_ids=[ID], points=None, hatch=True,
                  small_details=False, near_width=.09, far_width=.04,
                  near_dark=80, far_dark=45, model_path=MODEL)
    values.update(changes)
    return plan_section.request(**values)


def completed_item(id=ID):
    return dict(clipping_id=id, status="completed", object_ids=[OTHER],
                draw_plane=dict(origin=[12,34,-9], xaxis=[1,0,0], yaxis=[0,1,0]),
                extraction=dict(layers=["model::walls"], source_object_count=3,
                                include_hidden=True, include_locked=True, include_attachments=False))


def response(status="completed", item_status="completed"):
    item = completed_item() if item_status == "completed" else dict(clipping_id=ID, status=item_status)
    results = [item]
    if status == "partial":
        results.append(completed_item(OTHER))
    return dict(status="success", mutation_state="completed", result=dict(status=status, requested=len(results),
                completed=sum(i["status"] == "completed" for i in results), results=results))


def transport(reply=None, capability=2):
    calls = []
    def send(data, **kwargs):
        payload = json.loads(data)
        calls.append((payload, kwargs))
        if payload["type"] == "get_rhino_context":
            return json.dumps(dict(status="success", capabilities=dict(plan_section=capability)))
        if isinstance(reply, Exception): raise reply
        return json.dumps(response() if reply is None else reply)
    return send, calls


def test_guid_normalization_and_existing_batch_semantics():
    result = request(clipping_ids=[ID.upper(), ID], points={ID: [1, 2, 3]})
    assert result["clipping_ids"] == [ID] and result["points"] == {ID: [1, 2, 3]}
    assert len(request(clipping_ids=[str(UUID(int=i)) for i in range(1, 34)])["clipping_ids"]) == 33


@pytest.mark.parametrize("changes", [
    dict(operation="PDF"), dict(operation="Move"), dict(clipping_ids=[]), dict(clipping_ids=[str(UUID(int=0))]),
    dict(clipping_ids=[1]), dict(clipping_ids=["invalid"]), dict(points={OTHER: [0, 0]}),
    dict(operation="Update", points={}), dict(points={ID: [True, 0]}), dict(points={ID: [0, float('nan')]}),
    dict(hatch=1), dict(small_details=None), dict(near_width=True),
    dict(near_width=.01), dict(far_width=0), dict(near_dark=101), dict(far_dark=81), dict(near_width=float('inf')),
])
def test_invalid_requests_fail_before_transport(changes):
    with pytest.raises((ValueError, TypeError, AttributeError)):
        request(**changes)


def test_dedicated_native_dispatch_never_routes_caller_script_or_rhinocode():
    send, calls = transport()
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "success" and result["drawing_status"] == "completed"
    validate(result, public_output_schema('plan_section', wrapped=False))
    assert [c[0]["type"] for c in calls] == ["get_rhino_context", "plan_section"]
    assert calls[-1][1] == {"timeout": 600.0}
    assert not {"script", "language", "folder", "path", "output"}.intersection(calls[-1][0])


@pytest.mark.parametrize("capability", [None, 0, True, "2", 1])
def test_old_or_invalid_capability_never_dispatches_mutation(capability):
    send, calls = transport(capability=capability)
    result = plan_section.dispatch(request(), send)
    assert result["mutation_state"] == "not_started" and len(calls) == 1


@pytest.mark.parametrize("status,item_status", [("partial", "skipped"), ("partial", "failed"), ("cancelled", "cancelled")])
def test_partial_and_cancelled_results_keep_per_clipping_evidence(status, item_status):
    reply = response(status, item_status)
    send, calls = transport(reply)
    ids = [ID, OTHER] if status == "partial" else [ID]
    result = plan_section.dispatch(request(clipping_ids=ids), send)
    assert result["status"] == status and result["result"] == reply["result"] and len(calls) == 2


@pytest.mark.parametrize("reply", [TimeoutError("still computing"), [],
    dict(status="success", result_error="detachment failed"),
    dict(status="success", result=dict(status="completed", requested=1, completed=1,
                result_delivery="paged", result_id="a"*32, result_characters=70000, result_sha256="a"*64)),
    dict(status="success", result=dict(status="completed", requested=1, completed=1,
                results=[dict(clipping_id=ID, status="completed", object_ids=[OTHER])])),
    dict(status="success", result=dict(status="completed", completed=0, requested=1, results=[])),
    dict(status="success", result=dict(status="completed", completed=1, requested=True, results=[dict(clipping_id=ID,status="completed")])),
])
def test_timeout_and_unconfirmed_output_are_uncertain_without_retry(reply):
    send, calls = transport(reply)
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "error" and result["mutation_state"] == "unknown"
    assert result["requires_reconciliation"] is True and len(calls) == 2


def test_entire_batch_failure_keeps_clipping_evidence():
    reply = response("failed", "failed")
    send, calls = transport(reply)
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "error" and result["drawing_status"] == "failed"
    assert result["result"] == reply["result"] and len(calls) == 2


def test_native_error_keeps_undo_diagnostics():
    reply = dict(status="error", mutation_state="unknown", message="Undo recovery failed", error_trace="evidence")
    send, calls = transport(reply)
    assert plan_section.dispatch(request(), send) == {**reply, "requires_reconciliation": True} and len(calls) == 2


@pytest.mark.parametrize("reply", [
    dict(status="error", message="native dispatch failed", source="almond-bound-bridge"),
    dict(message="missing envelope status"),
    dict(status="error", mutation_state="invented", requires_reconciliation=False),
])
def test_unclassified_post_dispatch_error_is_uncertain_and_retains_diagnostics(reply):
    send, calls = transport(reply)
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "error" and result["mutation_state"] == "unknown"
    assert result["requires_reconciliation"] is True and len(calls) == 2
    for key in ("message", "source"):
        if key in reply: assert result[key] == reply[key]


def test_confirmed_native_not_started_is_preserved():
    reply = dict(status="error", mutation_state="not_started", requires_reconciliation=False, message="runtime unavailable")
    send, calls = transport(reply)
    assert plan_section.dispatch(request(), send) == reply and len(calls) == 2


def test_native_runtime_error_marks_actual_mcp_result_error(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    reply = dict(status="runtime_error", mutation_state="unknown", requires_reconciliation=True,
                 message="native drawing failed", error_trace="production trace")
    async def check():
        send, calls = transport(reply)
        mcp = FastMCP("plan-section-runtime-error")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=[ID]), raise_on_error=False)
            assert result.is_error
            payload = json.loads(result.content[0].text)
            assert payload["status"] == "error" and payload["native_status"] == "runtime_error"
            assert payload["message"] == reply["message"] and payload["error_trace"] == reply["error_trace"]
            assert payload["mutation_state"] == "unknown" and payload["requires_reconciliation"] is True
            assert len(calls) == 2
    asyncio.run(check())


def test_public_create_reports_explicit_reference_scope(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    reply = response()
    reply["result"]["results"][0]["extraction"]["include_attachments"] = True

    async def check():
        send, calls = transport(reply)
        mcp = FastMCP("plan-section-worksession")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section",
                dict(operation="Create", clipping_ids=[ID], include_attachments=True))
            assert not result.is_error
            assert calls[-1][0]["include_attachments"] is True
            result = await client.call_tool("drawing_06-generate_plan_section",
                dict(operation="Create", clipping_ids=[ID], include_attachments=False), raise_on_error=False)
            assert result.is_error  # The returned scope did not match the explicit request.
            assert calls[-1][0]["include_attachments"] is False

    asyncio.run(check())


async def schema_contract():
    send, calls = transport()
    mcp = FastMCP("plan-section-contract")
    register(mcp, SimpleNamespace(_send_and_receive=send))
    async with Client(mcp) as client:
        tool = next(t for t in await client.list_tools() if t.name == "drawing_06-generate_plan_section")
        assert set(tool.input_schema["required"]) == {"operation", "clipping_ids"}
        properties = tool.input_schema["properties"]
        assert properties["operation"]["enum"] == ["Create", "Update", "Move"]
        assert properties["small_details"]["default"] is False
        assert "elevation" not in properties and "expected_model_path" not in properties
        assert all(t.name != "drawing_03-get_plan_section_result" for t in await client.list_tools())
        for args in (dict(operation="PDF", clipping_ids=[ID]), dict(operation="Create", clipping_ids=[ID], hatch=1),
                     dict(operation="Create", clipping_ids=[ID], script="pass"),
                     dict(operation="Create", clipping_ids=[ID], include_attachments=1),
                     dict(operation="Create", clipping_ids=[ID], elevation=False),
                     dict(operation="Create", clipping_ids=[ID], expected_model_path=MODEL)):
            result = await client.call_tool("drawing_06-generate_plan_section", args, raise_on_error=False)
            assert result.is_error
        assert calls == []


def test_public_schema_rejects_untyped_and_arbitrary_code_inputs():
    asyncio.run(schema_contract())


def test_move_requires_explicit_xyz_and_dispatches_using_bound_environment(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)

    async def check():
        send, calls = transport()
        mcp = FastMCP("plan-section-move")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            missing = await client.call_tool("drawing_06-generate_plan_section",
                dict(operation="Move", clipping_ids=[ID]), raise_on_error=False)
            assert missing.is_error and not calls
            result = await client.call_tool("drawing_06-generate_plan_section",
                dict(operation="Move", clipping_ids=[ID], points={ID:[12,34,-9]}))
            assert not result.is_error and len(calls) == 2
            payload = calls[-1][0]
            assert payload["operation"] == "Move" and payload["points"] == {ID:[12,34,-9]}
            assert payload["expected_model_path"] == MODEL
            assert payload["small_details"] is False and "elevation" not in payload

    asyncio.run(check())


@pytest.mark.parametrize("operation", ["Create", "Update"])
@pytest.mark.parametrize("status", ["completed", "partial", "failed"])
def test_native_result_serializes_unicode_without_ironpython_ascii_encoder(operation, status):
    # The production IronPython traceback reaches py_encode_basestring_ascii on a
    # nested CLR string. CPython's ASCII encoder accepts it, so model that one
    # runtime divergence while executing the production invocation unchanged.
    native = Path(__file__).resolve().parents[1] / "features/modeling/native/PlanSectionTool.cs"
    invocation = native.read_text(encoding="utf-8").split('const string Invoke = @"', 1)[1].split('";', 1)[0]
    layer = "M::\uae30\uc900\uce35::caf\u00e9"
    name = "\ud3c9\uba74"
    items = []
    if status != "failed":
        items.append(dict(name=name, status="completed", extraction=dict(layers=[layer])))
    if status != "completed":
        items.append(dict(name=name, status="failed", error=layer,
                          recovery=dict(requires_reconciliation=status == "partial")))
    result = dict(status=status, results=items, requested=len(items), completed=int(status != "failed"))

    def ironpython_dumps(value, *, ensure_ascii=True):
        if ensure_ascii:
            layer.encode("ascii")
        return json.dumps(value, ensure_ascii=ensure_ascii)

    def run(doc, actual_operation, clipping_ids, **kwargs):
        assert actual_operation == operation and clipping_ids == [ID]
        assert kwargs["output"] == "Document"
        return result

    args = dict(operation=operation, clipping_ids=[ID], points={}, hatch=True,
                small_details=False, near_width=.09, far_width=.04, near_dark=80, far_dark=45)
    scope = dict(json=SimpleNamespace(loads=json.loads, dumps=ironpython_dumps), run=run,
                 _almond_doc=object(), _almond_arguments_json=json.dumps(args),
                 _almond_observe_attachments=None)
    exec(invocation, scope)
    assert json.loads(scope["_almond_result_json"]) == result


@pytest.fixture(scope="module")
def native_boundary_results():
    dotnet = os.environ.get("ALMOND_TEST_DOTNET")
    assert dotnet, "Run through run_tests.ps1 with the .NET 8 SDK."
    project = Path(__file__).with_name("plan_section_host") / "PlanSectionHost.csproj"
    result = subprocess.run([dotnet, "run", "--project", str(project), "--configuration", "Release"],
                            capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(next(line.split("=", 1)[1] for line in result.stdout.splitlines()
                           if line.startswith("PLAN_SECTION_RESULTS=")))


def test_native_adapter_context_and_failure_boundaries(native_boundary_results):
    assert native_boundary_results["native_geometry_tested"] is False
    assert native_boundary_results["production_result_projector"] is True
    assert native_boundary_results["passed"] >= 50


@pytest.mark.parametrize("case,is_error,status", [
    ("completed", False, "success"), ("partial", False, "partial"), ("cancelled", False, "cancelled"),
    ("runtime_error", True, "error"), ("failed", True, "error"), ("oversized", False, "success"),
])
def test_production_native_responses_through_actual_mcp_boundary(native_boundary_results, case, is_error, status, monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    native = native_boundary_results["responses"][case]
    async def check():
        send, calls = transport(native)
        mcp = FastMCP("production-plan-section-result")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            ids = [ID, OTHER] if case == "partial" else [ID]
            result = await client.call_tool("drawing_06-generate_plan_section",
                dict(operation="Create", clipping_ids=ids), raise_on_error=False)
            assert result.is_error is is_error
            value = json.loads(result.content[0].text)
            assert value["status"] == status and len(calls) == 2
            if case == "runtime_error":
                assert value["mutation_state"] == "unknown" and value["requires_reconciliation"] is True
            else:
                assert value["result"] == native["result"]
            if case == "runtime_error":
                assert value["native_status"] == "runtime_error"
                assert value["error_trace"] == native["error_trace"]
            if case == "oversized":
                item = value["result"]["results"][0]
                assert len(item["object_ids"]) == 1681
                assert item["draw_plane"]["origin"] == [12, 34, -9]
                assert item["extraction"]["layers"] == ["model::walls"]
    asyncio.run(check())


def test_embedded_algorithm_is_a_runtime_source_and_stale_changes_are_detected(tmp_path):
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("plan_section_runtime_verifier", root / "src/rhp/tools/verify_runtime.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    source = "src/mcp/features/modeling/PlanSection/PlanSection.py"
    assert verifier.is_source(source, "bridge") and not verifier.is_source(source, "cos")
    assert not verifier.is_source("src/mcp/features/modeling/plan_section.py", "bridge")
    target = tmp_path / source
    target.parent.mkdir(parents=True)
    target.write_text("algorithm v1\n", encoding="utf-8")
    files = {}
    for relative in verifier.required_outputs("bridge"):
        output = tmp_path / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"isolated runtime fixture")
        files[relative] = verifier.digest(output)
    manifest = {"component": "bridge", "sources": {source: verifier.source_digest(target)}, "files": files}
    assert verifier.verify(tmp_path, manifest) == []
    target.write_text("algorithm v2\n", encoding="utf-8")
    assert verifier.verify(tmp_path, manifest) == [source]
