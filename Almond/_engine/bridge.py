# -*- coding: utf-8 -*-
"""Rhino 8 / IronPython bridge lifecycle helper, used by rhino_start.py.

Reuse the installed PUBLIC BridgeServer; do not replace its TCP/request loop.
No source/DLL patch, no TCP health-check payload, no document editing calls.
Private _running/_listenerThread fields are READ ONLY lifecycle observations.
The public C# transport is reused without editing the installed plugin.
"""
from __future__ import print_function

STICKY_KEY = "Almond.extra_bridge"


class BridgeManager(object):
    """Small lifecycle controller; backend injection permits regression tests."""

    def __init__(self, sticky, backend, startup_timeout=5.0, stop_timeout=2.0):
        self.sticky = sticky
        self.backend = backend
        self.startup_timeout = startup_timeout
        self.stop_timeout = stop_timeout

    def record(self):
        record = self.sticky.get(STICKY_KEY)
        if record is not None and (not isinstance(record, dict) or
                                  not all(k in record for k in ("port", "bridge", "phase"))):
            raise RuntimeError("Unknown bridge record. Restart Rhino; no record was discarded.")
        return record

    def healthy(self, record):
        running, alive = self.backend.state(record["bridge"])
        if not (running and alive and self.backend.listening(record["port"])):
            return False
        # Do not confuse another process's listener with this Rhino's listener.
        if self.backend.owners(record["port"]) != set([self.backend.pid]):
            return False
        running, alive = self.backend.state(record["bridge"])
        return bool(running and alive and self.backend.listening(record["port"]))

    def cleanup(self, record):
        """Do not lose the object while Stop() is still asynchronous."""
        record["phase"] = "cleanup_pending"
        self.backend.stop(record["bridge"])
        deadline = self.backend.now() + self.stop_timeout
        while True:
            _running, alive = self.backend.state(record["bridge"])
            if not alive:
                # A dead thread alone is insufficient if its socket remains open.
                still_owned = (self.backend.listening(record["port"]) and
                               self.backend.pid in self.backend.owners(record["port"]))
                if not still_owned:
                    if hasattr(self.backend, "dispose"):
                        self.backend.dispose(record["bridge"])
                    if self.sticky.get(STICKY_KEY) is record:
                        del self.sticky[STICKY_KEY]
                    return
            if self.backend.now() >= deadline:
                raise RuntimeError(
                    "Cleanup is still pending for port {0}. No new bridge was started. "
                    "Stop MCP clients, let Rhino return to idle, then run Stop/Start again. "
                    "If it persists, save your work and restart this Rhino. "
                    "Stop() does NOT cancel already queued user code.".format(record["port"]))
            self.backend.sleep(0.05)

    def start(self, port):
        if not 1024 <= port <= 65535 or port == 5000:
            raise ValueError("Use a port from 1024 to 65535, excluding 5000.")
        old = self.record()
        if old is not None:
            if old["phase"] != "cleanup_pending" and self.healthy(old):
                old["phase"] = "running"
                if old["port"] == port:
                    return "already_running"
                raise RuntimeError(
                    "This Rhino has a live extra bridge on {0}. Stop its MCP client, "
                    "run this script's Stop action, then choose another port. "
                    "For parallel work use a DIFFERENT Rhino.exe.".format(old["port"]))
            # Retry only after the previous asynchronous startup has been cleaned up.
            self.cleanup(old)

        if self.backend.listening(port):
            raise RuntimeError("Port {0} is already listening. Choose another port; no process was killed.".format(port))
        bridge = self.backend.create(port)
        record = {"port": port, "bridge": bridge, "phase": "starting"}
        # Keep a reference for cleanup, NOT a claim of successful startup.
        self.sticky[STICKY_KEY] = record
        try:
            self.backend.start(bridge)
            deadline = self.backend.now() + self.startup_timeout
            while True:
                running, alive = self.backend.state(bridge)
                if not running or not alive:
                    raise RuntimeError("The listener stopped before startup was confirmed.")
                if self.backend.listening(port):
                    if self.healthy(record):
                        record["phase"] = "running"
                        return "started"
                    raise RuntimeError("Listener ownership/state does not match this Rhino; startup was not confirmed.")
                if self.backend.now() >= deadline:
                    raise RuntimeError("Timed out waiting for the extra listener to bind.")
                self.backend.sleep(0.05)
        except BaseException as error:
            try:
                self.cleanup(record)
            except BaseException as cleanup_error:
                raise RuntimeError("Startup failed: {0}\nRecovery: {1}".format(error, cleanup_error))
            raise

    def stop(self):
        record = self.record()
        if record is None:
            return "not_running"
        self.cleanup(record)
        return "stopped"


class RhinoBackend(object):
    def __init__(self, session_path=None, token=None, model_path=None, document_serial=None):
        import System
        import Rhino
        from System.Diagnostics import Process, Stopwatch
        from System.Net.NetworkInformation import IPGlobalProperties
        from System.Reflection import BindingFlags
        self.System = System
        self.Rhino = Rhino
        self.Process = Process
        self.IPGlobalProperties = IPGlobalProperties
        self.flags = BindingFlags.Instance | BindingFlags.NonPublic
        self.pid = int(Process.GetCurrentProcess().Id)
        self.clock = Stopwatch.StartNew()
        self.session_path = session_path
        self.token = token
        self.model_path = model_path
        self.document_serial = document_serial

    def now(self):
        return self.clock.Elapsed.TotalSeconds

    def sleep(self, seconds):
        # Bounded waits; deliberately no RhinoApp.Wait()/event pumping or recursive callbacks.
        self.System.Threading.Thread.Sleep(int(seconds * 1000))

    def listening(self, port):
        endpoints = self.IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners()
        return any(int(ep.Port) == port for ep in endpoints)

    def owners(self, port):
        """Query OS metadata only. Never connect to or send C# through the bridge."""
        import os
        import base64
        command = (
            "$ErrorActionPreference='Stop'; try { "
            "Get-NetTCPConnection -State Listen -ErrorAction Stop | "
            "Where-Object { $_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -eq %d } | "
            "ForEach-Object { [Console]::Out.WriteLine($_.OwningProcess) }; exit 0 "
            "} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }" % port)
        encoded = base64.b64encode(command.encode("utf-16le"))
        if not isinstance(encoded, str):
            encoded = encoded.decode("ascii")
        executable = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                  "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        info = self.System.Diagnostics.ProcessStartInfo()
        info.FileName = executable
        info.Arguments = "-NoLogo -NoProfile -NonInteractive -EncodedCommand " + encoded
        info.UseShellExecute = False
        info.CreateNoWindow = True
        info.RedirectStandardOutput = True
        info.RedirectStandardError = True
        process = self.Process.Start(info)
        try:
            # Drain both pipes asynchronously to avoid a pipe-buffer deadlock.
            stdout = process.StandardOutput.ReadToEndAsync()
            stderr = process.StandardError.ReadToEndAsync()
            if not process.WaitForExit(10000):
                process.Kill()  # Only this diagnostic child, NEVER Rhino or a port owner.
                raise RuntimeError("OS ownership query timed out. Startup is NOT confirmed.")
            if process.ExitCode != 0:
                raise RuntimeError("Cannot inspect TCP ownership: " + str(stderr.Result).strip())
            text = str(stdout.Result).strip()
            return set(int(line.strip()) for line in text.splitlines() if line.strip())
        finally:
            process.Dispose()

    def fields(self, bridge_type):
        running = bridge_type.GetField("_running", self.flags)
        thread = bridge_type.GetField("_listenerThread", self.flags)
        if running is None or thread is None:
            raise RuntimeError("Unsupported BridgeServer lifecycle fields. No internal fields are patched; re-review this plugin version.")
        return running, thread

    def create(self, port):
        if self.session_path:
            import os
            from System.Reflection import Assembly
            dll = os.path.join(os.path.dirname(os.path.abspath(__file__)), "native", "bin", "Release",
                               "net8.0", "Almond.Engine.dll")
            if not os.path.isfile(dll):
                raise RuntimeError("Build the Almond engine native helper before starting a shared connection: " + dll)
            assembly = Assembly.LoadFrom(dll)
            kind = assembly.GetType("AlmondEngine.BoundBridge", True)
            arguments = self.System.Array[self.System.Object]([
                self.System.Int32(port), self.session_path, self.token, self.model_path,
                self.System.UInt32(self.document_serial)])
            return self.System.Activator.CreateInstance(kind, arguments)
        candidates = []
        for assembly in self.System.AppDomain.CurrentDomain.GetAssemblies():
            candidate = assembly.GetType("RhinoAlmondBridge.BridgeServer", False)
            if candidate is not None:
                candidates.append(candidate)
        if len(candidates) != 1:
            raise RuntimeError("Expected exactly one loaded RhinoAlmondBridge assembly; found {0}. Check plugin installation.".format(len(candidates)))
        self.fields(candidates[0])  # Fail BEFORE starting an incompatible implementation.
        arguments = self.System.Array[self.System.Object]([self.System.Int32(port)])
        return self.System.Activator.CreateInstance(candidates[0], arguments)

    def state(self, bridge):
        if bridge.GetType().FullName == "AlmondEngine.BoundBridge":
            return bool(bridge.IsRunning), bool(bridge.IsAlive or bridge.Pending)
        running, thread = self.fields(bridge.GetType())
        listener_thread = thread.GetValue(bridge)
        return bool(running.GetValue(bridge)), bool(listener_thread is not None and listener_thread.IsAlive)

    def start(self, bridge):
        bridge.Start()

    def stop(self, bridge):
        bridge.Stop()

    def dispose(self, bridge):
        if bridge.GetType().FullName == "AlmondEngine.BoundBridge":
            bridge.Dispose()

    def identity(self):
        doc = self.Rhino.RhinoDoc.ActiveDoc
        path = (doc.Path or "(unsaved)") if doc else "(no active document)"
        serial = doc.RuntimeSerialNumber if doc else "none"
        modified = doc.Modified if doc else "none"
        self.Rhino.RhinoApp.WriteLine("Rhino PID={0} | document serial={1} | Modified={2}".format(self.pid, serial, modified))
        self.Rhino.RhinoApp.WriteLine("Document: {0}".format(path))


def main():
    import Rhino
    import rhinoscriptsyntax as rs
    import scriptcontext as sc
    backend = RhinoBackend()
    manager = BridgeManager(sc.sticky, backend)
    action = rs.GetString("Almond extra bridge action", "Start", ["Start", "Stop", "Status", "Inspect"])
    if action is None:
        return
    try:
        if action.lower() == "start":
            port = rs.GetInteger("Extra port (Rhino A-J=5501-5510; not 5000)", 5501, 1024, 65535)
            if port is None:
                return
            result = manager.start(port)
            Rhino.RhinoApp.WriteLine("Extra bridge: {0} | 127.0.0.1:{1} | PID={2}".format(result, port, backend.pid))
        elif action.lower() == "stop":
            Rhino.RhinoApp.WriteLine("Extra bridge: " + manager.stop())
        elif action.lower() == "status":
            record = manager.record()
            if record is None:
                Rhino.RhinoApp.WriteLine("No managed extra bridge is recorded.")
            else:
                Rhino.RhinoApp.WriteLine("Extra port={0} | recorded phase={1} | healthy now={2}".format(
                    record["port"], record["phase"], manager.healthy(record)))
        backend.identity()
        Rhino.RhinoApp.WriteLine(
            "This script sends NO MCP request. PID/document output is a snapshot, not a document lock. "
            "Almond C# queries can themselves create default layers. Default bridge 5000 is untouched.")
    except Exception as error:
        Rhino.RhinoApp.WriteLine("[AlmondParallel] ERROR: {0}".format(error))
        backend.identity()
        raise


if __name__ == "__main__":
    main()
