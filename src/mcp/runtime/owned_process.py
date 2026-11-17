"""Publish exact process ownership before admitting an external command.

The supervisor persists its own identity, then waits for the owning parent's
matching authorization. Its Windows job kills only its own CLI descendants if
the supervisor dies. Native completion is a separate caller-owned condition.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import time

from project import process_start_ticks, read_json, write_json


def child_process_identity(process):
    """The owned Windows handle remains valid even after a very fast exit."""
    if sys.platform != "win32":
        return dict(pid=process.pid, process_start_ticks=process_start_ticks(process.pid))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    values = [wintypes.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(int(process._handle), *(ctypes.byref(value) for value in values)):
        raise ctypes.WinError(ctypes.get_last_error())
    ticks = ((values[0].dwHighDateTime << 32) | values[0].dwLowDateTime) + 504911232000000000
    return dict(pid=process.pid, process_start_ticks=str(ticks))


def _read_owned(directory, name, owner):
    path = Path(directory) / name
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("Owned process evidence cannot use filesystem links.")
    if path.stat().st_size > 65536:
        raise ValueError("Owned process record exceeds its size limit.")
    value = read_json(path)
    if value.get("schema") != "almond-owned-process" or value.get("owner") != owner:
        raise ValueError("Process record does not match the exact request owner.")
    return value


def read_owned_identity(directory, owner):
    child = _read_owned(directory, "child.json", owner).get("child")
    if (not isinstance(child, dict) or type(child.get("pid")) is not int or child["pid"] <= 0
            or not isinstance(child.get("process_start_ticks"), str)
            or not child["process_start_ticks"].isascii() or not child["process_start_ticks"].isdecimal()
            or not 0 < int(child["process_start_ticks"]) <= 0x7fffffffffffffff):
        raise ValueError("Invalid owned process identity.")
    return child


def read_owned_exit(directory, owner):
    return _read_owned(directory, "child-exit.json", owner)


def launch_owned(argv, directory, owner, *, cwd=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    directory = Path(directory).absolute()
    request = directory / "launch.json"
    write_json(request, {"schema": "almond-owned-process", "owner": owner,
                         "argv": list(argv), "cwd": cwd})
    # Windows venv python.exe can be a redirector with a different PID from the
    # executing interpreter. Start the interpreter itself and retain this exact
    # environment's module paths so handle identity equals self-published PID.
    interpreter = getattr(sys, "_base_executable", sys.executable)
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join(os.path.abspath(entry) for entry in sys.path))
    return subprocess.Popen([interpreter, "-B", str(Path(__file__).absolute()), str(request)],
        cwd=cwd, shell=False, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
        env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)


def authorize_owned(process, directory, owner):
    expected = child_process_identity(process)
    deadline = time.monotonic() + 5
    while True:
        try:
            child = read_owned_identity(directory, owner)
            if child != expected:
                raise ValueError("Launch acknowledgement does not match the owned process handle.")
            write_json(Path(directory) / "dispatch.json", {"schema": "almond-owned-process",
                       "owner": owner, "child": child})
            return child
        except FileNotFoundError:
            if process.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError("The child did not publish its identity; no command was authorized.")
            time.sleep(.01)


def _own_windows_job():
    """An inherited host job is preserved; Windows supports nested jobs."""
    if sys.platform != "win32":
        return None
    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]
    class Counters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount",
            "WriteTransferCount", "OtherTransferCount")]
    class Limits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", Counters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = Limits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if (not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
            or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess())):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel.CloseHandle(job)
        raise error
    # Keep the non-inherited handle until process exit. Closing it deliberately
    # would terminate this supervisor as well as its exclusively owned child.
    return job


def _run(request_path):
    request = read_json(request_path)
    directory, owner = request_path.parent, request["owner"]
    child = {"pid": os.getpid(), "process_start_ticks": process_start_ticks(os.getpid())}
    record = {"schema": "almond-owned-process", "owner": owner, "child": child}
    dispatched = False
    try:
        write_json(directory / "child.json", record)
        job = _own_windows_job()
        deadline = time.monotonic() + 10
        while True:
            try:
                admission = _read_owned(directory, "dispatch.json", owner)
                if admission.get("child") != child:
                    raise ValueError("Dispatch authorization belongs to another process.")
                break
            except FileNotFoundError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("The owning parent did not authorize dispatch.")
                time.sleep(.01)
        process = subprocess.Popen(request["argv"], cwd=request["cwd"], shell=False,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        dispatched = True
        code = process.wait()
        write_json(directory / "child-exit.json", dict(record, dispatched=True, exit_code=code))
        return code
    except Exception as exc:
        write_json(directory / "child-exit.json", dict(record, dispatched=dispatched, error=str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(_run(Path(sys.argv[1]).absolute()))
