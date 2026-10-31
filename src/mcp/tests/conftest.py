import sys
from pathlib import Path

# pytest sets up src/mcp/__init__.py under the directory name `mcp` before
# running tests. Load the external SDK first so that a small test selection
# cannot alias Almond as `mcp` and break later FastMCP imports.
import mcp.client  # noqa: F401

# Make the repo checkout importable as the almond_mcp package without an
# editable install (use this module's pytest.ini/run_tests.ps1).
_PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "src" / "mcp"
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))
