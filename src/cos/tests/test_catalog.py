"""The reviewed image result type must not weaken inert schema generation."""
import ast
import asyncio
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from build_catalog import checked_stub, collect_tool_functions, generate
from runtime import check_contract, load_catalog
from cos_host import exposed_tools


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    def test_tool_names_are_plain_and_have_no_legacy_aliases(self):
        catalog = load_catalog()
        public, mapping = exposed_tools(catalog)
        names = {tool.name for tool in public}
        self.assertIn("project_info", {tool["name"] for tool in catalog["tools"]})
        self.assertTrue({"project_info", "start_session", "list_connections", "connect", "disconnect"} <= names)
        self.assertEqual(len(names), len(public))
        self.assertFalse([name for name in names if any(word in name.split("_") for word in ("almond", "cli", "cos"))])
        self.assertEqual(mapping["project_info"], "project_info")

    async def test_generation_stays_inert_and_matches_startup_catalog(self):
        self.assertNotIn("almond_mcp.server", sys.modules)
        generated = await generate()
        self.assertNotIn("almond_mcp.server", sys.modules)
        self.assertEqual(generated, await asyncio.to_thread(load_catalog))
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
    def test_external_description_is_inert_and_markdown_is_fingerprinted(self):
        from runtime import digest, source_paths
        paths = source_paths(Path(__file__).resolve().parents[2] / "mcp/runtime")
        markdown = {path for path in paths.values() if path.name.endswith("-explain.md")}
        self.assertIn(paths["entry"].with_name("mcp_server-explain.md"), markdown)
        self.assertTrue(any(path.name == "tools-explain.md" for path in markdown))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "tools.py"
            note = source.with_name("tools-explain.md")
            note.write_text("<!-- instruction:sample -->\nCall sample first.\n<!-- /instruction:sample -->", encoding="utf-8")
            node = ast.parse("@mcp.tool()\n@tool_instruction(__file__, 'sample')\ndef sample() -> str:\n    dangerous()\n").body[0]
            node._guidance_source = str(source)
            stub = checked_stub(node)
            self.assertEqual(ast.get_docstring(stub), "Call sample first.")
            self.assertEqual(len(stub.decorator_list), 1)
            catalog = {"packages": {}, "sources": {"guidance": digest(note)}}
            with patch("runtime.source_paths", return_value={"guidance": note}):
                check_contract(catalog)
                note.write_text(note.read_text(encoding="utf-8").replace("first", "last"), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "changed"):
                    check_contract(catalog)
            node.decorator_list[1].args[1] = ast.Call(ast.Name("dangerous", ast.Load()), [], [])
            with self.assertRaises(ValueError):
                checked_stub(node)

    def test_fresh_start_reads_changed_tools_without_a_catalog_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, entry = root / "server.py", root / "mcp_server.py"
            server.write_text("raise RuntimeError('must not import')\n@mcp.tool()\ndef sample(value: str = 'old') -> str:\n    pass\n", encoding="utf-8")
            entry.write_text("@mcp.tool()\ndef project_info() -> dict:\n    pass\n", encoding="utf-8")
            paths = {"server": server, "entry": entry}
            with patch("build_catalog.source_paths", return_value=paths), patch("runtime.source_paths", return_value=paths):
                first = load_catalog()
                server.write_text(server.read_text(encoding="utf-8").replace("'old'", "'new'") + "\n@mcp.tool()\ndef added() -> bool:\n    pass\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "changed"):
                    check_contract(first)
                second = load_catalog()
                check_contract(second)
            names = {t["name"]: t for t in second["tools"]}
            self.assertEqual(set(names), {"sample", "added", "project_info"})
            self.assertEqual(names["sample"]["inputSchema"]["properties"]["value"]["default"], "new")
            self.assertNotIn("almond_mcp.server", sys.modules)
            self.assertFalse(list(root.glob("*.sqlite3")))

    def test_unlocked_dependency_version_is_rejected_before_listing_tools(self):
        with patch("build_catalog.version", return_value="0.0.0-unreviewed"):
            with self.assertRaisesRegex(RuntimeError, "version|expects"):
                load_catalog()

    def test_worker_rejects_source_change_even_when_schema_is_identical(self):
        import os
        import cos_worker
        original = {"sources": {"server": "old"}, "packages": {}, "tools": []}
        changed = dict(original, sources={"server": "new"})
        from runtime import catalog_identity
        with patch.dict(os.environ, {"ALMONDCOS_SESSION_TOKEN": "fixture",
                                    "ALMONDCOS_CATALOG_ID": catalog_identity(original)}), \
                patch.object(sys, "argv", ["worker", "--session", "fixture", "--port", "5501", "--connection-id", "fixture"]), \
                patch.object(cos_worker, "load_catalog", return_value=changed), \
                patch.object(cos_worker, "check_contract"):
            with self.assertRaisesRegex(RuntimeError, "client.*source|source.*client"):
                cos_worker.main()

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
