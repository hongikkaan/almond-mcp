"""Live mode choices and the existing custom-mode resolver, without running Rhino."""
import asyncio
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from fastmcp import Client, FastMCP

from almond_mcp.features.context.tools import register
from test_layout_viewport_state import method


def test_capture_descriptions_explain_mode_choices_and_object_framing():
    async def catalogue():
        mcp = FastMCP("capture-mode-guidance")
        register(mcp, SimpleNamespace())
        async with Client(mcp) as client:
            return {tool.name: tool for tool in await client.list_tools()}

    tools = asyncio.run(catalogue())
    for name in ("capture_02-inspection", "capture_03-current_view", "capture_04-defined_view"):
        description = tools[name].description
        for choice in ("Wireframe", "Shaded", "Rendered", "Ghosted", "X-Ray", "Technical", "Arctic"):
            assert choice in description
        assert "사용자 정의" in description and "GUID" in description
        assert 'sections=["display_modes"]' in description
        assert "capture_supported=true" in description

    inspection = tools["capture_02-inspection"].description
    assert 'object_ids=["객체 GUID"]' in inspection
    assert "front" in inspection and "right" in inspection
    assert "direction=current는 현재 카메라를 유지" in inspection
    assert "두 방식을 함께 사용하지 않습니다" in inspection
    assert "카메라·선택·표시 모드는 유지" in inspection


def test_installed_mode_catalogue_refreshes_and_custom_names_and_guids_resolve(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source = (Path(__file__).parents[1] / "features/context/native/DocumentObservation.cs").read_text(encoding="utf-8")
    methods = "\n".join(method(source, name) for name in ("ResolveDisplayMode", "DisplayModes"))
    (tmp_path / "Program.cs").write_text(HARNESS.replace("// PRODUCTION_METHODS", methods), encoding="utf-8")
    project = tmp_path / "CaptureModes.csproj"
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk">
      <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable></PropertyGroup>
      <ItemGroup><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildBinPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup>
    </Project>''', encoding="utf-8")
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert built.returncode == 0, built.stdout + built.stderr
    run = subprocess.run([sdk, str(tmp_path / "bin/Release/net8.0/CaptureModes.dll")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS: live choices, custom names/GUIDs, ambiguity, realtime, bounded catalogue" in run.stdout


HARNESS = r'''
using System;
using System.Linq;
using Newtonsoft.Json.Linq;

sealed class Attributes { public Guid RealtimeDisplayId; }
sealed class DisplayModeDescription {
    public Guid Id = Guid.NewGuid();
    public string EnglishName;
    public string LocalName;
    public Attributes DisplayAttributes = new Attributes();
    public static DisplayModeDescription[] Modes = Array.Empty<DisplayModeDescription>();
    public static DisplayModeDescription[] GetDisplayModes() => Modes;
    public static DisplayModeDescription GetDisplayMode(Guid id) => Modes.SingleOrDefault(m => m.Id == id);
}
static class Program {
    // PRODUCTION_METHODS
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static void Main() {
        var custom = new DisplayModeDescription { EnglishName = "AGENT_Section_Glass", LocalName = "사용자 단면 유리" };
        var realtime = new DisplayModeDescription { EnglishName = "Raytraced", LocalName = "광선 추적",
            DisplayAttributes = new Attributes { RealtimeDisplayId = Guid.NewGuid() } };
        DisplayModeDescription.Modes = new[] { custom, realtime };
        var warnings = new JArray();
        var choices = DisplayModes(warnings);
        Check(choices.Count == 2 && warnings.Count == 0, "installed choices missing");
        Check((string)choices[0]["name"] == custom.EnglishName && (string)choices[0]["local_name"] == custom.LocalName,
            "custom/local names lost");
        Check((string)choices[0]["id"] == custom.Id.ToString() && (bool)choices[0]["capture_supported"], "raster choice unavailable");
        Check(!(bool)choices[1]["capture_supported"], "realtime mode must not be advertised as independent capture support");
        Check(ResolveDisplayMode("agent_section_glass") == custom && ResolveDisplayMode(custom.LocalName) == custom &&
            ResolveDisplayMode(custom.Id.ToString()) == custom, "custom name/local name/GUID did not resolve");
        Check(ResolveDisplayMode("missing") == null, "unknown mode accepted");
        var second = new DisplayModeDescription { EnglishName = custom.EnglishName, LocalName = "다른 이름" };
        DisplayModeDescription.Modes = new[] { custom, second };
        Check(ResolveDisplayMode(custom.EnglishName) == null, "ambiguous name must require GUID");
        Check(ResolveDisplayMode(second.Id.ToString()) == second, "GUID must distinguish duplicate names");
        second.EnglishName = "새 사용자 모드";
        DisplayModeDescription.Modes = new[] { second };
        choices = DisplayModes(new JArray());
        Check(choices.Count == 1 && (string)choices[0]["name"] == second.EnglishName, "catalogue is stale after mode edits");
        Check(ResolveDisplayMode(custom.Id.ToString()) == null, "removed mode still resolves");
        DisplayModeDescription.Modes = Enumerable.Range(0, 129).Select(i => new DisplayModeDescription {
            EnglishName = "Mode" + i, LocalName = "Mode" + i }).ToArray();
        warnings = new JArray();
        Check(DisplayModes(warnings).Count == 128 && warnings.Count == 1, "catalogue bound or truncation warning lost");
        Console.WriteLine("PASS: live choices, custom names/GUIDs, ambiguity, realtime, bounded catalogue");
    }
}
'''
