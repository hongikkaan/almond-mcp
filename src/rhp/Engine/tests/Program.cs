using System.Diagnostics;
using AlmondEngine;

static void Require(bool value, string message) { if (!value) throw new Exception(message); }
static void Throws<T>(Action action) where T : Exception { try { action(); } catch (T) { return; } throw new Exception("Expected " + typeof(T).Name); }
var root = Path.Combine(Path.GetTempPath(), "almond-native-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
try
{
    var model = Path.Combine(root, "saved.3dm");
    File.WriteAllText(model, "path fixture only");
    string token = Guid.NewGuid().ToString("N");
    var paths = SessionFiles.Paths(model, "A", token, true);
    Require(SessionFiles.Same(model, Path.Combine(root, ".", "saved.3dm")), "Canonical identity mismatch");
    Require(SessionFiles.Same(model, Path.Combine(root, "SAVED.3DM")), "Path casing changed identity");
    Require(SessionFiles.Same(model, model + Path.DirectorySeparatorChar), "Trailing separator changed identity");
    Require(!SessionFiles.Same(model, Path.Combine(root, "other.3dm")), "Different model matched");
    Throws<ArgumentException>(() => SessionFiles.Paths(model, "K", token));
    Throws<ArgumentException>(() => SessionFiles.Paths(model, "A", token.ToUpperInvariant()));
    Throws<IOException>(() => SessionFiles.Paths(Path.Combine(root, "missing.3dm"), "A", token));
    Throws<System.ComponentModel.Win32Exception>(() => SessionFiles.Paths(model, "A", token, true));
    using (var one = SharedStorageLease.Acquire(paths.Storage))
    using (var two = SharedStorageLease.Acquire(paths.Storage))
        Throws<IOException>(() => { using var exclusive = new FileStream(Path.Combine(paths.Storage, "rhino.lock"), FileMode.Open, FileAccess.ReadWrite, FileShare.None); });
    using (var exclusive = new FileStream(Path.Combine(paths.Storage, "mcp.lock"), FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        Throws<IOException>(() => SharedStorageLease.Acquire(paths.Storage));
    using (var released = new FileStream(Path.Combine(paths.Storage, "launcher.lock"), FileMode.Open, FileAccess.ReadWrite, FileShare.None)) { }
    using var self = Process.GetCurrentProcess();
    string ticks = self.StartTime.ToUniversalTime().Ticks.ToString();
    Require(!ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Missing journal is not pending");
    File.WriteAllText(paths.RhinocodePath, "{invalid");
    Require(ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Invalid journal must retain ownership");
    var target = new { pid = self.Id, process_start_ticks = ticks, document_serial = 7, model_path = model, pipe_id = "fixture" };
    string operation = Guid.NewGuid().ToString("N"), request = Guid.NewGuid().ToString("N"), nonce = Guid.NewGuid().ToString("N"), hash = new string('a', 64);
    var journal = new { schema = "almond-rhinocode-execution", version = 1, token, operation_id = operation, request_id = request, nonce, source_hash = hash, language = "python", target, child = new { pid = self.Id, process_start_ticks = "1" } };
    SessionFiles.WriteJson(paths.RhinocodePath, journal);
    Require(ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Missing completion must retain ownership");
    var receiptDir = Path.Combine(paths.CallRoot, operation, "rhinocode", request);
    Directory.CreateDirectory(receiptDir);
    SessionFiles.WriteJson(Path.Combine(receiptDir, "complete.json"), new { schema = "almond-rhinocode-completion", version = 1, token, operation_id = operation, request_id = request, nonce, source_hash = hash, target, execution_complete = true, status = "success", mutation_state = "completed" });
    Require(!ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Matching completion did not release fence");
    Require(ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 8), "Different document serial must retain ownership");
    var owned = new { schema = "almond-rhinocode-execution", version = 1, token, operation_id = operation,
        request_id = request, nonce, source_hash = hash, language = "python", target,
        child = (object?)null, launch_protocol = "owned-v1" };
    var owner = new { token, operation_id = operation, request_id = request, nonce, source_hash = hash, target };
    var exitedChild = new { pid = self.Id, process_start_ticks = "1" }; // Reused PID, different creation identity.
    SessionFiles.WriteJson(paths.RhinocodePath, owned);
    SessionFiles.WriteJson(Path.Combine(receiptDir, "child.json"), new { schema = "almond-owned-process", owner, child = exitedChild });
    Require(!ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Durable child must recover a parent publication crash");
    File.Delete(Path.Combine(receiptDir, "complete.json"));
    Require(ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Supervisor exit cannot replace native completion");
    SessionFiles.WriteJson(Path.Combine(receiptDir, "child-exit.json"), new { schema = "almond-owned-process", owner,
        child = exitedChild, dispatched = false, error = "Parent did not authorize dispatch" });
    Require(!ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Exact undispatched child exit must release fence");
    SessionFiles.WriteJson(Path.Combine(receiptDir, "child.json"), new { schema = "almond-owned-process",
        owner = new { token = new string('f', 32), operation_id = operation, request_id = request, nonce, source_hash = hash, target }, child = exitedChild });
    Require(ExternalExecutionFence.IsPending(paths, token, self.Id, ticks, 7), "Another owner cannot discharge the fence");
    Console.WriteLine("PASS: identity, shared/exclusive leases, and completion fence");
}
finally { Directory.Delete(root, true); }
