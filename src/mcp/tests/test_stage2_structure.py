"""Structure tool regressions with a real solver and disposable history.

The native transport is controlled at the Python/Rhino boundary. These tests do
not load Rhino or validate C# rendering; the Windows wrapper owns those checks.
"""
import copy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastmcp import FastMCP
from jsonschema import validate

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.structure.tools import register
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.retrieval_store import AlmondStore


MODEL = {
    "status": "ok", "shells": 0, "tolerance_m": .001,
    "max_member_span_m": 2., "max_span_m": 2., "anchor_points": [[0, 0, 0]],
    "members": [{"source_guids": ["beam"], "points": [[0, 0, 0], [2, 0, 0]],
                 "section": {"shape": "solid_rectangle", "width": .3, "height": .5}}],
}
OPTIONS = dict(material="Concrete", load_kn=1, self_weight=False, stability="off")
LEGACY_DDL = """id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT NOT NULL,
    structure_type TEXT NOT NULL, material TEXT NOT NULL, load_kn REAL NOT NULL,
    member_count INTEGER NOT NULL, analysis_method TEXT NOT NULL, confidence TEXT NOT NULL,
    passed INTEGER NOT NULL, span_m REAL NOT NULL, max_deflection_mm REAL NOT NULL,
    deflection_limit_mm REAL NOT NULL, utilization_ratio REAL NOT NULL,
    max_stress_mpa REAL NOT NULL, yield_stress_mpa REAL NOT NULL, reactions_kn REAL NOT NULL,
    verdict TEXT NOT NULL, warnings_json TEXT NOT NULL, guids_json TEXT NOT NULL"""


class StructureTools:
    def __init__(self, database, overlay=None, overlay_ids=True):
        self.requests = []
        self.draw_status = "indicative"
        self.draw_displacement = .028
        self.draw_warnings = None
        self.overlay = overlay if overlay is not None else {}
        self.overlay_ids = overlay_ids
        self.api_analyses = 0
        self.model = copy.deepcopy(MODEL)
        self.namespace = {
            "_VIEW_ENGINE": None,
            "_send_and_receive": self.send,
            "retrieval_store": AlmondStore(database),
            "construction_library": SimpleNamespace(assess_span=lambda *args: {"warnings": []}),
        }
        self.namespace.update(register(FastMCP("stage2-structure"), FeatureContext(self.namespace)))

    def send(self, payload, timeout=0):
        request = json.loads(payload)
        self.requests.append(request)
        if request["type"] == "structure_model":
            return json.dumps(self.model)
        if request["type"] == "structure_draw":
            if "result" in request:
                self.overlay["response"] = {
                    "status": self.draw_status, "analysis_method": "native", "nodes": 0,
                    "max_displacement_mm": self.draw_displacement, "deflection_limit_mm": 8,
                    "warnings": self.draw_warnings if self.draw_warnings is not None else request["result"]["warnings"],
                }
                if self.overlay_ids:
                    self.overlay["response"]["overlay_id"] = uuid4().hex
            return json.dumps(self.overlay.get("response", {
                "status": "error", "message": "Nothing to display yet: send a result first.", "warnings": [],
            }))
        if request["type"] == "structure_view" and request.get("clear"):
            self.overlay.clear()
            return json.dumps({"status": "cleared"})
        if request["type"] == "structure_view":
            # Handle re-solves an empty conduit even when reanalyze=False;
            # HandleDraw above must instead report the missing overlay.
            if request.get("reanalyze", True) or "response" not in self.overlay:
                self.api_analyses += 1
                self.overlay["response"] = {
                    "status": "fail", "analysis_method": "api", "nodes": 2,
                    "max_displacement_mm": 50, "warnings": ["current api failure"],
                    "overlay_id": uuid4().hex,
                }
            return json.dumps(self.overlay["response"])
        raise AssertionError("Unexpected Karamba fallback: " + request["type"])

    def call(self, name, **kwargs):
        value = json.loads(self.namespace[name](**kwargs))
        validate(value, public_output_schema(name, wrapped=False))
        return value


