"""Shared project data, connection generations and Windows leases.

DB and tmp belong to the model directory. A fresh token owns connection metadata;
neither a port nor a model name is a storage namespace for user data.
"""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

import argparse
import asyncio
from contextlib import ExitStack, asynccontextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import sys
import uuid

SLOTS = "ABCDEFGHIJ"
STORAGE_PROTOCOL = 2
LEGACY_LOCKS = ("launcher.lock", "rhino.lock", "mcp.lock")
LOCK_WAIT_SECONDS = 10.0


@asynccontextmanager
async def serial_gate(lock: asyncio.Lock, timeout: float = LOCK_WAIT_SECONDS):
    """Bound only queued-call waiting; an executing owner's lock is untouched."""
    try:
        await asyncio.wait_for(lock.acquire(), timeout)
    except TimeoutError as exc:
        raise TimeoutError(f"Serialization lock wait exceeded {timeout:g} seconds. No operation was started.") from exc
    try:
        yield
    finally:
        lock.release()


def project_paths(model: str | Path, *, create: bool = False) -> dict[str, str]:
    path = Path(model).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".3dm":
        raise ValueError("Select an existing saved .3dm file.")
    if path.stem.endswith(('.', ' ')):
        raise ValueError('The model name before .3dm must not end with a dot or a space.')
    if ".almond" in (part.lower() for part in path.parts):
        raise ValueError("The model must be outside .almond.")
    if sys.platform == "win32":
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor))
        if str(path).startswith("\\\\") or drive_type == 4:
            raise ValueError(read_instruction(__file__, 'response-111'))
    storage = path.parent / ".almond"
    for folder in (storage.parent, storage, storage / "tmp"):
        if folder.is_symlink() or (hasattr(folder, "is_junction") and folder.is_junction()):
            raise ValueError(".almond storage must be a real local folder, not a directory link.")
        if folder.exists() and not folder.is_dir():
            raise ValueError(f"Expected a folder: {folder}")
    if create:
        storage.mkdir(parents=True, exist_ok=True)
    return dict(model_path=str(path), project_dir=str(path.parent), storage=str(storage),
                state_db=str(storage / "DB"), temp=str(storage / "tmp"))


def connection_paths(model: str | Path, slot: str, token: str, *, create: bool = False) -> dict[str, str]:
    """Return the one shared DB/tmp and metadata owned by a single generation."""
    if not isinstance(slot, str) or len(slot) != 1 or slot not in SLOTS:
        raise ValueError("Invalid Almond slot.")
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("A connection needs a fresh 32-character lowercase UUID token.")
    locations = project_paths(model, create=create)
    storage = Path(locations["storage"])
    session = storage / ".sessions" / token
    calls = Path(locations["temp"]) / "python" / token
    for folder in (session.parent, session, calls.parent, calls):
        if folder.is_symlink() or (hasattr(folder, "is_junction") and folder.is_junction()):
            raise ValueError("Connection directories must not be directory links.")
        if folder.exists() and not folder.is_dir():
            raise ValueError(f"Expected a folder: {folder}")
    if create:
        session.parent.mkdir(parents=True, exist_ok=True)
        # A generation is never reused, even when its old lock handles are gone.
        session.mkdir(exist_ok=False)
    return dict(locations, session_dir=str(session), ready_path=str(session / "ready.json"),
                call_root=str(calls))


