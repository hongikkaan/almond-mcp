"""Standalone bootstrap check: the environment selects this checkout and safe paths."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src/mcp/runtime"))

import almond_mcp
from almond_mcp import paths, __version__
from library_paths import configure_library_paths


class EnvironmentSmoke(unittest.TestCase):
    def test_editable_package_is_this_checkout(self):
        self.assertEqual(Path(almond_mcp.__file__).resolve(), (REPO / "src/mcp/__init__.py").resolve())

    def test_explicit_override_and_user_defaults(self):
        home = Path("C:/fixture/Almond")
        key = "RHINO_MCP_DRAWING_ASSET_DIR"
        with patch.dict(os.environ, {key: "C:/fixture/custom"}, clear=True), patch.object(paths, "user_data_dir", return_value=home):
            configure_library_paths()
            for variable, name in paths.LIBRARY_DIRS.items():
                expected = Path("C:/fixture/custom") if variable == key else home / name
                if variable != key and name in {"GeneratedAssetfiles", "Draftingfiles"}:
                    expected /= "releases" / Path(__version__)
                self.assertEqual(Path(os.environ[variable]), expected)
            self.assertNotIn("almond_mcp.server", sys.modules)


if __name__ == "__main__":
    unittest.main()
