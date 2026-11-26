using System.Buffers.Binary;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using AlmondEngine;
using Rhino;

var root = Directory.CreateDirectory(Path.GetFullPath(args.Single())).FullName;
CheckStorageLease(root);
await CheckNativeDispatch(root);

static void CheckStorageLease(string root)
{
    var storage = Directory.CreateDirectory(Path.Combine(root, "lease")).FullName;
    var legacyLock = Path.Combine(storage, "mcp.lock");

    // Modern sessions can coexist. Exclusive legacy maintenance must wait until both release.
    using (SharedStorageLease.Acquire(storage))
    {
        using (SharedStorageLease.Acquire(storage))
        {
            ExpectConflict(() => File.Open(legacyLock, FileMode.Open, FileAccess.ReadWrite, FileShare.None));
        }

        ExpectConflict(() => File.Open(legacyLock, FileMode.Open, FileAccess.ReadWrite, FileShare.None));
    }

    using var exclusive = File.Open(legacyLock, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
    ExpectConflict(() => SharedStorageLease.Acquire(storage));
    using var earlierLock = File.Open(Path.Combine(storage, "rhino.lock"), FileMode.Open,
        FileAccess.ReadWrite, FileShare.None);
    Console.WriteLine("PASS: shared Rhino storage and exclusive legacy maintenance");
}

static void ExpectConflict(Func<IDisposable> acquire)
{
    try
    {
        using var acquired = acquire();
    }
    catch (IOException)
    {
        return;
    }

    throw new InvalidOperationException("Exclusive storage acquisition overlapped an active lease.");
}

static async Task CheckNativeDispatch(string root)
{
    const uint documentSerial = 17;
    const int storageProtocol = 2;
    const string responsePayload = """{"changed":true}""";
    var model = Path.Combine(root, "fixture.3dm");
    File.WriteAllText(model, "Saved path for the session fixture.");
    var token = NewId();
    var operation = NewId();
    var paths = SessionFiles.Paths(model, "A", token, create: true);
    var operationTemp = Directory.CreateDirectory(Path.Combine(paths.CallRoot, operation)).FullName;
    var original = new RhinoDoc { Path = model, RuntimeSerialNumber = documentSerial };
    RhinoDoc.ActiveDoc = original;
    var plugin = new DocumentHandler(root, responsePayload);
    Rhino.PlugIns.PlugIn.Loaded = plugin;
    var callbacks = Channel.CreateUnbounded<Action>();
    using var process = Process.GetCurrentProcess();
    var ticks = process.StartTime.ToUniversalTime().Ticks.ToString();
    var port = GetLoopbackPort();

    SessionFiles.WriteJson(paths.ReadyPath, new
    {
        schema = "almond-project", storage_protocol = storageProtocol, token, valid = true, pid = process.Id,
        process_start_ticks = ticks, document_serial = documentSerial, port, label = "A",
        model_path = model, document_path = model, storage = paths.Storage, temp = paths.Temp,
        session_dir = paths.SessionDir, ready_path = paths.ReadyPath
    });
    SessionFiles.WriteJson(paths.WorkerPath, new
    {
        schema = "almond-worker", token, pid = process.Id, process_start_ticks = ticks,
        library_dirs = plugin.LibraryDirectories
    });
    SessionFiles.WriteJson(paths.OperationPath, new
    {
        schema = "almond-operation", token, operation_id = operation, state = "running",
        worker_pid = process.Id, worker_start_ticks = ticks, temp = operationTemp
    });

    using var bridge = new BoundBridge(port, paths.ReadyPath, token, model, documentSerial,
        new RhinoBridgeTarget(), action => callbacks.Writer.TryWrite(action));
    bridge.Start();
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));

    try
    {
        using (var foreign = new TcpClient())
        {
            var reply = await SendRequest(foreign, NewId(), NewId());
            Require(reply.GetProperty("completion_status").GetString() == "rejected", "Foreign token reached native work.");
            Require(!callbacks.Reader.TryRead(out _), "Foreign token queued work.");
        }

        using (var replaced = new TcpClient())
        {
            var requestId = NewId();
            var reply = SendRequest(replaced, token, requestId);
            var callback = await callbacks.Reader.ReadAsync(timeout.Token);
            using (var receipt = SessionFiles.ReadJson(paths.NativePath))
            {
                Require(receipt.RootElement.GetProperty("completion_status").GetString() == "running",
                    "Durable status marked queued work complete.");
            }

            // Reopening the same path produces a different Rhino document.
            var reopened = new RhinoDoc { Path = model, RuntimeSerialNumber = documentSerial + 1 };
            RhinoDoc.ActiveDoc = reopened;
            callback();
            Require((await reply).GetProperty("completion_status").GetString() == "rejected",
                "A request queued for the prior document instance succeeded.");
            Require(!original.Changed && !reopened.Changed, "A stale request modified a document.");
        }

        RhinoDoc.ActiveDoc = original;
        using var sameDocument = new TcpClient();
        var acceptedId = NewId();
        var accepted = SendRequest(sameDocument, token, acceptedId);
        (await callbacks.Reader.ReadAsync(timeout.Token))();
        var completed = await accepted;
        Require(completed.GetProperty("completion_status").GetString() == "completed" &&
            completed.GetProperty("request_id").GetString() == acceptedId &&
            completed.GetProperty("payload").GetString() == responsePayload && original.Changed,
            "The authenticated requester did not receive the bound document's completed mutation.");
        Console.WriteLine("PASS: authenticated native work remains bound to its queued document");

        await CheckExternalDrain(bridge, paths, documentSerial, token, process, timeout.Token);
    }
    finally
    {
        bridge.Stop();
        var deadline = Stopwatch.StartNew();
        while (!bridge.IsDrained && deadline.Elapsed < TimeSpan.FromSeconds(10))
        {
            if (callbacks.Reader.TryRead(out var callback))
            {
                callback();
            }

            await Task.Delay(10);
        }
    }

    async Task<JsonElement> SendRequest(TcpClient client, string session, string request)
    {
        await client.ConnectAsync(IPAddress.Loopback, port, timeout.Token);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new
        {
            schema = "almond-native-request", storage_protocol = storageProtocol, token = session,
            operation_id = operation, request_id = request, payload = """{"type":"fixture_change"}"""
        });
        using var stream = client.GetStream();
        var size = new byte[sizeof(int)];
        BinaryPrimitives.WriteInt32BigEndian(size, bytes.Length);
        await stream.WriteAsync(size, timeout.Token);
        await stream.WriteAsync(bytes, timeout.Token);
        await stream.ReadExactlyAsync(size, timeout.Token);
        var reply = new byte[BinaryPrimitives.ReadInt32BigEndian(size)];
        await stream.ReadExactlyAsync(reply, timeout.Token);
        using var json = JsonDocument.Parse(reply);
        return json.RootElement.Clone();
    }
}

