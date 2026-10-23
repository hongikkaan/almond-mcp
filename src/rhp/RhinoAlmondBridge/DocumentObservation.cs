using System;
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
            return GetContext(RhinoDoc.ActiveDoc, selectionLimit).ToString(Formatting.None);
        }

        public static string HandleViewportImage(JObject request)
        {
            int maxWidth, maxHeight;
            if (!ReadInteger(request, "max_width", 1280, 64, 2048, out maxWidth) ||
                !ReadInteger(request, "max_height", 960, 64, 2048, out maxHeight))
                return Error("invalid_arguments", "max_width and max_height must be integers from 64 through 2048.").ToString(Formatting.None);
            return GetViewportImage(RhinoDoc.ActiveDoc, maxWidth, maxHeight).ToString(Formatting.None);
        }

        /// <summary>
        /// Counts live normal, hidden, locked and reference objects, including lights;
        /// excludes deleted objects, instance-definition members and grips.
        /// Failed fields or sections are null and identified in warnings, never fake zeroes.
        /// </summary>
        public static JObject GetContext(RhinoDoc doc, int selectionLimit = 50)
        {
            if (selectionLimit < 0 || selectionLimit > MaxSelectionLimit)
                return Error("invalid_arguments", "selection_limit must be from 0 through 200.");
            if (doc == null)
                return Error("no_document", "No Rhino document is available.");

            var warnings = new JArray();
            var document = new JObject
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
            var selection = Observe("selection", () => ReadSelection(doc, selectionLimit, warnings), warnings);
            var viewport = Observe("viewport", () =>
            {
                var view = doc.Views.ActiveView;
                if (view == null)
                {
                    warnings.Add("viewport: This document has no active view.");
                    return JValue.CreateNull();
                }
                return ReadViewport(view.ActiveViewport);
            }, warnings);

            return new JObject
            {
                ["status"] = "success",
                ["capabilities"] = new JObject { ["fixed_probes"] = 1 },
                ["document"] = document,
                ["selection"] = selection,
                ["viewport"] = viewport,
                ["warnings"] = warnings
            };
        }

        /// <summary>
        /// Captures the current view window, at its existing aspect ratio, without
        /// changing its camera, display mode, clipping, selection or document state.
        /// In a page view the image and viewport metadata describe the whole page view;
        /// active_viewport_id separately identifies an active child detail.
        /// </summary>
        public static JObject GetViewportImage(RhinoDoc doc, int maxWidth = 1280, int maxHeight = 960)
        {
            if (maxWidth < 64 || maxWidth > 2048 || maxHeight < 64 || maxHeight > 2048)
                return Error("invalid_arguments", "max_width and max_height must be from 64 through 2048.");
            if (doc == null)
                return Error("no_document", "No Rhino document is available.");

            var warnings = new JArray();
            var stage = "observation_failed";
            try
            {
                if (doc.IsHeadless)
                    return Error("no_viewport", "A headless document has no view to capture.");
                var view = doc.Views.ActiveView;
                if (view == null)
                    return Error("no_viewport", "This document has no active view.");
                // CaptureToBitmap captures a RhinoView window, not just an active
                // layout detail. Use its main viewport for the image's camera/aspect.
                var viewport = view.MainViewport;
                if (viewport == null)
                    return Error("no_viewport", "The active view has no main viewport.");
                if (view.Document == null || view.Document.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                    return Error("document_changed", "The active view does not belong to the requested document.");

                var documentInfo = ReadIdentity(doc);
                var viewportInfo = ReadViewport(viewport);
                var activeViewportId = view.ActiveViewportID;
                var sourceSize = viewport.Size;
                if (sourceSize.Width <= 0 || sourceSize.Height <= 0)
                    return Error("invalid_viewport_size", "The active view has no positive pixel size.");
                if (activeViewportId != viewport.Id)
                    warnings.Add("The image captures the whole page view. viewport describes its main viewport; active_viewport_id identifies the active detail.");

                double scale = Math.Min(1.0, Math.Min((double)maxWidth / sourceSize.Width, (double)maxHeight / sourceSize.Height));
                var size = new Size(Math.Max(1, (int)Math.Floor(sourceSize.Width * scale)),
                                    Math.Max(1, (int)Math.Floor(sourceSize.Height * scale)));
                string capturedAt = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture);
                stage = "capture_failed";
                using (var bitmap = view.CaptureToBitmap(size))
                {
                    if (bitmap == null)
                        return Error("capture_failed", "Rhino did not produce a viewport bitmap.");
                    if (bitmap.Width != size.Width || bitmap.Height != size.Height)
                        return Error("unexpected_image_size", "The captured bitmap dimensions differ from the requested dimensions.");

                    // Do not attach a different document/camera's metadata if a
                    // display callback changed the view during the synchronous capture.
                    var activeDocument = RhinoDoc.ActiveDoc;
                    if (activeDocument == null || activeDocument.RuntimeSerialNumber != doc.RuntimeSerialNumber ||
                        !JToken.DeepEquals(documentInfo, ReadIdentity(doc)))
                        return Error("document_changed", "The active document or its identity changed during capture.");
                    var currentView = doc.Views.ActiveView;
                    if (currentView == null || currentView.MainViewport == null ||
                        currentView.MainViewport.Id != viewport.Id ||
                        currentView.ActiveViewportID != activeViewportId ||
                        !JToken.DeepEquals(viewportInfo, ReadViewport(viewport)))
                        return Error("viewport_changed", "The viewport changed during capture; no image was returned.");

                    stage = "image_encode_failed";
                    using (var stream = new MemoryStream())
                    {
                        bitmap.Save(stream, ImageFormat.Jpeg);
                        if (stream.Length == 0)
                            return Error("image_encode_failed", "JPEG encoding produced no bytes.");
                        if (stream.Length > MaxImageBytes)
                            return Error("image_too_large", "The JPEG exceeds the 4 MiB limit. Request smaller maximum dimensions.");
                        byte[] bytes = stream.ToArray();
                        return new JObject
                        {
                            ["status"] = "success",
                            ["document"] = documentInfo,
                            ["viewport"] = viewportInfo,
                            ["active_viewport_id"] = activeViewportId.ToString(),
                            ["capture_scope"] = view is RhinoPageView ? "page_view" : "model_view",
                            ["captured_at_utc"] = capturedAt,
                            ["image_byte_count"] = bytes.Length,
                            ["image"] = new JObject
                            {
                                ["mime_type"] = "image/jpeg",
                                ["data"] = Convert.ToBase64String(bytes),
                                ["width"] = bitmap.Width,
                                ["height"] = bitmap.Height
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
