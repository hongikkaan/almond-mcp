"""Representations share full sources, hashes and the existing policy snapshot."""
import hashlib
import json
import subprocess
import sys

import pytest
from fastmcp import FastMCP

import mcp_server
from almond_mcp import modeling_guidance as guidance
from almond_mcp.required_guidance import REQUIRED_DOCUMENTS, RequiredGuidanceError, load_required_guidance


@pytest.fixture
def required_sources(tmp_path, monkeypatch):
    sources = {name: tmp_path / name for name in REQUIRED_DOCUMENTS}
    for name, path in sources.items():
        path.write_text(f"\n  {name}: isolated fixture\n\n", encoding="utf-8")
    description, _ = guidance.POLICIES["basic"]
    monkeypatch.setattr(guidance, "POLICIES", {**guidance.POLICIES,
                        "basic": (description, sources["BASIC-INSTRUCTIONS.md"])})
    monkeypatch.setattr(guidance, "REQUIRED_GUIDE_SOURCES", sources)
    monkeypatch.delenv("ALMOND_GUIDANCE_FORMAT", raising=False)
    guidance._snapshot.cache_clear()
    yield sources
    guidance._snapshot.cache_clear()


def test_default_environment_and_explicit_argument_selection(required_sources, monkeypatch):
    sequential = guidance.startup_instructions()
    fields = guidance.startup_instructions("fields")
    assert sequential == guidance.startup_instructions("sequential")
    assert "BEGIN REQUIRED DOCUMENT BASIC-INSTRUCTIONS.md" in sequential
    assert set(json.loads(fields)) == {*REQUIRED_DOCUMENTS, "_metadata"}
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", "fields")
    assert guidance.startup_instructions() == fields
    assert guidance.startup_instructions("sequential") == sequential
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", "invalid")
    with pytest.raises(ValueError, match="sequential or fields"):
        guidance.startup_instructions()
    assert guidance.startup_instructions("fields") == fields


@pytest.mark.parametrize("delivery", ["", "Fields", "unknown", True])
def test_invalid_explicit_selection_does_not_choose_a_format(required_sources, delivery):
    with pytest.raises(ValueError, match="sequential or fields"):
        guidance.startup_instructions(delivery)


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_policy_hash_matches_full_required_basic_and_strip_compatibility_is_preserved(required_sources, delivery):
    text = "\n  첫 줄\n" + "설계 근거 " * 40_000 + "\n마지막 줄  \n\n"
    path = required_sources["BASIC-INSTRUCTIONS.md"]
    path.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
    startup = guidance.startup_instructions(delivery)
    basic = guidance.read_policy()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert basic == guidance.read_policy("basic")
    assert basic["text"] == text.strip()
    assert basic["source_refs"] == [{"path": "src/mcp/BASIC-INSTRUCTIONS.md", "sha256": digest}]
    if delivery == "fields":
        fields = json.loads(startup)
        assert fields["BASIC-INSTRUCTIONS.md"] == text
        assert startup.count(json.dumps(text, ensure_ascii=False)) == 1
        assert fields["_metadata"]["sha256"]["BASIC-INSTRUCTIONS.md"] == digest
        assert fields["_metadata"]["guide_version"] == basic["guide_version"]
    else:
        assert startup.count(text) == 1
        assert f"BASIC-INSTRUCTIONS.md sha256={digest}" in startup
        assert f'guide_version={basic["guide_version"]}' in startup


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
@pytest.mark.parametrize("stage", ["cached_edit", "during_collection"])
def test_basic_hash_mismatch_stops_startup_instead_of_mixing_snapshots(required_sources, delivery, stage, monkeypatch):
    path = required_sources["BASIC-INSTRUCTIONS.md"]
    if stage == "cached_edit":
        original = guidance.read_policy()
        path.write_text("changed source\n", encoding="utf-8")
        assert guidance.read_policy() == original
    else:
        read = guidance._read_content

        def changed(source):
            value = read(source)
            return value + b"changed" if source == path else value

        monkeypatch.setattr(guidance, "_read_content", changed)
    with pytest.raises(RuntimeError, match="BASIC guidance changed after initialization; start a new session"):
        guidance.startup_instructions(delivery)


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_running_snapshot_is_stable_and_a_real_new_process_gets_updated_content(required_sources, delivery, monkeypatch):
    monkeypatch.setenv("ALMOND_GUIDANCE_FORMAT", delivery)
    server = FastMCP("Almond")
    mcp_server.configure_rhino_session_instructions(server)
    original_instructions = server.instructions
    original = guidance.read_policy()
    original_required_version = load_required_guidance(required_sources).version
    text = "\n  새 프로세스가 읽은 기본지침.\n\n"
    required_sources["BASIC-INSTRUCTIONS.md"].write_text(text, encoding="utf-8")
    assert guidance.read_policy() == original
    assert server.instructions == original_instructions
    with pytest.raises(RuntimeError, match="start a new session"):
        guidance.startup_instructions(delivery)
    code = '''
import json, sys
from pathlib import Path
from almond_mcp import modeling_guidance as guidance
from almond_mcp.required_guidance import load_required_guidance
sources = {name: Path(path) for name, path in json.loads(sys.argv[1]).items()}
guidance.REQUIRED_GUIDE_SOURCES = sources
description, _ = guidance.POLICIES["basic"]
guidance.POLICIES["basic"] = (description, sources["BASIC-INSTRUCTIONS.md"])
print(json.dumps({"instructions": guidance.startup_instructions(sys.argv[2]),
                  "basic": guidance.read_policy(),
                  "required_version": load_required_guidance(sources).version}, ensure_ascii=False))
'''
    fresh = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", code,
                            json.dumps({name: str(path) for name, path in required_sources.items()}), delivery],
                           check=True, capture_output=True, text=True, encoding="utf-8", timeout=30)
    updated = json.loads(fresh.stdout)
    assert updated["basic"]["text"] == text.strip()
    assert updated["basic"]["source_refs"] != original["source_refs"]
    assert updated["basic"]["guide_version"] != original["guide_version"]
    assert updated["required_version"] != original_required_version
    if delivery == "fields":
        fields = json.loads(updated["instructions"])
        assert fields["BASIC-INSTRUCTIONS.md"] == text
        assert fields["_metadata"]["guide_version"] == updated["basic"]["guide_version"]
        assert fields["_metadata"]["required_guidance_version"] == updated["required_version"]
    else:
        assert updated["instructions"].count(text) == 1
        assert f'guide_version={updated["basic"]["guide_version"]}' in updated["instructions"]
        assert f'Almond required guidance version={updated["required_version"]}' in updated["instructions"]
    assert guidance.read_policy() == original
    assert server.instructions == original_instructions


@pytest.mark.parametrize("name", REQUIRED_DOCUMENTS)
def test_missing_required_source_is_never_replaced_by_another_file(required_sources, name):
    required_sources[name].unlink()
    with pytest.raises(RequiredGuidanceError, match=name):
        guidance.startup_instructions()
    if name == "design_judgment.md":
        # The explicit existing BASIC policy remains independent of final
        # design-judgment content; initialization requires both documents.
        assert guidance.read_policy()["selected_policy"] == "basic"
