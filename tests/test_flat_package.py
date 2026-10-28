"""The flat checkout retains the installed package's import/CLI contracts."""
import json
from pathlib import Path
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
                  "guide": read_guide("modeling")[0]["text"],
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
