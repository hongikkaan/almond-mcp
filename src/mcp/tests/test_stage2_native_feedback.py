"""Source-linked native result contracts with table/Rhino boundary doubles.

These tests do not reproduce Rhino's zoom algorithm or replace the Windows SDK,
ScriptExecutor, and live-document checks in the regular development test run.
"""
import json
import os
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape

import pytest
from fastmcp import FastMCP
from jsonschema import validate

from almond_mcp.features.modeling.tools import register as register_modeling
from almond_mcp.output_contracts import public_output_schema
from test_modeling_setup import context as modeling_context
from test_view_capture import capture_tools, invoke


def build_host(directory, code, sources):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source_root = Path(__file__).resolve().parents[1]
    links = "".join(f'<Compile Include="{escape(str(source_root / source))}" />' for source in sources)
    project = directory / "NativeFeedback.csproj"
    project.write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
      <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>
        <Nullable>disable</Nullable></PropertyGroup>
      <ItemGroup>{links}<Reference Include="Newtonsoft.Json">
        <HintPath>$(MSBuildSDKsPath)/../Newtonsoft.Json.dll</HintPath><Private>true</Private>
      </Reference></ItemGroup></Project>""", encoding="utf-8")
    (directory / "Program.cs").write_text(code, encoding="utf-8")
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert built.returncode == 0, built.stdout + built.stderr

    def run(scenario):
        completed = subprocess.run([sdk, str(directory / "bin/Release/net8.0/NativeFeedback.dll"), scenario],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return json.loads(completed.stdout)
    return run


@pytest.fixture(scope="module")
def setup_host(tmp_path_factory):
    return build_host(tmp_path_factory.mktemp("setup_feedback"), r'''
using System;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using RhinoAlmondBridge;
class Program {
    static void Main(string[] args) {
        string scenario = args[0]; int reads = 0;
        var recipe = new JObject { ["name"]="Oak", ["base_color"]=new JArray(10,20,30),
            ["metallic"]=0.0, ["roughness"]=0.5, ["opacity"]=1.0 };
        var materials = new JArray();
        if (scenario == "preserved" || scenario == "updated" || scenario == "unchanged") {
            var existing = (JObject)recipe.DeepClone(); existing["type"]="pbr";
            if (scenario != "unchanged") existing["roughness"]=0.2;
            materials.Add(existing);
        }
        JObject layer = null;
        var spec = new JObject { ["path"]="M::wood", ["color"]=new JArray(10,20,30), ["material"]=recipe.DeepClone() };
        var result = ModelingSetup.Apply(new JArray(recipe), new JArray(spec), scenario == "updated" || scenario == "unchanged",
            r => {
                reads++;
                if (scenario == "lookup_failed" || (scenario == "verification_failed" && reads == 2))
                    throw new Exception("Material lookup unavailable");
                return (JArray)materials.DeepClone();
            },
            r => {
                var material = (JObject)r.DeepClone(); material["type"]="pbr"; materials.Clear(); materials.Add(material);
                if (scenario == "write_failed") throw new Exception("Write acknowledgement unavailable");
            },
            s => { if (scenario == "layer_lookup_failed") throw new Exception("Layer lookup unavailable"); return layer; },
            s => { if (scenario != "refused") layer = new JObject { ["color"]=s["color"].DeepClone(),
                ["plot_color"]=s["color"].DeepClone(), ["material"]="Oak" }; });
        Console.WriteLine(result.ToString(Formatting.None));
    }
}''', ["features/modeling/native/ModelingSetup.cs"])


def test_failed_initial_observation_does_not_claim_zero_records(setup_host):
    result = setup_host("lookup_failed")
    assert result["applied"] is False
    assert result["changes"] == [
        {"kind": "material", "name": "Oak", "action": "skipped", "previous_count": None, "current_count": None},
        {"kind": "layer", "name": "M::wood", "action": "skipped", "previous_count": None, "current_count": None},
    ]


@pytest.mark.parametrize("scenario", ["write_failed", "verification_failed"])
def test_write_or_verification_failure_keeps_known_before_and_unknown_after(setup_host, scenario):
    result = setup_host(scenario)
    assert result["changes"][0] == {
        "kind": "material", "name": "Oak", "action": "unconfirmed", "previous_count": 0, "current_count": None,
    }
    assert result["changes"][1] == {
        "kind": "layer", "name": "M::wood", "action": "skipped", "previous_count": None, "current_count": None,
    }


def test_missing_layer_read_is_unknown_but_verified_refusal_is_zero(setup_host):
    failed = setup_host("layer_lookup_failed")
    assert failed["changes"][1]["previous_count"] is None
    refused = setup_host("refused")
    assert refused["applied"] is False
    assert refused["changes"][1] == {
        "kind": "layer", "name": "M::wood", "action": "unchanged", "previous_count": 0, "current_count": 0,
    }


def test_confirmed_creations_are_reported_independently_of_other_targets(setup_host):
    result = setup_host("refused")
    assert result["applied"] is False
    assert result["changes"][0] == {
        "kind": "material", "name": "Oak", "action": "created", "previous_count": 0, "current_count": 1,
    }


def test_incomplete_preserved_properties_do_not_hide_new_layer_creation(setup_host):
    result = setup_host("preserved")
    assert result["applied"] is False and result["errors"] == []
    assert result["differences"] == [{"kind": "material", "name": "Oak", "property": "roughness", "current": 0.2, "expected": 0.5}]
    assert result["changes"] == [
        {"kind": "material", "name": "Oak", "action": "preserved", "previous_count": 1, "current_count": 1},
        {"kind": "layer", "name": "M::wood", "action": "created", "previous_count": 0, "current_count": 1},
    ]


@pytest.mark.parametrize("scenario", ["updated", "unchanged"])
def test_same_count_distinguishes_updated_and_unchanged_values(setup_host, scenario):
    result = setup_host(scenario)
    assert result["applied"] is True
    assert result["changes"][0] == {
        "kind": "material", "name": "Oak", "action": scenario, "previous_count": 1, "current_count": 1,
    }


@pytest.fixture(scope="module")
def focus_host(tmp_path_factory):
    return build_host(tmp_path_factory.mktemp("focus_feedback"), r'''
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Display;
using Rhino.Geometry;
using RhinoAlmondBridge;

// Native boundary doubles expose controlled acknowledgements and observations.
// The production focus/capture orchestration is linked without source rewriting.
namespace Rhino.Geometry {
    public struct Point3d {
        public double X,Y,Z;
        public Point3d(double x,double y,double z) { X=x;Y=y;Z=z; }
    }
    public struct BoundingBox {
        public bool IsValid; public Point3d Min,Max;
        public static BoundingBox Empty => new BoundingBox();
        public void Union(BoundingBox b) {
            if (!b.IsValid) return;
            if (!IsValid) { this=b; return; }
            Min=new Point3d(Math.Min(Min.X,b.Min.X),Math.Min(Min.Y,b.Min.Y),Math.Min(Min.Z,b.Min.Z));
            Max=new Point3d(Math.Max(Max.X,b.Max.X),Math.Max(Max.Y,b.Max.Y),Math.Max(Max.Z,b.Max.Z));
        }
    }
    public class GeometryBase {
        public BoundingBox Bounds; public bool FailBounds;
        public BoundingBox GetBoundingBox(bool accurate) {
            if (FailBounds) throw new Exception("Bounds unavailable"); return Bounds;
        }
    }
}
namespace Rhino.DocObjects {
    public enum ActiveSpace { ModelSpace }
    public class ObjectAttributes { public ActiveSpace Space; }
    public class RhinoObject {
        public Guid Id=Guid.NewGuid(); public bool IsDeleted,IsInstanceDefinitionGeometry,Selected,FailSelect;
        public ObjectAttributes Attributes=new ObjectAttributes(); public GeometryBase Geometry=new GeometryBase();
        public bool IsSelectable(bool a,bool b,bool c,bool d) => true;
        public int Select(bool a,bool b,bool c,bool d,bool e,bool f) { Selected=!FailSelect; return Selected?1:0; }
    }
    public class Group { public bool IsDeleted; public int Index; }
    public class ViewInfo { public string Name; public Guid NamedViewId; }
}
namespace Rhino.Display {
    public enum ViewTypeFilter { Page }
    public class DisplayAttributes { public Guid RealtimeDisplayId; }
    public class DisplayModeDescription {
        public Guid Id=Guid.NewGuid(); public string EnglishName="Shaded",LocalName="Shaded";
        public DisplayAttributes DisplayAttributes=new DisplayAttributes();
        public static DisplayModeDescription[] Modes={ new DisplayModeDescription() };
        public static DisplayModeDescription[] GetDisplayModes() => Modes;
    }
    public class RhinoViewport {
        public Guid Id=Guid.NewGuid(); public string Name="Perspective";
        public bool IsParallelProjection=true,ZoomResult,FailCamera,FailDisplay;
        public Point3d CameraLocation { get { if(FailCamera) throw new Exception("Camera unavailable"); return new Point3d(231000,200000,1000); } }
        public Point3d CameraTarget => new Point3d(231000,200000,0);
        DisplayModeDescription mode=new DisplayModeDescription();
        public DisplayModeDescription DisplayMode { get=>mode; set { if(FailDisplay) throw new Exception("Mode acknowledgement unavailable"); mode=value; } }
        public bool ZoomExtentsSelected() => ZoomResult;
        public bool GetFrustum(out double l,out double r,out double b,out double t,out double n,out double f) {
            l=-100;r=100;b=-75;t=75;n=1;f=10000;return true;
        }
    }
    public class RhinoView { public RhinoViewport ActiveViewport=new RhinoViewport(); public RhinoViewport MainViewport=>ActiveViewport; }
    public class RhinoPageView:RhinoView { }
}
namespace Rhino.Commands { public class Command { public static bool InCommand()=>false; } }
namespace Rhino {
    public class ObjectTable {
        public List<RhinoObject> Items=new List<RhinoObject>();
        public RhinoObject FindId(Guid id)=>Items.SingleOrDefault(o=>o.Id==id);
        public void UnselectAll() { foreach(var o in Items) o.Selected=false; }
        public IEnumerable<RhinoObject> GetSelectedObjects(bool a,bool b)=>Items.Where(o=>o.Selected);
    }
    public class ViewTable {
        public RhinoView ActiveView=new RhinoView(); public bool FailRedraw;
        public void Redraw() { if(FailRedraw) throw new Exception("Redraw unavailable"); }
        public RhinoView[] GetViewList(ViewTypeFilter f)=>Array.Empty<RhinoView>();
    }
    public class GroupTable {
        public Group FindId(Guid id)=>null;
        public RhinoObject[] GroupMembers(int index)=>Array.Empty<RhinoObject>();
    }
    public class RhinoDoc {
        public static RhinoDoc ActiveDoc; public bool IsHeadless,IsReadOnly,UndoRecordingIsActive,UndoActive,RedoActive;
        public uint RuntimeSerialNumber=1; public string Path="fixture.3dm";
        public ObjectTable Objects=new ObjectTable(); public ViewTable Views=new ViewTable();
        public GroupTable Groups=new GroupTable(); public ViewInfo[] NamedViews=Array.Empty<ViewInfo>();
    }
    public class RhinoApp { public static bool IsolateResult=true; public static bool RunScript(string s,bool e)=>IsolateResult; }
}
namespace RhinoAlmondBridge {
    public class ComponentRegistry { public static JObject Handle(RhinoDoc d,JObject r)=>throw new NotSupportedException(); }
    public class IntersectionAnalysis { public static JObject Query(RhinoDoc d,Guid[] i,int m,bool b,string c)=>throw new NotSupportedException(); }
    public class ObjectObservation { public static void ValidateDocument(RhinoDoc d,JObject r) { } }
    public class DocumentObservation {
        public static JObject Response=new JObject { ["status"]="success", ["warnings"]=new JArray() };
        public static JObject GetViewportImage(RhinoDoc d,string s,int p,string m,bool l,int depth,string scope,string target,int w,int h,string kind="")=>Response;
    }
}
class Program {
    static void Main(string[] args) {
        string scenario=args[0]; var doc=new RhinoDoc(); RhinoDoc.ActiveDoc=doc;
        doc.Objects.Items.Add(new RhinoObject { Geometry=new GeometryBase { Bounds=new BoundingBox {
            IsValid=true,Min=new Point3d(231500,199500,0),Max=new Point3d(232500,200500,0) } } });
        doc.Objects.Items.Add(new RhinoObject { Geometry=new GeometryBase { Bounds=new BoundingBox {
            IsValid=true,Min=new Point3d(229500,199500,0),Max=new Point3d(230500,200500,0) } } });
        var view=doc.Views.ActiveView.ActiveViewport;
        view.ZoomResult=scenario=="capture_failed" || scenario=="success" || scenario=="redraw_failed";
        view.FailCamera=scenario=="camera_unavailable";
        view.FailDisplay=scenario=="display_failed";
        doc.Views.FailRedraw=scenario=="redraw_failed";
        doc.Objects.Items[0].Geometry.FailBounds=scenario=="bounds_unavailable";
        if(scenario=="bounds_invalid") doc.Objects.Items[0].Geometry.Bounds=BoundingBox.Empty;
        doc.Objects.Items[1].FailSelect=scenario=="select_failed";
        RhinoApp.IsolateResult=scenario!="isolate_failed";
        if(scenario=="capture_failed") DocumentObservation.Response=new JObject {
            ["status"]="error",["error_code"]="image_too_large",["message"]="PNG budget exceeded",["warnings"]=new JArray() };
        var request=new JObject { ["type"]="get_current_viewcapture",["target_ids"]=new JArray(doc.Objects.Items.Select(o=>o.Id.ToString())),
            ["isolate"]=true,["width"]=800,["height"]=600,["scale_percent"]=100 };
        if(scenario=="display_failed") { request.Remove("target_ids");request["isolate"]=false;request["display_mode"]="Shaded"; }
        var result=ViewCaptureTools.Handle(doc,request);
        Console.WriteLine(result.ToString(Formatting.None));
    }
}''', ["features/components/native/ComponentOperations.cs", "features/context/native/ViewCaptureTools.cs"])


def test_zoom_failure_keeps_completed_steps_and_observed_planar_bounds(focus_host):
    result = focus_host("zoom_failed")
    assert result["error_code"] == "component_focus_error"
    assert result["mutation_applied"] is None and result["requires_reconciliation"] is True
    assert result["failed_stage"] == "zoom_selected"
    assert result["view_change"] == {
        "selection_changed": True, "isolated": True, "zoom_selected": None,
        "display_mode_changed": False, "restore_visibility_command": "Unisolate",
    }
    observation = result["focus_observation"]
    assert observation["target_count"] == 2
    assert observation["target_bounds"] == {"min": [229500, 199500, 0], "max": [232500, 200500, 0]}
    for key in ("before_zoom", "after_failure"):
        assert observation[key]["camera_location"] == [231000, 200000, 1000]
        assert observation[key]["camera_target"] == [231000, 200000, 0]
        assert observation[key]["frustum"] == [-100, 100, -75, 75, 1, 10000]


def test_bounds_observation_failure_does_not_prevent_the_zoom_attempt(focus_host):
    result = focus_host("bounds_unavailable")
    assert result["view_change"]["zoom_selected"] is None
    assert result["message"] == "Rhino could not zoom to the selected Components."
    assert result["focus_observation"]["target_bounds_error"] == "Bounds unavailable"


def test_camera_observation_failure_does_not_replace_the_focus_failure(focus_host):
    result = focus_host("camera_unavailable")
    assert result["failed_stage"] == "zoom_selected"
    assert result["focus_observation"]["before_zoom"]["observation_error"] == "Camera unavailable"
    assert result["focus_observation"]["after_failure"]["observation_error"] == "Camera unavailable"


def test_incomplete_bounds_are_not_reported_as_the_full_target_union(focus_host):
    result = focus_host("bounds_invalid")
    assert result["view_change"]["zoom_selected"] is None
    assert "target_bounds" not in result["focus_observation"]
    assert result["focus_observation"]["target_bounds_error"]


@pytest.mark.parametrize("scenario,stage,selection,isolated,zoom", [
    ("select_failed", "select", None, False, False),
    ("isolate_failed", "isolate", True, None, False),
    ("redraw_failed", "redraw", True, True, True),
])
def test_failure_identifies_completed_unconfirmed_and_unattempted_steps(focus_host, scenario, stage, selection, isolated, zoom):
    result = focus_host(scenario)
    assert result["failed_stage"] == stage
    assert result["view_change"]["selection_changed"] is selection
    assert result["view_change"]["isolated"] is isolated
    assert result["view_change"]["zoom_selected"] is zoom


def test_failed_display_mode_acknowledgement_is_unknown(focus_host):
    result = focus_host("display_failed")
    assert result["mutation_applied"] is None and result["requires_reconciliation"] is True
    assert result["view_change"]["display_mode_changed"] is None


def test_capture_error_preserves_completed_focus_and_original_error(focus_host):
    result = focus_host("capture_failed")
    assert result["error_code"] == "image_too_large"
    assert result["message"] == "PNG budget exceeded"
    assert result["mutation_applied"] is True
    assert result["view_change"]["zoom_selected"] is True
    assert result["view_change"]["restore_visibility_command"] == "Unisolate"


@pytest.mark.parametrize("scenario", ["lookup_failed", "write_failed", "refused", "created", "preserved", "updated", "unchanged"])
def test_native_setup_accounting_survives_the_public_tool_and_schema(setup_host, scenario):
    native = setup_host(scenario)
    ctx = modeling_context({"status": "success", "result": native})
    result = json.loads(register_modeling(FastMCP("native-setup-feedback"), ctx)["setup_modeling"](False))
    assert result["applied"] is native["applied"]
    assert result["changes"] == native["changes"]
    validate(result, public_output_schema("setup_modeling", wrapped=False))


@pytest.mark.parametrize("scenario", ["zoom_failed", "bounds_unavailable", "camera_unavailable", "capture_failed", "display_failed"])
def test_native_focus_feedback_survives_the_public_tool_and_schema(focus_host, scenario):
    native = focus_host(scenario)
    tools, _ = capture_tools(native)
    result = invoke(tools).structured_content
    for key in ("view_change", "focus_observation", "failed_stage", "mutation_applied", "requires_reconciliation"):
        if key in native:
            assert result[key] == native[key]
    validate(result, public_output_schema("get_current_viewcapture", wrapped=False))
