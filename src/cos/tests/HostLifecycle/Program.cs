using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;
using AlmondCOS;
using AlmondEngine;

internal static class Program
{
    const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;

    static async Task<int> Main()
    {
        var tests = new (string Name, Func<Task> Run)[] {
            ("releasing A preserves shared storage and B's metadata/MCP owner", IndependentSessions),
            ("own MCP worker and native pending work both retain ownership", RetainUntilDrained),
            ("invalid ready publication failure retains ownership and can retry", FailedInvalidation),
            ("foreign locator token is retained", ForeignLocator),
            ("MCP gate stays held through invalidation and native disposal", ReleaseGate),
            ("detach waits for asynchronous listener drain", DetachDrain),
            ("retained native binding refuses a different client attach", RetainedBindingRejectsAttach)
        };
        foreach (var (name, run) in tests)
        {
            try { await run(); Console.WriteLine("PASS " + name); }
            catch (Exception ex) { Console.Error.WriteLine("FAIL " + name + "\n" + ex); return 1; }
        }
        Console.WriteLine("PASS " + tests.Length + " COS lifecycle fixtures; Rhino/native are simulated.");
        return 0;
    }

    static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    static bool IsLocked(string path)
    {
        try { using var probe = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); return false; }
        catch (IOException) { return true; }
    }

    static JsonElement Read(string path)
    {
        using var json = JsonDocument.Parse(File.ReadAllText(path));
        return json.RootElement.Clone();
    }

    static Task IndependentSessions()
    {
        using var workspace = new Workspace();
        using var first = new HostFixture(workspace.Path, "A");
        using var second = new HostFixture(workspace.Path, "B");
        using var secondWorker = new FileStream(second.Paths.McpLock, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        string originalReady = File.ReadAllText(second.Paths.ReadyPath);
        string originalLocator = File.ReadAllText(second.ActivePath);
        Check(first.Paths.Storage == second.Paths.Storage, "Fixture models do not share one storage root.");
        Check(first.Release(), "A could not detach while B owned its independent MCP lock.");
        Check(File.ReadAllText(second.Paths.ReadyPath) == originalReady &&
            File.ReadAllText(second.ActivePath) == originalLocator, "Releasing A changed B's records.");
        Check(IsLocked(second.Paths.RhinoLock) && IsLocked(second.Paths.McpLock), "Releasing A dropped B's role locks.");
        Check(IsLocked(System.IO.Path.Combine(second.Paths.Storage, "rhino.lock")), "B lost its legacy compatibility barrier.");
        return Task.CompletedTask;
    }

    static Task RetainUntilDrained()
    {
        using var workspace = new Workspace();
        using var fixture = new HostFixture(workspace.Path, "A");
        using (var worker = new FileStream(fixture.Paths.McpLock, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
        {
            Check(!fixture.Release(), "A live unregistered MCP worker lost ownership.");
            Check(IsLocked(fixture.Paths.RhinoLock), "Rhino lease was released while MCP was live.");
        }
        fixture.Native.Pending = 1;
        Check(!fixture.Release(), "Queued native work lost ownership after worker exit.");
        fixture.Native.Pending = 0;
        fixture.Native.KeepListener = true;
        fixture.Native.IsAlive = true;
        Check(!fixture.Release(), "Listener exit was not required.");
        fixture.Native.KeepListener = false;
        Check(fixture.Release(), "Drained native work did not release.");
        return Task.CompletedTask;
    }

    static Task RetainedBindingRejectsAttach()
    {
        using var workspace = new Workspace();
        using var fixture = new HostFixture(workspace.Path, "A");
        fixture.Native.Pending = 1;
        Check(!fixture.Release(), "Unconfirmed native work lost its binding.");
        var original = File.ReadAllText(fixture.Paths.ReadyPath);
        using var request = JsonDocument.Parse(JsonSerializer.Serialize(new {
            session_token = Guid.NewGuid().ToString("N")
        }));
        try
        {
            typeof(CosHost).GetMethod("Attach", Private)!.Invoke(fixture.Host, new object[] { request.RootElement });
            throw new InvalidOperationException("Another client replaced a retained binding.");
        }
        catch (TargetInvocationException ex) when (ex.InnerException is InvalidOperationException) { }
        Check((string)fixture.Binding["token"]! == fixture.Token, "Retained token changed.");
        Check(File.ReadAllText(fixture.Paths.ReadyPath) == original, "Rejected attach changed ready metadata.");
        Check(IsLocked(fixture.Paths.RhinoLock), "Rejected attach released the original Rhino lease.");
        return Task.CompletedTask;
    }

    static Task FailedInvalidation()
    {
        using var workspace = new Workspace();
        using var fixture = new HostFixture(workspace.Path, "A");
        File.SetAttributes(fixture.Paths.ReadyPath, FileAttributes.ReadOnly);
        Check(!fixture.Release(), "Failed invalidation was ignored.");
        Check(Read(fixture.Paths.ReadyPath).GetProperty("valid").GetBoolean(), "Fixture did not preserve the failed old ready file.");
        Check(IsLocked(fixture.Paths.RhinoLock) && !fixture.Native.Disposed, "Failed invalidation dropped ownership.");
        Check(File.Exists(fixture.ActivePath), "Failed invalidation deleted its locator.");
        File.SetAttributes(fixture.Paths.ReadyPath, FileAttributes.Normal);
        Check(fixture.Release(), "Invalidation failure could not be retried.");
        Check(!Read(fixture.Paths.ReadyPath).GetProperty("valid").GetBoolean(), "Ended generation remains valid.");
        return Task.CompletedTask;
    }

    static Task ForeignLocator()
    {
        using var workspace = new Workspace();
        using var fixture = new HostFixture(workspace.Path, "A");
        string foreign = Guid.NewGuid().ToString("N");
        SessionFiles.WriteJson(fixture.ActivePath, new { token = foreign });
        Check(!fixture.Release(), "A foreign generation locator was removed.");
        Check(Read(fixture.ActivePath).GetProperty("token").GetString() == foreign, "Foreign locator changed.");
        Check(IsLocked(fixture.Paths.RhinoLock), "Ownership was dropped on a locator mismatch.");
        SessionFiles.WriteJson(fixture.ActivePath, fixture.Binding);
        Check(fixture.Release(), "Owned locator could not be cleaned afterward.");
        return Task.CompletedTask;
    }

    static Task ReleaseGate()
    {
        using var workspace = new Workspace();
        using var fixture = new HostFixture(workspace.Path, "A");
        bool checkedInsideDispose = false;
        fixture.Native.OnDispose = () => {
            checkedInsideDispose = true;
            Check(IsLocked(fixture.Paths.McpLock), "The worker gate closed before native ownership was released.");
            Check(!Read(fixture.Paths.ReadyPath).GetProperty("valid").GetBoolean(), "Native disposal preceded invalid ready publication.");
            Check(!File.Exists(fixture.ActivePath), "Native disposal preceded owned locator removal.");
        };
        Check(fixture.Release() && checkedInsideDispose, "Native disposal was not observed.");
        Check(!IsLocked(fixture.Paths.McpLock), "The release guard leaked.");
        return Task.CompletedTask;
    }

    static async Task DetachDrain()
    {
        using var workspace = new Workspace();
        using var fixture = new HostFixture(workspace.Path, "A");
        fixture.Native.KeepListener = true;
        using var request = JsonDocument.Parse(JsonSerializer.Serialize(new { action = "detach", session_token = fixture.Token }));
        var method = typeof(CosHost).GetMethod("Dispatch", Private)!;
        var completion = (Task<object>)method.Invoke(fixture.Host, new object[] { request.RootElement, CancellationToken.None })!;
        await Task.Delay(50);
        Check(!completion.IsCompleted && IsLocked(fixture.Paths.RhinoLock), "Detach released before the listener drained.");
        fixture.Native.KeepListener = false;
        var result = await completion.WaitAsync(TimeSpan.FromSeconds(2));
        Check((bool)result.GetType().GetProperty("detached")!.GetValue(result)!, "Detach did not return success after drain.");
    }

    sealed class Workspace : IDisposable
    {
        internal string Path { get; } = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "Almond-CosLifecycle-" + Guid.NewGuid().ToString("N"));
        internal Workspace() => Directory.CreateDirectory(Path);
        public void Dispose() => Directory.Delete(Path, true);
    }

    sealed class HostFixture : IDisposable
    {
        internal readonly CosHost Host;
        internal readonly SessionPaths Paths;
        internal readonly string Token = Guid.NewGuid().ToString("N"), ActivePath;
        internal readonly BoundBridge Native;
        internal readonly Dictionary<string, object?> Binding;

        internal HostFixture(string root, string slot)
        {
            var model = System.IO.Path.Combine(root, slot + ".3dm");
            File.WriteAllText(model, "Fixture only; never opened by Rhino.");
            Paths = SessionFiles.Paths(model, slot, Token, true);
            ActivePath = System.IO.Path.Combine(root, "locators", slot, "active.json");
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(ActivePath)!);
            Binding = new Dictionary<string, object?> {
                ["schema"]="almond-project", ["storage_protocol"]=2, ["attachment"]="cos", ["label"]=slot,
                ["port"]=5501 + SessionFiles.Slots.IndexOf(slot), ["token"]=Token,
                ["pid"]=Environment.ProcessId, ["document_serial"]="1",
                ["model_path"]=model, ["storage"]=Paths.Storage, ["session_dir"]=Paths.SessionDir,
                ["ready_path"]=Paths.ReadyPath, ["valid"]=true, ["status"]="started"
            };
            SessionFiles.WriteJson(Paths.ReadyPath, Binding);
            SessionFiles.WriteJson(ActivePath, Binding);
            Native = new BoundBridge(5501, Paths.ReadyPath, Token, model, 1);
            // Only the release/dispatch paths are under test; skip advertising a host or starting UI/pipes.
            Host = (CosHost)RuntimeHelpers.GetUninitializedObject(typeof(CosHost));
            Set("binding", Binding);
            Set("readyPath", Paths.ReadyPath);
            Set("activePath", ActivePath);
            Set("sessionPaths", Paths);
            Set("storageLease", new SharedStorageLease(Paths.Storage));
            Set("launcherLease", new FileStream(Paths.LauncherLock, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None));
            Set("rhinoLease", new FileStream(Paths.RhinoLock, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None));
            Set("bridge", Native);
            Set("problem", "");
            Set("requestId", "unconfirmed logical outcome");
            Set("busy", true);
        }

        void Set(string name, object? value) => typeof(CosHost).GetField(name, Private)!.SetValue(Host, value);
        internal bool Release() => (bool)typeof(CosHost).GetMethod("Release", Private)!.Invoke(Host, null)!;
        public void Dispose()
        {
            Native.Pending = 0;
            Native.KeepListener = false;
            Native.OnDispose = null;
            if (File.Exists(Paths.ReadyPath)) File.SetAttributes(Paths.ReadyPath, FileAttributes.Normal);
            if (File.Exists(ActivePath)) SessionFiles.WriteJson(ActivePath, Binding);
            Check(Release(), "Fixture cleanup retained a lease.");
        }
    }
}
