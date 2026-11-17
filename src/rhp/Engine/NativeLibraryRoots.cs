using System.Text.Json;

namespace AlmondEngine;

internal static class NativeLibraryRoots
{
    internal static void Validate(IReadOnlyDictionary<string, string> cached, JsonElement libraries)
    {
        foreach (var variable in new[] { "RHINO_MCP_LIBRARY_DIR", "RHINO_MCP_CAPSULE_DIR", "RHINO_MCP_DRAWING_ASSET_DIR" })
            if (!cached.TryGetValue(variable, out var path) || string.IsNullOrWhiteSpace(path) ||
                !libraries.TryGetProperty(variable, out var expected) || expected.ValueKind != JsonValueKind.String ||
                string.IsNullOrWhiteSpace(expected.GetString()) || !SessionFiles.Same(path, expected.GetString()!))
                throw new IOException("The loaded native library directory differs from this worker: " + variable +
                    ". Restart Rhino with the selected library configuration.");
    }
}
