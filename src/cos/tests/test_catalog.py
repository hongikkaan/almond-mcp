"""The reviewed image result type must not weaken inert schema generation."""
import ast
import sys
import unittest

from build_catalog import checked_stub, generate
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
