using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    // Linked-source native tests. Invoke from a modeless Rhino UI callback.
    // RunAll owns only disposable headless documents; RunViewport uses a document
    // supplied by the caller and must be coordinated with its owner.
    public static partial class ObservationTests
    {
        public static string RunAll()
        {
            var lines = new List<string>();

            Run(lines, "Given a headless model, editor observation confirms a stable model without mutation", doc =>
            {
                var before = DocumentState(doc);
                var reply = EditingContext.Observe(doc);
                Check((string)reply["mode"] == "model" && (bool)reply["stable"] && reply["target"].Type == JTokenType.Null,
                    "A stable model was not established from actual editor-provider state: " + reply);
                Unchanged(before, DocumentState(doc), "Editor baseline");
                uint record = doc.BeginUndoRecord("transient editor observation fixture");
                try
                {
                    reply = EditingContext.Observe(doc);
                    Check((string)reply["mode"] == "unknown" && !(bool)reply["stable"],
                        "An active document edit was mistaken for a stable model: " + reply);
                }
                finally { doc.EndUndoRecord(record); }
            });

            Run(lines, "Given nested groups, default selection returns the top group and explicit depth expands only that branch", doc =>
            {
                var ids = Enumerable.Range(0, 3).Select(i => doc.Objects.AddPoint(new Point3d(i, 0, 0))).ToArray();
                int child = doc.Groups.Add("nested child", ids.Take(2));
                int parent = doc.Groups.Add("top group", ids);
                Check(child >= 0 && parent >= 0, "Could not create nested group fixture.");
                foreach (var id in ids) doc.Objects.Select(id, true);
                var before = DocumentState(doc);
                var raw = DocumentObservation.GetContext(doc, 50, new[] { "selection" });
                Check((int)raw["selection"]["total"] == 3 &&
                    new HashSet<string>(raw["selection"]["objects"].Select(row => (string)row["id"])).SetEquals(ids.Select(id => id.ToString())),
                    "Internal selection references lost the member object GUIDs of a fully selected group.");
                var summary = DocumentObservation.GetContext(doc, 50, new[] { "selection" }, selectionEntities: true);
                Check((int)summary["selection"]["total"] == 1 && (int)summary["selection"]["selected_object_count"] == 3,
                    "Group selection was expanded into leaf objects by default.");
                var rows = (JArray)summary["selection"]["objects"];
                Check(rows.Count == 1 && (string)rows[0]["id"] == doc.Groups[parent].Id.ToString() &&
                    (string)rows[0]["type"] == "Group", "The top group's persistent identity is missing.");
                var details = DocumentObservation.GetContext(doc, 50, new[] { "selection" }, true, 2, selectionEntities: true);
                rows = (JArray)details["selection"]["objects"];
                Check(rows.Count == 3 && rows.Count(row => (string)row["type"] == "Group") == 2 &&
                    (bool)details["selection"]["depth_limited"], "Explicit group depth expanded the wrong scope.");
                Unchanged(before, DocumentState(doc), "Grouped selection observation");
                doc.Objects.UnselectAll();
                doc.Objects.Select(ids[0], true); doc.Objects.Select(ids[2], true);
                before = DocumentState(doc);
                var partial = DocumentObservation.GetContext(doc, 50, new[] { "selection" }, selectionEntities: true);
                Check((int)partial["selection"]["total"] == 2 &&
                    ((JArray)partial["selection"]["objects"]).All(row => (string)row["type"] != "Group"),
                    "A partial group selection was fabricated into a complete group.");
                Unchanged(before, DocumentState(doc), "Partial grouped selection observation");
                int definition = doc.InstanceDefinitions.Add("selected block", "", Point3d.Origin,
                    new GeometryBase[] { new Rhino.Geometry.Point(Point3d.Origin) }, new[] { new ObjectAttributes() });
                var instance = doc.Objects.AddInstanceObject(definition, Transform.Identity);
                doc.Objects.UnselectAll(); doc.Objects.Select(instance, true);
                before = DocumentState(doc);
                var block = DocumentObservation.GetContext(doc, 50, new[] { "selection" }, selectionEntities: true);
                Check((string)block["selection"]["objects"][0]["type"] == "InstanceReference" &&
                    (string)block["selection"]["objects"][0]["name"] == "selected block",
                    "Block summaries changed the existing Rhino object type or lost the definition name.");
                Unchanged(before, DocumentState(doc), "Shallow block selection observation");
            });

            Run(lines, "Given large named geometry, default outline is bounded summary and explicit fields retain detailed probes", doc =>
            {
                var ids = Enumerable.Range(0, 100).Select(i => doc.Objects.AddPoint(new Point3d(i, 0, 0),
                    new ObjectAttributes { Name = new String('가', 400) + i })).ToArray();
                var before = DocumentState(doc);
                var request = new JObject { ["ids"] = new JArray(ids.Select(id => id.ToString())), ["max_bytes"] = 2048 };
                var summary = AlmondSpatial.Outline(doc, request);
                Check((string)summary["records"][0]["kind"] == "summary" &&
                    (int)summary["records"][0]["root_count"] == 100 &&
                    System.Text.Encoding.UTF8.GetByteCount(summary.ToString(Formatting.None)) < 2048 && (bool)summary["records"][0]["names_truncated"],
                    "Large default outline did not return a compact, honest summary.");
                request["ids"] = new JArray(ids[0].ToString());
                request["field_groups"] = new JArray("objects");
                var detailed = AlmondSpatial.Outline(doc, request);
                Check((string)detailed["records"][0]["kind"] == "occurrence" &&
                    detailed["records"][0]["geometry_to_world"] == null,
                    "Explicit object observations unexpectedly include transforms or omit the requested object.");
                Unchanged(before, DocumentState(doc), "Bounded geometry observation");
            });

            Run(lines, "Given explicit legacy details, summaries cannot replace occurrence or add unrequested geometry", doc =>
            {
                var point = doc.Objects.AddPoint(Point3d.Origin);
                var legacy = AlmondSpatial.Outline(doc, new JObject { ["ids"] = new JArray(point.ToString()),
                    ["include_geometry"] = true, ["annotations"] = false, ["max_items"] = 1 });
                Check(((JArray)legacy["records"]).Count == 1 && (string)legacy["records"][0]["kind"] == "occurrence",
                    "A new summary consumed the only slot in an explicit legacy detail query.");
            });

            Run(lines, "Given only a legacy annotations flag, leaf geometry remains excluded by default", doc =>
            {
                var point = doc.Objects.AddPoint(Point3d.Origin);
                var notesOnly = AlmondSpatial.Outline(doc, new JObject { ["ids"] = new JArray(point.ToString()), ["annotations"] = false });
                Check(!notesOnly["records"].HasValues, "Omitting include_geometry no longer preserves the legacy false default.");
            });

            Run(lines, "Given reused nested blocks, annotations-only work is bounded even when output definitions repeat", doc =>
            {
                int definition = doc.InstanceDefinitions.Add("notes leaf", "", Point3d.Origin,
                    new GeometryBase[] { new TextDot("leaf note", Point3d.Origin) }, new[] { new ObjectAttributes() });
                for (int i = 0; i < 12; i++)
                {
                    var child = doc.InstanceDefinitions[definition];
                    definition = doc.InstanceDefinitions.Add("notes level " + i, "", Point3d.Origin,
                        new GeometryBase[] { new InstanceReferenceGeometry(child.Id, Transform.Identity),
                            new InstanceReferenceGeometry(child.Id, Transform.Translation(1, 0, 0)) },
                        new[] { new ObjectAttributes(), new ObjectAttributes() });
                }
                var id = doc.Objects.AddInstanceObject(definition, Transform.Identity);
                var notes = AlmondSpatial.Outline(doc, new JObject { ["ids"] = new JArray(id.ToString()),
                    ["field_groups"] = new JArray("annotations"), ["max_items"] = 200 });
                Check((bool)notes["truncated"] && (int?)notes["visited"] <= 200 && (string)notes["reason"] == "max_visits",
                    "Annotations-only traversal performed unbounded repeated occurrence work.");
            });

            Run(lines, "Given offscreen entities, they cannot consume the visible label budget", doc =>
            {
                var outside = Enumerable.Range(0, 250).Select(i => doc.Objects.AddPoint(new Point3d(1000 + i, 0, 0))).ToList();
                var visible = doc.Objects.AddPoint(Point3d.Origin);
                outside.Add(visible);
                var roots = outside.Select(id => ObservationEntities.ObjectEntity(doc, doc.Objects.FindId(id), Transform.Identity, null));
                bool truncated, limited;
                var rows = ObservationEntities.Expand(doc, roots, 1, 200, out truncated, out limited,
                    entity => entity.Bounds.Center.X < 10);
                Check(rows.Count == 1 && rows[0].Id == visible && !truncated,
                    "Offscreen roots exhausted the label budget before the visible target was considered.");
            });

            Run(lines, "first context query preserves a fresh headless document", doc =>
            {
                Check(doc.Layers.FindName("A-WALL") == null && doc.Layers.FindName("A-STRC") == null &&
                    doc.Layers.FindName("A-GLAZ") == null, "The fresh fixture already has executor-created layers.");
                var before = DocumentState(doc);
                var reply = Wire(DocumentObservation.GetContext(doc, 50, new[] { "document", "selection", "viewport" }));
                Success(reply);
                ContextMetadata(reply, doc, 0);
                Check(reply["viewport"] != null && reply["viewport"].Type == JTokenType.Null,
                    "A missing headless viewport was presented as data.");
                Check(Warnings(reply).Values<string>().Any(value => value.Contains("viewport")),
                    "A headless document's unavailable viewport was not reported.");
                SelectionMetadata(reply, doc, 0, 0);
                Unchanged(before, DocumentState(doc), "First context query");
            });

            Run(lines, "selection limits preserve total counts, metadata and selected objects", doc =>
            {
                uint record = doc.BeginUndoRecord("observation selection fixture");
                Check(record != 0, "Could not open the fixture's Undo record.");
                var ids = new List<Guid>();
                try
                {
                    int layer = doc.Layers.Add(new Layer { Name = "observation fixture" });
                    Check(layer >= 0, "Could not create the fixture layer.");
                    for (int i = 0; i < 3; i++)
                    {
                        var id = doc.Objects.AddPoint(new Point3d(i, 2, 3),
                            new ObjectAttributes { Name = "selected " + i, LayerIndex = layer });
                        Check(id != Guid.Empty, "Could not create a selection fixture point.");
                        ids.Add(id);
                    }
                }
                finally
                {
                    Check(doc.EndUndoRecord(record), "Could not close the fixture's Undo record.");
                }
                foreach (var id in ids)
                    Check(doc.Objects.Select(id, true), "Could not select a fixture point.");
                doc.Modified = false;
                var before = DocumentState(doc);
                foreach (int limit in new[] { 0, 1, 3, 200 })
                {
                    var reply = Wire(DocumentObservation.GetContext(doc, limit, new[] { "document", "selection" }));
                    Success(reply);
                    ContextMetadata(reply, doc, 3);
                    SelectionMetadata(reply, doc, 3, Math.Min(limit, 3));
                    Unchanged(before, DocumentState(doc), "Context with selection limit " + limit);
                }
                FixtureUndoOrRedo(doc, false);
                Check(ids.All(id => !IsLive(doc, id)), "Fixture Undo no longer removes the original points.");
                FixtureUndoOrRedo(doc, true);
                Check(ids.All(id => IsLive(doc, id)), "Fixture Redo no longer restores the original points.");
            });

            Run(lines, "context collects only requested sections", doc =>
            {
                var before = DocumentState(doc);
                var defaults = Wire(DocumentObservation.GetContext(doc));
                Success(defaults);
                Check(defaults["document"] != null && defaults["selection"] == null && defaults["viewport"] == null,
                    "Default context must contain only document data.");
                Check(!Warnings(defaults).HasValues, "Unrequested headless viewport was still observed.");
                var selection = Wire(DocumentObservation.GetContext(doc, 0, new[] { "selection" }));
                Success(selection);
                Check(selection["selection"] != null && selection["document"] == null && selection["viewport"] == null,
                    "Selection-only context collected another section.");
                Error(Wire(DocumentObservation.GetContext(doc, 0, new[] { "invalid" })), "invalid_arguments");
                Unchanged(before, DocumentState(doc), "Selective context");
            });

            Run(lines, "context query works without enabling disabled Undo recording", doc =>
            {
                doc.UndoRecordingEnabled = false;
                var before = DocumentState(doc);
                Success(Wire(DocumentObservation.GetContext(doc)));
                Unchanged(before, DocumentState(doc), "Context with Undo disabled");
            });

            Run(lines, "context does not join or close a caller-owned Undo record", doc =>
            {
                uint owner = doc.BeginUndoRecord("observation fixture owner");
                Check(owner != 0, "Could not create the fixture's Undo record.");
                try
                {
                    Check(doc.Objects.AddPoint(Point3d.Origin) != Guid.Empty, "Could not create the fixture point.");
                    var before = DocumentState(doc);
                    Success(Wire(DocumentObservation.GetContext(doc)));
                    Unchanged(before, DocumentState(doc), "Context with a caller-owned record");
                }
                finally
                {
                    if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == owner)
                        Check(doc.EndUndoRecord(owner), "Could not close the fixture-owned record.");
                }
            });

            Run(lines, "out-of-range selection limits report errors without changes", doc =>
            {
                var before = DocumentState(doc);
                Error(Wire(DocumentObservation.GetContext(doc, -1)), "invalid_arguments");
                Error(Wire(DocumentObservation.GetContext(doc, 201)), "invalid_arguments");
                Unchanged(before, DocumentState(doc), "Invalid selection limit");
            });

            Run(lines, "dispatch rejects malformed limits before reading the active document", doc =>
            {
                var before = DocumentState(doc);
                foreach (var invalid in new JToken[] { JValue.CreateNull(), new JValue("1"),
                    new JValue(true), new JValue(1.5), new JValue(long.MaxValue) })
                {
                    Error(JObject.Parse(DocumentObservation.HandleContext(
                        new JObject { ["selection_limit"] = invalid.DeepClone() })), "invalid_arguments");
                    Error(JObject.Parse(DocumentObservation.HandleViewportImage(
                        new JObject { ["scale_percent"] = invalid.DeepClone() })), "invalid_arguments");
                    Error(JObject.Parse(DocumentObservation.HandleViewportImage(
                        new JObject { ["view"] = invalid.DeepClone() })), "invalid_arguments");
                }
                Unchanged(before, DocumentState(doc), "Invalid dispatch arguments");
            });

            Run(lines, "headless viewport capture reports unavailability without changes", doc =>
            {
                Check(doc.Views.ActiveView == null, "The headless fixture unexpectedly has an active view.");
                var before = DocumentState(doc);
                Error(Wire(DocumentObservation.GetViewportImage(doc)), "no_viewport");
                var listed = Wire(DocumentObservation.GetViewportImage(doc, "a"));
                Success(listed);
                Check(!listed["views"]["viewports"].HasValues && !listed["views"]["layouts"].HasValues,
                    "A headless document listed visible viewports.");
                Unchanged(before, DocumentState(doc), "Headless viewport capture");
            });

            var noDocument = Wire(DocumentObservation.GetContext(null));
            Error(noDocument, "no_document");
            lines.Add("PASS context without a document returns a structured error");
            var noImage = Wire(DocumentObservation.GetViewportImage(null));
            Error(noImage, "no_document");
            lines.Add("PASS capture without a document returns a structured error");

            return Report(lines, "headless observation");
        }

        // The caller chooses and owns the real document. Invoke on Rhino's UI thread
        // after explicitly arranging the desired view/selection/clipping fixture.
        // This method observes that state and never changes it to prepare a capture.
        public static string RunViewport(RhinoDoc doc)
        {
            Check(doc != null && !doc.IsHeadless, "RunViewport requires a caller-supplied visible document.");
            Check(RhinoDoc.ActiveDoc != null && RhinoDoc.ActiveDoc.RuntimeSerialNumber == doc.RuntimeSerialNumber,
                "RunViewport requires the caller's document to be active.");
            var view = doc.Views.ActiveView;
            Check(view != null, "RunViewport requires a real active viewport.");
            var before = DocumentState(doc);
            var lines = new List<string>();

            var context = Wire(DocumentObservation.GetContext(doc, 0, new[] { "document", "viewport" }));
            Success(context);
            IdentityMetadata(context, doc);
            ViewportMetadata(context["viewport"] as JObject, view.ActiveViewport);
            Unchanged(before, DocumentState(doc), "Real-view context");
            lines.Add("PASS real-view context describes the active viewport without changes");

            foreach (var percent in new[] { 1, 50, 100 })
            {
                var reply = Wire(DocumentObservation.GetViewportImage(doc, "", percent));
                Unchanged(before, DocumentState(doc), "Viewport capture " + percent);
                Success(reply);
                DecodePng(reply, percent);
                lines.Add("PASS " + percent + "% PNG capture; document/view state preserved");
            }

            foreach (var percent in new[] { 0, 101 })
            {
                Error(Wire(DocumentObservation.GetViewportImage(doc, "", percent)), "invalid_arguments");
                Unchanged(before, DocumentState(doc), "Invalid capture percentage " + percent);
            }
            Error(Wire(DocumentObservation.GetViewportImage(doc, Guid.NewGuid().ToString())), "view_not_found");
            Unchanged(before, DocumentState(doc), "Unknown view GUID");
            lines.Add("PASS capture argument errors preserve the real document and view");
            return Report(lines, "caller-supplied viewport observation");
        }

        private static void IdentityMetadata(JObject reply, RhinoDoc doc)
        {
            var document = reply["document"] as JObject;
            Check(document != null, "Observation omitted document identity.");
            Check((uint)document["runtime_serial_number"] == doc.RuntimeSerialNumber &&
                (string)document["path"] == doc.Path && (string)document["name"] == doc.Name,
                "Observation identifies a different document.");
        }

        // Only in a separate Rhino process with an empty, unmodified startup document.
        public static string RunImageTargets(string directory)
        {
            var startup = RhinoDoc.ActiveDoc;
            Check(startup == null || (!startup.Modified && string.IsNullOrEmpty(startup.Path) &&
                !startup.Objects.GetObjectList(ObjectType.AnyObject).Any()), "Use an isolated empty Rhino process.");
            Directory.CreateDirectory(directory);
            string path = Path.Combine(directory, "view-images.3dm");
            using (var seed = RhinoDoc.CreateHeadless(null))
            {
                seed.PageUnitSystem = UnitSystem.Millimeters;
                var boxId = seed.Objects.AddBox(new Box(new BoundingBox(new Point3d(-10, -20, 0), new Point3d(20, 10, 50))));
                var pointId = seed.Objects.AddPoint(new Point3d(0, 0, 50));
                seed.Groups.Add("capture group", new[] { boxId, pointId });
                using (var geometry = Brep.CreateFromBox(new BoundingBox(new Point3d(0, 0, 0), new Point3d(10, 10, 10))))
                {
                    int definition = seed.InstanceDefinitions.Add("capture block", "", Point3d.Origin,
                        new GeometryBase[] { geometry }, new[] { new ObjectAttributes() });
                    seed.Objects.AddInstanceObject(definition, Transform.Translation(40, 0, 0));
                }
                Check(seed.WriteFile(path, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Fixture save failed.");
            }
            bool alreadyOpen;
            using (var doc = RhinoDoc.Open(path, out alreadyOpen))
            {
                Check(doc != null && !alreadyOpen && !doc.IsHeadless, "A fresh visible fixture document is required.");
                try
                {
                    var model = doc.Views.GetStandardRhinoViews()[0];
                    doc.Views.ActiveView = model;
                    model.MainViewport.DisplayMode = DisplayModeDescription.GetDisplayMode(DisplayModeDescription.WireframeId);
                    model.MainViewport.ZoomExtents();
                    int namedIndex = doc.NamedViews.Add("saved model", model.MainViewport.Id);
                    Check(namedIndex >= 0, "Could not save the named-view fixture.");
                    model.MainViewport.ZoomBoundingBox(new BoundingBox(new Point3d(1000, 1000, 1000), new Point3d(1020, 1040, 1080)));
                    var page = doc.Views.AddPageView("A4 paper", 210, 297);
                    Check(page != null, "Could not create a layout fixture.");
                    var attributes = new ObjectAttributes { Space = ActiveSpace.PageSpace, ViewportId = page.MainViewport.Id };
                    doc.Objects.AddRectangle(new Rectangle3d(Plane.WorldXY, new Interval(10, 200), new Interval(10, 287)), attributes);
                    doc.Views.ActiveView = model;
                    doc.Views.Redraw();
                    doc.Modified = false;
                    var before = DocumentState(doc);
                    Check(ObservationEntities.ModelObjects(doc).All(obj => obj.Attributes.Space != ActiveSpace.PageSpace),
                        "Paper-space geometry leaked into model viewport label candidates.");
                    var listed = Wire(DocumentObservation.GetViewportImage(doc, "a"));
                    Success(listed);
                    Unchanged(before, DocumentState(doc), "List image targets");
                    var groups = (JObject)listed["views"];
                    Check(((JArray)groups["named_views"]).Count == 1 && ((JArray)groups["layouts"]).Count == 1,
                        "List omitted the saved view or layout.");
                    var lines = new List<string> { RunViewport(doc) };
                    using (ManagedFiles.Bind(doc, directory, "tmp/261026_native"))
                    {
                        Check(ManagedFiles.Input("view-images.3dm") == path, "Managed input root differs.");
                        string output = ManagedFiles.Output("nested/result.txt");
                        Check(output == Path.Combine(directory, "tmp", "261026_native", "nested", "result.txt"),
                            "Managed output did not use the selected artifact folder.");
                        File.WriteAllText(output, "fixture");
                        foreach (var invalid in new[] { "../escape.txt", path, "C:escape.txt" })
                        {
                            bool rejected = false;
                            try { ManagedFiles.Output(invalid); } catch (ArgumentException) { rejected = true; }
                            Check(rejected, "Managed path escape was accepted: " + invalid);
                        }
                    }
                    bool scopeClosed = false;
                    try { ManagedFiles.Input("view-images.3dm"); } catch (InvalidOperationException) { scopeClosed = true; }
                    Check(scopeClosed, "Managed file scope leaked beyond its call.");
                    lines.Add("PASS managed relative paths and call-scope restoration");
                    foreach (var group in groups.Properties())
                    {
                        foreach (JObject entry in (JArray)group.Value)
                        {
                            Check(entry.Properties().Count() == 2 && entry["name"] != null && entry["guid"] != null,
                                "View list exposes fields beyond name and GUID.");
                            int activations = 0;
                            EventHandler<ViewEventArgs> activated = (sender, args) => activations++;
                            JObject reply;
                            RhinoView.SetActive += activated;
                            try { reply = Wire(DocumentObservation.GetViewportImage(doc, (string)entry["guid"], 50)); }
                            finally { RhinoView.SetActive -= activated; }
                            Check(activations == 0, "Capturing a target activated a view before restoring it.");
                            Success(reply);
                            DecodePng(reply, 50);
                            Unchanged(before, DocumentState(doc), "Capture " + group.Name);
                            if (group.Name == "layouts")
                            {
                                Check(Math.Abs((int)reply["image"]["source_width"] - 210 * 96.0 / 25.4) <= 1 &&
                                    Math.Abs((int)reply["image"]["source_height"] - 297 * 96.0 / 25.4) <= 1,
                                    "Layout capture includes the workspace instead of the A4 paper.");
                            }
                            File.WriteAllBytes(Path.Combine(directory, group.Name + "-" + entry["guid"] + ".png"),
                                Convert.FromBase64String((string)reply["image"]["data"]));
                            lines.Add("PASS " + group.Name + " " + entry["name"] + ": PNG, percentage and unchanged document/view");
                        }
                    }
                    var named = DocumentObservation.GetViewportImage(doc, doc.NamedViews[namedIndex].NamedViewId.ToString());
                    var active = DocumentObservation.GetViewportImage(doc);
                    Check((string)named["image"]["data"] != (string)active["image"]["data"],
                        "Named-view capture returned the active camera instead of the saved view.");
                    Unchanged(before, DocumentState(doc), "Named view versus active camera");
                    lines.Add("PASS saved camera differs from active camera without restoring it");
                    var namedId = doc.NamedViews[namedIndex].NamedViewId.ToString();
                    var explicitShaded = DocumentObservation.GetViewportImage(doc, namedId, 75, "Shaded");
                    var noLabels = DocumentObservation.GetViewportImage(doc, namedId, 75, "Shaded", false);
                    var wireframe = DocumentObservation.GetViewportImage(doc, namedId, 75, "Wireframe", false);
                    Success(explicitShaded); Success(noLabels); Success(wireframe);
                    Check((string)named["image"]["data"] == (string)explicitShaded["image"]["data"], "Named View did not default to Shaded.");
                    Check((string)named["image"]["data"] != (string)noLabels["image"]["data"], "Default transient labels were not drawn.");
                    Check((string)noLabels["image"]["data"] != (string)wireframe["image"]["data"], "Explicit display mode had no effect.");
                    var installedModes = DisplayModeDescription.GetDisplayModes();
                    var alternateMode = installedModes.FirstOrDefault(candidate =>
                        String.Equals(candidate.EnglishName, "Dark", StringComparison.OrdinalIgnoreCase) ||
                        String.Equals(candidate.EnglishName, "CadWhite", StringComparison.OrdinalIgnoreCase)) ??
                        installedModes.FirstOrDefault(candidate => candidate.Id == DisplayModeDescription.GhostedId);
                    Check(alternateMode != null, "No installed alternate display mode is available for the capture fixture.");
                    var alternate = DocumentObservation.GetViewportImage(doc, namedId, 75, alternateMode.Id.ToString(), false);
                    Success(alternate); DecodePng(alternate, 75);
                    Check((string)alternate["image"]["data"] != (string)noLabels["image"]["data"],
                        "The installed " + alternateMode.EnglishName + " mode was silently rendered as Shaded.");
                    lines.Add("PASS installed " + alternateMode.EnglishName + " display mode is applied without registering or editing modes");
                    var realtimeMode = installedModes.FirstOrDefault(candidate => candidate.DisplayAttributes.RealtimeDisplayId != Guid.Empty);
                    if (realtimeMode != null)
                    {
                        Error(DocumentObservation.GetViewportImage(doc, namedId, 50, realtimeMode.Id.ToString(), false), "unsupported_display_mode");
                        lines.Add("PASS installed " + realtimeMode.EnglishName + " realtime mode is rejected before asynchronous rendering");
                    }
                    Unchanged(before, DocumentState(doc), "Capture modes and pixel labels");
                    lines.Add("PASS detached Shaded default, explicit Wireframe and transient labels preserve the user's mode");
                    // A distant object must not make a focused target's visible label disappear.
                    doc.Objects.AddBox(new Box(new BoundingBox(new Point3d(10000, 10000, 0), new Point3d(10020, 10040, 80))));
                    doc.Modified = false;
                    before = DocumentState(doc);
                    var captureGroup = doc.Groups.FindName("capture group");
                    var captureBlock = doc.Objects.GetObjectList(ObjectType.InstanceReference).OfType<InstanceObject>().Single();
                    foreach (var target in new[] { new[] { "group", captureGroup.Id.ToString() }, new[] { "block", captureBlock.Id.ToString() } })
                    {
                        var focused = DocumentObservation.GetViewportImage(doc, "", 50, "", true, 1, target[0], target[1]);
                        var withoutLabels = DocumentObservation.GetViewportImage(doc, "", 50, "", false, 1, target[0], target[1]);
                        Success(focused); DecodePng(focused, 50);
                        Success(withoutLabels);
                        Check((string)focused["image"]["data"] != (string)withoutLabels["image"]["data"],
                            "A visible focused " + target[0] + " target lost its label with distant model geometry.");
                        Unchanged(before, DocumentState(doc), "Framed " + target[0]);
                        File.WriteAllBytes(Path.Combine(directory, "target-" + target[0] + ".png"), Convert.FromBase64String((string)focused["image"]["data"]));
                    }
                    lines.Add("PASS group/block GUID captures frame independently without selecting or hiding objects");
                    using (var saved = new ViewportInfo(model.MainViewport))
                    {
                        var savedTarget = model.MainViewport.CameraTarget;
                        var cameraDiagnostics = new JObject { ["original"] = ViewportState(model.MainViewport) };
                        JObject movedState = null;
                        JObject capturedState = null;
                        bool moved = false;
                        EventHandler<DrawEventArgs> moveActive = (sender, args) =>
                        {
                            if (moved) return;
                            moved = true;
                            model.MainViewport.ZoomBoundingBox(new BoundingBox(new Point3d(2000, 2000, 0), new Point3d(2040, 2050, 100)));
                            movedState = DocumentState(doc);
                            cameraDiagnostics["fixture_moved"] = ViewportState(model.MainViewport);
                        };
                        JObject independent;
                        DisplayPipeline.DrawForeground += moveActive;
                        try
                        {
                            independent = DocumentObservation.GetViewportImage(doc, namedId, 50);
                            capturedState = DocumentState(doc);
                        }
                        finally
                        {
                            DisplayPipeline.DrawForeground -= moveActive;
                            cameraDiagnostics["after_capture"] = ViewportState(model.MainViewport);
                            Check(model.MainViewport.SetViewProjection(saved, true), "Could not restore the fixture camera projection.");
                            cameraDiagnostics["after_projection_restore"] = ViewportState(model.MainViewport);
                            // SetViewProjection(..., true) recalculates the target rather than
                            // restoring its original value. This is fixture cleanup, not capture.
                            model.MainViewport.SetCameraTarget(savedTarget, false);
                            cameraDiagnostics["after_target_restore"] = ViewportState(model.MainViewport);
                            File.WriteAllText(Path.Combine(directory, "independent-camera-diagnostics.json"), cameraDiagnostics.ToString(Formatting.Indented));
                        }
                        Success(independent);
                        Check(moved, "Independent-capture fixture did not move the active camera during capture.");
                        Unchanged(movedState, capturedState, "Independent named capture after fixture camera movement");
                    }
                    UnchangedAfterFixtureCameraRestore(before, DocumentState(doc), "Independent named capture with controlled active-camera movement");
                    lines.Add("PASS moving the active camera alone does not invalidate a detached Named View capture");
                    return Report(lines, "view image targets");
                }
                finally { doc.Modified = false; }
            }
        }

        private static void ContextMetadata(JObject reply, RhinoDoc doc, int objectCount)
        {
            IdentityMetadata(reply, doc);
            var document = (JObject)reply["document"];
            Check((string)document["units"] == doc.ModelUnitSystem.ToString() &&
                (double)document["absolute_tolerance"] == doc.ModelAbsoluteTolerance &&
                (double)document["angle_tolerance_radians"] == doc.ModelAngleToleranceRadians,
                "Document units or tolerances differ from the queried document.");
            Check((bool)document["modified"] == doc.Modified && (int)document["object_count"] == objectCount &&
                (int)document["layer_count"] == doc.Layers.ActiveCount, "Document state or counts are incorrect.");
        }

        private static void SelectionMetadata(JObject reply, RhinoDoc doc, int total, int returned)
        {
            var selection = reply["selection"] as JObject;
            Check(selection != null, "Observation omitted the selection section.");
            var objects = selection["objects"] as JArray;
            Check(objects != null && objects.Count == returned && (int)selection["total"] == total &&
                (int)selection["returned"] == returned && (bool)selection["truncated"] == (total > returned),
                "Selection limits, total count or truncation metadata are incorrect.");
            var ids = new HashSet<Guid>();
            foreach (var item in objects)
            {
                Guid id;
                Check(Guid.TryParse((string)item["id"], out id) && ids.Add(id), "Selected object ID is invalid or duplicated.");
                var obj = doc.Objects.FindId(id);
                Check(obj != null && obj.IsSelected(false) != 0, "Returned selection item is not selected.");
                Check((string)item["name"] == obj.Name && (string)item["type"] == obj.ObjectType.ToString() &&
                    (string)item["layer"] == doc.Layers[obj.Attributes.LayerIndex].FullPath,
                    "Selected object name, type or layer metadata is incorrect.");
            }
        }

        private static void ViewportMetadata(JObject metadata, RhinoViewport viewport)
        {
            Check(metadata != null, "Observation omitted viewport metadata.");
            Check((string)metadata["id"] == viewport.Id.ToString() && (string)metadata["name"] == viewport.Name &&
                (int)metadata["width"] == viewport.Size.Width && (int)metadata["height"] == viewport.Size.Height,
                "Viewport identity or original pixel dimensions are incorrect.");
            Check((string)metadata["display_mode"] == viewport.DisplayMode.EnglishName &&
                (double)metadata["lens_length"] == viewport.Camera35mmLensLength,
                "Viewport display mode or lens metadata is incorrect.");
            string projection = viewport.IsTwoPointPerspectiveProjection ? "two-point-perspective" :
                viewport.IsPerspectiveProjection ? "perspective" : viewport.IsParallelProjection ? "parallel" : "unknown";
            Check((string)metadata["projection"] == projection, "Viewport projection metadata is incorrect.");
            Check(JToken.DeepEquals(metadata["camera_location"], Point(viewport.CameraLocation)) &&
                JToken.DeepEquals(metadata["target"], Point(viewport.CameraTarget)) &&
                JToken.DeepEquals(metadata["up"], Vector(viewport.CameraUp)), "Camera metadata does not match the captured viewport.");
        }

        private static void DecodePng(JObject reply, int percent)
        {
            var payload = reply["image"] as JObject;
            Check(payload != null && (string)payload["mime_type"] == "image/png", "Capture omitted its PNG payload or MIME type.");
            byte[] bytes = Convert.FromBase64String((string)payload["data"]);
            Check(bytes.Length > 0 && bytes.Length <= 4 * 1024 * 1024, "Image exceeds the 4 MiB limit.");
            using (var stream = new MemoryStream(bytes, false))
            using (var decoded = Image.FromStream(stream, true, true))
            {
                Check(decoded.RawFormat.Guid == ImageFormat.Png.Guid, "Capture bytes are not a decodable PNG.");
                int width = decoded.Width, height = decoded.Height;
                Check(width == (int)payload["width"] && height == (int)payload["height"],
                    "Decoded PNG dimensions differ from image metadata.");
                Check(width == Math.Max(1, (int)payload["source_width"] * percent / 100) &&
                    height == Math.Max(1, (int)payload["source_height"] * percent / 100), "Capture ignored the requested percentage.");
            }
        }

        private static void Run(List<string> lines, string name, Action<RhinoDoc> test)
        {
            using (var doc = RhinoDoc.CreateHeadless(null))
            {
                doc.UndoRecordingEnabled = true;
                try
                {
                    test(doc);
                    Check(!doc.UndoActive && !doc.RedoActive && !doc.UndoRecordingIsActive &&
                        doc.CurrentUndoRecordSerialNumber == 0, "The observation left an active Undo operation.");
                    lines.Add("PASS " + name);
                }
                catch (Exception ex)
                {
                    lines.Add("FAIL " + name + ": " + ex);
                }
            }
        }

        private static JObject Wire(JObject response)
        {
            Check(response != null, "Observation returned no response.");
            using (var reader = new JsonTextReader(new StringReader(JsonConvert.SerializeObject(response))))
            {
                // JSON timestamps are strings on the wire; avoid Json.NET's optional
                // date coercion when checking the timestamp's UTC suffix and precision.
                reader.DateParseHandling = DateParseHandling.None;
                return JObject.Load(reader);
            }
        }

        private static void Success(JObject response)
        {
            Check((string)response["status"] == "success", "Observation failed: " + response.ToString(Formatting.None));
            Warnings(response);
        }

        private static void Error(JObject response, string expectedCode)
        {
            Check((string)response["status"] == "error", "Unavailable or invalid observation was reported as successful.");
            Check((string)response["error_code"] == expectedCode, "Unexpected observation error code: " + response);
            Check(!string.IsNullOrWhiteSpace((string)response["message"]), "Observation error omitted its explanation.");
            Check(response.Property("image") == null, "An unsuccessful capture exposed image data.");
            Warnings(response);
        }

        private static JArray Warnings(JObject response)
        {
            var warnings = response["warnings"] as JArray;
            Check(warnings != null, "Observation omitted the warnings array.");
            Check(warnings.All(item => item.Type == JTokenType.String && !string.IsNullOrWhiteSpace((string)item)),
                "Warnings must contain non-empty text.");
            return warnings;
        }

        private static JObject DocumentState(RhinoDoc doc)
        {
            // Capture independent document state; do not reuse the product's context
            // response as an oracle for whether that same product changed the model.
            var objects = new JArray();
            foreach (var obj in doc.Objects.GetObjectList(ObjectType.AnyObject).OrderBy(obj => obj.Id))
            {
                var state = new JObject
                {
                    ["id"] = obj.Id.ToString(),
                    ["type"] = obj.ObjectType.ToString(),
                    ["geometry_crc"] = obj.Geometry == null ? 0u : obj.Geometry.DataCRC(0),
                    ["attributes_json"] = obj.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions { WriteUserData = true }),
                    ["selection"] = obj.IsSelected(false)
                };
                var clippingPlane = obj as ClippingPlaneObject;
                if (clippingPlane != null)
                    state["clipped_viewports"] = new JArray(clippingPlane.ClippingPlaneGeometry.ViewportIds()
                        .OrderBy(id => id).Select(id => id.ToString()));
                objects.Add(state);
            }

            var layers = new JArray();
            foreach (var layer in doc.Layers.OrderBy(layer => layer.Id))
                layers.Add(new JObject
                {
                    ["id"] = layer.Id.ToString(),
                    ["index"] = layer.Index,
                    ["deleted"] = layer.IsDeleted,
                    ["crc"] = layer.DataCRC(0)
                });

            var views = new JArray();
            foreach (var view in doc.Views.GetViewList(true, true).OrderBy(view => view.MainViewport.Id))
                views.Add(ViewState(view));

            return new JObject
            {
                ["document_serial"] = doc.RuntimeSerialNumber,
                ["path"] = doc.Path,
                ["name"] = doc.Name,
                ["units"] = doc.ModelUnitSystem.ToString(),
                ["absolute_tolerance"] = doc.ModelAbsoluteTolerance,
                ["angle_tolerance_radians"] = doc.ModelAngleToleranceRadians,
                ["modified"] = doc.Modified,
                ["undo_enabled"] = doc.UndoRecordingEnabled,
                ["undo_active"] = doc.UndoActive,
                ["redo_active"] = doc.RedoActive,
                ["recording"] = doc.UndoRecordingIsActive,
                ["current_record"] = doc.CurrentUndoRecordSerialNumber,
                ["next_record"] = doc.NextUndoRecordSerialNumber,
                ["active_view"] = doc.Views.ActiveView == null ? null : doc.Views.ActiveView.ActiveViewport.Id.ToString(),
                ["objects"] = objects,
                ["layers"] = layers,
                ["views"] = views
            };
        }

        private static JObject ViewState(RhinoView view)
        {
            return new JObject
            {
                ["main_id"] = view.MainViewport.Id.ToString(),
                ["active_id"] = view.ActiveViewportID.ToString(),
                ["main"] = ViewportState(view.MainViewport),
                ["active"] = ViewportState(view.ActiveViewport)
            };
        }

        private static JObject ViewportState(RhinoViewport viewport)
        {
            double left, right, bottom, top, near, far;
            bool frustum = viewport.GetFrustum(out left, out right, out bottom, out top, out near, out far);
            return new JObject
            {
                ["id"] = viewport.Id.ToString(),
                ["name"] = viewport.Name,
                ["location"] = Point(viewport.CameraLocation),
                ["target"] = Point(viewport.CameraTarget),
                ["direction"] = Vector(viewport.CameraDirection),
                ["up"] = Vector(viewport.CameraUp),
                ["lens_mm"] = viewport.Camera35mmLensLength,
                ["parallel"] = viewport.IsParallelProjection,
                ["perspective"] = viewport.IsPerspectiveProjection,
                ["two_point"] = viewport.IsTwoPointPerspectiveProjection,
                ["display_mode"] = viewport.DisplayMode == null ? null : viewport.DisplayMode.Id.ToString(),
                ["width"] = viewport.Size.Width,
                ["height"] = viewport.Size.Height,
                ["frustum_available"] = frustum,
                ["frustum"] = new JArray(left, right, bottom, top, near, far)
            };
        }

        private static JArray Point(Point3d value)
        {
            return new JArray(value.X, value.Y, value.Z);
        }

        private static JArray Vector(Vector3d value)
        {
            return new JArray(value.X, value.Y, value.Z);
        }

        private static bool IsLive(RhinoDoc doc, Guid id)
        {
            var obj = doc.Objects.FindId(id);
            return obj != null && !obj.IsDeleted;
        }

        private static void FixtureUndoOrRedo(RhinoDoc doc, bool redo)
        {
            // Match the existing native Undo fixture: observe idle state before
            // cleanup, then close only the record created by this test's Undo/Redo.
            Check(!doc.UndoActive && !doc.RedoActive && !doc.UndoRecordingIsActive &&
                doc.CurrentUndoRecordSerialNumber == 0, "Observation left an active Undo record.");
            uint serial = doc.NextUndoRecordSerialNumber;
            try
            {
                Check(redo ? doc.Redo() : doc.Undo(), "Observation damaged the fixture's " + (redo ? "Redo." : "Undo."));
            }
            finally
            {
                if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == serial)
                    Check(doc.EndUndoRecord(serial), "Could not close the fixture's Undo/Redo record.");
            }
            Check(!doc.UndoActive && !doc.RedoActive && !doc.UndoRecordingIsActive &&
                doc.CurrentUndoRecordSerialNumber == 0, "Fixture Undo/Redo left an active record.");
        }

        private static void Unchanged(JObject before, JObject after, string label)
        {
            Check(JToken.DeepEquals(before, after),
                label + " changed document/view state. Before: " + before.ToString(Formatting.None) +
                " After: " + after.ToString(Formatting.None));
        }

        private static void UnchangedAfterFixtureCameraRestore(JObject before, JObject after, string label)
        {
            // Only the fixture intentionally restores its own camera through SetViewProjection.
            // Compare the resulting floating-point roundoff separately; all product captures above
            // retain exact document/view comparisons and every identity/attribute/Undo field stays exact.
            var normalized = (JObject)after.DeepClone();
            for (int i = 0; i < ((JArray)before["views"]).Count; i++)
            {
                foreach (var part in new[] { "main", "active" })
                foreach (var field in new[] { "location", "target", "direction", "up", "lens_mm", "frustum" })
                {
                    var expected = before["views"][i][part][field];
                    var actual = normalized["views"][i][part][field];
                    var expectedValues = expected is JArray ? expected.Values<double>().ToArray() : new[] { (double)expected };
                    var actualValues = actual is JArray ? actual.Values<double>().ToArray() : new[] { (double)actual };
                    Check(expectedValues.Length == actualValues.Length && expectedValues.Zip(actualValues,
                        (x, y) => Math.Abs(x - y) <= 1e-9 * Math.Max(1.0, Math.Max(Math.Abs(x), Math.Abs(y)))).All(equal => equal),
                        label + " changed the original viewport " + field + ". Expected: " + expected.ToString(Formatting.None) +
                        " Actual: " + actual.ToString(Formatting.None));
                    normalized["views"][i][part][field] = expected.DeepClone();
                }
            }
            Unchanged(before, normalized, label);
        }

        private static string Report(List<string> lines, string suite)
        {
            string report = "Rhino " + RhinoApp.Version + "\n" + string.Join("\n", lines);
            int failures = lines.Count(line => line.StartsWith("FAIL "));
            if (failures != 0)
                throw new InvalidOperationException(report + "\n" + failures + " test(s) failed.");
            return report + "\nPASS: " + lines.Count + "/" + lines.Count + " " + suite + " cases.";
        }

        private static void Check(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
