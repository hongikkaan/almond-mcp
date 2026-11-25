"""Real durable recovery reader rejects identities from another invocation."""
import hashlib
import json
from pathlib import Path

import pytest

from execution_recovery import ExecutionRecoveryStore, read_bound_execution
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


def test_explicit_recovery_requires_a_matching_locator(retained, tmp_path):
    binding, journal, _ = retained
    stored_id = "a" * 32
    store = ExecutionRecoveryStore(tmp_path)
    store.remember(binding, connection_id=stored_id)
    restarted = ExecutionRecoveryStore(tmp_path)
    request = journal["request_id"]
    with pytest.raises(ValueError, match="No unique retained session"):
        restarted.find_binding(request, connection_id="b" * 32)
    assert restarted.find_binding(request, connection_id=stored_id) == binding


def test_default_recovery_uses_existing_receipts_without_creating_a_second_root(retained, tmp_path, monkeypatch):
    from session_close import SessionCloser
    import runtime

    binding, journal, _ = retained
    source = tmp_path / "src"
    default = source / "beyond" / "data"
    legacy = source / "cos" / "data"
    custom = tmp_path / "custom"
    monkeypatch.setattr(runtime, "ROOT", default.parent)
    assert ExecutionRecoveryStore(default).directory == default / "execution-locators"
    assert SessionCloser(default).root == default / "session-closes"
    assert not default.exists() and not legacy.exists()

    connection_id = "a" * 32
    previous_store = ExecutionRecoveryStore(legacy)
    previous_store.remember(binding, connection_id=connection_id)
    previous_close = SessionCloser(legacy)
    record = dict(schema="almond-session-close", version=1, request_id="close-fixture",
                  connection_id=connection_id, status="completed")
    previous_close.persist(record)

    store = ExecutionRecoveryStore(default)
    close = SessionCloser(default)
    assert store.find_binding(journal["request_id"], connection_id=connection_id) == binding
    assert close.load(record["request_id"]) == record
    store.remember(binding, connection_id=connection_id)
    updated = dict(record, request_id="another-close")
    close.persist(updated)
    assert previous_close.load(updated["request_id"]) == updated
    assert not default.exists()
    assert ExecutionRecoveryStore(custom).directory == custom / "execution-locators"
    assert SessionCloser(custom).root == custom / "session-closes"
    assert not custom.exists()


def test_rollback_cannot_hide_existing_recovery_records(tmp_path, monkeypatch):
    import runtime

    source = tmp_path / "src"
    data = source / "beyond/data"
    current = data / "session-closes"
    legacy = source / "cos/data/session-closes"
    monkeypatch.setattr(runtime, "ROOT", data.parent)
    current.mkdir(parents=True)
    legacy.mkdir(parents=True)
    (current / "current-request").mkdir()
    assert runtime.recovery_directory(data, "session-closes") == current
    (legacy / "older-request").mkdir()
    with pytest.raises(RuntimeError, match="Recovery records exist in both"):
        runtime.recovery_directory(data, "session-closes")


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
    result = {"status": "success", "checks_passed": 3}
    data = json.dumps(result).encode("utf-8")
    (directory / "result.json").write_bytes(data)
    (directory / "stdout.txt").write_text("validation: success", encoding="utf-8")
    receipt.update(result_available=True, result_bytes=len(data), result_sha256=hashlib.sha256(data).hexdigest())
    (directory / "complete.json").write_text(json.dumps(receipt), encoding="utf-8")
    completed = read_bound_execution(binding, arguments, operation_id=journal["operation_id"])
    assert completed["completed"] and completed["request_id"] == journal["request_id"]
    assert completed["status"] == "executed"
    assert completed["result"] == result
    detailed = read_bound_execution(binding, {**arguments, "include_diagnostics": True, "include_stdout": True})
    assert detailed["stdout"] == "validation: success"
    assert detailed["status"] == "executed" and detailed["native_status"] == "executed"
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
