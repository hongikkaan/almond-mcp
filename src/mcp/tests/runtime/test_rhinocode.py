"""Disposable offline execution receipts, late results and wrapper failures."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import threading
import types

import pytest

import rhinocode as rc
from project import write_json


@pytest.fixture
def execution(tmp_path_factory, monkeypatch):
    # Three durable UUID levels also occur in production. Keep the test root
    # short enough for Windows Python 2/legacy atomic file APIs.
    root = tmp_path_factory.mktemp("r") / "p s"
    root.mkdir()
    model = root / "model.3dm"
    model.write_bytes(b"PATH FIXTURE, NOT A RHINO DOCUMENT")
    token, operation_id, request_id = "a" * 32, "b" * 32, "c" * 32
    session = root / ".almond" / ".sessions" / token
    session.mkdir(parents=True)
    calls = root / ".almond" / "tmp" / "python" / token
    directory = calls / operation_id / ("rc-" + request_id[:12])
    directory.mkdir(parents=True)
    binding = dict(schema="almond-project", token=token, pid=42, process_start_ticks="123",
                   document_serial=7, model_path=str(model), valid=True)
    locations = dict(project_dir=str(root), model_path=str(model), session_dir=str(session),
                     call_root=str(calls), temp=str(root / ".almond" / "tmp"),
                     storage=str(root / ".almond"))
    write_json(session / "ready.json", binding)
    journal = dict(schema="almond-rhinocode-execution", version=1, layout="compact-v1", token=token,
                   operation_id=operation_id, request_id=request_id, nonce="d" * 32,
                   source_hash=hashlib.sha256(b"source").hexdigest(), language="python",
                   target=dict(pid=42, process_start_ticks="123", document_serial=7,
                               model_path=str(model), pipe_id="rhinocode_remotepipe_42"),
                   child=dict(pid=99, process_start_ticks="456"))
    write_json(directory / "request.json", journal)
    write_json(session / "rhinocode.json", journal)
    monkeypatch.setattr(rc, "_process_alive", lambda record: False)
    return types.SimpleNamespace(root=root, model=model, session=session, calls=calls,
                                 directory=directory, binding=binding, locations=locations,
                                 journal=journal)


def completion(journal, **overrides):
    value = {key: journal[key] for key in rc._IDENTITY}
    if "layout" in journal:
        value["layout"] = journal["layout"]
    value.update(schema="almond-rhinocode-completion", version=1, execution_complete=True,
                 status="success", mutation_state="completed", user_code_started=True,
                 user_code_completed=True, result_available=False)
    value.update(overrides)
    return value


def publish_final(fixture, **overrides):
    value = completion(fixture.journal, **overrides)
    write_json(fixture.directory / "complete.json", value)
    return value


def inspect(fixture, alive=False):
    return rc.inspect_execution(fixture.journal, receipt_path=fixture.directory / "complete.json",
                                process_inspector=lambda record: alive)


def test_cli_exit_precedes_native_receipt_and_late_result_recovers(execution):
    before = inspect(execution)
    assert before["pending"] and before["uncertain"] and not before["completed"]
    assert before["completion_state"] == "awaiting_receipt"
    publish_final(execution)
    after = inspect(execution)
    assert after["completed"] and not after["pending"] and not after["uncertain"]


def test_final_does_not_release_a_running_or_inaccessible_child(execution):
    publish_final(execution)
    assert inspect(execution, True)["completion_state"] == "finishing"
    assert not inspect(execution, True)["completed"]
    assert not inspect(execution, None)["completed"]


@pytest.mark.parametrize("bad", [
    {"nonce": "e" * 32}, {"source_hash": "f" * 64}, {"request_id": "e" * 32},
    {"execution_complete": 1}, {"version": True}, {"status": "maybe"},
    {"target": {"pid": 42}}, {"layout": None}, {"layout": "unknown"},
])
def test_mismatched_or_non_boolean_completion_never_settles(execution, bad):
    publish_final(execution, **bad)
    assert inspect(execution)["uncertain"]
    assert not inspect(execution)["completed"]


def test_result_error_keeps_execution_completion(execution):
    publish_final(execution, result_error={"message": "too large"})
    result = inspect(execution)
    assert result["completed"] and result["status"] == "success"
    assert result["completion"]["result_error"]["message"] == "too large"


def test_missing_child_identity_cannot_be_inferred_from_a_final(execution):
    publish_final(execution)
    execution.journal["child"] = None
    assert not inspect(execution)["completed"]


def test_exact_native_result_is_readable_when_child_identity_is_unknown(execution):
    raw = b'{"completed_work":42}'
    (execution.directory / "result.json").write_bytes(raw)
    execution.journal["child"] = None
    write_json(execution.directory / "request.json", execution.journal)
    write_json(execution.session / "rhinocode.json", execution.journal)
    publish_final(execution, result_available=True, result_bytes=len(raw),
                  result_sha256=hashlib.sha256(raw).hexdigest())
    owner = rc.RhinocodeExecution(execution.binding, execution.locations)
    result = owner.get_execution()
    assert result["native_completed"] and result["native_status"] == "success"
    assert result["uncertain"] and result["completed"] is False
    assert result["result"] == {"completed_work": 42}
    assert result["result_file"] == str(execution.directory / "result.json")
    assert rc.inspect_session(execution.session)["completed"] is False


def test_proven_launch_failure_needs_no_native_receipt(execution):
    execution.journal.update(child=None, not_dispatched=True, dispatch_error="CreateProcess failed")
    result = inspect(execution)
    assert result["completed"] and result["mutation_state"] == "not_started"


def test_nondispatch_evidence_requires_explicit_null_child(execution):
    execution.journal.update(not_dispatched=True, dispatch_error="CreateProcess failed")
    execution.journal.pop("child")
    result = inspect(execution)
    assert result["uncertain"] and not result["completed"]


@pytest.mark.parametrize("ticks", ["0", "000456", "-1", "9223372036854775808", "٤٥٦"])
def test_noncanonical_child_start_identity_cannot_settle(execution, ticks):
    execution.journal["child"]["process_start_ticks"] = ticks
    publish_final(execution)
    result = inspect(execution)
    assert result["native_completed"] and result["uncertain"] and not result["completed"]


def test_session_fence_rejects_a_self_described_dead_wrong_target(execution):
    execution.journal["target"]["pid"] = 777
    write_json(execution.session / "rhinocode.json", execution.journal)
    called = []
    result = rc.inspect_session(execution.session, process_inspector=lambda rec: called.append(rec) or False)
    assert result["uncertain"] and not result["completed"] and called == []


def test_invalidated_binding_still_allows_exact_result_inspection(execution):
    execution.binding["valid"] = False
    write_json(execution.session / "ready.json", execution.binding)
    publish_final(execution)
    assert rc.inspect_session(execution.session, process_inspector=lambda rec: False)["completed"]


def test_ready_document_serial_string_matches_canonical_target(execution):
    binding = dict(execution.binding, document_serial="7")
    write_json(execution.session / "ready.json", binding)
    publish_final(execution)
    assert rc.inspect_session(execution.session, process_inspector=lambda rec: False)["completed"]
    with pytest.raises(ValueError, match="document runtime serial"):
        rc._matches_binding(execution.journal, dict(binding, document_serial=True))


def test_compact_prefix_cannot_alias_another_full_request(execution):
    other = execution.journal["request_id"][:12] + "d" * 20
    assert rc.find_request_manifest(execution.calls, other) is None
    owner = rc.RhinocodeExecution(execution.binding, execution.locations)
    assert not owner.has_execution(other)
    assert owner.has_execution(execution.journal["request_id"])


def test_legacy_layout_is_still_recoverable(execution):
    legacy = dict(execution.journal)
    legacy.pop("layout")
    root = execution.root / "legacy"
    directory = rc.execution_directory(root, legacy)
    directory.mkdir(parents=True)
    write_json(directory / "request.json", legacy)
    write_json(directory / "complete.json", completion(legacy))
    assert directory == root / legacy["operation_id"] / "rhinocode" / legacy["request_id"]
    assert rc.find_request_manifest(root, legacy["request_id"]) == directory / "request.json"
    owner = rc.RhinocodeExecution(execution.binding, dict(execution.locations, call_root=str(root)))
    assert owner.get_execution(legacy["request_id"])["completed"]


def test_receipt_size_limit_fails_closed(execution):
    (execution.directory / "complete.json").write_bytes(b"x" * (rc.RECEIPT_LIMIT + 1))
    assert not inspect(execution)["completed"]


def test_target_selection_checks_exact_process_and_document(execution, monkeypatch):
    checked = []
    monkeypatch.setattr(rc, "verify_process", lambda b: checked.append(b))
    good = dict(processId=42, pipeId="real-discovered-pipe", processVersion="8.34.26223",
                activeDoc={"location": str(execution.model)})
    assert rc.select_instance(execution.binding, [dict(good, processId=43), good])["pipeId"] == "real-discovered-pipe"
    assert checked == [execution.binding]
    for instances in ([], [good, good], [dict(good, activeDoc={"location": "wrong.3dm"})],
                      [dict(good, processVersion="8.10.0")]):
        with pytest.raises(RuntimeError):
            rc.select_instance(execution.binding, instances)
    monkeypatch.setattr(rc, "verify_process", lambda b: (_ for _ in ()).throw(RuntimeError("stale PID")))
    with pytest.raises(RuntimeError, match="stale PID"):
        rc.select_instance(execution.binding, [good])


def _fake_rhino(fixture, monkeypatch, *, fail_cleanup=False, run_script=None):
    class Views:
        RedrawEnabled = True
        def Redraw(self):
            self.redrawn = True
    class Doc:
        Path = str(fixture.model)
        RuntimeSerialNumber = 7
        CurrentUndoRecordSerialNumber = 0
        begins = 0
        def BeginUndoRecord(self, name):
            self.begins += 1
            self.CurrentUndoRecordSerialNumber = 9
            return 9
        def EndUndoRecord(self, serial):
            assert serial == 9
            if fail_cleanup:
                raise RuntimeError("cleanup fixture")
            self.CurrentUndoRecordSerialNumber = 0
            return True
    doc = Doc()
    doc.Views = Views()
    old_doc = object()
    context = types.SimpleNamespace(doc=old_doc)
    rhino = types.SimpleNamespace(RhinoDoc=types.SimpleNamespace(ActiveDoc=doc),
                                  RhinoApp=types.SimpleNamespace(IsOnMainThread=True, RunScript=run_script),
                                  Commands=types.SimpleNamespace(Command=types.SimpleNamespace(
                                      InScriptRunnerCommand=lambda: True)))
    start = types.SimpleNamespace(ToUniversalTime=lambda: types.SimpleNamespace(Ticks=123))
    system = types.SimpleNamespace(Diagnostics=types.SimpleNamespace(Process=types.SimpleNamespace(
        GetCurrentProcess=lambda: types.SimpleNamespace(Id=42, StartTime=start))))
    monkeypatch.setitem(sys.modules, "Rhino", rhino)
    monkeypatch.setitem(sys.modules, "System", system)
    monkeypatch.setitem(sys.modules, "scriptcontext", context)
    return doc, context, old_doc


def _run_python_wrapper(fixture, source, monkeypatch, **fake_options):
    doc, context, old_doc = _fake_rhino(fixture, monkeypatch, **fake_options)
    suffix, wrapper = rc.build_wrapper(fixture.journal, source, fixture.directory,
        project_root=str(fixture.root), artifact_dir=str(fixture.root / "artifacts"),
        executable=fixture.root / "rhinocode.exe")
    old_cwd, old_stdout, old_stderr = Path.cwd(), sys.stdout, sys.stderr
    exec(compile(wrapper, "generated_wrapper.py", "exec"), {})
    assert Path.cwd() == old_cwd
    assert sys.stdout is old_stdout and sys.stderr is old_stderr
    assert context.doc is old_doc
    assert doc.Views.RedrawEnabled is True
    return doc, json.loads((fixture.directory / "complete.json").read_text())


def test_wrapper_captures_print_and_persists_result_before_exact_final(execution, monkeypatch):
    doc, final = _run_python_wrapper(execution,
        "print('한글 output')\ndoc.marker = 'changed'\nresult = {'value': 27}", monkeypatch)
    assert doc.marker == "changed" and final["status"] == "success"
    assert final["undo"]["owned"] == 9 and final["undo"]["ended"]
    assert "한글 output" in (execution.directory / "stdout.txt").read_text(encoding="utf-8")
    assert json.loads((execution.directory / "result.json").read_text()) == {"value": 27}
    assert inspect(execution)["completed"]


@pytest.mark.parametrize("fail", [False, True])
def test_project_python_writes_in_plan_folder_and_restores_rhino_process(execution, monkeypatch, fail):
    doc, context, old_doc = _fake_rhino(execution, monkeypatch)
    directory = execution.root / "tmp" / "계획 O'Brien"
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", "previous-project")
    monkeypatch.delenv("ALMOND_ARTIFACT_DIR", raising=False)
    previous = dict(os.environ)
    cwd = Path.cwd()
    source = "import os\nimport scriptcontext\nassert doc is scriptcontext.doc\n" + (
        "with open('artifact.txt', 'w') as f: f.write(os.environ['ALMOND_MODEL_PATH'])\n"
        "result = {'cwd': os.getcwd(), 'artifact': os.environ['ALMOND_ARTIFACT_DIR']}\n")
    if fail:
        source += "raise RuntimeError('after file write')\n"
    _, wrapper = rc.build_wrapper(execution.journal, source, execution.directory,
        project_root=str(execution.root), artifact_dir=str(directory.relative_to(execution.root)),
        executable=execution.root / "rhinocode.exe", working_directory=str(directory))
    exec(compile(wrapper, "project_wrapper.py", "exec"), {})
    assert (directory / 'artifact.txt').read_text() == str(execution.model)
    assert dict(os.environ) == previous and Path.cwd() == cwd
    assert context.doc is old_doc and doc.Views.RedrawEnabled
    final = json.loads((execution.directory / 'complete.json').read_text())
    assert final['status'] == ('error' if fail else 'success')
    assert final['undo']['ended'] and inspect(execution)['completed']


def test_source_syntax_failure_is_known_without_starting_mutations(execution, monkeypatch):
    doc, final = _run_python_wrapper(execution, "if :", monkeypatch)
    assert doc.begins == 0 and not final["user_code_started"]
    assert final["error"]["stage"] == "compile" and final["mutation_state"] == "not_started"
    assert inspect(execution)["completed"]


def test_runtime_failure_reports_partial_change_and_retains_completion(execution, monkeypatch):
    doc, final = _run_python_wrapper(execution, "doc.marker = 8\nraise ValueError('user failure')", monkeypatch)
    assert doc.marker == 8 and final["mutation_state"] == "partial"
    assert final["error"]["message"] == "user failure"
    assert final["undo"]["ended"] and inspect(execution)["completed"]


@pytest.mark.parametrize("codepoint", [0x1F600, 0xD55C])
def test_non_ascii_failure_preserves_completion_with_bounded_diagnostics(execution, monkeypatch, codepoint):
    source = "doc.marker = 8\nraise RuntimeError(chr(%d) * 4000)" % codepoint
    doc, final = _run_python_wrapper(execution, source, monkeypatch)
    assert doc.marker == 8 and final["mutation_state"] == "partial"
    assert final["status"] == "error" and final["error"]["type"] == "RuntimeError"
    assert final["undo"]["ended"] and inspect(execution)["completed"]
    assert (execution.directory / "complete.json").stat().st_size <= rc.RECEIPT_LIMIT
    for key, maximum in (("message", 4000), ("traceback", 8000)):
        assert len(json.dumps(final["error"][key], ensure_ascii=True).encode("ascii")) <= maximum


def test_large_nested_diagnostics_keep_a_minimal_matching_completion(execution, monkeypatch):
    execution.journal["language"] = "csharp-script"
    (execution.root / "Newtonsoft.Json.dll").write_bytes(b"FIXTURE")
    def nested(serial, macro, echo):
        value = completion(execution.journal, status="error", mutation_state="partial",
            user_code_started=True, user_code_completed=False,
            error={"stage": "user_code", "type": "RuntimeError", "message": chr(0x1F600) * 9000},
            cleanup_errors=["cleanup incomplete"])
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        assert len(raw) < rc.RECEIPT_LIMIT
        (execution.directory / "child-complete.json").write_bytes(raw)
        return True
    _, final = _run_python_wrapper(execution, 'throw new Exception("error");',
                                   monkeypatch, run_script=nested)
    assert final["diagnostics_truncated"] is True
    assert final["status"] == "error" and final["mutation_state"] == "partial"
    assert final["error"]["stage"] == "user_code" and final["cleanup_errors"]
    assert final["undo"]["ended"] and inspect(execution)["completed"]
    assert (execution.directory / "complete.json").stat().st_size <= rc.RECEIPT_LIMIT
    recovered = rc.RhinocodeExecution(execution.binding, execution.locations).get_execution()
    assert recovered["completed"] and recovered["diagnostics_truncated"] is True


def test_exception_formatting_cannot_erase_execution_final(execution, monkeypatch):
    source = ("class BrokenMessage(Exception):\n"
              "    def __str__(self):\n"
              "        raise RuntimeError('formatting failed')\n"
              "raise BrokenMessage()\n")
    _, final = _run_python_wrapper(execution, source, monkeypatch)
    assert final["status"] == "error" and final["error"]["type"] == "BrokenMessage"
    assert "could not be converted" in final["error"]["message"]
    assert final["undo"]["ended"] and inspect(execution)["completed"]


def test_unserializable_result_and_cleanup_failure_do_not_erase_final(execution, monkeypatch):
    _, final = _run_python_wrapper(execution, "result = object()", monkeypatch, fail_cleanup=True)
    assert final["user_code_completed"] and final["result_error"]
    assert final["cleanup_errors"] and final["status"] == "error"
    assert inspect(execution)["completed"]


def test_result_limit_preserves_success_and_complete_receipt(execution, monkeypatch):
    monkeypatch.setattr(rc, "RESULT_LIMIT", 50)
    _, final = _run_python_wrapper(execution, "result = list(range(100))", monkeypatch)
    assert final["status"] == "success" and final["result_error"]
    assert not (execution.directory / "result.json").exists()
    assert inspect(execution)["completed"]


def test_csharp_compile_failure_has_outer_final_without_user_start(execution, monkeypatch):
    execution.journal["language"] = "csharp-script"
    (execution.root / "Newtonsoft.Json.dll").write_bytes(b"FIXTURE")
    calls = []
    def reject(serial, macro, echo):
        calls.append((serial, macro, echo))
        assert macro.endswith('child.cs"')
        return False
    doc, final = _run_python_wrapper(execution, "invalid C# source", monkeypatch, run_script=reject)
    assert len(calls) == 1 and calls[0][0] == 7 and calls[0][2] is False
    assert final["status"] == "error" and final["error"]["stage"] == "compile"
    assert final["user_code_started"] is False and final["mutation_state"] == "not_started"
    assert final["undo"]["ended"] and doc.Views.RedrawEnabled
    assert (execution.directory / "child.cs").exists()
    assert inspect(execution)["completed"]


def test_csharp_runtime_error_is_adopted_after_outer_cleanup(execution, monkeypatch):
    execution.journal["language"] = "csharp-script"
    (execution.root / "Newtonsoft.Json.dll").write_bytes(b"FIXTURE")
    def nested(serial, macro, echo):
        write_json(execution.directory / "child-complete.json",
                   completion(execution.journal, status="error", mutation_state="partial",
                              user_code_started=True, user_code_completed=False,
                              error={"stage": "user_code", "message": "actual C# error"},
                              cleanup_errors=[], stdout_capture={"retained_bytes": 9}, diagnostics_truncated=True))
        return True
    _, final = _run_python_wrapper(execution, 'throw new Exception("actual C# error");',
                                   monkeypatch, run_script=nested)
    assert final["status"] == "error" and final["error"]["message"] == "actual C# error"
    assert final["mutation_state"] == "partial" and final["undo"]["ended"]
    assert final["stdout_capture"] == {"retained_bytes": 9}
    assert final["diagnostics_truncated"] is True
    assert inspect(execution)["completed"]


def test_csharp_result_is_not_overwritten_by_outer_python(execution, monkeypatch):
    execution.journal["language"] = "csharp-script"
    (execution.root / "Newtonsoft.Json.dll").write_bytes(b"FIXTURE")
    raw = b'{"csharp":42}'
    def nested(serial, macro, echo):
        (execution.directory / "result.json").write_bytes(raw)
        write_json(execution.directory / "child-complete.json",
                   completion(execution.journal, user_code_started=True, user_code_completed=True,
                              result_available=True, result_bytes=len(raw),
                              result_sha256=hashlib.sha256(raw).hexdigest(), cleanup_errors=[]))
        return True
    _, final = _run_python_wrapper(execution, 'result_json = "{\"csharp\":42}";',
                                   monkeypatch, run_script=nested)
    assert final["status"] == "success" and final["result_available"]
    assert (execution.directory / "result.json").read_bytes() == raw
    assert "result_error" not in final
    assert inspect(execution)["completed"]


def test_recovery_selects_and_pages_stored_result_without_rhino(execution):
    value = {"name": "retained", "objects": [{"id": str(n), "value": n} for n in range(12)]}
    raw = json.dumps(value).encode()
    (execution.directory / "result.json").write_bytes(raw)
    publish_final(execution, result_available=True, result_bytes=len(raw),
                  result_sha256=hashlib.sha256(raw).hexdigest())
    owner = rc.RhinocodeExecution(execution.binding, execution.locations)
    result = owner.get_execution(result_fields=["objects"], offset=4, limit=3, include_ids=False)
    assert result["completed"] and result["result"] == {"objects": [{"value": n} for n in range(4, 7)]}
    assert result["result_page"]["pages"]["objects"] == dict(total=12, offset=4, returned=3, next_offset=7)
    hidden = owner.get_execution(include_result=False)
    assert hidden["completed"] and "result" not in hidden
    (execution.directory / "result.json").write_bytes(b"{}")
    damaged = owner.get_execution()
    assert damaged["completed"] and "no longer matches" in damaged["result_display_error"]


def test_unreadable_log_does_not_hide_known_execution_completion(execution, monkeypatch):
    publish_final(execution)
    (execution.directory / "stdout.txt").write_bytes(b"logged")
    original = Path.open
    def locked_log(path, *args, **kwargs):
        if path.name == "stdout.txt":
            raise PermissionError("log access fixture")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", locked_log)
    owner = rc.RhinocodeExecution(execution.binding, execution.locations)
    result = owner.get_execution(include_stdout=True)
    assert result["completed"] and "log access fixture" in result["stdout_display_error"]


def test_huge_result_field_metadata_is_bounded_and_file_remains_retrievable(execution):
    raw = json.dumps({"x" * 100000: "stored"}).encode()
    (execution.directory / "result.json").write_bytes(raw)
    publish_final(execution, result_available=True, result_bytes=len(raw),
                  result_sha256=hashlib.sha256(raw).hexdigest())
    result = rc.RhinocodeExecution(execution.binding, execution.locations).get_execution()
    assert result["completed"] and result["result_page"]["metadata_truncated"]
    assert "result" not in result and "result_display_error" in result
    assert Path(result["result_file"]).read_bytes() == raw
    assert len(json.dumps(result)) < 12000


def _launch_fixture(execution, monkeypatch):
    (execution.session / "rhinocode.json").unlink()
    binary = execution.root / "rhinocode.exe"
    binary.write_bytes(b"OFFLINE FIXTURE")
    monkeypatch.setattr(rc, "find_binary", lambda explicit=None: binary)
    monkeypatch.setattr(rc, "discover_instances", lambda executable: [dict(
        processId=42, pipeId="rhinocode_remotepipe_42", processVersion="8.34.26223",
        activeDoc={"location": str(execution.model)})])
    monkeypatch.setattr(rc, "verify_process", lambda binding: None)
    monkeypatch.setattr(rc, "_child_identity", lambda process: dict(pid=99, process_start_ticks="456"))
    owner = rc.RhinocodeExecution(execution.binding, execution.locations, enabled_languages={"python"})
    return owner


def test_register_and_durable_fence_precede_launch_failure(execution, monkeypatch):
    owner = _launch_fixture(execution, monkeypatch)
    registered = []
    def fail(*args, **kwargs):
        assert registered and owner.journal_path.exists()
        assert kwargs["shell"] is False
        assert args[0][1:4] == ["--rhino", "rhinocode_remotepipe_42", "command"]
        assert args[0][4].startswith('_-ScriptEditor _Run "')
        raise FileNotFoundError("executable disappeared")
    monkeypatch.setattr(rc.subprocess, "Popen", fail)
    result = owner.execute("result = 1", "python", 1, operation_id="b" * 32,
                           operation_dir=execution.calls / ("b" * 32), register=registered.append)
    assert result["completed"] and result["not_dispatched"]
    assert rc.inspect_session(execution.session)["completed"]


def test_exited_cli_is_waited_for_late_wrapper_final(execution, monkeypatch):
    owner = _launch_fixture(execution, monkeypatch)
    calls = []
    timer = None
    class Child:
        pid = 99
        stdout = io.BytesIO(b"dispatch")
        stderr = io.BytesIO()
        def poll(self):
            return 0
    def launch(*args, **kwargs):
        nonlocal timer
        calls.append(args)
        journal = json.loads(owner.journal_path.read_text())
        directory = rc.execution_directory(execution.calls, journal)
        timer = threading.Timer(0.1, lambda: write_json(directory / "complete.json", completion(journal)))
        timer.start()
        return Child()
    monkeypatch.setattr(rc.subprocess, "Popen", launch)
    try:
        result = owner.execute("result = 1", "python", 1, operation_id="b" * 32,
                               operation_dir=execution.calls / ("b" * 32), register=lambda handle: None)
    finally:
        if timer:
            timer.join()
    assert result["completed"] and len(calls) == 1


def test_timeout_retains_files_and_recovers_without_reexecution(execution, monkeypatch):
    owner = _launch_fixture(execution, monkeypatch)
    calls = []
    class Child:
        pid = 99
        stdout = io.BytesIO()
        stderr = io.BytesIO()
        def poll(self):
            return 0
    monkeypatch.setattr(rc.subprocess, "Popen", lambda *a, **k: calls.append(a) or Child())
    result = owner.execute("result = 1", "python", 1, operation_id="b" * 32,
                           operation_dir=execution.calls / ("b" * 32), register=lambda handle: None)
    assert result["timed_out"] and not result["completed"] and len(calls) == 1
    handle = owner.handles[result["request_id"]]
    assert (handle.directory / "wrapper.py").exists()
    write_json(handle.directory / "complete.json", completion(handle.journal))
    recovered = owner.get_execution(result["request_id"])
    assert recovered["completed"] and not recovered["uncertain"] and len(calls) == 1


def test_unverified_command_and_async_body_rejected_before_dispatch(execution):
    owner = rc.RhinocodeExecution(execution.binding, execution.locations,
                                  enabled_languages={"python", "command"}, command_enabled=False)
    with pytest.raises(ValueError, match="synchronous"):
        owner.execute("_Circle 0,0,0 10", "command", 1, operation_id="b" * 32,
                      operation_dir=execution.calls / ("b" * 32), register=lambda handle: None)
    with pytest.raises(ValueError, match="Asynchronous"):
        owner.execute("# async: true\nresult = 1", "python", 1, operation_id="b" * 32,
                      operation_dir=execution.calls / ("b" * 32), register=lambda handle: None)


def _complete_design_query(execution, monkeypatch, value):
    owner = _launch_fixture(execution, monkeypatch)
    calls = []
    class Child:
        pid = 99
        stdout = io.BytesIO()
        stderr = io.BytesIO()
        def poll(self):
            return 0
    def launch(*args, **kwargs):
        calls.append(args)
        journal = json.loads(owner.journal_path.read_text())
        directory = rc.execution_directory(execution.calls, journal)
        raw = json.dumps(value).encode()
        (directory / "result.json").write_bytes(raw)
        write_json(directory / "complete.json", completion(
            journal, result_available=True, result_bytes=len(raw),
            result_sha256=hashlib.sha256(raw).hexdigest(),
            undo={"before": 9, "owned": 0, "ended": False}, cleanup_errors=[]))
        return Child()
    monkeypatch.setattr(rc.subprocess, "Popen", launch)
    result = owner.execute("result = design_measurements", "python", 1,
                           operation_id="b" * 32, operation_dir=execution.calls / ("b" * 32),
                           register=lambda handle: None)
    return owner, result, calls


def test_design_measurements_are_the_small_success_response(execution, monkeypatch):
    # Given measured room area and door clearance from one Rhino script,
    # When the execution succeeds, Then the answer stays small and directly useful.
    measurements = {"areas_m2": {"living": 32.5}, "clearances_mm": {"door": 900}}
    owner, answer, calls = _complete_design_query(execution, monkeypatch, measurements)
    assert answer["completed"] and answer["status"] == "success"
    assert answer["result"] == measurements and len(calls) == 1
    assert len(json.dumps(answer)) < 600
    assert "undo" not in answer and "native_status" not in answer and "result_file" not in answer
    detail = owner.get_execution(answer["request_id"], result_fields=["clearances_mm"])
    assert detail["result"] == {"clearances_mm": {"door": 900}}
    assert detail["result_sha256"] and detail["undo"]["before"] == 9
    assert len(calls) == 1


def test_large_design_schedule_still_exposes_remaining_rows_without_rerun(execution, monkeypatch):
    # Given a 25-member schedule, When the first answer shows 20 rows,
    # Then its continuation can retrieve the last five from the same execution.
    schedule = [{"member": "beam-" + str(n), "length_mm": 3000 + n} for n in range(25)]
    owner, answer, calls = _complete_design_query(execution, monkeypatch, schedule)
    assert answer["result"] == schedule[:20]
    assert answer["result_page"]["pages"]["result"]["next_offset"] == 20
    continuation = owner.get_execution(answer["request_id"], offset=20, limit=20)
    assert continuation["result"] == schedule[20:] and len(calls) == 1


@pytest.mark.parametrize("value", [
    json.dumps({"extended": 24, "cut_objects": 6}),
    "벽체 24개를 연장하고 절단 객체 6개를 정리했습니다.",
    "🧱" * 4096,
], ids=["serialized-json", "korean", "unicode-boundary"])
def test_small_text_result_is_complete_in_initial_response(execution, monkeypatch, value):
    owner, answer, calls = _complete_design_query(execution, monkeypatch, value)
    assert answer["completed"] and answer["result"] == value
    assert "result_page" not in answer and "result_display_error" not in answer
    # Explicit reads retain their documented character offset/limit contract.
    page = owner.get_execution(answer["request_id"], offset=3, limit=7)
    assert page["result"] == value[3:10] and len(calls) == 1


def test_large_text_initial_page_has_character_continuation(execution, monkeypatch):
    value = "측정" * 2500
    owner, answer, calls = _complete_design_query(execution, monkeypatch, value)
    assert answer["result"] == value[:4096]
    assert answer["result_page"]["unit"] == "characters"
    assert answer["result_page"]["pages"]["result"]["next_offset"] == 4096
    page = owner.get_execution(answer["request_id"], offset=4096, limit=1000)
    assert page["result"] == value[4096:] and len(calls) == 1
