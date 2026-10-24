using System.Diagnostics;
using System.Net.NetworkInformation;
using System.Text.Json;
using AlmondEngine;
using Rhino;
using EApplication = Eto.Forms.Application;

namespace AlmondCOS;

internal sealed class CosHost : IDisposable
{
    const string Slots = "ABCDEFGHIJ";
    readonly string root, engine, commonData, discoveryPath;
    readonly string hostId = Guid.NewGuid().ToString("N");
    readonly string accessToken = Guid.NewGuid().ToString("N") + Guid.NewGuid().ToString("N");
    readonly string pipeName, startTicks;
    readonly int pid = Environment.ProcessId;
    readonly ControlPipe control;
    Dictionary<string, object?>? binding;
    FileStream? launcherLease, rhinoLease;
    SharedStorageLease? storageLease;
    SessionPaths? sessionPaths;
    Mutex? slotMutex;
    Process? worker;
    BoundBridge? bridge;
    string readyPath = "", activePath = "", requestId = "";
    string problem = "";
    bool busy, invalid, disposed, notifyDisconnect;

    internal CosHost()
    {
        root = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(typeof(CosHost).Assembly.Location)!, ".."));
        engine = Path.GetFullPath(Path.Combine(root, "..", "..", "mcp", "runtime"));
        commonData = Path.Combine(engine, "data");
        if (!File.Exists(Path.Combine(engine, "mcp_server.py")))
            throw new InvalidOperationException("공용 Engine을 찾을 수 없습니다. Rhino 플러그인 위치를 확인하세요.");
        using var current = Process.GetCurrentProcess();
        startTicks = current.StartTime.ToUniversalTime().Ticks.ToString();
        pipeName = "AlmondCOS-" + pid + "-" + hostId;
        var discovery = Path.GetFullPath(Path.Combine(root, "..", "..", "cos", "data", "hosts"));
        Directory.CreateDirectory(discovery);
        discoveryPath = Path.Combine(discovery, hostId + ".json");
        control = new ControlPipe(pipeName, accessToken, Dispatch, OwnerDisconnected);
        try
        {
            Save(discoveryPath, new { schema = "almond-cos-host", protocol = 1, host_id = hostId,
                pid, process_start_ticks = startTicks, pipe = pipeName, access_token = accessToken });
            RhinoDoc.ActiveDocumentChanged += DocumentChanged;
            RhinoDoc.EndSaveDocument += AfterSave;
            RhinoDoc.CloseDocument += BeforeClose;
            RhinoApp.Idle += AfterIdle;
        }
        catch { control.Dispose(); throw; }
    }

    static string Canonical(string path) => Path.GetFullPath(path).TrimEnd('\\', '/');
    static bool Same(string a, string b) => string.Equals(Canonical(a), Canonical(b), StringComparison.OrdinalIgnoreCase);
    static string Text(JsonElement value, string key) => value.GetProperty(key).GetString() ?? "";
    static void Save(string path, object value) => SessionFiles.WriteJson(path, value);

    Task<object> OnUi(Func<object> action, CancellationToken cancellation = default)
    {
        var completion = new TaskCompletionSource<object>(TaskCreationOptions.RunContinuationsAsynchronously);
        var app = EApplication.Instance;
        if (app == null) { completion.SetException(new InvalidOperationException("Rhino UI unavailable.")); return completion.Task; }
        app.AsyncInvoke(() =>
        {
            if (cancellation.IsCancellationRequested) { completion.TrySetCanceled(cancellation); return; }
            try { completion.TrySetResult(action()); }
            catch (Exception ex) { completion.TrySetException(ex); }
        });
        return completion.Task;
    }

    async Task<object> Dispatch(JsonElement request, CancellationToken cancellation)
    {
        if (Text(request, "action") != "detach")
            return await OnUi(() => Handle(request), cancellation).ConfigureAwait(false);
        // Stop/accept completion is asynchronous; do not report a normal detach
        // as unconfirmed merely because the listener is finishing on another thread.
        for (int attempt = 0; attempt < 100; attempt++)
        {
            bool released = (bool)await OnUi(() => {
                if (binding != null) Own(request);
                return Release();
            }, cancellation).ConfigureAwait(false);
            if (released) return new { detached = true };
            await Task.Delay(20, cancellation).ConfigureAwait(false);
        }
        throw new IOException("Native 작업 또는 worker 종료가 확인되지 않아 소유권을 유지합니다.");
    }

    async Task OwnerDisconnected(string token)
    {
        if (disposed) return;
        await OnUi(() =>
        {
            if (binding != null && token == (string)binding["token"]!)
            {
                Invalidate(busy ? "COS 연결이 실행 중 끊겨 결과 확인이 필요합니다." : "COS 연결 종료");
                Release();
            }
            return true;
        }).ConfigureAwait(false);
    }

    string State => binding == null ? "available" : busy ? "unconfirmed_or_running" : invalid ? "cleanup_pending" : "connected";

    internal string StatusText() => binding == null
        ? "AlmondCOS 준비됨. 저장된 현재 문서를 COS의 almond_cos_list_connections에서 선택하세요."
        : "AlmondCOS " + binding["label"] + " · " + Path.GetFileName((string)binding["model_path"]!) +
          (busy ? " · 요청 처리 중 또는 결과 확인 필요" : invalid ? " · 연결 정리 대기" : " · 연결됨");

    object Describe()
    {
        CheckDocument();
        var doc = RhinoDoc.ActiveDoc;
        bool saved = doc != null && !string.IsNullOrWhiteSpace(doc.Path) && File.Exists(doc.Path);
        return new { host_id = hostId, pid, process_start_ticks = startTicks,
            model_path = saved ? Canonical(doc!.Path) : null,
            document_serial = saved ? doc!.RuntimeSerialNumber.ToString() : null,
            supported_slots = Slots, state = State, reason = problem, saved };
    }

    void Own(JsonElement request)
    {
        if (binding == null || Text(request, "session_token") != (string)binding["token"]!)
            throw new InvalidOperationException("다른 연결이거나 종료된 AlmondCOS 연결입니다.");
    }

    object Handle(JsonElement request)
    {
        if (disposed) throw new ObjectDisposedException(nameof(CosHost));
        switch (Text(request, "action"))
        {
            case "describe": return Describe();
            case "attach": return Attach(request);
            case "status": Own(request); return Describe();
            case "worker":
                Own(request);
                if (invalid || worker != null) throw new InvalidOperationException("Worker 등록 상태가 다릅니다.");
                var candidate = Process.GetProcessById(request.GetProperty("pid").GetInt32());
                try
                {
                    if (candidate.Id == pid || !candidate.ProcessName.Equals("python", StringComparison.OrdinalIgnoreCase) ||
                        candidate.StartTime.ToUniversalTime().Ticks.ToString() != Text(request, "process_start_ticks"))
                        throw new InvalidOperationException("Worker 프로세스가 다릅니다.");
                    _ = candidate.Handle;
                    worker = candidate;
                    candidate.EnableRaisingEvents = true;
                    var token = (string)binding!["token"]!;
                    candidate.Exited += (_, _) =>
                    {
                        if (disposed) return;
                        _ = OnUi(() =>
                        {
                            if (binding != null && (string)binding["token"]! == token)
                            { Invalidate(busy ? "Worker가 실행 중 종료됐습니다. 결과를 확인하세요." : "Worker 종료"); Release(); }
                            return true;
                        });
                    };
                    if (candidate.HasExited) throw new InvalidOperationException("Worker가 이미 종료됐습니다.");
                }
                catch { if (worker == candidate) worker = null; candidate.Dispose(); throw; }
                return new { registered = true };
            case "begin":
                Own(request); CheckDocument();
                if (invalid || busy || worker == null || worker.HasExited || bridge?.IsRunning != true)
                    throw new InvalidOperationException("Rhino 연결이 변경됐거나 이전 요청이 아직 끝나지 않았습니다.");
                requestId = Text(request, "request_id");
                if (!Guid.TryParseExact(requestId, "N", out _)) throw new InvalidOperationException("잘못된 요청 ID입니다.");
                busy = true;
                return new { accepted = true };
            case "end":
                Own(request);
                if (!busy || Text(request, "request_id") != requestId)
                    throw new InvalidOperationException("완료할 요청이 현재 요청과 다릅니다.");
                busy = false; requestId = "";
                return new { completed = true };
            case "fail":
                Own(request); Invalidate("요청 결과 확인 필요: " + Text(request, "reason"));
                return new { state = State, retained = true };
            default: throw new InvalidOperationException("지원하지 않는 AlmondCOS 제어 요청입니다.");
        }
    }

    static bool Acquire(Mutex mutex, int milliseconds)
    {
        try { return mutex.WaitOne(milliseconds); }
        catch (AbandonedMutexException) { return true; }
    }

    static FileStream Lease(string storage, string name)
        => new(Path.Combine(storage, name), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);

    static bool Listening(int port) => IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners().Any(x => x.Port == port);

    bool SlotAvailable(char slot)
    {
        if (Listening(5501 + Slots.IndexOf(slot))) return false;
        foreach (var name in new[] { "active.json", "ready.json" })
        {
            var path = Path.Combine(commonData, slot.ToString(), name);
            if (!File.Exists(path)) continue;
            try
            {
                using var json = JsonDocument.Parse(File.ReadAllText(path));
                var r = json.RootElement;
                if (!r.TryGetProperty("pid", out var id) || id.ValueKind != JsonValueKind.Number) continue;
                Process other;
                try { other = Process.GetProcessById(id.GetInt32()); }
                catch (ArgumentException) { continue; }
                using (other)
                    if (other.ProcessName.Equals("Rhino", StringComparison.OrdinalIgnoreCase) &&
                        other.StartTime.ToUniversalTime().Ticks.ToString() == Text(r, "process_start_ticks")) return false;
            }
            catch { return false; }
        }
        return true;
    }

    void CheckOtherOwner()
    {
        foreach (var slot in Slots)
        foreach (var name in new[] { "active.json", "ready.json" })
        {
            var path = Path.Combine(commonData, slot.ToString(), name);
            if (!File.Exists(path)) continue;
            using var json = JsonDocument.Parse(File.ReadAllText(path));
            var r = json.RootElement;
            if (r.TryGetProperty("pid", out var id) && id.ValueKind == JsonValueKind.Number && id.GetInt32() == pid &&
                Text(r, "process_start_ticks") == startTicks)
                throw new InvalidOperationException("이 Rhino에 기존 Almond 연결이 있습니다. 현재 작업을 유지합니다.");
        }
    }

    object Attach(JsonElement request)
    {
        if (binding != null) throw new InvalidOperationException("이미 연결됐거나 정리를 기다리는 Rhino입니다.");
        // Original external launch markers persist even after its old worker exits.
        var oldStart = Path.Combine(engine, "rhino_start.py");
        if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("ALMOND_SESSION_FOLDER")) ||
            !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("ALMOND_SESSION_TOKEN")) ||
            Environment.GetCommandLineArgs().Any(a => a.Contains(oldStart, StringComparison.OrdinalIgnoreCase)))
            throw new InvalidOperationException("기존 Almond 실행기로 연 Rhino입니다. COS는 일반적으로 실행한 Rhino에서 사용하세요.");
        var doc = RhinoDoc.ActiveDoc;
        var model = Text(request, "model_path");
        var serial = Text(request, "document_serial");
        var token = Text(request, "session_token");
        if (doc == null || string.IsNullOrWhiteSpace(doc.Path) || !Same(doc.Path, model) ||
            serial != doc.RuntimeSerialNumber.ToString() || request.GetProperty("pid").GetInt32() != pid ||
            Text(request, "process_start_ticks") != startTicks || !Guid.TryParseExact(token, "N", out _))
            throw new InvalidOperationException("선택한 Rhino 문서가 변경됐습니다. 연결 목록을 다시 확인하세요.");
        model = Canonical(model);
        var storage = SessionFiles.Paths(model, "A", token).Storage;
        using var gate = new Mutex(false, @"Local\Almond_Process_Maintenance");
        if (!Acquire(gate, 2000)) throw new InvalidOperationException("Almond 시작 또는 정리가 진행 중입니다. 잠시 후 다시 연결하세요.");
        try
        {
            CheckOtherOwner();
            Directory.CreateDirectory(Path.Combine(storage, "tmp"));
            storageLease = new SharedStorageLease(storage);
            string? selected = null;
            foreach (var slot in Slots)
            {
                var candidate = new Mutex(false, @"Local\Almond_Dedicated_CLI_" + slot);
                bool owned = false, keep = false;
                try
                {
                    owned = Acquire(candidate, 0);
                    if (owned && SlotAvailable(slot))
                    { slotMutex = candidate; selected = slot.ToString(); keep = true; break; }
                }
                finally
                {
                    if (!keep) { if (owned) candidate.ReleaseMutex(); candidate.Dispose(); }
                }
            }
            if (selected == null) throw new InvalidOperationException("사용 가능한 Almond 슬롯 A-J가 없습니다.");
            int port = 5501 + Slots.IndexOf(selected, StringComparison.Ordinal);
            sessionPaths = SessionFiles.Paths(model, selected, token, true);
            launcherLease = Lease(sessionPaths.SessionDir, "launcher.lock");
            rhinoLease = Lease(sessionPaths.SessionDir, "rhino.lock");
            using (Lease(sessionPaths.SessionDir, "mcp.lock")) { }
            readyPath = sessionPaths.ReadyPath;
            activePath = Path.Combine(commonData, selected, "active.json");
            binding = new Dictionary<string, object?> {
                ["schema"]="almond-project", ["storage_protocol"]=SessionFiles.StorageProtocol,
                ["attachment"]="cos", ["label"]=selected, ["port"]=port,
                ["token"]=token, ["pid"]=pid, ["process_start_ticks"]=startTicks, ["document_serial"]=serial,
                ["model_path"]=model, ["document_path"]=Canonical(doc.Path), ["storage"]=storage, ["engine"]=engine,
                ["session_dir"]=sessionPaths.SessionDir, ["ready_path"]=readyPath, ["call_root"]=sessionPaths.CallRoot,
                ["state_db"]=sessionPaths.StateDb, ["temp"]=sessionPaths.Temp, ["rhino_temp"]=Path.GetTempPath(),
                ["model_units"]=doc.ModelUnitSystem.ToString(), ["valid"]=true, ["status"]="starting"
            };
            invalid = false; busy = false; problem = "";
            Directory.CreateDirectory(Path.GetDirectoryName(activePath)!);
            // Existing maintenance and the original RHP see this reservation.
            Save(activePath, binding);
            Save(readyPath, binding);
            bridge = new BoundBridge(port, readyPath, token, model, doc.RuntimeSerialNumber);
            bridge.Start();
            if (!bridge.IsRunning) throw new IOException("이 Rhino의 브리지 포트 시작을 확인하지 못했습니다.");
            binding["status"] = "started";
            Save(sessionPaths.LaunchPath, binding);
            Save(readyPath, binding);
            Save(activePath, binding);
            RhinoApp.WriteLine(StatusText());
            return binding;
        }
        catch
        {
            if (binding != null) Release();
            else ReleaseLeases();
            throw;
        }
        finally { gate.ReleaseMutex(); }
    }

    void Invalidate(string reason)
    {
        if (binding == null) return;
        problem = reason;
        if (!invalid)
        {
            invalid = true;
            binding["valid"] = false;
            binding["status"] = reason;
            try { Save(readyPath, binding); }
            catch (Exception ex) { RhinoApp.WriteLine("AlmondCOS 연결 무효화 기록 실패: " + ex.Message); }
        }
        try { bridge?.Stop(); }
        catch (Exception ex) { RhinoApp.WriteLine("AlmondCOS 브리지 중단 확인 필요: " + ex.GetBaseException().Message); }
    }

    void CheckDocument()
    {
        if (binding == null || invalid) return;
        var doc = RhinoDoc.ActiveDoc;
        if (doc == null || string.IsNullOrEmpty(doc.Path) ||
            doc.RuntimeSerialNumber.ToString() != (string)binding["document_serial"]! ||
            !Same(doc.Path, (string)binding["model_path"]!))
            Invalidate("연결된 문서 또는 파일명이 변경됐습니다.");
        else if (bridge != null && !bridge.IsRunning)
            Invalidate("이 연결의 native bridge가 종료됐습니다.");
    }

    void DocumentChanged(object? sender, DocumentEventArgs e) => CheckDocument();
    void AfterSave(object? sender, DocumentSaveEventArgs e) => CheckDocument();
    void AfterIdle(object? sender, EventArgs e)
    {
        if (!disposed && binding != null && invalid) Release();
    }
    void BeforeClose(object? sender, DocumentEventArgs e)
    {
        if (binding != null && e.Document != null &&
            e.Document.RuntimeSerialNumber.ToString() == (string)binding["document_serial"]!)
            Invalidate("연결된 문서가 닫혔습니다.");
    }

    bool Release()
    {
        if (binding == null) return true;
        Invalidate(string.IsNullOrEmpty(problem) ? "COS 연결 종료" : problem);
        if (worker != null && !worker.HasExited) return false;
        if (bridge != null)
        {
            try { bridge.Stop(); }
            catch { return false; }
            if (!bridge.IsDrained) return false;
        }
        // Hold the worker gate through invalidation and owner release. A probe
        // followed by close leaves a startup race if the earlier ready write failed.
        FileStream workerGuard;
        try { workerGuard = Lease(sessionPaths!.SessionDir, "mcp.lock"); }
        catch (IOException) { return false; }
        using var retainedWorkerGuard = workerGuard;
        try
        {
            binding["valid"] = false;
            Save(readyPath, binding);
            if (File.Exists(activePath))
            {
                using var json = JsonDocument.Parse(File.ReadAllText(activePath));
                if (Text(json.RootElement, "token") != (string)binding["token"]!) return false;
                File.Delete(activePath);
            }
        }
        catch (Exception ex) { problem = "점유 기록 정리 실패: " + ex.Message; return false; }
        worker?.Dispose(); worker = null;
        bridge?.Dispose();
        bridge = null; binding = null;
        ReleaseLeases();
        busy = false; invalid = false; requestId = ""; problem = "";
        if (notifyDisconnect)
        {
            notifyDisconnect = false;
            RhinoApp.WriteLine("AlmondCOS 연결 해제를 완료했습니다. Rhino와 작업 파일은 유지됩니다.");
        }
        return true;
    }

    void ReleaseLeases()
    {
        rhinoLease?.Dispose(); rhinoLease = null;
        launcherLease?.Dispose(); launcherLease = null;
        storageLease?.Dispose(); storageLease = null;
        sessionPaths = null;
        if (slotMutex != null) { slotMutex.ReleaseMutex(); slotMutex.Dispose(); slotMutex = null; }
    }

    internal string DisconnectFromRhino()
    {
        if (binding == null) return "AlmondCOS 연결이 없습니다.";
        notifyDisconnect = false;
        Invalidate("Rhino에서 COS 연결 해제 요청");
        if (Release()) return "AlmondCOS 연결을 해제했습니다. Rhino와 작업 파일은 유지됩니다.";
        notifyDisconnect = true;
        return busy
            ? "AlmondCOS 연결 해제를 요청했습니다. 처리 중인 작업의 완료를 확인한 뒤 자동으로 정리합니다. 완료 여부가 불확실하면 잠금을 유지합니다."
            : "AlmondCOS 연결 해제를 요청했습니다. COS가 worker와 점유를 자동으로 정리합니다. 완료 안내를 기다리세요.";
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        RhinoDoc.ActiveDocumentChanged -= DocumentChanged;
        RhinoDoc.EndSaveDocument -= AfterSave;
        RhinoDoc.CloseDocument -= BeforeClose;
        RhinoApp.Idle -= AfterIdle;
        Release();
        control.Dispose();
        try { File.Delete(discoveryPath); }
        catch (IOException) { }
    }
}
