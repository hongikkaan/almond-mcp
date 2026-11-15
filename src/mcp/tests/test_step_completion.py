"""Automatic completion transport and offline native safety; never opens Rhino."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from almond_mcp.features.planning import completion


MODEL = r"C:\offline\model.3dm"


def successful_result(**changes):
    return dict(cleanup_complete=True, document_serial=7, deleted_object_count=2,
                deleted_layer_count=1, mutation_state='applied', **changes)


def transport(reply=None, *, capability=2):
    calls = []
    def send(data, **kwargs):
        request = json.loads(data)
        calls.append(request)
        if request['type'] == 'get_rhino_context':
            return json.dumps(dict(status='success', capabilities=dict(step_completion=capability)))
        if isinstance(reply, Exception):
            raise reply
        if reply is not None:
            return json.dumps(reply)
        return json.dumps(dict(status='success', result=successful_result()))
    return send, calls


def test_cleanup_sends_only_bound_document_request_once_and_reports_actual_counts():
    send, calls = transport()
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'success' and result['cleanup_complete'] is True
    assert (result['deleted_object_count'], result['deleted_layer_count']) == (2, 1)
    assert '완료에 따른 정상 정리 과정' in result['message']
    assert 'Rhino Undo는 Step의 저장 상태를 되돌리지 않습니다' in result['message']
    assert result['message'].endswith('삭제 객체: 2개, 레이어: 1개.')
    assert [request['type'] for request in calls] == ['get_rhino_context', 'step_completion']
    assert calls[-1] == dict(type='step_completion', expected_model_path=MODEL)


def test_no_temp_is_success_without_confirmation_or_retained_state():
    value = {**successful_result(), 'deleted_object_count': 0, 'deleted_layer_count': 0,
             'mutation_state': 'not_needed'}
    send, calls = transport(dict(status='success', result=value))
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'success' and result['mutation_state'] == 'not_needed'
    assert len(calls) == 2
    assert 'temp 계층이 없어' in result['message']
    assert '삭제했습니다' not in result['message']
    assert not {'token', 'inventory', 'receipt', 'fingerprint'}.intersection(result)
    assert not hasattr(completion, 'prepare')


@pytest.mark.parametrize('capability', [None, 0, 1, True, '2', 3])
def test_only_automatic_cleanup_capability_two_can_dispatch(capability):
    send, calls = transport(capability=capability)
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'error' and result['mutation_state'] == 'not_started'
    assert result['error_code'] == 'unsupported_step_completion'
    assert len(calls) == 1


@pytest.mark.parametrize('model', ['', ' ', None, [], True])
def test_missing_bound_document_cannot_dispatch(model):
    send, calls = transport()
    assert completion.cleanup(send, model)['mutation_state'] == 'not_started'
    assert calls == []


@pytest.mark.parametrize('reply', [TimeoutError('lost native completion'), [],
    dict(status='success', result_error='too large'), dict(status='runtime_error', message='undo failed'),
    dict(status='success', result=dict(cleanup_complete=True)),
    dict(status='success', result=successful_result(), requires_reconciliation=True),
    dict(status='success', result=successful_result(), mutation_state='unknown')])
def test_uncertain_mutation_is_never_retried_or_reported_complete(reply):
    send, calls = transport(reply)
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'error' and result['mutation_state'] == 'unknown'
    assert result['cleanup_complete'] is False and result['requires_reconciliation'] is True
    assert len(calls) == 2


@pytest.mark.parametrize('field,value', [
    ('document_serial', True), ('document_serial', 0), ('document_serial', -1), ('document_serial', '7'),
    ('deleted_object_count', True), ('deleted_object_count', -1), ('deleted_object_count', None),
    ('deleted_object_count', 1.0), ('deleted_layer_count', False), ('deleted_layer_count', -1),
    ('deleted_layer_count', '1'), ('cleanup_complete', 1), ('mutation_state', 'partial'),
    ('mutation_state', 'unknown'), ('requires_reconciliation', True),
])
def test_success_result_requires_strict_confirmed_serial_counts_and_state(field, value):
    data = {**successful_result(), field: value}
    send, calls = transport(dict(status='success', result=data))
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'error' and result['mutation_state'] == 'unknown'
    assert result['requires_reconciliation'] is True and len(calls) == 2


def test_native_rejection_preserves_no_mutation_evidence():
    send, calls = transport(dict(status='error', mutation_state='not_started', message='wrong document'))
    result = completion.cleanup(send, MODEL)
    assert result['mutation_state'] == 'not_started' and result['cleanup_complete'] is False
    assert len(calls) == 2


@pytest.mark.parametrize('state,objects,layers', [('not_needed', 1, 0), ('not_needed', 0, 1),
                                                ('applied', 0, 0)])
def test_mutation_state_must_match_actual_deleted_counts(state, objects, layers):
    value = {**successful_result(), 'mutation_state': state, 'deleted_object_count': objects,
             'deleted_layer_count': layers}
    send, calls = transport(dict(status='success', result=value))
    result = completion.cleanup(send, MODEL)
    assert result['mutation_state'] == 'unknown' and result['requires_reconciliation']
    assert result['cleanup_complete'] is False and len(calls) == 2


def test_empty_temp_layer_still_reports_applied_cleanup():
    value = {**successful_result(), 'deleted_object_count': 0}
    send, _ = transport(dict(status='success', result=value))
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'success' and result['mutation_state'] == 'applied'
    assert '잔여 객체를 삭제했습니다' in result['message']


def test_partial_attempt_counts_are_not_confirmed_deleted_counts():
    send, calls = transport(dict(status='error', mutation_state='unknown', message='delete failed',
        deleted_object_count=None, deleted_layer_count=None, attempted_object_count=3,
        attempted_layer_count=1, requires_reconciliation=True))
    result = completion.cleanup(send, MODEL)
    assert result['status'] == 'error' and result['mutation_state'] == 'unknown'
    assert result['deleted_object_count'] is None and result['deleted_layer_count'] is None
    assert result['attempted_object_count'] == 3 and result['cleanup_complete'] is False
    assert len(calls) == 2


def test_instruction_failure_happens_before_cleanup_dispatch(monkeypatch):
    def fail(*args):
        raise ValueError('missing completion instruction')
    monkeypatch.setattr(completion, 'read_instruction', fail)
    send, calls = transport()
    result = completion.cleanup(send, MODEL)
    assert result['mutation_state'] == 'not_started' and len(calls) == 1

def test_native_fixture_and_installed_sdk_compile():
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 -Development to select .NET 8 SDK."
    root = Path(__file__).with_name("step_completion_host")
    subprocess.run([sys.executable, "-B", str(root / "prepare_executor.py")], check=True,
                   capture_output=True, text=True, encoding="utf-8", timeout=30)
    for name in ("StepCompletionHost.csproj", "StepCompletionSdk.csproj"):
        result = subprocess.run([sdk, "build", str(root / name), "-c", "Release", "--nologo",
            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run([sdk, str(root / "bin/Release/net8.0/StepCompletionHost.dll")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "passed" and report["actualRhinoLoaded"] is False
    assert report["tests"] >= 16
