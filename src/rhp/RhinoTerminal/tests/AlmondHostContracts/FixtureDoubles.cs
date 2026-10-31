#pragma warning disable CS0067
namespace Rhino
{
    public sealed class RhinoDoc
    {
        public static RhinoDoc? ActiveDoc { get; set; }
        public string Path { get; set; } = "";
        public uint RuntimeSerialNumber { get; set; } = 7;
        public string ModelUnitSystem => "Millimeters";
        public static event EventHandler<DocumentEventArgs>? ActiveDocumentChanged;
        public static event EventHandler<DocumentSaveEventArgs>? EndSaveDocument;
        public static event EventHandler<DocumentEventArgs>? CloseDocument;
    }
    public sealed class DocumentEventArgs : EventArgs { public RhinoDoc? Document { get; set; } }
    public sealed class DocumentSaveEventArgs : EventArgs { }
    public static class RhinoApp { public static void WriteLine(string message) { } }
}
namespace Eto.Forms { public sealed class Application { public static Application? Instance => null; public void AsyncInvoke(Action action) => action(); } }
namespace AlmondEngine
{
    public sealed class BoundBridge : IDisposable
    {
        public bool IsRunning { get; set; }
        public bool IsAlive { get; set; }
        public int Pending { get; set; }
        public bool IsDrained => !IsRunning && !IsAlive && Pending == 0;
        public bool Disposed { get; private set; }
        public BoundBridge(int port, string ready, string token, string model, uint serial) { }
        public void Start() => throw new InvalidOperationException("No native listener in fixture");
        public void Stop() { IsRunning = false; }
        public void Dispose() { if (!IsDrained) throw new InvalidOperationException("Not drained"); Disposed = true; }
    }
}
