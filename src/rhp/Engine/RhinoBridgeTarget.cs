using System.Text.Json;
using Rhino;

namespace AlmondEngine;

internal readonly record struct NativeRequestIdentity(string ModelPath, uint DocumentSerial,
    string SessionToken, string OperationId, string RequestId);

internal interface IBridgeTarget
{
    void Validate(string modelPath, uint documentSerial);
    void ValidateLibraries(JsonElement libraries) { }
    string Handle(string request, NativeRequestIdentity identity);
}

/// <summary>Uses the loaded plugin's explicit Engine contract; never owns its lifetime.</summary>
internal sealed class RhinoBridgeTarget : IBridgeTarget
{
    static readonly Guid PluginId = new("c337dbb8-394a-4593-9c2b-a3d7cfc91893");
    readonly IBridgeProvider provider;
    readonly IBridgeRequestHandler handler;

    internal RhinoBridgeTarget()
    {
        provider = Rhino.PlugIns.PlugIn.Find(PluginId) as IBridgeProvider
            ?? throw new InvalidOperationException("Load a compatible RhinoAlmondBridge plugin first.");
        handler = provider.RequestHandler ?? throw new InvalidOperationException("The Bridge is not initialized.");
    }

    public void Validate(string modelPath, uint documentSerial)
    {
        if (!ReferenceEquals(Rhino.PlugIns.PlugIn.Find(PluginId), provider) ||
            !ReferenceEquals(provider.RequestHandler, handler))
            throw new InvalidOperationException("The Bridge instance changed. Reconnect.");
        var document = RhinoDoc.ActiveDoc;
        if (document == null || document.RuntimeSerialNumber != documentSerial ||
            string.IsNullOrWhiteSpace(document.Path) || !SessionFiles.Same(document.Path, modelPath))
            throw new InvalidOperationException("The active Rhino document changed. Reconnect.");
    }

    public void ValidateLibraries(JsonElement libraries) => NativeLibraryRoots.Validate(handler.LibraryDirectories, libraries);

    public string Handle(string request, NativeRequestIdentity identity)
    {
        Validate(identity.ModelPath, identity.DocumentSerial);
        var context = new BridgeDispatchContext(RhinoDoc.ActiveDoc!, identity.ModelPath, identity.DocumentSerial,
            identity.SessionToken, identity.OperationId, identity.RequestId);
        return handler.HandleRequest(context, request);
    }
}
