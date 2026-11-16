using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json.Linq;
using Rhino;

namespace RhinoAlmondBridge
{
    internal static class WorksessionObservation
    {
        public static JToken Read(RhinoDoc doc, JArray warnings)
        {
            try
            {
                var worksession = doc.Worksession;
                if (worksession?.Document?.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                    throw new InvalidOperationException("Rhino did not return the current document's Worksession.");
                var activePath = doc.Path;
                var active = String.IsNullOrEmpty(activePath) ? null : FullPath(activePath);
                var serial = worksession.RuntimeSerialNumber;
                var modelCount = worksession.ModelCount;
                var paths = worksession.ModelPaths;

                // RhinoCommon returns 0 or [] when its native reads fail. Treat an
                // empty response as known only when the other native evidence agrees.
                if (serial == 0 && modelCount == 0 && paths?.Length == 0)
                    return new JArray();
                // ModelCount includes the current model even if unsaved; ModelPaths doesn't.
                if (paths == null || modelCount < 1 || paths.Length != modelCount - (active == null ? 1 : 0))
                    throw new InvalidOperationException("Rhino returned an incomplete Worksession model list.");

                var result = new JArray();
                var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                bool foundActive = active == null;
                foreach (var path in paths)
                {
                    var normalized = FullPath(path);
                    if (String.Equals(active, normalized, StringComparison.OrdinalIgnoreCase))
                    {
                        foundActive = true;
                        continue;
                    }
                    if (seen.Add(normalized))
                        result.Add(new JObject { ["file_name"] = Path.GetFileName(normalized), ["file_path"] = normalized });
                }
                if (!foundActive)
                    throw new InvalidOperationException("Rhino's Worksession model list omitted its active model.");
                return result;
            }
            catch (Exception ex)
            {
                warnings.Add("worksession_files: " + ex.Message);
                return JValue.CreateNull();
            }
        }

        private static string FullPath(string path)
        {
            if (String.IsNullOrWhiteSpace(path) || !Path.IsPathFullyQualified(path))
                throw new InvalidOperationException("Rhino returned an invalid Worksession model path.");
            var normalized = Path.GetFullPath(path);
            if (String.IsNullOrEmpty(Path.GetFileName(normalized)))
                throw new InvalidOperationException("Rhino returned a Worksession path without a file name.");
            return normalized;
        }
    }
}
