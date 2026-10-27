using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Text.Json;
using AlmondEngine;

internal static class Program
{
    static readonly string OriginalResponse = "{\"status\":\"success\",\"objects\":[\"one\",\"two\"],\"extra\":{\"kept\":true}}";

    static async Task<int> Main(string[] args)
    {
        if (args.Length == 3 && args[0] == "--relay-host")
            return await RelayHost(int.Parse(args[1]), args[2]);
        if (args.Length == 4 && args[0] == "--foreign-client")
        {
            var (client, response) = await Send(int.Parse(args[1]), args[2], args[3]);
            using (client)
                return (await response).Contains("does not own", StringComparison.Ordinal) ? 0 : 2;
        }
        var tests = new (string Name, Func<Task> Run)[] {
            ("shared paths, fresh generations, role locks and legacy exclusion", PathsAndLeases),
            ("user C# reaches the native handler unchanged", UserScriptUnchanged),
            ("native library caches are checked without modification", LibraryRoots),
            ("listener startup can precede ready publication", BeforeReady),
            ("native responses and operation receipts preserve their contract", ResponseContract),
            ("old worker PID and token leave the current receipt untouched", ForeignWorker),
            ("delayed old frames cannot become the next operation", DelayedOperation),
            ("duplicate request IDs execute at most once", DuplicateRequest),
            ("raw and malformed envelopes leave the receipt untouched", InvalidEnvelopes),
            ("stale operation and document are rejected at UI entry", RevalidateAtUi),
            ("multiple native requests remain counted until every completion", AggregatePending),
            ("EOF and Stop cannot drain a queued UI callback early", StopQueued),
            ("EOF and Stop cannot drain a running native handler early", StopRunning),
            ("Stop cancels an accepted partial frame and drains it", StopReceiving),
            ("one OS owner per Rhino process survives until Dispose", ProcessOwnership),
            ("receipt publication failure stops dispatch before mutation", ReceiptFailure),
            ("a UI-finally publication failure cannot borrow a prior acknowledgement", FinallyReceiptFailure),
            ("ambiguous UI dispatch failure retains pending work", AmbiguousDispatch)
        };
        int passed = 0;
        foreach (var (name, run) in tests)
        {
            try { await run(); Console.WriteLine("PASS " + name); passed++; }
            catch (Exception ex) { Console.Error.WriteLine("FAIL " + name + "\n" + ex); return 1; }
        }
        Console.WriteLine("PASS " + passed + " native fixtures; no Rhino document or installed package was loaded.");
        return 0;
    }

    static async Task<int> RelayHost(int workerPid, string workerTicks)
    {
        // A disposable fake document/handler on an ephemeral port, never a Rhino host.
        await using var fixture = new Fixture(workerPid, workerTicks);
        fixture.Start();
        Console.OutputEncoding = new UTF8Encoding(false);
        Console.WriteLine(JsonSerializer.Serialize(new {
            schema = "almond-native-fixture", port = fixture.Port, token = fixture.Token,
            operation_id = fixture.Operation, session_dir = fixture.Paths.SessionDir,
            native_path = fixture.Paths.NativePath, ready_path = fixture.Paths.ReadyPath,
            host_pid = Environment.ProcessId, worker_pid = workerPid
        }));
        Console.Out.Flush();
        var command = Task.Run(() => Console.In.ReadLine());
        while (!command.IsCompleted)
        {
            while (fixture.Ui.Count != 0) fixture.Ui.RunOne();
            await Task.WhenAny(command, Task.Delay(10));
        }
        string? value = await command;
        if (value is not (null or "stop")) throw new IOException("Unknown fixture command.");
        return 0;
    }

    static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    static void Throws<T>(Action action) where T : Exception
    {
        try { action(); }
        catch (T) { return; }
        throw new InvalidOperationException("Expected " + typeof(T).Name);
    }

    static async Task Until(Func<bool> condition, string message)
    {
        var timer = Stopwatch.StartNew();
        while (!condition())
        {
            if (timer.Elapsed > TimeSpan.FromSeconds(10)) throw new TimeoutException(message);
            await Task.Delay(10);
        }
    }

