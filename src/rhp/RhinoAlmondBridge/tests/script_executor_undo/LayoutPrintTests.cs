using System;
using System.Collections.Generic;
using System.Drawing;
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
    public static partial class ObservationTests
    {
        // Diagnostic for the disposable fixture only: compare supported capture
        // settings without toggling PrintDisplay or touching the active view.
        public static string DiagnoseLayoutPrint(string directory)
        {
            var doc = RhinoDoc.ActiveDoc;
            var page = doc == null ? null : doc.Views.GetPageViews().SingleOrDefault(v => v.PageName == "A4 print colors and detail scales");
            Check(page != null, "Open only the disposable print fixture for this diagnostic.");
            Directory.CreateDirectory(directory);
            var before = DocumentState(doc);
            var results = new JArray();
            foreach (bool raster in new[] { false, true })
            foreach (bool background in new[] { false, true })
            using (var settings = new ViewCaptureSettings(page, 72))
            {
                settings.Document = doc;
                settings.SetLayout(settings.MediaSize, new Rectangle(System.Drawing.Point.Empty, settings.MediaSize));
                settings.RasterMode = raster;
                settings.OutputColor = ViewCaptureSettings.ColorMode.PrintColor;
                settings.UsePrintWidths = true;
                settings.DrawBackground = background;
                settings.HeaderText = settings.FooterText = "";
                using (var bitmap = ViewCapture.CaptureToBitmap(settings))
                {
                    Check(bitmap != null, "Diagnostic capture failed");
                    string path = Path.Combine(directory, "raster-" + raster + "-background-" + background + ".png");
                    bitmap.Save(path, System.Drawing.Imaging.ImageFormat.Png);
                    var area = new Rectangle(0, 0, bitmap.Width, bitmap.Height);
                    results.Add(new JObject { ["raster"] = raster, ["background"] = background,
                        ["output_color"] = settings.OutputColor.ToString(), ["print_widths"] = settings.UsePrintWidths,
                        ["black"] = ColorBounds(bitmap, area, IsBlack).ToString(),
                        ["red"] = ColorBounds(bitmap, area, IsRed).ToString(),
                        ["blue"] = ColorBounds(bitmap, area, IsBlue).ToString(), ["file"] = path });
                }
                Unchanged(before, DocumentState(doc), "Print capture variant");
            }
            File.WriteAllText(Path.Combine(directory, "variants.json"), results.ToString(Formatting.Indented));
            return results.ToString(Formatting.None);
        }

        // Actual pixels and independent state, never a mocked bitmap or source-text assertion.
        // Invoke in a dedicated empty Rhino process from a modeless UI callback.
        public static string RunLayoutPrint(string directory)
        {
            var startup = RhinoDoc.ActiveDoc;
            Check(startup == null || (!startup.Modified && string.IsNullOrEmpty(startup.Path) &&
                !startup.Objects.GetObjectList(ObjectType.AnyObject).Any()), "Use an isolated empty Rhino process.");
            Directory.CreateDirectory(directory);
            string path = Path.Combine(directory, "layout-print.3dm");
            Check(!File.Exists(path), "Use a new fixture directory; do not overwrite an existing model.");
            // The guarded startup document is already this fixture's disposable
            // visible document. Opening another document from ScriptServer can be
            // rejected even on the UI thread and is unrelated to capture behavior.
            var doc = startup;
            Check(doc != null && !doc.IsHeadless,
                "A visible empty startup document is required. doc=" + (doc == null ? "null" :
                "serial=" + doc.RuntimeSerialNumber + ", headless=" + doc.IsHeadless + ", path=" + doc.Path));
            doc.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
            doc.PageUnitSystem = UnitSystem.Millimeters;
            Check(doc.Objects.AddLine(Point3d.Origin, new Point3d(1000, 0, 0),
                PrintAttributes(Color.Red, Color.Blue, 0.5)) != Guid.Empty, "Could not create the measured model line.");
            {
                try
                {
                    var model = doc.Views.GetStandardRhinoViews()[0];
                    doc.Views.ActiveView = model;
                    var page = doc.Views.AddPageView("A4 print colors and detail scales", 297, 210);
                    Check(page != null, "Could not create the print layout.");
                    AddPaperLine(doc, page, 150, 0.5);
                    AddPaperLine(doc, page, 130, 2.0);
                    Guid fifty = AddPrintDetail(doc, page, "1:50", 15, 125, 50);
                    Guid hundred = AddPrintDetail(doc, page, "1:100", 155, 265, 100);
                    doc.Views.ActiveView = model;
                    doc.Views.Redraw();
                    // A selected off-page point makes selection preservation nontrivial.
                    var selected = doc.Objects.AddPoint(new Point3d(1000000, 1000000, 1000000));
                    doc.Objects.Select(selected, true);
                    Check(doc.WriteFile(path, new Rhino.FileIO.FileWriteOptions {
                        SuppressDialogBoxes = true, SuppressAllInput = true, UpdateDocumentPath = false
                    }), "Could not save the disposable layout fixture evidence.");
                    doc.Modified = false;
                    var before = DocumentState(doc);
                    var ratios = new[] { DetailRatio(doc, fifty), DetailRatio(doc, hundred) };
                    Check(Math.Abs(ratios[0] - 0.02) < 1e-12 && Math.Abs(ratios[1] - 0.01) < 1e-12,
                        "The fixture did not establish actual 1:50 and 1:100 detail scales.");
                    var measurements = new JArray();
                    var lines = new List<string>();
                    double defaultFiftyWidth = 0;
                    foreach (int percent in new[] { 75, 100 })
                    {
                        int activations = 0;
                        EventHandler<ViewEventArgs> activated = (sender, args) => activations++;
                        JObject response;
                        RhinoView.SetActive += activated;
                        try
                        {
                            response = percent == 75
                                ? Wire(DocumentObservation.GetViewportImage(doc, page.MainViewport.Id.ToString()))
                                : Wire(DocumentObservation.GetViewportImage(doc, page.MainViewport.Id.ToString(), percent));
                        }
                        finally { RhinoView.SetActive -= activated; }
                        Success(response);
                        DecodePng(response, percent);
                        Check(activations == 0, "Layout capture activated a view.");
                        Unchanged(before, DocumentState(doc), "Print capture " + percent);
                        Check(DetailRatio(doc, fifty) == ratios[0] && DetailRatio(doc, hundred) == ratios[1],
                            "Capture changed a detail's physical scale.");
                        byte[] bytes = Convert.FromBase64String((string)response["image"]["data"]);
                        string output = Path.Combine(directory, "layout-print-" + percent + ".png");
                        File.WriteAllBytes(output, bytes);
                        using (var stream = new MemoryStream(bytes))
                        using (var bitmap = new Bitmap(stream))
                        {
                            Rectangle thinArea = PaperArea(bitmap, 20, 145, 110, 155);
                            Rectangle thickArea = PaperArea(bitmap, 20, 125, 110, 135);
                            var thin = ColorBounds(bitmap, thinArea, IsBlack);
                            var thick = ColorBounds(bitmap, thickArea, IsBlack);
                            Check(!thin.IsEmpty && !thick.IsEmpty, "Print-color black strokes were not captured.");
                            Check(ColorBounds(bitmap, thinArea, IsRed).IsEmpty && ColorBounds(bitmap, thickArea, IsRed).IsEmpty,
                                "Layout used display red instead of the configured print black.");
                            Check(thick.Height >= thin.Height * 2 && thick.Height >= 4,
                                "The 2.0 mm print stroke did not remain thicker than the 0.5 mm stroke.");
                            var a = ColorBounds(bitmap, PaperArea(bitmap, 15, 20, 125, 110), IsBlue);
                            var b = ColorBounds(bitmap, PaperArea(bitmap, 155, 20, 265, 110), IsBlue);
                            Check(!a.IsEmpty && !b.IsEmpty, "The measured print-blue line is missing from a detail.");
                            double pixelsPerMm = bitmap.Width / 297.0;
                            Check(Math.Abs(a.Width - 20 * pixelsPerMm) <= 3 && Math.Abs(b.Width - 10 * pixelsPerMm) <= 3,
                                "The printed line does not match its actual 1:50 and 1:100 paper lengths.");
                            Check((double)a.Width / b.Width > 1.8 && (double)a.Width / b.Width < 2.2,
                                "Different detail scales were collapsed to a common image scale.");
                            if (percent == 75) defaultFiftyWidth = a.Width;
                            else Check(Math.Abs(defaultFiftyWidth - a.Width * 0.75) <= 3,
                                "Image percentage changed the drawing scale instead of pixel density.");
                            measurements.Add(new JObject {
                                ["scale_percent"] = percent, ["width"] = bitmap.Width, ["height"] = bitmap.Height,
                                ["thin_width_pixels"] = thin.Height, ["thick_width_pixels"] = thick.Height,
                                ["detail_1_50_line_pixels"] = a.Width, ["detail_1_100_line_pixels"] = b.Width,
                                ["detail_ratios"] = new JArray(ratios[0], ratios[1]), ["png"] = output
                            });
                        }
                        lines.Add("PASS " + percent + "%: print colors, print widths, distinct detail scales and unchanged document/view/selection/Undo");
                    }
                    File.WriteAllText(Path.Combine(directory, "layout-print-measurements.json"), measurements.ToString(Formatting.Indented));
                    return Report(lines, "layout print appearance");
                }
                finally { doc.Modified = false; }
            }
        }

        private static ObjectAttributes PrintAttributes(Color display, Color print, double width)
        {
            return new ObjectAttributes {
                ColorSource = ObjectColorSource.ColorFromObject, ObjectColor = display,
                PlotColorSource = ObjectPlotColorSource.PlotColorFromObject, PlotColor = print,
                PlotWeightSource = ObjectPlotWeightSource.PlotWeightFromObject, PlotWeight = width
            };
        }

        private static void AddPaperLine(RhinoDoc doc, RhinoPageView page, double y, double width)
        {
            var attributes = PrintAttributes(Color.Red, Color.Black, width);
            attributes.Space = ActiveSpace.PageSpace;
            attributes.ViewportId = page.MainViewport.Id;
            Check(doc.Objects.AddLine(new Point3d(25, y, 0), new Point3d(105, y, 0), attributes) != Guid.Empty,
                "Could not create the paper-space print stroke.");
        }

        private static Guid AddPrintDetail(RhinoDoc doc, RhinoPageView page, string name, double left, double right, double scale)
        {
            var detail = page.AddDetailView(name, new Point2d(left, 20), new Point2d(right, 110), DefinedViewportProjection.Top);
            Check(detail != null, "Could not create " + name + " detail.");
            Guid id = detail.Id;
            detail.Viewport.DisplayMode = DisplayModeDescription.GetDisplayMode(DisplayModeDescription.WireframeId);
            var region = new BoundingBox(new Point3d(0, -100, -1), new Point3d(1000, 100, 1));
            Check(detail.Viewport.ZoomBoundingBox(region), "Could not frame the detail line.");
            detail.Viewport.SetCameraTarget(region.Center, true);
            Check(detail.CommitViewportChanges(), "Could not commit the detail camera.");
            detail = (DetailViewObject)doc.Objects.FindId(id);
            Check(detail.DetailGeometry.SetScale(scale, doc.ModelUnitSystem, 1, doc.PageUnitSystem), "Could not set " + name + " scale.");
            detail.DetailGeometry.IsProjectionLocked = true;
            Check(detail.CommitChanges(), "Could not commit the detail scale.");
            var attributes = detail.Attributes.Duplicate();
            attributes.PlotWeightSource = ObjectPlotWeightSource.PlotWeightFromObject;
            attributes.PlotWeight = -1; // Do not print the viewport frame.
            Check(doc.Objects.ModifyAttributes(id, attributes, true), "Could not suppress the fixture detail border.");
            return id;
        }

        private static double DetailRatio(RhinoDoc doc, Guid id) => ((DetailViewObject)doc.Objects.FindId(id)).DetailGeometry.PageToModelRatio;

        private static Rectangle PaperArea(Bitmap bitmap, double left, double bottom, double right, double top)
        {
            int x0 = (int)Math.Floor(left / 297 * bitmap.Width), x1 = (int)Math.Ceiling(right / 297 * bitmap.Width);
            int y0 = (int)Math.Floor((210 - top) / 210 * bitmap.Height), y1 = (int)Math.Ceiling((210 - bottom) / 210 * bitmap.Height);
            return Rectangle.Intersect(new Rectangle(0, 0, bitmap.Width, bitmap.Height), Rectangle.FromLTRB(x0, y0, x1, y1));
        }

        private static Rectangle ColorBounds(Bitmap bitmap, Rectangle area, Func<Color, bool> matches)
        {
            int left = bitmap.Width, right = -1, top = bitmap.Height, bottom = -1;
            for (int y = area.Top; y < area.Bottom; y++)
            for (int x = area.Left; x < area.Right; x++)
                if (matches(bitmap.GetPixel(x, y)))
                {
                    left = Math.Min(left, x); right = Math.Max(right, x);
                    top = Math.Min(top, y); bottom = Math.Max(bottom, y);
                }
            return right < left ? Rectangle.Empty : Rectangle.FromLTRB(left, top, right + 1, bottom + 1);
        }

        private static bool IsBlack(Color c) => c.R < 90 && c.G < 90 && c.B < 90;
        private static bool IsRed(Color c) => c.R > 150 && c.G < 100 && c.B < 100;
        private static bool IsBlue(Color c) => c.B > 150 && c.R < 100 && c.G < 130;
    }
}
