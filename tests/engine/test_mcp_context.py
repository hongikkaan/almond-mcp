"""Real MCP protocol checks with a fake executor; never connect to a Rhino port."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid

from fastmcp import Client, FastMCP
from mcp_server import configure_project_context
from project import connection_paths, process_start_ticks, write_json


FIXTURE_ROOT = None


def setUpModule():
    global FIXTURE_ROOT
    data = Path(__file__).resolve().parent / 'data'
    data.mkdir(parents=True, exist_ok=True)
    FIXTURE_ROOT = Path(tempfile.mkdtemp(prefix='_mcp_context_', dir=data))
    print('MCP context fixtures retained at:', FIXTURE_ROOT, flush=True)


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
        await configure_project_context(self.mcp, args, self.binding, self.locations)

    async def test_paths_visible_in_protocol_metadata_and_execution_tool(self):
        async with Client(self.mcp) as client:
            instructions = client.instructions
            self.assertIn('Keep upstream instructions.', instructions)
            self.assertIn(self.locations['call_root'], instructions)
            tools = {tool.name: tool for tool in await client.list_tools()}
            self.assertEqual(set(tools), {'execute_rhino_script', 'unrelated', 'almond_project_info'})
            tool = tools['execute_rhino_script']
            self.assertIn('Original executor description.', tool.description)
            self.assertIn(self.locations['call_root'], tool.description)
            self.assertIn('System.IO.Path.Combine(@"', tool.description)
            self.assertEqual(tool.input_schema, self.original_schema)

    async def test_metadata_distinguishes_project_and_rhino_temp(self):
        async with Client(self.mcp) as client:
            result = await client.call_tool('almond_project_info', {})
            info = json.loads(result.content[0].text)
            self.assertEqual(info['artifact_dir'], self.locations['call_root'])
            self.assertEqual(info['state_db'], self.locations['state_db'])
            self.assertEqual(info['storage_protocol'], 2)
            self.assertEqual(info['session_dir'], self.locations['session_dir'])
            self.assertEqual(info['ready_path'], str(self.ready))
            self.assertEqual(info['storage_scope'], 'model_directory')
            self.assertEqual(info['rhino_temp_at_attach'], r'C:\Original-Rhino-Temp')
            self.assertNotEqual(info['artifact_dir'], info['rhino_temp_at_attach'])
            self.assertEqual(info['mcp_temp'], info['effective_temp'])
            self.assertFalse(info['live_document_checked'])
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
                await client.call_tool('almond_project_info', {})
            self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