@pytest.mark.parametrize("engine", ["native", "auto"])
def test_completed_indicative_analysis_exports_a_native_report(tmp_path, engine):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    value = tools.call("validate_structure", guids=["beam"], engine=engine, **OPTIONS)
    assert value["status"] == "indicative" and value["passed"] is None
    assert value["results"]["reactions_kn"] == pytest.approx(1)
    exported = tools.call("export_structural_report", path=str(tmp_path / "report.md"))
    assert exported["status"] == "success" and exported["runs"] == 1
    report = Path(exported["path"]).read_text(encoding="utf-8")
    assert "native (INDICATIVE)" in report and "native (FAIL)" not in report
    assert "**native**" in report and "Only **api**" not in report


@pytest.mark.parametrize("engine", ["native", "auto"])
def test_indicative_overlay_redraw_and_clear_do_not_fall_back(tmp_path, engine):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    shown = tools.call("visualize_structure", guids=["beam"], engine=engine, **OPTIONS)
    assert shown["status"] == "indicative" and shown["passed"] is None and shown["nodes"] == 2
    assert [r["type"] for r in tools.requests] == ["structure_model", "structure_draw"]
    tools.requests.clear()
    redrawn = tools.call("visualize_structure", guids=["beam"], engine=engine,
                         reanalyze=False, scale=10, physics=False, **OPTIONS)
    assert redrawn["status"] == "indicative" and redrawn["passed"] is None and redrawn["nodes"] == 2
    assert redrawn["design_code"] == shown["design_code"]
    assert redrawn["combinations"] == shown["combinations"] and redrawn["warnings"] == shown["warnings"]
    assert [r["type"] for r in tools.requests] == ["structure_draw"]
    assert "result" not in tools.requests[0]  # Display-only request, no solver result replaced.
    cleared = tools.call("visualize_structure", clear=True)
    assert cleared["status"] == "cleared"
    tools.requests.clear()
    # No cached result remains after clear: a subsequent display needs a model again.
    shown_again = tools.call("visualize_structure", guids=["beam"], engine=engine,
                             reanalyze=False, **OPTIONS)
    assert shown_again["nodes"] == 2
    assert [r["type"] for r in tools.requests] == ["structure_model", "structure_draw"]


def test_concrete_deflection_failure_remains_failure_in_history_and_redraw(tmp_path):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    options = {**OPTIONS, "load_kn": 1000, "engine": "native"}
    failed = tools.call("validate_structure", guids=["beam"], **options)
    assert failed["status"] == "fail" and failed["passed"] is False
    assert failed["results"]["max_deflection_mm"] > failed["results"]["deflection_limit_mm"]
    exported = tools.call("export_structural_report", path=str(tmp_path / "failure.md"))
    report = Path(exported["path"]).read_text(encoding="utf-8")
    assert "native (FAIL)" in report and "native (PASS)" not in report
    tools.draw_status = "fail"
    for reanalyze in (True, False):
        shown = tools.call("visualize_structure", guids=["beam"], reanalyze=reanalyze, **options)
        assert shown["status"] == "fail" and shown["passed"] is False and shown["nodes"] == 2


def test_new_steel_analysis_replaces_indicative_cache_and_records_pass(tmp_path):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    tools.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)
    options = {**OPTIONS, "material": "Steel", "engine": "native"}
    value = tools.call("validate_structure", guids=["beam"], **options)
    assert value["status"] == "pass" and value["passed"] is True
    tools.draw_status = "pass"
    for reanalyze in (True, False):
        shown = tools.call("visualize_structure", guids=["beam"], reanalyze=reanalyze, **options)
        assert shown["status"] == "pass" and shown["passed"] is True and shown["nodes"] == 2
    exported = tools.call("export_structural_report", path=str(tmp_path / "steel.md"))
    assert "native (PASS)" in Path(exported["path"]).read_text(encoding="utf-8")


