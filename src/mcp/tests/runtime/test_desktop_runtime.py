"""Desktop stdio contracts with local peers only; no WMI, Rhino or user data."""
import io
import json
from pathlib import Path
import socket
import struct
import threading
from types import SimpleNamespace

import pytest

import desktop_runtime as runtime

ALMOND_ARGS = ["-B", "-m", "almond_mcp.features.assets.asset_repository", "--snapshot"]


class FragmentedSocket:
    def __init__(self, incoming=b"", fragment=1):
        self.incoming = bytearray(incoming)
        self.fragment = fragment
        self.sent = bytearray()

    def recv(self, count):
        count = min(count, self.fragment, len(self.incoming))
        result = bytes(self.incoming[:count])
        del self.incoming[:count]
        return result

    def sendall(self, data):
        self.sent.extend(data)

    def settimeout(self, value):
        pass

    def shutdown(self, how):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def wire(kind, data=b""):
    payload = kind + data
    return struct.pack("!I", len(payload)) + payload


@pytest.fixture
def desktop_peer(monkeypatch):
    """Replace the process launcher with an authenticated in-process socket peer."""
    threads, failures, observations = [], [], []
    monkeypatch.setattr(runtime, "_require_full_trust", lambda: None)

    def install(callback):
        def launch(port, token):
            observations.append((port, token))
            def communicate():
                try:
                    callback(port, token)
                except BaseException as error:
                    failures.append(error)
            thread = threading.Thread(target=communicate, daemon=True)
            threads.append(thread)
            thread.start()
            return 12345
        monkeypatch.setattr(runtime, "_launch_reader", launch)
        return observations

    yield install
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive(), "Local test peer did not finish"
    assert not failures, repr(failures)


def authenticate(port, token):
    peer = socket.create_connection(("127.0.0.1", port), timeout=3)
    # Fragment authentication too: a recv call need not return the whole token.
    for offset in range(0, len(token), 3):
        peer.sendall(token[offset:offset + 3].encode("ascii"))
    return peer


def test_frames_preserve_fragmented_utf8_and_message_boundaries():
    text = "한글 3DM 🔎".encode("utf-8")
    stream = FragmentedSocket(wire(b"O", text[:2]) + wire(b"O", text[2:]) + wire(b"I"))
    first = runtime._read_frame(stream)
    second = runtime._read_frame(stream)
    assert first[0] == second[0] == b"O"
    assert first[1] + second[1] == text
    assert runtime._read_frame(stream) == (b"I", b"")
    assert not stream.incoming


@pytest.mark.parametrize("size", [0, runtime._MAX_FRAME + 1])
def test_invalid_frame_sizes_are_rejected_before_reading_payload(size):
    stream = FragmentedSocket(struct.pack("!I", size) + b"private payload")
    with pytest.raises(ValueError, match="frame size"):
        runtime._read_frame(stream)
    assert stream.incoming == b"private payload"


@pytest.mark.parametrize("truncated", [b"\x00\x00", struct.pack("!I", 4) + b"Oa"])
def test_truncated_header_or_payload_reports_eof(truncated):
    with pytest.raises(EOFError, match="connection closed"):
        runtime._read_frame(FragmentedSocket(truncated))


def test_send_frame_accepts_exact_limit_and_rejects_oversize_without_writing():
    stream = FragmentedSocket(fragment=65536)
    data = b"a" * (runtime._MAX_FRAME - 1)
    runtime._send_frame(stream, threading.Lock(), b"O", data)
    assert bytes(stream.sent) == wire(b"O", data)
    before = bytes(stream.sent)
    with pytest.raises(ValueError, match="exceeded"):
        runtime._send_frame(stream, threading.Lock(), b"O", data + b"a")
    assert bytes(stream.sent) == before


def test_desktop_fast_path_does_not_launch(monkeypatch):
    monkeypatch.setattr(runtime, "redirected_library_view", lambda: False)
    def forbidden(*args, **kwargs):
        raise AssertionError("The ordinary file view must not re-execute")
    monkeypatch.setattr(runtime, "run_desktop", forbidden)
    assert runtime.ensure_desktop_runtime() is None


def test_reexecution_preserves_original_python_arguments_and_happens_once(monkeypatch):
    original = ["python.exe", "-B", "-X", "utf8", "-m", "almond_mcp", "--model", "한글 모델.3dm"]
    monkeypatch.setattr(runtime.sys, "orig_argv", original)
    views = iter([True, False])
    monkeypatch.setattr(runtime, "redirected_library_view", lambda: next(views))
    calls = []
    def run(args):
        calls.append(args)
        runtime.ensure_desktop_runtime()  # The actual desktop entry sees no redirection.
        return 19
    monkeypatch.setattr(runtime, "run_desktop", run)
    with pytest.raises(SystemExit) as exit_status:
        runtime.ensure_desktop_runtime()
    assert exit_status.value.code == 19 and calls == [original[1:]]


