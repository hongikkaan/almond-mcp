import json
import os
import subprocess
import sys
import time
from uuid import uuid4

import pytest

from owned_process import authorize_owned, launch_owned, read_owned_exit
from project import process_start_ticks, read_json


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Almond supervises a Windows process tree")


def _wait_for(check, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    pytest.fail("The disposable process did not reach the expected state")


def _stop(process):
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=5)


def _exit_receipt(directory, owner):
    try:
        return read_owned_exit(directory, owner)
    except FileNotFoundError:
        return None


def _original_process_exited(identity):
    try:
        return process_start_ticks(identity["pid"]) != identity["process_start_ticks"]
    except RuntimeError:
        return True


def test_parent_exit_without_admission_cannot_run_the_command(tmp_path):
    owner = {"request_id": uuid4().hex, "nonce": uuid4().hex}
    parent_code = """
import json, os, subprocess, sys
from owned_process import launch_owned

directory, owner = sys.argv[1:]
launch_owned(
    [sys.executable, "-c", "from pathlib import Path; Path('changed.txt').touch()"],
    directory, json.loads(owner), cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
os._exit(73)
"""
    parent = subprocess.run(
        [sys.executable, "-B", "-c", parent_code, str(tmp_path), json.dumps(owner)],
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(os.path.abspath(entry) for entry in sys.path)),
        timeout=10,
    )
    assert parent.returncode == 73

    receipt = _wait_for(lambda: _exit_receipt(tmp_path, owner))
    assert receipt["dispatched"] is False
    assert not (tmp_path / "changed.txt").exists()


def test_terminating_an_admitted_supervisor_only_ends_its_own_command(tmp_path):
    owner = {"request_id": uuid4().hex, "nonce": uuid4().hex}
    interpreter = getattr(sys, "_base_executable", sys.executable)
    command = """
import os, time
from project import process_start_ticks, write_json

write_json("running.json", {
    "pid": os.getpid(),
    "process_start_ticks": process_start_ticks(os.getpid()),
})
time.sleep(30)
"""
    neighbor = subprocess.Popen([interpreter, "-B", "-c", "import time; time.sleep(30)"])
    try:
        process = launch_owned(
            [interpreter, "-B", "-c", command], tmp_path, owner, cwd=str(tmp_path),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            authorize_owned(process, tmp_path, owner)
            evidence = tmp_path / "running.json"
            _wait_for(evidence.is_file)
            child = read_json(evidence)
            assert not _original_process_exited(child)
            assert neighbor.poll() is None

            _stop(process)
            _wait_for(lambda: _original_process_exited(child))
            assert neighbor.poll() is None
        finally:
            _stop(process)
    finally:
        _stop(neighbor)