@pytest.mark.parametrize("overlay_ids", [True, False])
def test_another_worker_overlay_failure_keeps_current_verdict_and_warnings(tmp_path, overlay_ids):
    overlay = {}
    first = StructureTools(tmp_path / "first.sqlite3", overlay, overlay_ids)
    second = StructureTools(tmp_path / "second.sqlite3", overlay, overlay_ids)
    first.model["members"][0]["points"] = [[0, 0, 0], [0, 0, 2]]
    first.draw_status = "pass"
    stable = first.call("visualize_structure", guids=["beam"], engine="native", view="buckling",
                        **{**OPTIONS, "material": "Steel"})
    assert stable["status"] == "pass" and stable["buckling"]["alpha_cr"] > 1
    second.draw_status = "fail"
    second.draw_displacement = 50
    second.draw_warnings = ["current overlay failed"]
    second.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)

    redrawn = first.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False,
                         scale=10, **OPTIONS)
    assert redrawn["status"] == "fail" and redrawn["passed"] is False
    assert redrawn["max_displacement_mm"] == 50 and redrawn["deflection_limit_mm"] == 8
    assert redrawn["warnings"] == ["current overlay failed"]
    assert "buckling" not in redrawn and "design_code" not in redrawn
    assert "overlay_id" not in stable and "overlay_id" not in redrawn


def test_another_worker_identical_geometry_and_numbers_do_not_reuse_material_verdict(tmp_path):
    overlay = {}
    first = StructureTools(tmp_path / "first.sqlite3", overlay)
    second = StructureTools(tmp_path / "second.sqlite3", overlay)
    first.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)
    # The boundary returns identical geometry/numbers; material capacity and
    # warnings belong to the second analysis, regardless of those similarities.
    second.draw_status = "pass"
    second.draw_warnings = ["current steel check"]
    second.call("visualize_structure", guids=["beam"], engine="native",
                **{**OPTIONS, "material": "Steel"})
    for _ in range(2):
        redrawn = first.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False,
                             scale=10, **OPTIONS)
        assert redrawn["status"] == "pass" and redrawn["passed"] is True
        assert redrawn["max_displacement_mm"] == .028
        assert redrawn["warnings"] == ["current steel check"]
        assert "design_code" not in redrawn and "combinations" not in redrawn
        assert "overlay_id" not in redrawn


def test_current_failure_and_new_warning_survive_same_overlay_buckling_report(tmp_path):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    tools.model["members"][0]["points"] = [[0, 0, 0], [0, 0, 2]]
    tools.draw_status = "pass"
    shown = tools.call("visualize_structure", guids=["beam"], engine="native", view="buckling",
                       **{**OPTIONS, "material": "Steel"})
    tools.overlay["response"]["status"] = "fail"
    tools.overlay["response"]["warnings"] = ["current native failure"]
    redrawn = tools.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False,
                         scale=10, **OPTIONS)
    assert redrawn["status"] == "fail" and redrawn["passed"] is False
    assert redrawn["warnings"][0] == "current native failure"
    assert redrawn["buckling"] == shown["buckling"]


def test_missing_overlay_identity_discards_enrichment_and_keeps_indicative(tmp_path):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    shown = tools.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)
    assert "design_code" in shown
    identity = tools.overlay["response"].pop("overlay_id")
    tools.overlay["response"]["warnings"] = ["current indicative result"]
    for restore_identity in (False, True):
        if restore_identity:
            tools.overlay["response"]["overlay_id"] = identity
        redrawn = tools.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False, **OPTIONS)
        assert redrawn["status"] == "indicative" and redrawn["passed"] is None
        assert redrawn["warnings"] == ["current indicative result"]
        assert "design_code" not in redrawn and "combinations" not in redrawn


def test_native_input_error_does_not_create_a_completed_history_run(tmp_path):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    value = tools.call("validate_structure", guids=["beam"], engine="native",
                       **{**OPTIONS, "material": "Not a structural material"})
    assert value["status"] == "error"
    target = tmp_path / "error.md"
    exported = tools.call("export_structural_report", path=str(target))
    assert exported["status"] == "error" and not target.exists()


