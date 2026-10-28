// Exercise the real command, panel and runtime without launching Rhino or a shell.
#pragma warning disable CS0067
using System.Threading.Channels;

namespace Rhino
{
    public sealed class RhinoDoc
    {
        public static RhinoDoc? ActiveDoc { get; set; }
        public string Path { get; set; } = "";
    }
    public static class RhinoApp
    {
        public static void WriteLine(string value) { }
    }
}
namespace Rhino.Commands
{
    public enum Result { Success, Cancel, Failure }
    public enum RunMode { Interactive, Scripted }
    public abstract class Command
    {
        public abstract string EnglishName { get; }
        protected abstract Result RunCommand(Rhino.RhinoDoc doc, RunMode mode);
        public Result Execute() => RunCommand(new Rhino.RhinoDoc(), RunMode.Interactive);
    }
}
namespace Rhino.Input
{
    public enum GetResult { Option, Cancel, Nothing }
}
namespace Rhino.Input.Custom
{
    public sealed class GetOption : IDisposable
    {
        public static string Selected = "";
        public static string[] LastOptions = Array.Empty<string>();
        readonly List<string> options = new();
        public void SetCommandPrompt(string value) { }
        public int AddOption(string name) { options.Add(name); return options.Count; }
        public Rhino.Input.GetResult Get()
        {
            LastOptions = options.ToArray();
            return options.Contains(Selected) ? Rhino.Input.GetResult.Option : Rhino.Input.GetResult.Cancel;
        }
        public int OptionIndex() => options.IndexOf(Selected) + 1;
        public Rhino.Commands.Result CommandResult() => Rhino.Commands.Result.Cancel;
        public void Dispose() { }
    }
}
namespace Rhino.UI
{
    public static class Panels
    {
        public static bool Visible;
        public static int OpenCalls;
        public static bool IsPanelVisible(Guid id) => Visible;
        public static void OpenPanel(Guid id) { Visible = true; OpenCalls++; }
        public static void ClosePanel(Guid id) => Visible = false;
    }
}
namespace Eto.Forms
{
    public class Panel : IDisposable
    {
        public object? Content { get; set; }
        protected virtual void Dispose(bool disposing) { }
        public void Dispose() => Dispose(true);
    }
    public sealed class WebView
    {
        public bool BrowserContextMenuEnabled { get; set; }
        public List<string> Scripts { get; } = new();
        public event EventHandler<WebViewMessageEventArgs>? MessageReceived;
        public void LoadHtml(string html) { }
        public Task ExecuteScriptAsync(string script) { Scripts.Add(script); return Task.CompletedTask; }
        public void Receive(string json) => MessageReceived?.Invoke(this, new WebViewMessageEventArgs { Message = json });
    }
    public sealed class WebViewMessageEventArgs : EventArgs { public string Message { get; set; } = ""; }
    public sealed class UITimer : IDisposable
    {
        static readonly List<UITimer> all = new();
        bool running;
        public UITimer() => all.Add(this);
        public double Interval { get; set; }
        public event EventHandler? Elapsed;
        public void Start() => running = true;
        public void Stop() => running = false;
        public void Dispose() => all.Remove(this);
        public static void TickAll()
        {
            foreach (var timer in all.ToArray()) if (timer.running) timer.Elapsed?.Invoke(timer, EventArgs.Empty);
        }
    }
    public sealed class Application
    {
        public static Application Instance { get; } = new();
        public void AsyncInvoke(Action action) => action();
    }
    public enum MessageBoxButtons { YesNo }
    public enum MessageBoxType { Warning }
    public enum DialogResult { Yes, No }
    public static class MessageBox
    {
        public static DialogResult Answer = DialogResult.Yes;
        public static DialogResult Show(Panel owner, string text, string title, MessageBoxButtons buttons, MessageBoxType type) => Answer;
    }
}
namespace System.Windows.Forms
{
    public static class Clipboard
    {
        static string text = "";
        public static void SetText(string value) => text = value;
        public static bool ContainsText() => text.Length > 0;
        public static string GetText() => text;
    }
}
namespace RhinoTerminal
{
    internal sealed class TerminalSession
    {
        public static readonly List<TerminalSession> Created = new();
        readonly TaskCompletionSource<int> completion = new();
        public TerminalSession() => Created.Add(this);
        public Task? Completion { get; private set; }
        public int Pid => Completion == null ? 0 : 123;
        public Channel<string> Output { get; } = Channel.CreateUnbounded<string>();
        public event Action<string>? Status;
        public bool Stopped { get; private set; }
        public bool DelayCompletionOnStop { get; set; }
        public List<string> Input { get; } = new();
        public void Start(string cwd, string script) => Completion = completion.Task;
        public void Stop() { Stopped = true; if (!DelayCompletionOnStop) completion.TrySetResult(0); }
        public Task Write(string text) { Input.Add(text); return Task.CompletedTask; }
        public void Resize(int columns, int rows) { }
    }
    internal sealed class AlmondHost : IDisposable
    {
        public static readonly List<AlmondHost> Created = new();
        public AlmondHost(Action<string> report) { Report = report; Created.Add(this); }
        public Action<string> Report { get; }
        public string Engine => Path.GetTempPath();
        public string PipeName => "fixture";
        public string AccessToken => "fixture";
        public string? ProjectDirectory => null;
        public bool Disposed { get; private set; }
        public int Checks { get; private set; }
        public void CheckDocument() => Checks++;
        public bool Release() => true;
        public void Dispose() => Disposed = true;
    }
}
