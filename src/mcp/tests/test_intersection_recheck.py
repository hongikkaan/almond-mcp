"""Exercise the native comparison recheck with a detached observation and no Rhino UI."""
import json
from pathlib import Path

import pytest

from test_stage2_native_feedback import build_host


@pytest.fixture(scope="module")
def recheck(tmp_path_factory):
    source = (Path(__file__).resolve().parents[1] / "features/components/native/IntersectionReview.cs").read_text(encoding="utf-8")
    # Run the production recheck, its exception handler and the final change receipt.
    # Document selection, geometry observation and all viewport operations are fixture boundaries.
    capture = (source[source.index("        public static JObject Capture("):source.index("                ObjectObservation.ValidateDocument")]
               + "var a = request[\"a\"]; var b = request[\"b\"]; var first = a; var second = b;\n"
               + source[source.index("                using (var observed ="):source.index("                hidden = Hidden(doc);")]
               + 'throw new InvalidOperationException("Fixture viewport failed.");\n}\n'
               + source[source.index("            catch (Exception ex)"):source.index("            finally")]
               + source[source.index('            answer["mutation_applied"]'):source.index("        static HashSet<Guid> Hidden(")])
    harness = """
using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
class RhinoDoc {
    public double ModelAbsoluteTolerance => 0.004;
    public string ModelUnitSystem => "Meters";
    public JObject Report;
}
class IntersectionAnalysis {
    public class Scope {}
    public class Observation : IDisposable {
        public JObject Report;
        public void Dispose() {}
    }
    public static Observation Observe(RhinoDoc doc, JToken a, JToken b) => new Observation { Report = doc.Report };
}
class Program {
    static void Main(string[] args) {
        var report = JObject.Parse(args[0]);
        Console.WriteLine(Capture(new RhinoDoc { Report = report }, report).ToString(Formatting.None));
    }
    // CAPTURE
}"""
    return build_host(tmp_path_factory.mktemp("recheck"), harness.replace("// CAPTURE", capture), [])


@pytest.mark.parametrize("status", ["unknown", "zero_volume", "positive_volume"])
def test_only_unknown_recheck_reports_incomplete_pair_and_current_tolerance(recheck, status):
    pair = {"a": {"object_id": "00000000-0000-0000-0000-000000000001"},
            "b": {"object_id": "00000000-0000-0000-0000-000000000002"},
            "overlap": {"status": status}}
    if status == "unknown":
        pair["overlap"]["reason"] = "Empty BooleanIntersection."
    error = recheck(json.dumps(pair))
    assert error["status"] == "error" and error["error_code"] == "intersection_review_failed"
    assert error["mutation_applied"] is False and error["view_change"]["geometry_changed"] is False
    assert "image" not in error and error["requires_reconciliation"] is False
    if status == "unknown":
        assert error["assessment"] == "incomplete" and error["failed_pairs"] == [pair]
        assert error["unsupported_objects"] == []
        assert error["tolerance_model_units"] == 0.004 and error["document_units"] == "Meters"
    else:
        assert "assessment" not in error
        assert error["message"] == ("The current pair has no confirmed positive overlap; query again."
                                    if status == "zero_volume" else "Fixture viewport failed.")
