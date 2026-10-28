"""The direct Codex entry must never import the CoS application entry."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from runtime import ROOT
from external_host import server_description
from almond_mcp.modeling_guidance import startup_instructions


class ClientRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_codex_and_cos_keep_equal_tools_and_distinct_server_names(self):
        inventories = []
        with tempfile.TemporaryDirectory() as directory:
            for module, client, identity in (("codex_host", "codex", "beyond"), ("cos_host", "cos", "CoS")):
                data = Path(directory) / module
                entry = "import sys; "
                if module == "codex_host":
                    entry += "sys.modules['cos_host'] = None; "
                entry += f"from pathlib import Path; from {module} import main; main(Path({str(data)!r}))"
                params = StdioServerParameters(command=sys.executable,
                    args=["-B", "-X", "utf8", "-u", "-c", entry],
                    cwd=str(ROOT), env=dict(os.environ))
                async with stdio_client(params) as (reader, writer):
                    async with ClientSession(reader, writer, read_timeout_seconds=30) as session:
                        initialized = await session.initialize()
                        self.assertEqual(initialized.server_info.name, identity)
                        description = server_description(client)
                        self.assertTrue(description.startswith(identity + "는 "))
                        self.assertNotIn("{server_name}", description)
                        self.assertEqual(initialized.server_info.description, description)
                        self.assertEqual(initialized.instructions, description + "\n\n" + startup_instructions())
                        tools = await session.list_tools()
                        descriptions = {tool.name: tool.description for tool in tools.tools}
                        self.assertIn("get_modeling_guide", descriptions)
                        self.assertEqual(descriptions["project_info"], 'Read selected project information.')
                        inventories.append([tool.model_dump() for tool in tools.tools])
                        listing = await session.call_tool("list_connections", {})
                        self.assertFalse(listing.is_error)
                        payload = listing.structured_content or json.loads(listing.content[0].text)
                        self.assertEqual(payload["connections"], [])
                        self.assertEqual(payload["targets"], [])
        self.assertEqual(inventories[0], inventories[1])
