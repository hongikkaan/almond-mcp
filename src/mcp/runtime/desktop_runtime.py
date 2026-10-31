"""Keep Windows desktop libraries shared with Rhino under packaged launchers.

MSIX descendants can see private AppData copies even without a package identity.
Only that detected file-view mismatch uses a normal Windows process. The relay
preserves stdio, environment and exit status; it never starts or closes Rhino.
"""
from __future__ import annotations

import base64
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time

_MAX_FRAME = 1024 * 1024
_STOP_EVENT_ENV = "ALMOND_DESKTOP_STOP_EVENT"


class _ShutdownSignal:
    """Named Windows event for runtimes which do not consume stdio (HTTP)."""

    def __init__(self, name=None):
        import ctypes
        from ctypes import wintypes as w
        self.name = name or "Local\\AlmondDesktop-" + secrets.token_hex(32)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateEventW.argtypes = [ctypes.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
        self.kernel.CreateEventW.restype = w.HANDLE
        self.kernel.OpenEventW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        self.kernel.OpenEventW.restype = w.HANDLE
        self.kernel.SetEvent.argtypes = [w.HANDLE]
        self.kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.handle = (self.kernel.OpenEventW(0x00100000, False, self.name) if name
                       else self.kernel.CreateEventW(None, True, False, self.name))
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.kernel.CloseHandle(self.handle)

    def set(self):
        if not self.kernel.SetEvent(self.handle):
            import ctypes
            raise ctypes.WinError(ctypes.get_last_error())

    def is_set(self):
        result = self.kernel.WaitForSingleObject(self.handle, 0)
        if result not in (0, 258):  # WAIT_OBJECT_0 / WAIT_TIMEOUT
            import ctypes
            raise ctypes.WinError(ctypes.get_last_error())
        return result == 0


def serve_until_desktop_exit(server):
    """Allow an HTTP CLI to finish without depending on stdin or console signals."""
    with _ShutdownSignal(os.environ[_STOP_EVENT_ENV]) as stop:
        server.timeout = 0.25
        while not stop.is_set():
            server.handle_request()


def _require_full_trust():
    """This bootstrap is not a way out of a restricted token or AppContainer."""
    import ctypes
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    security.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    security.IsTokenRestricted.argtypes = [w.HANDLE]
    security.IsTokenRestricted.restype = w.BOOL
    security.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            w.DWORD, ctypes.POINTER(w.DWORD)]
    token = w.HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        container, size = w.DWORD(), w.DWORD()
        if not security.GetTokenInformation(token, 29, ctypes.byref(container), 4, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        if security.IsTokenRestricted(token) or container.value:
            raise PermissionError("The shared-library runtime cannot leave a restricted execution context. Start Almond through its authorized desktop MCP registration.")
    finally:
        kernel.CloseHandle(token)


def _validate_args(args):
    """Only existing Almond CLI entries may cross the desktop file-view boundary."""
    if not isinstance(args, list) or any(not isinstance(arg, str) or "\0" in arg for arg in args):
        raise ValueError("Invalid Almond runtime arguments.")
    command = list(args)
    while command and command[0].startswith("-") and command[0] != "-m":
        flag = command.pop(0)
        if flag in ("-B", "-u", "-Xutf8"):
            continue
        if flag == "-X" and command and command.pop(0) == "utf8":
            continue
        raise ValueError("Only Almond runtime entry points can use the desktop bootstrap.")
    if len(command) >= 2 and command[0] == "-m" and command[1] in (
            "almond_mcp", "almond_mcp.cli", "almond_mcp.features.assets.asset_repository"):
        return
    source = Path(__file__).resolve().parents[2]
    allowed = {source / "cos/codex_host.py", source / "cos/cos_host.py",
               source / "mcp/runtime/mcp_server.py"}
    if command and not command[0].startswith("-") and Path(command[0]).resolve() in allowed:
        return
    raise ValueError("Only Almond runtime entry points can use the desktop bootstrap.")


def redirected_library_view() -> bool:
    """Test the actual file view, not package identity or a directory alias.

    Explicit libraries outside LocalAppData are left alone. The unique probe is
    removed immediately and never reads or changes a library manifest.
    """
    if sys.platform != "win32":
        return False
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    selected = [v for k, v in os.environ.items()
                if k.startswith("RHINO_MCP_") and k.endswith("_DIR") and v]
    # With every library explicitly selected outside AppData (offline tests),
    # no desktop library is involved and no process boundary is needed.
    from almond_mcp.paths import LIBRARY_DIRS
    if all(os.environ.get(k) for k in LIBRARY_DIRS) and all(
            not Path(v).is_relative_to(local) for v in selected):
        return False
    root = local / "Almond"
    root.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix=".file-view-", dir=root)
    os.close(fd)
    probe = Path(filename)
    try:
        actual = probe.resolve(strict=True)
        expected = Path(os.path.abspath(probe))
        if os.path.normcase(str(actual)) == os.path.normcase(str(expected)):
            return False
        # Do not mistake a user-selected symlink or redirected profile for MSIX.
        relative = actual.relative_to(local / "Packages")
        parts = relative.parts
        return len(parts) >= 4 and parts[1:3] == ("LocalCache", "Local")
    except ValueError:
        return False
    finally:
        probe.unlink()


