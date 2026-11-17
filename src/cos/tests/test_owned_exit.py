"""The external Exit adapter recovers its common runtime child ownership."""
import json
import os
import sys

import session_close
from owned_process import launch_owned


def test_exit_adapter_recovers_exact_child_when_parent_record_was_not_updated(tmp_path, monkeypatch):
    record = dict(request_id="close-fixture", nonce="e" * 32,
                  target=dict(pid=os.getpid(), process_start_ticks="1", document_serial=1,
                              model_path=str(tmp_path / "fixture.3dm")),
                  pipe_id="fixture", executable=sys.executable, launch_protocol="owned-v1")
    monkeypatch.setattr(session_close, "discover_instances", lambda _: [])
    monkeypatch.setattr(session_close, "select_instance", lambda *_: {"pipeId": "fixture"})
    def fixture_cli(argv, directory, owner, **options):
        receipt = dict(owner, schema="almond-close-guard", state="rejected", reason="fixture refusal")
        body = "from pathlib import Path; Path(" + repr(str(directory / "guard.json")) + ").write_text(" + repr(json.dumps(receipt)) + ")"
        return launch_owned([sys.executable, "-c", body], directory, owner, **options)
    monkeypatch.setattr(session_close, "launch_owned", fixture_cli)
    adapter = session_close.RhinoExit()
    adapter.launch(record, tmp_path)
    adapter.process.wait(timeout=5)
    record.pop("child")  # Parent died before publishing its in-memory update.
    recovered = session_close.RhinoExit().inspect(record, tmp_path)
    assert recovered["cli_closed"] and recovered["guard_state"] == "rejected"
