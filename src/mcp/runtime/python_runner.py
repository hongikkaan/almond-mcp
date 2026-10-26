"""Bounded Python output and an owned Windows process tree, without script files."""
import ctypes
from ctypes import wintypes as w
import json
import os
import subprocess
import sys
import threading


class _BasicLimits(ctypes.Structure):
    _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                ("flags", w.DWORD), ("minimum", ctypes.c_size_t), ("maximum", ctypes.c_size_t),
                ("active", w.DWORD), ("affinity", ctypes.c_size_t),
                ("priority", w.DWORD), ("scheduling", w.DWORD)]


class _Limits(ctypes.Structure):
    _fields_ = [("basic", _BasicLimits), ("io", ctypes.c_uint64 * 6), ("memory", ctypes.c_size_t * 4)]


def run_python(code: str, directory, timeout: int, output_limit: int = 200000) -> dict:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    process = None
    readers = []
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = [False]
    timed_out = False
    try:
        limits = _Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        # The venv redirector may spawn a different Python PID. The real child
        # announces itself, then waits until its lifetime job is assigned before
        # receiving any user code. Descendants inherit this non-breakaway job.
        bootstrap = "import os,sys,json; print(os.getpid(),flush=True); exec(compile(json.loads(sys.stdin.read()),'<project-python>','exec'))"
        process = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-c", bootstrap],
            cwd=directory, env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)
        # A startup watchdog also covers a broken interpreter before its handshake.
        watchdog = threading.Timer(timeout, process.kill)
        watchdog.start()
        try:
            line = process.stdout.readline(64)
            child = kernel.OpenProcess(0x0100 | 0x0001, False, int(line))
            if not child:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not kernel.AssignProcessToJobObject(job, child):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                kernel.CloseHandle(child)
        finally:
            watchdog.cancel()

        def drain(name, pipe):
            while chunk := pipe.read(8192):
                available = max(0, output_limit - len(streams[name]))
                streams[name].extend(chunk[:available])
                if len(chunk) > available:
                    truncated[0] = True

        for name in streams:
            reader = threading.Thread(target=drain, args=(name, getattr(process, name)), daemon=True)
            reader.start()
            readers.append(reader)
        process.stdin.write(json.dumps(code).encode("utf-8"))
        process.stdin.close()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
    finally:
        kernel.CloseHandle(job)  # also stops children left behind by completed code
        if process is not None:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            for reader in readers:
                reader.join()
            process.stdout.close()
            process.stderr.close()
    return {"status": "error" if timed_out or process.returncode else "success",
            "exit_code": process.returncode, "timed_out": timed_out,
            **{name: data.decode("utf-8", errors="replace") for name, data in streams.items()},
            "output_truncated": truncated[0]}
