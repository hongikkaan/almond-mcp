using Rhino;
using Rhino.Commands;
using Rhino.Input;
using Rhino.Input.Custom;
using Rhino.UI;

namespace RhinoTerminal;

public sealed class OpenTerminalCommand : Command
{
    public override string EnglishName => "RhinoTerminal";
    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        using var option = new GetOption();
        option.SetCommandPrompt("RhinoTerminal 실행 또는 패널 표시");
        var on = option.AddOption("On");
        var off = option.AddOption("Off");
        var toggle = option.AddOption("PanelToggle");
        if (option.Get() != GetResult.Option) return option.CommandResult();
        var selected = option.OptionIndex();
        if (selected == on) TerminalRuntime.Instance.Start();
        else if (selected == off) TerminalRuntime.Instance.Stop();
        else if (selected == toggle)
        {
            var id = typeof(TerminalPanel).GUID;
            if (Panels.IsPanelVisible(id)) Panels.ClosePanel(id);
            else Panels.OpenPanel(id);
        }
        return Result.Success;
    }
}
