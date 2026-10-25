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
        public void LoadForTest() { string error = ""; OnLoad(ref error); }
    }
}
namespace Rhino.UI {
    public enum PanelType { System }
    public static class Panels {
        public static int Registered;
        public static void RegisterPanel(object plugin, Type panel, string name, object icon, PanelType type = PanelType.System) => Registered++;
    }
}
namespace RhinoAlmondBridge {
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
namespace AlmondCOS {
    internal class CosHost : IDisposable {
        public int Disconnects;
        public string StatusText() => "Ready";
        public string DisconnectFromRhino() { Disconnects++; return "Disconnected"; }
        public void Dispose() { }
    }
}
