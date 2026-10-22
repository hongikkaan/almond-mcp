using System.Buffers.Binary;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Win32.SafeHandles;

namespace AlmondEngine;

/// <summary>Owns only its transport. The original plugin's server and helpers remain untouched.</summary>
public sealed class BoundBridge : IDisposable
{
    sealed class Ticket
    {
        internal readonly TcpClient Client;
        internal readonly IPEndPoint Peer;
        internal WorkerIdentity Worker;
        internal OperationIdentity Operation;
        internal bool Authorized, NativeEntered, NativeFinished;
        internal string RequestToken = "", RequestOperation = "", RequestId = "", Payload = "";
        internal string Phase = "receiving", Completion = "rejected";
        internal long NativeSequence;
        internal Ticket(TcpClient client)
        {
            Client = client;
            Peer = (IPEndPoint)client.Client.RemoteEndPoint!;
        }
    }

    readonly record struct OperationIdentity(string Id, string Temp);
    readonly object sync = new();
    readonly int port;
    readonly string token, modelPath, readyPath, startTicks;
    readonly uint documentSerial;
    readonly bool enforceSlotPort;
    readonly IBridgeTarget target;
    readonly Action<Action> dispatch;
    readonly SessionPaths paths;
    readonly CancellationTokenSource stop = new();
    readonly List<Ticket> authorized = new();
    readonly HashSet<string> requestIds = new(StringComparer.Ordinal);
    TcpListener? listener;
    Task? acceptTask;
    SafeWaitHandle? processLease;
    bool started, stopping, listenerExited = true, disposed;
    int pending;
    long sequence;
    string operationId = "", lastRequestId = "", completedStatus = "none", fault = "", lastError = "";

    public BoundBridge(int port, string readyPath, string token, string modelPath, uint documentSerial)
        : this(port, readyPath, token, modelPath, documentSerial, new RhinoBridgeTarget(),
            action => Rhino.RhinoApp.InvokeOnUiThread(action), true) { }

    internal BoundBridge(int port, string readyPath, string token, string modelPath, uint documentSerial,
        IBridgeTarget target, Action<Action> dispatch, bool enforceSlotPort = false)
    {
        if (enforceSlotPort && (port < 5501 || port > 5510)) throw new ArgumentOutOfRangeException(nameof(port));
        SessionFiles.CheckToken(token);
        this.port = port;
        this.token = token;
        this.modelPath = SessionFiles.Canonical(modelPath);
        this.readyPath = SessionFiles.Canonical(readyPath);
        this.documentSerial = documentSerial;
        this.target = target;
        this.dispatch = dispatch;
        this.enforceSlotPort = enforceSlotPort;
        paths = SessionFiles.Paths(modelPath, enforceSlotPort ? SessionFiles.Slots[port - 5501].ToString() : "A", token);
        if (!SessionFiles.Same(paths.ReadyPath, readyPath)) throw new IOException("Ready metadata must belong to this session token.");
        using var current = Process.GetCurrentProcess();
        startTicks = current.StartTime.ToUniversalTime().Ticks.ToString();
    }

    public bool IsRunning { get { lock (sync) return started && !stopping && !listenerExited && fault.Length == 0; } }
    public bool IsAlive { get { lock (sync) return !listenerExited || pending != 0; } }
    public int Pending { get { lock (sync) return pending; } }
    public bool IsDrained { get { lock (sync) return stopping && listenerExited && pending == 0; } }

