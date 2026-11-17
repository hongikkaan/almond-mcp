"""Exercise startup without touching a user's installation or running Rhino."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

from fastmcp import Client

from almond_mcp import paths
from almond_mcp.startup import create_server


def test_import_has_no_store_or_library_side_effects(tmp_path):
    source = Path(__file__).resolve().parents[1]
    state = tmp_path / "db" / "scene.sqlite3"
    local = tmp_path / "appdata"
    env = {name: value for name, value in os.environ.items()
           if name not in paths.LIBRARY_DIRS}
    env.update(PYTHONPATH=str(source), LOCALAPPDATA=str(local), XDG_DATA_HOME=str(local),
               RHINO_MCP_STATE_DB=str(state))
    program = """
import sys
from almond_mcp import paths
def fail(*args):
    raise AssertionError("Startup paths are resolved only when serving")
paths.resolve_dir = paths.resolve_state_db = fail
from almond_mcp.server import mcp
from almond_mcp.startup import create_server
assert callable(mcp.run) and callable(create_server)
assert "almond_mcp.retrieval_store" not in sys.modules
assert "almond_mcp.features.grasshopper.ghx_parser" not in sys.modules
"""
    result = subprocess.run([sys.executable, "-B", "-c", program], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert not state.parent.exists()
    assert not local.exists()


def test_applications_use_their_own_transport_and_store(tmp_path, monkeypatch):
    def unexpected_lookup(*args):
        raise AssertionError("Explicitly configured applications cannot resolve environment paths.")

    monkeypatch.setattr(paths, "resolve_dir", unexpected_lookup)
    monkeypatch.setattr(paths, "resolve_state_db", unexpected_lookup)
    events = []

    def application(label, objects):
        def send(payload, timeout=60.0):
            request = json.loads(payload)
            events.append((label, request["type"]))
            return json.dumps({"status": "success", "capabilities": {"context_sections": 2},
                               "document": {"object_count": objects}})

        folder = tmp_path / label
        library_dirs = {variable: str(folder / name) for variable, name in paths.LIBRARY_DIRS.items()}
        return create_server(state_db=folder / "state.sqlite3", library_dirs=library_dirs, send=send)

    first = application("first", 3)
    second = application("second", 9)

    async def tool(client, name, arguments):
        response = await client.call_tool(name, arguments)
        assert not response.is_error
        return json.loads(response.structured_content["result"])

    async def exercise():
        async with Client(first.mcp) as one, Client(second.mcp) as two:
            created = await tool(one, "scene_02-create", {"name": "Only in the first project"})
            assert created["status"] == "success"
            assert (await tool(one, "scene_07-list", {}))["total"] == 1
            assert (await tool(two, "scene_07-list", {}))["total"] == 0
            one_context = await tool(one, "inspect_03-get_document_context", {"sections": ["document"]})
            two_context = await tool(two, "inspect_03-get_document_context", {"sections": ["document"]})
            assert one_context["document"]["object_count"] == 3
            assert two_context["document"]["object_count"] == 9

    asyncio.run(exercise())
    assert events == [("first", "get_rhino_context"), ("second", "get_rhino_context")]
