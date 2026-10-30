"""Real shipped helper caches and real worker defaults agree without running Rhino."""
from pathlib import Path
import shutil
import subprocess
import sys


def test_native_library_caches_match_the_worker_launcher():
    root = Path(__file__).resolve().parents[2]
    powershell = shutil.which("pwsh")
    assert powershell, "PowerShell 7 is required for the offline shipped-runtime contract."
    result = subprocess.run(
        [powershell, "-NoProfile", "-File",
         str(root / "src/rhp/RhinoAlmondBridge/tests/library_paths/verify.ps1"),
         "-RepositoryRoot", str(root), "-PythonExecutable", sys.executable],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("PASS ") == 3, result.stdout
