"""Exercise PowerShell runtime tooling without compiling or registering a plugin."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Rhino runtime tooling is Windows-only")
@pytest.mark.parametrize("fixture", ["Test-RuntimeRegistration.ps1", "Test-RuntimeBuild.ps1"])
def test_runtime_powershell_fixture(tmp_path, fixture):
    script = Path(__file__).parent / "fixtures" / fixture
    shell = shutil.which("pwsh") or shutil.which("powershell")
    assert shell, "A Windows PowerShell executable is required to verify runtime tooling."
    result = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
         str(script), "-Scratch", str(tmp_path)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout
