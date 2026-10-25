"""Explicitly open a new Rhino, then reuse its existing COS attach protocol.

No model save, kill, worker, DB, slot allocator, or native policy lives here.
The existing AlmondCOS RHP owns those leases and allocates its A-J slot when
the broker connects. This module is imported only for a start_session call.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from runtime import ENGINE
from winpipe import process_identity, read_hosts
from detached_process import launch_detached


class RhinoStart:
    def __init__(self, model_path: str, data: Path, *,
                 settings_path: Path = ENGINE / "settings.json",
                 process_factory=launch_detached, identity_reader=process_identity,
                 host_reader=read_hosts, timeout: float = 300, poll_interval: float = 0.25):
        if not Path(model_path).is_absolute():
            raise ValueError("model_path must be an absolute path to an existing saved local .3dm.")
        sys.path.insert(0, str(ENGINE))
        from project import project_paths
        # Existing runtime validation rejects missing, remote and storage paths.
        # Do not create .almond or touch a DB until the RHP attaches this model.
        project = project_paths(model_path, create=False)
        self.model_path = project["model_path"]
        config = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        executable = Path(config["rhino_exe"])
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError("Rhino executable is missing. Check runtime/settings.json before starting a session.")
        self.data, self.host_reader, self.identity_reader = data, host_reader, identity_reader
        self.timeout, self.poll_interval = timeout, poll_interval
        environment = dict(os.environ)
        for key in ("ALMOND_SESSION_FOLDER", "ALMOND_SESSION_TOKEN", "ALMONDCOS_SESSION_TOKEN",
                    "ALMOND_ISOLATED_RUN", "ALMOND_V2_RUN", "ALMOND_V3_SESSION"):
            environment.pop(key, None)
        # The launcher verifies complete job breakaway before Rhino can execute;
        # ending a Terminal/client job must never terminate this separate Rhino.
        self.process = process_factory(
            [str(executable), project["model_path"], "/nosplash", "/runscript=_AlmondCOS"],
            cwd=project["project_dir"], env=environment,
        )
        try:
            self.identity = identity_reader(self.process.pid)
        except Exception as exc:
            raise RuntimeError(f"Started Rhino PID {self.process.pid}, but could not verify its identity. Inspect that window; do not automatically start another Rhino.") from exc

    async def discover(self):
        """Repeatable observation of this one process; never relaunch on delay."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout
        while True:
            if self.process.poll() is not None:
                raise RuntimeError(f"Rhino PID {self.identity['pid']} exited before its COS advertisement was confirmed. No replacement was started.")
            if self.identity_reader(self.process.pid) != self.identity:
                raise RuntimeError("Rhino process identity changed. No other Rhino was adopted.")
            matches = [record for record in self.host_reader(self.data)
                       if record.get("pid") == self.identity["pid"]
                       and str(record.get("process_start_ticks")) == self.identity["process_start_ticks"]]
            if len(matches) > 1:
                raise RuntimeError("Multiple COS advertisements identify the new Rhino; inspect its plugin registration.")
            if matches:
                return matches[0]
            if loop.time() >= deadline:
                raise TimeoutError("Check the new Rhino window for startup dialogs and the AlmondCOS registration. Rhino remains open.")
            await asyncio.sleep(self.poll_interval)
