using Rhino;

namespace AlmondEngine;

/// <summary>The authenticated UI-thread request, independent of its transport envelope.</summary>
public sealed record BridgeDispatchContext(RhinoDoc Document, string ModelPath, uint DocumentSerial,
    string SessionToken, string OperationId, string RequestId)
{
    public void ValidateDocument()
    {
        if (!ReferenceEquals(RhinoDoc.ActiveDoc, Document) || Document.RuntimeSerialNumber != DocumentSerial ||
            string.IsNullOrWhiteSpace(Document.Path) || !SessionFiles.Same(Document.Path, ModelPath))
            throw new InvalidOperationException("The bound Rhino document changed. Reconnect before another request.");
    }
}

public interface IBridgeRequestHandler
{
    IReadOnlyDictionary<string, string> LibraryDirectories { get; }
    string HandleRequest(BridgeDispatchContext context, string request);
}

public interface IBridgeProvider
{
    IBridgeRequestHandler RequestHandler { get; }
}
