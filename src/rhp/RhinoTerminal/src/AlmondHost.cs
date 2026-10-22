#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Net.NetworkInformation;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AlmondEngine;
using Rhino;
using EApplication = Eto.Forms.Application;

namespace RhinoTerminal;

// A private control channel for THIS panel's shell. It accepts only document
// description and bridge lifecycle operations, never executable source code.
internal sealed class AlmondHost : IDisposable
{
    const string SupportedSlots = "ABCDEFGHIJ";
    const int StorageProtocol = 2;
    static readonly HashSet<AlmondHost> pendingCleanup = new(); // UI-thread only; retain failed stops.
    public string PipeName { get; } = "RhinoTerminal-" + Environment.ProcessId + "-" + Guid.NewGuid().ToString("N");
    public string AccessToken { get; } = Guid.NewGuid().ToString("N") + Guid.NewGuid().ToString("N");
    public string Engine { get; } = Path.GetFullPath(Path.Combine(
        Path.GetDirectoryName(typeof(AlmondHost).Assembly.Location)!, "..", "..", "..", "engine"));
    readonly CancellationTokenSource shutdown = new();
    readonly Action<string> report;
    Dictionary<string, object?>? binding;
    FileStream? lease;
    SharedStorageLease? sharedLease;
    BoundBridge? bridge;
    string sessionDirectory = "", readyPath = "", locatorPath = "";
    bool disposed;
    public bool HasBinding => binding != null;
    public string? ProjectDirectory => binding != null ? Path.GetDirectoryName((string)binding["model_path"]!) : null;

    public AlmondHost(Action<string> report)
    {
        this.report = report;
        RhinoDoc.ActiveDocumentChanged += DocumentChanged;
        RhinoDoc.EndSaveDocument += AfterSave;
        RhinoDoc.CloseDocument += BeforeClose;
        _ = Task.Run(Listen);
    }

    public static string Canonical(string path) => Path.GetFullPath(path).TrimEnd('\\', '/');
    static bool Same(string a, string b) => string.Equals(Canonical(a), Canonical(b), StringComparison.OrdinalIgnoreCase);
    static string Text(JsonElement value, string key) => value.GetProperty(key).GetString() ?? "";
    static void Save(string path, object value)
        => SessionFiles.WriteJson(path, value);

    void CheckOwnership(string path)
    {
        if (!File.Exists(path)) return;
        using var json = JsonDocument.Parse(File.ReadAllText(path));
        if (Text(json.RootElement, "token") != (string)binding!["token"]!)
            throw new IOException("다른 Almond 세션의 연결 기록은 변경하지 않습니다.");
    }

    void SaveOwned(string path)
    {
        CheckOwnership(path);
        Save(path, binding!);
    }

    void ReleaseLeases()
    {
        lease?.Dispose(); lease = null;
        sharedLease?.Dispose(); sharedLease = null;
    }