@pytest.mark.parametrize("material,load_kn,status,confidence,marker", [
    ("Concrete", 1, "indicative", "low", "LOW CONFIDENCE"),
    ("Concrete", 1000, "fail", "low", "LOW CONFIDENCE"),
    ("Steel", 1, "pass", "high", "HIGH CONFIDENCE"),
    ("Steel", 10000, "fail", "high", "HIGH CONFIDENCE"),
])
def test_validation_verdict_and_export_match_numeric_result_confidence(
    tmp_path, material, load_kn, status, confidence, marker,
):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    value = tools.call("validate_structure", guids=["beam"], engine="native",
                       **{**OPTIONS, "material": material, "load_kn": load_kn})
    assert value["status"] == status and value["confidence"] == confidence
    assert marker in value["verdict"]
    opposite = "HIGH CONFIDENCE" if confidence == "low" else "LOW CONFIDENCE"
    assert opposite not in value["verdict"]
    exported = tools.call("export_structural_report", path=str(tmp_path / "confidence.md"))
    report = Path(exported["path"]).read_text(encoding="utf-8")
    assert marker + "]" in report and opposite + "]" not in report


@pytest.mark.parametrize("material,load_kn,expected_status,expected_passed", [
    ("Concrete", 1, "indicative", None),
    ("Concrete", 20000, "fail", False),
    ("Steel", 1, "pass", True),
])
def test_buckling_verdict_keeps_material_capacity_limitations_on_redraw(
    tmp_path, material, load_kn, expected_status, expected_passed,
):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    tools.model["members"][0]["points"] = [[0, 0, 0], [0, 0, 2]]
    tools.draw_status = "indicative" if material == "Concrete" else "pass"
    options = {**OPTIONS, "material": material, "load_kn": load_kn, "engine": "native", "view": "buckling"}
    for reanalyze in (True, False):
        shown = tools.call("visualize_structure", guids=["beam"], reanalyze=reanalyze, **options)
        assert shown["status"] == expected_status and shown["passed"] is expected_passed
        assert (shown["buckling"]["alpha_cr"] > 1) == (load_kn == 1)
        assert "max_displacement_mm" not in shown  # A mode's amplitude is not a deflection.


