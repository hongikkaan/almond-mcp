"""Read retained execution evidence after the external broker process exits.

Locators record only sessions this adapter actually attached. Recovery never
discovers arbitrary project folders, starts a worker, or sends a Rhino command.
"""
from pathlib import Path
import re
import sys

from runtime import ENGINE


_TOKEN = re.compile(r"[0-9a-f]{32}\Z")


def _locations(binding):
    sys.path.insert(0, str(ENGINE))
    from project import connection_paths, STORAGE_PROTOCOL
    if (not isinstance(binding, dict) or binding.get('schema') != 'almond-project'
            or binding.get('storage_protocol') != STORAGE_PROTOCOL
            or type(binding.get('pid')) is not int or binding['pid'] <= 0
            or not str(binding.get('process_start_ticks', '')).isascii()
            or not str(binding.get('process_start_ticks', '')).isdecimal()
            or not 0 < int(binding['process_start_ticks']) <= 0x7FFFFFFFFFFFFFFF
            or str(int(binding['process_start_ticks'])) != str(binding['process_start_ticks'])
            or not str(binding.get('document_serial', '')).isascii()
            or not str(binding.get('document_serial', '')).isdecimal()
            or not 0 < int(binding['document_serial']) <= 0xFFFFFFFF):
        raise ValueError('Retained execution binding has an invalid native identity.')
    locations = connection_paths(binding['model_path'], binding['label'], binding['token'], recovery=True)
    for field in ('storage', 'temp', 'session_dir', 'ready_path', 'call_root'):
        if Path(str(binding.get(field, ''))).resolve() != Path(locations[field]):
            raise ValueError('Retained execution binding has an invalid ' + field + '.')
    return locations


def read_bound_execution(binding, arguments):
    """Validate the old generation, including invalidated ready state, read only."""
    locations = _locations(binding)
    from project import read_json, STORAGE_PROTOCOL
    from rhinocode import RhinocodeExecution
    from storage_cleanup import process_identity_alive
    current = read_json(locations['ready_path'])
    if (current.get('schema') != 'almond-project' or current.get('storage_protocol') != STORAGE_PROTOCOL
            or current.get('token') != binding['token'] or current.get('label') != binding['label']
            or current.get('pid') != binding['pid']
            or str(current.get('process_start_ticks')) != str(binding['process_start_ticks'])
            or str(current.get('document_serial')) != str(binding['document_serial'])
            or Path(str(current.get('model_path', ''))).resolve() != Path(binding['model_path']).resolve()):
        raise ValueError('Retained execution target changed; no result can be attributed to this binding.')
    _locations(current)
    result = RhinocodeExecution(binding, locations).get_execution(**arguments)
    result['target_identity'] = {key: binding[key] for key in
                                 ('pid', 'process_start_ticks', 'document_serial', 'model_path')}
    result['rhino_process_alive'] = process_identity_alive(binding)
    return result


class ExecutionRecoveryStore:
    def __init__(self, data):
        self.directory = Path(data).absolute() / 'execution-locators'

    def remember(self, binding):
        _locations(binding)
        from project import write_json
        from storage_cleanup import plain_descendant
        path = plain_descendant(self.directory / (binding['token'] + '.json'), self.directory.parent)
        self.directory.mkdir(parents=True, exist_ok=True)
        write_json(path, dict(schema='almond-execution-locator', version=1, binding=dict(binding)))

    def recover(self, arguments):
        request = arguments.get('request_id', '')
        if not isinstance(request, str) or not _TOKEN.fullmatch(request):
            raise ValueError('Without connection_id, get_rhino_execution requires an exact returned request_id.')
        sys.path.insert(0, str(ENGINE))
        from project import read_json
        from rhinocode import find_request_manifest
        from storage_cleanup import plain_descendant
        matches = []
        for path in self.directory.glob('*.json'):
            if not _TOKEN.fullmatch(path.stem):
                continue
            try:
                plain_descendant(path, self.directory.parent)
                record = read_json(path)
                if (record.get('schema') != 'almond-execution-locator' or type(record.get('version')) is not int
                        or record['version'] != 1):
                    continue
                binding = record.get('binding')
                locations = _locations(binding)
                if binding['token'] != path.stem:
                    continue
            except (OSError, ValueError, KeyError, TypeError):
                continue  # An unrelated stale locator cannot select a different target.
            if find_request_manifest(locations['call_root'], request) is not None:
                matches.append(binding)
        if len(matches) != 1:
            raise ValueError('No unique retained session matches request_id; the result may have been cleaned up.')
        result = read_bound_execution(matches[0], arguments)
        result.update(connection_state='unbound', requires_reconnect=True, recovery_only=True)
        return result
