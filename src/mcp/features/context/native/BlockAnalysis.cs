using System;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;

namespace RhinoAlmondBridge
{
    // Only compiled block queries are callable; no source, file output or ScriptExecutor.
    public static class BlockAnalysis
    {
        public const int MaxBytes = 262144;

        public static string Handle(JObject request)
        {
            return Analyze(RhinoDoc.ActiveDoc, request).ToString(Formatting.None);
        }

        public static JObject Analyze(RhinoDoc doc, JObject request)
        {
            if (doc == null) return Error("no_document", "No Rhino document is available.");
            try
            {
                if (request == null || request["mode"]?.Type != JTokenType.String ||
                    request["expected_model_path"]?.Type != JTokenType.String ||
                    !(request["options"] is JObject))
                    return Error("invalid_arguments", "mode, expected_model_path and an options object are required.");
                if (Encoding.UTF8.GetByteCount(request.ToString(Formatting.None)) > MaxBytes)
                    return Error("invalid_arguments", "Block analysis request exceeds 256 KiB; narrow the request.");
                string expected = (string)request["expected_model_path"];
                if (String.IsNullOrWhiteSpace(expected) || !Path.IsPathRooted(expected) ||
                    !String.Equals(expected, Path.GetFullPath(expected), StringComparison.OrdinalIgnoreCase))
                    return Error("invalid_arguments", "expected_model_path must be an absolute normalized model path.");
                if (String.IsNullOrWhiteSpace(doc.Path) ||
                    !String.Equals(Path.GetFullPath(doc.Path), expected, StringComparison.OrdinalIgnoreCase))
                    return Error("document_mismatch", "The active saved document differs from expected_model_path.");

                string mode = (string)request["mode"];
                var options = (JObject)request["options"];
                JObject data;
                switch (mode)
                {
                    case "outline": data = AlmondSpatial.Outline(doc, options); break;
                    case "resolve-block":
                        var path = options["path"] as JArray;
                        if (options.Properties().Any(p => p.Name != "path") || path == null ||
                            path.Count < 1 || path.Count > 65 || path.Any(t => t.Type != JTokenType.String))
                            return Error("invalid_arguments", "resolve-block requires only path with 1..65 GUID strings.");
                        data = AlmondSpatial.ResolveBlock(doc, path.Values<string>().Select(Guid.Parse).ToArray());
                        break;
                    default: return Error("invalid_arguments", "Use outline or resolve-block.");
                }
                var reply = new JObject
                {
                    ["status"] = "success",
                    ["mode"] = mode,
                    ["document"] = new JObject
                    {
                        ["runtime_serial_number"] = doc.RuntimeSerialNumber,
                        ["path"] = doc.Path,
                        ["units"] = doc.ModelUnitSystem.ToString(),
                        ["absolute_tolerance"] = doc.ModelAbsoluteTolerance
                    },
                    ["data"] = data
                };
                if (Encoding.UTF8.GetByteCount(reply.ToString(Formatting.None)) > MaxBytes)
                    return Error("block_analysis_too_large", "Block analysis response exceeds 256 KiB; narrow the scope or output budgets.");
                return reply;
            }
            catch (ArgumentException ex) { return Error("invalid_arguments", ex.Message); }
            catch (FormatException ex) { return Error("invalid_arguments", ex.Message); }
            catch (Exception ex) { return Error("block_analysis_failed", ex.Message); }
        }

        private static JObject Error(string code, string message)
        {
            return new JObject { ["status"] = "error", ["error_code"] = code, ["message"] = message };
        }
    }
}
