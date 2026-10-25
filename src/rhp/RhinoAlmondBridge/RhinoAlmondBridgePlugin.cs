using Rhino;
using Rhino.PlugIns;

namespace RhinoAlmondBridge
{
    /// <summary>
    /// RhinoAlmondBridge Plugin - MCP Bridge for AI-driven C# RhinoCommon script execution.
    /// Registers panels and prepares native handlers. Only a bound Engine session
    /// may open a transport and dispatch requests to those handlers.
    /// </summary>
    public class RhinoAlmondBridgePlugin : PlugIn
    {
        private BridgeServer _server;

        public static RhinoAlmondBridgePlugin Instance { get; private set; }

        public RhinoAlmondBridgePlugin()
        {
            Instance = this;
        }

        // Panels and native helpers must exist before a Terminal/Codex/CoS
        // session attaches. Loading this plugin does not start a server.
        public override PlugInLoadTime LoadTime => PlugInLoadTime.AtStartup;

        protected override LoadReturnCode OnLoad(ref string errorMessage)
        {
            RhinoApp.WriteLine("RhinoAlmondBridge: Loading MCP Bridge plugin...");
            Rhino.UI.Panels.RegisterPanel(this, typeof(AlmondLibraryPanel), "Almond", Icon("almond.ico"));
            Rhino.UI.Panels.RegisterPanel(this, typeof(AlmondResultsPanel), "Almond Results", Icon("results.ico"));
            Rhino.UI.Panels.RegisterPanel(this, typeof(RhinoTerminal.TerminalPanel), "Terminal",
                System.Drawing.SystemIcons.Application, Rhino.UI.PanelType.System);

            // Keep this field/type for the Engine's verified handler contract.
            _server = new BridgeServer();
            RhinoApp.WriteLine("Almond 준비됨. 외부 Codex·CoS 연결은 almondconnect, 터미널은 RhinoTerminal → On을 사용하세요.");

            return LoadReturnCode.Success;
        }

        // Panel tab icons, embedded in the assembly (Resources/*.ico, several sizes each).
        private static System.Drawing.Icon Icon(string name)
        {
            try
            {
                using (var stream = typeof(RhinoAlmondBridgePlugin).Assembly.GetManifestResourceStream("RhinoAlmondBridge.Resources." + name))
                    return stream == null ? null : new System.Drawing.Icon(stream);
            }
            catch { return null; }
        }

        protected override void OnShutdown()
        {
            try { RhinoTerminal.TerminalPanel.StopAll(); }
            catch (System.Exception ex) { RhinoApp.WriteLine("RhinoTerminal shutdown failed: " + ex.Message); }
            AlmondLibraryCommand.StopArchive();
            RhinoApp.WriteLine("RhinoAlmondBridge: Plugin shut down.");
            base.OnShutdown();
        }
    }
}
