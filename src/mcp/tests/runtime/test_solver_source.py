"""Provenance and cold solver protocol checks, without Rhino or a shared DB."""
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from almond_mcp.runtime import solve


ROOT = Path(__file__).resolve().parents[4]
LAUNCHER = ROOT / "src/mcp/runtime/solve.py"


class SolverSourceTests(unittest.TestCase):
    def test_current_editable_checkout(self):
        solve.check_source(ROOT)

    def test_same_version_wheel_is_rejected_before_import(self):
        dist = SimpleNamespace(metadata={"Name": "almond-mcp", "Version": "0.7.0rc2"},
                               read_text=lambda name: None)
        with patch.object(
                solve.importlib.metadata, "distributions", return_value=[dist]), patch.object(
                solve.importlib.util, "find_spec", side_effect=AssertionError("must reject first")):
            with self.assertRaisesRegex(RuntimeError, "editable installation"):
                solve.check_source(ROOT)

    def test_another_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            direct = json.dumps({"url": Path(folder).as_uri(), "dir_info": {"editable": True}})
            dist = SimpleNamespace(metadata={"Name": "almond-mcp"}, read_text=lambda name: direct)
            with patch.object(
                    solve.importlib.metadata, "distributions", return_value=[dist]):
                with self.assertRaisesRegex(RuntimeError, "registered checkout"):
                    solve.check_source(ROOT)

    def test_duplicate_distribution_is_rejected(self):
        dist = importlib.metadata.distribution("almond-mcp")
        alias = SimpleNamespace(metadata={"Name": "Almond.MCP"})
        with patch.object(solve.importlib.metadata, "distributions", return_value=[dist, alias]):
            with self.assertRaisesRegex(RuntimeError, "exactly one"):
                solve.check_source(ROOT)

    def test_foreign_import_origin_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = importlib.util.spec_from_file_location("almond_mcp", Path(folder) / "__init__.py")
            with patch.object(solve.importlib.util, "find_spec", return_value=spec):
                with self.assertRaisesRegex(RuntimeError, "outside"):
                    solve.check_source(ROOT)

    def call_launcher(self, folder, request, launcher=LAUNCHER):
        env = dict(os.environ)
        # All per-user solver/library reads stay in this disposable directory.
        for key in ("LOCALAPPDATA", "APPDATA", "XDG_DATA_HOME", "HOME", "USERPROFILE"):
            env[key] = str(folder)
        from almond_mcp import paths
        for key in paths.LIBRARY_DIRS:
            env[key] = str(folder / key)
        shadow = folder / "shadow"
        shadow.mkdir(exist_ok=True)
        marker = folder / "foreign-imported"
        (shadow / "almond_mcp.py").write_text(f"raise RuntimeError({str(marker)!r})\n")
        env["PYTHONPATH"] = str(shadow)
        completed = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(launcher)],
                                   input=json.dumps(request), text=True, capture_output=True,
                                   cwd=folder, env=env, timeout=30)
        self.assertNotIn(str(marker), completed.stdout + completed.stderr)
        return completed, json.loads(completed.stdout)

    def test_cold_ping_ignores_pythonpath(self):
        with tempfile.TemporaryDirectory() as folder:
            completed, result = self.call_launcher(Path(folder), {"protocol": 1, "ping": True})
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["protocol"], 1)
            self.assertIn("design_codes", result)

    def test_launcher_copied_to_another_checkout_refuses_to_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            launcher = root / "other/src/mcp/runtime/solve.py"
            launcher.parent.mkdir(parents=True)
            shutil.copyfile(LAUNCHER, launcher)
            completed, result = self.call_launcher(root, {"ping": True}, launcher)
            self.assertEqual(completed.returncode, 1)
            self.assertEqual(result["status"], "error")
            self.assertIn("registered checkout", result["message"])

    def test_cold_concrete_study_retains_indicative_verdict(self):
        request = {"protocol": 1, "model": {"status": "ok", "shells": 0,
            "members": [{"source_guids": ["beam"], "points": [[0, 0, 0], [3, 0, 0]],
                         "section": {"shape": "rect", "width": 0.3, "height": 0.6}}],
            "anchor_points": [[0, 0, 0]], "tolerance_m": 0.001,
            "max_member_span_m": 3, "max_span_m": 3},
            "settings": {"structure": "beam", "material": "Concrete", "load_kn": 0.1,
                         "self_weight": False, "stability": "off", "design_basis": "unfactored"}}
        with tempfile.TemporaryDirectory() as folder:
            completed, result = self.call_launcher(Path(folder), request)
            self.assertEqual(completed.returncode, 0, result)
            self.assertEqual(result["status"], "indicative", result)
            self.assertIsNone(result["validation"]["passed"])
            self.assertEqual(result["draw"]["verdict_label"], "INDICATIVE")

    def test_library_paths_preserve_daily_defaults_and_override(self):
        from almond_mcp import __version__, paths
        from almond_mcp.runtime.library_paths import configure_library_paths
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            data = Path(folder)
            os.environ["RHINO_MCP_DRAWING_ASSET_DIR"] = str(data / "explicit")
            with patch.object(paths, "user_data_dir", return_value=data):
                configure_library_paths()
            self.assertEqual(os.environ["RHINO_MCP_DRAWING_ASSET_DIR"], str(data / "explicit"))
            self.assertEqual(os.environ["RHINO_MCP_GENERATED_ASSET_DIR"],
                             str(data / "GeneratedAssetfiles/releases" / __version__))
            self.assertEqual(os.environ["RHINO_MCP_DRAFTING_DIR"],
                             str(data / "Draftingfiles/releases" / __version__))


if __name__ == "__main__":
    unittest.main()
