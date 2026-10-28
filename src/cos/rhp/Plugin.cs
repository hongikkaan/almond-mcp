using System.Runtime.InteropServices;
using Rhino;
using Rhino.Commands;
using Rhino.PlugIns;

[assembly: Guid("39EB74F6-8283-4E43-BF26-F0106D891B75")]

namespace AlmondRhino;

public sealed class RhinoPlugin : PlugIn
{
    internal static RhinoPlugin Instance { get; private set; } = null!;
    internal RhinoHost? Host;
    public RhinoPlugin() => Instance = this;
    protected override void OnShutdown()
    {
        Host?.Dispose();
        base.OnShutdown();
    }
}

public sealed class ConnectCommand : Command
{
    public override string EnglishName => "almondconnect";
    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        try
        {
            RhinoPlugin.Instance.Host ??= new RhinoHost();
            RhinoApp.WriteLine(RhinoPlugin.Instance.Host.StatusText());
            return Result.Success;
        }
        catch (Exception ex) { RhinoApp.WriteLine("Almond 연결: " + ex.GetBaseException().Message); return Result.Failure; }
    }
}

public sealed class DisconnectCommand : Command
{
    public override string EnglishName => "almonddisconnect";
    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        var host = RhinoPlugin.Instance.Host;
        if (host == null) { RhinoApp.WriteLine("Almond 연결이 없습니다."); return Result.Success; }
        RhinoApp.WriteLine(host.DisconnectFromRhino());
        return Result.Success;
    }
}
