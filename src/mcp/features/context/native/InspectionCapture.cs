using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
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
    // Fixed UI-thread observation. Detached viewports only; no document visibility or selection edits.
    public static class InspectionCapture
    {
        const int MaxPixels = 16 * 1024 * 1024;
        const int HeaderHeight = 28;
        static readonly HashSet<string> Directions = new HashSet<string> {
            "current", "top", "bottom", "front", "back", "left", "right",
            "iso_ne", "iso_nw", "iso_se", "iso_sw", "below_ne", "below_nw", "below_se", "below_sw"
        };

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            try
            {
                if (request == null) throw new ArgumentException("A capture request is required.");
                ObjectObservation.ValidateDocument(doc, request);
                if ((string)request["type"] != "capture_rhino_inspection" ||
                    request.Properties().Any(p => !new[] { "type", "expected_model_path", "views", "width", "height", "columns" }.Contains(p.Name)))
                    throw new ArgumentException("Unsupported inspection capture fields.");
                var views = request["views"] as JArray;
                if (views == null || views.Count < 1 || views.Count > 16)
                    throw new ArgumentException("views must contain 1..16 explicitly chosen tiles.");
                int width = Integer(request, "width", 640, 128, 2048);
                int height = Integer(request, "height", 480, 128, 2048);
                int columns = Integer(request, "columns", (int)Math.Ceiling(Math.Sqrt(views.Count)), 1, views.Count);
                int rows = (views.Count + columns - 1) / columns;
                if ((long)width * columns * height * rows > MaxPixels)
                    throw new ArgumentException("The contact sheet exceeds 16 megapixels; reduce tile dimensions.");
                foreach (var token in views)
                {
                    var tile = token as JObject;
                    if (tile == null || tile.Properties().Any(p => !new[] { "object_ids", "direction", "display_mode", "label" }.Contains(p.Name)))
                        throw new ArgumentException("Each tile accepts object_ids, direction, display_mode and label.");
                    ObjectObservation.ReadIds(tile["object_ids"], 512, false);
                    if (!Directions.Contains(Text(tile, "direction", "current", 32)))
                        throw new ArgumentException("Unknown capture direction.");
                    Text(tile, "display_mode", "", 512);
                    Text(tile, "label", "", 120);
                }
                if (doc.IsHeadless || doc.Views.ActiveView == null)
                    return Error("no_viewport", "A live model viewport is required.");
                if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                    return Error("document_mismatch", "The requested document is not active.");
                var source = doc.Views.ActiveView;
                if (source is RhinoPageView)
                    return Error("layout_not_supported", "Inspection sheets use the active model viewport; use the Layout capture tool for paper.");
                var editor = EditingContext.Observe(doc);
                if ((string)editor["mode"] != "model" || (bool?)editor["stable"] != true)
                    return Error("editing_context_unverified", "Detached inspection requires a verified model editing context; group/block editing is unsupported.");
                var baseline = ObjectObservation.VisibleObjects(doc);
                var baselineIds = new HashSet<Guid>(baseline.Select(o => o.Id));
                var beforeView = ViewState(source.ActiveViewport);
                var beforeSelection = Selected(doc);
                bool beforeModified = doc.Modified;
                var tiles = new JArray();
                int captured = 0;
                using (var sheet = new Bitmap(width * columns, height * rows, PixelFormat.Format24bppRgb))
                using (var graphics = Graphics.FromImage(sheet))
                {
                    graphics.Clear(Color.White);
                    for (int index = 0; index < views.Count; index++)
                    {
                        var tileRequest = (JObject)views[index];
                        var rectangle = new Rectangle(index % columns * width, index / columns * height, width, height);
                        var tile = new JObject { ["index"] = index, ["direction"] = (string)tileRequest["direction"] ?? "current",
                            ["label"] = (string)tileRequest["label"] ?? "", ["rectangle"] = new JArray(rectangle.X, rectangle.Y, width, height) };
                        tiles.Add(tile);
                        try
                        {
                            var requested = ObjectObservation.ReadIds(tileRequest["object_ids"], 512, false);
                            bool explicitFilter = requested.Length != 0;
                            var filter = new HashSet<Guid>(requested);
                            var objects = explicitFilter ? baseline.Where(o => filter.Contains(o.Id)).ToArray() : baseline;
                            var actualIds = new HashSet<Guid>(objects.Select(o => o.Id));
                            var excluded = requested.Where(id => !actualIds.Contains(id)).ToArray();
                            tile["scope"] = new JObject {
                                ["kind"] = explicitFilter ? "explicit_ids_within_document_visible" : "document_visible_baseline",
                                ["filter_ids"] = new JArray(requested.Select(id => id.ToString())),
                                ["eligible_count"] = objects.Length,
                                ["eligible_object_ids"] = new JArray(objects.Take(512).Select(o => o.Id.ToString())),
                                ["eligible_ids_truncated"] = objects.Length > 512,
                                ["excluded_requested_ids"] = new JArray(excluded.Select(id => id.ToString())),
                                ["group_expansion"] = false, ["block_definition_filtering"] = "unsupported",
                                ["visibility_evidence"] = "document visibility eligibility, not frustum, occlusion or pixel visibility",
                                ["complete"] = excluded.Length == 0
                            };
                            if (excluded.Length != 0)
                                throw new CaptureException("scope_unavailable", "Some requested IDs are hidden, missing, or not top-level model objects; the tile was not rendered.");
                            if (objects.Length == 0)
                                throw new CaptureException("empty_scope", "The chosen scope has no document-visible model objects.");
                            if (explicitFilter && objects.Any(o => o is InstanceObject))
                                throw new CaptureException("unsupported_block_filter", "Explicit block occurrence filtering is unsupported; no definition/member expansion was performed.");
                            string modeName = (string)tileRequest["display_mode"] ?? "";
                            var mode = modeName.Length == 0 ? source.ActiveViewport.DisplayMode : DocumentObservation.ResolveDisplayMode(modeName);
                            if (mode == null)
                                throw new CaptureException("display_mode_not_found", "The display mode is missing or ambiguous; provide an installed mode GUID.");
                            if (mode.DisplayAttributes.RealtimeDisplayId != Guid.Empty)
                                throw new CaptureException("unsupported_display_mode", "Realtime display modes are unsupported by detached inspection capture.");
                            tile["display_mode"] = new JObject { ["name"] = mode.EnglishName, ["id"] = mode.Id.ToString() };
                            var bounds = BoundingBox.Empty;
                            foreach (var obj in objects) bounds.Union(obj.Geometry.GetBoundingBox(true));
                            if (!bounds.IsValid)
                                throw new CaptureException("invalid_bounds", "The scope has no frameable bounds.");
                            using (var bitmap = Capture(doc, source.ActiveViewport, objects, bounds, (string)tile["direction"],
                                mode, new Size(width, height - HeaderHeight), explicitFilter, tile))
                                graphics.DrawImageUnscaled(bitmap, rectangle.X, rectangle.Y + HeaderHeight);
                            tile["status"] = "success";
                            captured++;
                        }
                        catch (CaptureException ex) { TileError(tile, ex.Code, ex.Message); }
                        catch (Exception ex) { TileError(tile, "capture_failed", ex.Message); }
                        DrawCaption(graphics, rectangle, tile);
                    }
                    ObjectObservation.ValidateDocument(doc, request);
                    if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber ||
                        doc.Views.ActiveView?.RuntimeSerialNumber != source.RuntimeSerialNumber ||
                        !JToken.DeepEquals(beforeView, ViewState(source.ActiveViewport)) ||
                        !beforeSelection.SetEquals(Selected(doc)) || doc.Modified != beforeModified ||
                        !baselineIds.SetEquals(ObjectObservation.VisibleObjects(doc).Select(o => o.Id)))
                        return Error("observation_state_changed", "Document, camera, selection or visibility changed during capture; no image was returned.", tiles);
                    if (captured == 0)
                        return Error("all_tiles_failed", "No requested inspection tile could be captured.", tiles);
                    using (var stream = new MemoryStream())
                    {
                        sheet.Save(stream, ImageFormat.Png);
                        if (stream.Length == 0 || stream.Length > DocumentObservation.MaxImageBytes)
                            return Error("image_too_large", "The contact-sheet PNG exceeds 4 MiB; reduce tile dimensions or the number of tiles.", tiles);
                        var result = new JObject {
                            ["status"] = "success", ["schema"] = "almond-inspection-capture/v1", ["complete"] = captured == views.Count,
                            ["columns"] = columns, ["rows"] = rows, ["tiles"] = tiles,
                            ["baseline"] = new JObject { ["document_path"] = doc.Path, ["viewport_id"] = source.ActiveViewport.Id.ToString(),
                                ["document_visible_count"] = baseline.Length, ["live_state_preserved"] = true },
                            ["limitations"] = new JArray("Scopes describe document-visible eligible objects, not proof that every object produced visible pixels.",
                                "Groups never expand the supplied object IDs. Explicit block occurrence/definition filtering is unsupported.",
                                "Existing non-object display conduits may draw overlays; clipping participation belongs to the detached viewport.",
                                "Captures do not establish geometric or architectural correctness.")
                        };
                        if (Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) > 512 * 1024)
                            return Error("metadata_too_large", "Capture metadata exceeds 512 KiB; narrow the scopes.");
                        result["image"] = new JObject { ["mime_type"] = "image/png", ["data"] = Convert.ToBase64String(stream.ToArray()),
                            ["width"] = sheet.Width, ["height"] = sheet.Height };
                        return result;
                    }
                }
            }
            catch (ArgumentException ex) { return Error("invalid_arguments", ex.Message); }
            catch (InvalidOperationException ex) { return Error("document_mismatch", ex.Message); }
            catch (Exception ex) { return Error("inspection_capture_failed", ex.Message); }
        }

        static Bitmap Capture(RhinoDoc doc, RhinoViewport source, RhinoObject[] objects, BoundingBox bounds,
            string direction, DisplayModeDescription mode, Size size, bool explicitFilter, JObject metadata)
        {
            using (var control = new DocumentObservation.CaptureViewportControl { Visible = false, Size = size })
            {
                var handle = control.Handle;
                var viewport = control.Viewport;
                using (var projection = new ViewportInfo(source))
                    if (!viewport.SetViewProjection(projection, true))
                        throw new InvalidOperationException("Could not copy the source camera to the detached viewport.");
                viewport.DisplayMode = mode;
                if (direction != "current")
                {
                    viewport.ChangeToParallelProjection(true);
                    var offset = Direction(direction);
                    offset.Unitize();
                    viewport.SetCameraLocations(bounds.Center, bounds.Center + offset * Math.Max(bounds.Diagonal.Length * 3.0, 1.0));
                    viewport.CameraUp = direction == "top" || direction == "bottom" ? Vector3d.YAxis : Vector3d.ZAxis;
                    bounds.Inflate(Math.Max(bounds.Diagonal.Length * .025, doc.ModelAbsoluteTolerance));
                    if (!viewport.ZoomBoundingBox(bounds))
                        throw new InvalidOperationException("Could not frame the chosen scope.");
                }
                metadata["camera"] = ViewState(viewport);
                var conduit = new ScopeConduit(doc.RuntimeSerialNumber, viewport.Id, objects.Select(o => o.Id), explicitFilter);
                DisplayPipeline pipeline = null;
                try
                {
                    conduit.Enabled = true;
                    control.InitializeCapturePipeline();
                    pipeline = control.Display;
                    if (pipeline == null || (!pipeline.IsOpen && !pipeline.Open()))
                        throw new InvalidOperationException("Could not initialize the detached capture pipeline.");
                    // Initialization paints do not prove that the exported bitmap used this scope.
                    conduit.ResetCounters();
                    var bitmap = DisplayPipeline.DrawToBitmap(viewport, size.Width, size.Height);
                    if (bitmap == null || bitmap.Width != size.Width || bitmap.Height != size.Height)
                    {
                        bitmap?.Dispose();
                        throw new InvalidOperationException("Rhino did not return the requested bitmap dimensions.");
                    }
                    if (conduit.Observed == 0)
                    {
                        bitmap.Dispose();
                        throw new CaptureException("scope_filter_unverified", "No scoped culling callback was observed; no unverified image was returned.");
                    }
                    metadata["scope"]["culling_candidates_observed"] = conduit.Observed;
                    metadata["scope"]["culling_candidates_excluded"] = conduit.Excluded;
                    return bitmap;
                }
                finally
                {
                    conduit.Enabled = false;
                    if (pipeline != null) pipeline.Close();
                }
            }
        }

        sealed class ScopeConduit : DisplayConduit
        {
            readonly uint documentSerial;
            readonly Guid viewportId;
            readonly HashSet<Guid> ids;
            readonly bool explicitFilter;
            public int Observed { get; private set; }
            public int Excluded { get; private set; }
            public ScopeConduit(uint serial, Guid viewport, IEnumerable<Guid> objects, bool explicitIds)
            { documentSerial = serial; viewportId = viewport; ids = new HashSet<Guid>(objects); explicitFilter = explicitIds; }
            public void ResetCounters() { Observed = 0; Excluded = 0; }
            protected override void ObjectCulling(CullObjectEventArgs e)
            {
                if (e.RhinoDoc == null || e.RhinoDoc.RuntimeSerialNumber != documentSerial || e.Viewport.Id != viewportId) return;
                var obj = e.RhinoObject;
                if (obj == null) return;
                Observed++;
                // Let Rhino render whole block occurrences only for an unfiltered visible baseline.
                bool keep = obj.IsInstanceDefinitionGeometry ? !explicitFilter : ids.Contains(obj.Id);
                if (!keep) { e.CullObject = true; Excluded++; }
            }
        }

        static Vector3d Direction(string value)
        {
            switch (value)
            {
                case "top": return new Vector3d(0, 0, 1);
                case "bottom": return new Vector3d(0, 0, -1);
                case "front": return new Vector3d(0, -1, 0);
                case "back": return new Vector3d(0, 1, 0);
                case "left": return new Vector3d(-1, 0, 0);
                case "right": return new Vector3d(1, 0, 0);
                default: return new Vector3d(value.EndsWith("ne") || value.EndsWith("se") ? 1 : -1,
                    value.EndsWith("ne") || value.EndsWith("nw") ? 1 : -1, value.StartsWith("below_") ? -1 : 1);
            }
        }

        static JObject ViewState(RhinoViewport viewport)
        {
            return new JObject { ["id"] = viewport.Id.ToString(), ["camera"] = Point(viewport.CameraLocation),
                ["target"] = Point(viewport.CameraTarget), ["up"] = Point((Point3d)viewport.CameraUp),
                ["direction"] = Point((Point3d)viewport.CameraDirection), ["lens"] = viewport.Camera35mmLensLength,
                ["projection"] = viewport.IsParallelProjection ? "parallel" : viewport.IsTwoPointPerspectiveProjection ? "two_point" : "perspective",
                ["display_mode_id"] = viewport.DisplayMode.Id.ToString(), ["size"] = new JArray(viewport.Size.Width, viewport.Size.Height) };
        }
        static JArray Point(Point3d p) => new JArray(p.X, p.Y, p.Z);
        static HashSet<Guid> Selected(RhinoDoc doc) => new HashSet<Guid>(doc.Objects.GetSelectedObjects(false, false).Select(o => o.Id));
        static string Text(JObject value, string key, string fallback, int maximum)
        {
            var token = value[key];
            if (token == null) return fallback;
            if (token.Type != JTokenType.String || ((string)token).Length > maximum)
                throw new ArgumentException(key + " must be a string of at most " + maximum + " characters.");
            return (string)token;
        }
        static int Integer(JObject value, string key, int fallback, int minimum, int maximum)
        {
            var token = value[key];
            if (token == null) return fallback;
            if (token.Type != JTokenType.Integer || (long)token < minimum || (long)token > maximum)
                throw new ArgumentException(key + " must be an integer from " + minimum + " through " + maximum + ".");
            return (int)token;
        }
        static void DrawCaption(Graphics graphics, Rectangle rectangle, JObject tile)
        {
            bool ok = (string)tile["status"] == "success";
            string caption = ((int)tile["index"] + 1) + ". " + ((string)tile["label"] == "" ? (string)tile["direction"] : (string)tile["label"]);
            if (!ok) caption += " | " + (string)tile["error_code"];
            using (var background = new SolidBrush(ok ? Color.FromArgb(238, 242, 246) : Color.FromArgb(255, 229, 229)))
                graphics.FillRectangle(background, rectangle.X, rectangle.Y, rectangle.Width, HeaderHeight);
            using (var format = new StringFormat { Trimming = StringTrimming.EllipsisCharacter, FormatFlags = StringFormatFlags.NoWrap, LineAlignment = StringAlignment.Center })
                graphics.DrawString(caption, SystemFonts.MessageBoxFont, Brushes.Black,
                    new RectangleF(rectangle.X + 6, rectangle.Y, rectangle.Width - 12, HeaderHeight), format);
            graphics.DrawRectangle(Pens.LightGray, rectangle.X, rectangle.Y, rectangle.Width - 1, rectangle.Height - 1);
        }
        static void TileError(JObject tile, string code, string message)
        { tile["status"] = "error"; tile["error_code"] = code; tile["message"] = message; }
        static JObject Error(string code, string message, JArray tiles = null)
        {
            var result = new JObject { ["status"] = "error", ["error_code"] = code, ["message"] = message };
            if (tiles != null) result["tiles"] = tiles;
            return result;
        }
        sealed class CaptureException : Exception
        {
            public string Code { get; }
            public CaptureException(string code, string message) : base(message) { Code = code; }
        }
    }
}
