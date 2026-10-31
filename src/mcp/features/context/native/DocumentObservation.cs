using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    /// <summary>
    /// Fixed observations dispatched on Rhino's UI thread through the existing bridge.
    /// Does not execute scripts, open Undo records, change views, or create document data.
    /// </summary>
    public static class DocumentObservation
    {
        public const int MaxSelectionLimit = 200;
        public const int MaxImageBytes = 4 * 1024 * 1024;
        private const double LayoutDpi = 144.0;

        public static string HandleContext(JObject request)
        {
            int selectionLimit, depth;
            bool recursive, includeImage, selectionEntities;
            if (!ReadInteger(request, "selection_limit", 50, 0, MaxSelectionLimit, out selectionLimit) ||
                !ReadInteger(request, "depth", 1, 1, 8, out depth) ||
                !ReadBoolean(request, "recursive", false, out recursive) ||
                !ReadBoolean(request, "selection_entities", false, out selectionEntities) ||
                !ReadBoolean(request, "include_image", false, out includeImage))
                return Error("invalid_arguments", "Use selection_limit 0..200, depth 1..8 and boolean recursive/include_image.").ToString(Formatting.None);
            string[] sections = null;
            if (request["sections"] != null)
            {
                var requested = request["sections"] as JArray;
                if (requested == null || requested.Any(item => item.Type != JTokenType.String))
                    return Error("invalid_arguments", "sections must be an array of document, selection or viewport.").ToString(Formatting.None);
                sections = requested.Values<string>().ToArray();
            }
            return GetContext(RhinoDoc.ActiveDoc, selectionLimit, sections, recursive, depth, includeImage, selectionEntities).ToString(Formatting.None);
        }

        public static string HandleViewportImage(JObject request)
        {
            int scalePercent, depth;
            bool labels;
            if (!ReadInteger(request, "scale_percent", 75, 1, 100, out scalePercent) ||
                !ReadInteger(request, "depth", 1, 1, 8, out depth) ||
                !ReadBoolean(request, "labels", true, out labels) ||
                (request["view"] != null && request["view"].Type != JTokenType.String) ||
                new[] { "display_mode", "target_kind", "target_id" }.Any(key => request[key] != null && request[key].Type != JTokenType.String) ||
                request["max_width"] != null || request["max_height"] != null)
                return Error("invalid_arguments", "Use view (empty, 'a', or a GUID) and integer scale_percent from 1 through 100.").ToString(Formatting.None);
            return GetViewportImage(RhinoDoc.ActiveDoc, (string)request["view"] ?? "", scalePercent,
                (string)request["display_mode"] ?? "", labels, depth,
                (string)request["target_kind"] ?? "view", (string)request["target_id"] ?? "").ToString(Formatting.None);
        }

        /// <summary>
        /// Counts live normal, hidden, locked and reference objects, including lights;
        /// excludes deleted objects, instance-definition members and grips.
        /// Failed fields or sections are null and identified in warnings, never fake zeroes.
        /// </summary>
        public static JObject GetContext(RhinoDoc doc, int selectionLimit = 50, string[] sections = null,
            bool recursive = false, int depth = 1, bool includeImage = false, bool selectionEntities = false)
        {
            var requested = new HashSet<string>(sections ?? new[] { "document" });
            if (requested.Except(new[] { "document", "selection", "viewport", "editor", "display_modes" }).Any())
                return Error("invalid_arguments", "sections must contain document, selection, viewport, editor or display_modes.");
            if (selectionLimit < 0 || selectionLimit > MaxSelectionLimit || depth < 1 || depth > 8)
                return Error("invalid_arguments", "selection_limit must be 0..200 and depth 1..8.");
            if (doc == null)
                return Error("no_document", "No Rhino document is available.");

            var warnings = new JArray();
            var result = new JObject
            {
                ["status"] = "success",
                ["capabilities"] = new JObject { ["block_analysis"] = 1, ["modeling_materials"] = 2, ["design_components"] = 1, ["component_registry"] = 2,
                    ["component_operations"] = 1, ["drawing_asset_extract"] = 2, ["context_sections"] = 1, ["document_save"] = 1, ["editing_context"] = 1, ["capture_options"] = 1,
                    ["object_observation"] = 2, ["inspection_capture"] = 1, ["face_edit"] = 1,
                    ["face_edit_batch"] = 1, ["intersection_queries"] = 1, ["intersection_tools"] = 1,
                    ["drawing_asset_linked"] = 1 },
                ["warnings"] = warnings
            };
            if (requested.Contains("document")) result["document"] = new JObject
            {
                ["runtime_serial_number"] = Observe("document.runtime_serial_number", () => new JValue(doc.RuntimeSerialNumber), warnings),
                ["path"] = Observe("document.path", () => new JValue(doc.Path), warnings),
                ["name"] = Observe("document.name", () => new JValue(doc.Name), warnings),
                ["units"] = Observe("document.units", () => new JValue(doc.ModelUnitSystem.ToString()), warnings),
                ["absolute_tolerance"] = Observe("document.absolute_tolerance", () => Number(doc.ModelAbsoluteTolerance), warnings),
                ["angle_tolerance_radians"] = Observe("document.angle_tolerance_radians", () => Number(doc.ModelAngleToleranceRadians), warnings),
                ["modified"] = Observe("document.modified", () => new JValue(doc.Modified), warnings),
                ["object_count"] = Observe("document.object_count", () => new JValue(CountObjects(doc)), warnings),
                ["layer_count"] = Observe("document.layer_count", () => new JValue(doc.Layers.ActiveCount), warnings)
            };
            if (requested.Contains("selection"))
                result["selection"] = Observe("selection", () => ObservationEntities.Selection(doc, selectionLimit, recursive, depth, selectionEntities), warnings);
            if (requested.Overlaps(new[] { "document", "selection", "viewport", "editor" }))
            {
                var editor = EditingContext.Observe(doc);
                if (!requested.Contains("editor"))
                {
                    editor.Remove("evidence");
                    editor.Remove("warnings");
                }
                result["editor"] = editor;
            }
            if (requested.Contains("display_modes")) result["display_modes"] = DisplayModes(warnings);
            if (requested.Contains("viewport")) result["viewport"] = Observe("viewport", () =>
            {
                var view = doc.Views.ActiveView;
                if (view == null)
                {
                    warnings.Add("viewport: This document has no active view.");
                    return JValue.CreateNull();
                }
                return ReadViewport(view.ActiveViewport);
            }, warnings);

            if (includeImage)
            {
                var capture = GetViewportImage(doc);
                if ((string)capture["status"] == "success")
                {
                    result["image"] = capture["image"];
                    foreach (var warning in (JArray)capture["warnings"]) warnings.Add(warning.DeepClone());
                }
                else result["image_error"] = capture;
            }

            return result;
        }

        /// <summary>
        /// Lists or captures model viewports, saved named views and layout paper.
        /// Named views render through a detached viewport; no view is activated/restored.
        /// All bitmaps and encoded bytes stay in memory, without temporary files.
        /// </summary>
        public static JObject GetViewportImage(RhinoDoc doc, string selector = "", int scalePercent = 75,
            string displayMode = "", bool labels = true, int depth = 1,
            string targetKind = "view", string target = "")
        {
            selector = (selector ?? "").Trim().ToLowerInvariant();
            Guid targetId = Guid.Empty;
            Guid entityId;
            if (scalePercent < 1 || scalePercent > 100 || depth < 1 || depth > 8 ||
                displayMode == null || displayMode.Length > 512 ||
                (targetKind != "view" && targetKind != "group" && targetKind != "block") ||
                (targetKind == "view" ? !String.IsNullOrEmpty(target) : selector != "" || !Guid.TryParse(target, out entityId)) ||
                (selector != "" && selector != "a" && !Guid.TryParse(selector, out targetId)))
                return Error("invalid_arguments", "Use view (empty, 'a', or a GUID) and integer scale_percent from 1 through 100.");
            if (doc == null)
                return Error("no_document", "No Rhino document is available.");

            var stage = "observation_failed";
            try
            {
                if (selector == "a")
                    return ListImageViews(doc);
                if (doc.IsHeadless)
                    return Error("no_viewport", "A headless document has no view to capture.");
                var activeView = doc.Views.ActiveView;
                if (activeView == null)
                    return Error("no_viewport", "This document has no active view.");
                if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                    return Error("document_changed", "The requested document is not active.");
                RhinoView view = selector == "" && targetKind == "view" ? activeView : null;
                ViewInfo namedView = null;
                List<ObservationEntities.Entity> entities = null;
                if (targetKind != "view") entities = ObservationEntities.CaptureRoots(doc, targetKind, Guid.Parse(target));
                if (selector != "")
                {
                    foreach (var candidate in doc.Views.GetViewList(ViewTypeFilter.Model | ViewTypeFilter.Page))
                        if (candidate.MainViewport.Id == targetId)
                            view = candidate;
                    if (view == null)
                        foreach (var candidate in doc.NamedViews)
                            if (candidate.NamedViewId == targetId)
                                namedView = candidate;
                    if (view == null && namedView == null)
                        return Error("view_not_found", "This GUID is not an available viewport, named view or layout. Use view='a' to list them.");
                }
                var documentInfo = ReadIdentity(doc);
                var activeState = ImageViewState(activeView);
                var targetState = view == null ? null : ImageViewState(view);
                var page = view as RhinoPageView;
                if (page != null && displayMode != "")
                    return Error("unsupported_display_mode", "Layout captures preserve each detail's display mode; capture a model viewport or Named View to override it.");
                DisplayModeDescription mode = null;
                if (displayMode != "" || namedView != null || targetKind != "view")
                {
                    mode = ResolveDisplayMode(displayMode == "" ? "Shaded" : displayMode);
                    if (mode == null)
                    {
                        var error = Error("display_mode_not_found", "The display mode is missing or ambiguous. Use context sections=['display_modes'] for installed names/GUIDs.");
                        error["display_modes"] = DisplayModes((JArray)error["warnings"]);
                        return error;
                    }
                }
                // A mode override or independent capture requests a new render. A current-view
                // capture without an override can still copy its existing realtime frame.
                if (mode != null && mode.DisplayAttributes.RealtimeDisplayId != Guid.Empty)
                    return Error("unsupported_display_mode", "Realtime display modes require an asynchronous render; choose an installed raster display mode such as Shaded.");
                Size sourceSize;
                if (page != null)
                {
                    // Paper dimensions at the default Layout DPI define 100%, independent of layout zoom.
                    using (var settings = new ViewCaptureSettings(page, LayoutDpi))
                        sourceSize = settings.MediaSize;
                }
                else if (namedView != null)
                {
                    var port = namedView.Viewport.GetScreenPort();
                    sourceSize = new Size(Math.Abs(port.Width), Math.Abs(port.Height));
                    if (sourceSize.Width == 0 || sourceSize.Height == 0)
                        sourceSize = activeView.ActiveViewport.Size;
                }
                else
                    sourceSize = view == null ? activeView.ActiveViewport.Size : view.MainViewport.Size;
                if (sourceSize.Width <= 0 || sourceSize.Height <= 0)
                    return Error("invalid_viewport_size", "The requested view has no positive pixel size.");
                var size = new Size(Math.Max(1, (int)((long)sourceSize.Width * scalePercent / 100)),
                                    Math.Max(1, (int)((long)sourceSize.Height * scalePercent / 100)));
                if ((long)size.Width * size.Height > 16 * 1024 * 1024)
                    return Error("image_too_large", "The requested image exceeds 16 megapixels. Use a lower scale_percent.");
                stage = "capture_failed";
                var warnings = new JArray();
                using (var bitmap = CaptureImage(doc, view, namedView, size, sourceSize, scalePercent,
                    mode, labels, depth, entities, warnings))
                {
                    if (bitmap == null)
                        return Error("capture_failed", "Rhino did not produce a viewport bitmap.");
                    if (bitmap.Width != size.Width || bitmap.Height != size.Height)
                        return Error("unexpected_image_size", "The captured bitmap dimensions differ from the requested dimensions.");

                    var activeDocument = RhinoDoc.ActiveDoc;
                    if (activeDocument == null || activeDocument.RuntimeSerialNumber != doc.RuntimeSerialNumber ||
                        !JToken.DeepEquals(documentInfo, ReadIdentity(doc)))
                        return Error("document_changed", "The active document or its identity changed during capture.");
                    var currentView = doc.Views.ActiveView;
                    if (namedView == null && targetKind == "view" && (currentView == null ||
                        !JToken.DeepEquals(activeState, ImageViewState(currentView)) ||
                        (view != null && !JToken.DeepEquals(targetState, ImageViewState(view)))))
                        return Error("viewport_changed", "The viewport changed during capture; no image was returned.");

                    stage = "image_encode_failed";
                    using (var stream = new MemoryStream())
                    {
                        if (page != null)
                        {
                            var dpi = (float)(LayoutDpi * scalePercent / 100.0);
                            bitmap.SetResolution(dpi, dpi);
                        }
                        bitmap.Save(stream, ImageFormat.Png);
                        if (stream.Length == 0)
                            return Error("image_encode_failed", "PNG encoding produced no bytes.");
                        if (stream.Length > MaxImageBytes)
                            return Error("image_too_large", "The PNG exceeds the 4 MiB limit. Use a lower scale_percent.");
                        byte[] bytes = stream.ToArray();
                        return new JObject
                        {
                            ["status"] = "success",
                            ["image"] = new JObject
                            {
                                ["mime_type"] = "image/png",
                                ["data"] = Convert.ToBase64String(bytes),
                                ["width"] = bitmap.Width,
                                ["height"] = bitmap.Height,
                                ["source_width"] = sourceSize.Width,
                                ["source_height"] = sourceSize.Height
                            },
                            ["warnings"] = warnings
                        };
                    }
                }
            }
            catch (Exception ex)
            {
                return Error(stage, ex.Message);
            }
        }

        private static JObject ListImageViews(RhinoDoc doc)
        {
            var viewports = new JArray();
            var layouts = new JArray();
            var namedViews = new JArray();
            foreach (var view in doc.Views.GetViewList(ViewTypeFilter.Model | ViewTypeFilter.Page))
                (view is RhinoPageView ? layouts : viewports).Add(new JObject
                {
                    ["name"] = view.MainViewport.Name,
                    ["guid"] = view.MainViewport.Id.ToString()
                });
            foreach (var view in doc.NamedViews)
                namedViews.Add(new JObject { ["name"] = view.Name, ["guid"] = view.NamedViewId.ToString() });
            return new JObject
            {
                ["status"] = "success",
                ["views"] = new JObject { ["viewports"] = viewports, ["named_views"] = namedViews, ["layouts"] = layouts },
                ["warnings"] = new JArray()
            };
        }

        private static JObject ImageViewState(RhinoView view)
        {
            return new JObject { ["main"] = ReadViewport(view.MainViewport), ["active"] = ReadViewport(view.ActiveViewport) };
        }

        private static Bitmap CaptureImage(RhinoDoc doc, RhinoView view, ViewInfo namedView,
            Size size, Size sourceSize, int scalePercent, DisplayModeDescription mode,
            bool labels, int depth, List<ObservationEntities.Entity> entities, JArray warnings)
        {
            var page = view as RhinoPageView;
            if (page != null)
            {
                if (labels) warnings.Add("labels: Layout detail overlays are unavailable; capture its model viewport or a Named View for entity labels.");
                using (var settings = new ViewCaptureSettings(page, LayoutDpi * scalePercent / 100.0))
                {
                    settings.Document = doc;
                    settings.RasterMode = true;
                    // Capture the paper's print appearance without changing PrintDisplay
                    // or the individual details' physical model-to-paper scales.
                    settings.OutputColor = ViewCaptureSettings.ColorMode.PrintColor;
                    settings.UsePrintWidths = true;
                    settings.DrawBackground = true;
                    settings.HeaderText = "";
                    settings.FooterText = "";
                    settings.SetLayout(size, new Rectangle(System.Drawing.Point.Empty, size));
                    // RhinoCommon's public overload hard-codes forPrinting=false, so
                    // Layout details ignore OutputColor and UsePrintWidths. Use its
                    // Rhino 8 printing overload without changing document PrintDisplay.
                    var printCapture = typeof(ViewCapture).GetMethod("CaptureToBitmap",
                        System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic,
                        null, new[] { typeof(ViewCaptureSettings), typeof(bool), typeof(bool) }, null);
                    if (printCapture == null)
                        throw new NotSupportedException("This RhinoCommon version does not support Layout capture with print colors and widths.");
                    return (Bitmap)printCapture.Invoke(null, new object[] { settings, true, false });
                }
            }
            if (namedView == null && entities == null)
            {
                var bitmap = mode == null ? view.CaptureToBitmap(size) : view.CaptureToBitmap(size, mode);
                if (bitmap != null && labels) ObservationEntities.DrawLabels(doc, bitmap, view.MainViewport,
                    ObservationEntities.Roots(doc, ObservationEntities.ModelObjects(doc)), depth, warnings);
                return bitmap;
            }
            if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                throw new InvalidOperationException("The capture document is no longer active.");
            // A never-shown SDK control initializes its own display pipeline. Printing settings
            // accept a detached camera but silently render Wireframe on the supported Rhino SDK.
            using (var control = new CaptureViewportControl { Visible = false, Size = size })
            {
                var handle = control.Handle;
                var viewport = control.Viewport;
                if (namedView != null)
                {
                    if (!viewport.SetViewProjection(namedView.Viewport, true))
                        throw new InvalidOperationException("Could not apply the named view to a detached viewport.");
                }
                else
                    using (var projection = new ViewportInfo(view == null ? doc.Views.ActiveView.ActiveViewport : view.MainViewport))
                        if (!viewport.SetViewProjection(projection, true))
                            throw new InvalidOperationException("Could not copy the capture projection.");
                if (mode != null) viewport.DisplayMode = mode;
                if (entities != null)
                {
                    var bounds = BoundingBox.Empty;
                    foreach (var entity in entities) bounds.Union(entity.Bounds);
                    if (!bounds.IsValid || !viewport.ZoomBoundingBox(bounds))
                        throw new InvalidOperationException("The capture target has no frameable bounds.");
                }
                DisplayPipeline pipeline = null;
                try
                {
                    control.InitializeCapturePipeline();
                    pipeline = control.Display;
                    if (pipeline == null || (!pipeline.IsOpen && !pipeline.Open()))
                        throw new InvalidOperationException("Could not initialize the independent capture pipeline.");
                    var bitmap = DisplayPipeline.DrawToBitmap(viewport, size.Width, size.Height);
                    if (bitmap != null && labels) ObservationEntities.DrawLabels(doc, bitmap, viewport,
                        entities ?? ObservationEntities.Roots(doc, ObservationEntities.ModelObjects(doc)), depth, warnings);
                    return bitmap;
                }
                finally { if (pipeline != null) pipeline.Close(); }
            }
        }

        internal sealed class CaptureViewportControl : RhinoWindows.Forms.Controls.ViewportControl
        {
            internal void InitializeCapturePipeline()
            {
                // Use the supported protected painting extension point to initialize OpenGL.
                // No Form, Show, view activation, registered display-mode edits or screen capture.
                for (int attempt = 0; attempt < 2; attempt++)
                    using (var bitmap = new Bitmap(ClientSize.Width, ClientSize.Height))
                    using (var graphics = Graphics.FromImage(bitmap))
                    using (var args = new System.Windows.Forms.PaintEventArgs(graphics, ClientRectangle))
                        base.OnPaint(args);
            }
        }

        internal static DisplayModeDescription ResolveDisplayMode(string value)
        {
            Guid id;
            if (Guid.TryParse(value, out id)) return DisplayModeDescription.GetDisplayMode(id);
            var matches = DisplayModeDescription.GetDisplayModes().Where(mode =>
                String.Equals(mode.EnglishName, value, StringComparison.OrdinalIgnoreCase) ||
                String.Equals(mode.LocalName, value, StringComparison.OrdinalIgnoreCase)).ToArray();
            return matches.Length == 1 ? matches[0] : null;
        }

        private static JArray DisplayModes(JArray warnings)
        {
            var modes = DisplayModeDescription.GetDisplayModes();
            if (modes.Length > 128) warnings.Add("display_modes: first 128 installed modes returned.");
            return new JArray(modes.Take(128).Select(mode => new JObject
                { ["name"] = mode.EnglishName, ["id"] = mode.Id.ToString() }));
        }

        private static bool ReadBoolean(JObject request, string name, bool fallback, out bool value)
        {
            value = fallback;
            if (request[name] == null) return true;
            if (request[name].Type != JTokenType.Boolean) return false;
            value = (bool)request[name];
            return true;
        }

        private static JObject ReadIdentity(RhinoDoc doc)
        {
            return new JObject
            {
                ["runtime_serial_number"] = doc.RuntimeSerialNumber,
                ["path"] = doc.Path,
                ["name"] = doc.Name
            };
        }

        private static long CountObjects(RhinoDoc doc)
        {
            var settings = new ObjectEnumeratorSettings
            {
                ActiveObjects = true, ReferenceObjects = true, NormalObjects = true,
                HiddenObjects = true, LockedObjects = true, DeletedObjects = false,
                IncludeLights = true, IncludeGrips = false, IdefObjects = false
            };
            long count = 0;
            foreach (var obj in doc.Objects.GetObjectList(settings))
                count = checked(count + 1);
            return count;
        }

        private static JObject ReadViewport(RhinoViewport viewport)
        {
            if (viewport == null)
                throw new InvalidOperationException("The active viewport is unavailable.");
            var size = viewport.Size;
            var mode = viewport.DisplayMode;
            if (mode == null)
                throw new InvalidOperationException("The viewport display mode is unavailable.");
            return new JObject
            {
                ["id"] = viewport.Id.ToString(),
                ["name"] = viewport.Name,
                ["width"] = size.Width,
                ["height"] = size.Height,
                ["display_mode"] = mode.EnglishName,
                ["projection"] = viewport.IsTwoPointPerspectiveProjection ? "two-point-perspective" :
                    viewport.IsPerspectiveProjection ? "perspective" : viewport.IsParallelProjection ? "parallel" : "unknown",
                ["camera_location"] = Coordinates(viewport.CameraLocation),
                ["target"] = Coordinates(viewport.CameraTarget),
                ["up"] = Coordinates((Point3d)viewport.CameraUp),
                ["lens_length"] = Number(viewport.Camera35mmLensLength)
            };
        }

        private static JArray Coordinates(Point3d value)
        {
            return new JArray(Number(value.X), Number(value.Y), Number(value.Z));
        }

        private static JValue Number(double value)
        {
            if (!RhinoMath.IsValidDouble(value))
                throw new InvalidOperationException("Rhino returned an unset or non-finite numeric value.");
            return new JValue(value);
        }

        private static JToken Observe(string name, Func<JToken> read, JArray warnings)
        {
            try { return read() ?? JValue.CreateNull(); }
            catch (Exception ex)
            {
                warnings.Add(name + ": " + ex.Message);
                return JValue.CreateNull();
            }
        }

        private static bool ReadInteger(JObject request, string name, int fallback, int minimum, int maximum, out int value)
        {
            value = fallback;
            var token = request == null ? null : request[name];
            if (token == null)
                return true;
            if (token.Type != JTokenType.Integer)
                return false;
            try { value = token.Value<int>(); }
            catch (Exception) { return false; }
            return value >= minimum && value <= maximum;
        }

        private static JObject Error(string code, string message)
        {
            return new JObject
            {
                ["status"] = "error",
                ["error_code"] = code,
                ["message"] = message,
                ["warnings"] = new JArray()
            };
        }
    }
}
