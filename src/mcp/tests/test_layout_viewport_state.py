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


def test_layout_paper_state_preserves_null_without_relaxing_model_or_detail(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source = (Path(__file__).parents[1] / "features/context/native/DocumentObservation.cs").read_text(encoding="utf-8")
    methods = "\n".join(method(source, name) for name in ("ImageViewState", "ReadViewport", "Coordinates", "Number"))
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
    assert "PASS: paper, model, detail, missing viewport, state changes" in run.stdout


HARNESS = r'''
using System;
using System.Drawing;
using Newtonsoft.Json.Linq;

sealed class Mode { public string EnglishName = "Wireframe"; }
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
}
class RhinoView { public RhinoViewport MainViewport, ActiveViewport; }
sealed class RhinoPageView : RhinoView { }

static class Program
{
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
        Console.WriteLine("PASS: paper, model, detail, missing viewport, state changes");
    }
}
'''