def read_json(path: str | Path) -> dict:
    """Read an immutable metadata snapshot without blocking Windows file replacement."""
    if sys.platform != "win32":
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
    kernel.GetFileSizeEx.restype = wintypes.BOOL
    kernel.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # READ access; share READ|WRITE|DELETE; OPEN_EXISTING. No path is created.
    handle = kernel.CreateFileW(str(path), 0x80000000, 7, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), f"Cannot read connection metadata: {path}")
    try:
        size = ctypes.c_longlong()
        if not kernel.GetFileSizeEx(handle, ctypes.byref(size)):
            raise OSError(ctypes.get_last_error(), "Cannot size connection metadata.")
        if not 0 <= size.value <= 1024 * 1024:
            raise ValueError("Connection metadata exceeds the 1 MiB limit.")
        buffer = ctypes.create_string_buffer(size.value)
        count = wintypes.DWORD()
        if not kernel.ReadFile(handle, buffer, size.value, ctypes.byref(count), None):
            raise OSError(ctypes.get_last_error(), "Cannot read connection metadata.")
        if count.value != size.value:
            raise RuntimeError("Connection metadata was truncated.")
        value = json.loads(buffer.raw.decode("utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError("Connection metadata must be an object.")
        return value
    finally:
        kernel.CloseHandle(handle)


def write_json(path: str | Path, value: dict) -> None:
    """Publish owned metadata atomically; unrelated generations use different paths."""
    path = Path(path)
    temporary = path.with_name(path.name + ".new-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class FileLease:
    """An OS-held handle. Stale files are harmless; never unlink a lock file."""
    def __init__(self, path: str | Path, *, shared: bool = False):
        if sys.platform != "win32":
            raise RuntimeError("This installation requires Windows.")
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
            wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL
        # Shared handles form a compatibility barrier against old exclusive clients.
        # They never truncate or write the legacy files, and do not permit deletion.
        handle = self._kernel.CreateFileW(str(path), 0xC0000000, 3 if shared else 0, None, 4, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError(ctypes.get_last_error(), f"Lease is in use or not writable: {path}")
        self.handle = handle

    def close(self):
        if self.handle is not None:
            self._kernel.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ExclusiveFile(FileLease):
    """One owner for a connection role or a shared DB operation."""


class SharedStorageLease:
    """Allow protocol-2 connections together while excluding old root-lock owners."""
    def __init__(self, storage: str | Path):
        self._handles = ExitStack()
        try:
            for name in LEGACY_LOCKS:
                self._handles.enter_context(FileLease(Path(storage) / name, shared=True))
        except BaseException:
            self._handles.close()
            raise

    def close(self):
        self._handles.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def process_start_ticks(pid: int) -> str:
    """Read Windows process identity without relying on a recyclable PID alone."""
    if sys.platform != "win32":
        raise RuntimeError("This installation requires Windows.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        raise RuntimeError(f"Process {pid} is no longer available.")
    try:
        exit_code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != 259:
            raise RuntimeError(f"Process {pid} has exited.")
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(item) for item in times)):
            raise OSError(ctypes.get_last_error(), "Cannot verify process creation time.")
        ticks = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        return str(ticks + 504911232000000000)
    finally:
        kernel.CloseHandle(handle)


def verify_process(binding: dict) -> None:
    if process_start_ticks(int(binding["pid"])) != str(binding["process_start_ticks"]):
        raise RuntimeError(read_instruction(__file__, 'response-107'))


def read_binding(path: str | Path, token: str) -> tuple[dict, dict]:
    path = Path(path).resolve(strict=True)
    binding = read_json(path)
    if binding.get("token") != token or binding.get("schema") != "almond-project":
        raise RuntimeError(read_instruction(__file__, 'response-108'))
    if binding.get('valid') is False:
        raise RuntimeError(read_instruction(__file__, 'response-109'))
    slot = binding.get("label")
    if not isinstance(slot, str) or len(slot) != 1 or slot not in SLOTS or binding.get("port") != 5501 + SLOTS.index(slot):
        raise RuntimeError("Invalid slot/port binding.")
    if binding.get("storage_protocol") == STORAGE_PROTOCOL:
        paths = connection_paths(binding["model_path"], slot, token)
        if path != Path(paths["ready_path"]):
            raise RuntimeError("The connection generation and metadata path do not match.")
        for field in ("storage", "temp", "session_dir", "ready_path"):
            if not binding.get(field) or Path(binding[field]).resolve() != Path(paths[field]):
                raise RuntimeError(f"Invalid connection {field}.")
        if binding.get("valid") is not True:
            raise RuntimeError("The connection has not published a valid ready state.")
    else:
        # Reading a legacy locator remains useful for maintenance. New workers
        # explicitly reject it before opening the DB; it is not a shared session.
        paths = project_paths(binding["model_path"])
        if path != Path(paths["storage"]) / "ready.json":
            raise RuntimeError(read_instruction(__file__, 'response-120'))
    return binding, paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--slot", choices=list(SLOTS))
    parser.add_argument("--token")
    args = parser.parse_args()
    try:
        if bool(args.slot) != bool(args.token):
            raise ValueError("--slot and --token must be supplied together.")
        locations = (connection_paths(args.model, args.slot, args.token, create=args.create)
                     if args.slot else project_paths(args.model, create=args.create))
        print(json.dumps(locations, ensure_ascii=True))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
