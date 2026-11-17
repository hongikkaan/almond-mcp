"""Protect dependency direction and tracked runtime build evidence."""
import ast
from email.parser import BytesParser
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def test_mcp_never_imports_external_host_modules():
    modules = {p.stem for p in (ROOT / "src/cos").glob("*.py")}
    violations = []
    for path in (ROOT / "src/mcp").rglob("*.py"):
        if any(part in {"data", "__pycache__", ".venv"} for part in path.relative_to(ROOT / "src/mcp").parts):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            violations.extend(f"{path}:{node.lineno}: {name}" for name in names
                              if name.split(".")[0] in modules or name.startswith(("cos.", "src.cos")))
    assert not violations


def test_package_wheel_contract_includes_guidance_and_excludes_runtime():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        wheel = tomllib.load(stream)["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["sources"]["src/mcp"] == "almond_mcp"
    assert "src/mcp/runtime" in wheel["exclude"]
    assert "src/mcp/*-INSTRUCTIONS.md" in wheel["include"]
    assert "src/mcp/features/**" in wheel["include"]


def test_offline_built_distributions_contain_unaltered_guidance_without_runtime_in_wheel(tmp_path):
    build = subprocess.run(["uv", "build", "--offline", "--out-dir", str(tmp_path)],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = list(tmp_path.glob("*.whl"))
    sdists = list(tmp_path.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    package = ROOT / "src/mcp"
    policy_dir = "features/guidance/policies/"
    activity_files = {p.relative_to(package).as_posix() for p in (package / policy_dir).glob("*.md")}
    assert activity_files
    guidance_files = {
        "BASIC-INSTRUCTIONS.md", "design_judgment.md", "features/guidance/tools-explain.md",
        "modeling_policy.json", *activity_files,
    }
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        metadata = next(name for name in names if name.endswith(".dist-info/METADATA"))
        assert BytesParser().parsebytes(wheel.read(metadata))["Version"] == runpy.run_path(str(package / "__init__.py"))["__version__"]
        assert {name.removeprefix("almond_mcp/") for name in names
                if name.startswith("almond_mcp/" + policy_dir) and name.endswith(".md")} == activity_files
        for relative in guidance_files:
            assert wheel.read("almond_mcp/" + relative) == (package / relative).read_bytes()
        assert not any(name.startswith(("almond_mcp/runtime/", "almond_mcp/tests/")) for name in names)
        assert not any(name.startswith("almond_mcp/features/guidance/policy-validation/") for name in names)
    with tarfile.open(sdists[0]) as sdist:
        prefix = "src/mcp/"
        members = {member.name.partition("/")[2]: member for member in sdist.getmembers() if member.isfile()}
        assert {name.removeprefix(prefix) for name in members
                if name.startswith(prefix + policy_dir) and name.endswith(".md")} == activity_files
        for relative in guidance_files:
            assert sdist.extractfile(members[prefix + relative]).read() == (package / relative).read_bytes()
        assert prefix + "features/guidance/policy-validation/README.md" in members
    isolated = dict(os.environ, TMP=str(tmp_path), TEMP=str(tmp_path), TMPDIR=str(tmp_path))
    audit = subprocess.run(
        [sys.executable, "-B", str(ROOT / "src/mcp/release_validation/verify_release.py"), str(wheels[0])],
        env=isolated, capture_output=True, text=True, encoding="utf-8",
    )
    assert audit.returncode == 0, audit.stdout + audit.stderr


def test_bridge_project_and_yak_manifest_derive_the_same_release_version(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET") or shutil.which("dotnet")
    assert sdk, "Run the root test runner to select a .NET 8 SDK."
    for relative in (
        "src/mcp/almond_mcp.py", "src/rhp/tools/release_version.py",
        "src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj",
        "src/rhp/RhinoAlmondBridge/yak/manifest.yml",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)

    # Evaluate real MSBuild properties without building a Rhino plug-in.
    project = tmp_path / "src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj"
    staged = tmp_path / "manifest.yml"
    for python, semver in (("1.2.3rc4", "1.2.3-rc.4"), ("1.2.3", "1.2.3")):
        (tmp_path / "src/mcp/__init__.py").write_text(f'__version__ = "{python}"\n', encoding="utf-8")
        result = subprocess.run(
            [sdk, "msbuild", str(project), "-getProperty:Version"], cwd=ROOT,
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        assert result.stdout.strip() == semver
        subprocess.run(
            [sys.executable, "-B", str(tmp_path / "src/rhp/tools/release_version.py"), "--yak-manifest", str(staged)],
            check=True,
        )
        assert staged.read_text(encoding="utf-8").splitlines()[:2] == ["name: almondbridge", f"version: {semver}"]


def test_recorded_runtime_manifests_match_files_and_sources():
    check = subprocess.run([sys.executable, "-B", str(ROOT / "src/rhp/tools/verify_runtime.py")],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert check.returncode == 0, check.stdout + check.stderr