    public void Start()
    {
        lock (sync)
        {
            if (disposed || started || stopping) throw new InvalidOperationException("A bridge generation cannot be restarted.");
            if (File.Exists(readyPath)) ValidateBinding();
            target.Validate(modelPath, documentSerial);
            processLease = CreateEventW(IntPtr.Zero, true, false,
                @"Local\Almond_Rhino_" + Environment.ProcessId + "_" + startTicks);
            int error = Marshal.GetLastWin32Error();
            if (processLease.IsInvalid || error == 183)
            {
                processLease.Dispose();
                processLease = null;
                throw new IOException("This Rhino process already owns an Almond native session.");
            }
            try
            {
                listener = new TcpListener(IPAddress.Loopback, port);
                listener.Server.ExclusiveAddressUse = true;
                listener.Start();
                listenerExited = false;
                started = true;
                if (!PublishLocked()) throw new IOException("Cannot publish native session state: " + fault);
                acceptTask = Task.Run(AcceptLoop);
            }
            catch
            {
                listener?.Stop();
                listenerExited = true;
                stopping = true;
                processLease.Dispose();
                processLease = null;
                throw;
            }
        }
    }

    public void Stop()
    {
        lock (sync)
        {
            if (stopping) return;
            stopping = true;
            if (started) PublishLocked();
            stop.Cancel();
            listener?.Stop();
        }
    }

    async Task AcceptLoop()
    {
        try
        {
            while (!stop.IsCancellationRequested)
            {
                var client = await listener!.AcceptTcpClientAsync(stop.Token).ConfigureAwait(false);
                client.NoDelay = true;
                Ticket ticket;
                lock (sync)
                {
                    // Listener exit is also required for drain, covering accept-before-increment.
                    ticket = new Ticket(client);
                    pending++;
                }
                _ = Serve(ticket);
            }
        }
        catch (OperationCanceledException) when (stop.IsCancellationRequested) { }
        catch (SocketException) when (stopping) { }
        catch (ObjectDisposedException) when (stopping) { }
        catch (Exception ex)
        {
            lock (sync) { fault = ex.Message; stopping = true; lastError = ex.Message; }
            stop.Cancel();
            listener?.Stop();
        }
        finally
        {
            lock (sync)
            {
                listenerExited = true;
                if (started) PublishLocked();
            }
        }
    }

    void ValidateBinding()
    {
        using var json = SessionFiles.ReadJson(readyPath);
        var value = json.RootElement;
        var slot = SessionFiles.Text(value, "label");
        if (SessionFiles.Text(value, "schema") != "almond-project" ||
            value.GetProperty("storage_protocol").GetInt32() != SessionFiles.StorageProtocol ||
            SessionFiles.Text(value, "token") != token || value.GetProperty("valid").ValueKind != JsonValueKind.True ||
            value.GetProperty("pid").GetInt32() != Environment.ProcessId ||
            SessionFiles.Scalar(value, "process_start_ticks") != startTicks ||
            SessionFiles.Scalar(value, "document_serial") != documentSerial.ToString() ||
            value.GetProperty("port").GetInt32() != port || slot.Length != 1 || !SessionFiles.Slots.Contains(slot) ||
            (enforceSlotPort && port != 5501 + SessionFiles.Slots.IndexOf(slot, StringComparison.Ordinal)) ||
            !SessionFiles.Same(SessionFiles.Text(value, "model_path"), modelPath) ||
            !SessionFiles.Same(SessionFiles.Text(value, "document_path"), modelPath) ||
            !SessionFiles.Same(SessionFiles.Text(value, "storage"), paths.Storage) ||
            !SessionFiles.Same(SessionFiles.Text(value, "temp"), paths.Temp) ||
            !SessionFiles.Same(SessionFiles.Text(value, "session_dir"), paths.SessionDir) ||
            !SessionFiles.Same(SessionFiles.Text(value, "ready_path"), readyPath))
            throw new IOException("The Rhino session binding changed.");
    }

    WorkerIdentity ReadWorker(out JsonElement libraries)
    {
        using var json = SessionFiles.ReadJson(paths.WorkerPath);
        var value = json.RootElement;
        if (SessionFiles.Text(value, "schema") != "almond-worker" || SessionFiles.Text(value, "token") != token)
            throw new IOException("The worker generation changed.");
        var worker = new WorkerIdentity(value.GetProperty("pid").GetInt32(), SessionFiles.Scalar(value, "process_start_ticks"));
        if (!worker.IsAlive()) throw new IOException("The registered worker ended or its PID was reused.");
        libraries = value.GetProperty("library_dirs").Clone();
        if (libraries.ValueKind != JsonValueKind.Object) throw new IOException("The worker library directories are missing.");
        return worker;
    }

