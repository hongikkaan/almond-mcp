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
    Console.WriteLine("PASS: identity, shared/exclusive leases, and completion fence");
}
finally { Directory.Delete(root, true); }
