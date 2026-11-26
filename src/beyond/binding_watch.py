"""Watch RHP binding invalidation with one blocking Windows notification thread."""
from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
from pathlib import Path
import queue
import struct
import threading


_FILE_LIST_DIRECTORY = 0x0001
_FILE_SHARE_ALL = 0x0007  # Read, write and delete.
_OPEN_EXISTING = 3
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OVERLAPPED = 0x40000000
_FILE_NOTIFY_CHANGE_FILE_NAME = 0x0001
_ERROR_NOTIFY_ENUM_DIR = 1022
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_INFINITE = 0xFFFFFFFF
_MAX_BINDINGS = 10
_BUFFER_SIZE = 16 * 1024
_NOTIFY_HEADER = struct.Struct("<III")


class _Overlapped(ctypes.Structure):
    _fields_ = [
        ("internal", ctypes.c_size_t), ("internal_high", ctypes.c_size_t),
        ("offset", wintypes.DWORD), ("offset_high", wintypes.DWORD),
        ("event", wintypes.HANDLE),
    ]


def _windows_path(path: Path) -> str:
    value = str(path.resolve())
    return value if value.startswith("\\\\?\\") else "\\\\?\\" + value


def _kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    definitions = {
        "CreateEventW": ([ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
        "SetEvent": ([wintypes.HANDLE], wintypes.BOOL),
        "ResetEvent": ([wintypes.HANDLE], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "CreateFileW": ([wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                         wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE], wintypes.HANDLE),
        "ReadDirectoryChangesW": ([wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.BOOL,
                                   wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                   ctypes.POINTER(_Overlapped), ctypes.c_void_p], wintypes.BOOL),
        "GetOverlappedResult": ([wintypes.HANDLE, ctypes.POINTER(_Overlapped),
                                 ctypes.POINTER(wintypes.DWORD), wintypes.BOOL], wintypes.BOOL),
        "CancelIoEx": ([wintypes.HANDLE, ctypes.POINTER(_Overlapped)], wintypes.BOOL),
        "WaitForMultipleObjects": ([wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
                                    wintypes.BOOL, wintypes.DWORD], wintypes.DWORD),
    }
    for name, (arguments, result) in definitions.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    return kernel


def _contains_ready(buffer, ready_name):
    offset = 0
    while offset < len(buffer):
        next_offset, _, name_length = _NOTIFY_HEADER.unpack_from(buffer, offset)
        start = offset + _NOTIFY_HEADER.size
        name = buffer[start:start + name_length].decode("utf-16-le", errors="surrogatepass")
        if name.casefold() == ready_name:
            return True
        if not next_offset:
            break
        offset += next_offset
    return False


class _DirectoryWatch:
    def __init__(self, kernel, binding):
        self.kernel = kernel
        self.ready_name = Path(binding["ready_path"]).name.casefold()
        # DWORD-aligned storage must outlive the overlapped read.
        self.buffer = (ctypes.c_uint32 * (_BUFFER_SIZE // ctypes.sizeof(ctypes.c_uint32)))()
        self.pending = False
        path = _windows_path(Path(binding["session_dir"]))
        self.directory = kernel.CreateFileW(path, _FILE_LIST_DIRECTORY, _FILE_SHARE_ALL,
                                             None, _OPEN_EXISTING,
                                             _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OVERLAPPED, None)
        if self.directory == _INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        self.event = kernel.CreateEventW(None, True, False, None)
        if not self.event:
            error = ctypes.WinError(ctypes.get_last_error())
            kernel.CloseHandle(self.directory)
            raise error
        try:
            self._arm()
        except BaseException:
            self.close()
            raise

    def _arm(self):
        self.overlapped = _Overlapped(event=self.event)
        if not self.kernel.ResetEvent(self.event):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.kernel.ReadDirectoryChangesW(self.directory, self.buffer, _BUFFER_SIZE, False,
                                                 _FILE_NOTIFY_CHANGE_FILE_NAME, None,
                                                 ctypes.byref(self.overlapped), None):
            raise ctypes.WinError(ctypes.get_last_error())
        self.pending = True

    def changed(self):
        size = wintypes.DWORD()
        ok = self.kernel.GetOverlappedResult(self.directory, ctypes.byref(self.overlapped),
                                             ctypes.byref(size), False)
        self.pending = False
        if not ok and ctypes.get_last_error() != _ERROR_NOTIFY_ENUM_DIR:
            raise ctypes.WinError(ctypes.get_last_error())

        # A lost batch needs one authoritative status check. Both sides of
        # each rename are records, so an atomic replace matches the new name.
        changed = not ok or size.value == 0 or _contains_ready(
            ctypes.string_at(self.buffer, size.value), self.ready_name)
        # Windows buffers changes between reads on the same directory handle.
        self._arm()
        return changed

    def close(self):
        if self.pending:
            # Cancellation alone does not release the buffer or OVERLAPPED.
            self.kernel.CancelIoEx(self.directory, ctypes.byref(self.overlapped))
            size = wintypes.DWORD()
            self.kernel.GetOverlappedResult(self.directory, ctypes.byref(self.overlapped),
                                             ctypes.byref(size), True)
        self.kernel.CloseHandle(self.event)
        self.kernel.CloseHandle(self.directory)


class BindingWatcher:
    """All directory handles are created/waited/closed by their sole owner thread.

    The host constructs this lazily on its first connection. No timer, recursive
    watch, extra process or third-party package is used.
    """

    def __init__(self, notify):
        self.loop = asyncio.get_running_loop()
        self.notify = notify
        self.kernel = _kernel()
        self.wake = self.kernel.CreateEventW(None, False, False, None)
        if not self.wake:
            raise ctypes.WinError(ctypes.get_last_error())
        self.commands = queue.SimpleQueue()
        self.lock = threading.Lock()
        self.closed = False
        self.failure = None
        self.joined = None
        self.thread = threading.Thread(target=self._run, name="AlmondRhino binding notifications", daemon=True)
        try:
            self.thread.start()
        except BaseException:
            self.kernel.CloseHandle(self.wake)
            raise

    def _submit(self, action, key=None, binding=None, done=None):
        with self.lock:
            if self.closed or self.failure is not None:
                raise RuntimeError("AlmondRhino binding watcher is unavailable.")
            self.commands.put((action, key, binding, done))
            self.kernel.SetEvent(self.wake)

    async def add(self, key: str, binding: dict):
        done = self.loop.create_future()
        self._submit("add", key, dict(binding), done)
        try:
            await done
        except asyncio.CancelledError:
            self._remove(key, done)
            raise

    def remove(self, key: str):
        self._remove(key)

    def _remove(self, key, registration=None):
        with self.lock:
            if not self.closed and self.failure is None:
                self.commands.put(("remove", key, None, registration))
                self.kernel.SetEvent(self.wake)

    def _finish(self, future, error=None):
        def settle():
            if not future.done():
                if error is None:
                    future.set_result(None)
                else:
                    future.set_exception(error)
        self.loop.call_soon_threadsafe(settle)

    def _run(self):
        active = {}
        kernel = self.kernel

        def remove(key, registration=None):
            entry = active.get(key)
            if entry is not None and (registration is None or entry[1] is registration):
                watch, _ = active.pop(key)
                watch.close()

        try:
            while True:
                while True:
                    try:
                        action, key, binding, done = self.commands.get_nowait()
                    except queue.Empty:
                        break
                    if action == "stop":
                        return
                    if action == "remove":
                        remove(key, done)
                        continue
                    try:
                        if key in active or len(active) >= _MAX_BINDINGS:
                            raise RuntimeError("Invalid AlmondRhino binding watch registration.")
                        active[key] = (_DirectoryWatch(kernel, binding), done)
                        # The broker checks authenticated RHP status after
                        # registration. Never open ready.json: even share-delete
                        # readers can block replacement of an open destination.
                        self._finish(done)
                    except Exception as exc:
                        self._finish(done, exc)
                keys = list(active)
                handles = (wintypes.HANDLE * (len(keys) + 1))(
                    self.wake, *(active[key][0].event for key in keys))
                signaled = kernel.WaitForMultipleObjects(len(handles), handles, False, _INFINITE)
                if signaled == 0:
                    continue
                if not 1 <= signaled <= len(keys):
                    raise ctypes.WinError(ctypes.get_last_error())
                key = keys[signaled - 1]
                try:
                    changed = active[key][0].changed()
                except OSError:
                    reason = "Binding notification failed; reconnect after checking Rhino."
                    self.loop.call_soon_threadsafe(self.notify, key, reason)
                    remove(key)
                    continue
                if changed:
                    self.loop.call_soon_threadsafe(self.notify, key, None)
        except Exception as exc:
            with self.lock:
                self.failure = exc
                while True:
                    try:
                        action, _, _, done = self.commands.get_nowait()
                    except queue.Empty:
                        break
                    if action == "add":
                        self._finish(done, RuntimeError("AlmondRhino binding notification stopped."))
            for key in active:
                self.loop.call_soon_threadsafe(self.notify, key, "Binding notification stopped; inspect Rhino.")
        finally:
            for key in list(active):
                remove(key)

    async def close(self):
        with self.lock:
            if not self.closed:
                self.closed = True
                self.commands.put(("stop", None, None, None))
                self.kernel.SetEvent(self.wake)
                self.joined = asyncio.create_task(self._join())
        try:
            await asyncio.shield(self.joined)
        finally:
            # Canceling an asyncio waiter does not cancel a Win32 wait.
            await asyncio.shield(self.joined)

    async def _join(self):
        await asyncio.to_thread(self.thread.join)
        self.kernel.CloseHandle(self.wake)
