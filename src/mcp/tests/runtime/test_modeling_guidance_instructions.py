"""RhinoTerminal initialize delivers both required documents in full."""
import asyncio
import json

from fastmcp import Client, FastMCP
import pytest

import mcp_server
from almond_mcp import modeling_guidance
from almond_mcp.required_guidance import REQUIRED_DOCUMENTS, RequiredGuidanceError, load_required_guidance


@pytest.fixture
def required_sources(tmp_path, monkeypatch):
    sources = {name: tmp_path / name for name in REQUIRED_DOCUMENTS}
    for name, path in sources.items():
        path.write_text(f"{name}: 처음\n" + "검수 근거 " * 20_000 + f"\n{name}: 끝\n", encoding="utf-8")
    monkeypatch.setattr(modeling_guidance, "REQUIRED_GUIDE_SOURCES", sources)
    description, _ = modeling_guidance.POLICIES["basic"]
    monkeypatch.setattr(modeling_guidance, "POLICIES", {**modeling_guidance.POLICIES,
                        "basic": (description, sources["BASIC-INSTRUCTIONS.md"])})
    monkeypatch.delenv("ALMOND_GUIDANCE_FORMAT", raising=False)
    modeling_guidance._snapshot.cache_clear()
    yield sources
    modeling_guidance._snapshot.cache_clear()


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_rhino_session_instructions_are_discoverable_without_a_server_description(required_sources, delivery, monkeypatch):
    bundle = load_required_guidance(required_sources)
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)

    async def discover():
        server = FastMCP("Almond")
        assert server.instructions is None

        mcp_server.configure_rhino_session_instructions(server)

        async with Client(server) as client:
            assert client.instructions == modeling_guidance.startup_instructions()
            if delivery == "fields":
                fields = json.loads(client.instructions)
                assert set(fields) == {*REQUIRED_DOCUMENTS, "_metadata"}
                assert fields["_metadata"]["required_guidance_version"] == bundle.version
                assert fields["_metadata"]["guide_version"] == modeling_guidance.read_policy()["guide_version"]
                for document in bundle.documents:
                    assert fields[document.name] == document.text
                    assert fields["_metadata"]["sha256"][document.name] == document.sha256
                    assert client.instructions.count(json.dumps(document.text, ensure_ascii=False)) == 1
            else:
                assert "guide_version=" in client.instructions
                assert bundle.instructions() in client.instructions
                for document in bundle.documents:
                    assert client.instructions.count(document.text) == 1
                assert client.instructions.index("BEGIN REQUIRED DOCUMENT BASIC-INSTRUCTIONS.md") < client.instructions.index("BEGIN REQUIRED DOCUMENT design_judgment.md")
            assert client.server_info.description is None

    asyncio.run(discover())


def test_missing_document_stops_bound_server_configuration(required_sources):
    required_sources["design_judgment.md"].unlink()
    server = FastMCP("Almond")
    with pytest.raises(RequiredGuidanceError, match="design_judgment.md"):
        mcp_server.configure_rhino_session_instructions(server)
    assert server.instructions is None


def test_existing_server_retains_its_bundle_and_new_server_gets_updated_content(required_sources):
    first = FastMCP("Almond")
    mcp_server.configure_rhino_session_instructions(first)
    original = first.instructions
    required_sources["design_judgment.md"].write_text("revised document\n", encoding="utf-8")
    second = FastMCP("Almond")
    mcp_server.configure_rhino_session_instructions(second)
    assert first.instructions == original
    assert second.instructions != original
    assert "revised document\n" in second.instructions
