"""Start an independent GUI process only after proving it escaped every job.

Windows may only partially break away from nested jobs. Create suspended, check
membership, then resume. A rejected child has never run or opened a document.
Existing Rhino processes and terminal containment settings are never changed.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import subprocess


class StartupInfo(ctypes.Structure):
    _fields_ = [("cb", w.DWORD), ("reserved", w.LPWSTR), ("desktop", w.LPWSTR),
                ("title", w.LPWSTR), ("x", w.DWORD), ("y", w.DWORD),
                ("width", w.DWORD), ("height", w.DWORD), ("columns", w.DWORD),
                ("rows", w.DWORD), ("fill", w.DWORD), ("flags", w.DWORD),
                ("show", w.WORD), ("reserved_size", w.WORD), ("reserved_bytes", ctypes.c_void_p),
                ("stdin", w.HANDLE), ("stdout", w.HANDLE), ("stderr", w.HANDLE)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE), ("pid", w.DWORD), ("tid", w.DWORD)]


kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.CreateProcessW.argtypes = [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                 w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR,
                                 ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInfo)]
kernel.CreateProcessW.restype = w.BOOL
kernel.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
kernel.IsProcessInJob.restype = w.BOOL
kernel.GetCurrentProcess.restype = w.HANDLE
kernel.ResumeThread.argtypes = [w.HANDLE]
kernel.ResumeThread.restype = w.DWORD
kernel.TerminateProcess.argtypes = [w.HANDLE, w.UINT]
kernel.TerminateProcess.restype = w.BOOL
kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
kernel.WaitForSingleObject.restype = w.DWORD
kernel.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
kernel.GetExitCodeProcess.restype = w.BOOL
kernel.CloseHandle.argtypes = [w.HANDLE]
kernel.CloseHandle.restype = w.BOOL


def in_job(handle) -> bool:
    result = w.BOOL()
    if not kernel.IsProcessInJob(handle, None, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    return bool(result.value)


def current_process_in_job() -> bool:
    return in_job(kernel.GetCurrentProcess())


class IndependentProcess:
    def __init__(self, handle, pid):
        self.handle, self.pid, self.exit_code = handle, pid, None

    def poll(self):
        if self.handle is None:
            return self.exit_code
        state = kernel.WaitForSingleObject(self.handle, 0)
        if state == 258:  # WAIT_TIMEOUT
            return None
        if state != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = w.DWORD()
        if not kernel.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.exit_code = code.value
        self.close()
        return self.exit_code

    def close(self):
        if self.handle is not None:
            kernel.CloseHandle(self.handle)
            self.handle = None

    def __del__(self):
        self.close()  # Releasing an observation handle never terminates Rhino.


def launch_detached(args: list[str], *, cwd: str, env: dict) -> IndependentProcess:
    command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
    environment = ctypes.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(env.items())) + "\0\0")
    startup, process = StartupInfo(), ProcessInfo()
    startup.cb = ctypes.sizeof(startup)
    # DETACHED_PROCESS and no inherited handles keep MCP/ConPTY stdio private.
    # Rhino is a GUI application; its own interactive window remains visible.
    flags = 0x01000000 | 0x00000004 | 0x00000400 | 0x00000008
    if not kernel.CreateProcessW(args[0], command, None, None, False, flags,
                                 environment, cwd, ctypes.byref(startup), ctypes.byref(process)):
        error = ctypes.get_last_error()
        raise RuntimeError(f"Independent Rhino launch was refused by Windows ({error}); no Rhino was started. "
                           "Open Rhino normally and use list_connections/connect instead.")
    resumed = False
    try:
        if in_job(process.process):
            raise RuntimeError("Independent Rhino launch remains inside a parent job. No model was opened; "
                               "open Rhino normally and use list_connections/connect instead.")
        if kernel.ResumeThread(process.thread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        resumed = True
        return IndependentProcess(process.process, process.pid)
    finally:
        kernel.CloseHandle(process.thread)
        if not resumed:
            # Only our newly created, still-suspended process is discarded. It
            # has executed no Rhino code and cannot contain user model changes.
            kernel.TerminateProcess(process.process, 1)
            kernel.WaitForSingleObject(process.process, 5000)
            kernel.CloseHandle(process.process)