def test_relay_keeps_stdin_eof_stdout_stderr_arguments_and_exit_status(desktop_peer, monkeypatch):
    expected_input = "{\"jsonrpc\":\"2.0\",\"text\":\"한글\"}\n".encode("utf-8")
    expected_output = "{\"result\":\"완료 🔎\"}\n".encode("utf-8")
    expected_error = "진단은 stderr\n".encode("utf-8")
    args = ["-B", "-m", "almond_mcp", "--token", "argument with spaces"]
    monkeypatch.setenv("ALMOND_TEST_DESKTOP_ENV", "unchanged 한글")
    captured = {}
    def peer(port, token):
        with authenticate(port, token) as connection:
            kind, payload = runtime._read_frame(connection)
            assert kind == b"C"
            captured.update(json.loads(payload))
            chunks = []
            while True:
                kind, payload = runtime._read_frame(connection)
                assert kind == b"I"
                if not payload:
                    break
                chunks.append(payload)
            captured["stdin"] = b"".join(chunks)
            # Split inside a multibyte codepoint and fragment the wire as well.
            split = expected_output.index("완".encode("utf-8")) + 1
            outgoing = wire(b"O", expected_output[:split]) + wire(b"E", expected_error) + wire(b"O", expected_output[split:]) + wire(b"X", b"23")
            for offset in range(0, len(outgoing), 2):
                connection.sendall(outgoing[offset:offset + 2])
    launches = desktop_peer(peer)
    output, error = io.BytesIO(), io.BytesIO()
    assert runtime.run_desktop(args, stdin=io.BytesIO(expected_input), stdout=output, stderr=error) == 23
    assert captured["args"] == args and captured["cwd"] == runtime.os.getcwd()
    assert captured["env"]["ALMOND_TEST_DESKTOP_ENV"] == "unchanged 한글"
    assert captured["stdin"] == expected_input
    assert output.getvalue() == expected_output and error.getvalue() == expected_error
    assert len(launches) == 1


@pytest.mark.parametrize("message,error,match", [
    (wire(b"F", "child 준비 실패".encode("utf-8")), RuntimeError, "child 준비 실패"),
    (wire(b"?", b"unexpected"), ValueError, "Unexpected"),
    (b"", EOFError, "connection closed"),
])
def test_child_failure_is_not_reported_as_success(desktop_peer, message, error, match):
    def peer(port, token):
        with authenticate(port, token) as connection:
            assert runtime._read_frame(connection)[0] == b"C"
            # Consume the fixture's EOF so no test-owned sender remains blocked.
            assert runtime._read_frame(connection) == (b"I", b"")
            if message:
                connection.sendall(message)
    desktop_peer(peer)
    output = io.BytesIO()
    with pytest.raises(error, match=match):
        runtime.run_desktop(ALMOND_ARGS, stdin=io.BytesIO(), stdout=output, stderr=io.BytesIO())
    assert output.getvalue() == b""