static async Task CheckExternalDrain(BoundBridge bridge, SessionPaths paths, uint serial, string token,
    Process process, CancellationToken timeout)
{
    var startTicks = process.StartTime.ToUniversalTime().Ticks;
    var operation = NewId();
    var request = NewId();
    var nonce = NewId();
    var hash = new string('a', 64);
    var target = new
    {
        pid = process.Id, process_start_ticks = startTicks.ToString(),
        document_serial = serial, model_path = paths.ModelPath, pipe_id = "fixture"
    };
    var requestDirectory = Directory.CreateDirectory(Path.Combine(paths.CallRoot, operation, "rhinocode", request));
    var completion = Path.Combine(requestDirectory.FullName, "complete.json");
    SessionFiles.WriteJson(paths.RhinocodePath, new
    {
        schema = "almond-rhinocode-execution", version = 1, token, operation_id = operation,
        request_id = request, nonce, source_hash = hash, language = "python", target,
        // The child process has exited. Its PID now identifies a different process.
        child = new { pid = process.Id, process_start_ticks = (startTicks - 1).ToString() }
    });
    try
    {
        bridge.Stop();

        // Both TCP and the supervisor have finished. Native execution still owns the session.
        Require(bridge.Pending > 0 && !bridge.IsDrained, "Stopping released native work without a completion receipt.");
        PublishReceipt(NewId());
        Require(bridge.Pending > 0 && !bridge.IsDrained, "A foreign completion receipt released native work.");

        PublishReceipt(nonce);
        while (!bridge.IsDrained)
        {
            await Task.Delay(10, timeout);
        }

        Console.WriteLine("PASS: native completion releases only the matching RhinoCode request");
    }
    finally
    {
        File.Delete(paths.RhinocodePath);
    }

    void PublishReceipt(string receiptNonce) => SessionFiles.WriteJson(completion, new
    {
        schema = "almond-rhinocode-completion", version = 1, token, operation_id = operation,
        request_id = request, nonce = receiptNonce, source_hash = hash, target, execution_complete = true,
        status = "success", mutation_state = "completed"
    });
}

static int GetLoopbackPort()
{
    var listener = new TcpListener(IPAddress.Loopback, 0);
    listener.Start();
    try
    {
        return ((IPEndPoint)listener.LocalEndpoint).Port;
    }
    finally
    {
        listener.Stop();
    }
}

static string NewId() => Guid.NewGuid().ToString("N");

static void Require(bool condition, string detail)
{
    if (!condition)
    {
        throw new InvalidOperationException(detail);
    }
}

sealed class DocumentHandler(string root, string response) : Rhino.PlugIns.PlugIn, IBridgeProvider, IBridgeRequestHandler
{
    public IBridgeRequestHandler RequestHandler => this;

    public IReadOnlyDictionary<string, string> LibraryDirectories { get; } = new Dictionary<string, string>
    {
        ["RHINO_MCP_LIBRARY_DIR"] = root,
        ["RHINO_MCP_CAPSULE_DIR"] = root,
        ["RHINO_MCP_DRAWING_ASSET_DIR"] = root
    };

    public string HandleRequest(BridgeDispatchContext context, string request)
    {
        context.Document.Changed = true;
        return response;
    }
}
