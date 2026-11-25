"""Retained lookups use the journal version that matched the full request ID."""
import json
from pathlib import Path

import pytest

import rhinocode


def _write_manifest(root, journal):
    directory = rhinocode.execution_directory(root, journal)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "request.json"
    rhinocode._write_request(path, journal)
    return path


@pytest.fixture
def retained(tmp_path, monkeypatch):
    binding = dict(pid=1, process_start_ticks="2", document_serial=3,
                   model_path=str(tmp_path / "fixture.3dm"), token="a" * 32)
    target = {key: value for key, value in binding.items() if key != "token"}
    journal = dict(schema="almond-rhinocode-execution", version=1, layout="compact-v1",
                   token=binding["token"], operation_id="b" * 32, request_id="c" * 32,
                   nonce="d" * 32, language="python", source_hash="e" * 64,
                   target=dict(target, pipe_id="fixture"), child=dict(pid=5, process_start_ticks="6"))
    locations = dict(session_dir=str(tmp_path), project_dir=str(tmp_path), call_root=str(tmp_path))
    monkeypatch.setattr(rhinocode, "_process_alive", lambda _: False)
    return rhinocode.RhinocodeExecution(binding, locations), journal


@pytest.mark.parametrize("layout", ["compact-v1", None], ids=["compact", "legacy"])
def test_each_lookup_reads_the_manifest_once(retained, tmp_path, monkeypatch, layout):
    runner, journal = retained
    if layout is None:
        del journal["layout"]
    manifest = _write_manifest(tmp_path, journal)
    request_id = journal["request_id"]
    paths = []
    read_json = rhinocode.read_json

    def track_reads(path):
        paths.append(Path(path))
        return read_json(path)

    monkeypatch.setattr(rhinocode, "read_json", track_reads)
    assert rhinocode.find_request_manifest(tmp_path, request_id) == manifest
    assert runner.has_execution(request_id)
    waiting = runner.get_execution(request_id)
    assert waiting["request_id"] == request_id and waiting["completion_state"] == "awaiting_receipt"
    assert paths == [manifest] * 3

    # The next lookup still checks the independently published completion and CLI exit.
    receipt = {key: journal[key] for key in rhinocode._IDENTITY}
    if layout is not None:
        receipt["layout"] = layout
    receipt.update(schema="almond-rhinocode-completion", version=1, status="success",
                   mutation_state="completed", execution_complete=True)
    receipt_path = manifest.with_name("complete.json")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(rhinocode, "_process_alive", lambda _: True)
    assert runner.get_execution(request_id)["completion_state"] == "finishing"
    monkeypatch.setattr(rhinocode, "_process_alive", lambda _: False)
    completed = runner.get_execution(request_id)
    assert completed["status"] == "executed" and completed["completed"]
    assert paths[-2:] == [manifest, receipt_path]


def test_compact_lookup_keeps_the_exact_id_when_the_manifest_is_replaced(retained, tmp_path, monkeypatch):
    runner, journal = retained
    manifest = _write_manifest(tmp_path, journal)
    request_id = journal["request_id"]
    other_id = request_id[:12] + "f" * 20
    read_json = rhinocode.read_json

    def read_and_replace(path):
        value = read_json(path)
        if path == manifest and value["request_id"] == request_id:
            rhinocode._write_request(manifest, dict(journal, request_id=other_id))
        return value

    monkeypatch.setattr(rhinocode, "read_json", read_and_replace)
    assert runner.get_execution(request_id)["request_id"] == request_id
    assert not runner.has_execution(request_id)
    with pytest.raises(ValueError, match="No unique retained execution"):
        runner.get_execution(request_id)
    assert runner.get_execution(other_id)["request_id"] == other_id


def test_short_id_match_validates_layout_before_returning_a_path(retained, tmp_path):
    runner, journal = retained
    request_id = journal["request_id"]
    collision = _write_manifest(tmp_path, dict(journal, request_id=request_id[:12] + "f" * 20,
                                              operation_id="f" * 32))
    assert rhinocode.find_request_manifest(tmp_path, request_id) is None
    assert not runner.has_execution(request_id)

    legacy = {key: value for key, value in journal.items() if key != "layout"}
    legacy_path = _write_manifest(tmp_path, legacy)
    assert rhinocode.find_request_manifest(tmp_path, request_id) == legacy_path
    candidate = _write_manifest(tmp_path, journal)
    with pytest.raises(ValueError, match="Multiple retained executions"):
        runner.get_execution(request_id)

    candidate.unlink()
    rhinocode._write_request(collision, journal)
    with pytest.raises(ValueError, match="Retained execution path does not match its manifest"):
        rhinocode.find_request_manifest(tmp_path, request_id)
    collision.write_text("invalid JSON", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        runner.has_execution(request_id)
