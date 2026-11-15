"""Only a new completed transition cleans temp, before the same DB commit."""
from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter, ValidationError

from almond_mcp.features.planning import completion_flow
from almond_mcp.features.planning.completion_flow import StepCompletionFlow
from almond_mcp.features.planning.requests import UpdateRequest
from almond_mcp.retrieval_store import AlmondStore


@pytest.fixture
def flow(tmp_path, monkeypatch):
    store = AlmondStore(tmp_path / 'scene.sqlite3')
    plan = store.create_plan('Test completion', scope='component')
    model = str(tmp_path / 'existing.3dm')
    monkeypatch.setenv('ALMOND_MODEL_PATH', model)
    calls = []
    def clean(sender, model_path):
        assert model_path == model
        calls.append('cleanup')
        return {'status': 'success', 'cleanup_complete': True, 'mutation_state': 'applied',
                'document_serial': 7, 'deleted_object_count': 2, 'deleted_layer_count': 1}
    monkeypatch.setattr(completion_flow.completion, 'cleanup', clean)
    controller = StepCompletionFlow(SimpleNamespace(retrieval_store=store, _send_and_receive=lambda _: None))
    base = {'target': 'step', 'plan_id': plan['plan_id'], 'step_id': plan['steps'][0]['step_id']}
    return controller, store, base, calls


def update(flow, **fields):
    controller, _, base, _ = flow
    return controller.update(TypeAdapter(UpdateRequest).validate_python({**base, **fields}))


def test_automatic_completion_records_fields_once_after_cleanup(flow, monkeypatch):
    controller, store, base, calls = flow
    before = store.get_plan(base['plan_id'])['revision']
    record_revision = store._record_generation_revision
    def record(*args, **kwargs):
        assert calls == ['cleanup']
        return record_revision(*args, **kwargs)
    monkeypatch.setattr(store, '_record_generation_revision', record)
    result = update(flow, status='completed', takeaways='Keep south access', design_rationale='Less glare',
                    output_refs={'add': ['analysis.md']})
    assert result['cleanup_complete'] and result['step']['status'] == 'completed'
    assert calls == ['cleanup'] and result['plan']['revision'] == before + 1
    step = store.get_step(base['plan_id'], base['step_id'])['step']
    assert (step['takeaways'], step['design_rationale'], step['output_refs']) == ('Keep south access', 'Less glare', ['analysis.md'])
    assert not hasattr(controller, 'pending')
    assert not {'token', 'inventory', 'receipt'}.intersection(result)


@pytest.mark.parametrize('status', [None, 'pending', 'running', 'paused', 'failed', 'blocked'])
def test_noncompleted_updates_do_not_clean(flow, status):
    _, store, base, calls = flow
    result = update(flow, status=status, takeaways='A normal edit')
    assert not calls and 'cleanup' not in result
    assert store.get_step(base['plan_id'], base['step_id'])['step']['takeaways'] == 'A normal edit'


def test_already_completed_same_status_and_note_edits_do_not_clean(flow):
    _, store, base, calls = flow
    store.update_plan_step(base['plan_id'], base['step_id'], 'completed')
    before = store.get_plan(base['plan_id'])['revision']
    unchanged = update(flow, status='completed')
    assert not unchanged['changed'] and unchanged['plan']['revision'] == before
    noted = update(flow, status='completed', takeaways='Add note after completion')
    assert noted['changed'] and not calls and 'cleanup' not in noted
    assert noted['plan']['revision'] == before + 1


def test_paused_then_completed_recleans_after_an_earlier_completion(flow):
    first = update(flow, status='completed')
    update(flow, status='paused')
    second = update(flow, status='completed')
    assert first['cleanup_complete'] and second['cleanup_complete']
    assert flow[3] == ['cleanup', 'cleanup']


@pytest.mark.parametrize('prior', ['pending', 'running', 'paused', 'failed', 'blocked'])
def test_every_new_completed_transition_runs_cleanup(flow, prior):
    _, store, base, calls = flow
    store.update_plan_step(base['plan_id'], base['step_id'], prior)
    assert update(flow, status='completed')['cleanup_complete']
    assert calls == ['cleanup']


