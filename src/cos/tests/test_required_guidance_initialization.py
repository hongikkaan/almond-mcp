"""Both external client routes deliver one complete bundle in MCP initialize."""
import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

import external_host
import runtime
from almond_mcp import modeling_guidance
from almond_mcp.required_guidance import REQUIRED_DOCUMENTS, RequiredGuidanceError, load_required_guidance


@pytest.fixture
def required_sources(tmp_path, monkeypatch):
    sources = {"BASIC-INSTRUCTIONS.md": modeling_guidance.BASIC_GUIDE,
               "design_judgment.md": tmp_path / "design_judgment.md"}
    sources["design_judgment.md"].write_text("design_judgment.md: 첫 줄\n" + "설계 기준 " * 20_000
                                           + "\ndesign_judgment.md: 마지막 줄\n", encoding="utf-8")
    monkeypatch.setattr(modeling_guidance, "REQUIRED_GUIDE_SOURCES", sources)
    monkeypatch.delenv("ALMOND_GUIDANCE_FORMAT", raising=False)
    modeling_guidance._snapshot.cache_clear()
    yield sources
    modeling_guidance._snapshot.cache_clear()


@pytest.mark.parametrize("client", ["codex", "cos"])
@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_external_initialize_delivers_full_documents_once_before_connection(client, delivery, required_sources, monkeypatch, tmp_path):
    bundle = load_required_guidance(required_sources)
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)

    async def discover():
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            @asynccontextmanager
            async def transport():
                yield server_streams

            monkeypatch.setattr(external_host, "stdio_server", transport)
            task = asyncio.create_task(external_host.serve({"tools": []}, data=tmp_path / "unused", client=client))
            try:
                async with ClientSession(*client_streams) as session:
                    initialized = await session.initialize()
                    instructions = initialized.instructions
                    if delivery == "fields":
                        fields = json.loads(instructions)
                        assert set(fields) == {*REQUIRED_DOCUMENTS, "_metadata"}
                        assert fields["_metadata"]["required_guidance_version"] == bundle.version
                        assert fields["_metadata"]["guide_version"] == modeling_guidance.read_policy()["guide_version"]
                        assert fields["_metadata"]["introduction"].startswith(external_host.server_description(client))
                    else:
                        assert instructions.startswith(external_host.server_description(client) + "\n\n")
                        assert bundle.instructions() in instructions
                    for document in bundle.documents:
                        if delivery == "fields":
                            assert fields[document.name] == document.text
                            assert fields["_metadata"]["sha256"][document.name] == document.sha256
                            assert instructions.count(json.dumps(document.text, ensure_ascii=False)) == 1
                        else:
                            assert instructions.count(document.text) == 1
                        assert document.sha256 in instructions
                        assert document.text not in initialized.server_info.description
                    if delivery == "sequential":
                        assert instructions.index("BEGIN REQUIRED DOCUMENT BASIC-INSTRUCTIONS.md") < instructions.index("BEGIN REQUIRED DOCUMENT design_judgment.md")
                    assert initialized.server_info.name == external_host.CLIENT_SERVER_NAMES[client]
                    # Registration and initialize must not start a broker or connect to Rhino.
                    assert not (tmp_path / "unused").exists()
                    tools = await session.list_tools()
                    assert all("BEGIN REQUIRED DOCUMENT" not in tool.description for tool in tools.tools)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(discover())


def test_missing_document_stops_external_server_before_transport(required_sources, monkeypatch, tmp_path):
    required_sources["design_judgment.md"].unlink()

    def forbidden_transport():
        raise AssertionError("Missing mandatory content must stop before initialize transport.")

    monkeypatch.setattr(external_host, "stdio_server", forbidden_transport)
    with pytest.raises(RequiredGuidanceError, match="design_judgment.md"):
        asyncio.run(external_host.serve({"tools": []}, data=tmp_path / "unused"))
    assert not (tmp_path / "unused").exists()


def test_final_sources_participate_in_external_fingerprint(required_sources):
    paths = runtime.source_paths(runtime.ENGINE)
    for name, path in required_sources.items():
        assert paths["required_guidance/" + name] == path
    original = {key: runtime.digest(path) for key, path in paths.items()}
    required_sources["design_judgment.md"].write_text("changed content", encoding="utf-8")
    catalog = {"packages": {}, "sources": original}
    with pytest.raises(RuntimeError, match="design_judgment.md changed"):
        runtime.check_contract(catalog)
