using System.Runtime.InteropServices;
using Rhino;
using Rhino.Commands;
using Rhino.PlugIns;
using Rhino.UI;

[assembly: Guid("27D4B9A1-8FAD-421C-B64A-7A213D3B4079")]

namespace RhinoTerminal;

public sealed class TerminalPlugin : PlugIn
{
    public static TerminalPlugin Instance { get; private set; } = null!;
    public TerminalPlugin() { Instance = this; }

    protected override LoadReturnCode OnLoad(ref string errorMessage)
    {
        Panels.RegisterPanel(this, typeof(TerminalPanel), "Terminal",
            System.Drawing.SystemIcons.Application, PanelType.System);
        return LoadReturnCode.Success;
    }

    protected override void OnShutdown()
    {
        TerminalPanel.StopAll();
        base.OnShutdown();
    }
}

public sealed class OpenTerminalCommand : Command
{
    public override string EnglishName => "RhinoTerminal";
    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        Panels.OpenPanel(typeof(TerminalPanel).GUID);
        return Result.Success;
    }
}
