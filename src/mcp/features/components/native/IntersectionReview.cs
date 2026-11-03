using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    /// <summary>One live pair, one camera, context and native-Isolate captures.</summary>
    public static class IntersectionReview
    {
        public static JObject Capture(RhinoDoc doc, JObject request)
        {
            bool started = false, isolated = false, restored = false;
            uint serial = 0;
            HashSet<Guid> hidden = null;
            IntersectionAnalysis.Scope sa = null, sb = null;
            JObject answer = null;
            try
            {
                ObjectObservation.ValidateDocument(doc, request);
                serial = doc.RuntimeSerialNumber;
                var view = doc.Views.ActiveView;
                if (doc.IsHeadless || doc.IsReadOnly || RhinoDoc.ActiveDoc?.RuntimeSerialNumber != serial ||
                    view == null || view is RhinoPageView)
                    throw new ArgumentException("Use the current writable document and a model viewport for comparison.");
                var editor = EditingContext.Observe(doc);
                if ((bool?)editor["stable"] != true || (string)editor["mode"] != "model")
                    throw new ArgumentException("Finish group/block editing before reviewing document objects.");
                if (view.ActiveViewport.DisplayMode.DisplayAttributes.RealtimeDisplayId != Guid.Empty)
                    throw new ArgumentException("Use a raster display mode for synchronized comparison captures.");
                var a = IntersectionAnalysis.ResolveHandle(doc, request["a"] as JObject, out sa);
                var b = IntersectionAnalysis.ResolveHandle(doc, request["b"] as JObject, out sb);
                if (a.Key == b.Key) throw new ArgumentException("Choose distinct occurrences.");
                using (var observed = IntersectionAnalysis.Observe(doc, a, b))
                {
                    if ((string)observed.Report["overlap"]?["status"] != "positive_volume")
                        throw new ArgumentException("The current pair has no confirmed positive overlap; query again.");
                    answer = new JObject { ["status"] = "success", ["objects"] = new JArray(Describe(doc, a, 1), Describe(doc, b, 2)),
                        ["overlap"] = observed.Report["overlap"].DeepClone(),
                        ["regions"] = observed.Report["regions"]?.DeepClone(),
                        ["warnings"] = new JArray("Block occurrences are shown as their whole top-level instances; numbered markers identify the intersecting member positions.",
                            "Native Isolate can retain locked context. Camera and selection remain on the pair; comparison isolation is restored.") };
                }
                hidden = Hidden(doc);
                var focus = ComponentOperations.FocusObjects(doc, new[] { a.RootId, b.RootId }.Distinct().ToArray(), false);
                if ((string)focus["status"] != "success") return focus;
                started = true;
                // Two fixed zoom-out increments provide context without refocusing the second image.
                if (!view.ActiveViewport.Magnify(0.8, false) || !view.ActiveViewport.Magnify(0.8, false))
                    throw new InvalidOperationException("Rhino could not add comparison context around the selected pair.");
                Guid viewportId = view.ActiveViewport.Id;
                var camera = DocumentObservation.ImageViewState(view);
                using (var labels = new PairLabels(serial, viewportId, a.Bounds.Center, b.Bounds.Center))
                {
                    labels.Enabled = true;
                    doc.Views.Redraw();
                    using (var context = Image(doc))
                    {
                        if (!RhinoApp.RunScript("_Isolate", false))
                            throw new InvalidOperationException("Rhino did not complete comparison Isolate.");
                        isolated = true;
                        CheckView(doc, serial, viewportId, camera);
                        using (var detail = Image(doc))
                        using (var combined = new Bitmap(1280, 504))
                        using (var graphics = Graphics.FromImage(combined))
                        using (var font = new System.Drawing.Font(FontFamily.GenericSansSerif, 12))
                        {
                            CheckView(doc, serial, viewportId, camera);
                            graphics.Clear(Color.White);
                            graphics.DrawString("Context", font, Brushes.Black, 8, 2);
                            graphics.DrawString("Isolated pair", font, Brushes.Black, 648, 2);
                            graphics.DrawImageUnscaled(context, 0, 24);
                            graphics.DrawImageUnscaled(detail, 640, 24);
                            using (var stream = new MemoryStream())
                            {
                                combined.Save(stream, ImageFormat.Png);
                                if (stream.Length > 4 * 1024 * 1024) throw new InvalidOperationException("Comparison PNG exceeds 4 MiB.");
                                answer["image"] = new JObject { ["mime_type"] = "image/png", ["data"] = Convert.ToBase64String(stream.ToArray()),
                                    ["width"] = 1280, ["height"] = 504 };
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                answer = new JObject { ["status"] = "error", ["error_code"] = "intersection_review_failed", ["message"] = ex.Message,
                    ["requires_reconciliation"] = started };
            }
            finally
            {
                sa?.Dispose(); sb?.Dispose();
                if (isolated)
                {
                    try
                    {
                        if (RhinoDoc.ActiveDoc?.RuntimeSerialNumber != serial || !RhinoApp.RunScript("_Unisolate", false))
                            throw new InvalidOperationException("Comparison isolation could not be restored.");
                        if (!hidden.SetEquals(Hidden(doc)))
                            throw new InvalidOperationException("Visibility differs from before comparison; inspect it before continuing.");
                        restored = true;
                    }
                    catch (Exception ex)
                    {
                        answer = new JObject { ["status"] = "error", ["error_code"] = "intersection_visibility_unconfirmed",
                            ["message"] = ex.Message, ["requires_reconciliation"] = true };
                    }
                }
                if (started && RhinoDoc.ActiveDoc?.RuntimeSerialNumber == serial) doc.Views.Redraw();
            }
            answer["mutation_applied"] = started;
            answer["view_change"] = new JObject { ["selection_changed"] = started, ["zoom_selected"] = started,
                ["comparison_isolation_restored"] = restored, ["geometry_changed"] = false };
            return answer;
        }

        static HashSet<Guid> Hidden(RhinoDoc doc) => new HashSet<Guid>(ObjectObservation.ModelObjects(doc).Where(o => o.IsHidden).Select(o => o.Id));

        static void CheckView(RhinoDoc doc, uint serial, Guid viewport, JObject camera)
        {
            var current = doc.Views.ActiveView?.ActiveViewport;
            if (RhinoDoc.ActiveDoc?.RuntimeSerialNumber != serial || current == null || current.Id != viewport ||
                !JToken.DeepEquals(camera, DocumentObservation.ImageViewState(doc.Views.ActiveView)))
                throw new InvalidOperationException("The document or comparison camera changed; no combined image is returned.");
        }

        static Bitmap Image(RhinoDoc doc)
        {
            var captured = DocumentObservation.GetViewportImage(doc, "", 100, "", false, 1, "view", "", 640, 480);
            if ((string)captured["status"] != "success") throw new InvalidOperationException((string)captured["message"] ?? "Capture failed.");
            using (var stream = new MemoryStream(Convert.FromBase64String((string)captured["image"]["data"])))
            using (var decoded = System.Drawing.Image.FromStream(stream)) return new Bitmap(decoded);
        }

        static JObject Describe(RhinoDoc doc, IntersectionAnalysis.Member member, int number)
        {
            var obj = doc.Objects.FindId(member.RootId);
            var blocks = new JArray();
            foreach (Guid id in member.Path)
            {
                var instance = obj as InstanceObject;
                blocks.Add(new JObject { ["instance_id"] = obj.Id.ToString("D"), ["name"] = instance.InstanceDefinition.Name });
                obj = instance.InstanceDefinition.GetObjects().Single(o => o.Id == id);
            }
            var detail = ObjectObservation.IntersectionMetadata(obj);
            detail["number"] = number;
            detail["guid"] = member.RootId.ToString("D");
            detail["member_id"] = obj.Id.ToString("D");
            detail["handle"] = member.Info["handle"].DeepClone();
            detail["name"] = member.Info["name"].DeepClone();
            detail["layer"] = member.Info["layer_path"].DeepClone();
            detail["blocks"] = blocks;
            detail["document_object"] = member.Path.Length == 0;
            detail["is_reference"] = obj.IsReference;
            return detail;
        }

        sealed class PairLabels : DisplayConduit, IDisposable
        {
            readonly uint serial; readonly Guid view; readonly Point3d a, b;
            internal PairLabels(uint document, Guid viewport, Point3d first, Point3d second)
            { serial = document; view = viewport; a = first; b = second; }
            protected override void DrawForeground(DrawEventArgs e)
            {
                if (e.RhinoDoc?.RuntimeSerialNumber != serial || e.Viewport.Id != view) return;
                e.Display.DrawDot(a, "1", Color.DarkBlue, Color.White);
                e.Display.DrawDot(b, "2", Color.DarkRed, Color.White);
            }
            public void Dispose() { Enabled = false; }
        }
    }
}
