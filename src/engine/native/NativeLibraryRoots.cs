using System.Reflection;
using System.Text.Json;

namespace AlmondEngine;

/// <summary>Checks paths cached by the loaded original helpers without changing their state.</summary>
internal static class NativeLibraryRoots
{
    static readonly (string Helper, string Field, string Variable)[] Fields = {
        ("_validator", "_templateDir", "RHINO_MCP_LIBRARY_DIR"),
        ("_validator", "_capsuleDir", "RHINO_MCP_CAPSULE_DIR"),
        ("_definitionRunner", "_libraryDir", "RHINO_MCP_LIBRARY_DIR"),
        ("_definitionRunner", "_capsuleDir", "RHINO_MCP_CAPSULE_DIR"),
        ("_drawingAssetManager", "_libraryRoot", "RHINO_MCP_DRAWING_ASSET_DIR")
    };

    internal static void Validate(object server, JsonElement libraries)
    {
        foreach (var (helperName, fieldName, variable) in Fields)
        {
            object helper = ReadField(server, helperName);
            object cached = ReadField(helper, fieldName);
            if (cached is not string path || string.IsNullOrWhiteSpace(path) ||
                !libraries.TryGetProperty(variable, out var expected) || expected.ValueKind != JsonValueKind.String ||
                string.IsNullOrWhiteSpace(expected.GetString()) ||
                !SessionFiles.Same(path, expected.GetString()!))
                throw new IOException("The loaded native library directory differs from this worker: " + variable +
                    ". Restart Rhino with the selected library configuration.");
        }
    }

    static object ReadField(object owner, string name) =>
        owner.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(owner)
        ?? throw new IOException("The loaded native library cache is unavailable: " + name);
}
