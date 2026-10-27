using System;
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
    // Integration fixture: requires the separate serialization test plugin.
    public static class RegistrySaveIntegrationTests
    {
        public static string RunAll(string directory)
        {
            Check(Rhino.PlugIns.PlugIn.Find(new Guid("fcf793c0-6937-4c4f-9d2b-c3c65f4df8e1")) != null,
                "Load the separate serialization fixture identity before this test.");
            Directory.CreateDirectory(directory);
            string path = Path.Combine(Path.GetFullPath(directory), "registry-save-" + Guid.NewGuid().ToString("N") + ".3dm");
            using (var seed = RhinoDoc.CreateHeadless(null))
            using (var options = new FileWriteOptions { SuppressAllInput = true, SuppressDialogBoxes = true })
                Check(seed.WriteFile(path, options), "Could not seed the disposable document.");
            bool alreadyOpen;
            using (var doc = RhinoDoc.Open(path, out alreadyOpen))
            {
                Check(doc != null && !alreadyOpen && !doc.IsHeadless, "Expected a new regular fixture document.");
                try
                {
                    doc.UndoRecordingEnabled = true;
                    var attributes = new ObjectAttributes { Name = "User named member" };
                    attributes.SetUserString("user-note", "keep this");
                    Guid objectId = doc.Objects.AddBrep(new BoundingBox(0, 0, 0, 10, 10, 10).ToBrep(), attributes);
                    var request = new JObject { ["action"] = "upsert", ["expected_model_path"] = path,
                        ["component_id"] = "saved-meaning", ["name"] = "Saved assembly",
                        ["scene_ids"] = new JArray("inside"), ["object_ids"] = new JArray(objectId.ToString("D")) };
                    var created = Success(ComponentRegistry.Handle(doc, request));
                    string groupId = (string)created["component"]["rhino_group_id"];
                    request["rhino_group_id"] = groupId;
                    request["scene_ids"] = new JArray("outside");
                    Success(ComponentRegistry.Handle(doc, request));
                    UndoRedo(doc, false);
                    Check(Scene(doc) == "inside", "Semantic Undo did not restore the original Scene.");
                    UndoRedo(doc, true);
                    Check(Scene(doc) == "outside", "Semantic Redo did not restore the changed Scene.");
                    UndoRedo(doc, false);
                    var saved = Success(DocumentSave.Handle(doc, new JObject { ["expected_model_path"] = path }));
                    Check((bool?)saved["saved"] == true && (bool?)saved["modified"] == false,
                        "Dedicated save did not confirm the actual saved state.");
                    using (var reopened = RhinoDoc.OpenHeadless(path))
                    {
                        Check(reopened != null, "Could not reopen the actual saved archive.");
                        reopened.UndoRecordingEnabled = true;
                        var component = Inspect(reopened);
                        Check((string)component["rhino_group_id"] == groupId && Scene(reopened) == "inside" &&
                            component["effective_object_ids"].Values<string>().SequenceEqual(new[] { objectId.ToString("D") }),
                            "Save/reopen lost the group identity, Scene or member identity.");
                        var member = reopened.Objects.FindId(objectId);
                        Check(member != null && member.Attributes.Name == "User named member" &&
                            member.Attributes.GetUserStrings().Count == 1 && member.Attributes.GetUserString("user-note") == "keep this",
                            "Save/reopen changed user attributes or added management attributes.");
                        Success(ComponentRegistry.Handle(reopened, new JObject { ["action"] = "unregister",
                            ["expected_model_path"] = path, ["component_id"] = "saved-meaning" }));
                        Check((string)Inspect(reopened)["registration_status"] == "unregistered", "Unregister failed after reopening.");
                        UndoRedo(reopened, false);
                        Check((string)Inspect(reopened)["registration_status"] == "registered", "Undo failed after reopening.");
                        UndoRedo(reopened, true);
                        Check((string)Inspect(reopened)["registration_status"] == "unregistered" &&
                            !reopened.Groups.FindId(new Guid(groupId)).IsDeleted && reopened.Objects.FindId(objectId) != null,
                            "Redo failed or semantic unregister removed physical geometry.");
                        reopened.Modified = false;
                    }
                }
                finally { doc.Modified = false; }
            }
            return "PASS Semantic Scene Undo/Redo, dedicated save, actual archive reopen and reopened unregister Undo/Redo preserve physical geometry and user attributes";
        }

        private static JObject Inspect(RhinoDoc doc) => (JObject)Success(ComponentRegistry.Handle(doc,
            new JObject { ["action"] = "inspect", ["expected_model_path"] = doc.Path, ["component_id"] = "saved-meaning" }))["component"];
        private static string Scene(RhinoDoc doc) => Inspect(doc)["scene_ids"].Values<string>().Single();
        private static JObject Success(JObject value) { Check((string)value["status"] == "success", value.ToString()); return value; }
        private static void Check(bool value, string message) { if (!value) throw new InvalidOperationException(message); }
        private static void UndoRedo(RhinoDoc doc, bool redo)
        {
            Check(!doc.UndoRecordingIsActive, "Unexpected active Undo record.");
            uint next = doc.NextUndoRecordSerialNumber;
            try { Check(redo ? doc.Redo() : doc.Undo(), "Native Undo/Redo failed."); }
            finally { if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == next) Check(doc.EndUndoRecord(next), "Could not close native Undo bookkeeping."); }
        }
    }
}
