"""BDD: an agent saves the bound model once without entering a Rhino command."""
import json
import socket
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP

from almond_mcp.features.modeling.tools import register


@pytest.fixture
def save_tool(monkeypatch, tmp_path):
    model = tmp_path / 'model.3dm'
    monkeypatch.setenv('ALMOND_MODEL_PATH', str(model))
    context = SimpleNamespace()
    exports = register(FastMCP('save behavior'), context)
    return context, exports['save_rhino_document'], str(model)


def test_given_capable_bridge_when_saving_then_write_bound_document_once(save_tool):
    context, save, model = save_tool
    requests = []
    def send(payload):
        request = json.loads(payload)
        requests.append(request)
        if request['type'] == 'get_rhino_context':
            return json.dumps({'status': 'success', 'capabilities': {'document_save': 1}})
        return json.dumps({'status': 'success', 'saved': True, 'modified': False})
    context._send_and_receive = send
    assert json.loads(save()) == {'status': 'success', 'saved': True, 'modified': False}
    assert requests == [
        {'type': 'get_rhino_context', 'sections': [], 'selection_limit': 0},
        {'type': 'save_rhino_document', 'expected_model_path': model},
    ]


def test_given_old_bridge_when_saving_then_reject_without_unknown_mutation(save_tool):
    context, save, _ = save_tool
    requests = []
    context._send_and_receive = lambda payload: requests.append(json.loads(payload)) or '{"status":"success","capabilities":{}}'
    result = json.loads(save())
    assert result['status'] == 'error'
    assert result['error_code'] == 'unsupported_document_save'
    assert result['saved'] is False
    assert len(requests) == 1


def test_given_no_binding_when_saving_then_reject_before_native_call(save_tool, monkeypatch):
    context, save, _ = save_tool
    monkeypatch.delenv('ALMOND_MODEL_PATH')
    context._send_and_receive = lambda *_: pytest.fail('Unbound save must not reach Rhino')
    result = json.loads(save())
    assert result['status'] == 'error'
    assert result['saved'] is False


def test_given_active_editor_when_saving_then_preserve_native_rejection(save_tool):
    context, save, _ = save_tool
    refusal = {'status': 'error', 'error_code': 'editing_context_unstable', 'saved': False,
               'editing': {'mode': 'group', 'stable': False, 'target': {'name': 'working group'}}}
    context._send_and_receive = lambda payload: json.dumps(
        {'status': 'success', 'capabilities': {'document_save': 1}}
        if json.loads(payload)['type'] == 'get_rhino_context' else refusal)
    assert json.loads(save()) == refusal


@pytest.mark.parametrize('failure', [socket.timeout('late write'), RuntimeError('lost response')])
def test_given_lost_completion_when_saving_then_report_unknown_and_never_retry(save_tool, failure):
    context, save, _ = save_tool
    requests = []
    def send(payload):
        requests.append(json.loads(payload))
        if len(requests) == 1:
            return '{"status":"success","capabilities":{"document_save":1}}'
        raise failure
    context._send_and_receive = send
    result = json.loads(save())
    assert result['status'] == 'error'
    assert result['saved'] is None
    assert result['requires_reconciliation'] is True
    assert len(requests) == 2


@pytest.mark.parametrize('response', ['{}', '{"status":"success"}', '{"status":"success","saved":true,"modified":"no"}'])
def test_given_incomplete_result_when_saving_then_never_claim_confirmed_save(save_tool, response):
    context, save, _ = save_tool
    context._send_and_receive = lambda payload: ('{"status":"success","capabilities":{"document_save":1}}'
        if json.loads(payload)['type'] == 'get_rhino_context' else response)
    result = json.loads(save())
    assert result['status'] == 'error'
    assert result['saved'] is None
    assert result['requires_reconciliation'] is True
