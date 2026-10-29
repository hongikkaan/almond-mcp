"""Broker-restart evidence recovery from owned locators, without a Rhino process."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from execution_recovery import ExecutionRecoveryStore
from external_host import SessionAdapter, exposed_tools, result_dict
from project import connection_paths, process_start_ticks, read_json, write_json


CATALOG = {'tools': [{
    'name': 'get_rhino_execution', 'description': 'Read retained execution',
    'inputSchema': {'type': 'object', 'properties': {'request_id': {'type': 'string', 'default': ''}}}}]}


class RestartRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[3] / 'data'
        base.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='_rr_', dir=base)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = self.root / 'broker'
        self.store = ExecutionRecoveryStore(self.data)
        self.request = uuid4().hex
        self.binding, self.folder, self.final = self.retained('one', self.request)

    def retained(self, name, request):
        project = self.root / name
        project.mkdir()
        model = project / 'fixture.3dm'
        model.write_bytes(b'PATH FIXTURE; NEVER OPENED BY RHINO')
        token, operation = uuid4().hex, uuid4().hex
        locations = connection_paths(model, 'A', token, create=True)
        binding = dict(locations, schema='almond-project', storage_protocol=2, token=token,
                       label='A', port=5501, valid=True, document_serial='7',
                       pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
        write_json(locations['ready_path'], binding)
        self.store.remember(binding)
        folder = Path(locations['call_root']) / operation / ('rc-' + request[:12])
        folder.mkdir(parents=True)
        target = {key: binding[key] for key in ('pid', 'process_start_ticks', 'model_path')}
        target.update(document_serial=7, pipe_id='fixture-pipe')
        journal = dict(schema='almond-rhinocode-execution', version=1, layout='compact-v1',
                       token=token, operation_id=operation, request_id=request, nonce=uuid4().hex,
                       source_hash='b' * 64, language='python', target=target,
                       child=dict(pid=987654, process_start_ticks='123'))
        write_json(folder / 'request.json', journal)
        write_json(Path(locations['session_dir']) / 'rhinocode.json', journal)
        raw = json.dumps({'answer': 42}, ensure_ascii=True).encode('ascii')
        (folder / 'result.json').write_bytes(raw)
        final = dict(journal, schema='almond-rhinocode-completion', execution_complete=True,
                     status='success', mutation_state='completed', result_available=True,
                     result_bytes=len(raw), result_sha256=hashlib.sha256(raw).hexdigest())
        write_json(folder / 'complete.json', final)
        write_json(locations['ready_path'], dict(binding, valid=False))
        return binding, folder, final

    async def recover(self, **arguments):
        adapter = SessionAdapter(CATALOG, data=self.data)
        with patch('storage_cleanup.process_identity_alive',
                   side_effect=lambda identity: identity.get('pid') == os.getpid()):
            value = await adapter.call('get_rhino_execution', dict(request_id=self.request, **arguments))
        self.assertFalse(adapter.broker.connections)
        self.assertFalse(adapter.broker.background)
        await adapter.close()
        return value

    async def test_new_adapter_recovers_exact_result_without_connect_or_worker(self):
        result = result_dict(await self.recover())
        self.assertTrue(result['completed'])
        self.assertEqual(result['result'], {'answer': 42})
        self.assertTrue(result['requires_reconnect'])
        self.assertTrue(result['recovery_only'])
        self.assertTrue(result['rhino_process_alive'])
        self.assertEqual(result['target_identity']['document_serial'], '7')
        self.assertFalse(Path(self.binding['state_db']).exists())

    async def test_dead_cli_without_final_is_pending_after_restart(self):
        (self.folder / 'complete.json').unlink()
        result = result_dict(await self.recover())
        self.assertFalse(result['completed'])
        self.assertTrue(result['uncertain'])
        self.assertTrue(result['pending'])

    async def test_retained_result_survives_original_model_rename_and_delete(self):
        original = Path(self.binding['model_path'])
        renamed = original.with_name('renamed.3dm')
        original.rename(renamed)
        first = result_dict(await self.recover())
        self.assertTrue(first['completed'])
        self.assertEqual(first['result'], {'answer': 42})
        self.assertEqual(first['target_identity']['model_path'], str(original))
        renamed.unlink()
        second = result_dict(await self.recover())
        self.assertTrue(second['completed'])
        self.assertEqual(second['result'], {'answer': 42})
        self.assertTrue(self.folder.is_dir())
        self.assertFalse(original.exists())
        self.assertFalse(Path(self.binding['state_db']).exists())

    async def test_launch_crash_can_expose_result_without_falsely_releasing_lifecycle(self):
        journal = read_json(self.folder / 'request.json')
        journal['child'] = None
        write_json(self.folder / 'request.json', journal)
        write_json(Path(self.binding['session_dir']) / 'rhinocode.json', journal)
        result = result_dict(await self.recover())
        self.assertTrue(result['native_completed'])
        self.assertFalse(result['completed'])
        self.assertTrue(result['uncertain'])
        self.assertEqual(result['result'], {'answer': 42})
        self.assertTrue(result['requires_reconnect'])

    async def test_replaced_document_identity_cannot_supply_old_result(self):
        write_json(self.binding['ready_path'], dict(self.binding, valid=False, document_serial='8'))
        result = await self.recover()
        self.assertTrue(result.is_error)
        self.assertIn('target changed', result.content[0].text)

    async def test_ambiguous_request_id_does_not_select_a_session(self):
        self.retained('two', self.request)
        result = await self.recover()
        self.assertTrue(result.is_error)
        self.assertIn('unique retained session', result.content[0].text)

    def test_only_recovery_tool_allows_omitting_connection_id(self):
        from test_broker import CATALOG as EXECUTE
        tools, _ = exposed_tools({'tools': [*CATALOG['tools'], *EXECUTE['tools']]})
        schemas = {tool.name: tool.input_schema for tool in tools}
        self.assertNotIn('connection_id', schemas['get_rhino_execution'].get('required', []))
        self.assertIn('anyOf', schemas['get_rhino_execution'])
        self.assertIn('connection_id', schemas['execute']['required'])
