"""Execute production viewport snapshots with SDK-free doubles; no Rhino process or document."""
import os
from pathlib import Path
import re
import subprocess


def method(source, name):
    match = re.search(r"(?:private|internal) static [^\n]+ " + name + r"\([^\n]+\)\s*\{", source)
    assert match, name
    start = match.start()
    position = match.end()
    depth = 1
    while depth:
        depth += (source[position] == "{") - (source[position] == "}")
        position += 1
    return source[start:position]


def test_model_and_layout_capture_use_distinct_output_styles_and_preserve_view_state(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source = (Path(__file__).parents[1] / "features/context/native/DocumentObservation.cs").read_text(encoding="utf-8")
    names = ("CaptureModelImage", "CaptureLayoutImage", "CaptureRasterImage", "ImageViewState",
             "ReadViewport", "Coordinates", "Number")
    methods = "\n".join(method(source, name) for name in names)
    # Compile the exact production methods, including their call sites. Doubles only supply
    # SDK data; Newtonsoft's real null serialization and DeepEquals enforce the snapshot contract.
    (tmp_path / "Program.cs").write_text(HARNESS.replace("// PRODUCTION_METHODS", methods), encoding="utf-8")
    project = tmp_path / "LayoutState.csproj"
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable></PropertyGroup>
  <ItemGroup><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildBinPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    build = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([sdk, str(tmp_path / "bin/Release/net8.0/LayoutState.dll")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS: distinct model/Layout raster settings and unchanged views" in run.stdout


HARNESS = r'''
using System;
using System.Drawing;
using Newtonsoft.Json.Linq;

sealed class Mode
{
    public string EnglishName = "Wireframe";
    public DisplayAttributes DisplayAttributes = new DisplayAttributes();
}
sealed class DisplayAttributes { public bool ShowClippingPlanes, ShowLights; }
struct Point3d { public double X, Y, Z; }
static class RhinoMath { public static bool IsValidDouble(double value) => double.IsFinite(value); }
sealed class RhinoViewport
{
    public Guid Id = Guid.NewGuid();
    public string Name = "test";
    public Size Size = new Size(800, 600);
    public Mode DisplayMode;
    public bool IsTwoPointPerspectiveProjection, IsPerspectiveProjection, IsParallelProjection = true;
    public Point3d CameraLocation, CameraTarget, CameraUp;
    public double Camera35mmLensLength = 50;
    public bool ConstructionGridVisible, ConstructionAxesVisible;
}
class RhinoView { public RhinoViewport MainViewport, ActiveViewport; }
sealed class RhinoPageView : RhinoView { }
sealed class RhinoDoc { }
sealed class Bitmap { }

sealed class ViewCaptureSettings : IDisposable
{
    public enum ColorMode { DisplayColor, PrintColor }
    public enum ViewAreaMapping { View, Extents }
    public readonly RhinoView SourceView;
    public readonly double Dpi;
    public RhinoDoc Document;
    public ColorMode OutputColor = ColorMode.PrintColor;
    public ViewAreaMapping ViewArea = ViewAreaMapping.Extents;
    public Size MediaSize;
    public Rectangle DrawRectangle;
    public bool RasterMode, DrawBackground, DrawLockedObjects, ApplyDisplayModeThicknessScales;
    public bool UsePrintWidths = true, MatchLinetypePatternDefinition = true;
    public bool DrawGrid, DrawAxis, DrawClippingPlanes, DrawLights;
    public bool DrawSelectedObjectsOnly = true;
    public string HeaderText, FooterText;
    public ViewCaptureSettings(RhinoPageView page, double dpi) { SourceView = page; Dpi = dpi; }
    public ViewCaptureSettings(RhinoView view, Size size, double dpi)
    {
        SourceView = view;
        Dpi = dpi;
        SetLayout(size, new Rectangle(Point.Empty, size));
    }
    public void SetLayout(Size size, Rectangle bounds) { MediaSize = size; DrawRectangle = bounds; }
    public void Dispose() { }
}

static class ViewCapture
{
    public static ViewCaptureSettings Recorded;
    public static bool ForPrinting, Preview;
    private static Bitmap CaptureToBitmap(ViewCaptureSettings settings, bool forPrinting, bool preview)
    {
        Recorded = settings;
        ForPrinting = forPrinting;
        Preview = preview;
        return new Bitmap();
    }
}


static class Program
{
    private const int RasterCaptureDpi = 144;
    // PRODUCTION_METHODS
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static void Reject(Action action, string message)
    {
        try { action(); }
        catch (InvalidOperationException) { return; }
        throw new Exception(message);
    }
    static void Main()
    {
        var paper = new RhinoViewport();
        var page = new RhinoPageView { MainViewport = paper, ActiveViewport = paper };
        var before = ImageViewState(page);
        Check(before["main"]["display_mode"].Type == JTokenType.Null, "paper mode must serialize as null");
        Check(before["active"]["display_mode"].Type == JTokenType.Null, "active paper mode must serialize as null");
        Check(paper.DisplayMode == null && page.ActiveViewport == paper, "observation must not set mode or activate a view");
        Check(JToken.DeepEquals(before, ImageViewState(page)), "unchanged paper snapshots differ");
        page.ActiveViewport = new RhinoViewport { Id = paper.Id };
        Check(JToken.DeepEquals(before, ImageViewState(page)), "paper identity must use viewport GUID, not wrapper reference");
        page.ActiveViewport = paper;
        paper.DisplayMode = new Mode();
        var withMode = ImageViewState(page);
        Check(!JToken.DeepEquals(before, withMode), "null to mode transition was hidden");
        Check((string)withMode["main"]["display_mode"] == "Wireframe", "existing mode lost");
        paper.DisplayMode = null;
        Check(!JToken.DeepEquals(withMode, ImageViewState(page)), "mode to null transition was hidden");
        var detail = new RhinoViewport { DisplayMode = new Mode { EnglishName = "Shaded" } };
        page.ActiveViewport = detail;
        Check((string)ImageViewState(page)["active"]["display_mode"] == "Shaded", "detail mode lost");
        var activeDetail = ImageViewState(page);
        var document = new RhinoDoc();
        var size = new Size(1684, 1191);
        Check(CaptureLayoutImage(document, page, size, 75) != null, "blank paper can be returned as a bitmap");
        var settings = ViewCapture.Recorded;
        Check(settings.SourceView == page && settings.Document == document, "capture must bind the original Layout and document");
        Check(settings.RasterMode && ViewCapture.ForPrinting && !ViewCapture.Preview, "Layout requires raster printing");
        Check(settings.OutputColor == ViewCaptureSettings.ColorMode.PrintColor && settings.UsePrintWidths, "paper print appearance lost");
        Check(settings.Dpi == 108 && settings.MediaSize == size &&
              settings.DrawRectangle == new Rectangle(Point.Empty, size), "Layout paper dimensions changed");
        Check(settings.DrawLockedObjects && !settings.DrawSelectedObjectsOnly, "Layout should include all visibly eligible objects");
        Check(page.ActiveViewport == detail && JToken.DeepEquals(activeDetail, ImageViewState(page)), "capture changed Layout view state");
        detail.DisplayMode = null;
        Reject(() => ImageViewState(page), "missing detail mode accepted");
        var model = new RhinoView { MainViewport = paper, ActiveViewport = paper };
        Reject(() => ImageViewState(model), "missing model mode accepted");
        Reject(() => ReadViewport(paper), "default caller lost strict mode validation");
        paper.DisplayMode = new Mode();
        Check((string)ImageViewState(model)["main"]["display_mode"] == "Wireframe", "model observation regressed");
        page.ActiveViewport = null;
        Reject(() => ImageViewState(page), "missing active viewport accepted");
        page.MainViewport = null;
        Reject(() => ImageViewState(page), "missing main viewport accepted");
        var source = new RhinoViewport { DisplayMode = new Mode(), ConstructionGridVisible = true };
        source.DisplayMode.DisplayAttributes.ShowClippingPlanes = true;
        source.DisplayMode.DisplayAttributes.ShowLights = true;
        model.MainViewport = source;
        model.ActiveViewport = source;
        var modelBefore = ImageViewState(model);
        var modelSize = new Size(640, 480);
        Check(CaptureModelImage(document, model, modelSize) != null, "missing model bitmap");
        var modelSettings = ViewCapture.Recorded;
        Check(modelSettings.SourceView == model && modelSettings.Document == document, "model capture lost its source view");
        Check(modelSettings.RasterMode && ViewCapture.ForPrinting && !ViewCapture.Preview, "model must use the settings-based raster pipeline");
        Check(modelSettings.OutputColor == ViewCaptureSettings.ColorMode.DisplayColor && !modelSettings.UsePrintWidths, "model inherited print styling");
        Check(modelSettings.ApplyDisplayModeThicknessScales && !modelSettings.MatchLinetypePatternDefinition, "model lost viewport line appearance");
        Check(modelSettings.MediaSize == modelSize && modelSettings.ViewArea == ViewCaptureSettings.ViewAreaMapping.View, "model lost view framing");
        Check(modelSettings.DrawGrid && !modelSettings.DrawAxis && modelSettings.DrawClippingPlanes &&
              modelSettings.DrawLights && modelSettings.DrawLockedObjects && !modelSettings.DrawSelectedObjectsOnly, "model capture changed visible scope");
        Check(JToken.DeepEquals(modelBefore, ImageViewState(model)), "model capture changed its source viewport");
        Console.WriteLine("PASS: distinct model/Layout raster settings and unchanged views");
    }
}
'''
