using System.Buffers.Binary;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using AlmondEngine;
using Rhino;

string root = Path.GetFullPath(args.Single());
Directory.CreateDirectory(root);
foreach (var unavailable in new Rhino.PlugIns.PlugIn?[] { null, new Rhino.PlugIns.PlugIn() })
{
    Rhino.PlugIns.PlugIn.Loaded = unavailable;
    try { _ = new RhinoBridgeTarget(); throw new Exception("Missing/incompatible provider accepted"); }
    catch (InvalidOperationException) { }
}
await Run("success", false, false);
await Run("changed document", true, false);
await Run("failure after entry", false, true);
await Run("receipt sharing violation", false, false, true);
await Run("stop while queued", false, false, false, true);
var original = new RhinoDoc { Path = Path.Combine(root, "postcheck.3dm"), RuntimeSerialNumber = 71 };
RhinoDoc.ActiveDoc = original;
RhinoAlmondBridge.Leaf.OnObservation = () => RhinoDoc.ActiveDoc = new RhinoDoc { Path = original.Path, RuntimeSerialNumber = 72 };
try
{
    new RhinoAlmondBridge.BridgeServer().HandleRequest(new BridgeDispatchContext(original, original.Path, 71,
        Guid.NewGuid().ToString("N"), Guid.NewGuid().ToString("N"), Guid.NewGuid().ToString("N")), "{\"type\":\"get_rhino_context\"}");
    throw new Exception("BridgeServer omitted post-handler document validation");
}
catch (InvalidOperationException) { }
Require(ReferenceEquals(RhinoAlmondBridge.Leaf.Document, original), "BridgeServer reacquired a different document");
RhinoAlmondBridge.Leaf.OnObservation = null;
RhinoDoc.ActiveDoc = original;
var viewRequest = new RhinoAlmondBridge.BridgeServer().HandleRequest(new BridgeDispatchContext(original, original.Path, 71,
    Guid.NewGuid().ToString("N"), Guid.NewGuid().ToString("N"), Guid.NewGuid().ToString("N")), "{\"type\":\"manipulate_view\",\"operation\":\"zoom\"}");
Require(JsonDocument.Parse(viewRequest).RootElement.GetProperty("operation").GetString() == "zoom",
    "BridgeServer did not route relative view manipulation to the fixed typed handler");
Console.WriteLine("PASS: production BoundBridge TCP authentication, typed document dispatch, callback completion and failure drain");

