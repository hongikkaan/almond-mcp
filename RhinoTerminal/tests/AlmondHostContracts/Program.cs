using System.Diagnostics;
using System.Net.NetworkInformation;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;
using AlmondEngine;
using RhinoTerminal;

var parent = Path.GetFullPath(args.Single());
if (!Directory.Exists(parent)) throw new ArgumentException("Supply an existing workspace data directory.");
var suite = Path.Combine(parent, "host-contracts-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(suite);
try
{
    var shared = Path.Combine(suite, "shared", ".almond");
    Directory.CreateDirectory(shared);
    using (var first = new SharedStorageLease(shared))
    using (var second = new SharedStorageLease(shared))
        foreach (var name in new[] { "launcher.lock", "rhino.lock", "mcp.lock" })
            Check.That(!Check.Free(Path.Combine(shared, name)), "Legacy exclusive owner bypassed a shared owner.");
    foreach (var blocked in new[] { "rhino.lock", "mcp.lock" })
    {
        using (Check.Lock(Path.Combine(shared, blocked)))
            Check.Throws<IOException>(() => { using var failed = new SharedStorageLease(shared); });
        Check.That(Check.Free(Path.Combine(shared, "launcher.lock")), "Partial shared acquisition leaked a handle.");
        Check.That(Check.Free(Path.Combine(shared, "rhino.lock")), "Partial shared acquisition leaked the second handle.");
    }
    Console.WriteLine("PASS: real shared/legacy exclusion and partial-acquisition cleanup");

    var models = Path.Combine(suite, "peer-models");
    using (var first = new HostFixture(suite, "first", models))
    using (var second = new HostFixture(suite, "second", models))
    {
        var peerReady = File.ReadAllBytes(second.Ready);
        using var peerMcp = Check.Lock(Path.Combine(second.Session, "mcp.lock"));
        Check.That(first.Host.Release(), "A peer session MCP blocked this session's release.");
        Check.That(first.Native.Disposed, "Native ownership was not disposed after drain.");
        Check.That(Check.Free(Path.Combine(first.Session, "rhino.lock")), "Released host retained its own Rhino lease.");
        Check.That(!Check.Free(Path.Combine(second.Session, "rhino.lock")), "Releasing a peer dropped this Rhino lease.");
        Check.That(!Check.Free(Path.Combine(second.Storage, "rhino.lock")), "A live peer lost legacy exclusion.");
        Check.That(File.ReadAllBytes(second.Ready).SequenceEqual(peerReady), "Peer ready metadata changed.");
    }
    Console.WriteLine("PASS: one session exits while peer locks and metadata remain intact");

    using (var fixture = new HostFixture(suite, "drain"))
    {
        fixture.Native.IsAlive = true;
        fixture.Native.KeepListener = true;
        Check.That(!fixture.Host.Release(), "Live listener was released.");
        fixture.Native.KeepListener = false;
        fixture.Native.Pending = 1;
        Check.That(!fixture.Host.Release(), "Pending native operation was released.");
        Check.That(!Check.Free(Path.Combine(fixture.Session, "rhino.lock")), "Pending work lost Rhino ownership.");
        fixture.Native.Pending = 0;
        using (Check.Lock(Path.Combine(fixture.Session, "mcp.lock")))
            Check.That(!fixture.Host.Release(), "Active MCP was released.");
        Check.That(!fixture.Native.Disposed, "Native guard disposed before MCP drained.");
        Check.That(fixture.Host.Release() && fixture.Native.Disposed, "Drained host failed to release.");
        Check.That(Check.Free(Path.Combine(fixture.Storage, "launcher.lock")), "Final legacy handle leaked.");
    }
    Console.WriteLine("PASS: listener, pending work and own MCP independently retain ownership");

    using (var fixture = new HostFixture(suite, "foreign-token"))
    {
        var foreign = JsonSerializer.Serialize(new { token = Guid.NewGuid().ToString("N"), valid = true });
        File.WriteAllText(fixture.Locator, foreign);
        Check.That(!fixture.Host.Release(), "Foreign locator ownership was silently ignored.");
        Check.That(File.ReadAllText(fixture.Locator) == foreign, "Another token's locator was altered.");
        Check.That(!Check.Free(Path.Combine(fixture.Session, "rhino.lock")), "Unconfirmed cleanup dropped the lease.");
        fixture.WriteLocator();
        Check.That(fixture.Host.Release(), "Restored own locator did not permit cleanup.");
    }
    Console.WriteLine("PASS: another generation's metadata is never deleted");

    using (var fixture = new HostFixture(suite, "write-failure"))
    {
        using (new FileStream(fixture.Ready, FileMode.Open, FileAccess.Read, FileShare.Read))
            Check.That(!fixture.Host.Release(), "Failed invalidation write dropped ownership.");
        using (var ready = JsonDocument.Parse(File.ReadAllText(fixture.Ready)))
            Check.That(ready.RootElement.GetProperty("valid").GetBoolean(), "The write-failure fixture did not block replacement.");
        Check.That(!Check.Free(Path.Combine(fixture.Session, "rhino.lock")), "Stale valid metadata lost its guard.");
        Check.That(fixture.Host.Release(), "Retry after metadata write failure did not clean up.");
        using var invalid = JsonDocument.Parse(File.ReadAllText(fixture.Ready));
        Check.That(!invalid.RootElement.GetProperty("valid").GetBoolean(), "Released metadata remained valid.");
    }
    Console.WriteLine("PASS: invalidation write failure retains leases and retry persists invalid state");

    using (var fixture = new HostFixture(suite, "protocol", bind: false))
    {
        Check.Throws<InvalidOperationException>(() => fixture.Attach(1), "storage_protocol");
        Check.That(!Directory.Exists(fixture.Session), "Old protocol created a session.");
        var old = JsonSerializer.Serialize(new { token = fixture.Token, valid = false, preserved = "old ready" });
        Directory.CreateDirectory(fixture.Session);
        File.WriteAllText(fixture.Ready, old);
        Check.Throws<InvalidOperationException>(() => fixture.Attach(), "세션 토큰");
        Check.That(File.ReadAllText(fixture.Ready) == old, "Old ready metadata was overwritten.");
        Check.That(Check.Free(Path.Combine(fixture.Session, "rhino.lock")), "Reused token failure leaked a lease.");
    }
    Console.WriteLine("PASS: protocol mismatch and reused token fail before overwriting metadata");

    using (var fixture = new HostFixture(suite, "failed-start", bind: false))
    using (var retry = new HostFixture(suite, "retry", bind: false))
    {
        BoundBridge.FailStart = true;
        BoundBridge.PendingOnStart = 1;
        Check.Throws<IOException>(() => fixture.Attach(), "fixture native start failure");
        var native = (BoundBridge)HostFixture.Get(fixture.Host, "bridge")!;
        Check.That(!Check.Free(Path.Combine(fixture.Session, "rhino.lock")), "Failed startup released pending ownership.");
        Check.Throws<InvalidOperationException>(() => retry.Attach(), "이전 Almond 작업");
        native.Pending = 0;
        Check.That(fixture.Host.Release(), "Completed failed-start work did not release.");
        Check.That(native.Disposed, "Failed-start native owner was not disposed.");
        BoundBridge.PendingOnStart = 0;
        Check.Throws<IOException>(() => retry.Attach(), "fixture native start failure");
        Check.That(Check.Free(Path.Combine(retry.Session, "rhino.lock")), "Retry failure leaked ownership.");
        Check.That(!retry.Host.HasBinding, "Retry retained a fully drained binding.");
    }
    Console.WriteLine("PASS: failed startup retains pending ownership, blocks another panel and then recovers");
    Console.WriteLine("All seven host contract checks passed. Rhino UI/native execution were fixture doubles; no native listener was opened.");
}
finally
{
    Directory.Delete(suite, true);
}

static class Check
{
    public static void That(bool success, string message) { if (!success) throw new Exception(message); }
    public static FileStream Lock(string path) => new(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
    public static bool Free(string path)
    {
        try { using var lease = Lock(path); return true; }
        catch (IOException) { return false; }
    }
    public static void Throws<T>(Action action, string? contains = null) where T : Exception
    {
        try { action(); }
        catch (T error)
        {
            if (contains != null && !error.Message.Contains(contains, StringComparison.Ordinal))
                throw new Exception("Unexpected exception: " + error.Message);
            return;
        }
        throw new Exception("Expected " + typeof(T).Name);
    }
}

sealed class HostFixture : IDisposable
{
    const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
    public AlmondHost Host { get; }
    public BoundBridge Native { get; }
    public string Token { get; } = Guid.NewGuid().ToString("N");
    public string Model { get; }
    public string Storage { get; }
    public string Session { get; }
    public string Ready { get; }
    public string Locator { get; }
    readonly string slot;
    readonly int port;
    readonly Dictionary<string, object?> binding;

    public HostFixture(string suite, string name, string? models = null, bool bind = true)
    {
        var root = Path.Combine(suite, name);
        models ??= Path.Combine(root, "models");
        Directory.CreateDirectory(models);
        Model = Path.Combine(models, name + ".3dm");
        // This is only a saved-path fixture; no claim of valid Rhino geometry.
        File.WriteAllText(Model, "path fixture");
        Storage = Path.Combine(models, ".almond");
        Directory.CreateDirectory(Path.Combine(Storage, "tmp"));
        Session = Path.Combine(Storage, ".sessions", Token);
        Ready = Path.Combine(Session, "ready.json");
        var listeners = IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners().Select(x => x.Port).ToHashSet();
        slot = "ABCDEFGHIJ".FirstOrDefault(c => !listeners.Contains(5501 + "ABCDEFGHIJ".IndexOf(c))).ToString();
        if (slot == "\0") throw new Exception("No free slot for the rejection-only fixture; no production port was changed.");
        port = 5501 + "ABCDEFGHIJ".IndexOf(slot);
        var engine = Path.Combine(root, "Almond", "_engine");
        Locator = Path.Combine(root, "Almond", "data", slot, "active.json");
        Host = (AlmondHost)RuntimeHelpers.GetUninitializedObject(typeof(AlmondHost));
        Set(Host, "report", (Action<string>)(_ => { }));
        Set(Host, "<Engine>k__BackingField", engine);
        Set(Host, "sessionDirectory", Session);
        Set(Host, "readyPath", Ready);
        Set(Host, "locatorPath", Locator);
        Native = new BoundBridge(0, Ready, Token, Model, 7);
        binding = new Dictionary<string, object?> {
            ["token"]=Token, ["valid"]=true, ["status"]="started", ["port"]=0,
            ["storage_protocol"]=2, ["model_path"]=Model, ["document_serial"]="7",
            ["storage"]=Storage, ["temp"]=Path.Combine(Storage,"tmp"),
            ["session_dir"]=Session, ["ready_path"]=Ready
        };
        if (bind)
        {
            Directory.CreateDirectory(Session);
            Set(Host, "binding", binding);
            Set(Host, "bridge", Native);
            Set(Host, "sharedLease", new SharedStorageLease(Storage));
            Set(Host, "lease", Check.Lock(Path.Combine(Session, "rhino.lock")));
            File.WriteAllText(Ready, JsonSerializer.Serialize(binding));
            WriteLocator();
        }
    }

    public object? Attach(int protocol = 2)
    {
        Rhino.RhinoDoc.ActiveDoc = new Rhino.RhinoDoc { Path=Model, RuntimeSerialNumber=7 };
        using var request = JsonDocument.Parse(JsonSerializer.Serialize(new {
            storage_protocol=protocol, model_path=Model, document_serial="7", session_token=Token,
            storage=Storage, session_dir=Session, slot, port
        }));
        try { return typeof(AlmondHost).GetMethod("Attach", Private)!.Invoke(Host, new object[] { request.RootElement }); }
        catch (TargetInvocationException error) when (error.InnerException != null) { throw error.InnerException; }
    }

    public void WriteLocator()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Locator)!);
        File.WriteAllText(Locator, JsonSerializer.Serialize(binding));
    }
    public static object? Get(object target, string name) => target.GetType().GetField(name, Private)!.GetValue(target);
    static void Set(object target, string name, object? value) => target.GetType().GetField(name, Private)!.SetValue(target, value);
    public void Dispose()
    {
        // The fixture bypasses the UI/pipe constructor; release only resources it installed.
        typeof(AlmondHost).GetMethod("ReleaseLeases", Private)!.Invoke(Host, null);
        var pending = (HashSet<AlmondHost>)typeof(AlmondHost).GetField("pendingCleanup", BindingFlags.Static | BindingFlags.NonPublic)!.GetValue(null)!;
        pending.Remove(Host);
    }
}