    OperationIdentity ReadOperation(WorkerIdentity worker)
    {
        using var json = SessionFiles.ReadJson(paths.OperationPath);
        var value = json.RootElement;
        var id = SessionFiles.Text(value, "operation_id");
        SessionFiles.CheckToken(id);
        var temp = SessionFiles.Text(value, "temp");
        if (SessionFiles.Text(value, "schema") != "almond-operation" || SessionFiles.Text(value, "token") != token ||
            SessionFiles.Text(value, "state") != "running" || value.GetProperty("worker_pid").GetInt32() != worker.Pid ||
            SessionFiles.Scalar(value, "worker_start_ticks") != worker.StartTicks ||
            !SessionFiles.Same(temp, Path.Combine(paths.CallRoot, id)) || !Directory.Exists(temp))
            throw new IOException("The native request has no matching running operation.");
        SessionFiles.CheckPlainPath(temp);
        return new OperationIdentity(id, SessionFiles.Canonical(temp));
    }

    void ValidateTicket(Ticket ticket, bool checkDocument)
    {
        lock (sync)
            if (stopping || fault.Length != 0) throw new IOException("The native session is draining.");
        ValidateBinding();
        if (ReadWorker(out var libraries) != ticket.Worker ||
            !WindowsPeerIdentity.Matches(ticket.Peer, port, ticket.Worker) ||
            ReadOperation(ticket.Worker) != ticket.Operation)
            throw new IOException("The worker, TCP client, or operation changed before native dispatch.");
        if (checkDocument)
        {
            target.Validate(modelPath, documentSerial);
            target.ValidateLibraries(libraries);
        }
    }

    void ReadEnvelope(Ticket ticket, string frame)
    {
        using var json = JsonDocument.Parse(frame);
        var value = json.RootElement;
        if (value.ValueKind != JsonValueKind.Object) throw new IOException("A native request envelope must be an object.");
        static string Text(JsonElement value, string name) =>
            value.TryGetProperty(name, out var property) && property.ValueKind == JsonValueKind.String
                ? property.GetString()! : "";
        // Preserve parsed identifiers in rejection replies, without trusting them for dispatch.
        ticket.RequestToken = Text(value, "token");
        ticket.RequestOperation = Text(value, "operation_id");
        ticket.RequestId = Text(value, "request_id");
        var names = new HashSet<string>(StringComparer.Ordinal);
        if (value.EnumerateObject().Any(property => !names.Add(property.Name)))
            throw new IOException("The native request envelope contains a duplicate field.");
        if (Text(value, "schema") != "almond-native-request" ||
            !value.TryGetProperty("storage_protocol", out var protocol) ||
            !protocol.TryGetInt32(out int version) || version != SessionFiles.StorageProtocol)
            throw new IOException("The native request requires the bound protocol envelope.");
        SessionFiles.CheckToken(ticket.RequestToken);
        SessionFiles.CheckToken(ticket.RequestOperation);
        SessionFiles.CheckToken(ticket.RequestId);
        if (ticket.RequestToken != token) throw new IOException("The native request token belongs to another generation.");
        if (!value.TryGetProperty("payload", out var payload) || payload.ValueKind != JsonValueKind.String)
            throw new IOException("The native request payload must be the original JSON string.");
        ticket.Payload = payload.GetString()!;
    }

    static string ResponseEnvelope(Ticket ticket, string payload) => JsonSerializer.Serialize(new {
        schema = "almond-native-response", storage_protocol = SessionFiles.StorageProtocol,
        token = ticket.RequestToken, operation_id = ticket.RequestOperation, request_id = ticket.RequestId,
        completion_status = ticket.Completion, native_sequence = ticket.NativeSequence, payload
    });

