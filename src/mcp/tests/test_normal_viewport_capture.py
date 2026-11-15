"""Execute the production capture boundary with SDK-free doubles, never Rhino.

These tests prove routing, source-state preservation, clipping snapshot checks and cleanup.
They do not prove the native renderer's pixels or the effect of global PrintDisplay.
"""
import os
from pathlib import Path
import re
import subprocess


def _member(source, name, *, kind="method"):
    prefix = r"(?:private|internal|public) (?:sealed )?class " if kind == "class" else r"(?:private|internal|public) static [^\r\n]*\b"
    suffix = r"\b" if kind == "class" else r"\("
    match = re.search(r"(?m)^        " + prefix + re.escape(name) + suffix, source)
    assert match, f"Production {kind} missing: {name}"
    opening = source.index("{", match.end())
    # Skip comments and quoted strings so braces inside error text cannot truncate a method.
    tokens = re.finditer(r'//[^\n]*|/\*[\s\S]*?\*/|@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', source[opening:])
    depth = 0
    for token in tokens:
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():opening + token.end()]
    raise AssertionError(f"Unbalanced production {kind}: {name}")


def test_normal_viewport_uses_detached_pipeline_and_preserves_source_state(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source = (Path(__file__).parents[1] / "features/context/native/DocumentObservation.cs").read_text(encoding="utf-8")
    _run_production_capture(source, tmp_path, sdk)


def _run_production_capture(source, tmp_path, sdk):
    members = "\n".join(_member(source, name) for name in (
        "CaptureImage", "CaptureModelViewport", "CaptureNormalViewport", "ApplyCaptureView"))
    members += "\n" + _member(source, "UnverifiedCaptureViewException", kind="class")
    (tmp_path / "Program.cs").write_text(HARNESS.replace("// PRODUCTION_MEMBERS", members), encoding="utf-8")
    project = tmp_path / "NormalCapture.csproj"
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable></PropertyGroup>
  <ItemGroup><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildBinPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    env = {**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
           "DOTNET_CLI_HOME": str(tmp_path / "dotnet-home")}
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert built.returncode == 0, built.stdout + built.stderr
    run = subprocess.run([sdk, str(tmp_path / "bin/Release/net8.0/NormalCapture.dll")],
                         env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS: current, custom, override, fallback, named, clipping, focus, layout, cleanup" in run.stdout


HARNESS = r'''
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Newtonsoft.Json.Linq;
using Bitmap = FixtureBitmap;

sealed class FixtureBitmap : IDisposable {
    public int Width, Height;
    public bool Disposed;
    public FixtureBitmap(int width = 800, int height = 600) { Width = width; Height = height; }
    public void Dispose() { Disposed = true; }
}
sealed class DisplayAttributes { public Guid RealtimeDisplayId; }
sealed class DisplayModeDescription : IDisposable {
    public string EnglishName;
    public Guid Id = Guid.NewGuid();
    public DisplayAttributes DisplayAttributes = new DisplayAttributes();
    public bool Disposed;
    public int DisposeCount;
    public void Dispose() { Disposed = true; DisposeCount++; }
    public DisplayModeDescription Copy() => new DisplayModeDescription {
        Id = Id, EnglishName = EnglishName, DisplayAttributes = DisplayAttributes };
    public static DisplayModeDescription[] Modes = Array.Empty<DisplayModeDescription>();
    public static DisplayModeDescription GetDisplayMode(Guid id) => Modes.SingleOrDefault(mode => mode.Id == id);
    public static DisplayModeDescription FindByName(string name) => Modes.SingleOrDefault(mode => mode.EnglishName == name);
    public static DisplayModeDescription[] GetDisplayModes() => Modes;
}
sealed class RhinoViewport {
    public Guid Id = Guid.NewGuid();
    public Size Size = new Size(320, 240);
    public Guid[] ClippingIds = Array.Empty<Guid>();
    public int SectionBehavior = 2;
    public string Projection = "source-camera";
    public DisplayModeDescription StoredMode;
    public List<DisplayModeDescription> ModeCopies = new List<DisplayModeDescription>();
    public DisplayModeDescription DisplayMode {
        get {
            var copy = StoredMode?.Copy();
            if (copy != null) ModeCopies.Add(copy);
            return copy;
        }
        set { StoredMode = value?.Copy(); }
    }
    public bool ProjectionSucceeds = true, ZoomSucceeds = true;
    public bool ConstructionGridVisible = true, ConstructionAxesVisible = true, WorldAxesVisible = true;
    public string ConstructionPlane = "source-plane";
    public string GetConstructionPlane() => ConstructionPlane;
    public void SetConstructionPlane(string plane) { ConstructionPlane = plane; }
    public bool SetViewProjection(ViewportInfo source, bool updateTarget) {
        Projection = source.Projection;
        return ProjectionSucceeds;
    }
    public bool PushViewInfo(ViewInfo info, bool updateTarget) {
        Program.PushCount++;
        if (updateTarget) throw new Exception("Snapshot application changed the requested target contract");
        if (Program.Fail == "push") throw new InvalidOperationException("fixture snapshot application failure");
        if (Program.Fail == "push-rejected") return false;
        Projection = info.Viewport.Projection;
        Size = info.Viewport.Size;
        ClippingIds = (info.ClippingPlanesIds ?? Array.Empty<Guid>()).ToArray();
        SectionBehavior = info.SectionBehavior;
        if (Program.Fail == "clip-drop") ClippingIds = ClippingIds.Skip(1).ToArray();
        if (Program.Fail == "clip-extra") ClippingIds = ClippingIds.Concat(new[] { Guid.NewGuid() }).ToArray();
        if (Program.Fail == "clip-reorder") Array.Reverse(ClippingIds);
        if (Program.Fail == "section-behavior") SectionBehavior++;
        if (Program.Fail == "identity-copy") Id = info.Viewport.Id;
        if (Program.Fail == "identity-change") Id = Guid.NewGuid();
        return true;
    }
    public bool ZoomBoundingBox(BoundingBox bounds) {
        Program.FocusCount++;
        Projection = "focus-camera";
        return ZoomSucceeds;
    }
}
sealed class ViewportInfo : IDisposable {
    public string Projection;
    public Guid Id;
    public Size Size;
    public ViewportInfo(RhinoViewport viewport) { Projection = viewport.Projection; Id = viewport.Id; Size = viewport.Size; }
    public void Dispose() { }
}
sealed class ViewInfo : IDisposable {
    public ViewportInfo Viewport;
    public Guid[] ClippingPlanesIds = Array.Empty<Guid>();
    public int SectionBehavior;
    public bool Disposed;
    public static List<ViewInfo> Owned = new List<ViewInfo>();
    public ViewInfo() { }
    public ViewInfo(RhinoViewport source) {
        if (Program.Fail == "source-snapshot" && source == Program.SourceViewport)
            throw new InvalidOperationException("fixture source snapshot failure");
        if (Program.Fail == "applied-snapshot" && source != Program.SourceViewport)
            throw new InvalidOperationException("fixture applied snapshot failure");
        Viewport = new ViewportInfo(source);
        ClippingPlanesIds = source.ClippingIds.ToArray();
        SectionBehavior = source.SectionBehavior;
        Owned.Add(this);
    }
    public void Dispose() { Disposed = true; }
}
class RhinoView {
    public RhinoViewport MainViewport, ActiveViewport;
    public Bitmap CaptureToBitmap(Size size) => throw new Exception("Live current-view fastpath is forbidden");
    public Bitmap CaptureToBitmap(Size size, DisplayModeDescription mode) => throw new Exception("Live mode-override fastpath is forbidden");
}
sealed class RhinoPageView : RhinoView { }
sealed class ViewTable { public RhinoView ActiveView; }
sealed class RhinoDoc {
    public static RhinoDoc ActiveDoc;
    public uint RuntimeSerialNumber = 17;
    public bool Modified = true;
    public ViewTable Views = new ViewTable();
}
struct BoundingBox {
    public bool IsValid;
    public static BoundingBox Empty => new BoundingBox();
    public void Union(BoundingBox other) { IsValid |= other.IsValid; }
}
static class ObservationEntities {
    public sealed class Entity { public BoundingBox Bounds; }
    public static List<Entity> ModelObjects(RhinoDoc doc) => new List<Entity>();
    public static List<Entity> Roots(RhinoDoc doc, List<Entity> entities) => entities;
    public static void DrawLabels(RhinoDoc doc, Bitmap bitmap, RhinoViewport viewport,
        List<Entity> entities, int depth, JArray warnings) {
        Program.LabelCount++;
        if (Program.Fail == "labels") throw new InvalidOperationException("fixture labels failure");
    }
}
sealed class CaptureViewportControl : IDisposable {
    public static CaptureViewportControl Last;
    public bool Visible;
    public Size Size;
    public bool Disposed;
    public IntPtr Handle => IntPtr.Zero;
    public RhinoViewport Viewport = new RhinoViewport();
    public DisplayPipeline Display = new DisplayPipeline();
    public CaptureViewportControl() {
        Last = this;
        Program.ControlCount++;
        if (Program.Fail == "identity-empty") Viewport.Id = Guid.Empty;
        if (Program.Fail == "identity-collision") Viewport.Id = Program.SourceViewport.Id;
    }
    public void InitializeCapturePipeline() {
        if (Program.Fail == "initialize") throw new InvalidOperationException("fixture initialize failure");
    }
    public void Dispose() { Disposed = true; }
}
sealed class DisplayPipeline {
    public bool IsOpen;
    public bool Open() {
        Program.OpenCount++;
        if (Program.Fail == "open") return false;
        IsOpen = true;
        return true;
    }
    public void Close() {
        Program.CloseCount++;
        IsOpen = false;
        if (Program.Fail == "close") throw new InvalidOperationException("fixture close failure");
    }
    public static Bitmap DrawToBitmap(RhinoViewport viewport, int width, int height) {
        Program.DrawCount++;
        Program.RenderedViewport = viewport;
        if (Program.Fail == "draw") throw new InvalidOperationException("fixture draw failure");
        Program.LastBitmap = Program.Fail == "null-bitmap" ? null : new Bitmap(width, height);
        return Program.LastBitmap;
    }
}
sealed class ViewCaptureSettings : IDisposable {
    public enum ColorMode { DisplayColor, PrintColor }
    public RhinoDoc Document;
    public bool RasterMode, UsePrintWidths, DrawBackground;
    public string HeaderText, FooterText;
    public ColorMode OutputColor;
    public bool Disposed;
    public static ViewCaptureSettings Last;
    public ViewCaptureSettings(RhinoPageView page, double dpi) { Last = this; }
    public void SetLayout(Size size, Rectangle rectangle) { }
    public void Dispose() { Disposed = true; }
}
static class ViewCapture {
    private static Bitmap CaptureToBitmap(ViewCaptureSettings settings, bool forPrinting, bool preview) {
        if (!forPrinting || preview || !settings.UsePrintWidths || settings.OutputColor != ViewCaptureSettings.ColorMode.PrintColor)
            throw new Exception("Layout printing contract lost");
        Program.PrintCount++;
        return new Bitmap();
    }
}
static class DisplayModeId { public static Guid Shaded = Guid.Parse("00000000-0000-0000-0000-000000000001"); }

static class Program {
    const double LayoutDpi = 144.0;
    public static string Fail;
    public static int ControlCount, OpenCount, CloseCount, DrawCount, LabelCount, FocusCount, PrintCount, PushCount;
    public static RhinoViewport RenderedViewport;
    public static RhinoViewport SourceViewport;
    public static Bitmap LastBitmap;
    // PRODUCTION_MEMBERS
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static Exception Reject(Action action, string message) {
        try { action(); } catch (Exception ex) { return ex; }
        throw new Exception(message);
    }
    static void Reset() {
        Fail = null;
        ControlCount = OpenCount = CloseCount = DrawCount = LabelCount = FocusCount = PrintCount = PushCount = 0;
        RenderedViewport = null;
        LastBitmap = null;
        CaptureViewportControl.Last = null;
        ViewInfo.Owned.Clear();
    }
    static Bitmap Capture(RhinoDoc doc, RhinoView view, DisplayModeDescription mode = null,
        ViewInfo named = null, bool labels = false, List<ObservationEntities.Entity> entities = null) =>
        CaptureImage(doc, view, named, new Size(800, 600), new Size(800, 600), 100, mode, labels, 1, entities, new JArray());
    static void Preserved(RhinoDoc doc, RhinoViewport source, DisplayModeDescription original, string camera) {
        Check(source.StoredMode?.Id == original.Id && source.Projection == camera && doc.Modified,
            "Source mode/camera/document state was modified");
        Check(source.ModeCopies.All(copy => copy.Disposed && copy.DisposeCount == 1),
            "A source DisplayMode getter copy was leaked or disposed more than once");
        Check(!original.Disposed, "A borrowed mode was disposed instead of its getter copy");
        Check(ViewInfo.Owned.All(info => info.Disposed), "An owned full view snapshot was leaked");
    }
    static void Cleaned(string scenario) {
        Check(CaptureViewportControl.Last != null && CaptureViewportControl.Last.Disposed, scenario + ": control leaked");
        Check(CloseCount == 1, scenario + ": acquired pipeline not closed once");
    }
    static void Main() {
        var shaded = new DisplayModeDescription { Id = DisplayModeId.Shaded, EnglishName = "Shaded" };
        var custom = new DisplayModeDescription { EnglishName = "AGENT_Section_Glass" };
        var explicitMode = new DisplayModeDescription { EnglishName = "Technical" };
        DisplayModeDescription.Modes = new[] { shaded, custom, explicitMode };
        var source = new RhinoViewport { DisplayMode = custom };
        SourceViewport = source;
        var sourceId = source.Id;
        var view = new RhinoView { MainViewport = source, ActiveViewport = source };
        var doc = new RhinoDoc { Views = new ViewTable { ActiveView = view } };
        RhinoDoc.ActiveDoc = doc;

        Reset();
        using (Capture(doc, view)) { }
        Check(DrawCount == 1 && PrintCount == 0 && RenderedViewport != source, "Current capture did not use independent drawing");
        Check(RenderedViewport.StoredMode.Id == custom.Id && RenderedViewport.Projection == source.Projection, "Current custom mode/camera lost");
        Check(PushCount == 1 && source.Id == sourceId && RenderedViewport.Id != sourceId,
            "Full view snapshot was not applied or source viewport identity was copied");
        Check(RenderedViewport.Size == new Size(800, 600), "Source screen port replaced the requested output size");
        Preserved(doc, source, custom, "source-camera");
        Cleaned("current");
        Check(source.ModeCopies.Count == 1 && source.ModeCopies[0].Disposed, "Current fallback getter copy was not released");

        Reset();
        using (Capture(doc, view, explicitMode)) { }
        Check(RenderedViewport.StoredMode.Id == explicitMode.Id, "Explicit mode ignored");
        Check(!explicitMode.Disposed && source.ModeCopies.Count == 1, "An explicit caller mode was disposed or caused an unnecessary source-mode read");
        Preserved(doc, source, custom, "source-camera");

        Reset();
        using (CaptureModelViewport(doc, source, new Size(800, 600), custom, false)) { }
        Check(DrawCount == 1 && RenderedViewport.StoredMode.Id == custom.Id, "Conditioning capture bypassed the normal path");
        Check(!custom.Disposed, "Conditioning capture disposed its caller's mode");
        Check(!RenderedViewport.ConstructionGridVisible && !RenderedViewport.ConstructionAxesVisible && !RenderedViewport.WorldAxesVisible,
            "Grid-free capture changed routing or left overlays");
        Check(source.ConstructionGridVisible && source.ConstructionAxesVisible && source.WorldAxesVisible, "Source grid flags changed");
        Check(RenderedViewport.ConstructionPlane == source.ConstructionPlane, "Construction plane was lost");

        Reset();
        source.DisplayMode = null;
        var fallback = Reject(() => Capture(doc, view), "A missing source mode must use an explicit validated fallback or reject");
        Check(fallback is NotSupportedException, "Missing current display mode returned an unrelated error");
        Check(DrawCount == 0, "Missing source mode silently rendered the detached default");
        source.DisplayMode = custom;

        Reset();
        var realtime = new DisplayModeDescription { EnglishName = "Raytraced",
            DisplayAttributes = new DisplayAttributes { RealtimeDisplayId = Guid.NewGuid() } };
        source.DisplayMode = realtime;
        Check(Reject(() => Capture(doc, view), "Realtime current mode unexpectedly captured") is NotSupportedException,
            "Realtime current mode returned an unrelated error");
        Check(DrawCount == 0 && ControlCount == 0, "Realtime current mode entered raster drawing");
        Check(source.ModeCopies.Last().Disposed && !realtime.Disposed, "Rejected realtime source mode leaked its getter copy or disposed the borrowed mode");
        source.DisplayMode = custom;
        Check(Reject(() => CaptureModelViewport(doc, source, new Size(800, 600), realtime), "Explicit realtime mode unexpectedly captured") is NotSupportedException,
            "Explicit realtime mode returned an unrelated error");
        Check(DrawCount == 0 && ControlCount == 0, "Explicit realtime mode entered raster drawing");
        Check(!realtime.Disposed, "Rejected explicit realtime mode was disposed by its borrower");

        Reset();
        var named = new ViewInfo { Viewport = new ViewportInfo(new RhinoViewport { Projection = "named-camera" }) };
        using (Capture(doc, null, explicitMode, named)) { }
        Check(RenderedViewport.Projection == "named-camera" && RenderedViewport.StoredMode.Id == explicitMode.Id, "Named camera/mode lost");
        Check(!named.Disposed, "A borrowed saved view snapshot was disposed");
        Preserved(doc, source, custom, "source-camera");

        Reset();
        var clipA = Guid.NewGuid();
        var clipB = Guid.NewGuid();
        source.ClippingIds = new[] { clipA, clipB };
        using (Capture(doc, view)) { }
        Check(DrawCount == 1 && RenderedViewport.ClippingIds.SequenceEqual(source.ClippingIds) &&
            RenderedViewport.SectionBehavior == source.SectionBehavior, "Accepted current clipping snapshot was not retained");
        Check(source.Id == sourceId && RenderedViewport.Id != sourceId, "Current clipping copied the source viewport identity");
        Preserved(doc, source, custom, "source-camera");

        Reset();
        named.ClippingPlanesIds = new[] { Guid.NewGuid() };
        using (Capture(doc, null, explicitMode, named)) { }
        Check(DrawCount == 1 && RenderedViewport.ClippingIds.SequenceEqual(named.ClippingPlanesIds) &&
            RenderedViewport.SectionBehavior == named.SectionBehavior, "Saved clipping snapshot was replaced with the active view's clipping");
        Check(!named.Disposed, "A borrowed clipping snapshot was disposed");
        Preserved(doc, source, custom, "source-camera");

        Reset();
        named.ClippingPlanesIds = null;
        using (Capture(doc, null, explicitMode, named)) { }
        Check(DrawCount == 1 && RenderedViewport.ClippingIds.Length == 0,
            "An unclipped saved view incorrectly inherited clipping from the active model view");

        Reset();
        Fail = "clip-reorder";
        using (Capture(doc, view)) { }
        Check(DrawCount == 1 && new HashSet<Guid>(RenderedViewport.ClippingIds).SetEquals(source.ClippingIds),
            "Equivalent clipping ID association order was incorrectly rejected");

        foreach (var failure in new[] { "identity-empty", "identity-collision", "push-rejected", "clip-drop", "clip-extra", "section-behavior", "identity-copy", "identity-change" }) {
            Reset();
            Fail = failure;
            var error = Reject(() => Capture(doc, view), failure + ": unverified view snapshot returned an image");
            Check(error is UnverifiedCaptureViewException && DrawCount == 0,
                failure + ": invalid snapshot was not rejected before native drawing");
            Check(CaptureViewportControl.Last.Disposed && CloseCount == 0,
                failure + ": invalid snapshot leaked its control or opened the display pipeline");
            if (failure == "identity-empty" || failure == "identity-collision")
                Check(PushCount == 0, failure + ": invalid independent identity was accepted before applying view settings");
            Check(source.Id == sourceId && source.ClippingIds.SequenceEqual(new[] { clipA, clipB }),
                failure + ": snapshot validation modified the source identity or clipping");
            Preserved(doc, source, custom, "source-camera");
        }

        foreach (var failure in new[] { "source-snapshot", "applied-snapshot", "push" }) {
            Reset();
            Fail = failure;
            Reject(() => Capture(doc, view), failure + ": failed snapshot silently fell through to capture");
            Check(DrawCount == 0 && CaptureViewportControl.Last.Disposed,
                failure + ": failed snapshot produced an image or leaked its control");
            Preserved(doc, source, custom, "source-camera");
        }

        Reset();
        RhinoDoc.ActiveDoc = null;
        Reject(() => Capture(doc, view), "A changed active document unexpectedly captured");
        Check(ControlCount == 0 && DrawCount == 0, "A changed active document entered drawing");
        RhinoDoc.ActiveDoc = doc;
        Reject(() => CaptureModelViewport(doc, null, new Size(800, 600), custom), "A missing source unexpectedly captured");
        Reject(() => CaptureModelViewport(doc, source, Size.Empty, custom), "An empty capture size unexpectedly captured");
        Check(ControlCount == 0 && DrawCount == 0, "Invalid capture arguments entered drawing");

        Reset();
        var entities = new List<ObservationEntities.Entity> { new ObservationEntities.Entity { Bounds = new BoundingBox { IsValid = true } } };
        using (Capture(doc, view, entities: entities, labels: true)) { }
        Check(FocusCount == 1 && LabelCount == 1 && RenderedViewport.Projection == "focus-camera", "Focus/labels path lost");
        Preserved(doc, source, custom, "source-camera");

        foreach (var failure in new[] { "open", "draw", "labels" }) {
            Reset();
            Fail = failure;
            Reject(() => Capture(doc, view, labels: true), failure + ": capture unexpectedly succeeded");
            Cleaned(failure);
            if (failure == "labels") Check(LastBitmap != null && LastBitmap.Disposed, "Failed label rendering leaked the native bitmap");
            Preserved(doc, source, custom, "source-camera");
        }
        Reset();
        Fail = "initialize";
        Reject(() => Capture(doc, view), "Initialization failure unexpectedly succeeded");
        Check(CaptureViewportControl.Last.Disposed && CloseCount == 0, "Initialization failure leaked control or closed an unacquired pipeline");
        Reset();
        Fail = "null-bitmap";
        Check(Capture(doc, view) == null, "Null native bitmap turned into invented success");
        Cleaned("null bitmap");

        Reset();
        Fail = "close";
        Reject(() => Capture(doc, view), "Pipeline cleanup failure unexpectedly returned an image");
        Check(LastBitmap != null && LastBitmap.Disposed && CaptureViewportControl.Last.Disposed,
            "Pipeline cleanup failure leaked the completed bitmap or viewport control");
        Preserved(doc, source, custom, "source-camera");

        Reset();
        var page = new RhinoPageView { MainViewport = source, ActiveViewport = source };
        using (Capture(doc, page)) { }
        Check(PrintCount == 1 && DrawCount == 0 && ControlCount == 0 && ViewCaptureSettings.Last.Disposed,
            "Layout no longer has its separate printing branch or leaked settings");
        Preserved(doc, source, custom, "source-camera");

        Console.WriteLine("PASS: current, custom, override, fallback, named, clipping, focus, layout, cleanup");
    }
}
'''
