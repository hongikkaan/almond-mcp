using System.Runtime.InteropServices;
using Rhino;
using Rhino.Commands;
using Rhino.PlugIns;

[assembly: Guid("39EB74F6-8283-4E43-BF26-F0106D891B75")]

namespace AlmondCOS;

public sealed class CosPlugin : PlugIn
{
    internal static CosPlugin Instance { get; private set; } = null!;
    internal CosHost? Host;
    public CosPlugin() => Instance = this;
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
            CosPlugin.Instance.Host ??= new CosHost();
            RhinoApp.WriteLine(CosPlugin.Instance.Host.StatusText());
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
        var host = CosPlugin.Instance.Host;
        if (host == null) { RhinoApp.WriteLine("Almond 연결이 없습니다."); return Result.Success; }
        RhinoApp.WriteLine(host.DisconnectFromRhino());
        return Result.Success;
    }
}