    static string NewRoot()
    {
        var path = Path.Combine(Path.GetTempPath(), "Almond-NativeFixture-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        return path;
    }

    static Task PathsAndLeases()
    {
        var root = NewRoot();
        try
        {
            var firstModel = Path.Combine(root, "First.3dm");
            var secondModel = Path.Combine(root, "Second.3dm");
            File.WriteAllText(firstModel, "fixture");
            File.WriteAllText(secondModel, "fixture");
            string token = Guid.NewGuid().ToString("N");
            var first = SessionFiles.Paths(firstModel, "A", token, true);
            var second = SessionFiles.Paths(secondModel, "B", Guid.NewGuid().ToString("N"), true);
            Check(first.Storage == second.Storage && first.StateDb == second.StateDb && first.Temp == second.Temp,
                "Models in one folder must share DB and tmp.");
            Check(first.StateDb == Path.Combine(root, ".almond", "scene.sqlite3"),
                "A saved model must use its own project's SQLite database filename.");
            var otherProject = Path.Combine(root, "OtherProject");
            Directory.CreateDirectory(otherProject);
            var otherModel = Path.Combine(otherProject, "New.3dm");
            File.WriteAllText(otherModel, "fixture");
            var other = SessionFiles.Paths(otherModel, "C", Guid.NewGuid().ToString("N"), true);
            Check(other.StateDb == Path.Combine(otherProject, ".almond", "scene.sqlite3") && other.StateDb != first.StateDb,
                "An unrelated new project must not reuse another project's database.");
            Check(first.SessionDir != second.SessionDir && first.CallRoot != second.CallRoot, "Connection metadata must be isolated.");
            Throws<System.ComponentModel.Win32Exception>(() => SessionFiles.Paths(firstModel, "A", token, true));
            File.WriteAllText(Path.Combine(first.Storage, "launcher.lock"), "preserve");
            using (var one = new SharedStorageLease(first.Storage))
            using (var two = SharedStorageLease.Acquire(second.Storage))
            using (var roleOne = new FileStream(first.RhinoLock, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            using (var roleTwo = new FileStream(second.RhinoLock, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            {
                foreach (var name in new[] { "launcher.lock", "rhino.lock", "mcp.lock" })
                    Throws<IOException>(() => new FileStream(Path.Combine(first.Storage, name), FileMode.OpenOrCreate,
                        FileAccess.ReadWrite, FileShare.None).Dispose());
                Throws<IOException>(() => new FileStream(first.RhinoLock, FileMode.Open, FileAccess.ReadWrite, FileShare.None).Dispose());
            }
            Check(File.ReadAllText(Path.Combine(first.Storage, "launcher.lock")) == "preserve", "Legacy locks were truncated.");
            using (var old = new FileStream(Path.Combine(first.Storage, "rhino.lock"), FileMode.Open,
                FileAccess.ReadWrite, FileShare.None))
            {
                Throws<IOException>(() => new SharedStorageLease(first.Storage).Dispose());
                using var released = new FileStream(Path.Combine(first.Storage, "launcher.lock"), FileMode.Open,
                    FileAccess.ReadWrite, FileShare.None);
            }
        }
        finally { Directory.Delete(root, true); }
        return Task.CompletedTask;
    }

    static async Task UserScriptUnchanged()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        var script = "var previous = File.ReadAllText(Path.Combine(Path.GetTempPath(), \"almond_matgroups.txt\")); " +
            "// Path.Combine(Path.GetTempPath(), \"almond_imported.txt\")\n" +
            "var report = System.IO.Path.Combine(System.IO.Path.GetTempPath(), \"almond_import_report.json\");";
        string payload = JsonSerializer.Serialize(new { type = "execute", script });
        string request = Guid.NewGuid().ToString("N");
        using var client = new TcpClient(AddressFamily.InterNetwork);
        await client.ConnectAsync(IPAddress.Loopback, fixture.Port);
        await Write(client, JsonSerializer.Serialize(new {
            schema = "almond-native-request", storage_protocol = 2, token = fixture.Token,
            operation_id = fixture.Operation, request_id = request, payload
        }));
        var response = Read(client, fixture.Token, fixture.Operation, request);
        await Until(() => fixture.Ui.Count == 1, "User script did not queue.");
        fixture.Ui.RunOne();
        Check(await response == OriginalResponse, "User script request failed.");
        Check(fixture.Target.LastRequest == payload, "Native transport rewrote user C#.");
    }

    static async Task BeforeReady()
    {
        await using var fixture = new Fixture();
        File.Delete(fixture.Paths.ReadyPath);
        fixture.Start();
        var before = File.ReadAllText(fixture.Paths.NativePath);
        var (client, response) = await Send(fixture);
        using (client) Check((await response).Contains("\"status\":\"error\"", StringComparison.Ordinal), "Missing ready state admitted a request.");
        await Until(() => fixture.Bridge.Pending == 0, "Unready request did not drain.");
        Check(fixture.Bridge.IsRunning && fixture.Target.Calls == 0, "Startup or dispatch contract failed.");
        Check(File.ReadAllText(fixture.Paths.NativePath) == before, "Unready request changed the receipt.");
    }

    static async Task ResponseContract()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        JsonElement reply = default;
        var (client, response) = await Send(fixture, inspect: value => reply = value);
        using (client)
        {
            await Until(() => fixture.Ui.Count == 1, "Request was not queued.");
            Check(fixture.Bridge.Pending == 1 && fixture.Receipt().GetProperty("pending").GetInt32() == 1, "Queued work was not counted.");
            long queuedSequence = fixture.Receipt().GetProperty("sequence").GetInt64();
            fixture.Ui.RunOne();
            Check(await response == OriginalResponse, "Original native response was rewritten.");
            await Until(() => fixture.Bridge.Pending == 0, "Completed request did not drain.");
            var receipt = fixture.Receipt();
            Check(receipt.GetProperty("operation_id").GetString() == fixture.Operation, "Wrong operation receipt.");
            Check(receipt.GetProperty("completion_status").GetString() == "completed", "Actual native completion was not published.");
            Check(receipt.GetProperty("sequence").GetInt64() > queuedSequence, "Receipt sequence did not advance.");
            Check(reply.GetProperty("native_sequence").GetInt64() > queuedSequence &&
                receipt.GetProperty("sequence").GetInt64() >= reply.GetProperty("native_sequence").GetInt64(), "Acknowledgement did not follow this UI finally.");
            Check(reply.GetProperty("request_id").GetString() == receipt.GetProperty("request_id").GetString(), "Receipt lost its request identity.");
            Check(fixture.OperationState() == "running", "Native idle must not seal the worker's logical operation.");
            Check(fixture.Target.Calls == 1 && fixture.Bridge.IsRunning, "Unexpected handler/lifetime state.");
        }
    }

    static async Task ForeignWorker()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        string original = File.ReadAllText(fixture.Paths.NativePath);
        var start = new ProcessStartInfo(Environment.ProcessPath!) { UseShellExecute = false, CreateNoWindow = true };
        if (string.Equals(Path.GetFileNameWithoutExtension(Environment.ProcessPath), "dotnet", StringComparison.OrdinalIgnoreCase))
            start.ArgumentList.Add(Assembly.GetExecutingAssembly().Location);
        start.ArgumentList.Add("--foreign-client");
        start.ArgumentList.Add(fixture.Port.ToString());
        start.ArgumentList.Add(fixture.Token);
        start.ArgumentList.Add(fixture.Operation);
        using (var child = Process.Start(start)!)
        {
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            try
            {
                await child.WaitForExitAsync(deadline.Token);
            }
            finally
            {
                if (!child.HasExited)
                {
                    child.Kill(entireProcessTree: true);
                    await child.WaitForExitAsync();
                }
            }
            Check(child.ExitCode == 0, "A different process was not rejected.");
        }
        await Until(() => fixture.Bridge.Pending == 0, "Rejected peer did not drain.");
        Check(File.ReadAllText(fixture.Paths.NativePath) == original, "A stale peer changed the current native receipt.");
        fixture.WriteWorker(Guid.NewGuid().ToString("N"));
        var (client, response) = await Send(fixture);
        using (client) Check((await response).Contains("generation changed", StringComparison.Ordinal), "Stale token was not rejected.");
        await Until(() => fixture.Bridge.Pending == 0, "Stale token did not drain.");
        Check(File.ReadAllText(fixture.Paths.NativePath) == original, "A stale token changed the current native receipt.");
        fixture.WriteWorker(fixture.Token);
        Check(fixture.Bridge.IsRunning && fixture.Target.Calls == 0, "Stale worker invalidated the current connection.");
    }

    static async Task RevalidateAtUi()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        var (client, response) = await Send(fixture);
        using (client)
        {
            await Until(() => fixture.Ui.Count == 1, "Request was not queued.");
            fixture.NewOperation();
            fixture.Ui.RunOne();
            Check((await response).Contains("operation changed", StringComparison.Ordinal), "Queued old operation executed.");
            await Until(() => fixture.Bridge.Pending == 0, "Rejected operation did not drain.");
        }
        Check(fixture.Target.Calls == 0, "Old operation reached the handler.");
        var (next, nextResponse) = await Send(fixture);
        using (next)
        {
            await Until(() => fixture.Ui.Count == 1, "New operation was not queued.");
            fixture.Target.DocumentValid = false;
            fixture.Ui.RunOne();
            Check((await nextResponse).Contains("document changed", StringComparison.Ordinal), "Changed document was not rejected.");
            await Until(() => fixture.Bridge.Pending == 0, "Rejected document did not drain.");
        }
        Check(fixture.Target.Calls == 0, "Changed document reached the handler.");
        fixture.Target.DocumentValid = true;
        var (third, thirdResponse) = await Send(fixture);
        using (third)
        {
            await Until(() => fixture.Ui.Count == 1, "Library check was not queued.");
            fixture.Target.LibrariesValid = false;
            fixture.Ui.RunOne();
            Check((await thirdResponse).Contains("library changed", StringComparison.Ordinal), "Changed library cache was not rejected.");
            await Until(() => fixture.Bridge.Pending == 0, "Rejected library cache did not drain.");
        }
        Check(fixture.Target.Calls == 0, "Changed library cache reached the handler.");
    }

    static async Task AggregatePending()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        var (one, first) = await Send(fixture);
        // Independent TCP clients need not reach the UI queue in send order.
        await Until(() => fixture.Ui.Count == 1, "First request was not queued.");
        var (two, second) = await Send(fixture);
        using (one)
        using (two)
        {
            await Until(() => fixture.Ui.Count == 2, "Both requests were not queued.");
            var firstAction = fixture.Ui.Take();
            try
            {
                fixture.Ui.RunOne();
                Check(await second == OriginalResponse, "Second response failed.");
                await Until(() => fixture.Bridge.Pending == 1, "Second request did not finish.");
                Check(fixture.Receipt().GetProperty("pending").GetInt32() == 1 &&
                    fixture.Receipt().GetProperty("completion_status").GetString() == "running", "Early completion hid outstanding native work.");
            }
            finally { firstAction(); }
            Check(await first == OriginalResponse, "First response failed.");
            await Until(() => fixture.Bridge.Pending == 0, "First request did not finish.");
            Check(fixture.Target.Calls == 2, "Requests did not execute exactly once.");
        }
    }

