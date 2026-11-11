"""Compile the production resolver with a controlled runtime-location fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_native_solver_uses_only_the_registered_checkout(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    project = Path(__file__).with_name("native_solver_host") / "NativeSolverHost.csproj"
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    assert built.returncode == 0, built.stdout + built.stderr
    host = project.parent / "bin/Release/net8.0/NativeSolverHost.dll"
    result = subprocess.run([sdk, str(host), str(tmp_path), sys.executable],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "passed"
    assert len(report["tests"]) == 7
    assert report["actualRhinoLoaded"] is False
