"""Runtime recovery and durable cleanup fences; no real Rhino/CLI is used."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from project import connection_paths, process_start_ticks, read_json, write_json
from shared_store import ProjectRuntime, validate_artifact_writers
from storage_cleanup import cleanup_retired_sessions, process_identity_alive, rhinocode_settled
from test_native_request import Context, Message


class FakeExecution:
    def __init__(self):
        self.request_id = uuid4().hex
        self.done = False

    def snapshot(self):
        return dict(request_id=self.request_id, pending=not self.done,
                    uncertain=not self.done, completed=self.done)


class FakeCli:
    def __init__(self, runtime):
        self.runtime = runtime
        self.handle = None
        self.calls = 0
        self.native_failure = False
        self.finish_immediately = False

    def execute(self, **arguments):
        self.calls += 1
        self.handle = FakeExecution()
        arguments['register'](self.handle)
        self.folder = arguments['operation_dir']
        (self.folder / 'execution-evidence.json').write_text('{"result":42}', encoding='utf-8')
        if self.native_failure:
            self.handle.done = True
            try:
                self.runtime.send(lambda *_: '{}', b'{"type":"get_rhino_context"}')
            except RuntimeError:
                pass
        self.handle.done = self.finish_immediately or self.native_failure
        return dict(status='completed' if self.handle.done else 'pending', request_id=self.handle.request_id)

    def get_execution(self, **arguments):
        return dict(self.handle.snapshot(), result={'answer': 42})


class RuntimeCliTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[4] / 'data'
        base.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='_rc_', dir=base)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        model = self.root / 'fixture.3dm'
        model.write_bytes(b'PATH FIXTURE; NEVER OPENED BY RHINO')
        token = uuid4().hex
        self.locations = connection_paths(model, 'A', token, create=True)
        identity = dict(pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
        self.binding = dict(self.locations, **identity, schema='almond-project', storage_protocol=2,
                            token=token, label='A', port=5501, valid=True, document_serial='1')
        self.session = Path(self.locations['session_dir'])
        write_json(self.locations['ready_path'], self.binding)
        write_json(self.session / 'worker.json', dict(identity, schema='almond-worker', token=token))
        write_json(self.session / 'native.json', dict(schema='almond-native', storage_protocol=2,
            token=token, phase='listening', pending=0, capabilities={'rhinocode_fence': 1}))
        self.runtime = ProjectRuntime(SimpleNamespace(session=self.locations['ready_path'], token=token),
                                      self.binding, self.locations, check_owner=False)
        self.cli = FakeCli(self.runtime)
        self.runtime.rhinocode = self.cli

    async def execute(self):
        async def call(context):
            return self.runtime.execute_rhinocode('result = 42', 'python', 1)
        return await self.runtime.on_call_tool(Context(Message('execute_rhino_script')), call)

    async def recover(self):
        async def call(context):
            return self.runtime.get_rhino_execution()
        return await self.runtime.on_call_tool(Context(Message('get_rhino_execution')), call)

    async def test_late_receipt_recovers_same_operation_and_keeps_result_files(self):
        first = await self.execute()
        operation = read_json(self.session / 'operation.json')
        self.assertEqual(operation['state'], 'unconfirmed')
        self.assertTrue(self.runtime.unconfirmed)
        with self.assertRaisesRegex(RuntimeError, 'unconfirmed|not confirmed|완료|확인'):
            await self.execute()
        self.assertEqual(self.cli.calls, 1)
        self.cli.handle.done = True
        recovered = await self.recover()
        self.assertEqual(first['request_id'], recovered['request_id'])
        self.assertEqual(recovered['result']['answer'], 42)
        self.assertNotIn('transport', recovered['runtime_completion'])
        self.assertNotIn('external_requests', recovered['runtime_completion'])
        self.assertFalse(self.runtime.unconfirmed)
        self.assertFalse(self.runtime.completion()['uncertain'])
        self.assertEqual(read_json(self.session / 'operation.json')['operation_id'], operation['operation_id'])
        self.assertEqual(read_json(self.session / 'operation.json')['state'], 'completed')
        self.assertFalse((self.session / 'artifact-write.json').exists())
        self.assertTrue((self.cli.folder / 'execution-evidence.json').is_file())
        self.assertEqual(self.cli.calls, 1)

    async def test_native_uncertainty_survives_exact_cli_completion(self):
        self.cli.native_failure = True
        await self.execute()
        self.cli.handle.done = True
        await self.recover()
        self.assertTrue(self.runtime.unconfirmed)
        self.assertTrue(self.runtime.completion()['native_uncertain'])
        self.assertTrue((self.session / 'artifact-write.json').is_file())

    async def test_successful_cli_result_survives_ordinary_operation_cleanup(self):
        self.cli.finish_immediately = True
        await self.execute()
        self.assertFalse(self.runtime.unconfirmed)
        self.assertTrue(self.cli.folder.is_dir())
        self.assertFalse((self.session / 'artifact-write.json').exists())

    def test_callback_outside_an_owned_operation_never_dispatches(self):
        with self.assertRaisesRegex(RuntimeError, 'No active operation'):
            self.runtime.execute_rhinocode('result=1', 'python', 1)
        self.assertEqual(self.cli.calls, 0)

    async def test_old_or_stopped_native_plugin_cannot_dispatch_official_execution(self):
        native = read_json(self.session / 'native.json')
        for changed in ({'capabilities': {}}, {'capabilities': {'rhinocode_fence': True}},
                        {'phase': 'stopped'}, {'token': uuid4().hex}):
            with self.subTest(changed=changed):
                write_json(self.session / 'native.json', dict(native, **changed))
                with self.assertRaisesRegex(RuntimeError, 'completion fence'):
                    await self.execute()
                self.assertFalse(self.runtime.rhinocode_availability()['available'])
                self.assertEqual(self.cli.calls, 0)

    def test_legacy_native_stop_cannot_clear_unresolved_cli_artifact_fence(self):
        write_json(self.session / 'artifact-write.json', {
            'token': self.binding['token'], 'artifact_write': True, 'state': 'unconfirmed'})
        write_json(self.session / 'native.json', {
            'schema': 'almond-native', 'token': self.binding['token'], 'phase': 'stopped', 'pending': 0})
        write_json(self.session / 'rhinocode.json', {'schema': 'malformed-execution'})
        with self.assertRaisesRegex(RuntimeError, 'RhinoCode'):
            validate_artifact_writers(self.locations['storage'])

    def test_retired_cleanup_keeps_cli_journal_until_rhino_exit(self):
        write_json(self.locations['ready_path'], dict(self.binding, valid=False))
        write_json(self.session / 'worker.json', {'closed': True})
        write_json(self.session / 'native.json', {'phase': 'stopped', 'pending': 0})
        write_json(self.session / 'rhinocode.json', {'schema': 'malformed-execution'})
        with patch('storage_cleanup.process_identity_alive', return_value=True):
            self.assertEqual(cleanup_retired_sessions(Path(self.locations['storage'])), [])
        self.assertTrue(self.session.is_dir())
        with patch('storage_cleanup.process_identity_alive', return_value=False):
            self.assertEqual(cleanup_retired_sessions(Path(self.locations['storage'])), [self.binding['token']])
        self.assertFalse(self.session.exists())

    def test_invalid_owner_identity_cannot_prove_process_exit(self):
        for identity in ({'pid': 0, 'process_start_ticks': '123'},
                         {'pid': -1, 'process_start_ticks': '123'},
                         {'pid': True, 'process_start_ticks': '123'},
                         {'pid': os.getpid(), 'process_start_ticks': '0'},
                         {'pid': os.getpid(), 'process_start_ticks': '000123'},
                         {'pid': os.getpid(), 'process_start_ticks': str(2 ** 63)},
                         {'pid': os.getpid(), 'process_start_ticks': 'unknown'}):
            with self.subTest(identity=identity), patch('storage_cleanup.ctypes.WinDLL',
                    side_effect=AssertionError('Invalid identity reached process access')):
                self.assertIsNone(process_identity_alive(identity))

    def test_actual_late_completion_releases_cleanup_and_artifact_fences_together(self):
        request, operation, nonce = uuid4().hex, uuid4().hex, uuid4().hex
        target = {key: self.binding[key] for key in ('pid', 'process_start_ticks', 'model_path')}
        target.update(document_serial=1, pipe_id='fixture-pipe')
        child = dict(pid=987654, process_start_ticks='1234')
        journal = dict(schema='almond-rhinocode-execution', version=1, token=self.binding['token'],
                       request_id=request, operation_id=operation, nonce=nonce,
                       source_hash='a' * 64, language='python', target=target, child=child)
        folder = Path(self.locations['call_root']) / operation / 'rhinocode' / request
        folder.mkdir(parents=True)
        write_json(self.session / 'rhinocode.json', journal)
        write_json(self.locations['ready_path'], dict(self.binding, valid=False))
        write_json(self.session / 'worker.json', {'closed': True})
        write_json(self.session / 'native.json', dict(schema='almond-native', token=self.binding['token'],
                                                      phase='stopped', pending=0))
        write_json(self.session / 'artifact-write.json', dict(token=self.binding['token'],
                   artifact_write=True, state='unconfirmed'))
        final = dict(journal, schema='almond-rhinocode-completion', execution_complete=True,
                     status='success', mutation_state='completed', nonce=uuid4().hex)
        write_json(folder / 'complete.json', final)
        alive = lambda identity: identity.get('pid') != child['pid']
        with patch('storage_cleanup.process_identity_alive', side_effect=alive), \
                patch('shared_store.process_identity_alive', side_effect=alive):
            self.assertFalse(rhinocode_settled(self.session))
            self.assertEqual(cleanup_retired_sessions(Path(self.locations['storage'])), [])
            with self.assertRaisesRegex(RuntimeError, 'RhinoCode'):
                validate_artifact_writers(self.locations['storage'])
            final['nonce'] = nonce
            write_json(folder / 'complete.json', final)
            self.assertTrue(rhinocode_settled(self.session))
            validate_artifact_writers(self.locations['storage'])
            self.assertEqual(cleanup_retired_sessions(Path(self.locations['storage'])), [self.binding['token']])
        self.assertFalse(self.session.exists())
        self.assertFalse(folder.exists())
