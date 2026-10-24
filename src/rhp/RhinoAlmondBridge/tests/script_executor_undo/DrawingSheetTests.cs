using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    public static class DrawingSheetTests
    {
        public static string RunAll(string directory)
        {
            var lines = new List<string>();
            foreach (bool mixedUnits in new[] { false, true })
                Run(lines, directory, "Sheet identity, true scale and region center " + (mixedUnits ? "m/in" : "mm/mm"), doc =>
                {
                    double modelMm = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Millimeters);
                    var modelId = doc.Objects.AddLine(new Point3d(10000 / modelMm, 20000 / modelMm, 0),
                        new Point3d(30000 / modelMm, 30000 / modelMm, 0));
                    int pages = doc.Views.GetPageViews().Length;
                    var activeView = doc.Views.ActiveView;
                    var request = Request(doc, "upsert", "sheet-scale");
                    var created = Success(DrawingSheetRegistry.Handle(doc, request));
                    Check((string)created["plan_id"] == "", "A null plan_id was not normalized to an empty reference.");
                    Guid layout = Guid.Parse((string)created["layout_id"]);
                    Guid detailId = Guid.Parse((string)created["detail_id"]);
                    Check(doc.Views.GetPageViews().Length == pages + 1, "Sheet did not create exactly one layout.");
                    var detail = doc.Objects.FindId(detailId) as DetailViewObject;
                    Check(detail != null && Near(detail.DetailGeometry.PageToModelRatio, 0.01), "Physical scale is not 1:100.");
                    Check(detail.Viewport.CameraTarget.DistanceTo(new Point3d(20000 / modelMm, 25000 / modelMm, 0)) * modelMm < 0.001,
                        "Drawing region is not centered.");
                    Check(doc.Views.ActiveView?.RuntimeSerialNumber == activeView?.RuntimeSerialNumber, "Creating a Sheet changed the caller's active view.");
                    request["plan_id"] = "";
                    var repeated = Success(DrawingSheetRegistry.Handle(doc, request));
                    Check((string)repeated["plan_id"] == "", "An empty plan_id was not retained as an empty reference.");
                    Check((string)repeated["layout_id"] == layout.ToString("D") && (string)repeated["detail_id"] == detailId.ToString("D") &&
                        doc.Views.GetPageViews().Length == pages + 1, "Repeating the same identity duplicated layout/detail.");
                    request["layout_id"] = layout.ToString("D");
                    request["title"] = "Updated Sheet";
                    request["paper_mm"] = new JArray(594.0, 420.0);
                    request["scale_denominator"] = 50.0;
                    var updated = Success(DrawingSheetRegistry.Handle(doc, request));
                    Check((string)updated["layout_id"] == layout.ToString("D") && (string)updated["detail_id"] == detailId.ToString("D"), "Update changed identity.");
                    Check(Near((double)updated["scale_denominator"], 50) && Near((double)updated["paper_mm"][0], 594), "Update lost paper or physical scale.");
                    Check(doc.Objects.FindId(modelId) != null, "Sheet changed authored model geometry.");
                    var inspected = Success(DrawingSheetRegistry.Handle(doc, Request(doc, "inspect", "sheet-scale", layout)));
                    Check((bool)inspected["live_verified"] && (string)inspected["title"] == "Updated Sheet", "Live inspection did not read current layout.");
                    Check((bool)inspected["layout_undo_supported"] == false, "Sheet overclaims view-table Undo.");
                }, mixedUnits);

            Run(lines, directory, "Sheet preflight rejects bad fit, model and title collision without mutation", doc =>
            {
                var request = Request(doc, "upsert", "sheet-fit");
                int before = doc.Views.GetPageViews().Length;
                request["scale_denominator"] = 1.0;
                Rejected(DrawingSheetRegistry.Handle(doc, request));
                request["scale_denominator"] = 100.0;
                request["model_bounds_mm"] = new JArray(10000, 20000, 0, 30000, 30000, 1000);
                Rejected(DrawingSheetRegistry.Handle(doc, request));
                request = Request(doc, "upsert", "sheet-fit");
                request["expected_model_path"] = Path.Combine(Path.GetDirectoryName(doc.Path), "other.3dm");
                Rejected(DrawingSheetRegistry.Handle(doc, request));
                Check(doc.Views.GetPageViews().Length == before, "Rejected input created a layout.");
                var first = Success(DrawingSheetRegistry.Handle(doc, Request(doc, "upsert", "sheet-first")));
                Rejected(DrawingSheetRegistry.Handle(doc, Request(doc, "upsert", "sheet-second")));
                var wrongLayout = Request(doc, "upsert", "sheet-first", Guid.NewGuid());
                Rejected(DrawingSheetRegistry.Handle(doc, wrongLayout));
                Check(doc.Views.GetPageViews().Length == before + 1 && doc.Objects.FindId(Guid.Parse((string)first["detail_id"])) != null,
                    "A conflicting registration changed the existing layout.");
            });

            Run(lines, directory, "Sheet unregister retains layout, detail and model geometry; Undo restores registration", doc =>
            {
                var model = doc.Objects.AddPoint(Point3d.Origin);
                var created = Success(DrawingSheetRegistry.Handle(doc, Request(doc, "upsert", "sheet-remove")));
                Guid layout = Guid.Parse((string)created["layout_id"]), detailId = Guid.Parse((string)created["detail_id"]);
                int count = doc.Views.GetPageViews().Length;
                var removed = DrawingSheetRegistry.Handle(doc, Request(doc, "unregister", "sheet-remove", layout));
                Check((string)removed["status"] == "success" && (string)removed["sheet_id"] == "sheet-remove" &&
                    (string)removed["model_path"] == doc.Path && (string)removed["layout_id"] == layout.ToString("D") &&
                    removed["sheet"] == null, "Unregister did not return its top-level identity acknowledgement: " + removed);
                var repeated = DrawingSheetRegistry.Handle(doc, Request(doc, "unregister", "sheet-remove", layout));
                Check(JToken.DeepEquals(removed, repeated), "Repeated unregister changed its acknowledgement.");
                Check(doc.Views.GetPageViews().Length == count && doc.Objects.FindId(detailId) != null && doc.Objects.FindId(model) != null,
                    "Unregister deleted layout, detail or model geometry.");
                var proof = Success(DrawingSheetRegistry.Handle(doc, Request(doc, "inspect", "sheet-remove", layout)));
                Check((string)proof["registration_status"] == "unregistered" && (bool)proof["complete"] &&
                    (bool)proof["live_verified"], "Inspect cannot reconcile a completed unregister after a lost DB commit.");
                UndoRedo(doc, false);
                Check((string)Success(DrawingSheetRegistry.Handle(doc, Request(doc, "inspect", "sheet-remove", layout)))["registration_status"] == "registered",
                    "Undo did not restore detail registration metadata.");
                UndoRedo(doc, true);
                Check((string)Success(DrawingSheetRegistry.Handle(doc, Request(doc, "inspect", "sheet-remove", layout)))["registration_status"] == "unregistered",
                    "Redo did not restore the unregistered identity proof.");
            });

            Run(lines, directory, "Copied Sheet detail metadata is rejected without a second mutation", doc =>
            {
                var created = Success(DrawingSheetRegistry.Handle(doc, Request(doc, "upsert", "sheet-copy")));
                Guid layoutId = Guid.Parse((string)created["layout_id"]), detailId = Guid.Parse((string)created["detail_id"]);
                var page = doc.Views.GetPageViews().Single(p => p.MainViewport.Id == layoutId);
                var copied = page.AddDetailView("Copied detail", new Point2d(20, 20), new Point2d(100, 100), DefinedViewportProjection.Top);
                Check(copied != null, "Fixture detail copy failed.");
                var original = doc.Objects.FindId(detailId).Attributes;
                var attrs = copied.Attributes.Duplicate();
                attrs.SetUserString("almond:sheet_id", original.GetUserString("almond:sheet_id"));
                attrs.SetUserString("almond:sheet_metadata", original.GetUserString("almond:sheet_metadata"));
                Check(doc.Objects.ModifyAttributes(copied.Id, attrs, true), "Fixture metadata copy failed.");
                Rejected(DrawingSheetRegistry.Handle(doc, Request(doc, "inspect", "sheet-copy", layoutId)));
                Rejected(DrawingSheetRegistry.Handle(doc, Request(doc, "upsert", "sheet-copy", layoutId)));
                Check(page.GetDetailViews().Length == 2, "Ambiguous ownership rejection changed existing details.");
            });

            string report = String.Join("\n", lines);
            if (lines.Any(line => line.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + lines.Count + "/" + lines.Count + " drawing Sheet cases.";
        }

        private static void Run(List<string> lines, string directory, string name, Action<RhinoDoc> test, bool mixedUnits = false)
        {
            string path = Path.Combine(directory, "sheet-" + Guid.NewGuid().ToString("N") + ".3dm");
            using (var fixture = RhinoDoc.CreateHeadless(null))
            {
                fixture.AdjustModelUnitSystem(mixedUnits ? UnitSystem.Meters : UnitSystem.Millimeters, false);
                fixture.PageUnitSystem = mixedUnits ? UnitSystem.Inches : UnitSystem.Millimeters;
                Check(fixture.WriteFile(path, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Sheet fixture save failed.");
            }
            bool alreadyOpen;
            using (var doc = RhinoDoc.Open(path, out alreadyOpen))
            {
                try
                {
                    Check(doc != null && !alreadyOpen && !doc.IsHeadless, "Sheet fixtures need a fresh regular document in the isolated Rhino process.");
                    doc.UndoRecordingEnabled = true;
                    test(doc);
                    Check(!doc.UndoRecordingIsActive && !doc.UndoActive && !doc.RedoActive, "Sheet leaked an Undo operation.");
                    lines.Add("PASS " + name);
                }
                catch (Exception error) { lines.Add("FAIL " + name + ": " + error); }
                finally { if (doc != null) doc.Modified = false; }
            }
        }

        private static JObject Request(RhinoDoc doc, string action, string id, Guid layout = default(Guid)) =>
            new JObject { ["type"] = "drawing_sheet", ["action"] = action, ["expected_model_path"] = doc.Path,
                ["sheet_id"] = id, ["layout_id"] = layout == Guid.Empty ? "" : layout.ToString("D"),
                ["title"] = "Sheet A3", ["drawing_type"] = "plan", ["scale_denominator"] = 100.0,
                ["paper_mm"] = new JArray(420.0, 297.0), ["model_bounds_mm"] = new JArray(10000, 20000, 0, 30000, 30000, 0),
                ["scene_ids"] = new JArray("scene-example"), ["component_ids"] = new JArray("component-example"), ["plan_id"] = JValue.CreateNull() };

        private static JObject Success(JObject result)
        {
            Check((string)result["status"] == "success", result.ToString());
            return (JObject)result["sheet"];
        }
        private static void Rejected(JObject result) => Check((string)result["status"] == "error" &&
            (bool?)result["mutation_applied"] == false, result.ToString());
        private static bool Near(double first, double second) => Math.Abs(first - second) <= Math.Max(1e-9, Math.Abs(second) * 1e-8);
        private static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        private static void UndoRedo(RhinoDoc doc, bool redo)
        {
            Check(!doc.UndoRecordingIsActive, "Record active before Sheet Undo/Redo.");
            uint next = doc.NextUndoRecordSerialNumber;
            try { Check(redo ? doc.Redo() : doc.Undo(), "Sheet Undo/Redo failed."); }
            finally
            {
                if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == next)
                    Check(doc.EndUndoRecord(next), "Could not close Sheet Undo/Redo record.");
            }
        }
    }
}
