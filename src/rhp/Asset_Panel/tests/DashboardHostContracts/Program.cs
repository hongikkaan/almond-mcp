using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using AlmondEngine;
using RhinoAlmondBridge;

static void Require(bool value, string message) { if (!value) throw new Exception(message); }
static void VerifySdkCommand(string assemblyPath)
{
    using var file = File.OpenRead(assemblyPath);
    using var pe = new PEReader(file);
    var reader = pe.GetMetadataReader();
    var command = reader.TypeDefinitions.Select(reader.GetTypeDefinition).Single(type =>
        reader.GetString(type.Namespace) == "RhinoAlmondBridge" && reader.GetString(type.Name) == "AlmondDashboardCommand");
    Require((command.Attributes & TypeAttributes.VisibilityMask) == TypeAttributes.Public &&
        (command.Attributes & TypeAttributes.Abstract) == 0, "Rhino default discovery requires a public concrete command");
    var baseType = reader.GetTypeReference((TypeReferenceHandle)command.BaseType);
    Require(reader.GetString(baseType.Namespace) == "Rhino.Commands" && reader.GetString(baseType.Name) == "Command",
        "Dashboard command must implement the existing Rhino SDK discovery contract");
    var methods = command.GetMethods().Select(reader.GetMethodDefinition).Select(m => reader.GetString(m.Name)).ToArray();
    Require(methods.Contains(".ctor") && methods.Contains("EnsurePanelRegistered") && methods.Contains("OnRhinoClosing"),
        "Missing Dashboard-owned registration/cleanup methods");
    foreach (var expected in new[] { (Type: "Panels", Name: "RegisterPanel"), (Type: "RhinoApp", Name: "add_Closing") })
    {
        Require(reader.MemberReferences.Select(reader.GetMemberReference).Any(member =>
            member.Parent.Kind == HandleKind.TypeReference && reader.GetString(member.Name) == expected.Name &&
            reader.GetString(reader.GetTypeReference((TypeReferenceHandle)member.Parent).Name) == expected.Type),
            "Dashboard SDK integration hook missing: " + expected.Name);
    }
}
VerifySdkCommand(Assembly.GetExecutingAssembly().Location);
if (args.Length == 1) VerifySdkCommand(args[0]);
var fixtureRoot = Path.Combine(Path.GetTempPath(), "almond-dashboard-" + Guid.NewGuid().ToString("N"));
var runtimePath = Path.Combine(fixtureRoot, "src", "mcp", "runtime");
var pluginPath = Path.Combine(fixtureRoot, "src", "rhp", "RhinoAlmondBridge", "plugin-fixture", "RhinoAlmondBridge.rhp");
Directory.CreateDirectory(Path.Combine(runtimePath, "dashboard"));
try
{
    Require(RuntimeEnvironment.RuntimeDirectory(pluginPath) == runtimePath, "Plugin did not use its checkout's Dashboard source");
    string python = Path.Combine(fixtureRoot, "src", "engine", ".venv", "Scripts", "python.exe");
    Require(RuntimeEnvironment.PythonExecutable(runtimePath) == python, "Wrong shared Python path");
    File.WriteAllText(Path.Combine(runtimePath, "dashboard", "__main__.py"), "# fixture only");
    using (var missing = new DashboardRuntime(runtimePath, _ => throw new Exception("Child launched without its own Python")))
    {
        try { await missing.StartAsync(); throw new Exception("Missing runtime Python accepted"); }
        catch (FileNotFoundException e) { Require(e.FileName == python, "Wrong missing-Python diagnostic path"); }
    }
    Directory.CreateDirectory(Path.GetDirectoryName(python)!);
    File.WriteAllText(python, "unused executable placeholder");
    string token = new('a', 43);
    string address = "http://127.0.0.1:18542/#" + token;
    var inheritedEnvironment = new Dictionary<string, string?> {
        ["PYTHONHOME"] = @"C:\Rhino\embedded-python39",
        ["PYTHONPATH"] = @"C:\Rhino\embedded-python39\Lib",
        ["PYTHONEXECUTABLE"] = @"C:\Rhino\embedded-python39\python.exe",
        ["ALMOND_DASHBOARD_ENV_CONTRACT"] = "preserve unrelated child settings"
    };
    var originalEnvironment = inheritedEnvironment.Keys.ToDictionary(name => name, Environment.GetEnvironmentVariable);
    try
    {
        foreach (var entry in inheritedEnvironment) Environment.SetEnvironmentVariable(entry.Key, entry.Value);
        using var isolated = new DashboardRuntime(runtimePath, start => {
            foreach (string name in new[] { "PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE" })
                Require(!start.Environment.ContainsKey(name), "Rhino " + name + " leaked into external Dashboard Python");
            Require(start.Environment["ALMOND_DASHBOARD_ENV_CONTRACT"] == "preserve unrelated child settings",
                "Unrelated child environment was removed");
            foreach (var entry in inheritedEnvironment)
                Require(Environment.GetEnvironmentVariable(entry.Key) == entry.Value, "Parent environment changed: " + entry.Key);
            return new FakeProcess(address);
        });
        Require((await isolated.StartAsync()).AbsoluteUri == address, "Embedded Python environment prevented Dashboard startup");
    }
    finally
    {
        foreach (var entry in originalEnvironment) Environment.SetEnvironmentVariable(entry.Key, entry.Value);
    }
    var process = new FakeProcess(address);
    int starts = 0;
    using var host = new DashboardRuntime(runtimePath, start => {
        starts++;
        Require(start.FileName == python, "Not the main Engine's checkout-bound Python");
        Require(start.WorkingDirectory == runtimePath, "Not the matching checkout's Dashboard source");
        Require(start.ArgumentList.SequenceEqual(new[] { "-B", "-X", "utf8", "-E", "-m", "dashboard", "--port", "0", "--no-browser" }),
            "Native Dashboard CLI arguments changed");
        Require(!start.UseShellExecute && start.CreateNoWindow, "Visible unmanaged shell");
        return process;
    });
    var first = host.StartAsync();
    var second = host.StartAsync();
    Require((await first).AbsoluteUri == address && await second == await first, "Duplicate opening did not reuse URL");
    Require(starts == 1, "Duplicate process started");
    Require(host.AllowsNavigation(new Uri(address)), "Own origin rejected");
    Require(host.AllowsNavigation(new Uri("http://127.0.0.1:18542/")), "Own page refresh rejected");
    foreach (var unsafeUrl in new[] { "http://127.0.0.1:18543/", "https://127.0.0.1:18542/", "http://localhost:18542/", "https://example.com/", "file:///C:/private" })
        Require(!host.AllowsNavigation(new Uri(unsafeUrl)), "Foreign navigation accepted: " + unsafeUrl);
    host.Dispose();
    Require(process.Stops == 1 && !host.AllowsNavigation(new Uri(address)), "Own process not stopped once");
    foreach (var invalid in new[] { "https://example.com/#" + token, "http://127.0.0.1:18542/#short", "http://127.0.0.1:18542/private#" + token, "http://user@127.0.0.1:18542/#" + token })
    {
        var bad = new FakeProcess(invalid);
        using var rejected = new DashboardRuntime(runtimePath, _ => bad);
        try { await rejected.StartAsync(); throw new Exception("Invalid server address accepted"); }
        catch (InvalidDataException) { }
        Require(bad.Stops == 1, "Failed startup leaked process");
    }
    var pending = new FakeProcess(null);
    using var cancelled = new DashboardRuntime(runtimePath, _ => pending);
    var startup = cancelled.StartAsync();
    cancelled.Dispose();
    try { await startup; throw new Exception("Closed host completed startup"); }
    catch (OperationCanceledException) { }
    Require(pending.Stops == 1, "Close during startup leaked process");
    string project = Path.Combine(runtimePath, "project");
    Directory.CreateDirectory(project);
    string model = Path.Combine(project, "saved.3dm");
    File.WriteAllText(model, "offline model placeholder; never opened by Rhino");
    var children = new List<FakeProcess>();
    var selectedDatabases = new List<string>();
    using var documents = new DashboardDocumentSession(database => new DashboardRuntime(runtimePath, start => {
        Require(start.ArgumentList.TakeLast(2).SequenceEqual(new[] { "--", database }),
            "Current project DB was not passed as a literal CLI argument");
        selectedDatabases.Add(database);
        var child = new FakeProcess(address);
        children.Add(child);
        return child;
    }, database));
    Require(documents.Select(null, 1).DatabasePath == null, "Unsaved document has a database");
    Require(documents.Runtime == null, "Unsaved document started a server");
    Require(documents.Select(model, 2).DatabasePath == null, "Missing DB was created or selected");
    Require(!Directory.Exists(Path.Combine(project, ".almond")), "Resolving current document created storage");
    string storage = Path.Combine(project, ".almond");
    Directory.CreateDirectory(storage);
    string database = Path.Combine(storage, "scene.sqlite3");
    File.WriteAllText(database, "offline path fixture; Python reader is faked");
    var context = documents.Select(model, 2);
    Require(context.DatabasePath == database && context.Status.Contains(model), "Document/project identity missing");
    await documents.Runtime!.StartAsync();
    documents.Select(model, 2);
    await documents.Runtime!.StartAsync();
    Require(children.Count == 1, "Repeated passive display duplicated current project server");
    documents.Select(model, 2, reselect: true);
    Require(children[0].Stops == 1, "Explicit command did not clear a potentially manually selected DB");
    await documents.Runtime!.StartAsync();
    Require(children.Count == 2 && selectedDatabases.All(value => value == database), "Command did not reselect current DB");
    documents.Select(null, 3);
    Require(children[1].Stops == 1 && documents.Runtime == null, "Unsaved document switch retained previous DB");
    documents.Select(model, 2);
    await documents.Runtime!.StartAsync();
    using (new FileStream(database, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
    {
        Require(documents.Select(model, 2).DatabasePath == null, "Unreadable DB selected");
        Require(children[2].Stops == 1 && documents.Runtime == null, "Access failure retained previous DB");
    }
    documents.Select(model, 2);
    await documents.Runtime!.StartAsync();
    Require(File.ReadAllText(database) == "offline path fixture; Python reader is faked", "DB bytes were changed");
    File.Delete(database);
    Require(documents.Select(model, 2).DatabasePath == null && documents.Runtime == null, "Deleted DB retained previous data");
    Require(children[3].Stops == 1 && !File.Exists(database), "Deleted DB recreated or child leaked");
    string nextProject = Path.Combine(runtimePath, "next-project");
    Directory.CreateDirectory(Path.Combine(nextProject, ".almond"));
    string nextModel = Path.Combine(nextProject, "next.3dm");
    File.WriteAllText(nextModel, "offline next model placeholder");
    string nextDatabase = Path.Combine(nextProject, ".almond", "scene.sqlite3");
    File.WriteAllText(nextDatabase, "second project bytes");
    Require(documents.Select(nextModel, 4).DatabasePath == nextDatabase, "Document switch did not select new project");
    await documents.Runtime!.StartAsync();
    Require(selectedDatabases[^1] == nextDatabase, "New document DB did not reach launcher");
    var nextRuntime = documents.Runtime;
    string sameProjectModel = Path.Combine(nextProject, "second.3dm");
    File.WriteAllText(sameProjectModel, "offline same project model placeholder");
    Require(documents.Select(sameProjectModel, 5).DocumentPath == sameProjectModel && documents.Runtime == nextRuntime,
        "Same project document did not update identity while reusing DB");
    Require(!Directory.Exists(Path.Combine(nextProject, ".almond", ".sessions")), "Document selection allocated an Almond session");
    Console.WriteLine("Dashboard host contracts passed: launcher, duplicate start, URL isolation, startup failure, shutdown and current-document DB selection.");
}
finally { Directory.Delete(fixtureRoot, true); }

sealed class FakeProcess(string? address) : IDashboardProcess
{
    public int Stops;
    public bool Running => Stops == 0;
    public async Task<string> ReadAddressAsync(CancellationToken cancellation)
    {
        if (address != null) return address;
        await Task.Delay(Timeout.Infinite, cancellation);
        return "";
    }
    public void Dispose() => Stops++;
}
