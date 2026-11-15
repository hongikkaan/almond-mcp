"""Clean top-level temp once before each new completed transition commits."""
import os

from almond_mcp.features.planning import completion
from almond_mcp.features.planning.output import update_ack


class _CleanupFailed(Exception):
    def __init__(self, result):
        super().__init__(result.get('message', 'Step cleanup did not complete.'))
        self.result = result


class StepCompletionFlow:
    def __init__(self, context):
        self.context = context

    def update(self, request):
        changes = {name: getattr(request, name) for name in (
            'plan_id', 'step_id', 'status', 'input_refs', 'output_refs', 'takeaways',
            'design_rationale', 'expected_revision', 'loop_no')}
        store = self.context.retrieval_store
        if request.status != 'completed':
            return update_ack(store.edit_step(**changes), 'plan', request.step_id)
        cleaned = None

        def cleanup():
            nonlocal cleaned
            cleaned = completion.cleanup(self.context._send_and_receive,
                                         os.environ.get('ALMOND_MODEL_PATH', ''))
            if cleaned.get('status') != 'success' or cleaned.get('cleanup_complete') is not True:
                raise _CleanupFailed(cleaned)

        try:
            # The store validates first and invokes this hook only when a
            # non-completed Step is actually becoming completed.
            result = update_ack(store.edit_step(**changes, _before_complete=cleanup), 'plan', request.step_id)
            return result if cleaned is None else {
                **result, 'cleanup': cleaned, 'cleanup_complete': True,
                'message': cleaned.get('message', ''),
            }
        except _CleanupFailed as failure:
            return {**failure.result, 'changed': False}
        except Exception as exc:
            if cleaned is not None:
                return {'status': 'error', 'changed': False, 'cleanup': cleaned,
                        'cleanup_complete': cleaned.get('cleanup_complete', False),
                        'requires_reconciliation': True,
                        'message': f'Cleanup ran but Step completion was not confirmed: {exc}. Read the Step and inspect Rhino before another attempt.'}
            raise
