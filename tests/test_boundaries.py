"""Protect dependency direction and tracked runtime build evidence."""
import ast
from pathlib import Path
import subprocess
import sys
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


def test_offline_built_wheel_contains_unaltered_guidance_without_runtime(tmp_path):
    build = subprocess.run(["uv", "build", "--wheel", "--offline", "--out-dir", str(tmp_path)],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        for relative in ("BASIC-INSTRUCTIONS.md", "features/guidance/tools-explain.md", "modeling_policy.json"):
            assert wheel.read("almond_mcp/" + relative) == (ROOT / "src/mcp" / relative).read_bytes()
        assert not any(name.startswith(("almond_mcp/runtime/", "almond_mcp/tests/")) for name in names)


def test_recorded_runtime_manifests_match_files_and_sources():
    check = subprocess.run([sys.executable, "-B", str(ROOT / "src/rhp/tools/verify_runtime.py")],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert check.returncode == 0, check.stdout + check.stderr
