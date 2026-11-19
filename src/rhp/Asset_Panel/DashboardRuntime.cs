#nullable enable
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using AlmondEngine;

namespace RhinoAlmondBridge;

// Owns only the read-only Dashboard child. No document or MCP session is created.
internal interface IDashboardProcess : IDisposable
{
    bool Running { get; }
    Task<string> ReadAddressAsync(CancellationToken cancellation);
}

internal sealed class DashboardRuntime : IDisposable
{
    readonly string directory;
    readonly Func<ProcessStartInfo, IDashboardProcess> launch;
    readonly string? database;
    readonly CancellationTokenSource shutdown = new();
    readonly object gate = new();
    IDashboardProcess? process;
    Task<Uri>? opening;
    Uri? address;
    bool disposed;

    internal DashboardRuntime(string directory, Func<ProcessStartInfo, IDashboardProcess>? launch = null, string? database = null)
    {
        this.directory = directory;
        this.launch = launch ?? (start => new DashboardProcess(start));
        this.database = database;
    }

    internal Task<Uri> StartAsync()
    {
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            if (opening != null && (process?.Running == true || !opening.IsCompleted)) return opening;
            process?.Dispose();
            process = null;
            address = null;
            return opening = OpenAsync();
        }
    }

    async Task<Uri> OpenAsync()
    {
        IDashboardProcess? own = null;
        try
        {
            string source = Path.Combine(directory, "dashboard", "__main__.py");
            if (!File.Exists(source)) throw new FileNotFoundException("Dashboard 소스를 찾을 수 없습니다.", source);
            string python = RuntimeEnvironment.PythonExecutable(directory);
            if (!File.Exists(python)) throw new FileNotFoundException("이 플러그인의 Python 환경을 찾을 수 없습니다.", python);
            var start = new ProcessStartInfo(python) {
                UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8,
                WorkingDirectory = directory
            };
            // Rhino's embedded Python can export these paths. The selected
            // external Python must use its own runtime; leave Rhino unchanged.
            foreach (string name in new[] { "PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE" })
                start.Environment.Remove(name);
            // Match the standalone launch arguments without resolving a
            // different checkout or invoking the interactive file picker.
            foreach (string value in new[] { "-B", "-X", "utf8", "-E", "-m", "dashboard", "--port", "0", "--no-browser" })
                start.ArgumentList.Add(value);
            if (database != null)
            {
                start.ArgumentList.Add("--");
                start.ArgumentList.Add(database);
            }
            process = own = launch(start);
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(shutdown.Token);
            deadline.CancelAfter(TimeSpan.FromSeconds(20));
            string url = await own.ReadAddressAsync(deadline.Token).ConfigureAwait(false);
            if (!Uri.TryCreate(url, UriKind.Absolute, out var parsed) || parsed.Scheme != "http" ||
                parsed.Host != "127.0.0.1" || parsed.Port < 1 || parsed.Port > 65535 ||
                parsed.AbsolutePath != "/" || parsed.Query.Length != 0 || parsed.UserInfo.Length != 0 ||
                !Regex.IsMatch(parsed.Fragment, "^#[A-Za-z0-9_-]{32,128}$"))
                throw new InvalidDataException("Dashboard가 유효한 로컬 주소를 반환하지 않았습니다.");
            lock (gate)
            {
                shutdown.Token.ThrowIfCancellationRequested();
                address = parsed;
            }
            return parsed;
        }
        catch
        {
            lock (gate)
            {
                // Dispose may already have stopped this same child.
                if (ReferenceEquals(process, own)) { process?.Dispose(); process = null; }
                address = null;
            }
            throw;
        }
    }

    internal bool AllowsNavigation(Uri target)
    {
        lock (gate)
            return !disposed && process?.Running == true && address != null && target.Scheme == address.Scheme &&
                target.Host == address.Host && target.Port == address.Port && target.UserInfo.Length == 0;
    }

    public void Dispose()
    {
        lock (gate)
        {
            if (disposed) return;
            disposed = true;
            shutdown.Cancel();
            process?.Dispose();
            process = null;
            address = null;
        }
    }
}

internal sealed class DashboardProcess : IDashboardProcess
{
    readonly Process process;
    bool disposed;
    internal DashboardProcess(ProcessStartInfo start)
    {
        process = new Process { StartInfo = start };
        try
        {
            if (!process.Start()) throw new IOException("Dashboard 프로세스를 시작하지 못했습니다.");
            _ = DrainAsync(process.StandardError);
        }
        catch { process.Dispose(); throw; }
    }
    public bool Running => !disposed && !process.HasExited;
    public async Task<string> ReadAddressAsync(CancellationToken cancellation)
    {
        for (int line = 0; line < 8; line++)
        {
            string? text = await process.StandardOutput.ReadLineAsync(cancellation).ConfigureAwait(false);
            if (text == null || text.Length > 4096) break;
            const string prefix = "Almond DB Dashboard: ";
            if (text.StartsWith(prefix, StringComparison.Ordinal))
            {
                _ = DrainAsync(process.StandardOutput);
                return text.Substring(prefix.Length);
            }
        }
        throw new IOException("Dashboard가 시작되지 않았습니다. 이 플러그인의 Python 환경과 Dashboard 소스를 확인하고 다시 여세요.");
    }
    static async Task DrainAsync(StreamReader reader)
    {
        var buffer = new char[2048];
        try { while (await reader.ReadAsync(buffer).ConfigureAwait(false) != 0) { } }
        catch (Exception ex) when (ex is IOException || ex is ObjectDisposedException) { }
    }
    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
        catch (Exception ex) when (ex is InvalidOperationException || ex is System.ComponentModel.Win32Exception) { }
        finally { process.Dispose(); }
    }
}