def _receive(sock, count):
    result = bytearray()
    while len(result) < count:
        block = sock.recv(count - len(result))
        if not block:
            raise EOFError("Desktop runtime connection closed.")
        result.extend(block)
    return bytes(result)


def _read_frame(sock):
    size = struct.unpack("!I", _receive(sock, 4))[0]
    if not 1 <= size <= _MAX_FRAME:
        raise ValueError("Invalid desktop runtime frame size.")
    payload = _receive(sock, size)
    return payload[:1], payload[1:]


def _send_frame(sock, lock, kind, data=b""):
    payload = kind + data
    if len(payload) > _MAX_FRAME:
        raise ValueError("Desktop runtime frame exceeded its limit.")
    with lock:
        sock.sendall(struct.pack("!I", len(payload)) + payload)


def _launch_reader(port: int, token: str) -> int:
    """WMI creates an ordinary same-user process without changing registrations.

    No environment values, model/session arguments or credentials enter the
    PowerShell command. They travel only over the authenticated loopback stream.
    """
    command = subprocess.list2cmdline([
        sys.executable, "-B", str(Path(__file__).resolve()), "--relay-child",
        str(port), token,
    ])
    encoded_command = base64.b64encode(command.encode("utf-8")).decode("ascii")
    script = (
        "$ErrorActionPreference='Stop'; "
        "$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}; "
        "$c=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + encoded_command + "')); "
        "$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
        "-Arguments @{CommandLine=$c;ProcessStartupInformation=$s}; "
        "$r | Select-Object ReturnValue,ProcessId | ConvertTo-Json -Compress"
    )
    shell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    completed = subprocess.run(
        [str(shell), "-NoProfile", "-NonInteractive", "-EncodedCommand",
         base64.b64encode(script.encode("utf-16-le")).decode("ascii")],
        capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if completed.returncode:
        raise RuntimeError("Windows could not start the shared-library runtime (WMI). No library was changed.")
    reply = json.loads(completed.stdout.decode("utf-8-sig"))
    if reply.get("ReturnValue") != 0 or not reply.get("ProcessId"):
        raise RuntimeError("Windows refused the shared-library runtime: " + str(reply.get("ReturnValue")))
    return int(reply["ProcessId"])


def run_desktop(args: list[str], *, stdin=None, stdout=None, stderr=None) -> int:
    """Run this Python with its original arguments in the ordinary desktop view."""
    _validate_args(args)
    _require_full_trust()
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout.buffer if stdout is None else stdout
    stderr = sys.stderr.buffer if stderr is None else stderr
    token = secrets.token_hex(32)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(4)
        _launch_reader(listener.getsockname()[1], token)
        deadline = time.monotonic() + 20
        while True:
            listener.settimeout(max(0.01, deadline - time.monotonic()))
            connection, _ = listener.accept()
            connection.settimeout(max(0.01, deadline - time.monotonic()))
            try:
                if hmac.compare_digest(_receive(connection, 64), token.encode("ascii")):
                    break
            except (OSError, EOFError):
                pass
            connection.close()
            if time.monotonic() >= deadline:
                raise TimeoutError("Desktop runtime authentication timed out.")
        with connection:
            connection.settimeout(None)
            lock = threading.Lock()
            _send_frame(connection, lock, b"C", json.dumps({
                "args": args, "cwd": os.getcwd(), "env": dict(os.environ),
            }, ensure_ascii=False).encode("utf-8"))

            def input_loop():
                try:
                    try:
                        descriptor = stdin.fileno()
                    except (AttributeError, OSError):
                        descriptor = None
                    while True:
                        # Do not hold Python's buffered stdin lock in a daemon
                        # when a child fails before its MCP client sends EOF.
                        data = os.read(descriptor, 65536) if descriptor is not None else stdin.read(65536)
                        _send_frame(connection, lock, b"I", data)
                        if not data:
                            return
                except (OSError, ValueError):
                    # Closing the transport delivers EOF to the actual runtime.
                    try:
                        connection.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass

            threading.Thread(target=input_loop, daemon=True).start()
            while True:
                kind, data = _read_frame(connection)
                if kind in (b"O", b"E"):
                    stream = stdout if kind == b"O" else stderr
                    stream.write(data)
                    stream.flush()
                elif kind == b"X":
                    return int(data.decode("ascii"))
                elif kind == b"F":
                    raise RuntimeError(data.decode("utf-8"))
                else:
                    raise ValueError("Unexpected desktop runtime message.")


def ensure_desktop_runtime(args: list[str] | None = None) -> None:
    """Call before leases, databases, library caches or MCP stdio are opened."""
    if redirected_library_view():
        raise SystemExit(run_desktop(sys.orig_argv[1:] if args is None else args))


def _child(port: int, token: str) -> int:
    with socket.create_connection(("127.0.0.1", port), timeout=20) as connection:
        connection.sendall(token.encode("ascii"))
        kind, raw = _read_frame(connection)
        if kind != b"C":
            raise ValueError("Desktop runtime configuration was not received.")
        config = json.loads(raw)
        os.environ.clear()
        os.environ.update(config["env"])
        os.chdir(config["cwd"])
        connection.settimeout(None)
        lock = threading.Lock()
        try:
            _validate_args(config["args"])
            _require_full_trust()
        except (ValueError, OSError) as error:
            _send_frame(connection, lock, b"F", str(error).encode("utf-8"))
            return 1
        if redirected_library_view():
            _send_frame(connection, lock, b"F", b"Windows still redirects the shared library. No worker or library mutation was started.")
            return 1
        with _ShutdownSignal() as stop, subprocess.Popen([sys.executable, *config["args"]], cwd=config["cwd"],
                              env={**config["env"], _STOP_EVENT_ENV: stop.name}, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW) as process:
            protocol_failed = threading.Event()
            def input_loop():
                try:
                    while True:
                        kind, data = _read_frame(connection)
                        if kind != b"I":
                            raise ValueError("Unexpected desktop runtime input.")
                        if not data:
                            break
                        process.stdin.write(data)
                        process.stdin.flush()
                except ValueError as error:
                    protocol_failed.set()
                    try:
                        _send_frame(connection, lock, b"F", str(error).encode("utf-8"))
                    except OSError:
                        pass
                except (EOFError, OSError):
                    pass
                finally:
                    # HTTP library servers do not read stdin. Notify them before
                    # closing it; MCP still follows its existing EOF cleanup.
                    stop.set()
                    try:
                        process.stdin.close()
                    except OSError:
                        pass

            def output_loop(stream, kind):
                try:
                    while data := stream.read1(65536):
                        _send_frame(connection, lock, kind, data)
                except OSError:
                    # Keep draining until the existing runtime handles stdin EOF.
                    while stream.read1(65536):
                        pass

            input_thread = threading.Thread(target=input_loop, daemon=True)
            input_thread.start()
            outputs = [threading.Thread(target=output_loop, args=(stream, kind), daemon=True)
                       for stream, kind in ((process.stdout, b"O"), (process.stderr, b"E"))]
            for thread in outputs:
                thread.start()
            code = process.wait()
            # The child can finish before its client sends EOF (e.g. --help).
            # Finish the input watcher before disposing its shutdown event.
            try:
                connection.shutdown(socket.SHUT_RD)
            except OSError:
                pass
            input_thread.join()
            for thread in outputs:
                thread.join()
            if protocol_failed.is_set():
                code = 1
            try:
                _send_frame(connection, lock, b"X", str(code).encode("ascii"))
            except OSError:
                pass
            return code


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--relay-child":
        raise SystemExit(_child(int(sys.argv[2]), sys.argv[3]))
    raise SystemExit("This is an internal Almond desktop bootstrap, not a general process launcher.")
