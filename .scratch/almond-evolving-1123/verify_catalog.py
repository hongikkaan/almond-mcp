"""Compare the three checkout-local stdio catalogues using disposable bindings."""
import asyncio
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / path) for path in ("tests/integration", "src/cos", "src/mcp/runtime")]

from almond_mcp.modeling_guidance import startup_instructions
from build_catalog import generate
from external_host import exposed_tools
from jsonschema import Draft202012Validator
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from runtime import schema_identity
from test_stdio_contract import isolated_environment


async def collect(route, directory):
    if route == "worker":
        args = [str(ROOT / "tests/integration/bound_server_fixture.py")]
    else:
        args = ["-c", "import os; from pathlib import Path; from external_host import main; "
                      f"main(Path(os.environ['ALMOND_TEST_ROOT']), client={route!r})"]
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", *args],
                                   env=isolated_environment(directory))
    async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as client:
        assert startup_instructions() in (await client.initialize()).instructions
        listed = (await client.list_tools()).tools
    tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in listed}
    for item in tools.values():
        Draft202012Validator.check_schema(item["inputSchema"])
        Draft202012Validator.check_schema(item["outputSchema"])
    return tools


async def main():
    catalog = await generate()
    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf8"))
    document = (ROOT / "TOOL-DECLARATIONS-CURRENT.md").read_text(encoding="utf8")
    names = {name.replace("\\_", "_") for name in re.findall(r"^### \d+\. ([^\n]+)$", document, re.M)}
    for route, label in (("worker", "worker"), ("cos", "CoS"), ("codex", "beyond")):
        with tempfile.TemporaryDirectory() as folder:
            tools = await collect(route, Path(folder))
        if route == "worker":
            declarations = {item["name"]: item for item in catalog["tools"]}
            assert set(declarations) == set(tools) == set(baseline)
            for name, item in tools.items():
                assert schema_identity(item) == baseline[name] == schema_identity(declarations[name]), name
                assert item["description"] == declarations[name]["description"], name
        else:
            expected = exposed_tools(catalog, explicit_connections=route == "codex")
            assert tools == {item.name: item.model_dump(mode="json", by_alias=True, exclude_none=True)
                             for item in expected}
            assert set(tools) == names
            encoded = json.dumps([tools[key] for key in sorted(tools)], ensure_ascii=False,
                                 sort_keys=True, separators=(",", ":")).encode()
            assert f"{label} 선언 SHA-256: `{hashlib.sha256(encoded).hexdigest()}`" in document
        print(f"{label}: {len(tools)} tools verified")


if __name__ == "__main__":
    asyncio.run(main())
