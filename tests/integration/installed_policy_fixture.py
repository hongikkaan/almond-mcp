"""Exercise the standalone server from an installed wheel outside the checkout."""
import asyncio
import os
from pathlib import Path
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def serve(target):
    sys.path.insert(0, str(target))
    from almond_mcp import modeling_guidance, paths
    from almond_mcp.server import mcp

    assert modeling_guidance.PACKAGE == target / "almond_mcp"
    assert all(path.is_relative_to(target) for path in modeling_guidance.source_files())
    # Exercise the wheel's defaults with a disposable user profile and DB.
    for name in (*paths.LIBRARY_DIRS, paths.STATE_DB_ENV):
        os.environ.pop(name, None)
    for name in ("LOCALAPPDATA", "XDG_DATA_HOME", "HOME"):
        os.environ[name] = str(target.parent / "profile")
    mcp.run()


async def main(target):
    transport = StdioTransport(command=sys.executable,
                               args=["-I", "-B", __file__, str(target), "--serve"], env=dict(os.environ))
    async with Client(transport) as client:
        assert client.instructions is None
        tools = {tool.name: tool for tool in await client.list_tools()}
        policy_tool = "context_01-get_policy"
        choices = tools[policy_tool].input_schema["properties"]["policy"]["enum"]
        assert choices == ["", "basic", "metadata", "rhino_scripting", "rhinocode"]
        for name in choices:
            result = await client.call_tool(policy_tool, {"policy": name})
            value = result.structured_content
            assert value["selected_policy"] == (name or "basic")
            assert value["source_refs"] and all(ref["sha256"] for ref in value["source_refs"])
            if name == "metadata":
                assert "public_object_keys" in value["policy"] and "text" not in value
        rejected = await client.call_tool(policy_tool, {"policy": "drawing"}, raise_on_error=False)
        assert rejected.is_error


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve()
    if sys.argv[2:] == ["--serve"]:
        serve(target)
    else:
        asyncio.run(main(target))