@pytest.fixture(scope="module")
def overlay_host(tmp_path_factory):
    # Link the complete production file; only Rhino and the external solver are
    # boundary doubles. This does not exercise Rhino display or its Windows SDK.
    from test_stage2_native_feedback import build_host

    return build_host(tmp_path_factory.mktemp("structure_overlay"), r'''
using System;
using System.Collections.Generic;
using System.Drawing;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using RhinoAlmondBridge;

namespace Rhino.Geometry {
    public struct Point3d {
        public double X,Y,Z;
        public Point3d(double x,double y,double z) { X=x;Y=y;Z=z; }
        public static Point3d operator +(Point3d p, Vector3d v) => new Point3d(p.X+v.X,p.Y+v.Y,p.Z+v.Z);
        public static Point3d operator -(Point3d p, Vector3d v) => new Point3d(p.X-v.X,p.Y-v.Y,p.Z-v.Z);
    }
    public struct Point2d { public Point2d(double x,double y) {} }
    public struct Vector3d {
        public double X,Y,Z;
        public Vector3d(double x,double y,double z) { X=x;Y=y;Z=z; }
        public static Vector3d XAxis => new Vector3d(1,0,0);
        public bool Unitize() => true;
        public static Vector3d operator *(Vector3d v,double s) => new Vector3d(v.X*s,v.Y*s,v.Z*s);
    }
    public struct BoundingBox { public BoundingBox(Point3d[] p) {} }
    public struct Line { public Line(Point3d a,Point3d b) {} }
}
namespace Rhino {
    public enum UnitSystem { Millimeters, Meters }
    public static class RhinoMath { public static double UnitScale(UnitSystem a,UnitSystem b) => 1; }
    public class Views { public void Redraw() {} }
    public class RhinoDoc {
        public static RhinoDoc ActiveDoc = new RhinoDoc();
        public Views Views = new Views();
        public UnitSystem ModelUnitSystem = UnitSystem.Meters;
    }
}
namespace Rhino.Display {
    using Rhino.Geometry;
    public enum PointStyle { RoundControlPoint }
    public class DisplayConduit {
        public bool Enabled;
        protected virtual void CalculateBoundingBox(CalculateBoundingBoxEventArgs e) {}
        protected virtual void DrawForeground(DrawEventArgs e) {}
    }
    public class CalculateBoundingBoxEventArgs { public void IncludeBoundingBox(BoundingBox b) {} }
    public class Viewport { public Rectangle Bounds = new Rectangle(); public Vector3d CameraX; }
    public class DrawEventArgs { public Viewport Viewport = new Viewport(); public Pipeline Display = new Pipeline(); }
    public class Pipeline {
        public void DrawLine(Point3d a,Point3d b,Color c,int width) {}
        public void DrawPoint(Point3d p,PointStyle s,int size,Color c) {}
        public void DrawPolygon(Point3d[] p,Color c,bool fill) {}
        public void DrawPolyline(Point3d[] p,Color c,int width) {}
        public void DrawArrow(Line l,Color c,int style,double size) {}
        public void Draw2dRectangle(Rectangle r,Color c,int width,Color fill) {}
        public void Draw2dText(string s,Color c,Point2d p,bool middle,int size,string face) {}
        public void Draw2dLine(Point a,Point b,Color c,int width) {}
        public Rectangle Measure2dText(string s,Point2d p,bool middle,int angle,int size,string face) => new Rectangle();
    }
}
namespace RhinoAlmondBridge {
    public class SectionSpec { public string Shape,Source; public double Diameter,WallThickness; }
    public class Beam { public SectionSpec Section; }
    public class ConditionedModel {
        public List<Beam> Beams = new List<Beam> { new Beam() };
        public double MaxMemberSpan = 2, UnitScaleToMeters = 1;
    }
    public class ModelConditioner { public ConditionedModel Condition(Rhino.RhinoDoc doc,List<string> guids) => new ConditionedModel(); }
    public class KarambaModelSpec {
        public ConditionedModel Conditioned; public string MaterialName;
        public double ImposedLoadKN; public bool IncludeSelfWeight,FixedRotations,ReturnGeometry;
    }
    public class ElementDeflection {
        public List<string> SourceGuids; public double[] StartM,EndM;
        public List<double[]> SampleDispM; public double Utilization; public bool[] Hinges;
    }
    public class KarambaResults {
        public bool Available,GeometryAvailable,DisplacementAvailable;
        public string FailureReason; public double MaxDisplacementMM;
        public List<ElementDeflection> Elements = new List<ElementDeflection>();
        public List<double[]> SupportPointsM = new List<double[]>(), LoadedPointsM = new List<double[]>(), NodeDispM = new List<double[]>();
        public List<string> Warnings = new List<string>();
    }
    public static class KarambaAdapter {
        public static int Analyses;
        public static KarambaResults BuildAndAnalyze(KarambaModelSpec spec) {
            Analyses++;
            return new KarambaResults {
                Available=true, GeometryAvailable=true, MaxDisplacementMM=50, Warnings=new List<string> { "current api failure" }
            };
        }
    }
}
class Program {
    static JObject Draw(double displacement, string label=null, double? alpha=null) {
        var result = JObject.Parse(@"{'elements':[{'source_guids':['beam'],'start_m':[0,0,0],
          'end_m':[0,0,2],'samples_m':[[0,0,0],[0,0,0.05]],'utilization':0.1}],
          'warnings':['current native result']}");
        result["max_displacement_mm"] = displacement;
        var request = new JObject { ["result"]=result, ["span_m"]=2.0, ["engine"]="native" };
        if (label != null) request["verdict_label"]=label;
        if (alpha.HasValue) request["buckling_alpha"]=alpha.Value;
        return JObject.Parse(StructureView.HandleDraw(request));
    }
    static JObject Redraw() => JObject.Parse(StructureView.HandleDraw(new JObject { ["scale"]=10 }));
    static void Main(string[] args) {
        var output = new JObject();
        if (args[0] == "identity") {
            output["first"]=Draw(.028,"INDICATIVE");
            output["redraw"]=Redraw();
            output["replacement"]=Draw(.028,"INDICATIVE");
            output["replacement_redraw"]=Redraw();
            output["api"]=JObject.Parse(StructureView.Handle(new JObject()));
            output["api_redraw"]=Redraw();
            StructureView.Handle(new JObject { ["clear"]=true });
            output["analyses_before_empty_draw"]=KarambaAdapter.Analyses;
            output["cleared"]=Redraw();
            output["analyses_after_empty_draw"]=KarambaAdapter.Analyses;
            output["empty_handle"]=JObject.Parse(StructureView.Handle(new JObject { ["reanalyze"]=false }));
            output["analyses_after_empty_handle"]=KarambaAdapter.Analyses;
            output["after_clear"]=Draw(.028,"INDICATIVE");
        } else {
            output["stable_steel"]=Draw(50,null,2);
            output["stable_steel_redraw"]=Redraw();
            output["indicative"]=Draw(50,"INDICATIVE",2);
            output["indicative_redraw"]=Redraw();
            output["unstable"]=Draw(.028,"INDICATIVE",.5);
            output["deflection_failure"]=Draw(50,"INDICATIVE");
        }
        Console.WriteLine(output.ToString(Formatting.None));
    }
}''', ["../rhp/Structural_Analysis/StructureView.cs"])


