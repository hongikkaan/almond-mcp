#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Eto.Forms;
using Rhino;
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
    readonly TerminalRuntime runtime = TerminalRuntime.Instance;
    bool webReady, disposed, flushing;
    int generation = -1;
    long outputPosition;
    string? notice, previousMeta;

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

    void StartTerminal()
    {
        if (disposed) return;
        if (runtime.Running)
        {
            var result = MessageBox.Show(this,
                "현재 터미널과 그 안에서 실행한 프로그램을 종료하고 새로 엽니다. 진행 중인 작업을 먼저 마치세요.",
                "새 터미널", MessageBoxButtons.YesNo, MessageBoxType.Warning);
            if (result != DialogResult.Yes) return;
        }
        notice = null;
        runtime.Stop();
        runtime.Start();
    }

    void StopTerminal(bool confirm)
    {
        if (confirm && runtime.Running &&
            MessageBox.Show(this,
                "터미널과 이 터미널이 실행한 프로그램을 종료합니다. 미완료 작업은 중단됩니다. Rhino 모델은 저장하거나 닫지 않습니다.",
                "터미널 종료", MessageBoxButtons.YesNo, MessageBoxType.Warning) != DialogResult.Yes) return;
        notice = null;
        runtime.Stop();
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
                    break;
                case "input":
                    if (root.TryGetProperty("text", out var input))
                        await runtime.Write(input.GetString() ?? "");
                    break;
                case "resize":
                    runtime.Resize(root.GetProperty("cols").GetInt32(), root.GetProperty("rows").GetInt32());
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
                    else notice = "텍스트를 복사한 뒤 붙여넣으세요. 이미지는 파일 경로로 전달하세요.";
                    break;
            }
        }
        catch (Exception ex)
        {
            notice = "터미널 오류: " + ex.Message;
            RhinoApp.WriteLine(notice);
        }
    }

    async Task Script(string script)
    {
        if (!disposed && webReady) await web.ExecuteScriptAsync(script);
    }

    async Task Flush()
    {
        if (disposed || !webReady || flushing) return;
        flushing = true;
        try
        {
            if (generation != runtime.Generation)
            {
                generation = runtime.Generation;
                outputPosition = 0;
                notice = null;
                await Script("window.RhinoTerminal.reset()");
            }
            var meta = JsonSerializer.Serialize(new {
                status = notice ?? runtime.Status, cwd = runtime.WorkingDirectory,
                running = runtime.Running, ready = runtime.Ready,
                rhino_pid = Environment.ProcessId
            });
            if (meta != previousMeta)
            {
                await Script("window.RhinoTerminal.meta(" + meta + ")");
                previousMeta = meta;
            }
            var text = runtime.ReadOutput(ref outputPosition);
            if (text.Length > 0)
                await Script("window.RhinoTerminal.write(" + JsonSerializer.Serialize(text) + ")");
        }
        catch (Exception ex)
        {
            if (!disposed) notice = "화면 출력 오류: " + ex.Message;
        }
        finally { flushing = false; }
    }

    void Shutdown()
    {
        if (disposed) return;
        disposed = true;
        timer.Stop();
        timer.Dispose();
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
        TerminalRuntime.Instance.Stop();
        foreach (var panel in panels.ToArray()) panel.Shutdown();
    }
}
