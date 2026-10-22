using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Eto.Forms;
using Rhino;
using EApplication = Eto.Forms.Application;
using Panel = Eto.Forms.Panel;
using MessageBox = Eto.Forms.MessageBox;
using MessageBoxButtons = Eto.Forms.MessageBoxButtons;
using DialogResult = Eto.Forms.DialogResult;

namespace RhinoTerminal;

[Guid("4B3493B2-3421-4BEC-A8C8-F7F1786E8495")]
public sealed class TerminalPanel : Panel
{
    static readonly HashSet<TerminalPanel> panels = new();
    readonly WebView web = new() { BrowserContextMenuEnabled = false };
    readonly UITimer timer = new() { Interval = 0.04 };
    TerminalSession? session;
    AlmondHost? almond;
    bool webReady, disposed, flushing;
    int columns = 90, rows = 28;
    string status = "터미널 준비 중", workingDirectory = "";
    bool metaDirty = true;

    public TerminalPanel()
    {
        panels.Add(this);
        Content = web;
        web.MessageReceived += OnMessage;
        timer.Elapsed += async (_, _) => await Flush();
        var html = Resource("terminal.html")
            .Replace("/* XTERM_CSS */", Resource("xterm.css"))
            .Replace("/* XTERM_JS */", Resource("xterm.js"))
            .Replace("/* FIT_JS */", Resource("addon-fit.js"));
        web.LoadHtml(html);
        timer.Start();
    }

    static string Resource(string name)
    {
        using var stream = typeof(TerminalPanel).Assembly.GetManifestResourceStream("RhinoTerminal." + name)
            ?? throw new InvalidOperationException("Missing terminal resource: " + name);
        using var reader = new StreamReader(stream, Encoding.UTF8);
        return reader.ReadToEnd();
    }

    static string ShellLiteral(string text) => "'" + text.Replace("'", "''") + "'";

    void StartTerminal()
    {
        if (disposed) return;
        if (session != null && session.Completion?.IsCompleted == false)
        {
            var result = MessageBox.Show(this,
                "현재 터미널과 그 안에서 실행한 프로그램을 종료하고 새로 엽니다. 진행 중인 작업을 먼저 마치세요.",
                "새 터미널", MessageBoxButtons.YesNo, MessageBoxType.Warning);
            if (result != DialogResult.Yes) return;
        }
        session?.Stop();
        almond?.Dispose();
        almond = new AlmondHost(text => { if (!disposed) { status = text; metaDirty = true; } });
        var doc = RhinoDoc.ActiveDoc;
        workingDirectory = !string.IsNullOrWhiteSpace(doc?.Path)
            ? Path.GetDirectoryName(doc!.Path)! : Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (!Directory.Exists(workingDirectory))
            workingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var next = new TerminalSession();
        session = next;
        status = "PowerShell 시작 중";
        metaDirty = true;
        next.Resize(columns, rows);
        next.Status += text => EApplication.Instance?.AsyncInvoke(() => {
            if (!disposed && ReferenceEquals(session, next)) { status = text; metaDirty = true; }
        });
        // Register a shell-local command, but do not start an AI automatically.
        var script = "$u=New-Object System.Text.UTF8Encoding($false); " +
            "[Console]::InputEncoding=$u; [Console]::OutputEncoding=$u; $OutputEncoding=$u; " +
            "Set-Location -LiteralPath " + ShellLiteral(workingDirectory) + "; " +
            "Write-Host 'Rhino Terminal | PowerShell'; " +
            "function global:almond { & " + ShellLiteral(Path.Combine(almond.Engine, "terminal_almond.ps1")) +
            " -PipeName " + ShellLiteral(almond.PipeName) + " -AccessToken " + ShellLiteral(almond.AccessToken) + " @args }; " +
            "Write-Host '현재 Rhino 문서에 연결: almond (새 대화) / almond resume (이전 대화)'; " +
            "Write-Host '그냥 codex를 실행하면 이 문서의 Almond 연결은 설정되지 않습니다.'";
        next.Start(workingDirectory, script);
        var ownAlmond = almond;
        _ = next.Completion!.ContinueWith(_ => EApplication.Instance?.AsyncInvoke(() => {
            if (!disposed && ReferenceEquals(session, next)) ownAlmond?.Release();
        }), TaskScheduler.Default);
        _ = Script("window.RhinoTerminal.reset()");
    }

