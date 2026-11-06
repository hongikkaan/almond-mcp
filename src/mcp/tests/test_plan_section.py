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

from almond_mcp.features.modeling import plan_section
from almond_mcp.features.modeling.tools import register

ID = str(UUID(int=1))
OTHER = str(UUID(int=2))
MODEL = r"C:\offline\model.3dm"


def request(**changes):
    values = dict(operation="Create", clipping_ids=[ID], points=None, hatch=True,
                  elevation=True, small_details=True, near_width=.09, far_width=.04,
                  near_dark=80, far_dark=45, model_path=MODEL)
    values.update(changes)
    return plan_section.request(**values)


def response(status="completed", item_status="completed"):
    return dict(status="success", mutation_state="completed", result=dict(status=status, requested=1,
                completed=int(item_status == "completed"), results=[dict(clipping_id=ID, status=item_status)]))


def transport(reply=None, capability=1):
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
    dict(hatch=1), dict(elevation="true"), dict(small_details=None), dict(near_width=True),
    dict(near_width=.01), dict(far_width=0), dict(near_dark=101), dict(far_dark=81), dict(near_width=float('inf')),
])
def test_invalid_requests_fail_before_transport(changes):
    with pytest.raises((ValueError, TypeError, AttributeError)):
        request(**changes)


def test_dedicated_native_dispatch_never_routes_caller_script_or_rhinocode():
    send, calls = transport()
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "success" and result["drawing_status"] == "completed"
    assert [c[0]["type"] for c in calls] == ["get_rhino_context", "plan_section"]
    assert calls[-1][1] == {"timeout": 600.0}
    assert not {"script", "language", "folder", "path", "output"}.intersection(calls[-1][0])


@pytest.mark.parametrize("capability", [None, 0, True, "1", 2])
def test_old_or_invalid_capability_never_dispatches_mutation(capability):
    send, calls = transport(capability=capability)
    result = plan_section.dispatch(request(), send)
    assert result["mutation_state"] == "not_started" and len(calls) == 1


@pytest.mark.parametrize("status,item_status", [("partial", "skipped"), ("partial", "failed"), ("cancelled", "cancelled")])
def test_partial_and_cancelled_results_keep_per_clipping_evidence(status, item_status):
    reply = response(status, item_status)
    send, calls = transport(reply)
    result = plan_section.dispatch(request(), send)
    assert result["status"] == status and result["result"] == reply["result"] and len(calls) == 2


@pytest.mark.parametrize("reply", [TimeoutError("still computing"), [],
    dict(status="success", result_error="detachment failed"),
    dict(status="success", result=dict(status="completed", completed=0, requested=1, results=[])),
    dict(status="success", result=dict(status="completed", completed=1, requested=True, results=[dict(clipping_id=ID,status="completed")])),
])
def test_timeout_and_unconfirmed_output_are_uncertain_without_retry(reply):
    send, calls = transport(reply)
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "error" and result["mutation_state"] == "unknown"
    assert result["requires_reconciliation"] is True and len(calls) == 2


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


async def schema_contract():
    send, calls = transport()
    mcp = FastMCP("plan-section-contract")
    register(mcp, SimpleNamespace(_send_and_receive=send))
    async with Client(mcp) as client:
        tool = next(t for t in await client.list_tools() if t.name == "plan_section")
        assert set(tool.input_schema["required"]) == {"operation", "clipping_ids"}
        assert tool.input_schema["properties"]["operation"]["enum"] == ["Create", "Update"]
        for args in (dict(operation="PDF", clipping_ids=[ID]), dict(operation="Create", clipping_ids=[ID], hatch=1),
                     dict(operation="Create", clipping_ids=[ID], script="pass")):
            result = await client.call_tool("plan_section", args, raise_on_error=False)
            assert result.is_error
        assert calls == []


def test_public_schema_rejects_untyped_and_arbitrary_code_inputs():
    asyncio.run(schema_contract())


def test_native_adapter_context_and_failure_boundaries(tmp_path):
    dotnet = os.environ.get("ALMOND_TEST_DOTNET")
    assert dotnet, "Run through run_tests.ps1 with the .NET 8 SDK."
    project = Path(__file__).with_name("plan_section_host") / "PlanSectionHost.csproj"
    result = subprocess.run([dotnet, "run", "--project", str(project), "--configuration", "Release"],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"native_geometry_tested": false' in result.stdout
    assert '"passed": 33' in result.stdout


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
    manifest = {"sources": {source: verifier.source_digest(target)}, "files": {}}
    assert verifier.verify(tmp_path, manifest) == []
    target.write_text("algorithm v2\n", encoding="utf-8")
    assert verifier.verify(tmp_path, manifest) == [source]
