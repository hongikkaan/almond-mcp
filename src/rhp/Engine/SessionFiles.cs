using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace AlmondEngine;

public sealed class SessionPaths
{
    public string ModelPath { get; }
    public string Storage { get; }
    public string StateDb => Path.Combine(Storage, "scene.sqlite3");
    public string Temp => Path.Combine(Storage, "tmp");
    public string SessionDir { get; }
    public string CallRoot { get; }
    public string ReadyPath => Path.Combine(SessionDir, "ready.json");
    public string LaunchPath => Path.Combine(SessionDir, "launch.json");
    public string LastErrorPath => Path.Combine(SessionDir, "last-error.json");
    public string WorkerPath => Path.Combine(SessionDir, "worker.json");
    public string OperationPath => Path.Combine(SessionDir, "operation.json");
    public string NativePath => Path.Combine(SessionDir, "native.json");
    public string LauncherLock => Path.Combine(SessionDir, "launcher.lock");
    public string RhinoLock => Path.Combine(SessionDir, "rhino.lock");
    public string McpLock => Path.Combine(SessionDir, "mcp.lock");

    internal SessionPaths(string modelPath, string token)
    {
        ModelPath = modelPath;
        Storage = Path.Combine(Path.GetDirectoryName(modelPath)!, ".almond");
        SessionDir = Path.Combine(Storage, ".sessions", token);
        CallRoot = Path.Combine(Temp, "python", token);
    }
}

public static class SessionFiles
{
    public const int StorageProtocol = 2;
    public const string Slots = "ABCDEFGHIJ";

    public static SessionPaths Paths(string modelPath, string slot, string token, bool create = false)
    {
        if (slot.Length != 1 || !Slots.Contains(slot, StringComparison.Ordinal))
            throw new ArgumentException("Invalid Almond slot.", nameof(slot));
        CheckToken(token);
        var model = Canonical(modelPath);
        if (!File.Exists(model) || !Path.GetExtension(model).Equals(".3dm", StringComparison.OrdinalIgnoreCase) ||
            Path.GetFileNameWithoutExtension(model).EndsWith('.') || Path.GetFileNameWithoutExtension(model).EndsWith(' '))
            throw new IOException("An existing saved .3dm file is required.");
        if (model.StartsWith(@"\\", StringComparison.Ordinal) ||
            new DriveInfo(Path.GetPathRoot(model)!).DriveType == DriveType.Network ||
            model.Split('\\', '/').Any(p => p.Equals(".almond", StringComparison.OrdinalIgnoreCase)))
            throw new IOException("Use a local model outside .almond.");
        var paths = new SessionPaths(model, token);
        CheckPlainPath(model);
        CheckPlainPath(paths.SessionDir);
        CheckPlainPath(paths.CallRoot);
        if (create)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(paths.SessionDir)!);
            // CreateDirectoryW fails if this generation existed, even if it is empty.
            if (!CreateDirectoryW(paths.SessionDir, IntPtr.Zero))
                throw new Win32Exception(Marshal.GetLastWin32Error(), "The session token must name a new directory.");
        }
        return paths;
    }

    public static string Canonical(string path) => Path.GetFullPath(path).TrimEnd('\\', '/');
    public static bool Same(string first, string second) =>
        string.Equals(Canonical(first), Canonical(second), StringComparison.OrdinalIgnoreCase);

    internal static void CheckToken(string token)
    {
        if (!Regex.IsMatch(token, @"\A[0-9a-f]{32}\z", RegexOptions.CultureInvariant))
            throw new ArgumentException("A fresh lowercase 32-character token is required.");
    }

    internal static void CheckPlainPath(string path)
    {
        for (var current = Canonical(path); !string.IsNullOrEmpty(current); current = Path.GetDirectoryName(current)!)
        {
            if ((File.Exists(current) || Directory.Exists(current)) &&
                (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Session paths must not contain directory or file links.");
        }
    }

    internal static JsonDocument ReadJson(string path)
    {
        CheckPlainPath(path);
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        if (stream.Length > 1024 * 1024) throw new IOException("Session metadata is too large.");
        return JsonDocument.Parse(stream);
    }

    public static void WriteJson(string path, object value)
    {
        CheckPlainPath(path);
        var temporary = path + ".new-" + Guid.NewGuid().ToString("N");
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                writer.Write(JsonSerializer.Serialize(value));
            var retry = Stopwatch.StartNew();
            while (true)
            {
                try { File.Move(temporary, path, true); break; }
                catch (Exception ex) when ((ex is IOException or UnauthorizedAccessException) &&
                    (ex.HResult & 0xffff) is 5 or 32 or 33 && retry.ElapsedMilliseconds < 200)
                { Thread.Sleep(10); }
            }
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    internal static string Text(JsonElement value, string key) => value.GetProperty(key).GetString() ?? "";
    internal static string Scalar(JsonElement value, string key) => value.GetProperty(key).ToString();

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CreateDirectoryW(string path, IntPtr security);
}
