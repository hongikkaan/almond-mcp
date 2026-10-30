using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;

// Independent geometric fixtures. Runs only inside its own headless document.
public static class IntersectionTests
{
    private static readonly JArray Results = new JArray();

    public static string RunAll()
    {
        Results.Clear();
        using (var doc = RhinoDoc.CreateHeadless(null))
        {
            if (doc == null) throw new InvalidOperationException("CreateHeadless returned null.");
            doc.ModelUnitSystem = UnitSystem.Millimeters;
            doc.ModelAbsoluteTolerance = 0.01;
            RunIntersectionTests(doc);
        }
        int failed = Results.OfType<JObject>().Count(x => !(bool)x["passed"]);
        var report = new JObject {
            ["suite"] = "rhino-almond native geometry fixtures",
            ["tests"] = Results.Count,
            ["passed"] = Results.Count - failed,
            ["failed"] = failed,
            ["results"] = Results
        };
        string json = report.ToString(Formatting.Indented);
        if (failed != 0) throw new InvalidOperationException(json);
        return json;
    }

    private static void Test(string name, Action body)
    {
        try { body(); Results.Add(new JObject { ["name"] = name, ["passed"] = true }); }
        catch (Exception e) { Results.Add(new JObject { ["name"] = name, ["passed"] = false, ["error"] = e.ToString() }); }
    }

    private static void Check(bool ok, string message)
    {
        if (!ok) throw new InvalidOperationException(message);
    }

    private static void Near(double actual, double expected, double tolerance = 0.0001)
    {
        Check(!Double.IsNaN(actual) && !Double.IsInfinity(actual) && Math.Abs(actual - expected) <= tolerance,
            "Expected " + expected + ", got " + actual + ".");
    }

    private static Guid Box(RhinoDoc doc, double x, double y, double z, double dx = 10, double dy = 10, double dz = 10)
    {
        using (var b = Brep.CreateFromBox(new BoundingBox(new Point3d(x, y, z), new Point3d(x + dx, y + dy, z + dz))))
            return doc.Objects.AddBrep(b);
    }

    private static Guid MeshBox(RhinoDoc doc, double x, double y, double z, double dx = 10, double dy = 10, double dz = 10)
    {
        var box = new Rhino.Geometry.Box(Plane.WorldXY, new Interval(x, x + dx), new Interval(y, y + dy), new Interval(z, z + dz));
        using (var m = Mesh.CreateFromBox(box, 1, 1, 1)) return doc.Objects.AddMesh(m);
    }

    private static JObject PairRequest(Guid a, Guid b)
    {
        return new JObject { ["pairs"] = new JArray { new JArray(a.ToString(), b.ToString()) }, ["tolerance"] = 0.01 };
    }

    private static JObject PairRow(JObject result)
    {
        var rows = result["pairs"] as JArray;
        Check(rows != null && rows.Count == 1, "Expected exactly one pair record: " + result.ToString(Formatting.None));
        return (JObject)rows[0];
    }

    private static double OverlapVolume(JObject result)
    {
        var overlap = (JObject)PairRow(result)["overlap"];
        var volume = overlap["volume_model_units3"];
        Check(volume != null && volume.Type != JTokenType.Null,
            "Expected measured overlap volume: " + overlap.ToString(Formatting.None));
        return (double)volume;
    }

    private static Dictionary<Guid, uint> GeometryCrcs(RhinoDoc doc, params Guid[] ids)
    {
        return ids.ToDictionary(id => id, id => doc.Objects.FindId(id).Geometry.DataCRC(0));
    }

    private static void AssertUnchanged(RhinoDoc doc, Dictionary<Guid, uint> before)
    {
        foreach (var pair in before)
        {
            var obj = doc.Objects.FindId(pair.Key);
            Check(obj != null && !obj.IsDeleted, "Input object removed: " + pair.Key);
            Check(obj.Geometry.DataCRC(0) == pair.Value, "Input geometry changed: " + pair.Key);
        }
    }

    private static void ArgumentRejected(Action action)
    {
        try { action(); }
        catch (ArgumentException) { return; }
        throw new InvalidOperationException("Expected invalid input to throw ArgumentException.");
    }

    private static void UnsupportedPair(JObject result)
    {
        var row = PairRow(result);
        Check((string)row["status"] == "unsupported_input", "Unsupported geometry must be identified.");
        Check((string)row["overlap"]["status"] == "unknown", "Unsupported overlap must be unknown.");
        Check(row["overlap"]["volume_model_units3"].Type == JTokenType.Null, "Unknown overlap must have null volume.");
    }