    async Task Serve(Ticket ticket)
    {
        try
        {
            string payload;
            try
            {
                // Read the entire immutable request identity before consulting current metadata.
                // Unauthenticated/old peers never publish a receipt or invalidate this generation.
                using var receiving = CancellationTokenSource.CreateLinkedTokenSource(stop.Token);
                receiving.CancelAfter(TimeSpan.FromSeconds(30));
                string frame = await ReadFrame(ticket.Client.GetStream(), receiving.Token).ConfigureAwait(false);
                ReadEnvelope(ticket, frame);
                ValidateBinding();
                ticket.Worker = ReadWorker(out _);
                if (!WindowsPeerIdentity.Matches(ticket.Peer, port, ticket.Worker))
                    throw new IOException("The TCP client does not own this worker session.");
                ticket.Operation = ReadOperation(ticket.Worker);
                if (ticket.RequestOperation != ticket.Operation.Id)
                    throw new IOException("The native request belongs to a stale operation.");
                lock (sync)
                {
                    ValidateTicket(ticket, false);
                    if (authorized.Count != 0 && operationId != ticket.Operation.Id)
                        throw new IOException("A previous native operation has not drained.");
                    if (!requestIds.Add(ticket.RequestId))
                        throw new IOException("This native request ID has already been accepted.");
                    if (operationId != ticket.Operation.Id)
                    { operationId = ticket.Operation.Id; completedStatus = "none"; lastError = ""; }
                    ticket.Authorized = true;
                    authorized.Add(ticket);
                    if (!PublishLocked(ticket)) throw new IOException("Cannot publish native acceptance.");
                }
                ValidateTicket(ticket, false);
                var completion = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
                lock (sync)
                {
                    ticket.Phase = "queued";
                    if (!PublishLocked(ticket)) throw new IOException("Cannot publish native UI queue.");
                }
                try { dispatch(() =>
                {
                    string? response = null;
                    Exception? failure = null;
                    try
                    {
                        ValidateTicket(ticket, true);
                        lock (sync)
                        {
                            if (stopping || fault.Length != 0) throw new IOException("The native session is draining.");
                            if (authorized.Any(other => other != ticket && other.Phase == "running"))
                                throw new IOException("Another native request is still executing in this session.");
                            ticket.NativeEntered = true;
                            ticket.Phase = "running";
                            if (!PublishLocked(ticket)) throw new IOException("Cannot publish native execution.");
                        }
                        response = target.Handle(ticket.Payload);
                        ticket.Completion = "completed";
                    }
                    catch (Exception ex)
                    {
                        failure = ex;
                        ticket.Completion = ticket.NativeEntered ? "failed" : "rejected";
                    }
                    finally
                    {
                        lock (sync)
                        {
                            ticket.NativeFinished = true;
                            ticket.Phase = "sending";
                            if (PublishLocked(ticket)) ticket.NativeSequence = sequence;
                        }
                    }
                    // A response can acknowledge completion only after the actual UI finally.
                    if (failure == null) completion.TrySetResult(response!);
                    else completion.TrySetException(failure);
                }); }
                catch (Exception ex)
                {
                    // A dispatch failure cannot prove that its delegate was never enqueued.
                    // Retain this ticket until that delegate actually runs its finally.
                    lock (sync)
                    {
                        fault = "Cannot confirm native UI scheduling: " + ex.GetBaseException().Message;
                        lastError = fault;
                        stopping = true;
                        PublishLocked(ticket);
                        stop.Cancel();
                        listener?.Stop();
                    }
                }
                // Cancellation/EOF must never abandon a queued or running UI delegate.
                payload = await completion.Task.ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                if (ticket.Authorized)
                {
                    lock (sync)
                    {
                        lastError = ex.GetBaseException().Message;
                        // Validation/queue failures before dispatch have no outstanding native delegate.
                        if (!ticket.NativeFinished)
                        {
                            ticket.NativeFinished = true;
                            ticket.Phase = "sending";
                            if (PublishLocked(ticket)) ticket.NativeSequence = sequence;
                        }
                    }
                }
                payload = JsonSerializer.Serialize(new {
                    status = "error", message = ex.GetBaseException().Message, source = "almond-bound-bridge"
                });
            }
            // Exactly one reply attempt: a partial write must never be followed by another frame.
            try { await WriteFrame(ticket.Client.GetStream(), ResponseEnvelope(ticket, payload), stop.Token).ConfigureAwait(false); }
            catch (Exception ex) when (ex is IOException or SocketException or OperationCanceledException or ObjectDisposedException)
            {
                if (ticket.Authorized) lock (sync) lastError = ex.GetBaseException().Message;
            }
        }
        finally
        {
            ticket.Client.Dispose();
            lock (sync)
            {
                pending--;
                if (ticket.Authorized)
                {
                    authorized.Remove(ticket);
                    completedStatus = Worst(completedStatus, ticket.Completion);
                    PublishLocked(ticket);
                }
            }
        }
    }

