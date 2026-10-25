"""Real Windows jobs must never inherit a runnable independent Rhino process.

Disposable Python children stand in for Rhino and only write fixture markers.
"""
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class Basic(ctypes.Structure):
    _fields_ = [("user", ctypes.c_int64), ("job", ctypes.c_int64), ("flags", w.DWORD),
                ("min", ctypes.c_size_t), ("max", ctypes.c_size_t), ("count", w.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]


class Limits(ctypes.Structure):
    _fields_ = [("basic", Basic), ("io", ctypes.c_uint64 * 6),
                ("memory", ctypes.c_size_t * 4)]


class DetachedProcessTests(unittest.TestCase):
    def exercise(self, *, breakaway, nested=False):
        from detached_process import kernel
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        kernel.CreateJobObjectW.restype = w.HANDLE
        kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        jobs = []
        process = None
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker, release = root / "ran.json", root / "release"
            # Wait for the parent test to place this launcher inside the job(s).
            launcher = (
                "import json, sys; from detached_process import launch_detached; "
                "sys.stdin.readline(); "
                "\ntry:\n"
                " p = launch_detached(json.loads(sys.argv[1]), cwd=sys.argv[2], env=dict(__import__('os').environ))\n"
                " print(json.dumps({'pid':p.pid}), flush=True)\n"
                "except Exception as e: print(json.dumps({'error':str(e)}), flush=True)\n"
                "sys.stdin.readline()"
            )
            child = (
                "import json, os, pathlib, time; "
                "from detached_process import current_process_in_job; "
                f"p=pathlib.Path({str(marker)!r}); end=pathlib.Path({str(release)!r}); "
                "p.write_text(json.dumps({'pid':os.getpid(),'in_job':current_process_in_job()})); "
                "deadline=time.monotonic()+8\n"
                "while not end.exists() and time.monotonic()<deadline: time.sleep(.02)\n"
                "p.with_suffix('.done').touch()"
            )
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            try:
                # Bypass the venv redirector, which itself launches another
                # interpreter and creates a separate lifetime job.
                process = subprocess.Popen([sys._base_executable, "-B", "-c", launcher,
                                            json.dumps([sys._base_executable, "-B", "-c", child]), str(root)],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                # The outer restrictive job tests partial breakaway from a nested job.
                flags = ([0x2000, 0x2000 | 0x800] if nested else [0x2000 | (0x800 if breakaway else 0)])
                for flag in flags:
                    job = kernel.CreateJobObjectW(None, None)
                    self.assertTrue(job)
                    jobs.append(job)
                    limits = Limits()
                    limits.basic.flags = flag
                    self.assertTrue(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
                    self.assertTrue(kernel.AssignProcessToJobObject(job, int(process._handle)))
                process.stdin.write("go\n")
                process.stdin.flush()
                import queue
                import threading
                lines = queue.Queue()
                threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
                result = json.loads(lines.get(timeout=5))
                if not breakaway or nested:
                    self.assertIn("error", result)
                    self.assertFalse(marker.exists(), "Child instructions ran inside a terminating job")
                else:
                    if "remains inside a parent job" in result.get("error", ""):
                        self.skipTest("The test runner's outer job forbids complete breakaway; no child code ran")
                    self.assertIn("pid", result)
                    import time
                    deadline = time.monotonic() + 5
                    while not marker.exists() and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertFalse(json.loads(marker.read_text())["in_job"])
                for job in reversed(jobs):
                    kernel.CloseHandle(job)
                jobs.clear()
                process.wait(timeout=5)
                if breakaway and not nested:
                    release.touch()
                    deadline = time.monotonic() + 5
                    while not marker.with_suffix('.done').exists() and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertTrue(marker.with_suffix('.done').exists(), "Independent child died when launcher job closed")
            finally:
                release.touch()
                for job in reversed(jobs):
                    kernel.CloseHandle(job)
                if process is not None:
                    if process.poll() is None:
                        process.communicate("exit\n", timeout=5)
                    for stream in (process.stdin, process.stdout, process.stderr):
                        stream.close()

    def test_restrictive_job_refuses_before_any_child_code_runs(self):
        self.exercise(breakaway=False)

    def test_breakaway_child_survives_launcher_job_close(self):
        self.exercise(breakaway=True)

    def test_nested_outer_job_refuses_before_any_child_code_runs(self):
        self.exercise(breakaway=True, nested=True)
