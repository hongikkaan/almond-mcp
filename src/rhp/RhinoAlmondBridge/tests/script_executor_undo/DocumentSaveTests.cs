using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.FileIO;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    /// <summary>Run in a separate empty Rhino process, after the launch command returns.</summary>
    public static class DocumentSaveTests
    {
        public static string RunAll(string directory)
        {
            Directory.CreateDirectory(directory);
            var lines = new List<string>();
            string path = Path.Combine(Path.GetFullPath(directory), "save-" + Guid.NewGuid().ToString("N") + ".3dm");
            using (var seed = RhinoDoc.CreateHeadless(null))
            using (var options = new FileWriteOptions { SuppressDialogBoxes = true, SuppressAllInput = true })
                Check(seed.WriteFile(path, options), "Could not seed a disposable model.");
            bool alreadyOpen;
            using (var doc = RhinoDoc.Open(path, out alreadyOpen))
            {
                Check(doc != null && !alreadyOpen && !doc.IsHeadless, "Expected a fresh foreground fixture.");
                try
                {
                    var request = new JObject { ["expected_model_path"] = path };
                    byte[] original = File.ReadAllBytes(path);
                    var mismatch = DocumentSave.Handle(doc, new JObject { ["expected_model_path"] = path + ".other.3dm" });
                    Check((string)mismatch["error_code"] == "document_mismatch" && (bool)mismatch["saved"] == false,
                        "A mismatched binding was not rejected.");
                    Check(original.SequenceEqual(File.ReadAllBytes(path)), "A rejected save changed the file.");
                    lines.Add("PASS Given a mismatched binding, saving rejects without a file write");

                    var attributes = File.GetAttributes(path);
                    try
                    {
                        File.SetAttributes(path, attributes | FileAttributes.ReadOnly);
                        var readOnly = DocumentSave.Handle(doc, request);
                        Check((string)readOnly["error_code"] == "read_only_file" && (bool)readOnly["saved"] == false,
                            "A read-only file was not rejected before input.");
                    }
                    finally { File.SetAttributes(path, attributes); }
                    lines.Add("PASS Given a read-only model, saving rejects without prompting");

                    uint record = doc.BeginUndoRecord("Unstable save fixture");
                    Check(record != 0, "Could not open the fixture Undo record.");
                    try
                    {
                        var unstable = DocumentSave.Handle(doc, request);
                        Check((string)unstable["error_code"] == "editing_context_unstable" && (bool)unstable["saved"] == false,
                            "An unconfirmed editing context was not rejected: " + unstable);
                        Check(original.SequenceEqual(File.ReadAllBytes(path)), "An unstable save changed the file.");
                    }
                    finally { doc.EndUndoRecord(record); }
                    lines.Add("PASS Given an unstable editing context, saving rejects without changing the file");

                    int layer = doc.Layers.Add(new Layer { Name = "Saved layer" });
                    var objectAttributes = new ObjectAttributes { Name = "Saved object", LayerIndex = layer };
                    objectAttributes.SetUserString("user-note", "preserve this");
                    Guid id = doc.Objects.AddLine(Point3d.Origin, new Point3d(10, 20, 30), objectAttributes);
                    Check(id != Guid.Empty, "Could not add the fixture object.");
                    var view = doc.Views.ActiveView;
                    Check(view != null, "Expected a foreground viewport.");
                    Check(doc.NamedViews.Add("Saved view", view.MainViewport.Id) >= 0, "Could not add a named view.");
                    var editing = EditingContext.Observe(doc);
                    Check((bool?)editing["stable"] == true, "Disposable fixture has no confirmed stable model context: " + editing);
                    var saved = DocumentSave.Handle(doc, request);
                    Check((string)saved["status"] == "success" && (bool)saved["saved"] && !(bool)saved["modified"],
                        "Noninteractive save was not confirmed: " + saved);
                    Check(String.Equals(doc.Path, path, StringComparison.OrdinalIgnoreCase), "Save changed the document path.");
                    using (var disk = File3dm.Read(path))
                    {
                        var item = disk == null ? null : disk.Objects.FirstOrDefault(value => value.Attributes.ObjectId == id);
                        Check(item != null, "Saved geometry is absent from disk.");
                        Check(item.Attributes.Name == "Saved object" && item.Attributes.GetUserString("user-note") == "preserve this",
                            "Save lost user object attributes.");
                        Check(disk.AllLayers.Any(value => value.Name == "Saved layer") &&
                            disk.NamedViews.Any(value => value.Name == "Saved view"), "Save lost document layers or named views.");
                    }
                    Check(!doc.UndoRecordingIsActive && !doc.UndoActive && !doc.RedoActive, "Save left an Undo operation active.");
                    lines.Add("PASS Given a stable bound model, saving preserves geometry, user attributes, layers and named views and reports actual modified state");
                }
                finally { doc.Modified = false; }
            }
            return String.Join(System.Environment.NewLine, lines);
        }

        private static void Check(bool value, string message)
        {
            if (!value) throw new InvalidOperationException(message);
        }
    }
}
