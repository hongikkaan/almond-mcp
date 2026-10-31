using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    // The panel submits an asset ID, never a web-provided file path. Resolve it
    // again from the current canonical library before the common placer runs.
    internal static class LibraryAssetSource
    {
        internal static JObject Read(string libraryRoot, string assetId)
        {
            if (assetId == null || !Regex.IsMatch(assetId, "^[A-Za-z0-9._-]{1,100}$") || assetId == "." || assetId == "..")
                throw new ArgumentException("Invalid library asset ID.");
            string root = Path.GetFullPath(libraryRoot).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string manifestPath = Path.Combine(root, "manifest.json");
            if (!File.Exists(manifestPath))
                throw new InvalidDataException("The installed model library is unavailable. Register a 3DM asset before placement.");
            if ((File.GetAttributes(manifestPath) & FileAttributes.ReparsePoint) != 0)
                throw new InvalidDataException("The registered model manifest cannot be a symbolic link.");
            var manifest = JObject.Parse(File.ReadAllText(manifestPath, Encoding.UTF8));
            var matches = (manifest["assets"] as JArray ?? new JArray()).OfType<JObject>()
                .Where(asset => (string)asset["asset_id"] == assetId).ToArray();
            if (matches.Length != 1)
                throw new InvalidDataException("This model has no unique registered 3DM. Convert and register its source with prepare_drawing_asset before placement.");
            var record = (JObject)matches[0].DeepClone();
            string relative = (string)record["file"];
            if (String.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative))
                throw new InvalidDataException("The registered model path must be relative to its library.");
            string source = Path.GetFullPath(Path.Combine(root, relative));
            if (!source.StartsWith(root, StringComparison.OrdinalIgnoreCase) ||
                !String.Equals(Path.GetExtension(source), ".3dm", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Model assets must be registered 3DM files inside their library. Convert legacy formats before placement.");
            if (!File.Exists(source)) throw new FileNotFoundException("The registered 3DM source is missing.", source);
            for (string path = source; path != null && path.Length >= root.TrimEnd(Path.DirectorySeparatorChar).Length; path = Path.GetDirectoryName(path))
                if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("Linked asset sources must resolve within the registered library without junctions or symbolic links.");
            record["_resolved_file"] = source;
            return record;
        }
    }
}
