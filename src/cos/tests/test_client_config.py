import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from client_config import codex_toml, generic_json, install_codex, settings


class ClientConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="almond client ' ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for relative in ("src/engine/.venv/Scripts/python.exe", "src/cos/cos_host.py"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        self.config = settings(self.root)

    def test_toml_preserves_windows_paths_and_required_client_settings(self):
        parsed = tomllib.loads(codex_toml(self.config))["mcp_servers"]["rhino"]
        self.assertEqual(parsed, self.config)
        self.assertEqual(parsed["args"][-1], str(self.root / "src/cos/cos_host.py"))
        self.assertEqual(parsed["tool_timeout_sec"], 600)
        self.assertIn("LOCALAPPDATA", parsed["env_vars"])
        self.assertNotIn("ALMONDCOS_SESSION_TOKEN", parsed["env_vars"])

    def test_generic_client_preserves_only_library_environment(self):
        result = json.loads(generic_json(self.config, {
            "LOCALAPPDATA": "C:\\User Data", "RHINO_MCP_LIBRARY_DIR": "D:\\my library",
            "UNRELATED_SECRET": "never export", "ALMONDCOS_SESSION_TOKEN": "never export",
        }))["mcpServers"]["rhino"]
        self.assertEqual(result["env"]["RHINO_MCP_LIBRARY_DIR"], "D:\\my library")
        self.assertEqual(result["env"]["PYTHONUTF8"], "1")
        self.assertNotIn("UNRELATED_SECRET", result["env"])
        self.assertNotIn("ALMONDCOS_SESSION_TOKEN", result["env"])
        self.assertNotIn("env_vars", result)

    def test_install_preserves_settings_comments_and_original_backup(self):
        path = self.root / "config.toml"
        original = b'\xef\xbb\xbf# user comment\r\nmodel = "gpt-6-astra"\r\n[mcp_servers.other]\r\ncommand = "other.exe"\r\n'
        path.write_bytes(original)
        backup = install_codex(path, self.config)
        self.assertEqual(backup.read_bytes(), original)
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(parsed["model"], "gpt-6-astra")
        self.assertEqual(parsed["mcp_servers"]["other"], {"command": "other.exe"})
        self.assertIn("# user comment", path.read_text(encoding="utf-8"))
        installed = path.read_bytes()
        self.assertIsNone(install_codex(path, self.config))
        self.assertEqual(path.read_bytes(), installed)
        self.assertEqual(len(list(self.root.glob("*.almond-backup-*"))), 1)

    def test_conflicting_or_invalid_configuration_is_not_overwritten(self):
        path = self.root / "config.toml"
        for original in ('[mcp_servers.almond_cos]\ncommand="different"\n', 'invalid = ['):
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(ValueError):
                install_codex(path, self.config)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertFalse(list(self.root.glob("*.almond-backup-*")))

    def test_new_config_and_missing_runtime(self):
        path = self.root / "new.toml"
        self.assertIsNone(install_codex(path, self.config))
        self.assertEqual(tomllib.loads(path.read_text())["mcp_servers"]["rhino"], self.config)
        (self.root / "src/cos/cos_host.py").unlink()
        with self.assertRaisesRegex(ValueError, "Missing runtime"):
            settings(self.root)

    def test_exact_owned_legacy_entry_is_migrated_without_duplicate_server(self):
        path = self.root / "config.toml"
        legacy = codex_toml(self.config).replace("mcp_servers.rhino", "mcp_servers.almond_cos")
        original = '# preserve comment\nmodel = "gpt-6-astra"\n\n' + legacy
        path.write_text(original, encoding="utf-8")
        backup = install_codex(path, self.config)
        self.assertIsNotNone(backup)
        self.assertEqual(backup.read_text(encoding="utf-8"), original)
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(parsed["mcp_servers"], {"rhino": self.config})
        self.assertEqual(parsed["model"], "gpt-6-astra")
        self.assertIn("# preserve comment", path.read_text(encoding="utf-8"))
        self.assertIsNone(install_codex(path, self.config))

    def test_modified_legacy_or_duplicate_entries_are_preserved_without_changes(self):
        path = self.root / "config.toml"
        both = codex_toml(self.config) + codex_toml(self.config).replace("mcp_servers.rhino", "mcp_servers.almond_cos")
        for original in ('[mcp_servers.almond_cos]\ncommand="custom"\n', both):
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(ValueError):
                install_codex(path, self.config)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertFalse(list(self.root.glob("*.almond-backup-*")))
