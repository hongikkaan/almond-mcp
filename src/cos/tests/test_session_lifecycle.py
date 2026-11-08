"""Regression coverage for real Windows Rhino launch and unsaved documents."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src/cos"))
from detached_process import rhino_command_line
from external_host import Broker, UNSAVED_DOCUMENT
from session_start import RhinoStart


def test_startup_macro_has_literal_quotes_and_precedes_model_path():
    executable = r"C:\Program Files\Rhino 8\System\Rhino.exe"
    model = r"C:\work\한글 project\주거동.3dm"
    command = rhino_command_line([executable, "/nosplash", model], "_almondconnect")
    assert command == f'"{executable}" /runscript="_almondconnect" /nosplash "{model}"'
    assert '\\"' not in command


def test_no_startup_macro_preserves_standard_windows_argument_quoting():
    args = [r"C:\Program Files\Rhino 8\Rhino.exe", "/nosplash", r"C:\a b\model.3dm"]
    assert rhino_command_line(args) == subprocess.list2cmdline(args)


@pytest.mark.parametrize("script", ["", '"_almondconnect"', "first\nsecond", "first\rsecond", "first\0second"])
def test_startup_macro_rejects_ambiguous_raw_command_line(script):
    with pytest.raises(ValueError, match="startup script"):
        rhino_command_line(["Rhino.exe"], script)


def test_session_start_uses_quoted_macro_without_touching_saved_model(tmp_path, monkeypatch):
    executable = tmp_path / "Rhino.exe"
    executable.touch()
    model = tmp_path / "주거동 model.3dm"
    model.write_bytes(b"test fixture, not a live Rhino model")
    before = model.read_bytes()
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"rhino_exe": str(executable)}), encoding="utf-8")
    launches = []
    def launch(args, **kwargs):
        launches.append((args, kwargs))
        return SimpleNamespace(pid=123, poll=lambda: None)
    monkeypatch.setenv("ALMOND_SESSION_TOKEN", "old-test-token")
    started = RhinoStart(str(model), tmp_path, settings_path=settings, process_factory=launch,
                         identity_reader=lambda pid: {"pid": pid, "process_start_ticks": "456"})
    args, options = launches[0]
    assert args == [str(executable), "/nosplash", str(model)]
    assert options["startup_script"] == "_almondconnect"
    assert options["cwd"] == str(tmp_path)
    assert "ALMOND_SESSION_TOKEN" not in options["env"]
    assert started.identity["pid"] == 123
    assert model.read_bytes() == before
    assert not (tmp_path / ".almond").exists()


class Lease:
    closed = False
    def close(self):
        self.closed = True


class Control:
    def __init__(self, description):
        self.description = description
        self.calls = []
        self.closed = False

    async def request(self, action, **kwargs):
        self.calls.append(action)
        if action == "describe":
            return dict(self.description)
        if action == "detach":
            return {"detached": True}
        raise AssertionError(f"Unexpected native request: {action}")

    async def close(self):
        self.closed = True


def broker_for(tmp_path, description):
    record = {"host_id": "test-host", "pid": 123}
    control, lease = Control(description), Lease()
    broker = Broker({"tools": []}, data=tmp_path,
                    host_reader=lambda _: [record], control_factory=lambda _: control,
                    lease_factory=lambda *_: lease, contract_check=lambda _: None,
                    worker_factory=lambda *_: pytest.fail("Worker must not start"),
                    recovery_store_factory=lambda _: None)
    return broker, control, lease


@pytest.mark.parametrize("model_path", [None, "", " "])
def test_unsaved_document_is_unavailable_with_save_instructions(tmp_path, model_path):
    broker, control, lease = broker_for(tmp_path, {
        "model_path": model_path, "saved": False, "state": "available"})
    found = asyncio.run(broker.list_connections())["targets"][0]
    assert found["state"] == "unavailable"
    assert found["reason"] == UNSAVED_DOCUMENT
    assert found["saved"] is False
    assert control.calls == ["describe"]
    assert control.closed and lease.closed


@pytest.mark.parametrize("model_path", [None, "", " "])
def test_unsaved_connect_is_clear_and_releases_ownership(tmp_path, model_path):
    broker, control, lease = broker_for(tmp_path, {
        "model_path": model_path, "saved": False, "state": "available"})
    result = asyncio.run(broker.call("connect", {"host_id": "test-host", "model_path": ""}))
    assert result.is_error
    assert result.content[0].text == UNSAVED_DOCUMENT
    assert control.calls == ["describe", "detach"]
    assert control.closed and lease.closed
    assert not broker.connections and not broker.host_connections


def test_saved_document_listing_is_unchanged(tmp_path):
    broker, control, lease = broker_for(tmp_path, {
        "model_path": r"C:\work\model.3dm", "saved": True, "state": "available", "reason": ""})
    found = asyncio.run(broker.list_connections())["targets"][0]
    assert found["state"] == "available"
    assert found["reason"] == ""
    assert found["model_filename"] == "model.3dm"


def test_changed_saved_document_still_rejects_stale_model_path(tmp_path):
    broker, control, lease = broker_for(tmp_path, {
        "model_path": r"C:\work\new.3dm", "saved": True, "state": "available"})
    result = asyncio.run(broker.call("connect", {
        "host_id": "test-host", "model_path": r"C:\work\old.3dm"}))
    assert result.is_error
    assert "saved model changed" in result.content[0].text
    assert control.calls == ["describe", "detach"]
    assert control.closed and lease.closed