def test_wrong_authentication_never_receives_environment_or_arguments(desktop_peer, monkeypatch):
    received = []
    def peer(port, token):
        with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
            wrong = ("0" if token[0] != "0" else "1") + token[1:]
            connection.sendall(wrong.encode("ascii"))
            received.append(connection.recv(4096))
            assert received == [b""]
    desktop_peer(peer)
    clock = iter([0, 0, 0, 21])
    monkeypatch.setattr(runtime, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    with pytest.raises(TimeoutError, match="authentication"):
        runtime.run_desktop([*ALMOND_ARGS, "--secret", "must-not-leak"], stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO())
    # The peer assertion is completed by fixture teardown after the listener closes.
    assert not received or received == [b""]


def test_still_redirected_child_reports_failure_before_starting_worker(monkeypatch):
    config = {"args": ALMOND_ARGS, "cwd": "C:/test/isolated", "env": {"TEST_ONLY": "1"}}
    stream = FragmentedSocket(wire(b"C", json.dumps(config).encode("utf-8")))
    monkeypatch.setattr(runtime.socket, "create_connection", lambda *args, **kwargs: stream)
    environment, directories = {}, []
    monkeypatch.setattr(runtime, "os", SimpleNamespace(environ=environment, chdir=directories.append))
    monkeypatch.setattr(runtime, "redirected_library_view", lambda: True)
    monkeypatch.setattr(runtime, "_require_full_trust", lambda: None)
    def forbidden(*args, **kwargs):
        raise AssertionError("No worker may start while its library view is still redirected")
    monkeypatch.setattr(runtime.subprocess, "Popen", forbidden)
    token = "a" * 64
    assert runtime._child(123, token) == 1
    assert environment == config["env"] and directories == [config["cwd"]]
    assert bytes(stream.sent[:64]) == token.encode("ascii")
    kind, message = runtime._read_frame(FragmentedSocket(stream.sent[64:]))
    assert kind == b"F" and b"No worker or library mutation" in message


def test_launcher_failure_does_not_fall_back_to_the_private_library(monkeypatch):
    def denied(*args, **kwargs):
        raise RuntimeError("launcher refused")
    monkeypatch.setattr(runtime, "_launch_reader", denied)
    monkeypatch.setattr(runtime, "_require_full_trust", lambda: None)
    with pytest.raises(RuntimeError, match="launcher refused"):
        runtime.run_desktop(ALMOND_ARGS, stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO())


@pytest.mark.parametrize("entry", ["almond_mcp", "almond_mcp.cli", "almond_mcp.features.assets.asset_repository"])
def test_only_exact_official_modules_are_accepted(entry):
    runtime._validate_args(["-B", "-u", "-X", "utf8", "-Xutf8", "-m", entry, "--help"])


@pytest.mark.parametrize("entry", ["cos/codex_host.py", "cos/cos_host.py", "mcp/runtime/mcp_server.py"])
def test_only_fixed_checkout_scripts_are_accepted(entry):
    source = Path(runtime.__file__).resolve().parents[2]
    runtime._validate_args(["-B", str(source / entry), "--help"])


@pytest.mark.parametrize("args", [[], "not a list", [1], ["\0"], ["-c", "print('no')"],
    ["-m", "os"], ["-m", "almond_mcp.cli.other"], ["C:/other/mcp_server.py"],
    ["-i", "-m", "almond_mcp"], ["-X", "other", "-m", "almond_mcp"]])
def test_invalid_parent_entry_never_checks_token_or_launches(monkeypatch, args):
    def forbidden(*unused, **kwargs):
        raise AssertionError("Invalid executable request reached the launch boundary")
    monkeypatch.setattr(runtime, "_require_full_trust", forbidden)
    monkeypatch.setattr(runtime, "_launch_reader", forbidden)
    with pytest.raises(ValueError, match="Almond"):
        runtime.run_desktop(args, stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO())


@pytest.mark.parametrize("restricted,container", [(False, False), (True, False), (False, True)])
def test_token_guard_rejects_restricted_or_appcontainer_and_closes_handle(monkeypatch, restricted, container):
    import ctypes
    class Call:
        def __init__(self, callback):
            self.callback = callback
        def __call__(self, *args):
            return self.callback(*args)
    closed = []
    kernel = SimpleNamespace(GetCurrentProcess=Call(lambda: 91), CloseHandle=Call(lambda handle: closed.append(handle.value)))
    def open_token(process, access, target):
        assert process == 91 and access == 8
        target._obj.value = 92
        return 1
    def token_info(token, kind, target, size, returned):
        assert token.value == 92 and kind == 29 and size == 4
        target._obj.value = int(container)
        returned._obj.value = 4
        return 1
    security = SimpleNamespace(OpenProcessToken=Call(open_token), GetTokenInformation=Call(token_info),
                               IsTokenRestricted=Call(lambda token: restricted))
    monkeypatch.setattr(ctypes, "WinDLL", lambda name, **kwargs: kernel if name == "kernel32" else security)
    if restricted or container:
        with pytest.raises(PermissionError, match="restricted execution context"):
            runtime._require_full_trust()
    else:
        runtime._require_full_trust()
    assert closed == [92]


def test_denied_parent_token_never_starts_desktop_process(monkeypatch):
    def denied():
        raise PermissionError("restricted execution context")
    def forbidden(*args, **kwargs):
        raise AssertionError("A restricted token reached the launcher")
    monkeypatch.setattr(runtime, "_require_full_trust", denied)
    monkeypatch.setattr(runtime, "_launch_reader", forbidden)
    with pytest.raises(PermissionError, match="restricted"):
        runtime.run_desktop(ALMOND_ARGS, stdin=io.BytesIO(), stdout=io.BytesIO(), stderr=io.BytesIO())


@pytest.mark.parametrize("rejection", ["arbitrary_code", "restricted_token"])
def test_child_revalidates_entry_and_token_before_worker_start(monkeypatch, rejection):
    args = ["-c", "print('no')"] if rejection == "arbitrary_code" else ALMOND_ARGS
    config = {"args": args, "cwd": "C:/isolated", "env": {}}
    stream = FragmentedSocket(wire(b"C", json.dumps(config).encode()))
    monkeypatch.setattr(runtime.socket, "create_connection", lambda *args, **kwargs: stream)
    monkeypatch.setattr(runtime, "os", SimpleNamespace(environ={}, chdir=lambda path: None))
    def denied():
        raise PermissionError("restricted execution context")
    def forbidden(*args, **kwargs):
        raise AssertionError("Rejected child configuration started a worker")
    monkeypatch.setattr(runtime, "_require_full_trust", denied)
    monkeypatch.setattr(runtime.subprocess, "Popen", forbidden)
    assert runtime._child(123, "a" * 64) == 1
    kind, data = runtime._read_frame(FragmentedSocket(stream.sent[64:]))
    assert kind == b"F"
    assert (b"Almond runtime entry" if rejection == "arbitrary_code" else b"restricted") in data


def test_malformed_child_input_reports_failure_and_nonzero_exit(monkeypatch):
    config = {"args": ALMOND_ARGS, "cwd": "C:/isolated", "env": {}}
    stream = FragmentedSocket(wire(b"C", json.dumps(config).encode()) + wire(b"?", b"invalid input"))
    monkeypatch.setattr(runtime.socket, "create_connection", lambda *args, **kwargs: stream)
    monkeypatch.setattr(runtime, "os", SimpleNamespace(environ={}, chdir=lambda path: None))
    monkeypatch.setattr(runtime, "_require_full_trust", lambda: None)
    monkeypatch.setattr(runtime, "redirected_library_view", lambda: False)
    closed = threading.Event()
    class Input(io.BytesIO):
        def close(self):
            super().close()
            closed.set()
    class Process:
        stdin, stdout, stderr = Input(), io.BytesIO(), io.BytesIO()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def wait(self):
            assert closed.wait(3), "Malformed input must close the actual worker stdin"
            return 0  # A clean worker exit cannot overwrite the protocol failure.
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *args, **kwargs: Process())
    assert runtime._child(123, "a" * 64) == 1
    output = FragmentedSocket(stream.sent[64:])
    kind, data = runtime._read_frame(output)
    assert kind == b"F" and b"Unexpected desktop runtime input" in data
    assert runtime._read_frame(output) == (b"X", b"1")