    private static void RunIntersectionTests(RhinoDoc doc)
    {
        Guid a = Box(doc, 0, 0, 0), overlap = Box(doc, 5, 0, 0), contact = Box(doc, 10, 0, 0);
        Guid gap = Box(doc, 12, 0, 0), contained = Box(doc, 2, 2, 2, 5, 5, 5), far = Box(doc, 30, 20, 10);
        Test("intersection: overlapping 10 mm cubes have 500 mm3 intersection", () => Near(OverlapVolume(SolidIntersections.AuditPairs(doc, PairRequest(a, overlap))), 500));
        Test("intersection: 5 mm cube fully contained has 125 mm3 intersection", () => Near(OverlapVolume(SolidIntersections.AuditPairs(doc, PairRequest(a, contained))), 125));
        Test("intersection: face-contact does not report positive overlap", () =>
        {
            var row = PairRow(SolidIntersections.AuditPairs(doc, PairRequest(a, contact)));
            var value = row["overlap"]["volume_model_units3"];
            if (value != null && value.Type != JTokenType.Null) Near((double)value, 0);
            else Check((string)row["overlap"]["status"] == "unknown", "Unavailable contact volume must stay unknown.");
        });
        Test("intersection: 2 mm separation has zero overlap", () => Near(OverlapVolume(SolidIntersections.AuditPairs(doc, PairRequest(a, gap))), 0));
        Test("intersection: 2 mm separation labels bbox distance as a lower bound", () =>
        {
            var row = PairRow(SolidIntersections.AuditPairs(doc, PairRequest(a, gap)));
            Near((double)row["bbox_distance_lower_bound"], 2);
            Check((string)row["surface_gap_status"] == "not_measured", "BBox distance must not be presented as measured surface gap.");
            Check(row["surface_gap"].Type == JTokenType.Null, "Unmeasured gap must be null.");
        });
        Test("intersection: fully separated boxes have zero overlap", () => Near(OverlapVolume(SolidIntersections.AuditPairs(doc, PairRequest(a, far))), 0));
        Test("intersection: intersection observations preserve input geometry", () =>
        {
            var before = GeometryCrcs(doc, a, overlap);
            var request = PairRequest(a, overlap);
            Near(OverlapVolume(SolidIntersections.AuditPairs(doc, request)), 500);
            AssertUnchanged(doc, before);
        });
        Test("intersection: inward solid normalized on duplicate only", () =>
        {
            Guid inward;
            using (var reversed = Brep.CreateFromBox(new BoundingBox(new Point3d(0, 0, 0), new Point3d(10, 10, 10))))
            { reversed.Flip(); inward = doc.Objects.AddBrep(reversed); }
            var before = GeometryCrcs(doc, inward, overlap);
            Near(OverlapVolume(SolidIntersections.AuditPairs(doc, PairRequest(inward, overlap))), 500);
            AssertUnchanged(doc, before);
        });
        Test("intersection: missing object is unsupported with unknown volume", () => UnsupportedPair(SolidIntersections.AuditPairs(doc, PairRequest(a, Guid.NewGuid()))));
        Test("intersection: mesh input is explicitly unsupported", () =>
        {
            Guid mesh = MeshBox(doc, 0, 0, 0);
            UnsupportedPair(SolidIntersections.AuditPairs(doc, PairRequest(a, mesh)));
        });
        Test("intersection: open Brep is explicitly unsupported", () =>
        {
            using (var surface = new PlaneSurface(Plane.WorldXY, new Interval(0, 10), new Interval(0, 10)))
            using (var brep = surface.ToBrep())
                UnsupportedPair(SolidIntersections.AuditPairs(doc, PairRequest(a, doc.Objects.AddBrep(brep))));
        });
        Test("intersection: empty pairs rejected", () => ArgumentRejected(() => SolidIntersections.AuditPairs(doc, new JObject { ["pairs"] = new JArray() })));
        Test("intersection: same-object pair rejected", () => ArgumentRejected(() => SolidIntersections.AuditPairs(doc, PairRequest(a, a))));
        Test("intersection: negative tolerance rejected", () =>
        {
            var request = PairRequest(a, gap); request["tolerance"] = -1;
            ArgumentRejected(() => SolidIntersections.AuditPairs(doc, request));
        });
        Test("intersection: pair count budget reports truncation", () =>
        {
            var request = PairRequest(a, gap); ((JArray)request["pairs"]).Add(new JArray(a.ToString(), far.ToString()));
            request["max_pairs"] = 1;
            var result = SolidIntersections.AuditPairs(doc, request);
            Check((bool)result["truncated"] && (string)result["truncation_reason"] == "max_pairs", "Pair cap must be visible.");
            Check((int)result["requested_pairs"] == 2 && (int)result["evaluated_pairs"] == 1, "Requested/evaluated counts must preserve omitted work.");
        });
        Test("intersection: byte budget emits whole records within bound", () =>
        {
            var request = PairRequest(a, gap);
            for (int i = 1; i < 32; i++) ((JArray)request["pairs"]).Add(new JArray(a.ToString(), far.ToString()));
            request["max_pairs"] = 64; request["max_bytes"] = 4096;
            var result = SolidIntersections.AuditPairs(doc, request);
            Check((bool)result["truncated"] && (string)result["truncation_reason"] == "max_bytes", "Byte cap must be visible.");
            Check(System.Text.Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) <= 4096, "JSON exceeds requested byte bound.");
            foreach (JObject row in (JArray)result["pairs"]) Check(row["overlap"] is JObject, "Partial record emitted.");
        });
    }
}