    static string Worst(string first, string second)
    {
        static int Rank(string value) => value switch { "failed" => 3, "rejected" => 2, "completed" => 1, _ => 0 };
        return Rank(first) >= Rank(second) ? first : second;
    }

    bool PublishLocked(Ticket? ticket = null)
    {
        if (ticket != null) lastRequestId = ticket.RequestId;
        string phase = fault.Length != 0 ? "faulted" : stopping ? (listenerExited && authorized.Count == 0 ? "stopped" : "draining") :
            authorized.Any(t => t.Phase == "running") ? "running" :
            authorized.Any(t => t.Phase == "queued") ? "queued" :
            authorized.Any(t => t.Phase == "receiving") ? "receiving" :
            authorized.Count != 0 ? "sending" : "listening";
        try
        {
            SessionFiles.WriteJson(paths.NativePath, new {
                schema = "almond-native", storage_protocol = SessionFiles.StorageProtocol, token,
                operation_id = operationId, request_id = lastRequestId, pending = authorized.Count, phase, sequence = ++sequence,
                completion_status = authorized.Count != 0 ? "running" : completedStatus,
                error = lastError.Length == 0 ? null : lastError
            });
            return true;
        }
        catch (Exception ex)
        {
            fault = ex.Message;
            stopping = true;
            // Stop new work without ever pretending that outstanding native callbacks completed.
            stop.Cancel();
            listener?.Stop();
            return false;
        }
    }

    static async Task<string> ReadFrame(NetworkStream stream, CancellationToken cancellation)
    {
        var header = new byte[4];
        await stream.ReadExactlyAsync(header, cancellation).ConfigureAwait(false);
        int length = BinaryPrimitives.ReadInt32BigEndian(header);
        if (length <= 0 || length > 64 * 1024 * 1024) throw new IOException("Invalid native request frame length.");
        var payload = new byte[length];
        await stream.ReadExactlyAsync(payload, cancellation).ConfigureAwait(false);
        return new UTF8Encoding(false, true).GetString(payload);
    }

    static async Task WriteFrame(NetworkStream stream, string response, CancellationToken cancellation)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellation);
        timeout.CancelAfter(TimeSpan.FromSeconds(30));
        byte[] payload = Encoding.UTF8.GetBytes(response), header = new byte[4];
        BinaryPrimitives.WriteInt32BigEndian(header, payload.Length);
        await stream.WriteAsync(header, timeout.Token).ConfigureAwait(false);
        await stream.WriteAsync(payload, timeout.Token).ConfigureAwait(false);
    }

    public void Dispose()
    {
        Stop();
        lock (sync)
        {
            if (disposed) return;
            if (!IsDrained) throw new InvalidOperationException("Wait for native drain before disposing its owner.");
            processLease?.Dispose();
            processLease = null;
            stop.Dispose();
            disposed = true;
        }
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern SafeWaitHandle CreateEventW(IntPtr security, bool manualReset, bool initialState, string name);
}
