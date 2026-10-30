"""Exercise real SDK resolution and a nested offline build without installing SDKs."""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def dotnet():
    executable = os.environ.get("ALMOND_TEST_DOTNET") or shutil.which("dotnet")
    assert executable, "Run run_tests.ps1 with a .NET 8 SDK."
    return Path(executable)


@pytest.fixture(scope="module")
def resolve_sdk(dotnet):
    # This is the native resolver used by dotnet itself. No runtime is initialized.
    libraries = list((dotnet.parent / "host/fxr").glob("*/hostfxr.dll"))
    assert libraries, "The selected SDK host must include hostfxr.dll."
    host = ctypes.CDLL(str(libraries[-1]))
    callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_wchar_p)
    resolve = host.hostfxr_resolve_sdk2
    resolve.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int, callback_type]
    resolve.restype = ctypes.c_int

    def selected_version(installation, cwd):
        results = {}
        callback = callback_type(lambda key, value: results.__setitem__(key, value))
        code = resolve(str(installation), str(cwd), 0, callback)
        return code, Path(results[0]).name if 0 in results else None

    return selected_version


@pytest.mark.parametrize("versions, expected", [
    (["8.0.100", "8.0.426", "9.0.100", "10.0.100"], "8.0.426"),
    (["8.0.100", "9.0.100", "10.0.100"], "8.0.100"),
])
def test_global_json_selects_only_sdk8_with_newer_sdks_present(tmp_path, resolve_sdk, versions, expected):
    installation = tmp_path / "dotnet"
    for version in versions:
        directory = installation / "sdk" / version
        directory.mkdir(parents=True)
        # SDK enumeration checks this entry; the resolver does not load its contents.
        (directory / "dotnet.dll").touch()
    unpinned = tmp_path / "unpinned"
    unpinned.mkdir()
    assert resolve_sdk(installation, unpinned) == (0, "10.0.100")
    pinned = tmp_path / "pinned"
    nested = pinned / "subdirectory/project"
    nested.mkdir(parents=True)
    shutil.copyfile(ROOT / "global.json", pinned / "global.json")
    assert resolve_sdk(installation, nested) == (0, expected)


def test_nested_project_build_reports_the_actual_sdk8(tmp_path, dotnet):
    shutil.copyfile(ROOT / "global.json", tmp_path / "global.json")
    (tmp_path / "NuGet.Config").write_text(
        '<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    (project / "Fixture.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <Target Name="RecordSelectedSdk" BeforeTargets="CoreCompile">
    <WriteLinesToFile File="$(MSBuildProjectDirectory)/sdk-used.txt"
                      Lines="$(NETCoreSdkVersion)" Overwrite="true" />
  </Target>
</Project>''', encoding="utf-8")
    (project / "Probe.cs").write_text("public sealed class Probe {}", encoding="utf-8")
    cwd = tmp_path / "another/nested/directory"
    cwd.mkdir(parents=True)
    built = subprocess.run(
        [str(dotnet), "build", str(project / "Fixture.csproj"), "-c", "Release", "--nologo",
         "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
        cwd=cwd, capture_output=True, text=True, timeout=60,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    assert (project / "sdk-used.txt").read_text(encoding="utf-8-sig").strip().startswith("8.0.")
    assert (project / "bin/Release/net8.0/Fixture.dll").is_file()
