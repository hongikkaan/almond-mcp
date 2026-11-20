"""Managed errors and path projection preserve the tool's public transport."""
import asyncio
import json
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware
from fastmcp.tools import ToolResult
from jsonschema import validate
from mcp.types import ImageContent, TextContent
import pytest

from almond_mcp.output_contracts import public_output_schema
from shared_store import ProjectRuntime, public_result
from almond_mcp.tool_guidance import guide_result


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("is_error", [False, True])
def test_guidance_and_paths_preserve_transport_metadata_and_evidence(tmp_path, monkeypatch, wrapped, is_error):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    payload = {"status": "error" if is_error else "success", "complete": False,
               "mutation_applied": None, "requires_reconciliation": True,
               "object_ids": ["created-object"], "proof": {"receipt": "native-receipt"},
               "image_file": {"status": "saved", "path": str(tmp_path / "capture.png"), "lifetime": "plan"}}
    text = TextContent(type="text", text=json.dumps(payload),
                       annotations={"audience": ["assistant"], "priority": 0.8},
                       _meta={"source": "native"})
    image = ImageContent(type="image", data="AA==", mimeType="image/png", _meta={"view": "perspective"})
    source = ToolResult(content=[text, image],
                        structured_content={"result": json.dumps(payload)} if wrapped else payload,
                        is_error=is_error, meta={"request": "request-original"})
    guided = guide_result("capture_rhino_inspection", source, {})
    result = public_result(guided, "capture_rhino_inspection")
    assert result.meta == source.meta
    assert result.is_error is is_error
    assert result.content[0].annotations == text.annotations
    assert result.content[0].meta == text.meta
    assert result.content[1] == image
    body = json.loads(result.content[0].text)
    structured = json.loads(result.structured_content["result"]) if wrapped else result.structured_content
    assert body == structured
    assert body["image_file"]["path"] == "capture.png"
    for field in ("complete", "mutation_applied", "requires_reconciliation", "object_ids", "proof"):
        assert body[field] == payload[field]
    assert json.loads(source.content[0].text) == payload


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
    internal_name = "export_structural_report" if wrapped else "generate_asset_drawing_views"
    name = "analysis_04-export_structural_report" if wrapped else "asset_02-generate_drawing_views"
    schema = public_output_schema(internal_name, wrapped=wrapped)
    runtime = object.__new__(ProjectRuntime)
    runtime.locations = {"project_dir": str(tmp_path), "call_root": str(tmp_path / "calls")}
    runtime.workspace = SimpleNamespace(current=lambda: {"artifact_dir": ""}, artifact_path=lambda selection=None: tmp_path)

    class Preflight(Middleware):
        async def on_call_tool(self, context, call_next):
            return await runtime._owned_call(context, call_next, internal_name, False, "")

    server = FastMCP("preflight-contract")
    def export_structural_report(path: str):
        raise AssertionError("Rejected path must not dispatch")
    def generate_asset_drawing_views(source_glb: str):
        raise AssertionError("Rejected path must not dispatch")
    server.tool(name=name, output_schema=schema)(export_structural_report if wrapped else generate_asset_drawing_views)
    server.add_middleware(Preflight())

    async def run():
        async with Client(server) as client:
            listed = {tool.name: tool for tool in await client.list_tools()}
            response = await client.call_tool(name,
                {"path" if wrapped else "source_glb": "../outside.json"}, raise_on_error=False)
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
