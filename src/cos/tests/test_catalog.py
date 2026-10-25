"""The reviewed image result type must not weaken inert schema generation."""
import ast
import sys
import tempfile
from pathlib import Path
import unittest

from build_catalog import checked_stub, collect_tool_functions, generate
from runtime import check_contract, load_catalog


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_generation_stays_inert_and_matches_checked_catalog(self):
        self.assertNotIn("almond_mcp.server", sys.modules)
        generated = await generate()
        self.assertNotIn("almond_mcp.server", sys.modules)
        self.assertEqual(generated, load_catalog())
        self.assertEqual(len(generated["tools"]), 77)
        check_contract(generated)

    def test_only_a_direct_toolresult_return_is_allowed(self):
        safe = ast.parse("def image(max_width: StrictInt = 1280) -> ToolResult:\n    pass").body[0]
        checked_stub(safe)
        for source in (
            "def bad(value: ToolResult) -> str:\n    pass",
            "def bad() -> list[ToolResult]:\n    pass",
            "def bad() -> dangerous.Type:\n    pass",
            "def bad() -> dangerous():\n    pass",
            "def bad(value: str = dangerous()) -> str:\n    pass",
        ):
            with self.subTest(source=source), self.assertRaises((ValueError, TypeError)):
                checked_stub(ast.parse(source).body[0])


class FeatureSourceTests(unittest.TestCase):
    def test_factory_sources_are_read_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = root / "server.py"
            server.write_text("@mcp.tool()\ndef legacy() -> str:\n    return 'old'\n", encoding="utf-8")
            feature = root / "features" / "sample"
            feature.mkdir(parents=True)
            tool = feature / "tools.py"
            tool.write_text(
                "raise RuntimeError('Never import a source to collect schemas')\n"
                "def register(mcp, context):\n"
                "    @mcp.tool(annotations={'readOnlyHint': True})\n"
                "    def moved(value: str = '') -> str:\n"
                "        return context.sender(value)\n"
                "    return {'moved': moved}\n", encoding="utf-8")
            nodes = collect_tool_functions(server)
            self.assertEqual([n.name for n in nodes], ["legacy", "moved"])
            for node in nodes:
                checked_stub(node)
            tool.write_text("def register(mcp, context):\n    @mcp.tool()\n    def legacy() -> str:\n        pass\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Duplicate"):
                collect_tool_functions(server)
