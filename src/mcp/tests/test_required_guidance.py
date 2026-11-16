"""The mandatory bundle is complete, stable and delivered without truncation."""
from pathlib import Path
import json

import pytest

from almond_mcp import required_guidance as guidance


@pytest.fixture
def sources(tmp_path):
    result = {name: tmp_path / name for name in guidance.REQUIRED_DOCUMENTS}
    for name, path in result.items():
        path.write_text(f"{name} fixture body\n", encoding="utf-8")
    return result


@pytest.mark.parametrize("delivery", ["sequential", "fields"])
def test_complete_unicode_documents_are_delivered_once_without_truncation(sources, delivery):
    text = "첫 줄\n" + "설계 근거 " * 40_000 + "\n마지막 줄\n"
    sources["BASIC-INSTRUCTIONS.md"].write_text(text, encoding="utf-8")
    bundle = guidance.load_required_guidance(sources)
    delivered = json.dumps(bundle.fields(), ensure_ascii=False) if delivery == "fields" else bundle.instructions()
    fields = json.loads(delivered) if delivery == "fields" else None
    for document in bundle.documents:
        if fields is not None:
            assert fields[document.name] == document.text
            assert delivered.count(json.dumps(document.text, ensure_ascii=False)) == 1
            assert fields["_metadata"]["sha256"][document.name] == document.sha256
        else:
            assert delivered.count(f"BEGIN REQUIRED DOCUMENT {document.name} ") == 1
            assert delivered.count(f"END REQUIRED DOCUMENT {document.name}") == 1
            assert delivered.count(document.text) == 1
        assert document.sha256 in delivered
    if fields is not None:
        assert set(fields) == {*guidance.REQUIRED_DOCUMENTS, "_metadata"}
        assert "첫 줄" in delivered
    assert bundle.version in delivered


def test_existing_snapshot_is_stable_but_new_server_observes_updated_version(sources):
    first = guidance.load_required_guidance(sources)
    original = first.instructions()
    sources["design_judgment.md"].write_text("updated final line\n", encoding="utf-8")
    second = guidance.load_required_guidance(sources)
    assert second.version != first.version
    assert first.instructions() == original
    assert "updated final line\n" in second.instructions()
    assert guidance.load_required_guidance(sources) == second


def test_normalized_line_endings_and_bom_do_not_change_version(sources):
    first = guidance.load_required_guidance(sources)
    path = sources["BASIC-INSTRUCTIONS.md"]
    path.write_bytes(b"\xef\xbb\xbf" + first.documents[0].text.replace("\n", "\r\n").encode("utf-8"))
    assert guidance.load_required_guidance(sources) == first


@pytest.mark.parametrize("failure", ["missing", "empty", "invalid_utf8", "directory"])
def test_incomplete_bundle_fails_instead_of_delivering_one_document(sources, failure):
    path = sources["design_judgment.md"]
    if failure == "missing":
        path.unlink()
    elif failure == "empty":
        path.write_text(" \n\t", encoding="utf-8")
    elif failure == "invalid_utf8":
        path.write_bytes(b"\xff\xfe\xff")
    else:
        path.unlink()
        path.mkdir()
    with pytest.raises(guidance.RequiredGuidanceError, match="design_judgment.md"):
        guidance.load_required_guidance(sources)


def test_source_map_must_supply_both_exact_document_names(sources):
    for changed in ({}, {"BASIC-INSTRUCTIONS.md": sources["BASIC-INSTRUCTIONS.md"]},
                    {**sources, "extra.md": Path("not-read.md")}):
        with pytest.raises(guidance.RequiredGuidanceError, match="Configure exactly"):
            guidance.load_required_guidance(changed)


def test_same_source_cannot_impersonate_both_documents(sources):
    sources["design_judgment.md"] = sources["BASIC-INSTRUCTIONS.md"]
    with pytest.raises(guidance.RequiredGuidanceError, match="own source"):
        guidance.load_required_guidance(sources)


def test_change_during_collection_fails_as_a_whole(sources, monkeypatch):
    original = guidance._read
    reads = 0

    def changed(path):
        nonlocal reads
        reads += 1
        text = original(path)
        return text + "changed" if reads == 4 else text

    monkeypatch.setattr(guidance, "_read", changed)
    with pytest.raises(guidance.RequiredGuidanceError, match="changed while reading"):
        guidance.load_required_guidance(sources)