    void StopTerminal(bool confirm)
    {
        if (confirm && session?.Completion?.IsCompleted == false &&
            MessageBox.Show(this,
                "터미널과 이 터미널이 실행한 프로그램을 종료합니다. 미완료 작업은 중단됩니다. Rhino 모델은 저장하거나 닫지 않습니다.",
                "터미널 종료", MessageBoxButtons.YesNo, MessageBoxType.Warning) != DialogResult.Yes) return;
        session?.Stop();
        almond?.Dispose(); almond = null;
        status = "종료됨 — 새 터미널로 다시 시작";
        metaDirty = true;
    }

    async void OnMessage(object? sender, WebViewMessageEventArgs e)
    {
        try
        {
            if (disposed || string.IsNullOrEmpty(e.Message) || e.Message.Length > 1024 * 1024) return;
            using var json = JsonDocument.Parse(e.Message);
            var root = json.RootElement;
            if (!root.TryGetProperty("type", out var type)) return;
            switch (type.GetString())
            {
                case "ready":
                    if (webReady) return;
                    webReady = true;
                    StartTerminal();
                    break;
                case "input":
                    if (session != null && root.TryGetProperty("text", out var input))
                        await session.Write(input.GetString() ?? "");
                    break;
                case "resize":
                    columns = Math.Clamp(root.GetProperty("cols").GetInt32(), 20, 500);
                    rows = Math.Clamp(root.GetProperty("rows").GetInt32(), 5, 200);
                    session?.Resize(columns, rows);
                    break;
                case "new": StartTerminal(); break;
                case "stop": StopTerminal(true); break;
                case "copy":
                    var text = root.GetProperty("text").GetString();
                    if (!string.IsNullOrEmpty(text)) System.Windows.Forms.Clipboard.SetText(text);
                    break;
                case "paste":
                    if (System.Windows.Forms.Clipboard.ContainsText())
                        await Script("window.RhinoTerminal.paste(" +
                            JsonSerializer.Serialize(System.Windows.Forms.Clipboard.GetText()) + ")");
                    else { status = "텍스트를 복사한 뒤 붙여넣으세요. 이미지는 파일 경로로 전달하세요."; metaDirty = true; }
                    break;
            }
        }
        catch (Exception ex)
        {
            status = "터미널 오류: " + ex.Message;
            metaDirty = true;
            RhinoApp.WriteLine(status);
        }
    }

    async Task Script(string script)
    {
        if (!disposed && webReady) await web.ExecuteScriptAsync(script);
    }

    async Task Flush()
    {
        if (disposed || !webReady || flushing) return;
        almond?.CheckDocument();
        flushing = true;
        try
        {
            if (metaDirty)
            {
                metaDirty = false;
                await Script("window.RhinoTerminal.meta(" + JsonSerializer.Serialize(new {
                    status, cwd = almond?.ProjectDirectory ?? workingDirectory, running = session?.Completion?.IsCompleted == false
                }) + ")");
            }
            var current = session;
            if (current == null) return;
            var buffer = new StringBuilder();
            while (buffer.Length < 32768 && current.Output.Reader.TryRead(out var chunk)) buffer.Append(chunk);
            if (buffer.Length > 0 && ReferenceEquals(current, session))
                await Script("window.RhinoTerminal.write(" + JsonSerializer.Serialize(buffer.ToString()) + ")");
        }
        catch (Exception ex)
        {
            if (!disposed) { status = "화면 출력 오류: " + ex.Message; metaDirty = true; }
        }
        finally { flushing = false; }
    }

    void Shutdown()
    {
        if (disposed) return;
        disposed = true;
        timer.Stop();
        timer.Dispose();
        session?.Stop();
        almond?.Dispose(); almond = null;
        web.MessageReceived -= OnMessage;
        panels.Remove(this);
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) Shutdown();
        base.Dispose(disposing);
    }

    public static void StopAll()
    {
        foreach (var panel in panels.ToArray()) panel.Shutdown();
    }
}