def test_native_overlay_identity_belongs_to_the_current_result(overlay_host):
    results = overlay_host("identity")
    first = results["first"]["overlay_id"]
    second = results["replacement"]["overlay_id"]
    api = results["api"]["overlay_id"]
    assert first and second and api
    assert len({first, second, api, results["after_clear"]["overlay_id"]}) == 4
    assert results["redraw"]["overlay_id"] == first
    assert results["replacement_redraw"]["overlay_id"] == second
    assert results["first"]["nodes"] == results["replacement_redraw"]["nodes"] == 2
    assert results["api_redraw"]["overlay_id"] == api
    assert results["cleared"]["status"] == "error" and "overlay_id" not in results["cleared"]
    assert results["analyses_before_empty_draw"] == results["analyses_after_empty_draw"] == 1
    assert results["analyses_after_empty_handle"] == 2


def test_native_buckling_verdict_uses_current_mode_and_keeps_indicative(overlay_host):
    results = overlay_host("buckling")
    for key in ("stable_steel", "stable_steel_redraw"):
        assert results[key]["status"] == "pass"
        assert "max_displacement_mm" not in results[key]
    for key in ("indicative", "indicative_redraw"):
        assert results[key]["status"] == "indicative"
        assert "max_displacement_mm" not in results[key]
    assert results["unstable"]["status"] == "fail"
    assert results["deflection_failure"]["status"] == "fail"
    assert results["deflection_failure"]["max_displacement_mm"] == 50


def test_native_api_overlay_replacement_keeps_current_report_on_repeated_redraw(tmp_path, overlay_host):
    tools = StructureTools(tmp_path / "scene.sqlite3")
    tools.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)
    # A panel/API analysis replaces the shared conduit outside this worker.
    tools.overlay["response"] = overlay_host("identity")["api"]
    for _ in range(2):
        redrawn = tools.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False,
                             scale=10, **OPTIONS)
        assert redrawn["status"] == "fail" and redrawn["analysis_method"] == "api"
        assert redrawn["max_displacement_mm"] == 50
        assert redrawn["warnings"] == ["current api failure"]
        assert "design_code" not in redrawn and "overlay_id" not in redrawn


