using System;
using System.IO;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.FileIO;

namespace RhinoAlmondBridge
{
    /// <summary>Save only the bound, existing document without entering a Rhino command.</summary>
    public static class DocumentSave
    {
        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                if (doc == null || RhinoDoc.ActiveDoc == null ||
                    doc.RuntimeSerialNumber != RhinoDoc.ActiveDoc.RuntimeSerialNumber)
                    return Reject("no_active_document", "The bound document is not active.");
                var expected = request["expected_model_path"];
                if (expected == null || expected.Type != JTokenType.String ||
                    String.IsNullOrWhiteSpace((string)expected) || String.IsNullOrWhiteSpace(doc.Path))
                    return Reject("unsaved_document", "An existing bound .3dm file is required.");
                string path = Path.GetFullPath(doc.Path);
                if (!Path.IsPathRooted((string)expected) ||
                    !String.Equals(path, Path.GetFullPath((string)expected), StringComparison.OrdinalIgnoreCase))
                    return Reject("document_mismatch", "The active document differs from the bound model.");
                if (!String.Equals(Path.GetExtension(path), ".3dm", StringComparison.OrdinalIgnoreCase) || !File.Exists(path))
                    return Reject("unsaved_document", "Save the document to a .3dm file before connecting.");
                if ((File.GetAttributes(path) & FileAttributes.ReadOnly) != 0)
                    return Reject("read_only_file", "The bound model file is read-only.");
                JObject editing = EditingContext.Observe(doc);
                if (editing["stable"]?.Type != JTokenType.Boolean || (bool)editing["stable"] != true)
                {
                    var reply = Reject("editing_context_unstable", "Finish group/block editing before saving the bound document.");
                    reply["editing"] = editing;
                    return reply;
                }
                using (var options = new FileWriteOptions
                {
                    SuppressDialogBoxes = true,
                    SuppressAllInput = true,
                    UpdateDocumentPath = true,
                    WriteSelectedObjectsOnly = false,
                    WriteGeometryOnly = false,
                    WriteUserData = true,
                    IncludeHistory = true
                })
                {
                    started = true;
                    bool saved = doc.WriteFile(path, options);
                    if (!saved)
                        return new JObject { ["status"] = "error", ["error_code"] = "save_failed",
                            ["message"] = "Rhino did not confirm a successful file write.",
                            ["saved"] = false, ["modified"] = doc.Modified };
                }
                return new JObject { ["status"] = "success", ["saved"] = true, ["modified"] = doc.Modified };
            }
            catch (Exception error)
            {
                return new JObject { ["status"] = "error", ["error_code"] = started ? "save_result_unconfirmed" : "save_not_started",
                    ["message"] = error.Message, ["saved"] = started ? JValue.CreateNull() : new JValue(false),
                    ["requires_reconciliation"] = started };
            }
        }

        private static JObject Reject(string code, string message)
        {
            return new JObject { ["status"] = "error", ["error_code"] = code,
                ["message"] = message, ["saved"] = false };
        }
    }
}
