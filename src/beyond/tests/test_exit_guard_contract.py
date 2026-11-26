import json
import runpy
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

import session_close
from session_close import RhinoExit


@pytest.mark.parametrize("change", ["none", "modified", "different-document", "restarted-process"])
def test_exit_guard_only_closes_the_same_unmodified_document(tmp_path, monkeypatch, change):
    model = tmp_path / "drawing.3dm"
    model.touch()
    target = {"pid": 101, "process_start_ticks": "10", "model_path": str(model), "document_serial": 3}
    token = uuid4().hex
    ready = tmp_path / "ready.json"
    ready.write_text(json.dumps({"token": token, "valid": True}), encoding="utf-8")
    record = {
        "target": target, "request_id": "one-close", "nonce": uuid4().hex,
        "binding": {"ready_path": str(ready), "token": token},
        "worker_identity": {"pid": 102, "process_start_ticks": "20"},
    }
    monkeypatch.setattr(session_close, "find_binary", lambda: "offline-rhino-code")
    monkeypatch.setattr(session_close, "discover_instances", lambda _: [])
    monkeypatch.setattr(session_close, "select_instance", lambda *_: {"pipeId": "fixture"})
    RhinoExit().prepare(record, tmp_path)

    document = SimpleNamespace(
        RuntimeSerialNumber=4 if change == "different-document" else 3,
        Path=str(model), Modified=change == "modified", IsReadOnly=False,
    )
    requests = []

    def run_script(serial, command, echo):
        requests.append((serial, command))
        return True

    def process(pid, start):
        return SimpleNamespace(
            Id=pid, HasExited=False, Dispose=lambda: None,
            StartTime=SimpleNamespace(ToUniversalTime=lambda: SimpleNamespace(Ticks=start)),
        )

    monkeypatch.setitem(sys.modules, "Rhino", SimpleNamespace(
        RhinoDoc=SimpleNamespace(ActiveDoc=document),
        RhinoApp=SimpleNamespace(IsOnMainThread=True, RunScript=run_script),
        Commands=SimpleNamespace(Command=SimpleNamespace(InScriptRunnerCommand=lambda: True)),
    ))
    monkeypatch.setitem(sys.modules, "System", SimpleNamespace(Diagnostics=SimpleNamespace(
        Process=SimpleNamespace(
            GetCurrentProcess=lambda: process(101, 11 if change == "restarted-process" else 10),
            GetProcessById=lambda pid: process(pid, 20),
        ),
    )))
    runpy.run_path(str(tmp_path / "guard.py"))
    receipt = json.loads((tmp_path / "guard.json").read_text(encoding="utf-8"))

    if change == "none":
        assert requests == [(3, "_-Exit")]
        assert receipt["state"] == "exit_returned"
    else:
        assert requests == []
        assert receipt["state"] == "rejected"
