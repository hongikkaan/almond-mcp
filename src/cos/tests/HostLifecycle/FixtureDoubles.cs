// The production host, path calculation and OS leases are linked unchanged.
// Rhino UI and the native transport are simulated; no Rhino assembly is loaded.
#pragma warning disable CS0067
namespace Rhino
{
    public sealed class RhinoDoc
    {
        public static RhinoDoc? ActiveDoc { get; set; }
        public string Path { get; set; } = "";
        public uint RuntimeSerialNumber { get; set; } = 1;
        public string ModelUnitSystem => "Millimeters";
        public static event EventHandler<DocumentEventArgs>? ActiveDocumentChanged;
        public static event EventHandler<DocumentSaveEventArgs>? EndSaveDocument;
        public static event EventHandler<DocumentEventArgs>? CloseDocument;
    }
    public sealed class DocumentEventArgs : EventArgs { public RhinoDoc? Document { get; set; } }
    public sealed class DocumentSaveEventArgs : EventArgs { }
    public static class RhinoApp
    {
        public static event EventHandler? Idle;
        public static void WriteLine(string value) { }
    }
}
namespace Eto.Forms
{
    public sealed class Application
    {
        public static Application Instance { get; } = new();
        public void AsyncInvoke(Action action) => action();
    }
}
namespace AlmondCOS
{
    internal sealed class ControlPipe : IDisposable
    {
        internal ControlPipe(string name, string accessToken,
            Func<System.Text.Json.JsonElement, CancellationToken, Task<object>> handler,
            Func<string, Task> disconnected) { }
        public void Dispose() { }
    }
}
namespace AlmondEngine
{
    public sealed class BoundBridge : IDisposable
    {
        public bool IsRunning { get; set; } = true;
        public bool IsAlive { get; set; } = true;
        public bool KeepListener { get; set; }
        public int Pending { get; set; }
        public bool IsDrained => !IsRunning && !IsAlive && Pending == 0;
        public bool Disposed { get; private set; }
        public Action? OnDispose { get; set; }
        public BoundBridge(int port, string readyPath, string token, string modelPath, uint documentSerial) { }
        public void Start() => throw new InvalidOperationException("This fixture never attaches a real Rhino.");
        public void Stop() { IsRunning = false; if (!KeepListener) IsAlive = false; }
        public void Dispose()
        {
            if (!IsDrained) throw new InvalidOperationException("Native work was disposed before drain.");
            OnDispose?.Invoke();
            Disposed = true;
        }
    }
}
