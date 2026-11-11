"""Exercise maintenance against disposable editable environments, never a model."""
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[3]


def run(args, cwd, *, check=True):
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    env["UV_OFFLINE"] = "1"
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=120)
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


def maintenance(repo, *args, check=True):
    return run(["pwsh", "-NoProfile", "-File", str(repo / "src/mcp/rebuild_environment.ps1"),
                *args], repo, check=check)


@pytest.fixture
def checkout(tmp_path, request):
    (tmp_path / "src/mcp").mkdir(parents=True)
    (tmp_path / "src/mcp/__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(ROOT / "src/mcp/rebuild_environment.ps1",
                    tmp_path / "src/mcp/rebuild_environment.ps1")
    version = importlib.metadata.version("packaging")
    (tmp_path / "pyproject.toml").write_text(f'''[project]
name = "almond-mcp"
version = "0.0.1"
requires-python = ">=3.12"
dependencies = ["packaging=={version}"]
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[tool.hatch.build.targets.wheel]
packages = ["src/mcp"]
sources = {{"src/mcp" = "almond_mcp"}}
dev-mode-dirs = ["src/mcp"]
''', encoding="utf-8")
    # Match this repository's editable import shim without importing its server.
    (tmp_path / "src/mcp/almond_mcp.py").write_text('''from pathlib import Path
__path__ = [str(Path(__file__).parent)]
__file__ = str(Path(__file__).with_name("__init__.py"))
''', encoding="utf-8")
    run(["uv", "lock", "--python", "3.12.12"], tmp_path)
    if getattr(request, "param", True):
        run(["uv", "sync", "--locked", "--python", "3.12.12", "--no-progress"], tmp_path)
    maintenance(tmp_path)
    return tmp_path


def add_leftover(repo, relative):
    site = repo / relative / "Lib/site-packages"
    info = site / "unused_fixture-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: unused-fixture\nVersion: 1.0\n", encoding="utf-8")
    (info / "RECORD").write_text("unused_fixture-1.0.dist-info/METADATA,,\nunused_fixture-1.0.dist-info/RECORD,,\n", encoding="utf-8")
    return info


def test_maintenance_cleans_both_existing_environments(checkout):
    leftovers = [add_leftover(checkout, relative) for relative in (".venv", "src/engine/.venv")]
    maintenance(checkout)
    assert not any(path.exists() for path in leftovers)


def test_verify_only_reports_drift_without_changing_packages_or_lock(checkout):
    leftover = add_leftover(checkout, ".venv")
    lock = (checkout / "uv.lock").read_bytes()
    result = maintenance(checkout, "-VerifyOnly", check=False)
    assert result.returncode != 0
    assert "Environment differs from uv.lock" in result.stdout + result.stderr
    assert leftover.is_dir()
    assert (checkout / "uv.lock").read_bytes() == lock


def test_stale_editable_requirements_are_detected_and_repaired(checkout):
    metadata = next((checkout / ".venv/Lib/site-packages").glob("almond_mcp-*.dist-info/METADATA"))
    with metadata.open("a", encoding="utf-8") as stream:
        stream.write("Requires-Dist: unused-fixture>=1\n")
    before = metadata.read_bytes()
    assert maintenance(checkout, "-VerifyOnly", check=False).returncode != 0
    assert metadata.read_bytes() == before
    maintenance(checkout)
    assert b"unused-fixture" not in metadata.read_bytes()
    maintenance(checkout, "-VerifyOnly")


@pytest.mark.parametrize("relative", [".venv", "src/engine/.venv"])
@pytest.mark.parametrize("executable", ["python.exe", "pythonw.exe"])
def test_busy_environment_blocks_all_repairs_but_allows_readonly_check(checkout, relative, executable):
    python = checkout / relative / "Scripts" / executable
    ready, stop = checkout / "ready", checkout / "stop"
    code = "from pathlib import Path\nimport sys,time\nPath(sys.argv[1]).touch()\nwhile not Path(sys.argv[2]).exists(): time.sleep(0.1)"
    process = subprocess.Popen([str(python), "-c", code, str(ready), str(stop)])
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists(), "Disposable Python did not start"
        maintenance(checkout, "-VerifyOnly")
        leftovers = [add_leftover(checkout, folder) for folder in (".venv", "src/engine/.venv")]
        result = maintenance(checkout, check=False)
        assert result.returncode != 0
        assert "Environment in use" in result.stdout + result.stderr
        assert all(path.is_dir() for path in leftovers)
    finally:
        stop.touch()  # cooperative fixture shutdown; no force termination
        process.wait(timeout=15)
        assert process.returncode == 0


def test_development_mode_leaves_daily_and_root_environments_untouched(checkout):
    leftovers = [add_leftover(checkout, relative) for relative in (".venv", "src/engine/.venv")]
    maintenance(checkout, "-Development")
    maintenance(checkout, "-Development", "-VerifyOnly")
    assert all(path.is_dir() for path in leftovers)
    assert (checkout / "data/development/.venv/Scripts/python.exe").is_file()


@pytest.mark.parametrize("checkout", [False], indirect=True)
def test_optional_root_environment_is_not_created(checkout):
    maintenance(checkout, "-VerifyOnly")
    assert not (checkout / ".venv").exists()


def test_compatibility_readonly_entry_does_not_configure_cos(checkout):
    wrapper = checkout / "src/engine/rebuild_environment.ps1"
    shutil.copyfile(ROOT / "src/engine/rebuild_environment.ps1", wrapper)
    (checkout / "src/cos").mkdir()
    (checkout / "src/cos/configure.ps1").write_text("throw 'Unexpected configure mutation'", encoding="utf-8")
    run(["pwsh", "-NoProfile", "-File", str(wrapper), "-VerifyOnly"], checkout)
