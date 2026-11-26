"""Build the external catalog from MCP declarations and the source snapshot."""
from __future__ import annotations

import asyncio
from importlib.metadata import version
import json
from pathlib import Path
import sys
import tomllib

from almond_mcp import __version__
from almond_mcp.tool_declarations import declaration_sources, inspect_declarations, register_inert_tools

sys.dont_write_bytecode = True
from runtime import CATALOG, ENGINE, ROOT, digest, source_paths


def checked_versions() -> dict[str, str]:
    """Verify the editable package version and its locked protocol dependencies."""
    lock = tomllib.loads((ROOT.parents[1] / "uv.lock").read_text(encoding="utf-8"))
    result = {}
    for name in ("almond-mcp", "fastmcp", "mcp"):
        if name == "almond-mcp":
            expected, source = {__version__}, "the current checkout"
        else:
            expected = {p["version"] for p in lock["package"] if p["name"] == name}
            source = "uv.lock"
        actual = version(name)
        if expected != {actual}:
            raise RuntimeError(f"Runtime expects {name} version {sorted(expected)} from {source}; installed: {actual}.")
        result[name] = actual
    return result


def _source_digests(paths: dict[str, Path], captured: dict[Path, bytes] | None = None) -> dict[str, str]:
    captured = {} if captured is None else captured
    # Several inventory keys can refer to the same file.
    by_path = {path: digest(path, captured_bytes=captured.get(path)) for path in dict.fromkeys(paths.values())}
    return {name: by_path[path] for name, path in paths.items()}


async def generate(engine: Path = ENGINE) -> dict:
    packages = checked_versions()
    server_loaded = "almond_mcp.server" in sys.modules
    from fastmcp import FastMCP

    paths = source_paths(engine)
    tool_sources = declaration_sources(paths["server"].parent, document_entry=paths["entry"])
    # Use one snapshot so a transient edit cannot separate declarations from their hashes.
    captured = {path: path.read_bytes() for path in tool_sources}
    sources = _source_digests(paths, captured)
    declarations = inspect_declarations(tool_sources, captured_bytes=captured)
    mcp = FastMCP("Almond external schema build")
    register_inert_tools(mcp, declarations)
    tools = [tool.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
             for tool in await mcp.list_tools()]
    if not tools:
        raise RuntimeError("No common tools found in the current source.")
    if not server_loaded and "almond_mcp.server" in sys.modules:
        raise RuntimeError("Catalog generation must not import the Almond server.")
    if sources != _source_digests(source_paths(engine)):
        raise RuntimeError("Tool sources changed during schema discovery. Start a new client session.")
    return {
        "format": 1,
        "packages": packages,
        "sources": sources,
        "tools": sorted(tools, key=lambda t: t["name"]),
    }


if __name__ == "__main__":
    catalog = asyncio.run(generate())
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(catalog['tools'])} tool schemas without importing Almond.")
