"""Dedicated PlanSection transport, schema and completion contracts; no live Rhino."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
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
                  small_details=False, include_references=False, near_width=.09, far_width=.04,
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
    dict(hatch=1), dict(include_references="true"), dict(small_details=None), dict(near_width=True),
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


def test_native_runtime_error_marks_actual_mcp_result_error():
    reply = dict(status="runtime_error", mutation_state="unknown", requires_reconciliation=True,
                 message="native drawing failed", error_trace="production trace")
    async def check():
        send, calls = transport(reply)
        mcp = FastMCP("plan-section-runtime-error")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=[ID],
                request_id=""), raise_on_error=False)
            assert result.is_error
            payload = json.loads(result.content[0].text)
            assert payload["status"] == "error" and payload["native_status"] == "runtime_error"
            assert payload["message"] == reply["message"] and payload["error_trace"] == reply["error_trace"]
            assert payload["mutation_state"] == "unknown" and payload["requires_reconciliation"] is True
            assert len(calls) == 2
    asyncio.run(check())


async def schema_contract():
    send, calls = transport()
    mcp = FastMCP("plan-section-contract")
    register(mcp, SimpleNamespace(_send_and_receive=send))
    async with Client(mcp) as client:
        tool = next(t for t in await client.list_tools() if t.name == "drawing_06-generate_plan_section")
        assert set(tool.input_schema["required"]) == {"operation", "clipping_ids"}
        assert tool.input_schema["properties"]["operation"]["enum"] == ["Create", "Update", "Move"]
        for args in (dict(operation="PDF", clipping_ids=[ID]), dict(operation="Create", clipping_ids=[ID], hatch=1),
                     dict(operation="Create", clipping_ids=[ID], script="pass")):
            result = await client.call_tool("drawing_06-generate_plan_section", args, raise_on_error=False)
            assert result.is_error
        assert calls == []


def test_public_schema_rejects_untyped_and_arbitrary_code_inputs():
    asyncio.run(schema_contract())


def test_result_lookup_tool_removed_and_public_defaults(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    async def check():
        send, calls = transport()
        mcp = FastMCP("plan-section-contract")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            tools = await client.list_tools()
            assert not any("get_plan_section_result" in tool.name for tool in tools)
            tool = next(t for t in tools if t.name == "drawing_06-generate_plan_section")
            properties = tool.input_schema["properties"]
            assert "elevation" not in properties and "expected_model_path" not in properties
            assert properties["small_details"]["default"] is False
            assert properties["include_references"]["default"] is False
            result = await client.call_tool(tool.name, dict(operation="Create", clipping_ids=[ID]))
            assert not result.is_error
            assert calls[-1][0]["expected_model_path"] == MODEL
            assert calls[-1][0]["small_details"] is False
            assert "elevation" not in calls[-1][0]
    asyncio.run(check())


@pytest.fixture(autouse=True)
def bound_model(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)


@pytest.fixture(scope="module")
def native_boundary_results(tmp_path_factory):
    dotnet = os.environ.get("ALMOND_TEST_DOTNET")
    assert dotnet, "Run through run_tests.ps1 with the .NET 8 SDK."
    project = Path(__file__).with_name("plan_section_host") / "PlanSectionHost.csproj"
    fixture = tmp_path_factory.mktemp("algorithm-outcomes") / "rollback.json"
    emitter = Path(__file__).parents[1] / "features/modeling/PlanSection/tests/emit_rollback_fixture.py"
    emitted = subprocess.run([sys.executable, "-B", "-X", "utf8", str(emitter), str(fixture)], capture_output=True, text=True, timeout=30)
    assert emitted.returncode == 0, emitted.stdout + emitted.stderr
    result = subprocess.run([dotnet, "run", "--project", str(project), "--configuration", "Release", "--", "--algorithm-fixtures", str(fixture)],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(next(line.split("=", 1)[1] for line in result.stdout.splitlines()
                           if line.startswith("PLAN_SECTION_RESULTS=")))


def test_native_adapter_context_and_failure_boundaries(native_boundary_results):
    assert native_boundary_results["native_geometry_tested"] is False
    assert native_boundary_results["production_result_projector"] is True
    assert native_boundary_results["passed"] >= 60


@pytest.mark.parametrize("case,is_error,status", [
    ("completed", False, "success"), ("partial", False, "partial"), ("cancelled", False, "cancelled"),
    ("runtime_error", True, "error"), ("oversized", False, "success"), ("mandatory_overflow", True, "error"), ("historical", True, "error"),
])
def test_production_native_responses_through_actual_mcp_boundary(native_boundary_results, case, is_error, status):
    native = native_boundary_results["responses"][case]
    async def check():
        send, calls = transport(native)
        mcp = FastMCP("production-plan-section-result")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=[ID],
                request_id=""), raise_on_error=False)
            assert result.is_error is is_error
            value = json.loads(result.content[0].text)
            assert value["status"] == status and len(calls) == 2
            if is_error:
                assert value["mutation_state"] == "unknown" and value["requires_reconciliation"] is True
            else:
                assert value["result"] == native["result"]
            if case == "historical":
                assert value["error_code"] == "plan_section_historical_response"
                assert value["historical_drawing_status"] == "completed" and "drawing_status" not in value
            if case == "runtime_error":
                assert value["native_status"] == "runtime_error"
                assert value["error_trace"] == native["error_trace"]
            if case == "oversized":
                assert "result_delivery" not in value["result"]
                assert value["result"]["results"][0]["output_object_count"] == 1681
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
    manifest = {"sources": {source: verifier.source_digest(target)}, "files": {}}
    assert verifier.verify(tmp_path, manifest) == []
    target.write_text("algorithm v2\n", encoding="utf-8")
    assert verifier.verify(tmp_path, manifest) == [source]


def test_move_requires_all_points_and_keeps_key():
    key = str(UUID(int=9))
    value = request(operation="Move", points={ID: [1, 2, 3]}, request_id=key, include_references=True)
    assert value["operation"] == "Move" and value["points"][ID] == [1, 2, 3]
    assert value["request_id"] == key and value["include_references"] is True


def test_successful_generation_with_missing_response_details_is_distinct_from_partial():
    send, _ = transport(dict(status="success", result=dict(status="completed", requested=1, completed=1,
                         result_delivery="unavailable", result_error="response budget")))
    result = plan_section.dispatch(request(), send)
    assert result["status"] == "error" and result["mutation_state"] == "completed"
    assert result["drawing_status"] == "completed" and result["error_code"] == "plan_section_response_incomplete"


def test_response_loss_keeps_client_supplied_key_without_automatic_mutation_retry():
    key = str(UUID(int=7))
    send, calls = transport(TimeoutError("response lost"))
    result = plan_section.dispatch(request(request_id=key), send)
    assert result["request_id"] == key and result["mutation_state"] == "unknown" and len(calls) == 2
    assert "같은 request_id" in result["next_step_guide"]


def test_historical_native_completion_is_not_current_document_completion(native_boundary_results):
    native = native_boundary_results["responses"]["historical"]
    send, calls = transport(native)
    result = plan_section.dispatch(request(request_id=native["request_id"]), send)
    assert result["status"] == "error" and result["error_code"] == "plan_section_historical_response"
    assert result["mutation_state"] == "unknown" and result["requires_reconciliation"] is True
    assert result["historical_drawing_status"] == "completed" and result["recorded_mutation_state"] == "completed"
    assert "drawing_status" not in result and result["current_output_confirmed"] is False
    assert len(calls) == 2


def test_total_response_loss_then_same_key_recovers_production_native_replay(native_boundary_results):
    replay = native_boundary_results["responses"]["replayed"]
    payload = request(request_id=replay["request_id"])
    attempts = []
    def send(data, **kwargs):
        value = json.loads(data)
        if value["type"] == "get_rhino_context":
            return json.dumps(dict(status="success", capabilities=dict(plan_section=1)))
        attempts.append(value)
        if len(attempts) == 1: raise TimeoutError("the entire response was lost")
        return json.dumps(replay)
    lost = plan_section.dispatch(payload, send)
    recovered = plan_section.dispatch(payload, send)
    assert lost["mutation_state"] == "unknown" and recovered["status"] == "success"
    assert recovered["response_replayed"] is True and recovered["current_output_confirmed"] is False
    assert attempts[0] == attempts[1] and len(attempts) == 2
    # The linked production C# fixture asserts one ScriptExecutor invocation for this replay.


def test_incomplete_drawing_requires_intentional_new_key_update_instead_of_response_recovery():
    first = request(request_id=str(UUID(int=40)))
    send, calls = transport(response("partial", "failed"))
    partial = plan_section.dispatch(first, send)
    assert partial["status"] == "partial" and "새 request_id" in partial["next_step_guide"]
    update = request(operation="Update", request_id=str(UUID(int=41)))
    next_send, next_calls = transport()
    assert plan_section.dispatch(update, next_send)["status"] == "success"
    assert calls[-1][0]["request_id"] != next_calls[-1][0]["request_id"]
    assert next_calls[-1][0]["operation"] == "Update" and next_calls[-1][0]["points"] == {}


@pytest.mark.parametrize("case", ["undelete", "cleanup", "registry-restore", "move"])
def test_actual_algorithm_rollback_failure_crosses_native_dispatch_and_mcp(native_boundary_results, case):
    native = native_boundary_results["responses"]["algorithm_" + case]
    async def check():
        send, calls = transport(native)
        mcp = FastMCP("rollback-reconciliation")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=[ID]), raise_on_error=False)
            value = json.loads(result.content[0].text)
            assert result.is_error and value["mutation_state"] == "unknown" and value["requires_reconciliation"]
            assert value["result"]["results"][0]["rollback_errors"]
            assert "기존 유효 도면은 보존됩니다" not in value["next_step_guide"]
            assert "새 request_id로 생성·갱신하지 않습니다" in value["next_step_guide"]
            assert len(calls) == 2
    asyncio.run(check())


@pytest.mark.parametrize("case,code", [("budget", "plan_section_response_budget"), ("preflight", "plan_section_preflight_failed")])
def test_actual_readonly_preflight_rejection_remains_not_started_through_mcp(native_boundary_results, case, code):
    native = native_boundary_results["responses"]["algorithm_" + case]
    async def check():
        send, calls = transport(native)
        mcp = FastMCP("preflight-rejection")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=[ID]), raise_on_error=False)
            value = json.loads(result.content[0].text)
            assert result.is_error and value["mutation_state"] == "not_started" and value["error_code"] == code
            assert value["requires_reconciliation"] is False and len(calls) == 2
            assert value["status"] == "error" and "drawing_status" not in value
            assert value["result"]["status"] == "error" and not value.get("result_error")
    asyncio.run(check())


@pytest.mark.parametrize("status", ["completed", "partial", "cancelled"])
def test_response_detail_loss_guidance_distinguishes_completion_from_incomplete(status):
    send, _ = transport(dict(status="success", result=dict(status=status, requested=1, completed=int(status == "completed"), result_delivery="unavailable")))
    value = plan_section.dispatch(request(), send)
    if status == "completed":
        assert "생성 완료 상태는 확인" in value["next_step_guide"] and "새 request_id" not in value["next_step_guide"]
    else:
        assert "불완전하거나 취소" in value["next_step_guide"] and "새 request_id" in value["next_step_guide"]
    assert value["mutation_state"] == ("completed" if status == "completed" else "partial")


def test_unknown_overrides_response_unavailable_guidance():
    send, _ = transport(dict(status="success", mutation_state="unknown", result=dict(status="partial", requested=1, completed=0, result_delivery="unavailable")))
    value = plan_section.dispatch(request(), send)
    assert value["mutation_state"] == "unknown" and "생성·갱신하지 않습니다" in value["next_step_guide"]


def test_conflict_details_and_optional_budget_markers_survive_native_boundary(native_boundary_results):
    small = native_boundary_results["responses"]["completed"]["result"]["results"][0]["report"]
    assert small["metadata_conflicts"][0] == dict(field="user_text.Phase", sources=["block/source"], reason="different_values")
    large = native_boundary_results["responses"]["optional_overflow"]
    report = large["result"]["results"][0]["report"]
    assert report["metadata_conflicts_truncated"] and report["metadata_conflicts_omitted_count"] == 64
    assert report["metadata_conflict_count"] == 64 and large["result"]["results"][0]["generation_conditions"]
    assert len(json.dumps(large, ensure_ascii=True).encode("utf-8")) < 65536


def test_many_korean_clippings_keep_required_conditions_through_mcp(native_boundary_results):
    native = native_boundary_results["responses"]["combined"]
    ids = [row["clipping_id"] for row in native["result"]["results"]]
    async def check():
        send, _ = transport(native)
        mcp = FastMCP("combined-korean-drawing-result")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=ids))
            value = json.loads(result.content[0].text)
            assert not result.is_error and len(value["result"]["results"]) == 8
            assert len(json.dumps(value, ensure_ascii=True).encode("utf-8")) < 65536
            for row in value["result"]["results"]:
                assert row["generation_conditions"]["clipping_plane"] and row["generation_conditions"]["source_layer_names"]
                assert row["report"]["metadata_conflict_count"] == 64 and row["report"]["metadata_conflicts_truncated"]
    asyncio.run(check())


@pytest.mark.parametrize("case,expected_error,mutation", [
    ("completed_missing_clip", False, "completed"),
    ("historical_missing_clip", True, "unknown"),
    ("pending_missing_clip", True, "unknown"),
    ("new_missing_clip", True, "not_started"),
    ("recovery_wrong_binding", True, "not_started"),
])
def test_journal_recovery_does_not_depend_on_current_clipping(native_boundary_results, case, expected_error, mutation):
    native = native_boundary_results["responses"][case]
    async def check():
        send, calls = transport(native)
        mcp = FastMCP("missing-clipping-recovery")
        register(mcp, SimpleNamespace(_send_and_receive=send))
        async with Client(mcp) as client:
            result = await client.call_tool("drawing_06-generate_plan_section", dict(operation="Create", clipping_ids=[ID], request_id=native.get("request_id", "")), raise_on_error=False)
            value = json.loads(result.content[0].text)
            assert result.is_error is expected_error and value["mutation_state"] == mutation
            if case == "completed_missing_clip":
                assert value["response_replayed"] is True and value["current_output_confirmed"] is False
            elif case in ("historical_missing_clip", "pending_missing_clip"):
                assert value["requires_reconciliation"] is True
            else:
                assert value["requires_reconciliation"] is False and not value.get("response_replayed")
            assert len(calls) == 2
    asyncio.run(check())
