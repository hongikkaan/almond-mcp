"""Current-user Windows message pipes using the standard library, never pickle."""
from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import time

FILETIME_TO_TICKS = 504911232000000000


def process_identity(pid: int) -> dict:
    if os.name != "nt":
        raise RuntimeError("AlmondRhino requires Windows.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise OSError(ctypes.get_last_error(), "Process is unavailable.")
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            raise OSError(ctypes.get_last_error(), "Cannot verify process start.")
        started = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        return {"pid": pid, "process_start_ticks": str(started + FILETIME_TO_TICKS)}
    finally:
        kernel.CloseHandle(handle)


class ControlError(RuntimeError):
    pass


class PipeControl:
    """One ordered persistent control connection; JSON is bounded on both ends."""

    def __init__(self, record: dict, timeout: float = 25.0):
        self.record = record
        self.timeout = timeout
        self.connection = None
        self.lock = asyncio.Lock()
        self.serial = 0

    def _open(self):
        from multiprocessing.connection import Client
        identity = process_identity(int(self.record["pid"]))
        if identity["process_start_ticks"] != str(self.record["process_start_ticks"]):
            raise ControlError("The advertised Rhino process has changed.")
        pipe = self.record["pipe"]
        expected = f"AlmondRhino-{identity['pid']}-"
        if not isinstance(pipe, str) or not pipe.startswith(expected) or any(c in pipe for c in "\\/"):
            raise ControlError("Invalid AlmondRhino pipe address.")
        deadline = time.monotonic() + min(self.timeout, 3.0)
        while True:
            try:
                connection = Client("\\\\.\\pipe\\" + pipe, family="AF_PIPE", authkey=None)
                break
            except FileNotFoundError:
                # The server replaces its pipe instance after EOF; discovery can
                # also become visible just before its first listener is ready.
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
        try:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
            kernel.GetNamedPipeServerProcessId.restype = wintypes.BOOL
            owner = wintypes.ULONG()
            if not kernel.GetNamedPipeServerProcessId(connection.fileno(), ctypes.byref(owner)):
                raise ControlError("Cannot verify Rhino control pipe owner.")
            if owner.value != identity["pid"] or process_identity(owner.value) != identity:
                raise ControlError("Rhino control pipe owner changed.")
            self.connection = connection
        except BaseException:
            connection.close()
            raise

    def _exchange(self, request: dict):
        if self.connection is None:
            self._open()
        payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
        if len(payload) > 8192:
            raise ControlError("Control message exceeds 8 KiB.")
        try:
            self.connection.send_bytes(payload)
            if not self.connection.poll(self.timeout):
                raise TimeoutError("Rhino control response timed out.")
            response = json.loads(self.connection.recv_bytes(65536))
            if response.get("id") != request["id"]:
                raise ControlError("Rhino control response ID mismatch.")
        except BaseException:
            self.connection.close()
            self.connection = None
            raise
        if response.get("ok") is not True:
            raise ControlError(response.get("error", "Rhino control request failed."))
        return response["result"]

    async def request(self, action: str, **fields):
        async with self.lock:
            self.serial += 1
            request = dict(fields, id=self.serial, action=action, access_token=self.record["access_token"])
            task = asyncio.create_task(asyncio.to_thread(self._exchange, request))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # Do not abandon a late-opened pipe or overlap the next exchange.
                try:
                    await asyncio.shield(task)
                finally:
                    raise

    async def close(self):
        async with self.lock:
            if self.connection is not None:
                self.connection.close()
                self.connection = None


def read_hosts(data: Path) -> list[dict]:
    records = []
    for path in sorted((data / "hosts").glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
            if record.get("schema") != "almond-rhino-host" or record.get("protocol") != 1:
                continue
            if path.stem != record.get("host_id"):
                continue
            identity = process_identity(int(record["pid"]))
            if identity["process_start_ticks"] == str(record["process_start_ticks"]):
                records.append(record)
        except (OSError, ValueError, KeyError, TypeError):
            # Dead discovery records do not authorize cleanup of any process/file.
            continue
    return records
