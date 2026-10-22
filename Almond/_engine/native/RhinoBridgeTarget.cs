using System.Reflection;
using System.Text.Json;
using Rhino;

namespace AlmondEngine;

internal interface IBridgeTarget
{
    void Validate(string modelPath, uint documentSerial);
    void ValidateLibraries(JsonElement libraries) { }
    string Handle(string request);
}

/// <summary>Reads the already-loaded plugin's handler; never starts, stops, replaces, or patches its server.</summary>
internal sealed class RhinoBridgeTarget : IBridgeTarget
{
    readonly PropertyInfo instanceProperty;
    readonly FieldInfo serverField;
    readonly object plugin, server;
    readonly MethodInfo handler;

    internal RhinoBridgeTarget()
    {
        var assemblies = AppDomain.CurrentDomain.GetAssemblies()
            .Where(a => a.GetName().Name == "RhinoAlmondBridge").ToArray();
        if (assemblies.Length != 1 ||
            assemblies[0].GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion != "0.7.0-rc.2")
            throw new InvalidOperationException("Load the verified RhinoAlmondBridge 0.7.0-rc.2 plugin first.");
        var pluginType = assemblies[0].GetType("RhinoAlmondBridge.RhinoAlmondBridgePlugin", true)!;
        var serverType = assemblies[0].GetType("RhinoAlmondBridge.BridgeServer", true)!;
        instanceProperty = pluginType.GetProperty("Instance", BindingFlags.Static | BindingFlags.Public)
            ?? throw new MissingMemberException(pluginType.FullName, "Instance");
        serverField = pluginType.GetField("_server", BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new MissingFieldException(pluginType.FullName, "_server");
        plugin = instanceProperty.GetValue(null) ?? throw new InvalidOperationException("The original plugin is not initialized.");
        server = serverField.GetValue(plugin) ?? throw new InvalidOperationException("The original server is not initialized.");
        if (server.GetType() != serverType) throw new InvalidOperationException("The original server type changed.");
        handler = serverType.GetMethod("HandleRequest", BindingFlags.Instance | BindingFlags.NonPublic,
            null, new[] { typeof(string) }, null) ?? throw new MissingMethodException(serverType.FullName, "HandleRequest");
        if (handler.ReturnType != typeof(string)) throw new InvalidOperationException("The original request contract changed.");
        foreach (var name in new[] { "_validator", "_definitionRunner", "_drawingAssetManager", "_drawingStyleManager" })
            if (serverType.GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(server) == null)
                throw new InvalidOperationException("The original helper is not initialized: " + name);
    }

    public void Validate(string modelPath, uint documentSerial)
    {
        if (!ReferenceEquals(instanceProperty.GetValue(null), plugin) ||
            !ReferenceEquals(serverField.GetValue(plugin), server))
            throw new InvalidOperationException("The original plugin instance changed. Reconnect.");
        var document = RhinoDoc.ActiveDoc;
        if (document == null || document.RuntimeSerialNumber != documentSerial ||
            string.IsNullOrWhiteSpace(document.Path) || !SessionFiles.Same(document.Path, modelPath))
            throw new InvalidOperationException("The active Rhino document changed. Reconnect.");
    }

    public void ValidateLibraries(JsonElement libraries) => NativeLibraryRoots.Validate(server, libraries);

    public string Handle(string request)
    {
        try { return (string)(handler.Invoke(server, new object[] { request }) ?? throw new IOException("Empty native response.")); }
        catch (TargetInvocationException ex) { throw new IOException("The original native handler failed.", ex.InnerException ?? ex); }
    }
}
