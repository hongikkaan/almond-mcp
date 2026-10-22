"""Watch RHP binding invalidation with one blocking Windows notification thread."""
from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
from pathlib import Path
import queue
import threading


def _windows_path(path: Path) -> str:
    value = str(path.resolve())
    return value if value.startswith("\\\\?\\") else "\\\\?\\" + value


def _kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    definitions = {
        "CreateEventW": ([ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
        "SetEvent": ([wintypes.HANDLE], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "FindFirstChangeNotificationW": ([wintypes.LPCWSTR, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        "FindNextChangeNotification": ([wintypes.HANDLE], wintypes.BOOL),
        "FindCloseChangeNotification": ([wintypes.HANDLE], wintypes.BOOL),
        "WaitForMultipleObjects": ([wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
                                    wintypes.BOOL, wintypes.DWORD], wintypes.DWORD),
    }
    for name, (arguments, result) in definitions.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    return kernel


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
        self.thread = threading.Thread(target=self._run, name="AlmondCOS binding notifications", daemon=True)
        try:
            self.thread.start()
        except BaseException:
            self.kernel.CloseHandle(self.wake)
            raise

    def _submit(self, action, key=None, binding=None, done=None):
        with self.lock:
            if self.closed or self.failure is not None:
                raise RuntimeError("AlmondCOS binding watcher is unavailable.")
            self.commands.put((action, key, binding, done))
            self.kernel.SetEvent(self.wake)

    async def add(self, key: str, binding: dict):
        done = self.loop.create_future()
        self._submit("add", key, dict(binding), done)
        await asyncio.shield(done)

    def remove(self, key: str):
        with self.lock:
            if not self.closed and self.failure is None:
                self.commands.put(("remove", key, None, None))
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

        def remove(key):
            entry = active.pop(key, None)
            if entry is not None:
                kernel.FindCloseChangeNotification(entry[1])

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
                        remove(key)
                        continue
                    try:
                        if key in active or len(active) >= 10:
                            raise RuntimeError("Invalid AlmondCOS binding watch registration.")
                        # RHP Save() atomically renames a temporary file onto
                        # ready.json. Watch only file-name changes in its parent.
                        path = _windows_path(Path(binding["session_dir"]))
                        handle = kernel.FindFirstChangeNotificationW(path, False, 0x1)
                        if handle == ctypes.c_void_p(-1).value:
                            raise ctypes.WinError(ctypes.get_last_error())
                        active[key] = (binding, handle)
                        # The broker checks authenticated RHP status after
                        # registration. Never open ready.json: even share-delete
                        # readers can block replacement of an open destination.
                        self._finish(done)
                    except Exception as exc:
                        remove(key)
                        self._finish(done, exc)
                keys = list(active)
                handles = (wintypes.HANDLE * (len(keys) + 1))(
                    self.wake, *(active[key][1] for key in keys))
                signaled = kernel.WaitForMultipleObjects(len(handles), handles, False, 0xFFFFFFFF)
                if signaled == 0:
                    continue
                if not 1 <= signaled <= len(keys):
                    raise ctypes.WinError(ctypes.get_last_error())
                key = keys[signaled - 1]
                binding, handle = active[key]
                # Re-arm before notifying so a concurrent replacement is seen.
                if not kernel.FindNextChangeNotification(handle):
                    reason = "Binding notification failed; reconnect after checking Rhino."
                    self.loop.call_soon_threadsafe(self.notify, key, reason)
                    remove(key)
                else:
                    self.loop.call_soon_threadsafe(self.notify, key, None)
        except Exception as exc:
            with self.lock:
                self.failure = exc
                while True:
                    try:
                        _, _, _, done = self.commands.get_nowait()
                    except queue.Empty:
                        break
                    if done is not None:
                        self._finish(done, RuntimeError("AlmondCOS binding notification stopped."))
            for key in active:
                self.loop.call_soon_threadsafe(self.notify, key, "Binding notification stopped; inspect Rhino.")
        finally:
            for key in list(active):
                remove(key)

    async def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.commands.put(("stop", None, None, None))
            self.kernel.SetEvent(self.wake)
        joined = asyncio.create_task(asyncio.to_thread(self.thread.join))
        try:
            await asyncio.shield(joined)
        finally:
            # Canceling an asyncio waiter does not cancel a Win32 wait.
            await asyncio.shield(joined)
            self.kernel.CloseHandle(self.wake)
