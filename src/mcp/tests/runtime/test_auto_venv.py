"""Windows shell integration using disposable projects and fresh Python environments."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows shell environment selection")
SOURCE = Path(__file__).resolve().parents[2] / "runtime/auto-venv"
WINDOWS_PS = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
GIT = shutil.which("git") or str(Path(os.environ["ProgramFiles"]) / "Git/cmd/git.exe")


def clean_environment():
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("AUTO_VENV_")
            and k.upper() not in ("VIRTUAL_ENV", "PYTHONHOME")}


def fake_env(root, relative=".venv"):
    env = root / relative
    (env / "Scripts").mkdir(parents=True)
    (env / "Scripts/python.exe").touch()
    (env / "pyvenv.cfg").write_text("home = test\n")
    return env


def git(root, *args):
    root.mkdir(parents=True, exist_ok=True)
    return subprocess.run([GIT, "-C", str(root), *args], check=True, capture_output=True,
                          timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)


def init_repo(root):
    git(root, "init", "--quiet")
    return root


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@pytest.fixture(params=["windows", "pwsh"])
def shell(request):
    if request.param == "windows":
        return WINDOWS_PS
    candidates = [Path(os.environ["ProgramFiles"]) / "PowerShell/7/pwsh.exe",
                  Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WindowsApps/pwsh.exe"]
    executable = next((p for p in candidates if p.is_file()), None)
    if executable is None:
        pytest.skip("Optional PowerShell 7 is not installed")
    return executable


def run_ps(shell, root, body, environment=None):
    script = root / "case.ps1"
    script.write_text("$ErrorActionPreference='Stop'\n" + body, encoding="utf-8-sig")
    result = subprocess.run([str(shell), "-NoProfile", "-STA", "-File", str(script)], cwd=root,
                            env=environment or clean_environment(), capture_output=True,
                            text=True, errors="replace", timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stdout + result.stderr


def test_powershell_switch_restore_and_preserve_prompt(shell, tmp_path):
    a, b = init_repo(tmp_path / "project A"), init_repo(tmp_path / "project B")
    first, second = fake_env(a), fake_env(b, "venv")
    nested = a / "src"; nested.mkdir()
    receipt = tmp_path / "result.json"
    env = dict(clean_environment(), PATH="C:\\base-tools", PYTHONHOME="C:\\original-home")
    run_ps(shell, tmp_path, f'''
function global:prompt {{ 'CUSTOM> ' }}
$basePath = $env:PATH
Set-Location {quote(nested)}
. {quote(SOURCE / 'auto-venv.ps1')}
$a = @{{venv=$env:VIRTUAL_ENV; path=$env:PATH; home=$env:PYTHONHOME; prompt=(prompt); root=$env:AUTO_VENV_REPO_ROOT; python=$env:AUTO_VENV_PYTHON}}
. {quote(SOURCE / 'auto-venv.ps1')}
Set-Location {quote(b)}
$prompt = prompt
$b = @{{venv=$env:VIRTUAL_ENV; path=$env:PATH; prompt=$prompt}}
Set-Location {quote(tmp_path)}
$prompt = prompt
$outside = @{{venv=$env:VIRTUAL_ENV; path=$env:PATH; home=$env:PYTHONHOME; prompt=$prompt}}
[IO.File]::WriteAllText({quote(receipt)}, (@{{a=$a;b=$b;outside=$outside;basePath=$basePath}} | ConvertTo-Json -Depth 4))
''', env)
    result = json.loads(receipt.read_text(encoding="utf-8-sig"))
    assert Path(result["a"]["venv"]) == first
    assert Path(result["a"]["root"]) == a
    assert Path(result["a"]["python"]) == first / "Scripts/python.exe"
    assert result["a"]["path"].startswith(str(first / "Scripts"))
    assert not result["a"]["home"] and "CUSTOM>" in result["a"]["prompt"]
    assert Path(result["b"]["venv"]) == second
    assert str(first / "Scripts") not in result["b"]["path"]
    assert result["outside"]["venv"] in (None, "")
    assert result["outside"]["path"] == result["basePath"]
    assert result["outside"]["home"] == env["PYTHONHOME"]
    assert result["outside"]["prompt"] == "CUSTOM> "


def test_powershell_manual_environment_and_git_boundary(shell, tmp_path):
    fake_env(tmp_path)
    project = tmp_path / "nested repo"; project.mkdir(); (project / ".git").touch()
    receipt = tmp_path / "result.json"
    run_ps(shell, tmp_path, f'''
Set-Location {quote(project)}
. {quote(SOURCE / 'auto-venv.ps1')}
$boundary = $env:VIRTUAL_ENV
$env:VIRTUAL_ENV = 'C:\\manual-environment'
$env:PATH = 'C:\\manual-tools'
Update-AutoVenv
[IO.File]::WriteAllText({quote(receipt)}, (@{{boundary=$boundary;manual=$env:VIRTUAL_ENV;path=$env:PATH}} | ConvertTo-Json))
''')
    result = json.loads(receipt.read_text(encoding="utf-8-sig"))
    assert result["boundary"] in (None, "")
    assert result["manual"] == "C:\\manual-environment" and result["path"] == "C:\\manual-tools"


def test_cmd_select_switch_restore_and_manual_environment(tmp_path):
    a, b = init_repo(tmp_path / "project A"), init_repo(tmp_path / "project B")
    first, second = fake_env(a), fake_env(b, "data/development/.venv")
    dump = tmp_path / "dump.ps1"
    dump.write_text("[IO.File]::WriteAllText($args[0], (@{venv=$env:VIRTUAL_ENV;path=$env:PATH;cwd=(Get-Location).Path;active=$env:AUTO_VENV_ACTIVE} | ConvertTo-Json))", encoding="utf-8-sig")
    driver = tmp_path / "case.cmd"
    chcp = Path(os.environ["SystemRoot"]) / "System32/chcp.com"
    lines = ["@echo off", f'"{chcp}" > "{tmp_path / "codepage-before.txt"}"']
    for name, location in (("a", a), ("b", b), ("outside", tmp_path)):
        lines += [f'cd /d "{location}"', f'call "{SOURCE / "auto-venv.cmd"}"',
                  f'"{WINDOWS_PS}" -NoProfile -File "{dump}" "{tmp_path / (name + ".json")}"']
    lines += ['set "VIRTUAL_ENV=C:\\manual-environment"', 'set "PATH=C:\\manual-tools"',
              f'cd /d "{a}"', f'call "{SOURCE / "auto-venv.cmd"}"',
              f'"{WINDOWS_PS}" -NoProfile -File "{dump}" "{tmp_path / "manual.json"}"',
              f'"{chcp}" > "{tmp_path / "codepage-after.txt"}"', 'exit /b 0']
    driver.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    env = dict(clean_environment(), PATH="C:\\base-tools")
    result = subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe"), "/d", "/c", str(driver)],
                            env=env, cwd=tmp_path, capture_output=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stdout + result.stderr
    states = {name: json.loads((tmp_path / (name + ".json")).read_text(encoding="utf-8-sig"))
              for name in ("a", "b", "outside", "manual")}
    assert Path(states["a"]["venv"]) == first and Path(states["b"]["venv"]) == second
    assert str(first / "Scripts") not in states["b"]["path"]
    assert states["outside"]["venv"] in (None, "") and states["outside"]["path"] == env["PATH"]
    assert states["manual"]["venv"] == "C:\\manual-environment" and states["manual"]["path"] == "C:\\manual-tools"
    assert (tmp_path / "codepage-before.txt").read_bytes() == (tmp_path / "codepage-after.txt").read_bytes()
    assert Path(states["a"]["cwd"]) == a and Path(states["b"]["cwd"]) == b


@pytest.mark.parametrize("development", [False, True])
def test_dashboard_uses_original_python_and_worktree_source(shell, tmp_path, development):
    foreign_project = init_repo(tmp_path / "foreign project")
    foreign = foreign_project / ".venv"
    main = init_repo(tmp_path / "original repository")
    git(main, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "--allow-empty", "-m", "fixture")
    checkout = tmp_path / "dashboard checkout"
    git(main, "worktree", "add", "--quiet", "--detach", str(checkout), "HEAD")
    original = main / ("data/development/.venv" if development else ".venv")
    for env in (foreign, original):
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(env)], check=True,
                       capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    fake_env(checkout)  # A worktree environment must not be used for this launcher.
    runtime = checkout / "src/mcp/runtime"
    (runtime / "dashboard").mkdir(parents=True)
    (runtime / "auto-venv").mkdir()
    shutil.copyfile(SOURCE.parent / "dashboard.ps1", runtime / "dashboard.ps1")
    shutil.copyfile(SOURCE / "repository.ps1", runtime / "auto-venv/repository.ps1")
    (runtime / "dashboard/__init__.py").touch()
    receipt = tmp_path / "python.json"
    (runtime / "dashboard/__main__.py").write_text(
        'import json,os,sys\nfrom pathlib import Path\n'
        'Path(os.environ["AUTO_VENV_TEST_RECEIPT"]).write_text(json.dumps('
        '{"prefix":sys.prefix,"executable":sys.executable,"source":__file__,"virtual_env":os.environ.get("VIRTUAL_ENV")}))\n', encoding="utf-8")
    env = dict(clean_environment(), AUTO_VENV_TEST_RECEIPT=str(receipt))
    run_ps(shell, tmp_path, f'''
Set-Location {quote(foreign_project)}
. {quote(SOURCE / 'auto-venv.ps1')}
if ($env:VIRTUAL_ENV -ne {quote(foreign)}) {{ throw 'Foreign environment was not selected' }}
& {quote(runtime / 'dashboard.ps1')} {'-Development' if development else ''} -NoBrowser
if ($env:VIRTUAL_ENV -ne {quote(foreign)}) {{ throw 'Dashboard changed the caller environment' }}
''', env)
    result = json.loads(receipt.read_text())
    assert Path(result["prefix"]) == original
    assert Path(result["executable"]) == original / "Scripts/python.exe"
    assert Path(result["source"]) == runtime / "dashboard/__main__.py"
    assert Path(result["virtual_env"]) == foreign


def test_powershell_priority_disable_and_strict_mode(shell, tmp_path):
    init_repo(tmp_path)
    fake_env(tmp_path, "venv")
    preferred = fake_env(tmp_path)
    receipt = tmp_path / "priority.json"
    run_ps(shell, tmp_path, f'''
Set-StrictMode -Version Latest
$basePath = $env:PATH
. {quote(SOURCE / 'auto-venv.ps1')}
$selected = $env:VIRTUAL_ENV
$env:AUTO_VENV_DISABLE = '1'
Update-AutoVenv
[IO.File]::WriteAllText({quote(receipt)}, (@{{selected=$selected;outside=$env:VIRTUAL_ENV;path=$env:PATH;basePath=$basePath}} | ConvertTo-Json))
''')
    result = json.loads(receipt.read_text(encoding="utf-8-sig"))
    assert Path(result["selected"]) == preferred
    assert result["outside"] in (None, "") and result["path"] == result["basePath"]


def test_installer_copies_verified_sources_and_keeps_backup(shell, tmp_path):
    destination = tmp_path / "installed copy"
    run_ps(shell, tmp_path, f'& {quote(SOURCE / "install.ps1")} -Destination {quote(destination)}')
    for name in ("repository.ps1", "auto-venv.cmd", "auto-venv.ps1"):
        assert (destination / name).read_bytes() == (SOURCE / name).read_bytes()
    (destination / "auto-venv.cmd").write_text("old local copy")
    run_ps(shell, tmp_path, f'& {quote(SOURCE / "install.ps1")} -Destination {quote(destination)}')
    backups = list((destination / "backups").glob("*/auto-venv.cmd"))
    assert len(backups) == 1 and backups[0].read_text() == "old local copy"
    assert (destination / "auto-venv.cmd").read_bytes() == (SOURCE / "auto-venv.cmd").read_bytes()
    run_ps(shell, tmp_path, f'& {quote(SOURCE / "install.ps1")} -Destination {quote(destination)}')
    assert list((destination / "backups").glob("*/auto-venv.cmd")) == backups


def test_cmd_selects_environment_in_unicode_directory(tmp_path):
    project = init_repo(tmp_path / "한글 & project")
    selected = fake_env(project)
    receipt = tmp_path / "unicode.json"
    dump = tmp_path / "dump.ps1"
    dump.write_text("[IO.File]::WriteAllText($args[0], (@{venv=$env:VIRTUAL_ENV} | ConvertTo-Json))", encoding="utf-8-sig")
    driver = tmp_path / "unicode.cmd"
    driver.write_bytes(b'@echo off\r\ncall "%AUTO_VENV_TEST_HELPER%"\r\n'
                       b'"%AUTO_VENV_TEST_SHELL%" -NoProfile -File "%AUTO_VENV_TEST_DUMP%" "%AUTO_VENV_TEST_RECEIPT%"\r\n'
                       b'exit /b %errorlevel%\r\n')
    env = dict(clean_environment(), PATH="C:\\base-tools", AUTO_VENV_TEST_HELPER=str(SOURCE / "auto-venv.cmd"),
               AUTO_VENV_TEST_SHELL=str(WINDOWS_PS), AUTO_VENV_TEST_DUMP=str(dump), AUTO_VENV_TEST_RECEIPT=str(receipt))
    result = subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe"), "/d", "/c", str(driver)],
                            env=env, cwd=project, capture_output=True, timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stdout + result.stderr
    assert Path(json.loads(receipt.read_text(encoding="utf-8-sig"))["venv"]) == selected


@pytest.mark.parametrize("separate_git_dir", [False, True])
@pytest.mark.parametrize("original_environment", [False, True])
def test_git_resolves_distant_worktree_root_for_both_shells(shell, tmp_path, separate_git_dir, original_environment):
    """A distant worktree uses the original checkout's environment, in both shells."""
    main = tmp_path / "원본 & repository"
    if separate_git_dir:
        git(main, "init", "--quiet", "--separate-git-dir", str(tmp_path / "git metadata"))
        git(main, "config", "extensions.worktreeConfig", "true")
        git(main, "config", "--worktree", "core.worktree", str(main))
    else:
        init_repo(main)
    original = fake_env(main) if original_environment else None
    git(main, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--quiet", "--allow-empty", "-m", "fixture")
    worktree = tmp_path / "unrelated location" / "한글 & checkout"
    git(main, "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD")
    fake_env(worktree, "data/development/.venv")
    nested = worktree / "src/module"
    fake_env(nested)  # A nested environment must not override the repository's choice.
    receipt = tmp_path / "git-root.json"
    run_ps(shell, tmp_path, f'''
Set-Location {quote(nested)}
. {quote(SOURCE / 'auto-venv.ps1')}
[IO.File]::WriteAllText({quote(receipt)}, (@{{root=$env:AUTO_VENV_REPO_ROOT;worktree=$env:AUTO_VENV_WORKTREE_ROOT;python=$env:AUTO_VENV_PYTHON;venv=$env:VIRTUAL_ENV}} | ConvertTo-Json))
''')
    expected = json.loads(receipt.read_text(encoding="utf-8-sig"))
    assert Path(expected["root"]) == main
    assert Path(expected["worktree"]) == worktree
    if original:
        assert Path(expected["venv"]) == original
        assert Path(expected["python"]) == original / "Scripts/python.exe"
    else:
        assert not expected["venv"] and not expected["python"]
    dump = tmp_path / "dump-root.ps1"
    dump.write_text('[IO.File]::WriteAllText($args[0], (@{root=$env:AUTO_VENV_REPO_ROOT;worktree=$env:AUTO_VENV_WORKTREE_ROOT;'
                    'python=$env:AUTO_VENV_PYTHON;venv=$env:VIRTUAL_ENV} | ConvertTo-Json))', encoding="utf-8-sig")
    driver = tmp_path / "git-root.cmd"
    driver.write_bytes(b'@echo off\r\ncall "%AUTO_VENV_TEST_HELPER%"\r\n'
                       b'"%AUTO_VENV_TEST_SHELL%" -NoProfile -File "%AUTO_VENV_TEST_DUMP%" "%AUTO_VENV_TEST_RECEIPT%"\r\n'
                       b'exit /b %errorlevel%\r\n')
    env = dict(clean_environment(), PATH="C:\\base-tools", AUTO_VENV_TEST_HELPER=str(SOURCE / "auto-venv.cmd"),
               AUTO_VENV_TEST_SHELL=str(WINDOWS_PS), AUTO_VENV_TEST_DUMP=str(dump), AUTO_VENV_TEST_RECEIPT=str(receipt))
    result = subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe"), "/d", "/c", str(driver)],
                            env=env, cwd=nested, capture_output=True, timeout=20,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0 and not result.stderr, result.stdout + result.stderr
    assert json.loads(receipt.read_text(encoding="utf-8-sig")) == expected


def test_non_git_directory_does_not_select_environment(shell, tmp_path):
    fake_env(tmp_path)
    run_ps(shell, tmp_path, f'''
. {quote(SOURCE / 'auto-venv.ps1')}
if ($env:VIRTUAL_ENV -or $env:AUTO_VENV_REPO_ROOT -or $env:AUTO_VENV_PYTHON) {{ throw 'Selected outside Git' }}
''')
