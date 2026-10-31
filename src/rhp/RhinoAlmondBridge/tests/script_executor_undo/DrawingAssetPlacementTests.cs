using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    public static class DrawingAssetPlacementTests
    {
        public static string RunAll(string directory)
        {
            var results = new List<string>();
            foreach (UnitSystem units in new[] { UnitSystem.Millimeters, UnitSystem.Meters })
            {
                string name = "linked 3DM placement, source refresh, Active layers and Undo in " + units;
                try
                {
                    string model = Path.Combine(directory, "placement-" + Guid.NewGuid().ToString("N") + ".3dm");
                    string asset = Path.Combine(directory, "source-" + Guid.NewGuid().ToString("N") + ".3dm");
                    using (var blank = RhinoDoc.CreateHeadless(null))
                    {
                        blank.AdjustModelUnitSystem(units, false);
                        Check(blank.WriteFile(model, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Model fixture save failed.");
                    }
                    WriteAsset(asset, 30);
                    bool alreadyOpen;
                    using (var doc = RhinoDoc.Open(model, out alreadyOpen))
                    {
                        try
                        {
                            Check(doc != null && !doc.IsHeadless && !alreadyOpen, "Use an isolated regular test document.");
                            doc.UndoRecordingEnabled = true;
                            var manager = new FurnitureAssetManager(directory, "ALMOND-DRAW::ASSETS", "DRAWING", "drawing_asset", "drawing asset", new[] { ".3dm" });
                            var request = new FurniturePlacementRequest { AssetId = "fixture", FilePath = asset, Name = "Free asset name",
                                Position = new[] { 1.0, 2.0, 0.0 }, Scale = Double.NaN,
                                Metadata = new JObject { ["sha256"] = Hash(asset) } };
                            var rejected = manager.Place(request);
                            Check(rejected.Status == "error" && !doc.Objects.GetObjectList(ObjectType.AnyObject).Any() && doc.InstanceDefinitions.Count == 0,
                                "Invalid placement changed geometry or definitions.");
                            request.Scale = 1;
                            request.Metadata.Remove("sha256");
                            var unregistered = manager.Place(request);
                            Check(unregistered.Status == "error" && unregistered.NeedsRefresh && unregistered.MutationState == "not_started" &&
                                !doc.Objects.GetObjectList(ObjectType.AnyObject).Any() && doc.InstanceDefinitions.Count == 0,
                                "A source without its registered SHA was placed or changed the document.");
                            request.Metadata["sha256"] = Hash(asset);
                            var first = manager.Place(request);
                            Check(first.Status == "success" && first.DefinitionCreated, first.Message);
                            var firstObject = doc.Objects.FindId(Guid.Parse(first.ObjectGuid));
                            var linked = ((InstanceObject)firstObject).InstanceDefinition;
                            Check(linked.UpdateType == InstanceDefinitionUpdateType.Linked && linked.LayerStyle == InstanceDefinitionLayerStyle.Active,
                                "A model asset was embedded or used reference layers.");
                            Check(Path.GetFullPath(linked.SourceArchive) == Path.GetFullPath(asset) && first.LinkType == "linked", "Linked source identity changed.");
                            Check(linked.GetObjects().All(o => !doc.Layers.FindIndex(o.Attributes.LayerIndex).IsReference), "Source layers became reference layers.");
                            Check(firstObject.Attributes.GetUserString("almond.metadata_scope") == "source_at_placement", "Metadata snapshot was not identified.");
                            double unit = RhinoMath.UnitScale(UnitSystem.Millimeters, units);
                            var firstBounds = firstObject.Geometry.GetBoundingBox(true);
                            Near(firstBounds.Min.X, 1 - 5 * unit); Near(firstBounds.Max.Y, 2 + 10 * unit); Near(firstBounds.Max.Z, 30 * unit);
                            Check(firstObject.Attributes.Name == "Free asset name", "Placement name changed.");
                            request.Position = new[] { 100.0, 200.0, 0.0 };
                            var second = manager.Place(request);
                            Check(second.Status == "success" && !second.DefinitionCreated && second.BlockDefinition == first.BlockDefinition, second.Message);
                            Undo(doc);
                            Check(doc.Objects.FindId(Guid.Parse(second.ObjectGuid)) == null && doc.Objects.FindId(Guid.Parse(first.ObjectGuid)) != null,
                                "Undo removed the wrong placement or retained the last one.");
                            File.Delete(asset);
                            WriteAsset(asset, 40);
                            int beforeStale = doc.Objects.Count;
                            var stale = manager.Place(request);
                            Check(stale.Status == "error" && stale.NeedsRefresh && stale.MutationState == "not_started" && doc.Objects.Count == beforeStale,
                                "Changed source was placed with stale metadata.");
                            request.Metadata["sha256"] = Hash(asset);
                            var changed = manager.Place(request);
                            Check(changed.Status == "success" && !changed.DefinitionCreated && changed.BlockDefinition == first.BlockDefinition,
                                "The same linked source produced a second unrelated definition.");
                            Check(changed.DefinitionRefreshed && changed.AffectedExistingInstances == 1, "Linked update impact was not reported.");
                            Near(doc.Objects.FindId(Guid.Parse(changed.ObjectGuid)).Geometry.GetBoundingBox(true).Max.Z, 40 * unit);
                            Near(doc.Objects.FindId(Guid.Parse(first.ObjectGuid)).Geometry.GetBoundingBox(true).Max.Z, 40 * unit);
                            // A user may detach a linked definition. A later asset placement must
                            // not relink that ordinary block merely because its name matches.
                            var detached = ((InstanceObject)doc.Objects.FindId(Guid.Parse(first.ObjectGuid))).InstanceDefinition;
                            Check(doc.InstanceDefinitions.DestroySourceArchive(detached, true), "Fixture could not detach definition.");
                            int beforeConflict = doc.Objects.Count;
                            var conflict = manager.Place(request);
                            Check(conflict.Status == "error" && conflict.MutationState == "not_started" && doc.Objects.Count == beforeConflict,
                                "A same-name ordinary block was reused or converted.");
                            Check(!doc.UndoRecordingIsActive, "Placement leaked an Undo record.");
                        }
                        finally { if (doc != null) doc.Modified = false; }
                    }
                    results.Add("PASS " + name);
                }
                catch (Exception error) { results.Add("FAIL " + name + ": " + error); }
            }
            string report = String.Join("\n", results);
            if (results.Any(line => line.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + results.Count + "/" + results.Count + " drawing asset placement cases.";
        }

        private static void WriteAsset(string path, double height)
        {
            using (var source = RhinoDoc.CreateHeadless(null))
            {
                source.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
                int layer = source.Layers.Add(new Layer { Name = "Asset material", Color = System.Drawing.Color.DarkGreen });
                source.Objects.AddBrep(new BoundingBox(-5, -10, 0, 5, 10, height).ToBrep(), new ObjectAttributes { LayerIndex = layer });
                Check(source.WriteFile(path, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Asset save failed.");
            }
        }
        private static string Hash(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var algorithm = SHA256.Create()) return BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "");
        }
        private static void Undo(RhinoDoc doc)
        {
            Check(!doc.UndoRecordingIsActive, "Undo record already active.");
            uint next = doc.NextUndoRecordSerialNumber;
            try { Check(doc.Undo(), "Undo failed."); }
            finally { if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == next) Check(doc.EndUndoRecord(next), "Undo record did not close."); }
        }
        private static void Near(double actual, double expected) => Check(Math.Abs(actual - expected) < 1e-7, "Unexpected placement bound: " + actual + " vs " + expected);
        private static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