@pytest.mark.parametrize("ending", [wire(b"I"), b""])
def test_relay_shutdown_signals_workers_that_do_not_read_stdin(monkeypatch, ending):
    import time
    config = {"args": ["-m", "almond_mcp", "library"], "cwd": "C:/isolated", "env": {}}
    stream = FragmentedSocket(wire(b"C", json.dumps(config).encode()) + ending)
    monkeypatch.setattr(runtime.socket, "create_connection", lambda *args, **kwargs: stream)
    monkeypatch.setattr(runtime, "os", SimpleNamespace(environ={}, chdir=lambda path: None))
    monkeypatch.setattr(runtime, "_require_full_trust", lambda: None)
    monkeypatch.setattr(runtime, "redirected_library_view", lambda: False)

    class Process:
        def __init__(self, *args, env, **kwargs):
            self.stdin, self.stdout, self.stderr = io.BytesIO(), io.BytesIO(), io.BytesIO()
            self.stop = runtime._ShutdownSignal(env[runtime._STOP_EVENT_ENV])
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stop.__exit__(*args)
        def wait(self):
            deadline = time.monotonic() + 3
            while not self.stop.is_set() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert self.stop.is_set(), "Transport closure must signal a worker independently of stdin"
            return 0

    monkeypatch.setattr(runtime.subprocess, "Popen", Process)
    assert runtime._child(123, "a" * 64) == 0


def test_library_stop_signal_releases_its_listening_port(monkeypatch):
    import http.client
    from almond_mcp.features.assets import asset_repository
    server = asset_repository.create_server(0, SimpleNamespace(records={}, files={}, catalogue=lambda: {}))
    port = server.server_port
    monkeypatch.setattr(asset_repository, "create_server", lambda requested: server)
    results, failures = [], []
    with runtime._ShutdownSignal() as stop:
        monkeypatch.setenv(runtime._STOP_EVENT_ENV, stop.name)
        def serve():
            try:
                results.append(asset_repository.serve_library(port))
            except BaseException as error:
                failures.append(error)
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            connection.request("GET", "/api/catalogue")
            response = connection.getresponse()
            assert response.status == 200 and response.read() == b"{}"
            connection.close()
        finally:
            stop.set()
            thread.join(3)
        assert not thread.is_alive() and results == [0] and not failures
    with socket.socket() as replacement:
        replacement.bind(("127.0.0.1", port))
