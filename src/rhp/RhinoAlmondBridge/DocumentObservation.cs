using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
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

        public static string HandleContext(JObject request)
        {
            int selectionLimit;
            if (!ReadInteger(request, "selection_limit", 50, 0, MaxSelectionLimit, out selectionLimit))
                return Error("invalid_arguments", "selection_limit must be an integer from 0 through 200.").ToString(Formatting.None);
            string[] sections = null;
            if (request["sections"] != null)
            {
                var requested = request["sections"] as JArray;
                if (requested == null || requested.Any(item => item.Type != JTokenType.String))
                    return Error("invalid_arguments", "sections must be an array of document, selection or viewport.").ToString(Formatting.None);
                sections = requested.Values<string>().ToArray();
            }
            return GetContext(RhinoDoc.ActiveDoc, selectionLimit, sections).ToString(Formatting.None);
        }

        public static string HandleViewportImage(JObject request)
        {
            int scalePercent;
            if (!ReadInteger(request, "scale_percent", 50, 1, 100, out scalePercent) ||
                (request["view"] != null && request["view"].Type != JTokenType.String) ||
                request["max_width"] != null || request["max_height"] != null)
                return Error("invalid_arguments", "Use view (empty, 'a', or a GUID) and integer scale_percent from 1 through 100.").ToString(Formatting.None);
            return GetViewportImage(RhinoDoc.ActiveDoc, (string)request["view"] ?? "", scalePercent).ToString(Formatting.None);
        }

        /// <summary>
        /// Counts live normal, hidden, locked and reference objects, including lights;
        /// excludes deleted objects, instance-definition members and grips.
        /// Failed fields or sections are null and identified in warnings, never fake zeroes.
        /// </summary>
        public static JObject GetContext(RhinoDoc doc, int selectionLimit = 50, string[] sections = null)
        {
            var requested = new HashSet<string>(sections ?? new[] { "document" });
            if (requested.Any(section => section != "document" && section != "selection" && section != "viewport"))
                return Error("invalid_arguments", "sections must contain only document, selection or viewport.");
            if (selectionLimit < 0 || selectionLimit > MaxSelectionLimit)
                return Error("invalid_arguments", "selection_limit must be from 0 through 200.");
            if (doc == null)
                return Error("no_document", "No Rhino document is available.");

            var warnings = new JArray();
            var result = new JObject
            {
                ["status"] = "success",
                ["capabilities"] = new JObject { ["fixed_probes"] = 1, ["modeling_materials"] = 2, ["design_components"] = 1, ["component_registry"] = 2,
                    ["component_operations"] = 1, ["drawing_asset_extract"] = 1, ["context_sections"] = 1 },
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
                result["selection"] = Observe("selection", () => ReadSelection(doc, selectionLimit, warnings), warnings);
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

            return result;
        }

        /// <summary>
        /// Lists or captures model viewports, saved named views and layout paper.
        /// Named views render through a detached viewport; no view is activated/restored.
        /// All bitmaps and encoded bytes stay in memory, without temporary files.
        /// </summary>
        public static JObject GetViewportImage(RhinoDoc doc, string selector = "", int scalePercent = 50)
        {
            selector = (selector ?? "").Trim().ToLowerInvariant();
            Guid targetId = Guid.Empty;
            if (scalePercent < 1 || scalePercent > 100 ||
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
                RhinoView view = selector == "" ? activeView : null;
                ViewInfo namedView = null;
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
                Size sourceSize;
                if (page != null)
                {
                    // Paper dimensions at 96 dpi define 100%, independent of layout zoom.
                    using (var settings = new ViewCaptureSettings(page, 96.0))
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
                    sourceSize = view.MainViewport.Size;
                if (sourceSize.Width <= 0 || sourceSize.Height <= 0)
                    return Error("invalid_viewport_size", "The requested view has no positive pixel size.");
                var size = new Size(Math.Max(1, (int)((long)sourceSize.Width * scalePercent / 100)),
                                    Math.Max(1, (int)((long)sourceSize.Height * scalePercent / 100)));
                if ((long)size.Width * size.Height > 16 * 1024 * 1024)
                    return Error("image_too_large", "The requested image exceeds 16 megapixels. Use a lower scale_percent.");
                stage = "capture_failed";
                using (var bitmap = CaptureImage(doc, view, namedView, size, sourceSize, scalePercent))
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
                    if (currentView == null || !JToken.DeepEquals(activeState, ImageViewState(currentView)) ||
                        (view != null && !JToken.DeepEquals(targetState, ImageViewState(view))))
                        return Error("viewport_changed", "The viewport changed during capture; no image was returned.");

                    stage = "image_encode_failed";
                    using (var stream = new MemoryStream())
                    {
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
                            ["warnings"] = new JArray()
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
            Size size, Size sourceSize, int scalePercent)
        {
            var page = view as RhinoPageView;
            if (page != null)
            {
                using (var settings = new ViewCaptureSettings(page, 96.0 * scalePercent / 100.0))
                {
                    settings.Document = doc;
                    settings.RasterMode = true;
                    settings.DrawBackground = true;
                    settings.HeaderText = "";
                    settings.FooterText = "";
                    settings.SetLayout(size, new Rectangle(System.Drawing.Point.Empty, size));
                    return ViewCapture.CaptureToBitmap(settings);
                }
            }
            if (namedView == null)
                return view.CaptureToBitmap(size);
            using (var viewport = new RhinoViewport(doc.Views.ActiveView.ActiveViewport))
            {
                viewport.Size = sourceSize;
                if (!viewport.SetViewProjection(namedView.Viewport, true))
                    throw new InvalidOperationException("Could not apply the named view to a detached viewport.");
                using (var settings = new ViewCaptureSettings(doc.Views.ActiveView, size, 96.0))
                {
                    settings.Document = doc;
                    settings.SetViewport(viewport);
                    settings.RasterMode = true;
                    settings.DrawBackground = true;
                    settings.HeaderText = "";
                    settings.FooterText = "";
                    settings.SetLayout(size, new Rectangle(System.Drawing.Point.Empty, size));
                    return ViewCapture.CaptureToBitmap(settings);
                }
            }
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

        private static JObject ReadSelection(RhinoDoc doc, int limit, JArray warnings)
        {
            var objects = new JArray();
            long total = 0;
            foreach (var obj in doc.Objects.GetSelectedObjects(true, false))
            {
                if (obj == null)
                    throw new InvalidOperationException("Selection enumeration returned a missing object.");
                total = checked(total + 1);
                if (objects.Count >= limit)
                    continue;
                string label = "selection.objects[" + objects.Count.ToString(CultureInfo.InvariantCulture) + "]";
                objects.Add(new JObject
                {
                    ["id"] = Observe(label + ".id", () => new JValue(obj.Id.ToString()), warnings),
                    ["name"] = Observe(label + ".name", () => new JValue(obj.Name ?? ""), warnings),
                    ["layer"] = Observe(label + ".layer", () => new JValue(LayerPath(doc, obj)), warnings),
                    ["type"] = Observe(label + ".type", () => new JValue(obj.ObjectType.ToString()), warnings)
                });
            }
            return new JObject
            {
                ["total"] = total,
                ["returned"] = objects.Count,
                ["truncated"] = total > objects.Count,
                ["objects"] = objects
            };
        }

        private static string LayerPath(RhinoDoc doc, RhinoObject obj)
        {
            int index = obj.Attributes.LayerIndex;
            if (index < 0 || index >= doc.Layers.Count)
                throw new InvalidOperationException("Object layer index is outside the layer table.");
            var layer = doc.Layers[index];
            if (layer == null || layer.IsDeleted)
                throw new InvalidOperationException("Object layer is unavailable or deleted.");
            return layer.FullPath;
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
