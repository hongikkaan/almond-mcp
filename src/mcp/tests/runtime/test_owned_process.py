"""Real disposable children verify launch ownership before any external work."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from project import read_json


def test_owned_cli_has_durable_identity_before_command_can_run(tmp_path):
    from owned_process import authorize_owned, launch_owned, read_owned_identity
    owner = {"request_id": "a" * 32, "nonce": "b" * 32}
    output = tmp_path / "observed.json"
    code = "import pathlib; p=pathlib.Path(__import__('sys').argv[1]); (p/'observed.json').write_bytes((p/'child.json').read_bytes())"
    process = launch_owned([sys.executable, "-c", code, str(tmp_path)], tmp_path, owner,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    authorize_owned(process, tmp_path, owner)
    assert process.wait(timeout=10) == 0
    identity = read_owned_identity(tmp_path, owner)
    assert read_json(output)["child"] == identity
    assert identity["pid"] == process.pid and int(identity["process_start_ticks"]) > 0


def test_parent_death_before_authorization_cannot_dispatch_cli(tmp_path):
    from owned_process import read_owned_identity
    owner = {"request_id": "c" * 32, "nonce": "d" * 32}
    code = '''
import json, os, subprocess, sys
from owned_process import launch_owned
from pathlib import Path
folder = Path(sys.argv[1])
launch_owned([sys.executable, "-c", "from pathlib import Path; Path('MUTATED').touch()"],
             folder, json.loads(sys.argv[2]), cwd=str(folder),
             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os._exit(73)
'''
    child = subprocess.run([sys.executable, "-c", code, str(tmp_path), json.dumps(owner)],
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)))
    assert child.returncode == 73
    deadline = time.monotonic() + 15
    while not (tmp_path / "child-exit.json").exists() and time.monotonic() < deadline:
        time.sleep(.05)
    assert read_json(tmp_path / "child-exit.json")["dispatched"] is False
    assert not (tmp_path / "MUTATED").exists()
    assert read_owned_identity(tmp_path, owner)["pid"] > 0


def test_recovery_after_parent_death_uses_child_identity_and_exact_native_receipt(tmp_path):
    from rhinocode import inspect_execution
    journal = dict(schema="almond-rhinocode-execution", version=1, token="a" * 32,
        operation_id="b" * 32, request_id="c" * 32, nonce="d" * 32, source_hash="e" * 64,
        language="python", child=None, launch_protocol="owned-v1",
        target=dict(pid=1, process_start_ticks="2", document_serial=3,
                    model_path=str(tmp_path / "fixture.3dm"), pipe_id="fixture"))
    (tmp_path / "request.json").write_text(json.dumps(journal))
    code = '''
import json, os, subprocess, sys
from pathlib import Path
from owned_process import launch_owned, authorize_owned
folder = Path(sys.argv[1])
journal = json.loads((folder / "request.json").read_text())
owner = {key: journal[key] for key in ("token", "operation_id", "request_id", "nonce", "source_hash", "target")}
receipt = dict(owner, schema="almond-rhinocode-completion", version=1,
               status="success", mutation_state="completed", execution_complete=True)
body = "import time,pathlib; time.sleep(.2); pathlib.Path('complete.json').write_text(" + repr(json.dumps(receipt)) + ")"
process = launch_owned([sys.executable, "-c", body], folder, owner, cwd=str(folder),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
authorize_owned(process, folder, owner)
os._exit(74)  # The owning execution journal still has child=None.
'''
    child = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)))
    assert child.returncode == 74
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = inspect_execution(journal, receipt_path=tmp_path / "complete.json")
        if state["completed"]:
            break
        time.sleep(.02)
    assert state["completed"] and state["request_id"] == "c" * 32
    assert state["native_completed"] and not state["uncertain"]
    # Process exit by itself must never discharge a Rhino operation.
    (tmp_path / "complete.json").unlink()
    missing = inspect_execution(journal, receipt_path=tmp_path / "complete.json")
    assert not missing["completed"] and missing["completion_state"] == "awaiting_receipt"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows job ownership")
def test_supervisor_death_terminates_only_its_owned_cli_tree(tmp_path):
    from owned_process import authorize_owned, launch_owned
    from storage_cleanup import process_identity_alive
    owner = {"request_id": "e" * 32, "nonce": "f" * 32}
    body = ("import os,time; from project import process_start_ticks,write_json; "
            "write_json('cli.json',dict(pid=os.getpid(),process_start_ticks=process_start_ticks(os.getpid()))); "
            "time.sleep(30)")
    process = launch_owned([getattr(sys, "_base_executable", sys.executable), "-c", body],
                          tmp_path, owner, cwd=str(tmp_path),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        authorize_owned(process, tmp_path, owner)
        deadline = time.monotonic() + 5
        while not (tmp_path / "cli.json").exists() and time.monotonic() < deadline:
            time.sleep(.02)
        cli = read_json(tmp_path / "cli.json")
        assert process_identity_alive(cli) is True
        process.terminate()  # Only the exact test-owned process handle.
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while process_identity_alive(cli) is not False and time.monotonic() < deadline:
            time.sleep(.02)
        assert process_identity_alive(cli) is False
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def test_public_rhinocode_execution_uses_real_owned_launcher(tmp_path, monkeypatch):
    import rhinocode
    from owned_process import launch_owned
    session, operation = tmp_path / "session", tmp_path / ("1" * 32)
    session.mkdir()
    operation.mkdir()
    binding = dict(pid=1, process_start_ticks="2", document_serial=3,
                   model_path=str(tmp_path / "fixture.3dm"), token="a" * 32)
    locations = dict(session_dir=str(session), project_dir=str(tmp_path), call_root=str(tmp_path))
    monkeypatch.setattr(rhinocode, "find_binary", lambda _: Path(sys.executable))
    monkeypatch.setattr(rhinocode, "discover_instances", lambda _: [])
    monkeypatch.setattr(rhinocode, "select_instance", lambda *_: {"pipeId": "fixture"})
    def fixture_cli(argv, directory, owner, **options):
        receipt = dict(owner, schema="almond-rhinocode-completion", version=1, layout="compact-v1",
                       status="success", mutation_state="completed", execution_complete=True)
        body = "from pathlib import Path; Path(" + repr(str(directory / "complete.json")) + ").write_text(" + repr(json.dumps(receipt)) + ")"
        # Replace only the native endpoint command. Ownership, handshake,
        # process lifetime, journal, and public execute/get_execution stay real.
        return launch_owned([sys.executable, "-c", body], directory, owner, **options)
    monkeypatch.setattr(rhinocode, "launch_owned", fixture_cli)
    runner = rhinocode.RhinocodeExecution(binding, locations)
    result = runner.execute("pass", "python", 5, operation_id="1" * 32,
                            operation_dir=operation, register=lambda handle: None)
    assert result["status"] == "executed" and result["completed"] and not result.get("uncertain", False)
    journal = read_json(session / "rhinocode.json")
    assert journal["launch_protocol"] == "owned-v1" and journal["child"]["pid"] > 0
    assert runner.get_execution(result["request_id"])["completed"]
