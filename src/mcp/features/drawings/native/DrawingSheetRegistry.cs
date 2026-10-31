using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    /// <summary>One registered layout/detail for an already authored model-space XY drawing.</summary>
    public static class DrawingSheetRegistry
    {
        private const int MaxBytes = 2097152;
        private const double MarginMm = 10;
        private static string IdKey => ModelingMetadata.Key("sheet_id");
        private static string MetadataKey => ModelingMetadata.Key("sheet_metadata");

        private sealed class Binding
        {
            internal RhinoPageView Page;
            internal Guid DetailId;
            internal Guid LayoutId;
        }

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool mutationStarted = false, createdPage = false;
            Binding binding = null;
            RhinoView previousView = null;
            string oldTitle = null;
            double oldWidth = 0, oldHeight = 0;
            string sheetId = "";
            try
            {
                CheckDocument(doc, request);
                string action = Text(request, "action");
                if (action != "upsert" && action != "inspect" && action != "unregister")
                    throw new ArgumentException("Unsupported drawing Sheet action.");
                sheetId = Text(request, "sheet_id");
                binding = Find(doc, sheetId, Text(request, "layout_id", false));
                if (action == "inspect")
                {
                    if (binding == null) throw new ArgumentException("The registered Sheet layout is missing.");
                    return Success(Snapshot(doc, binding, sheetId));
                }

                JObject prior = binding == null ? null : Metadata(doc, binding, sheetId);
                if (action == "unregister")
                {
                    if (binding == null) throw new ArgumentException("The registered Sheet layout is missing.");
                    if ((string)prior["registration_status"] == "unregistered")
                        return UnregisterAcknowledgement(Snapshot(doc, binding, sheetId));
                    var tombstone = (JObject)prior.DeepClone();
                    tombstone["registration_status"] = "unregistered";
                    tombstone["scene_ids"] = new JArray();
                    tombstone["component_ids"] = new JArray();
                    tombstone["plan_id"] = "";
                    JObject observed = null;
                    var removed = new ScriptExecutor().ExecuteAction(doc, () =>
                    {
                        mutationStarted = true;
                        Stamp(doc, binding, sheetId, tombstone);
                        observed = UnregisterAcknowledgement(Snapshot(doc, binding, sheetId));
                        return null;
                    });
                    if (removed.Status != "success") throw new InvalidOperationException(removed.Message);
                    return observed;
                }

                JObject desired = Settings(request, doc);
                string title = (string)desired["title"];
                if (Pages(doc).Any(page => (binding == null || page.MainViewport.Id != binding.LayoutId) &&
                    String.Equals(page.PageName, title, StringComparison.OrdinalIgnoreCase)))
                    throw new ArgumentException("Another layout already uses this title; choose a distinct Sheet title.");
                previousView = doc.Views.ActiveView;
                if (binding != null)
                {
                    oldTitle = binding.Page.PageName;
                    oldWidth = binding.Page.PageWidth;
                    oldHeight = binding.Page.PageHeight;
                }
                JObject response = null;
                var updated = new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    mutationStarted = true;
                    var paper = desired["paper_mm"].Values<double>().ToArray();
                    double pageMm = UnitMm(doc.PageUnitSystem);
                    if (binding == null)
                    {
                        var page = doc.Views.AddPageView(title, paper[0] / pageMm, paper[1] / pageMm);
                        if (page == null) throw new InvalidOperationException("Rhino could not create the Sheet layout.");
                        binding = new Binding { Page = page, LayoutId = page.MainViewport.Id };
                        createdPage = true;
                        var detail = page.AddDetailView("Sheet drawing", new Point2d(MarginMm / pageMm, MarginMm / pageMm),
                            new Point2d((paper[0] - MarginMm) / pageMm, (paper[1] - MarginMm) / pageMm), DefinedViewportProjection.Top);
                        if (detail == null) throw new InvalidOperationException("Rhino could not create the Sheet detail.");
                        binding.DetailId = detail.Id;
                    }
                    else
                    {
                        binding.Page.PageName = title;
                        binding.Page.PageWidth = paper[0] / pageMm;
                        binding.Page.PageHeight = paper[1] / pageMm;
                    }
                    ConfigureDetail(doc, binding, desired);
                    desired["sheet_id"] = sheetId;
                    desired["layout_id"] = binding.LayoutId.ToString("D");
                    desired["detail_id"] = binding.DetailId.ToString("D");
                    desired["model_path"] = doc.Path;
                    desired["registration_status"] = "registered";
                    Stamp(doc, binding, sheetId, desired);
                    // Both geometry observation and response bounds remain inside our Undo record.
                    response = Success(Snapshot(doc, binding, sheetId));
                    return null;
                });
                if (updated.Status != "success") throw new InvalidOperationException(updated.Message);
                return response;
            }
            catch (Exception error)
            {
                string recoveryError = "";
                if (mutationStarted && binding != null)
                {
                    try
                    {
                        // View-table properties need explicit compensation; they are not object Undo data.
                        var page = Pages(doc).FirstOrDefault(p => p.MainViewport.Id == binding.LayoutId);
                        if (page != null && createdPage)
                        {
                            var settings = new ObjectEnumeratorSettings { NormalObjects = true, HiddenObjects = true,
                                LockedObjects = true, ReferenceObjects = true, IdefObjects = false, DeletedObjects = false };
                            if (doc.Objects.GetObjectList(settings).Any(o => o.Attributes.Space == ActiveSpace.PageSpace &&
                                o.Attributes.ViewportId == binding.LayoutId && o.Id != binding.DetailId))
                                throw new InvalidOperationException("The new layout contains other objects and was preserved.");
                            if (!page.Close()) throw new InvalidOperationException("The new layout could not be closed.");
                        }
                        else if (page != null && oldTitle != null)
                        {
                            page.PageName = oldTitle;
                            page.PageWidth = oldWidth;
                            page.PageHeight = oldHeight;
                        }
                    }
                    catch (Exception recovery) { recoveryError = " Layout recovery: " + recovery.Message; }
                }
                return new JObject { ["status"] = "error", ["error_code"] = "drawing_sheet_error",
                    ["message"] = error.Message + recoveryError, ["sheet_id"] = sheetId,
                    ["layout_id"] = binding?.LayoutId.ToString("D") ?? "",
                    ["mutation_applied"] = mutationStarted ? JValue.CreateNull() : new JValue(false),
                    ["requires_reconciliation"] = mutationStarted };
            }
            finally
            {
                // AddPageView activates the page on Rhino 8 Windows; preserve the caller's current view.
                if (previousView != null)
                {
                    try { doc.Views.ActiveView = previousView; }
                    catch (Exception error) { RhinoApp.WriteLine("Sheet view restoration: " + error.Message); }
                }
            }
        }

        private static RhinoPageView[] Pages(RhinoDoc doc) => doc.Views.GetPageViews() ?? new RhinoPageView[0];

        private static Binding Find(RhinoDoc doc, string sheetId, string layoutText)
        {
            Guid layoutId = String.IsNullOrEmpty(layoutText) ? Guid.Empty : Guid.Parse(layoutText);
            if (!String.IsNullOrEmpty(layoutText) && layoutId == Guid.Empty)
                throw new ArgumentException("layout_id must be a nonempty GUID.");
            var pages = Pages(doc);
            var matches = (from page in pages from detail in page.GetDetailViews()
                           where detail.Attributes.GetUserString(IdKey) == sheetId
                           select new Binding { Page = page, DetailId = detail.Id, LayoutId = page.MainViewport.Id }).ToArray();
            if (matches.Length > 1) throw new ArgumentException("Several details carry this Sheet ID; explicitly repair copied registration metadata.");
            var match = matches.SingleOrDefault();
            if (layoutId != Guid.Empty && (match == null || match.LayoutId != layoutId))
                throw new ArgumentException("Sheet ID and the existing layout GUID do not match. A missing layout is not recreated automatically.");
            if (match != null && match.Page.GetDetailViews().Any(d => d.Id != match.DetailId &&
                !String.IsNullOrEmpty(d.Attributes.GetUserString(IdKey))))
                throw new ArgumentException("The layout has more than one registered Sheet detail.");
            return match;
        }

        private static DetailViewObject Detail(RhinoDoc doc, Binding binding)
        {
            var detail = doc.Objects.FindId(binding.DetailId) as DetailViewObject;
            if (detail == null || detail.IsDeleted || detail.IsReference ||
                !binding.Page.GetDetailViews().Any(d => d.Id == binding.DetailId))
                throw new ArgumentException("The Sheet's editable detail is missing from its layout.");
            return detail;
        }

        private static JObject Metadata(RhinoDoc doc, Binding binding, string sheetId)
        {
            var detail = Detail(doc, binding);
            var value = JObject.Parse(detail.Attributes.GetUserString(MetadataKey) ?? "{}");
            if (detail.Attributes.GetUserString(IdKey) != sheetId || Text(value, "sheet_id") != sheetId ||
                Guid.Parse(Text(value, "layout_id")) != binding.LayoutId ||
                Guid.Parse(Text(value, "detail_id")) != binding.DetailId ||
                !SamePath(Text(value, "model_path"), doc.Path))
                throw new ArgumentException("Sheet metadata and live document/layout/detail identity disagree.");
            string state = Text(value, "registration_status");
            if (state != "registered" && state != "unregistered")
                throw new ArgumentException("Invalid Sheet registration status.");
            return value;
        }

        private static void Stamp(RhinoDoc doc, Binding binding, string sheetId, JObject metadata)
        {
            var attributes = Detail(doc, binding).Attributes.Duplicate();
            if (!attributes.SetUserString(IdKey, sheetId) ||
                !attributes.SetUserString(MetadataKey, metadata.ToString(Formatting.None)) ||
                !doc.Objects.ModifyAttributes(binding.DetailId, attributes, true))
                throw new InvalidOperationException("Could not commit Sheet registration metadata.");
        }

        private static void ConfigureDetail(RhinoDoc doc, Binding binding, JObject desired)
        {
            double modelMm = UnitMm(doc.ModelUnitSystem), pageMm = UnitMm(doc.PageUnitSystem);
            double[] paper = desired["paper_mm"].Values<double>().ToArray();
            double[] bounds = desired["model_bounds_mm"].Values<double>().ToArray();
            var detail = Detail(doc, binding);
            var geometry = detail.DetailGeometry;
            bool wasLocked = geometry.IsProjectionLocked;
            geometry.IsProjectionLocked = false;
            var oldBox = geometry.GetBoundingBox(true);
            if (!oldBox.IsValid || oldBox.Max.X <= oldBox.Min.X || oldBox.Max.Y <= oldBox.Min.Y)
                throw new ArgumentException("Sheet detail has no valid paper boundary.");
            var anchor = new Plane(oldBox.Min, Vector3d.ZAxis);
            var size = Transform.Scale(anchor, (paper[0] - 2 * MarginMm) / pageMm / (oldBox.Max.X - oldBox.Min.X),
                (paper[1] - 2 * MarginMm) / pageMm / (oldBox.Max.Y - oldBox.Min.Y), 1);
            var move = Transform.Translation(MarginMm / pageMm - oldBox.Min.X, MarginMm / pageMm - oldBox.Min.Y, -oldBox.Min.Z);
            bool resize = !Near(oldBox.Min.X * pageMm, MarginMm) || !Near(oldBox.Min.Y * pageMm, MarginMm) ||
                !Near(oldBox.Max.X * pageMm, paper[0] - MarginMm) || !Near(oldBox.Max.Y * pageMm, paper[1] - MarginMm) ||
                !Near(oldBox.Min.Z * pageMm, 0);
            if ((resize && !geometry.Transform(move * size)) || ((resize || wasLocked) && !detail.CommitChanges()))
                throw new InvalidOperationException("Could not resize the Sheet detail.");
            detail = Detail(doc, binding);
            var region = new BoundingBox(bounds[0] / modelMm, bounds[1] / modelMm, bounds[2] / modelMm,
                bounds[3] / modelMm, bounds[4] / modelMm, bounds[5] / modelMm);
            if (!detail.Viewport.SetProjection(DefinedViewportProjection.Top, "Sheet drawing", false) ||
                !detail.Viewport.ZoomBoundingBox(region))
                throw new InvalidOperationException("Could not frame the drawing's XY region.");
            detail.Viewport.SetCameraTarget(region.Center, true);
            if (!detail.CommitViewportChanges()) throw new InvalidOperationException("Could not commit the Sheet camera.");
            detail = Detail(doc, binding);
            if (!detail.DetailGeometry.SetScale((double)desired["scale_denominator"] / modelMm,
                doc.ModelUnitSystem, 1 / pageMm, doc.PageUnitSystem))
                throw new InvalidOperationException("Could not set the requested physical drawing scale.");
            detail.DetailGeometry.IsProjectionLocked = true;
            if (!detail.CommitChanges()) throw new InvalidOperationException("Could not commit the Sheet scale.");
        }

        private static JObject Snapshot(RhinoDoc doc, Binding binding, string sheetId)
        {
            var value = Metadata(doc, binding, sheetId);
            if ((string)value["registration_status"] == "unregistered")
                return new JObject { ["sheet_id"] = sheetId, ["layout_id"] = binding.LayoutId.ToString("D"),
                    ["detail_id"] = binding.DetailId.ToString("D"), ["model_path"] = doc.Path,
                    ["registration_status"] = "unregistered", ["complete"] = true, ["live_verified"] = true };
            var detail = Detail(doc, binding);
            double modelMm = UnitMm(doc.ModelUnitSystem), pageMm = UnitMm(doc.PageUnitSystem);
            double ratio = detail.DetailGeometry.PageToModelRatio;
            var direction = detail.Viewport.CameraDirection;
            var up = detail.Viewport.CameraUp;
            if (!detail.DetailGeometry.IsParallelProjection || !Double.IsFinite(ratio) || ratio <= 0 ||
                !direction.Unitize() || !up.Unitize() || direction * -Vector3d.ZAxis < 1 - 1e-8 ||
                up * Vector3d.YAxis < 1 - 1e-8)
                throw new ArgumentException("The Sheet detail must use a parallel Top view.");
            value["title"] = binding.Page.PageName;
            value["paper_mm"] = new JArray(binding.Page.PageWidth * pageMm, binding.Page.PageHeight * pageMm);
            value["scale_denominator"] = 1 / ratio;
            var normalized = Settings(value, doc);
            double[] bounds = normalized["model_bounds_mm"].Values<double>().ToArray();
            var center = new Point3d((bounds[0] + bounds[3]) / (2 * modelMm),
                (bounds[1] + bounds[4]) / (2 * modelMm), (bounds[2] + bounds[5]) / (2 * modelMm));
            if (detail.Viewport.CameraTarget.DistanceTo(center) * modelMm > 0.001)
                throw new ArgumentException("Sheet detail center differs from its recorded drawing region; explicitly upsert the intended model_bounds_mm.");
            var frame = detail.DetailGeometry.GetBoundingBox(true);
            double left, right, bottom, top, near, far;
            if (!frame.IsValid || !Near(frame.Min.X * pageMm, MarginMm) || !Near(frame.Min.Y * pageMm, MarginMm) ||
                !Near(frame.Max.X * pageMm, binding.Page.PageWidth * pageMm - MarginMm) ||
                !Near(frame.Max.Y * pageMm, binding.Page.PageHeight * pageMm - MarginMm) ||
                !detail.Viewport.GetFrustum(out left, out right, out bottom, out top, out near, out far) ||
                !Near((right - left) * modelMm * ratio, (frame.Max.X - frame.Min.X) * pageMm) ||
                !Near((top - bottom) * modelMm * ratio, (frame.Max.Y - frame.Min.Y) * pageMm))
                throw new ArgumentException("Sheet viewport framing and physical scale disagree.");
            foreach (var item in normalized) value[item.Key] = item.Value;
            value["model_path"] = doc.Path;
            value["complete"] = true;
            value["live_verified"] = true;
            value["layout_undo_supported"] = false;
            value["margin_mm"] = MarginMm;
            return value;
        }

        private static bool Near(double a, double b) => Math.Abs(a - b) <= Math.Max(0.001, Math.Abs(b) * 1e-6);

        private static JObject Settings(JObject input, RhinoDoc doc)
        {
            string title = Text(input, "title"), kind = Text(input, "drawing_type");
            double scale = Number(input["scale_denominator"], "scale_denominator");
            double[] paper = Numbers(input, "paper_mm", 2), bounds = Numbers(input, "model_bounds_mm", 6);
            if (scale <= 0 || paper.Any(v => v <= 2 * MarginMm))
                throw new ArgumentException("Scale must be positive and paper must leave a 10 mm inset on each side.");
            if (bounds[3] <= bounds[0] || bounds[4] <= bounds[1] || bounds[5] < bounds[2] ||
                Math.Abs(bounds[5] - bounds[2]) > Math.Max(1e-6, doc.ModelAbsoluteTolerance * UnitMm(doc.ModelUnitSystem)))
                throw new ArgumentException("Use a nonempty authored 2D drawing region parallel to world XY; no 3D projection is generated.");
            if ((bounds[3] - bounds[0]) / scale > paper[0] - 2 * MarginMm + 1e-6 ||
                (bounds[4] - bounds[1]) / scale > paper[1] - 2 * MarginMm + 1e-6)
                throw new ArgumentException("The drawing region does not fit the paper at the requested scale and 10 mm inset.");
            if (paper.Any(v => !Double.IsFinite(v / UnitMm(doc.PageUnitSystem))) ||
                bounds.Any(v => !Double.IsFinite(v / UnitMm(doc.ModelUnitSystem))))
                throw new ArgumentException("Sheet dimensions exceed the document's coordinate range.");
            return new JObject { ["title"] = title, ["drawing_type"] = kind, ["scale_denominator"] = scale,
                ["paper_mm"] = new JArray(paper), ["model_bounds_mm"] = new JArray(bounds),
                ["scene_ids"] = Strings(input, "scene_ids"), ["component_ids"] = Strings(input, "component_ids"),
                ["plan_id"] = input["plan_id"]?.Type == JTokenType.Null ? "" : Text(input, "plan_id", false) };
        }

        private static JArray Strings(JObject input, string name)
        {
            var value = input[name] as JArray;
            if (value == null || value.Count > 4096 || value.Any(v => v.Type != JTokenType.String ||
                String.IsNullOrWhiteSpace((string)v) || ((string)v).Length > 160) ||
                value.Values<string>().Distinct(StringComparer.Ordinal).Count() != value.Count)
                throw new ArgumentException(name + " must be a bounded list of distinct identifiers.");
            return (JArray)value.DeepClone();
        }

        private static double[] Numbers(JObject input, string name, int count)
        {
            var value = input[name] as JArray;
            if (value == null || value.Count != count) throw new ArgumentException(name + " has an invalid length.");
            return value.Select(v => Number(v, name)).ToArray();
        }

        private static double Number(JToken token, string name)
        {
            if (token == null || (token.Type != JTokenType.Float && token.Type != JTokenType.Integer))
                throw new ArgumentException(name + " must contain numbers.");
            double value = (double)token;
            if (!Double.IsFinite(value)) throw new ArgumentException(name + " must be finite.");
            return value;
        }

        private static string Text(JObject input, string name, bool required = true)
        {
            var token = input[name];
            if (token == null && !required) return "";
            if (token?.Type != JTokenType.String) throw new ArgumentException(name + " must be a string.");
            string value = (string)token;
            if ((required && String.IsNullOrWhiteSpace(value)) || value.Length > 1024 || value.Any(c => c < 32))
                throw new ArgumentException(name + " is empty, too long or contains control characters.");
            return value;
        }

        private static double UnitMm(UnitSystem unit)
        {
            double scale = RhinoMath.UnitScale(unit, UnitSystem.Millimeters);
            if (unit == UnitSystem.None || unit == UnitSystem.CustomUnits || !Double.IsFinite(scale) || scale <= 0)
                throw new ArgumentException("Set supported model and page units before registering Sheets.");
            return scale;
        }

        private static bool SamePath(string first, string second) => Path.IsPathRooted(first) &&
            String.Equals(Path.GetFullPath(first), Path.GetFullPath(second), StringComparison.OrdinalIgnoreCase);

        private static void CheckDocument(RhinoDoc doc, JObject request)
        {
            if (doc == null || doc.IsHeadless) throw new ArgumentException("Sheets require a regular Rhino document with layout views.");
            if (request == null || Encoding.UTF8.GetByteCount(request.ToString(Formatting.None)) > MaxBytes)
                throw new ArgumentException("Missing or oversized Sheet request.");
            if (String.IsNullOrWhiteSpace(doc.Path) || !SamePath(Text(request, "expected_model_path"), doc.Path))
                throw new ArgumentException("The active saved document differs from expected_model_path.");
            UnitMm(doc.ModelUnitSystem);
            UnitMm(doc.PageUnitSystem);
        }

        private static JObject UnregisterAcknowledgement(JObject sheet) => new JObject
        {
            ["status"] = "success", ["sheet_id"] = (string)sheet["sheet_id"],
            ["model_path"] = (string)sheet["model_path"], ["layout_id"] = (string)sheet["layout_id"]
        };

        private static JObject Success(JObject sheet)
        {
            var result = new JObject { ["status"] = "success", ["sheet"] = sheet };
            if (Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) > MaxBytes)
                throw new ArgumentException("Sheet response exceeds 2 MiB.");
            return result;
        }
    }
}
