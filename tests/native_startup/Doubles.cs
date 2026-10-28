// Production plugin/command entry points are linked unchanged. This fixture
// observes startup and routing without loading Rhino or creating a process.
namespace Rhino {
    public class RhinoDoc { }
    public static class RhinoApp {
        public static void WriteLine(string text, params object[] args) { }
        public static void InvokeOnUiThread(Action action) => action();
    }
}
namespace Rhino.Commands {
    public enum Result { Success, Failure }
    public enum RunMode { Interactive }
    public abstract class Command {
        public abstract string EnglishName { get; }
        protected abstract Result RunCommand(Rhino.RhinoDoc doc, RunMode mode);
        public Result RunForTest() => RunCommand(new Rhino.RhinoDoc(), RunMode.Interactive);
    }
}
namespace Rhino.PlugIns {
    public enum PlugInLoadTime { AtStartup }
    public enum LoadReturnCode { Success }
    public class PlugIn {
        public virtual PlugInLoadTime LoadTime => PlugInLoadTime.AtStartup;
        protected virtual LoadReturnCode OnLoad(ref string errorMessage) => LoadReturnCode.Success;
        protected virtual void OnShutdown() { }
        protected virtual bool ShouldCallWriteDocument(Rhino.FileIO.FileWriteOptions options) => false;
        protected virtual void WriteDocument(Rhino.RhinoDoc doc, Rhino.FileIO.BinaryArchiveWriter archive, Rhino.FileIO.FileWriteOptions options) { }
        protected virtual void ReadDocument(Rhino.RhinoDoc doc, Rhino.FileIO.BinaryArchiveReader archive, Rhino.FileIO.FileReadOptions options) { }
        public void LoadForTest() { string error = ""; OnLoad(ref error); }
    }
}
namespace Rhino.FileIO {
    public class FileWriteOptions { }
    public class FileReadOptions { }
    public class BinaryArchiveWriter { }
    public class BinaryArchiveReader { }
}
namespace Rhino.UI {
    public enum PanelType { System }
    public static class Panels {
        public static int Registered;
        public static void RegisterPanel(object plugin, Type panel, string name, object icon, PanelType type = PanelType.System) => Registered++;
    }
}
namespace RhinoAlmondBridge {
    // Startup tests do not serialize a document. Fail if startup unexpectedly does.
    public static class ComponentSemanticRegistry {
        public static void Write(Rhino.RhinoDoc doc, Rhino.FileIO.BinaryArchiveWriter archive) => throw new InvalidOperationException("Unexpected document write during startup");
        public static void Read(Rhino.RhinoDoc doc, Rhino.FileIO.BinaryArchiveReader archive, Rhino.FileIO.FileReadOptions options) => throw new InvalidOperationException("Unexpected document read during startup");
    }
    public class BridgeServer {
        public static int Starts;
        public BridgeServer(int port = 5000) { }
        public void Start() => Starts++;
        public void Stop() { }
    }
    public class AlmondLibraryPanel { }
    public class AlmondResultsPanel { }
    public static class AlmondLibraryCommand { public static void StopArchive() { } }
}
namespace RhinoTerminal { public class TerminalPanel { public static void StopAll() { } } }
namespace AlmondRhino {
    internal class RhinoHost : IDisposable {
        public int Disconnects;
        public string StatusText() => "Ready";
        public string DisconnectFromRhino() { Disconnects++; return "Disconnected"; }
        public void Dispose() { }
    }
}
