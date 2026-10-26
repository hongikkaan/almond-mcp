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
        runtime = SimpleNamespace(workspace=Workspace(self.locations, AlmondStore(self.locations["state_db"])))
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
            self.assertEqual(set(tools), {'execute_rhino_script', 'unrelated', 'project_info', 'set_working_plan', 'rename_artifact_folder', 'execute_project_python'})
            tool = tools['execute_rhino_script']
            self.assertEqual(tool.description, 'Original executor description.')
            self.assertEqual(tool.input_schema, self.original_schema)

    async def test_metadata_distinguishes_project_and_rhino_temp(self):
        async with Client(self.mcp) as client:
            result = await client.call_tool('project_info', {})
            info = json.loads(result.content[0].text)
            self.assertEqual(info['project']['project_root'], self.locations['project_dir'])
            self.assertTrue(info['project']['root_variable_set'])
            self.assertEqual(info['project']['database'], '.almond/DB')
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
