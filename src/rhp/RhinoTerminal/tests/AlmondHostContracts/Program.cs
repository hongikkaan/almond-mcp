using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;
using AlmondEngine;
using RhinoTerminal;

static void Require(bool value, string message) { if (!value) throw new Exception(message); }
static void Set(object owner, string field, object? value) => owner.GetType().GetField(field, BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(owner, value);
string root = Path.Combine(Path.GetTempPath(), "almond-terminal-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
try
{
    var session = Path.Combine(root, ".almond", ".sessions", Guid.NewGuid().ToString("N"));
    Directory.CreateDirectory(session);
    string token = Guid.NewGuid().ToString("N"), ready = Path.Combine(session, "ready.json"), locator = Path.Combine(root, "active.json");
    var binding = new Dictionary<string, object?> { ["token"] = token, ["valid"] = true, ["status"] = "started", ["port"] = 0 };
    File.WriteAllText(ready, JsonSerializer.Serialize(binding));
    File.WriteAllText(locator, JsonSerializer.Serialize(binding));
    var host = (AlmondHost)RuntimeHelpers.GetUninitializedObject(typeof(AlmondHost));
    var bridge = new BoundBridge(0, ready, token, "", 7) { Pending = 1 };
    Set(host, "binding", binding); Set(host, "bridge", bridge); Set(host, "report", (Action<string>)(_ => { }));
    Set(host, "sessionDirectory", session); Set(host, "readyPath", ready); Set(host, "locatorPath", locator);
    Set(host, "lease", new FileStream(Path.Combine(session, "rhino.lock"), FileMode.Create, FileAccess.ReadWrite, FileShare.None));
    Require(!host.Release(), "Pending native work released ownership");
    Require(!bridge.Disposed, "Pending bridge was disposed");
    bridge.Pending = 0;
    using (new FileStream(Path.Combine(session, "mcp.lock"), FileMode.Create, FileAccess.ReadWrite, FileShare.None))
        Require(!host.Release(), "Active MCP released ownership");
    File.WriteAllText(locator, JsonSerializer.Serialize(new { token = "foreign" }));
    Require(!host.Release(), "Foreign locator was deleted");
    Require(File.Exists(locator), "Foreign locator missing");
    File.WriteAllText(locator, JsonSerializer.Serialize(binding));
    Require(host.Release() && bridge.Disposed, "Drained owner failed to release");
    Require(!File.Exists(locator), "Owned locator retained");
    Console.WriteLine("PASS: pending native/MCP work and foreign metadata retain Terminal ownership");
}
finally { Directory.Delete(root, true); }