@pytest.mark.parametrize("initial_engine", ["native", "karamba"])
def test_api_takeover_then_external_clear_cannot_trigger_another_analysis(tmp_path, initial_engine):
    overlay = {}
    first = StructureTools(tmp_path / "first.sqlite3", overlay)
    second = StructureTools(tmp_path / "second.sqlite3", overlay)
    first.call("visualize_structure", guids=["beam"], engine=initial_engine, **OPTIONS)
    second.call("visualize_structure", guids=["beam"], engine="karamba", **OPTIONS)
    first.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False, **OPTIONS)
    second.call("visualize_structure", clear=True)
    first.requests.clear()
    for _ in range(2):
        result = first.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False, **OPTIONS)
        assert result["status"] == "error" and "Nothing to display" in result["message"]
    assert first.api_analyses == (1 if initial_engine == "karamba" else 0)
    assert [r["type"] for r in first.requests] == ["structure_draw", "structure_draw"]


def test_api_takeover_then_other_workers_indicative_overlay_keeps_unknown_capacity(tmp_path):
    overlay = {}
    first = StructureTools(tmp_path / "first.sqlite3", overlay)
    second = StructureTools(tmp_path / "second.sqlite3", overlay)
    first.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)
    second.call("visualize_structure", guids=["beam"], engine="karamba", **OPTIONS)
    first.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False, **OPTIONS)
    second.call("visualize_structure", guids=["beam"], engine="native", **OPTIONS)
    first.requests.clear()
    for _ in range(2):
        result = first.call("visualize_structure", guids=["beam"], engine="native", reanalyze=False, **OPTIONS)
        assert result["status"] == "indicative" and result["passed"] is None
        assert "design_code" not in result and "overlay_id" not in result
    assert [r["type"] for r in first.requests] == ["structure_draw", "structure_draw"]


def seed_legacy_history(database):
    with sqlite3.connect(database) as db:
        db.execute(f"CREATE TABLE validation_runs ({LEGACY_DDL})")
        for number, passed in ((13, 1), (21, 0), (89, 1)):
            db.execute("INSERT INTO validation_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (number, "2026-11-10", "beam", "Steel", 10, 1, "native", "high", passed,
                        2, .5, 8, .2, 20, 235, 10, "old verdict", '["preserved"]', '["original-guid"]'))
        db.execute("DELETE FROM validation_runs WHERE id = 89")
        return db.execute("SELECT * FROM validation_runs ORDER BY id").fetchall()


def test_legacy_history_keeps_rows_and_does_not_reuse_retired_run_ids(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    original = seed_legacy_history(database)
    tools = StructureTools(database)
    exported = tools.call("export_structural_report", path=str(tmp_path / "legacy.md"))
    report = Path(exported["path"]).read_text(encoding="utf-8")
    assert "Run 13 — beam, native (PASS)" in report and "Run 21 — beam, native (FAIL)" in report
    # Exact raw-data preservation is the migration contract, including JSON bytes.
    with sqlite3.connect(database) as db:
        columns = [row[1] for row in db.execute("PRAGMA table_info(validation_runs)") if row[1] != "status"]
        assert db.execute("SELECT " + ",".join(columns) + " FROM validation_runs ORDER BY id").fetchall() == original
    value = tools.call("validate_structure", guids=["beam"], engine="native", **OPTIONS)
    assert value["status"] == "indicative" and value["passed"] is None
    reopened = StructureTools(database)
    rows = reopened.namespace["retrieval_store"].list_validation_runs()
    assert rows[0]["id"] > 89
    assert [(r["status"], r["passed"]) for r in rows] == [("indicative", None), ("fail", False), ("pass", True)]


def test_empty_legacy_history_keeps_retired_run_ids(tmp_path):
    database = tmp_path / "empty.sqlite3"
    seed_legacy_history(database)
    with sqlite3.connect(database) as db:
        db.execute("DELETE FROM validation_runs")
    tools = StructureTools(database)
    tools.call("validate_structure", guids=["beam"], engine="native", **OPTIONS)
    assert AlmondStore(database).list_validation_runs()[0]["id"] > 89
