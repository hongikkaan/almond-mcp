"""Managed errors and path projection preserve the tool's public transport."""
import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware
from fastmcp.tools import ToolResult
from jsonschema import validate
from mcp.types import TextContent
import pytest

from almond_mcp.output_contracts import public_output_schema
from shared_store import ProjectRuntime, public_result


@pytest.mark.parametrize("envelope", ["text", "structured", "wrapped", "direct"])
def test_json_body_keeps_embedded_json_strings_byte_for_byte(tmp_path, monkeypatch, envelope):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    original = '{"path":"' + (tmp_path / "original.txt").as_posix() + '"}'
    value = {"result": {"literal": original, "items": [original], "file": str(tmp_path / "output.txt")}}
    source = value if envelope == "direct" else ToolResult(
        content=[TextContent(type="text", text=json.dumps(value))],
        structured_content=value if envelope == "structured" else {"result": json.dumps(value)} if envelope == "wrapped" else None)
    result = public_result(source, "execute_rhino_script")
    body = result if envelope == "direct" else json.loads(result.content[0].text)
    assert body["result"]["literal"] == original
    assert body["result"]["items"] == [original]
    assert body["result"]["file"] == "output.txt"
    if envelope == "structured":
        assert result.structured_content == body
    if envelope == "wrapped":
        assert json.loads(result.structured_content["result"]) == body


@pytest.mark.parametrize("wrapped", [False, True])
def test_preflight_error_matches_registered_output_envelope(tmp_path, monkeypatch, wrapped):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    internal_name = "import_asset_contract" if wrapped else "generate_asset_drawing_views"
    name = "exchange_03-import_asset_contract" if wrapped else "asset_02-generate_drawing_views"
    schema = public_output_schema(internal_name, wrapped=wrapped)
    runtime = object.__new__(ProjectRuntime)
    runtime.locations = {"project_dir": str(tmp_path), "call_root": str(tmp_path / "calls")}
    runtime.workspace = SimpleNamespace(current=lambda: {"artifact_dir": ""})

    class Preflight(Middleware):
        async def on_call_tool(self, context, call_next):
            return await runtime._owned_call(context, call_next, internal_name, False, "")

    server = FastMCP("preflight-contract")
    def import_asset_contract(contract_path: str):
        raise AssertionError("Rejected path must not dispatch")
    def generate_asset_drawing_views(source_glb: str):
        raise AssertionError("Rejected path must not dispatch")
    server.tool(name=name, output_schema=schema)(import_asset_contract if wrapped else generate_asset_drawing_views)
    server.add_middleware(Preflight())

    async def run():
        async with Client(server) as client:
            listed = {tool.name: tool for tool in await client.list_tools()}
            response = await client.call_tool(name,
                {"contract_path" if wrapped else "source_glb": "../outside.json"}, raise_on_error=False)
            assert response.is_error
            validate(response.structured_content, listed[name].output_schema)
            body = json.loads(response.content[0].text)
            assert body["error_code"] == "invalid_arguments"
            if wrapped:
                assert json.loads(response.structured_content["result"]) == body
            else:
                assert response.structured_content == body
            assert not (tmp_path / "calls").exists()
    asyncio.run(run())