    async Task Listen()
    {
        while (!shutdown.IsCancellationRequested)
        {
            try
            {
                using var pipe = new NamedPipeServerStream(PipeName, PipeDirection.InOut, 1,
                    PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
                await pipe.WaitForConnectionAsync(shutdown.Token).ConfigureAwait(false);
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(shutdown.Token);
                timeout.CancelAfter(TimeSpan.FromSeconds(25));
                var bytes = new List<byte>();
                var chunk = new byte[1024];
                bool complete = false;
                while (!complete)
                {
                    int n = await pipe.ReadAsync(chunk, timeout.Token).ConfigureAwait(false);
                    if (n == 0) throw new IOException("Control channel closed.");
                    for (int i = 0; i < n; i++)
                    {
                        if (chunk[i] == 10) { complete = true; break; }
                        bytes.Add(chunk[i]);
                        if (bytes.Count > 32768) throw new IOException("Control message too large.");
                    }
                }
                object response;
                try
                {
                    using var json = JsonDocument.Parse(Encoding.UTF8.GetString(bytes.ToArray()));
                    if (Text(json.RootElement, "access_token") != AccessToken)
                        throw new InvalidOperationException("다른 터미널의 연결 요청입니다.");
                    var request = json.RootElement.Clone();
                    var done = new TaskCompletionSource<object>(TaskCreationOptions.RunContinuationsAsynchronously);
                    var app = EApplication.Instance ?? throw new InvalidOperationException("Rhino UI is unavailable.");
                    app.AsyncInvoke(() => {
                        if (timeout.IsCancellationRequested || disposed) { done.TrySetCanceled(); return; }
                        try { done.TrySetResult(Handle(request)); }
                        catch (Exception ex) { done.TrySetException(ex); }
                    });
                    response = new { ok = true, result = await done.Task.WaitAsync(timeout.Token).ConfigureAwait(false) };
                }
                catch (Exception ex) { response = new { ok = false, error = ex.GetBaseException().Message }; }
                var output = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(response) + "\n");
                await pipe.WriteAsync(output, timeout.Token).ConfigureAwait(false);
                await pipe.FlushAsync(timeout.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) { }
            catch (Exception ex)
            {
                if (!shutdown.IsCancellationRequested)
                    EApplication.Instance?.AsyncInvoke(() => report("Almond 제어 통신: " + ex.Message));
            }
        }
    }

    object Describe()
    {
        var doc = RhinoDoc.ActiveDoc;
        if (doc == null || string.IsNullOrWhiteSpace(doc.Path) || !File.Exists(doc.Path))
            throw new InvalidOperationException("먼저 이 Rhino 문서를 .3dm으로 저장한 뒤 almond를 입력하세요.");
        using var process = Process.GetCurrentProcess();
        return new { model_path = Canonical(doc.Path), document_serial = doc.RuntimeSerialNumber.ToString(),
            pid = process.Id, process_start_ticks = process.StartTime.ToUniversalTime().Ticks.ToString(),
            supported_slots = SupportedSlots, storage_protocol = StorageProtocol };
    }

    object Handle(JsonElement request)
    {
        switch (Text(request, "action"))
        {
            case "describe": return Describe();
            case "attach": return Attach(request);
            case "validate":
                CheckDocument();
                if (binding == null || Text(request, "session_token") != (string)binding["token"]! ||
                    binding["valid"] is not true) throw new InvalidOperationException("Almond 문서 연결이 끝났거나 문서가 변경됐습니다.");
                return binding;
            case "detach":
                if (binding != null && Text(request, "session_token") != (string)binding["token"]!)
                    throw new InvalidOperationException("다른 세션은 해제하지 않습니다.");
                if (!Release()) throw new InvalidOperationException("브리지 작업 또는 MCP가 아직 종료 중입니다. 작업 종료 후 다시 연결하세요.");
                return new { detached = true };
            default: throw new InvalidOperationException("지원하지 않는 제어 요청입니다.");
        }
    }

    object Attach(JsonElement request)
    {
        foreach (var old in pendingCleanup.ToArray())
            if (old.Release()) pendingCleanup.Remove(old);
        if (pendingCleanup.Any(old => old.binding != null))
            throw new InvalidOperationException("이 Rhino의 이전 Almond 작업이 아직 종료 중입니다. 종료 확인 후 다시 연결하세요.");
        if (binding != null && binding["valid"] is false) Release();
        if (binding != null) throw new InvalidOperationException("이 패널은 이미 Almond에 연결돼 있습니다. 기존 Codex에서 /exit 후 다시 실행하세요.");
        if (!request.TryGetProperty("storage_protocol", out var protocol) ||
            !protocol.TryGetInt32(out var version) || version != StorageProtocol)
            throw new InvalidOperationException("이 패널에는 storage_protocol=2를 지원하는 Almond 실행기가 필요합니다.");
        var doc = RhinoDoc.ActiveDoc;
        var model = Text(request, "model_path");
        var serial = Text(request, "document_serial");
        var slot = Text(request, "slot");
        var token = Text(request, "session_token");
        var port = request.GetProperty("port").GetInt32();
        if (doc == null || string.IsNullOrEmpty(doc.Path) || !File.Exists(doc.Path) || !Same(doc.Path, model) ||
            doc.RuntimeSerialNumber.ToString() != serial || slot.Length != 1 ||
            !SupportedSlots.Contains(slot) || port != 5501 + SupportedSlots.IndexOf(slot) || !Guid.TryParseExact(token, "N", out _))
            throw new InvalidOperationException("요청한 모델·문서·연결 번호가 현재 Rhino와 다릅니다.");
        var paths = SessionFiles.Paths(model, slot, token);
        var storage = paths.Storage;
        if (!Same(storage, Text(request, "storage")) || !Directory.Exists(Path.Combine(storage, "tmp")))
            throw new InvalidOperationException("공유 프로젝트 저장소 경로가 다릅니다.");
        var session = paths.SessionDir;
        if (request.TryGetProperty("session_dir", out var requestedSession) &&
            !Same(session, requestedSession.GetString() ?? ""))
            throw new InvalidOperationException("요청한 Almond 세션 경로가 다릅니다.");
        // Do not attach a second bridge to a Rhino owned by the external launcher.
        using var process = Process.GetCurrentProcess();
        var ticks = process.StartTime.ToUniversalTime().Ticks.ToString();
        var data = Path.Combine(Engine, "data");
        foreach (var label in SupportedSlots)
        foreach (var name in new[] { "active.json", "ready.json" })
        {
            var path = Path.Combine(data, label.ToString(), name);
            if (!File.Exists(path)) continue;
            using var old = JsonDocument.Parse(File.ReadAllText(path));
            var r = old.RootElement;
            if (r.TryGetProperty("pid", out var pid) && pid.ValueKind == JsonValueKind.Number && pid.GetInt32() == process.Id &&
                r.TryGetProperty("process_start_ticks", out var t) && t.GetString() == ticks)
                throw new InvalidOperationException("이 Rhino에는 기존 Almond 연결이 있습니다. 기존 연결을 종료한 뒤 사용하세요.");
        }
        if (Listening(port)) throw new InvalidOperationException("배정된 포트가 이미 사용 중입니다. 다시 almond를 실행하세요.");
        try
        {
            // Shared legacy handles reject old exclusive hosts while allowing protocol 2 peers.
            sharedLease = new SharedStorageLease(storage);
            sessionDirectory = session;
            Directory.CreateDirectory(sessionDirectory);
            lease = new FileStream(Path.Combine(sessionDirectory, "rhino.lock"),
                FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            using (new FileStream(Path.Combine(sessionDirectory, "mcp.lock"),
                FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None)) { }
            readyPath = Path.Combine(sessionDirectory, "ready.json");
            if (File.Exists(readyPath))
                throw new InvalidOperationException("이미 사용한 세션 토큰입니다. almond를 새로 실행하세요.");
            locatorPath = Path.Combine(data, slot, "active.json");
            binding = new Dictionary<string, object?> {
                ["schema"]="almond-project", ["storage_protocol"]=StorageProtocol,
                ["attachment"]="terminal", ["label"]=slot, ["port"]=port,
                ["token"]=token, ["pid"]=process.Id, ["process_start_ticks"]=ticks, ["document_serial"]=serial,
                ["model_path"]=Canonical(model), ["document_path"]=Canonical(doc.Path), ["storage"]=storage,
                ["session_dir"]=sessionDirectory, ["ready_path"]=readyPath,
                ["state_db"]=Path.Combine(storage,"scene.sqlite3"),
                ["engine"]=Engine, ["temp"]=Path.Combine(storage,"tmp"), ["rhino_temp"]=Path.GetTempPath(),
                ["model_units"]=doc.ModelUnitSystem.ToString(), ["valid"]=true, ["status"]="starting"
            };
            Directory.CreateDirectory(Path.GetDirectoryName(locatorPath)!);
            SaveOwned(Path.Combine(sessionDirectory, "launch.json"));
            SaveOwned(readyPath);
            // Publish ownership before starting a listener, including failed-start cleanup.
            Save(locatorPath, binding);
            bridge = new BoundBridge(port, readyPath, token, Canonical(model), doc.RuntimeSerialNumber);
            bridge.Start();
            var watch = Stopwatch.StartNew();
            while (watch.Elapsed < TimeSpan.FromSeconds(5))
            {
                if (!bridge.IsRunning || !bridge.IsAlive)
                    throw new IOException("Almond 브리지가 시작 중 종료됐습니다.");
                if (Listening(port)) break;
                Thread.Sleep(25);
            }
            if (!Listening(port)) throw new IOException("Almond 포트 시작 확인 시간이 초과됐습니다.");
            binding["status"] = "started";
            SaveOwned(Path.Combine(sessionDirectory, "launch.json"));
            SaveOwned(readyPath);
            SaveOwned(locatorPath);
            report("Almond " + slot + " · " + Path.GetFileName(model));
            return binding;
        }
        catch
        {
            if (binding == null) ReleaseLeases();
            else if (!Release()) pendingCleanup.Add(this);
            throw;
        }
    }

    static bool Listening(int port) => IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners().Any(x => x.Port == port);

    void Invalidate(string reason)
    {
        if (binding == null || binding["valid"] is not true) return;
        binding["valid"] = false;
        binding["status"] = reason;
        try { SaveOwned(readyPath); }
        catch (Exception ex) { RhinoApp.WriteLine("Almond 연결 무효화 기록 실패: " + ex.Message); }
        // BoundBridge rejects invalid documents at dispatch; active native work must drain.
        try { bridge?.Stop(); }
        catch (Exception ex) { RhinoApp.WriteLine("Almond 중단 확인 필요: " + ex.GetBaseException().Message); }
        report(reason + " — Codex에서 /exit 후 almond를 다시 입력하세요.");
    }

    public void CheckDocument()
    {
        if (binding == null || binding["valid"] is not true) return;
        var doc = RhinoDoc.ActiveDoc;
        if (doc == null || string.IsNullOrEmpty(doc.Path) ||
            doc.RuntimeSerialNumber.ToString() != (string)binding["document_serial"]! || !Same(doc.Path, (string)binding["model_path"]!))
            Invalidate("Rhino 문서 또는 파일명이 변경됐습니다");
    }
    // BeginOpenDocument also fires for clipboard paste/import. Do not mistake
    // those for a document replacement. Close/current-document/path checks are used.
    void DocumentChanged(object? sender, DocumentEventArgs e) => CheckDocument();
    void AfterSave(object? sender, DocumentSaveEventArgs e) => CheckDocument();
    void BeforeClose(object? sender, DocumentEventArgs e)
    { if (binding != null && e.Document != null && e.Document.RuntimeSerialNumber.ToString() == (string)binding["document_serial"]!) Invalidate("Rhino 문서가 닫혔습니다"); }

    // Called on the Rhino UI thread. If stop is not confirmed, retain the
    // object and Rhino/session ownership until native work and its MCP have drained.
    public bool Release()
    {
        if (binding == null) return true;
        Invalidate("Almond 연결 종료");
        if (bridge != null)
        {
            try { bridge.Stop(); }
            catch { return false; }
            if (bridge.IsRunning || bridge.IsAlive || bridge.Pending != 0 || !bridge.IsDrained ||
                Listening((int)binding["port"]!)) return false;
        }
        try
        {
            // Keep this generation's MCP excluded until its host ownership is released.
            using var probe = new FileStream(Path.Combine(sessionDirectory, "mcp.lock"),
                FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            // Retry a failed invalidation write before allowing another MCP to acquire this generation.
            SaveOwned(readyPath);
            if (File.Exists(locatorPath))
            {
                CheckOwnership(locatorPath);
                File.Delete(locatorPath);
            }
            bridge?.Dispose();
            ReleaseLeases();
            bridge = null; binding = null;
            pendingCleanup.Remove(this);
        }
        catch (Exception ex)
        {
            RhinoApp.WriteLine("Almond 종료 확인: " + ex.Message);
            return false;
        }
        report("PowerShell — almond를 입력하면 현재 문서에 다시 연결합니다");
        return true;
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        shutdown.Cancel();
        RhinoDoc.ActiveDocumentChanged -= DocumentChanged;
        RhinoDoc.EndSaveDocument -= AfterSave;
        RhinoDoc.CloseDocument -= BeforeClose;
        if (!Release())
        {
            pendingCleanup.Add(this);
            RhinoApp.WriteLine("Almond 브리지 종료가 지연돼 잠금을 유지합니다. Rhino 재시작이 필요할 수 있습니다.");
        }
    }
}
