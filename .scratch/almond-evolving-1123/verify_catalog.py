"""Verify the checkout-local beyond and RhinoTerminal stdio catalogs."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / path) for path in ("tests/integration", "src/beyond", "src/mcp/runtime")]

from almond_mcp.modeling_guidance import startup_instructions
from build_catalog import generate
from external_host import exposed_tools
from jsonschema import Draft202012Validator
from render_tool_declarations import read_catalog, render_catalogs, stdio_parameters
from runtime import schema_identity


async def main():
    catalog = await generate()
    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf8"))
    document = (ROOT / "TOOL-DECLARATIONS-CURRENT.md").read_text(encoding="utf8")
    scratch = ROOT / "data/t"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix="catalog-") as folder:
        beyond_init, beyond = await read_catalog(stdio_parameters("beyond", Path(folder) / "beyond"))
        terminal_init, terminal = await read_catalog(stdio_parameters("terminal", Path(folder) / "terminal"))
    assert startup_instructions() in beyond_init.instructions
    assert terminal_init.instructions == startup_instructions()
    for tools in (beyond, terminal):
        for tool in tools.values():
            Draft202012Validator.check_schema(tool["inputSchema"])
            Draft202012Validator.check_schema(tool["outputSchema"])
    declarations = {item["name"]: item for item in catalog["tools"]}
    assert set(declarations) == set(terminal) == set(baseline)
    for name, tool in terminal.items():
        assert schema_identity(tool) == baseline[name] == schema_identity(declarations[name]), name
        assert tool["description"] == declarations[name]["description"], name
    assert beyond == {item.name: item.model_dump(mode="json", by_alias=True, exclude_none=True)
                      for item in exposed_tools(catalog)}
    assert document == render_catalogs(beyond, terminal)
    print(f"beyond: {len(beyond)} tools verified")
    print(f"RhinoTerminal: {len(terminal)} tools verified")


if __name__ == "__main__":
    asyncio.run(main())
