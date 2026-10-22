// Only Rhino dispatch and native work are simulated. The host, paths and file leases
// are the actual production source linked by this fixture project.
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
    public sealed class DocumentEventArgs : EventArgs
    {
        public RhinoDoc? Document { get; set; }
    }
    public sealed class DocumentSaveEventArgs : EventArgs { }
    public static class RhinoApp
    {
        public static void WriteLine(string value) { }
    }
}
namespace Eto.Forms
{
    public sealed class Application
    {
        public static Application? Instance => null;
        public void AsyncInvoke(Action action) => action();
    }
}
namespace AlmondEngine
{
    public sealed class BoundBridge : IDisposable
    {
        public static bool FailStart;
        public static int PendingOnStart;
        public bool IsRunning { get; set; }
        public bool IsAlive { get; set; }
        public int Pending { get; set; }
        public bool KeepListener { get; set; }
        public bool IsDrained => !IsRunning && !IsAlive && Pending == 0;
        public bool Disposed { get; private set; }

        public BoundBridge(int port, string readyPath, string token, string modelPath, uint docSerial) { }
        public void Start()
        {
            Pending = PendingOnStart;
            if (FailStart) throw new IOException("fixture native start failure");
            throw new InvalidOperationException("This fixture never starts a native listener.");
        }
        public void Stop()
        {
            IsRunning = false;
            if (!KeepListener) IsAlive = false;
        }
        public void Dispose()
        {
            if (!IsDrained) throw new InvalidOperationException("Disposed before native drain.");
            Disposed = true;
        }
    }
}