    static async Task StopQueued()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        var (client, response) = await Send(fixture);
        await Until(() => fixture.Ui.Count == 1, "Request was not queued.");
        client.Dispose();
        fixture.Bridge.Stop();
        Check(!fixture.Bridge.IsDrained && fixture.Bridge.Pending == 1, "EOF/Stop drained a queued delegate early.");
        Throws<InvalidOperationException>(() => fixture.Bridge.Dispose());
        fixture.Ui.RunOne();
        try { await response; } catch (Exception ex) when (ex is IOException or SocketException or ObjectDisposedException) { }
        await Until(() => fixture.Bridge.IsDrained, "Queued rejection did not drain.");
        Check(fixture.Target.Calls == 0, "Stopped queued request executed.");
    }

    static async Task StopRunning()
    {
        await using var fixture = new Fixture();
        using var entered = new ManualResetEventSlim();
        using var release = new ManualResetEventSlim();
        fixture.Target.Run = () => { entered.Set(); release.Wait(TimeSpan.FromSeconds(10)); return OriginalResponse; };
        fixture.Start();
        var (client, response) = await Send(fixture);
        await Until(() => fixture.Ui.Count == 1, "Request was not queued.");
        var run = Task.Run(fixture.Ui.RunOne);
        await Until(() => entered.IsSet, "Native handler did not begin.");
        try
        {
            client.Dispose();
            fixture.Bridge.Stop();
            Check(!fixture.Bridge.IsDrained && fixture.Bridge.Pending == 1, "EOF/Stop drained a running handler early.");
        }
        finally { release.Set(); }
        await run;
        try { await response; } catch (Exception ex) when (ex is IOException or SocketException or ObjectDisposedException) { }
        await Until(() => fixture.Bridge.IsDrained, "Completed running handler did not drain.");
        Check(fixture.Target.Calls == 1, "Native handler was retried or abandoned.");
    }

    static async Task StopReceiving()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        using var client = new TcpClient(AddressFamily.InterNetwork);
        await client.ConnectAsync(IPAddress.Loopback, fixture.Port);
        await Until(() => fixture.Bridge.Pending == 1, "Accepted connection was not counted.");
        fixture.Bridge.Stop();
        await Until(() => fixture.Bridge.IsDrained, "Partial frame held the transport forever.");
        Check(fixture.Target.Calls == 0, "Partial frame reached the handler.");
    }

    static async Task ProcessOwnership()
    {
        await using var first = new Fixture();
        await using var second = new Fixture();
        first.Start();
        Throws<IOException>(() => second.Start());
        first.Bridge.Stop();
        await Until(() => first.Bridge.IsDrained, "First listener did not drain.");
        Throws<IOException>(() => second.Start());
        first.Bridge.Dispose();
        second.Start();
        Check(second.Bridge.IsRunning, "Process ownership was not released by Dispose.");
    }

    static async Task ReceiptFailure()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        File.SetAttributes(fixture.Paths.NativePath, FileAttributes.ReadOnly);
        try
        {
            var (client, response) = await Send(fixture);
            using (client)
                try { await response; } catch (Exception ex) when (ex is IOException or SocketException or ObjectDisposedException) { }
            await Until(() => fixture.Bridge.IsDrained, "Receipt failure did not stop and drain.");
            Check(fixture.Target.Calls == 0 && !fixture.Bridge.IsRunning, "Native action executed without a trustworthy receipt.");
        }
        finally { File.SetAttributes(fixture.Paths.NativePath, FileAttributes.Normal); }
    }

    static Task LibraryRoots()
    {
        var expected = new Dictionary<string, string> {
            ["RHINO_MCP_LIBRARY_DIR"] = @"C:\fixture\library",
            ["RHINO_MCP_CAPSULE_DIR"] = @"C:\fixture\capsules",
            ["RHINO_MCP_DRAWING_ASSET_DIR"] = @"C:\fixture\drawing-assets"
        };
        var roots = JsonSerializer.SerializeToElement(expected);
        string[] values = { expected["RHINO_MCP_LIBRARY_DIR"], expected["RHINO_MCP_CAPSULE_DIR"],
            expected["RHINO_MCP_LIBRARY_DIR"], expected["RHINO_MCP_CAPSULE_DIR"], expected["RHINO_MCP_DRAWING_ASSET_DIR"] };
        var good = new LibraryServer(values);
        NativeLibraryRoots.Validate(good, roots);
        Check(good.Snapshot().SequenceEqual(values), "Library validation changed the cached roots.");
        for (int index = 0; index < values.Length; index++)
        {
            var changed = (string[])values.Clone();
            changed[index] += "-changed";
            var bad = new LibraryServer(changed);
            Throws<IOException>(() => NativeLibraryRoots.Validate(bad, roots));
            Check(bad.Snapshot().SequenceEqual(changed), "A mismatched library cache was rewritten.");
        }
        expected.Remove("RHINO_MCP_CAPSULE_DIR");
        Throws<IOException>(() => NativeLibraryRoots.Validate(good, JsonSerializer.SerializeToElement(expected)));
        Throws<IOException>(() => NativeLibraryRoots.Validate(new object(), roots));
        return Task.CompletedTask;
    }

    static async Task DelayedOperation()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        var (first, firstResponse) = await Send(fixture);
        using (first)
        {
            await Until(() => fixture.Ui.Count == 1, "First operation did not queue.");
            fixture.Ui.RunOne();
            Check(await firstResponse == OriginalResponse, "First operation failed.");
            await Until(() => fixture.Bridge.Pending == 0, "First operation did not drain.");
        }
        string oldOperation = fixture.Operation, oldRequest = Guid.NewGuid().ToString("N");
        using var delayed = new TcpClient(AddressFamily.InterNetwork);
        await delayed.ConnectAsync(IPAddress.Loopback, fixture.Port);
        byte[] frame = Encoding.UTF8.GetBytes(Envelope(fixture.Token, oldOperation, oldRequest));
        var header = new byte[4];
        BinaryPrimitives.WriteInt32BigEndian(header, frame.Length);
        await delayed.GetStream().WriteAsync(header);
        await Until(() => fixture.Bridge.Pending == 1, "Delayed frame was not accepted.");

        fixture.NewOperation();
        var (next, nextResponse) = await Send(fixture);
        using (next)
        {
            await Until(() => fixture.Ui.Count == 1, "Next operation did not queue.");
            fixture.Ui.RunOne();
            Check(await nextResponse == OriginalResponse, "Next operation failed.");
            await Until(() => fixture.Bridge.Pending == 1, "Next operation did not drain.");
        }
        string receipt = File.ReadAllText(fixture.Paths.NativePath);
        await delayed.GetStream().WriteAsync(frame);
        var rejected = await Read(delayed, fixture.Token, oldOperation, oldRequest);
        Check(rejected.Contains("stale operation", StringComparison.Ordinal), "The delayed request acquired the next operation's identity.");
        await Until(() => fixture.Bridge.Pending == 0, "Delayed old request did not drain.");
        Check(fixture.Target.Calls == 2 && fixture.Ui.Count == 0, "Delayed old request executed.");
        Check(File.ReadAllText(fixture.Paths.NativePath) == receipt, "A delayed old request changed the current receipt.");
    }

    static async Task DuplicateRequest()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        string requestId = Guid.NewGuid().ToString("N");
        var (first, firstResponse) = await Send(fixture, requestId);
        using (first)
        {
            await Until(() => fixture.Ui.Count == 1, "First request did not queue.");
            string queued = File.ReadAllText(fixture.Paths.NativePath);
            var (duplicate, duplicateResponse) = await Send(fixture, requestId);
            using (duplicate) Check((await duplicateResponse).Contains("already been accepted", StringComparison.Ordinal), "Concurrent duplicate was not rejected.");
            await Until(() => fixture.Bridge.Pending == 1, "Concurrent duplicate did not drain.");
            Check(File.ReadAllText(fixture.Paths.NativePath) == queued, "Duplicate changed the queued receipt.");
            fixture.Ui.RunOne();
            Check(await firstResponse == OriginalResponse, "First request failed.");
            await Until(() => fixture.Bridge.Pending == 0, "First request did not drain.");
        }
        string completed = File.ReadAllText(fixture.Paths.NativePath);
        var (late, lateResponse) = await Send(fixture, requestId);
        using (late) Check((await lateResponse).Contains("already been accepted", StringComparison.Ordinal), "Completed request ID was reused.");
        await Until(() => fixture.Bridge.Pending == 0, "Completed duplicate did not drain.");
        Check(fixture.Target.Calls == 1 && File.ReadAllText(fixture.Paths.NativePath) == completed, "A duplicate executed or changed the receipt.");
    }

    static async Task InvalidEnvelopes()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        string original = File.ReadAllText(fixture.Paths.NativePath);
        string requestId = Guid.NewGuid().ToString("N");
        string valid = Envelope(fixture.Token, fixture.Operation, requestId);
        var invalid = new[] {
            ("{\"action\":\"execute\",\"script\":\"// raw bypass\"}", "", "", ""),
            (valid.Replace("\"storage_protocol\":2", "\"storage_protocol\":\"2\""), fixture.Token, fixture.Operation, requestId),
            (valid.Insert(1, "\"token\":\"" + fixture.Token + "\","), fixture.Token, fixture.Operation, requestId),
            (Envelope(Guid.NewGuid().ToString("N"), fixture.Operation, requestId), "", fixture.Operation, requestId)
        };
        foreach (var (frame, expectedToken, operation, request) in invalid)
        {
            using var client = new TcpClient(AddressFamily.InterNetwork);
            await client.ConnectAsync(IPAddress.Loopback, fixture.Port);
            await Write(client, frame);
            string actualToken = expectedToken;
            if (operation.Length != 0 && actualToken.Length == 0)
                actualToken = JsonDocument.Parse(frame).RootElement.GetProperty("token").GetString()!;
            Check((await Read(client, actualToken, operation, request)).Contains("\"status\":\"error\"", StringComparison.Ordinal), "Invalid envelope was not rejected.");
            await Until(() => fixture.Bridge.Pending == 0, "Invalid envelope did not drain.");
            Check(File.ReadAllText(fixture.Paths.NativePath) == original, "Invalid envelope changed current receipt.");
        }
        Check(fixture.Target.Calls == 0 && fixture.Bridge.IsRunning, "Invalid envelopes affected native execution.");
    }

    static async Task FinallyReceiptFailure()
    {
        await using var fixture = new Fixture();
        fixture.Start();
        long acknowledged = 0;
        var (first, firstResponse) = await Send(fixture, inspect: value => acknowledged = value.GetProperty("native_sequence").GetInt64());
        using (first)
        {
            await Until(() => fixture.Ui.Count == 1, "First request did not queue.");
            fixture.Ui.RunOne();
            Check(await firstResponse == OriginalResponse, "First request failed.");
            await Until(() => fixture.Bridge.Pending == 0, "First request did not drain.");
        }
        Check(acknowledged > 0, "First request did not acknowledge its finally.");
        fixture.Target.Run = () => {
            File.SetAttributes(fixture.Paths.NativePath, FileAttributes.ReadOnly);
            return OriginalResponse;
        };
        try
        {
            var (second, secondResponse) = await Send(fixture);
            using (second)
            {
                await Until(() => fixture.Ui.Count == 1, "Second request did not queue.");
                fixture.Ui.RunOne();
                bool gotAcknowledgement = false;
                try { await secondResponse; gotAcknowledgement = true; }
                catch (Exception ex) when (ex is IOException or SocketException or ObjectDisposedException) { }
                Check(!gotAcknowledgement, "A failed finally publication borrowed an earlier acknowledgement.");
                await Until(() => fixture.Bridge.IsDrained, "Failed finally publication did not drain.");
            }
            Check(fixture.Target.Calls == 2, "Actual native completion was lost.");
        }
        finally { File.SetAttributes(fixture.Paths.NativePath, FileAttributes.Normal); }
    }

    static async Task AmbiguousDispatch()
    {
        await using var fixture = new Fixture();
        fixture.Ui.ThrowAfterQueue = true;
        fixture.Start();
        var (client, response) = await Send(fixture);
        using (client)
        {
            await Until(() => fixture.Ui.Count == 1 && !fixture.Bridge.IsRunning, "Dispatch exception was not detected.");
            Check(fixture.Bridge.Pending == 1 && !fixture.Bridge.IsDrained && !response.IsCompleted,
                "An ambiguous dispatch exception abandoned its queued delegate.");
            fixture.Ui.RunOne();
            try { await response; } catch (Exception ex) when (ex is IOException or SocketException or ObjectDisposedException) { }
            await Until(() => fixture.Bridge.IsDrained, "Rejected ambiguous delegate did not drain.");
        }
        Check(fixture.Target.Calls == 0, "A faulted dispatcher reached the native handler.");
    }

    static string Envelope(string token, string operation, string request) => JsonSerializer.Serialize(new {
        schema = "almond-native-request", storage_protocol = 2, token, operation_id = operation, request_id = request,
        payload = "{\"action\":\"execute\",\"script\":\"// fixture 한글\"}"
    });

    static Task<(TcpClient Client, Task<string> Response)> Send(Fixture fixture, string? requestId = null,
        Action<JsonElement>? inspect = null) => Send(fixture.Port, fixture.Token, fixture.Operation, requestId, inspect);

    static async Task<(TcpClient Client, Task<string> Response)> Send(int port, string token, string operation,
        string? requestId = null, Action<JsonElement>? inspect = null)
    {
        string request = requestId ?? Guid.NewGuid().ToString("N");
        var client = new TcpClient(AddressFamily.InterNetwork);
        await client.ConnectAsync(IPAddress.Loopback, port);
        await Write(client, Envelope(token, operation, request));
        return (client, Read(client, token, operation, request, inspect));
    }

    static async Task Write(TcpClient client, string frame)
    {
        var data = Encoding.UTF8.GetBytes(frame);
        var header = new byte[4];
        BinaryPrimitives.WriteInt32BigEndian(header, data.Length);
        await client.GetStream().WriteAsync(header);
        await client.GetStream().WriteAsync(data);
    }

    static async Task<string> Read(TcpClient client, string token, string operation, string request,
        Action<JsonElement>? inspect = null)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var header = new byte[4];
        await client.GetStream().ReadExactlyAsync(header, timeout.Token);
        var data = new byte[BinaryPrimitives.ReadInt32BigEndian(header)];
        await client.GetStream().ReadExactlyAsync(data, timeout.Token);
        using var json = JsonDocument.Parse(data);
        var value = json.RootElement;
        Check(value.GetProperty("schema").GetString() == "almond-native-response" &&
            value.GetProperty("storage_protocol").GetInt32() == 2 &&
            value.GetProperty("token").GetString() == token &&
            value.GetProperty("operation_id").GetString() == operation &&
            value.GetProperty("request_id").GetString() == request, "Native acknowledgement identity changed.");
        string status = value.GetProperty("completion_status").GetString()!;
        long sequence = value.GetProperty("native_sequence").GetInt64();
        Check(status is "completed" or "rejected" or "failed", "Invalid native completion status.");
        Check(sequence >= 0 && (status == "rejected" || sequence > 0), "Native completion lacks this request's finally sequence.");
        inspect?.Invoke(value.Clone());
        return value.GetProperty("payload").GetString()!;
    }

    sealed class UiQueue
    {
        readonly ConcurrentQueue<Action> queue = new();
        internal int Count => queue.Count;
        internal bool ThrowAfterQueue;
        internal void Post(Action action)
        {
            queue.Enqueue(action);
            if (ThrowAfterQueue) throw new IOException("Fixture dispatch failed after enqueue.");
        }
        internal Action Take() => queue.TryDequeue(out var action) ? action : throw new InvalidOperationException("No queued callback.");
        internal void RunOne() => Take()();
    }

    sealed class Target : IBridgeTarget
    {
        internal bool DocumentValid = true, LibrariesValid = true;
        internal int Calls;
        internal string? LastRequest;
        internal Func<string> Run = () => OriginalResponse;
        public void Validate(string path, uint serial)
        {
            if (!DocumentValid) throw new IOException("The document changed.");
        }
        public void ValidateLibraries(JsonElement libraries)
        {
            if (!LibrariesValid) throw new IOException("The native library changed.");
        }
        public string Handle(string request) { LastRequest = request; Interlocked.Increment(ref Calls); return Run(); }
    }

    sealed class LibraryServer
    {
        readonly ValidatorCache _validator;
        readonly DefinitionCache _definitionRunner;
        readonly DrawingCache _drawingAssetManager;
        internal LibraryServer(string[] values)
        {
            _validator = new(values[0], values[1]);
            _definitionRunner = new(values[2], values[3]);
            _drawingAssetManager = new(values[4]);
        }
        internal string[] Snapshot() => _validator.Snapshot().Concat(_definitionRunner.Snapshot()).Concat(_drawingAssetManager.Snapshot()).ToArray();
    }
    sealed class ValidatorCache
    {
        readonly string _templateDir, _capsuleDir;
        internal ValidatorCache(string template, string capsule) { _templateDir = template; _capsuleDir = capsule; }
        internal string[] Snapshot() => new[] { _templateDir, _capsuleDir };
    }
    sealed class DefinitionCache
    {
        readonly string _libraryDir, _capsuleDir;
        internal DefinitionCache(string library, string capsule) { _libraryDir = library; _capsuleDir = capsule; }
        internal string[] Snapshot() => new[] { _libraryDir, _capsuleDir };
    }
    sealed class DrawingCache
    {
        readonly string _libraryRoot;
        internal DrawingCache(string root) { _libraryRoot = root; }
        internal string[] Snapshot() => new[] { _libraryRoot };
    }

    sealed class Fixture : IAsyncDisposable
    {
        internal readonly string Root = NewRoot(), Token = Guid.NewGuid().ToString("N");
        internal readonly SessionPaths Paths;
        internal readonly BoundBridge Bridge;
        internal readonly UiQueue Ui = new();
        internal readonly Target Target = new();
        internal readonly int Port;
        internal string Operation = "";
        readonly string ticks, workerTicks;
        readonly int workerPid;

        internal Fixture(int? externalWorkerPid = null, string? externalWorkerTicks = null)
        {
            var model = Path.Combine(Root, "Fixture.3dm");
            File.WriteAllText(model, "fixture: never opened by Rhino");
            Paths = SessionFiles.Paths(model, "A", Token, true);
            using var current = Process.GetCurrentProcess();
            ticks = current.StartTime.ToUniversalTime().Ticks.ToString();
            workerPid = externalWorkerPid ?? Environment.ProcessId;
            workerTicks = externalWorkerTicks ?? ticks;
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            Port = ((IPEndPoint)listener.LocalEndpoint).Port;
            listener.Stop();
            SessionFiles.WriteJson(Paths.ReadyPath, new {
                schema = "almond-project", storage_protocol = 2, token = Token, label = "A", port = Port,
                pid = Environment.ProcessId, process_start_ticks = ticks, document_serial = "1",
                model_path = model, document_path = model, storage = Paths.Storage, temp = Paths.Temp,
                session_dir = Paths.SessionDir, ready_path = Paths.ReadyPath, valid = true, status = "started"
            });
            WriteWorker(Token);
            NewOperation();
            Bridge = new BoundBridge(Port, Paths.ReadyPath, Token, model, 1, Target, Ui.Post);
        }

        internal void Start() => Bridge.Start();
        internal void WriteWorker(string token) => SessionFiles.WriteJson(Paths.WorkerPath,
            new { schema = "almond-worker", token, pid = workerPid, process_start_ticks = workerTicks,
                library_dirs = new Dictionary<string, string>() });
        internal void NewOperation()
        {
            Operation = Guid.NewGuid().ToString("N");
            var temp = Path.Combine(Paths.CallRoot, Operation);
            Directory.CreateDirectory(temp);
            SessionFiles.WriteJson(Paths.OperationPath, new {
                schema = "almond-operation", token = Token, operation_id = Operation,
                worker_pid = workerPid, worker_start_ticks = workerTicks, temp, state = "running"
            });
        }
        internal JsonElement Receipt()
        {
            using var json = SessionFiles.ReadJson(Paths.NativePath);
            return json.RootElement.Clone();
        }
        internal string OperationState()
        {
            using var json = SessionFiles.ReadJson(Paths.OperationPath);
            return json.RootElement.GetProperty("state").GetString()!;
        }
        public async ValueTask DisposeAsync()
        {
            Bridge.Stop();
            await Until(() => {
                while (Ui.Count != 0) Ui.RunOne();
                return Bridge.IsDrained;
            }, "Fixture cleanup could not confirm native drain.");
            Bridge.Dispose();
            Directory.Delete(Root, true);
        }
    }
}
