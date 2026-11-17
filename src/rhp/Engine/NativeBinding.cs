namespace AlmondEngine;

/// <summary>Shared binding publication and drain; hosts retain shell/worker/discovery ownership.</summary>
public static class NativeBinding
{
    public static Dictionary<string, object?> Create(SessionPaths paths, string slot, int port, uint serial,
        int pid, string ticks, string engine, string units, string attachment) => new() {
        ["schema"]="almond-project", ["storage_protocol"]=SessionFiles.StorageProtocol,
        ["attachment"]=attachment, ["label"]=slot, ["port"]=port,
        ["token"]=Path.GetFileName(paths.SessionDir), ["pid"]=pid, ["process_start_ticks"]=ticks,
        ["document_serial"]=serial.ToString(), ["model_path"]=paths.ModelPath, ["document_path"]=paths.ModelPath,
        ["storage"]=paths.Storage, ["session_dir"]=paths.SessionDir, ["ready_path"]=paths.ReadyPath,
        ["state_db"]=paths.StateDb, ["engine"]=engine, ["temp"]=paths.Temp, ["rhino_temp"]=Path.GetTempPath(),
        ["model_units"]=units, ["valid"]=true, ["status"]="starting"
    };

    public static bool MatchesDocument(Dictionary<string, object?> binding, string? path, uint serial) =>
        !string.IsNullOrWhiteSpace(path) && serial.ToString() == (string)binding["document_serial"]! &&
        SessionFiles.Same(path, (string)binding["model_path"]!);

    static void CheckOwner(Dictionary<string, object?> binding, string path)
    {
        if (!File.Exists(path)) return;
        using var json = SessionFiles.ReadJson(path);
        if (SessionFiles.Text(json.RootElement, "token") != (string)binding["token"]!)
            throw new IOException("Another session owns this binding record; it was preserved.");
    }

    public static void Publish(Dictionary<string, object?> binding, string path)
    {
        CheckOwner(binding, path);
        SessionFiles.WriteJson(path, binding);
    }

    public static void Invalidate(Dictionary<string, object?> binding, string readyPath, string reason, BoundBridge? bridge)
    {
        binding["valid"] = false;
        binding["status"] = reason;
        try { Publish(binding, readyPath); }
        finally { bridge?.Stop(); }
    }

    public static bool Release(Dictionary<string, object?> binding, string sessionDirectory,
        string readyPath, string locatorPath, BoundBridge? bridge, Action releaseLeases)
    {
        bridge?.Stop();
        if (bridge != null && !bridge.IsDrained) return false;
        // Retain the worker gate until the binding, locator and native owner have all been released.
        using var workerGate = new FileStream(Path.Combine(sessionDirectory, "mcp.lock"),
            FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        binding["valid"] = false;
        Publish(binding, readyPath);
        CheckOwner(binding, locatorPath);
        if (File.Exists(locatorPath)) File.Delete(locatorPath);
        bridge?.Dispose();
        releaseLeases();
        return true;
    }
}
