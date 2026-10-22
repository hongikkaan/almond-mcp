using Rhino;
using Rhino.Commands;
using Rhino.UI;

namespace RhinoTerminal;

public sealed class OpenTerminalCommand : Command
{
    public override string EnglishName => "RhinoTerminal";
    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        Panels.OpenPanel(typeof(TerminalPanel).GUID);
        return Result.Success;
    }
}
