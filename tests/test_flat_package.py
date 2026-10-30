"""The flat checkout retains the installed package's import/CLI contracts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_editable_package_and_resources_from_another_directory(tmp_path):
    result = subprocess.run([sys.executable, "-B", "-c", """
import json
import almond_mcp
import mcp
from importlib.resources import files
from almond_mcp.modeling_guidance import read_guide
print(json.dumps({"source": almond_mcp.__file__,
                  "guide": read_guide()["text"],
                  "resource": files("almond_mcp").joinpath("modeling_policy.json").is_file(),
                  "protocol": mcp.__file__}))
"""], cwd=tmp_path, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    source = Path(__file__).resolve().parents[1] / "src/mcp/__init__.py"
    assert Path(payload["source"]).resolve() == source
    assert payload["resource"] and payload["guide"]
    assert Path(payload["protocol"]).resolve() != source


def test_module_entrypoint_from_another_directory(tmp_path):
    result = subprocess.run([sys.executable, "-B", "-m", "almond_mcp", "--help"],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    assert "serve" in result.stdout and "doctor" in result.stdout


def test_wheel_layout_without_runtime_initializes_and_lists_available_guides(tmp_path):
    package = tmp_path / "almond_mcp"
    source = Path(__file__).resolve().parents[1] / "src/mcp"
    shutil.copytree(source, package, ignore=shutil.ignore_patterns(
        "runtime", "tests", "release_validation", "__pycache__", "data"))
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", """
import asyncio, json
import almond_mcp
from fastmcp import Client
from almond_mcp.server import mcp
from almond_mcp.modeling_guidance import read_guide, startup_instructions
async def check():
    async with Client(mcp) as client:
        names = {tool.name for tool in await client.list_tools()}
        guide = read_guide()
        assert set(guide['tools']) == names
        for name in names:
            assert read_guide(tool=name)['text']
        assert 'get_modeling_guide()' in startup_instructions()
        print(json.dumps({'package': almond_mcp.__file__, 'tools': sorted(names)}))
asyncio.run(check())
"""], cwd=tmp_path, env=dict(os.environ, RHINO_MCP_STATE_DB=str(tmp_path / "state.sqlite3")),
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert Path(payload["package"]).parent == package
    assert "assign_material" in payload["tools"]
    assert "analyze_block_reculviely" in payload["tools"]
    assert "project_info" not in payload["tools"]
    assert not (package / "runtime").exists()
