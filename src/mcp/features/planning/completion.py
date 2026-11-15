"""One fixed automatic temp cleanup through the runtime-bound native sender.

The store owns transition/revision checks. This module never selects candidates,
stores confirmation state, retries a mutation, or changes planning records.
"""
from __future__ import annotations

import json

from almond_mcp.instruction_text import read_instruction


def _error(message, *, uncertain=False, code='step_cleanup_failed'):
    return dict(status='error', error_code=code, message=message,
                cleanup_complete=False, mutation_state='unknown' if uncertain else 'not_started',
                requires_reconciliation=uncertain)


def cleanup(send, model_path):
    """Clean the bound document's entire top-level temp hierarchy exactly once."""
    if not isinstance(model_path, str) or not model_path.strip():
        return _error('A bound saved model path is required.')
    dispatched = False
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","sections":[],"selection_limit":0}'))
        if not isinstance(context, dict) or context.get('status') != 'success':
            return _error("Could not verify the bound Bridge's Step cleanup capability.")
        capabilities = context.get('capabilities')
        version = capabilities.get('step_completion') if isinstance(capabilities, dict) else None
        if type(version) is not int or version != 2:
            return _error(read_instruction(__file__, 'unsupported'), code='unsupported_step_completion')
        completed_message = read_instruction(__file__, 'completed')
        not_needed_message = read_instruction(__file__, 'not_needed')
        request = dict(type='step_completion', expected_model_path=model_path)
        dispatched = True
        reply = json.loads(send(json.dumps(request, ensure_ascii=False).encode('utf-8'), timeout=60.0))
        if not isinstance(reply, dict):
            raise ValueError('The Bridge returned an invalid Step cleanup response.')
        if reply.get('status') != 'success':
            if reply.get('mutation_state') != 'not_started':
                return {**reply, **_error(reply.get('message', 'Cleanup completion is unconfirmed.'),
                                         uncertain=True), 'native_status': reply.get('status')}
            return {**reply, 'cleanup_complete': False}
        result = reply.get('result')
        if (reply.get('result_error') or reply.get('requires_reconciliation')
                or not isinstance(result, dict) or result.get('cleanup_complete') is not True
                or type(result.get('document_serial')) is not int or result['document_serial'] <= 0
                or any(type(result.get(key)) is not int or result[key] < 0
                       for key in ('deleted_object_count', 'deleted_layer_count'))
                or result.get('mutation_state') not in ('applied', 'not_needed')
                or result.get('requires_reconciliation')
                or reply.get('mutation_state') in ('unknown', 'partial')):
            raise ValueError('Cleanup ran but its completion could not be confirmed. Inspect Rhino before any retry.')
        removed_any = result['deleted_object_count'] > 0 or result['deleted_layer_count'] > 0
        if (result['mutation_state'] == 'applied') != removed_any:
            raise ValueError('Cleanup state does not match its deleted counts. Inspect Rhino before any retry.')
    except Exception as exc:
        return _error(str(exc), uncertain=dispatched)
    return {**result, 'status': 'success',
            'message': (completed_message if result['mutation_state'] == 'applied' else not_needed_message)
                       + f" 삭제 객체: {result['deleted_object_count']}개, 레이어: {result['deleted_layer_count']}개."}
