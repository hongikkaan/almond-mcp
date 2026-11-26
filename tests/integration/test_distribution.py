"""Build the distribution and start its installed console entry point."""
import asyncio
from hashlib import sha256
import json
import subprocess
import sys

from jsonschema import Draft202012Validator
from mcp.client.stdio import StdioServerParameters

from render_tool_declarations import ROOT, isolated_environment, open_stdio


def test_installed_wheel_policy(tmp_path):
    env = isolated_environment(tmp_path / "state")
    env.update(TEMP=str(tmp_path), TMP=str(tmp_path), TMPDIR=str(tmp_path))
    env.pop("PYTHONPATH")
    distributions = tmp_path / "dist"
    subprocess.run(["uv", "build", "--offline", "--out-dir", str(distributions)],
                   cwd=ROOT, env=env, check=True, timeout=120)
    wheel, = distributions.glob("*.whl")
    installed = tmp_path / "installed"
    subprocess.run(["uv", "pip", "install", "--offline", "--no-deps", "--target", str(installed), str(wheel)],
                   cwd=tmp_path, env=env, check=True, timeout=60)
    package = installed / "almond_mcp"
    scripts = package / "features/modeling/rhino3d-scripts"
    script_files = [scripts / "INTEGRATION.md", scripts / "SKILL.md", *sorted((scripts / "references").glob("*.md"))]
    policy_files = {
        "metadata": [package / "modeling_policy.json"],
        "rhino_scripting": script_files,
        "rhinocode": [package / "RHINOCODE-INSTRUCTIONS.md"],
    }

    # Resolve the wheel's exported entry point from its installed metadata.
    # -I and the isolated cwd prevent a checkout copy from shadowing it.
    launcher = """
from importlib.metadata import distributions
from pathlib import Path
import sys

installed = Path(sys.argv.pop(1))
sys.path.insert(0, str(installed))
from almond_mcp import __file__ as package
assert Path(package).is_relative_to(installed)
distribution, = distributions(path=[str(installed)])
entry, = (entry for entry in distribution.entry_points if entry.name == "almond-mcp")
raise SystemExit(entry.load()())
"""
    params = StdioServerParameters(command=sys.executable, args=["-I", "-B", "-X", "utf8", "-c", launcher,
                                                                str(installed), "serve"], cwd=tmp_path, env=env)

    async def inspect():
        async with open_stdio(params) as (client, initialized):
            assert initialized.instructions is None
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            name = "context_01-get_policy"
            validator = Draft202012Validator(tools[name].output_schema)
            result = await client.call_tool(name, {})
            assert not result.is_error, result.content
            guide = result.structured_content
            validator.validate(guide)
            assert guide["selected_policy"] == "basic"
            assert set(guide["tools"]) == tools.keys()
            assert "context_04-get_project_info" not in tools

            for policy, files in policy_files.items():
                result = await client.call_tool(name, {"policy": policy})
                assert not result.is_error, result.content
                value = result.structured_content
                validator.validate(value)
                assert value["selected_policy"] == policy
                assert value["guide_version"] == guide["guide_version"]
                expected = {f"src/mcp/{path.relative_to(package).as_posix()}": path.read_text(encoding="utf-8-sig")
                            for path in files}
                sources = value["scripting_skill"]["sources"] if policy == "rhino_scripting" else value["source_refs"]
                assert {ref["path"]: ref["sha256"] for ref in sources} == {
                    path: sha256(content.encode("utf-8")).hexdigest() for path, content in expected.items()
                }
                if policy == "metadata":
                    assert value["policy"] == json.loads(next(iter(expected.values())))
                    assert value["policy"]["public_object_keys"]
                elif policy == "rhino_scripting":
                    assert set(value) == {"selected_policy", "guide_version", "scripting_skill"}
                    assert {source["path"]: source["text"] for source in sources} == expected
                else:
                    assert value["text"] == next(iter(expected.values())).strip()
                    assert value["text"]

    asyncio.run(inspect())
