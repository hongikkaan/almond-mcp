using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    public static class ComponentOperationTests
    {
        public static string RunAll(string directory)
        {
            var lines = new List<string>();
            Run(lines, "Intersection broadphase and volume preserve the document", doc =>
            {
                Guid a = Box(doc, 0), b = Box(doc, 5), far = Box(doc, 100);
                var before = State(doc);
                var result = Success(ComponentOperations.CheckIntersectVolumes(doc, new[] { a, b, a, far }));
                Check((int)result["object_count"] == 3 && (int)result["candidate_pair_count"] == 1 &&
                    (int)result["bbox_pruned_pair_count"] == 2 && (int)result["evaluated_pairs"] == 1, "Incorrect candidate scope: " + result);
                Check((bool)result["complete"] && (bool)result["has_positive_overlap"] &&
                    Near((double)result["pairs"][0]["overlap"]["volume_model_units3"], 500), "Overlap volume is not 500: " + result);
                Unchanged(before, doc);
            });
            Run(lines, "Containment reuses the pair probe's positive-volume evidence", doc =>
            {
                var outer = Box(doc, 0);
                var inner = doc.Objects.AddBrep(new BoundingBox(2, 2, 2, 4, 4, 4).ToBrep());
                var before = State(doc);
                var result = Success(ComponentOperations.CheckIntersectVolumes(doc, new[] { outer, inner }));
                Check((bool)result["complete"] && (bool)result["has_positive_overlap"] &&
                    Near((double)result["pairs"][0]["overlap"]["volume_model_units3"], 8), "Contained volume was lost: " + result);
                Unchanged(before, doc);
            });
            Run(lines, "Unsupported block and TextDot do not become a complete no-overlap result", doc =>
            {
                var a = Box(doc, 0);
                var dot = doc.Objects.AddTextDot("annotation", new Point3d(100, 0, 0));
                int definition = doc.InstanceDefinitions.Add("Volume test block", "", Point3d.Origin,
                    new GeometryBase[] { new BoundingBox(0, 0, 0, 10, 10, 10).ToBrep() }, new[] { new ObjectAttributes() });
                Check(definition >= 0, "Block fixture failed.");
                var block = doc.Objects.AddInstanceObject(definition, Transform.Translation(200, 0, 0));
                var before = State(doc);
                var result = Success(ComponentOperations.CheckIntersectVolumes(doc, new[] { a, dot, block }));
                Check(!(bool)result["complete"] && result["has_positive_overlap"].Type == JTokenType.Null &&
                    ((JArray)result["unsupported_objects"]).Count == 2, "Unsupported geometry was treated as zero volume: " + result);
                Unchanged(before, doc);
            });
            Run(lines, "Pair budget reports omitted candidates and retained positive evidence", doc =>
            {
                var ids = Enumerable.Range(0, 4).Select(i => Box(doc, i)).ToArray();
                var before = State(doc);
                var result = Success(ComponentOperations.CheckIntersectVolumes(doc, ids, 2));
                Check((int)result["candidate_pair_count"] == 6 && (int)result["evaluated_pairs"] == 2 &&
                    (bool)result["truncated"] && !(bool)result["complete"] && (bool)result["has_positive_overlap"],
                    "Pair budget silently omitted work: " + result);
                Unchanged(before, doc);
            });
            Run(lines, "Disjoint bounds avoid kernel work; stale IDs and headless focus reject cleanly", doc =>
            {
                Guid a = Box(doc, 0), b = Box(doc, 100);
                var before = State(doc);
                var result = Success(ComponentOperations.CheckIntersectVolumes(doc, new[] { a, b }));
                Check((bool)result["complete"] && !(bool)result["has_positive_overlap"] &&
                    (int)result["evaluated_pairs"] == 0 && (int)result["bbox_pruned_pair_count"] == 1, "Disjoint scope was not proven: " + result);
                Rejected(ComponentOperations.CheckIntersectVolumes(doc, new[] { a, Guid.NewGuid() }));
                Rejected(ComponentOperations.CheckIntersectVolumes(doc, new[] { a, b }, 65));
                Rejected(ComponentOperations.IsolateAndZoomSelected(doc, new[] { a }));
                Unchanged(before, doc);
            });
            Run(lines, "Existing outline discovers group and nested block TextDots without edits", doc =>
            {
                var groupDot = doc.Objects.AddTextDot("group note", new Point3d(10, 20, 30));
                doc.Objects.AddTextDot("outside note", new Point3d(1000, 0, 0));
                int definition = doc.InstanceDefinitions.Add("Note test block", "", Point3d.Origin,
                    new GeometryBase[] { new TextDot("block note", new Point3d(1, 2, 3)) }, new[] { new ObjectAttributes() });
                Check(definition >= 0, "Note block fixture failed.");
                var instance = doc.Objects.AddInstanceObject(definition, Transform.Translation(100, 200, 300));
                int group = doc.Groups.Add("Annotated group", new[] { groupDot, instance });
                Check(group >= 0, "Group fixture failed.");
                var ids = doc.Groups.GroupMembers(group).Select(o => o.Id.ToString("D"));
                var before = State(doc);
                var outline = AlmondSpatial.Outline(doc, new JObject { ["ids"] = new JArray(ids),
                    ["annotations"] = true, ["include_geometry"] = false, ["max_items"] = 30 });
                var records = (JArray)outline["records"];
                var notes = records.Where(r => (string)r["kind"] == "note").ToArray();
                Check(notes.Length == 2 && notes.Any(n => (string)n["text"] == "group note") &&
                    notes.All(n => (string)n["text"] != "outside note"), "Group scope leaked unrelated annotations: " + outline);
                var blockNote = notes.Single(n => (string)n["text"] == "block note");
                var occurrence = records.Single(r => (string)r["kind"] == "occurrence" && (string)r["id"] == instance.ToString("D"));
                var matrix = occurrence["definition_to_world"].Values<double>().ToArray();
                var world = Transform.Identity;
                for (int row = 0; row < 4; row++) for (int column = 0; column < 4; column++) world[row, column] = matrix[row * 4 + column];
                var local = blockNote["point_local"].Values<double>().ToArray();
                var point = new Point3d(local[0], local[1], local[2]);
                point.Transform(world);
                Check(point.DistanceTo(new Point3d(101, 202, 303)) < 1e-9, "Nested TextDot world position is incorrect.");
                Check(!(bool)outline["truncated"] && !(bool)outline["depth_limited"], "Small outline was unexpectedly incomplete.");
                Unchanged(before, doc);
            });
            RunView(lines, directory, doc =>
            {
                Guid target = Box(doc, 1000), other = Box(doc, -1000);
                Success(ComponentRegistry.Handle(doc, new JObject {
                    ["action"] = "upsert", ["expected_model_path"] = doc.Path,
                    ["component_id"] = "focus-leaf", ["name"] = "Leaf", ["scene_ids"] = new JArray("scene"),
                    ["object_ids"] = new JArray(target.ToString("D"))
                }));
                Guid rootDirect = Box(doc, 2000);
                int rootGroup = doc.Groups.Add("Assembly", new[] { target, rootDirect });
                Success(ComponentRegistry.Handle(doc, new JObject {
                    ["action"] = "upsert", ["expected_model_path"] = doc.Path,
                    ["component_id"] = "focus-root", ["name"] = "Assembly", ["scene_ids"] = new JArray("scene"),
                    ["object_ids"] = new JArray(rootDirect.ToString("D")), ["child_component_ids"] = new JArray("focus-leaf"),
                    ["rhino_group_id"] = doc.Groups[rootGroup].Id.ToString("D")
                }));
                var request = new JObject { ["action"] = "intersections", ["expected_model_path"] = doc.Path,
                    ["component_ids"] = new JArray("focus-root", "focus-leaf") };
                var hidden = doc.Objects.AddPoint(new Point3d(5000, 0, 0));
                var locked = doc.Objects.AddPoint(new Point3d(-5000, 0, 0));
                Check(doc.Objects.Hide(hidden, true) && doc.Objects.Lock(locked, true), "Visibility fixtures failed.");
                doc.Objects.FindId(other).Select(true);
                var before = State(doc);
                Rejected(ComponentOperations.IsolateAndZoomSelected(doc, new[] { hidden }));
                Rejected(ComponentOperations.IsolateAndZoomSelected(doc, new[] { locked }));
                Rejected(ComponentOperations.IsolateAndZoomSelected(doc, new[] { Guid.NewGuid() }));
                var overlap = Success(ComponentOperations.Handle(doc, request));
                Check((int)overlap["object_count"] == 2 && (bool)overlap["complete"] && !(bool)overlap["has_positive_overlap"],
                    "Component dispatch did not resolve and deduplicate the live descendant set.");
                request["expected_model_path"] = doc.Path + ".other";
                Rejected(ComponentOperations.Handle(doc, request));
                request["expected_model_path"] = doc.Path;
                request["max_pairs"] = "64";
                Rejected(ComponentOperations.Handle(doc, request));
                request.Remove("max_pairs");
                Unchanged(before, doc);
                var geometries = doc.Objects.GetObjectList(ObjectType.AnyObject).ToDictionary(o => o.Id, o => o.Geometry.DataCRC(0));
                Point3d cameraBefore=doc.Views.ActiveView.ActiveViewport.CameraLocation;
                Point3d targetBefore=doc.Views.ActiveView.ActiveViewport.CameraTarget;
                request["action"] = "focus";
                var result = Success(ComponentOperations.Handle(doc, request));
                Check((bool)result["isolated"] && (bool)result["zoom_selected"] && ((JArray)result["selected_ids"]).Count == 2, "Incomplete focus acknowledgement.");
                Check(doc.Objects.FindId(rootDirect).IsSelected(false) != 0, "Parent direct member was not focused.");
                Check(doc.Objects.FindId(target).IsSelected(false) != 0 && !doc.Objects.FindId(target).IsHidden &&
                    doc.Objects.FindId(other).IsHidden && doc.Objects.FindId(hidden).IsHidden &&
                    doc.Objects.FindId(locked).IsLocked && !doc.Objects.FindId(locked).IsHidden, "Isolate did not preserve Rhino's locked/previously hidden behavior.");
                var focused=doc.Views.ActiveView;
                Check(cameraBefore.DistanceTo(focused.ActiveViewport.CameraLocation)>1e-6||targetBefore.DistanceTo(focused.ActiveViewport.CameraTarget)>1e-6,
                    "Focus did not move the camera or its target.");
                CheckFramed(focused,doc.Objects.FindId(target).Geometry.GetBoundingBox(true));
                CheckFramed(focused,doc.Objects.FindId(rootDirect).Geometry.GetBoundingBox(true));
                Check(geometries.All(pair => doc.Objects.FindId(pair.Key)?.Geometry.DataCRC(0) == pair.Value), "Focus changed geometry.");
                Check(RhinoApp.RunScript("_Unisolate", false), "Native Unisolate failed.");
                Check(!doc.Objects.FindId(other).IsHidden && doc.Objects.FindId(hidden).IsHidden && doc.Objects.FindId(locked).IsLocked,
                    "Unisolate lost earlier hidden/locked state.");
            });
            string report = String.Join("\n", lines);
            if (lines.Any(line => line.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + lines.Count + "/" + lines.Count + " Component operation cases.";
        }

        private static Guid Box(RhinoDoc doc, double x) => doc.Objects.AddBrep(new BoundingBox(x, 0, 0, x + 10, 10, 10).ToBrep());
        private static void CheckFramed(Rhino.Display.RhinoView view,BoundingBox bounds)
        {
            // IsVisible returned false in the disposable hidden process even when
            // native Zoom Selected and captured pixels showed both targets. Check
            // every actual box corner in clip and client coordinates instead.
            var rectangle=view.ClientRectangle;var viewport=view.ActiveViewport;
            Check(rectangle.Width>0&&rectangle.Height>0,"Focus viewport has no drawable area.");
            var worldToClip=viewport.GetTransform(CoordinateSystem.World,CoordinateSystem.Clip);
            foreach(Point3d corner in bounds.GetCorners())
            {
                var clip=corner;clip.Transform(worldToClip);var client=viewport.WorldToClient(corner);
                Check(clip.IsValid&&Math.Abs(clip.X)<=1.000001&&Math.Abs(clip.Y)<=1.000001&&Math.Abs(clip.Z)<=1.000001,
                    "Target corner is outside the active view frustum: "+clip);
                Check(client.X>=-1e-6&&client.X<=rectangle.Width+1e-6&&client.Y>=-1e-6&&client.Y<=rectangle.Height+1e-6,
                    "Target corner is outside the active viewport pixels: "+client);
            }
        }
        private static void Run(List<string> lines, string name, Action<RhinoDoc> test)
        {
            using (var doc = RhinoDoc.CreateHeadless(null))
            {
                doc.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
                doc.ModelAbsoluteTolerance = 0.001;
                doc.UndoRecordingEnabled = true;
                try { test(doc); lines.Add("PASS " + name); }
                catch (Exception error) { lines.Add("FAIL " + name + ": " + error); }
            }
        }

        private static void RunView(List<string> lines, string directory, Action<RhinoDoc> test)
        {
            const string name = "Isolate and ZoomSelected preflight, native restore and geometry preservation";
            string path = Path.Combine(directory, "component-focus-" + Guid.NewGuid().ToString("N") + ".3dm");
            try
            {
                using (var fixture = RhinoDoc.CreateHeadless(null))
                {
                    fixture.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
                    Check(fixture.WriteFile(path, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Focus fixture save failed.");
                }
                bool alreadyOpen;
                using (var doc = RhinoDoc.Open(path, out alreadyOpen))
                {
                    Check(doc != null && !alreadyOpen && !doc.IsHeadless, "Focus tests need a fresh regular document in the isolated test process.");
                    doc.UndoRecordingEnabled = true;
                    try { test(doc); }
                    finally { doc.Modified = false; }
                }
                lines.Add("PASS " + name);
            }
            catch (Exception error) { lines.Add("FAIL " + name + ": " + error); }
        }

        private static JObject State(RhinoDoc doc)
        {
            var settings = new ObjectEnumeratorSettings { NormalObjects = true, HiddenObjects = true,
                LockedObjects = true, ReferenceObjects = true, IdefObjects = true, DeletedObjects = false };
            var objects = new JArray(doc.Objects.GetObjectList(settings).OrderBy(o => o.Id).Select(o => new JObject
            {
                ["id"] = o.Id.ToString("D"), ["geometry_crc"] = o.Geometry?.DataCRC(0) ?? 0u,
                ["attributes"] = o.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions { WriteUserData = true }),
                ["selection"] = o.IsSelected(false)
            }));
            var viewport = doc.Views.ActiveView?.ActiveViewport;
            return new JObject { ["objects"] = objects, ["modified"] = doc.Modified,
                ["undo_recording"] = doc.UndoRecordingIsActive, ["undo_active"] = doc.UndoActive, ["redo_active"] = doc.RedoActive,
                ["current_record"] = doc.CurrentUndoRecordSerialNumber, ["next_record"] = doc.NextUndoRecordSerialNumber,
                ["layers"] = new JArray(doc.Layers.OrderBy(l => l.Id).Select(l => l.DataCRC(0))),
                ["camera_location"] = viewport == null ? null : new JArray(viewport.CameraLocation.X, viewport.CameraLocation.Y, viewport.CameraLocation.Z),
                ["camera_target"] = viewport == null ? null : new JArray(viewport.CameraTarget.X, viewport.CameraTarget.Y, viewport.CameraTarget.Z) };
        }
        private static JObject Success(JObject result) { Check((string)result["status"] == "success", result.ToString()); return result; }
        private static void Rejected(JObject result) => Check((string)result["status"] == "error" && (bool?)result["mutation_applied"] == false, result.ToString());
        private static void Unchanged(JObject before, RhinoDoc doc) => Check(JToken.DeepEquals(before, State(doc)), "Operation changed the document state.");
        private static bool Near(double a, double b) => Math.Abs(a - b) < Math.Max(1e-6, Math.Abs(b) * 1e-6);
        private static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
