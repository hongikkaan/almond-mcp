#nullable enable
using System;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Eto.Forms;
using Rhino;
using EApplication = Eto.Forms.Application;

namespace RhinoTerminal;

// Rhino owns one terminal runtime. Views may be created, hidden or disposed
// without creating or stopping its shell and document-bound Almond host.
internal sealed class TerminalRuntime
{
    public static TerminalRuntime Instance { get; } = new();
    const int HistoryLimit = 131072;
    readonly UITimer timer = new() { Interval = 0.04 };
    readonly StringBuilder output = new();
    TerminalSession? session;
    AlmondHost? almond;
    long outputStart;
    int columns = 90, rows = 28;
    string workingDirectory = "";
    public string Status { get; private set; } = "정지됨 — RhinoTerminal On 또는 새 터미널로 시작";
    public string WorkingDirectory => almond?.ProjectDirectory ?? workingDirectory;
    public bool Running => session?.Completion?.IsCompleted == false;
    public bool Ready => Running && session!.Pid > 0;
    public int Generation { get; private set; }

    TerminalRuntime() => timer.Elapsed += (_, _) => Pump();

    static string ShellLiteral(string text) => "'" + text.Replace("'", "''") + "'";

    public void Start()
    {
        if (Running) return;
        session?.Stop();
        almond?.Dispose();
        var next = new TerminalSession();
        session = next;
        AlmondHost? ownAlmond = null;
        ownAlmond = new AlmondHost(text => {
            if (ReferenceEquals(almond, ownAlmond)) Status = text;
        });
        almond = ownAlmond;
        var doc = RhinoDoc.ActiveDoc;
        workingDirectory = !string.IsNullOrWhiteSpace(doc?.Path)
            ? Path.GetDirectoryName(doc!.Path)! : Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (!Directory.Exists(workingDirectory))
            workingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        output.Clear();
        outputStart = 0;
        Generation++;
        Status = "PowerShell 시작 중";
        next.Resize(columns, rows);
        next.Status += text => EApplication.Instance?.AsyncInvoke(() => {
            if (ReferenceEquals(session, next) && ReferenceEquals(almond, ownAlmond)) Status = text;
        });
        // Register the existing shell-local entry point; AI starts only on input.
        var script = "$u=New-Object System.Text.UTF8Encoding($false); " +
            "[Console]::InputEncoding=$u; [Console]::OutputEncoding=$u; $OutputEncoding=$u; " +
            "Set-Location -LiteralPath " + ShellLiteral(workingDirectory) + "; " +
            "Write-Host 'Rhino Terminal | PowerShell'; " +
            "function global:almond { & " + ShellLiteral(Path.Combine(ownAlmond.Engine, "terminal_almond.ps1")) +
            " -PipeName " + ShellLiteral(ownAlmond.PipeName) + " -AccessToken " + ShellLiteral(ownAlmond.AccessToken) + " @args }; " +
            "Write-Host '현재 Rhino 문서에 연결: almond (새 대화) / almond resume (이전 대화)'; " +
            "Write-Host '그냥 codex를 실행하면 이 문서의 Almond 연결은 설정되지 않습니다.'";
        next.Start(workingDirectory, script);
        _ = next.Completion!.ContinueWith(_ => EApplication.Instance?.AsyncInvoke(() => {
            if (ReferenceEquals(almond, ownAlmond)) ownAlmond.Release();
        }), TaskScheduler.Default);
        timer.Start();
    }

    public void Stop()
    {
        session?.Stop();
        almond?.Dispose();
        almond = null;
        Pump();
        // Stop terminates the contained process synchronously; its reader may
        // still drain asynchronously. A later On must not reuse that shell.
        session = null;
        timer.Stop();
        Status = "종료됨 — RhinoTerminal On 또는 새 터미널로 다시 시작";
    }

    public Task Write(string text) => Running ? session!.Write(text) : Task.CompletedTask;

    public void Resize(int cols, int lines)
    {
        columns = Math.Clamp(cols, 20, 500);
        rows = Math.Clamp(lines, 5, 200);
        session?.Resize(columns, rows);
    }

    void Pump()
    {
        // Drain even without a view: TerminalSession's bounded output channel
        // must not block a hidden shell. Keep only a bounded recent replay.
        almond?.CheckDocument();
        var read = 0;
        while (read < 32768 && session?.Output.Reader.TryRead(out var chunk) == true)
        {
            output.Append(chunk);
            read += chunk.Length;
        }
        if (output.Length > HistoryLimit)
        {
            var remove = output.Length - HistoryLimit;
            output.Remove(0, remove);
            outputStart += remove;
        }
    }

    public string ReadOutput(ref long position)
    {
        var start = (int)Math.Clamp(position - outputStart, 0, output.Length);
        var text = output.ToString(start, output.Length - start);
        position = outputStart + output.Length;
        return text;
    }
}