@pytest.mark.parametrize('state', ['not_started', 'partial', 'unknown'])
def test_failed_or_uncertain_cleanup_keeps_prior_record_without_retry(flow, monkeypatch, state):
    _, store, base, calls = flow
    before = store.get_plan(base['plan_id'])
    def fail(*args, **kwargs):
        calls.append('cleanup')
        return {'status': 'error', 'cleanup_complete': False, 'mutation_state': state}
    monkeypatch.setattr(completion_flow.completion, 'cleanup', fail)
    result = update(flow, status='completed', takeaways='Not committed', output_refs={'add': ['not-saved.txt']})
    assert result['status'] == 'error' and result['mutation_state'] == state
    assert result['changed'] is False and store.get_plan(base['plan_id']) == before
    assert calls == ['cleanup']


def test_db_failure_preserves_actual_cleanup_evidence_and_keeps_step_pending(flow, monkeypatch):
    _, store, base, calls = flow
    before = store.get_plan(base['plan_id'])
    monkeypatch.setattr(store, '_record_generation_revision', lambda *args: (_ for _ in ()).throw(RuntimeError('disk full')))
    result = update(flow, status='completed')
    assert result['status'] == 'error' and result['cleanup_complete']
    assert result['requires_reconciliation'] and calls == ['cleanup']
    assert result['cleanup']['deleted_object_count'] == 2
    assert 'Read the Step and inspect Rhino' in result['message']
    assert store.get_plan(base['plan_id']) == before


def test_revision_and_field_validation_happens_before_native_cleanup(flow):
    _, store, base, calls = flow
    with pytest.raises(ValueError, match='revision conflict'):
        update(flow, status='completed', expected_revision=999)
    assert not calls
    with pytest.raises(KeyError, match='Unknown step_id'):
        controller_request = TypeAdapter(UpdateRequest).validate_python({**base, 'step_id': 'missing', 'status': 'completed'})
        flow[0].update(controller_request)
    assert not calls


def test_completion_does_not_fill_missing_loop_for_delayed_revision(flow):
    _, store, base, calls = flow
    first = store.execute_looping(base['plan_id'])
    current = store.execute_looping(base['plan_id'])
    assert first['revision'] == current['revision'] == 1 and current['loop_no'] == 2
    with pytest.raises(ValueError, match='Supply loop_no with expected_revision'):
        update(flow, status='completed', expected_revision=first['revision'], takeaways='Loop 1 note')
    assert store.get_plan(base['plan_id']) == current and not calls
    with pytest.raises(ValueError, match='Only current Loop'):
        update(flow, status='completed', expected_revision=1, loop_no=1)
    assert not calls


def test_omitted_guards_complete_current_loop_without_new_pinning_contract(flow):
    _, store, base, calls = flow
    store.execute_looping(base['plan_id'])
    store.execute_looping(base['plan_id'])
    result = update(flow, status='completed', takeaways='Current Loop note')
    assert result['step']['status'] == 'completed' and result['step']['loop_no'] == 2
    assert calls == ['cleanup']


@pytest.mark.parametrize('extra', [dict(temp_layer='temp'), dict(completion={'answer': 'yes', 'token': 'old'}),
                                  dict(completion=None), dict(token='old'), dict(receipt='old')])
def test_confirmation_and_partial_scope_inputs_have_no_compatibility_alias(extra):
    with pytest.raises(ValidationError):
        TypeAdapter(UpdateRequest).validate_python({'target': 'step', 'plan_id': 'p', 'step_id': 's',
                                                    'status': 'completed', **extra})


@pytest.mark.parametrize('value', [[], {}, 1, True])
def test_decision_text_input_is_strict(value):
    with pytest.raises(ValidationError):
        TypeAdapter(UpdateRequest).validate_python({'target': 'step', 'plan_id': 'p', 'step_id': 's', 'takeaways': value})
