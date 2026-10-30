"""Real MCP protocol checks with a fake executor; never connect to a Rhino port."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from fastmcp import Client, FastMCP
from mcp_server import configure_project_context
from project import connection_paths, process_start_ticks, write_json
from almond_mcp.retrieval_store import AlmondStore
from workspace import Workspace


FIXTURE_ROOT = None
FIXTURE_DIRECTORY = None


def setUpModule():
    global FIXTURE_ROOT, FIXTURE_DIRECTORY
    data = Path(__file__).resolve().parent / 'data'
    data.mkdir(parents=True, exist_ok=True)
    FIXTURE_DIRECTORY = tempfile.TemporaryDirectory(prefix='_mcp_context_', dir=data)
    FIXTURE_ROOT = Path(FIXTURE_DIRECTORY.name)


def tearDownModule():
    FIXTURE_DIRECTORY.cleanup()


class McpContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = FIXTURE_ROOT / uuid.uuid4().hex
        self.root.mkdir()
        model = self.root / "설계 O'Brien.3dm"
        model.write_bytes(b'PATH FIXTURE ONLY; NOT A RHINO DOCUMENT')
        token = uuid.uuid4().hex
        self.locations = connection_paths(model, 'A', token, create=True)
        self.binding = dict(self.locations, schema='almond-project', storage_protocol=2,
                            attachment='terminal', label='A', port=5501, token=token,
                            pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()),
                            valid=True,
                            rhino_temp=r'C:\Original-Rhino-Temp')
        self.ready = Path(self.locations['ready_path'])
        write_json(self.ready, self.binding)
        args = SimpleNamespace(session=self.ready, token=token)
        self.calls = []
        self.observations = []
        self.enterContext(patch.dict(os.environ, {"ALMOND_PROJECT_ROOT": self.locations["project_dir"]}))
        runtime = SimpleNamespace(workspace=Workspace(self.locations, AlmondStore(self.locations["state_db"])),
                                  rhinocode_availability=lambda: {"available": False, "reason": "fixture"},
                                  get_rhino_execution=lambda *args: {"status": "pending", "request_id": "fixture"})
        self.runtime = runtime
        def sender(payload):
            self.observations.append(json.loads(payload))
            return json.dumps({"status": "success", "document": {"path": str(model), "name": model.name}, "warnings": []})
        self.mcp = FastMCP('Path fixture', instructions='Keep upstream instructions.')

        @self.mcp.tool()
        def execute_rhino_script(script: str) -> str:
            """Original executor description."""
            self.calls.append(script)
            return script

        @self.mcp.tool()
        def unrelated() -> str:
            return 'unchanged'

        self.original_schema = (await self.mcp.get_tool('execute_rhino_script')).parameters
        await configure_project_context(self.mcp, args, self.binding, self.locations, sender=sender, runtime=runtime)

    async def test_project_info_preserves_executor_metadata(self):
        async with Client(self.mcp) as client:
            self.assertEqual(client.instructions, 'Keep upstream instructions.')
            tools = {tool.name: tool for tool in await client.list_tools()}
            self.assertEqual(set(tools), {'execute_rhino_script', 'unrelated', 'project_info', 'set_working_plan', 'rename_artifact_folder', 'execute_project_python', 'get_rhino_execution'})
            tool = tools['execute_rhino_script']
            self.assertEqual(tool.description, 'Original executor description.')
            self.assertEqual(tool.input_schema, self.original_schema)

    async def test_project_python_uses_bound_rhinocode_and_retains_pending_request(self):
        directory = self.root / "tmp" / "project-python"
        self.runtime.workspace = SimpleNamespace(artifact_path=lambda: directory)
        calls = []
        self.runtime.execute_rhinocode = lambda *args, **kwargs: calls.append((args, kwargs)) or {
            "status": "pending", "completed": False, "request_id": "same-execution"}
        async with Client(self.mcp) as client:
            result = await client.call_tool('execute_project_python', {'code': 'result = doc.Name', 'timeout_seconds': 1})
            value = json.loads(result.content[0].text)
            self.assertEqual(value['request_id'], 'same-execution')
            self.assertFalse(value['completed'])
            self.assertEqual(calls, [(('result = doc.Name', 'python', 1), {'working_directory': str(directory)})])
            self.assertFalse(directory.exists())  # Rhino creates it after target validation.

    async def test_metadata_distinguishes_project_and_rhino_temp(self):
        async with Client(self.mcp) as client:
            result = await client.call_tool('project_info', {})
            info = json.loads(result.content[0].text)
            self.assertEqual(info['project']['project_root'], self.locations['project_dir'])
            self.assertTrue(info['project']['root_variable_set'])
            self.assertEqual(info['project']['database'], '.almond/scene.sqlite3')
            self.assertEqual(info['artifacts']['artifact_dir'], '')
            self.assertTrue(info['document']['live_document_checked'])
            self.assertTrue(info['document']['is_bound_document'])
            self.assertEqual(info['document']['path'], Path(self.locations['model_path']).name)
            self.assertNotIn('runtime', info)
            self.assertNotIn('instructions', info)
            self.assertEqual(self.observations, [{"type": "get_rhino_context", "sections": ["document"], "selection_limit": 0}])
            runtime = json.loads((await client.call_tool('project_info', {'sections': ['runtime']})).content[0].text)
            self.assertFalse(Path(runtime['runtime']['rhino_temp_at_attach']).is_absolute())
            self.assertEqual(len(self.observations), 1)
            self.assertEqual(self.calls, [])

    async def test_execution_recovery_remains_read_only_after_binding_invalidation(self):
        self.binding['valid'] = False
        write_json(self.ready, self.binding)
        async with Client(self.mcp) as client:
            value = json.loads((await client.call_tool('get_rhino_execution', {})).content[0].text)
            self.assertEqual(value['request_id'], 'fixture')
            self.assertEqual(self.calls, [])
            self.assertEqual(self.observations, [])

    async def test_instructions_and_topics_keep_one_snapshot_after_disk_changes(self):
        from almond_mcp.features.guidance.tools import register
        from almond_mcp.modeling_guidance import PACKAGE, startup_instructions, project_instructions
        startup = startup_instructions()
        expected = project_instructions()
        register(self.mcp, object())
        changed_paths = {PACKAGE / 'BASIC-INSTRUCTIONS.md'}
        original_text, original_bytes = Path.read_text, Path.read_bytes

        def changed_text(path, *args, **kwargs):
            return 'NEW_GUIDANCE_SENTINEL' if path in changed_paths else original_text(path, *args, **kwargs)

        def changed_bytes(path):
            return b'NEW_GUIDANCE_SENTINEL' if path in changed_paths else original_bytes(path)

        async with Client(self.mcp) as client:
            before = json.loads((await client.call_tool('get_modeling_guide', {})).content[0].text)
            # The first project_info instructions call is after the simulated update.
            with patch.object(Path, 'read_text', changed_text), patch.object(Path, 'read_bytes', changed_bytes):
                result = await client.call_tool('project_info', {'sections': ['instructions']})
                instructions = json.loads(result.content[0].text)['instructions']
                after = json.loads((await client.call_tool('get_modeling_guide', {})).content[0].text)
                self.assertEqual(instructions, expected)
                self.assertEqual(startup_instructions(), startup)
                self.assertEqual(before, after)
        self.assertEqual(self.observations, [])
        self.assertEqual(self.calls, [])

    async def test_description_change_preserves_script_and_other_tools(self):
        script = 'UNEXECUTED fixture text with quotes, \\paths and 한글'
        async with Client(self.mcp) as client:
            result = await client.call_tool('execute_rhino_script', {'script': script})
            self.assertEqual(result.content[0].text, script)
            self.assertEqual(self.calls, [script])
            other = await client.call_tool('unrelated', {})
            self.assertEqual(other.content[0].text, 'unchanged')

    async def test_invalidated_binding_rejects_metadata_without_executor(self):
        async with Client(self.mcp) as client:
            self.binding['valid'] = False
            write_json(self.ready, self.binding)
            with self.assertRaisesRegex(Exception, 'connection ended or changed'):
                await client.call_tool('project_info', {})
            self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