async Task Run(string scenario, bool changeDocument, bool fail, bool failReceipt = false, bool stopQueued = false)
{
    string folder = Path.Combine(root, Guid.NewGuid().ToString("N"));
    Directory.CreateDirectory(folder);
    string model = Path.Combine(folder, "fixture.3dm");
    File.WriteAllText(model, "fixture path only, never opened in Rhino");
    string token = Guid.NewGuid().ToString("N"), operation = Guid.NewGuid().ToString("N"), request = Guid.NewGuid().ToString("N");
    var paths = SessionFiles.Paths(model, "A", token, true);
    var doc = new RhinoDoc { Path = model, RuntimeSerialNumber = 17 };
    RhinoDoc.ActiveDoc = doc;
    foreach (string variable in new[] { "RHINO_MCP_LIBRARY_DIR", "RHINO_MCP_CAPSULE_DIR", "RHINO_MCP_DRAWING_ASSET_DIR" })
        Environment.SetEnvironmentVariable(variable, Path.GetFullPath("data"));
    var plugin = new FixturePlugin();
    Rhino.PlugIns.PlugIn.Loaded = plugin;
    var queue = Channel.CreateUnbounded<Action>();
    using var self = Process.GetCurrentProcess();
    string ticks = self.StartTime.ToUniversalTime().Ticks.ToString();
    var probe = new TcpListener(IPAddress.Loopback, 0); probe.Start();
    int port = ((IPEndPoint)probe.LocalEndpoint).Port; probe.Stop();
    Directory.CreateDirectory(Path.Combine(paths.CallRoot, operation));
    SessionFiles.WriteJson(paths.ReadyPath, new {
        schema = "almond-project", storage_protocol = 2, token, valid = true, pid = self.Id,
        process_start_ticks = ticks, document_serial = "17", port, label = "A", model_path = model,
        document_path = model, storage = paths.Storage, temp = paths.Temp, session_dir = paths.SessionDir, ready_path = paths.ReadyPath
    });
    SessionFiles.WriteJson(paths.WorkerPath, new { schema = "almond-worker", token, pid = self.Id, process_start_ticks = ticks, library_dirs = plugin.LibraryDirectories });
    SessionFiles.WriteJson(paths.OperationPath, new { schema = "almond-operation", token, operation_id = operation,
        state = "running", worker_pid = self.Id, worker_start_ticks = ticks, temp = Path.Combine(paths.CallRoot, operation) });
    using var bridge = new BoundBridge(port, paths.ReadyPath, token, model, 17,
        new RhinoBridgeTarget(), action => queue.Writer.TryWrite(action));
    bridge.Start();
    FileStream? receiptLock = null;
    try
    {
        // The old inner payload remains accepted inside its authenticated envelope; a bare payload does not.
        using (var bare = new TcpClient())
        {
            await bare.ConnectAsync(IPAddress.Loopback, port);
            await Write(bare.GetStream(), "{\"type\":\"execute\",\"script\":\"legacy payload\"}");
            var rejected = await Read(bare.GetStream());
            Require(rejected.GetProperty("completion_status").GetString() == "rejected", "Bare unauthenticated payload executed");
        }
        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, port);
        string payload = "{\"type\":\"get_rhino_context\",\"script\":\"legacy payload\"}";
        await Write(client.GetStream(), JsonSerializer.Serialize(new { schema = "almond-native-request", storage_protocol = 2,
            token, operation_id = operation, request_id = request, payload }));
        var response = Read(client.GetStream());
        var callback = await queue.Reader.ReadAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(10));
        using (var pending = JsonDocument.Parse(File.ReadAllText(paths.NativePath)))
            Require(pending.RootElement.GetProperty("pending").GetInt32() == 1 &&
                pending.RootElement.GetProperty("completion_status").GetString() == "running", "Queued native callback acknowledged completion");
        if (changeDocument) RhinoDoc.ActiveDoc = new RhinoDoc { Path = model, RuntimeSerialNumber = 18 };
        if (stopQueued)
        {
            bridge.Stop();
            Require(!bridge.IsDrained && bridge.Pending > 0, "Stop released a queued native callback");
        }
        plugin.OnHandle = context => {
            Require(ReferenceEquals(context.Document, doc) && context.ModelPath == model && context.DocumentSerial == 17,
                "The handler lost the authenticated document");
            Require(context.SessionToken == token && context.OperationId == operation && context.RequestId == request,
                "The handler lost the authenticated request identity");
            Require(!response.IsCompleted && bridge.Pending > 0, "Completion escaped before the handler finished");
            using var current = JsonDocument.Parse(File.ReadAllText(paths.NativePath));
            Require(current.RootElement.GetProperty("phase").GetString() == "running", "Native running receipt missing");
            if (failReceipt) receiptLock = new FileStream(paths.NativePath, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (fail) throw new IOException("Fixture failure after native entry");
        };
        var timer = Stopwatch.StartNew();
        callback();
        if (failReceipt || stopQueued)
        {
            if (failReceipt)
            {
                using var retained = JsonDocument.Parse(File.ReadAllText(paths.NativePath));
                Require(retained.RootElement.GetProperty("completion_status").GetString() == "running",
                    "Failed receipt durability exposed completed native state");
                Console.WriteLine("Receipt contention callback milliseconds: " + timer.ElapsedMilliseconds);
            }
            else Require(plugin.Calls == 0, "Stopped queued callback executed native code");
            try { await response.WaitAsync(TimeSpan.FromSeconds(10)); throw new Exception("Stopped transport acknowledged completion"); }
            catch (EndOfStreamException) { }
            return;
        }
        var reply = await response.WaitAsync(TimeSpan.FromSeconds(10));
        string expected = changeDocument ? "rejected" : fail ? "failed" : "completed";
        Require(reply.GetProperty("completion_status").GetString() == expected, scenario + " status mismatch");
        Require(plugin.Calls == (changeDocument ? 0 : 1), "Changed document reached native mutation");
        if (!changeDocument && !fail) Require(reply.GetProperty("payload").GetString() == payload, "Inner payload changed");
    }
    finally
    {
        receiptLock?.Dispose();
        bridge.Stop();
        var deadline = Stopwatch.StartNew();
        while (!bridge.IsDrained && deadline.Elapsed < TimeSpan.FromSeconds(10)) await Task.Delay(10);
        Require(bridge.IsDrained, "Native ownership did not drain");
    }
}

static async Task Write(NetworkStream stream, string value)
{
    byte[] data = Encoding.UTF8.GetBytes(value), header = new byte[4];
    BinaryPrimitives.WriteInt32BigEndian(header, data.Length);
    await stream.WriteAsync(header); await stream.WriteAsync(data);
}
static async Task<JsonElement> Read(NetworkStream stream)
{
    byte[] header = new byte[4]; await stream.ReadExactlyAsync(header);
    byte[] data = new byte[BinaryPrimitives.ReadInt32BigEndian(header)]; await stream.ReadExactlyAsync(data);
    using var value = JsonDocument.Parse(data); return value.RootElement.Clone();
}
static void Require(bool value, string message) { if (!value) throw new Exception(message); }

sealed class FixturePlugin : Rhino.PlugIns.PlugIn, IBridgeProvider, IBridgeRequestHandler
{
    public IBridgeRequestHandler RequestHandler => this;
    public IReadOnlyDictionary<string, string> LibraryDirectories { get; } = new Dictionary<string, string> {
        ["RHINO_MCP_LIBRARY_DIR"] = Path.GetFullPath("data"), ["RHINO_MCP_CAPSULE_DIR"] = Path.GetFullPath("data"),
        ["RHINO_MCP_DRAWING_ASSET_DIR"] = Path.GetFullPath("data") };
    public Action<BridgeDispatchContext>? OnHandle;
    public int Calls;
    readonly RhinoAlmondBridge.BridgeServer server = new();
    public string HandleRequest(BridgeDispatchContext context, string request)
    {
        Calls++; OnHandle?.Invoke(context); return server.HandleRequest(context, request);
    }
}
