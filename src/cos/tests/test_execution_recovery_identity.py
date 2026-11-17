"""Real durable recovery reader rejects identities from another invocation."""
import json
from pathlib import Path

import pytest

from execution_recovery import read_bound_execution
from project import connection_paths, write_json
import rhinocode


@pytest.fixture
def retained(tmp_path, monkeypatch):
    model = tmp_path / "fixture.3dm"
    model.write_bytes(b"offline fixture, not a Rhino model")
    token, operation, request = "a" * 32, "b" * 32, "c" * 32
    locations = connection_paths(model, "A", token, create=True)
    binding = dict(locations, schema="almond-project", storage_protocol=2,
                   pid=1, process_start_ticks="2", document_serial=3, token=token, label="A")
    write_json(locations["ready_path"], binding)
    journal = dict(schema="almond-rhinocode-execution", version=1, layout="compact-v1",
                   token=token, operation_id=operation, request_id=request, nonce="d" * 32,
                   source_hash="e" * 64, language="python", child=dict(pid=5, process_start_ticks="6"),
                   target=dict(pid=1, process_start_ticks="2", document_serial=3,
                               model_path=str(model), pipe_id="fixture"))
    directory = rhinocode.execution_directory(locations["call_root"], journal)
    directory.mkdir(parents=True)
    rhinocode._write_request(directory / "request.json", journal)
    write_json(Path(locations["session_dir"]) / "rhinocode.json", journal)
    monkeypatch.setattr(rhinocode, "_process_alive", lambda _: False)
    monkeypatch.setattr("storage_cleanup.process_identity_alive", lambda _: False)
    return binding, journal, directory


def test_durable_reader_checks_operation_before_public_projection(retained):
    binding, journal, directory = retained
    arguments = {"request_id": journal["request_id"]}
    pending = read_bound_execution(binding, arguments, operation_id=journal["operation_id"])
    assert pending["pending"] and pending["request_id"] == journal["request_id"]
    with pytest.raises(ValueError, match="current operation"):
        read_bound_execution(binding, arguments, operation_id="f" * 32)
    receipt = {key: journal[key] for key in rhinocode._IDENTITY}
    receipt.update(schema="almond-rhinocode-completion", version=1, layout="compact-v1",
                   status="success", mutation_state="completed", execution_complete=True)
    (directory / "complete.json").write_text(json.dumps(receipt), encoding="utf-8")
    completed = read_bound_execution(binding, arguments, operation_id=journal["operation_id"])
    assert completed["completed"] and completed["request_id"] == journal["request_id"]
    with pytest.raises(ValueError, match="current operation"):
        read_bound_execution(binding, arguments, operation_id="f" * 32)


@pytest.mark.parametrize("change", ["missing_manifest", "corrupt_manifest", "changed_document"])
def test_durable_reader_never_treats_an_in_memory_or_stale_id_as_evidence(retained, change):
    binding, journal, directory = retained
    manifest = directory / "request.json"
    if change == "missing_manifest":
        manifest.unlink()
    elif change == "corrupt_manifest":
        manifest.write_text("not json", encoding="utf-8")
    else:
        write_json(binding["ready_path"], {**binding, "document_serial": 4})
    with pytest.raises(ValueError):
        read_bound_execution(binding, {"request_id": journal["request_id"]}, operation_id=journal["operation_id"])
