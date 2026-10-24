"""Editable source selection must not redirect existing user assets."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src" / "mcp" / "runtime"))

import almond_mcp
from almond_mcp import paths, __version__
from library_paths import configure_library_paths


class LibraryPathTests(unittest.TestCase):
    def test_appdata_defaults_and_explicit_override(self):
        root = Path("C:/fixture/Almond")
        variable = "RHINO_MCP_DRAWING_ASSET_DIR"
        with patch.dict(os.environ, {variable: "C:/custom/drawing"}, clear=True), \
                patch.object(paths, "user_data_dir", return_value=root):
            configure_library_paths()
            for key, name in paths.LIBRARY_DIRS.items():
                expected = root / name
                if name in {"GeneratedAssetfiles", "Draftingfiles"}:
                    expected = expected / "releases" / __version__
                if key == variable:
                    expected = Path("C:/custom/drawing")
                self.assertEqual(Path(paths.resolve_dir(key)), expected)
            self.assertNotIn("almond_mcp.server", sys.modules)

    def test_package_comes_from_this_checkout(self):
        expected = Path(__file__).resolve().parents[4] / "src/mcp/almond_mcp/__init__.py"
        self.assertEqual(Path(almond_mcp.__file__).resolve(), expected)


if __name__ == "__main__":
    unittest.main()
