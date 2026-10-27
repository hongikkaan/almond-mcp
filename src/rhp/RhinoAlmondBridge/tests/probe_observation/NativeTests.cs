using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;

// Independent geometric fixtures. Runs only inside its own headless document.
public static class NativeTests
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
            RunJointTests(doc);
            RunTerrainTests(doc);
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

    private static void RunJointTests(RhinoDoc doc)
    {
        Guid a = Box(doc, 0, 0, 0), overlap = Box(doc, 5, 0, 0), contact = Box(doc, 10, 0, 0);
        Guid gap = Box(doc, 12, 0, 0), contained = Box(doc, 2, 2, 2, 5, 5, 5), far = Box(doc, 30, 20, 10);
        Test("joint: overlapping 10 mm cubes have 500 mm3 intersection", () => Near(OverlapVolume(AlmondJoints.AuditPairs(doc, PairRequest(a, overlap))), 500));
        Test("joint: 5 mm cube fully contained has 125 mm3 intersection", () => Near(OverlapVolume(AlmondJoints.AuditPairs(doc, PairRequest(a, contained))), 125));
        Test("joint: face-contact does not report positive overlap", () =>
        {
            var row = PairRow(AlmondJoints.AuditPairs(doc, PairRequest(a, contact)));
            var value = row["overlap"]["volume_model_units3"];
            if (value != null && value.Type != JTokenType.Null) Near((double)value, 0);
            else Check((string)row["overlap"]["status"] == "unknown", "Unavailable contact volume must stay unknown.");
        });
        Test("joint: 2 mm separation has zero overlap", () => Near(OverlapVolume(AlmondJoints.AuditPairs(doc, PairRequest(a, gap))), 0));
        Test("joint: 2 mm separation labels bbox distance as a lower bound", () =>
        {
            var row = PairRow(AlmondJoints.AuditPairs(doc, PairRequest(a, gap)));
            Near((double)row["bbox_distance_lower_bound"], 2);
            Check((string)row["surface_gap_status"] == "not_measured", "BBox distance must not be presented as measured surface gap.");
            Check(row["surface_gap"].Type == JTokenType.Null, "Unmeasured gap must be null.");
        });
        Test("joint: fully separated boxes have zero overlap", () => Near(OverlapVolume(AlmondJoints.AuditPairs(doc, PairRequest(a, far))), 0));
        Test("joint: operation comparisons preserve input geometry", () =>
        {
            var before = GeometryCrcs(doc, a, overlap);
            var request = PairRequest(a, overlap); request["compare_operations"] = true;
            Near(OverlapVolume(AlmondJoints.AuditPairs(doc, request)), 500);
            AssertUnchanged(doc, before);
        });
        Test("joint: inward solid normalized on duplicate only", () =>
        {
            Guid inward;
            using (var reversed = Brep.CreateFromBox(new BoundingBox(new Point3d(0, 0, 0), new Point3d(10, 10, 10))))
            { reversed.Flip(); inward = doc.Objects.AddBrep(reversed); }
            var before = GeometryCrcs(doc, inward, overlap);
            Near(OverlapVolume(AlmondJoints.AuditPairs(doc, PairRequest(inward, overlap))), 500);
            AssertUnchanged(doc, before);
        });
        Test("joint: missing object is unsupported with unknown volume", () => UnsupportedPair(AlmondJoints.AuditPairs(doc, PairRequest(a, Guid.NewGuid()))));
        Test("joint: mesh input is explicitly unsupported", () =>
        {
            Guid mesh = MeshBox(doc, 0, 0, 0);
            UnsupportedPair(AlmondJoints.AuditPairs(doc, PairRequest(a, mesh)));
        });
        Test("joint: open Brep is explicitly unsupported", () =>
        {
            using (var surface = new PlaneSurface(Plane.WorldXY, new Interval(0, 10), new Interval(0, 10)))
            using (var brep = surface.ToBrep())
                UnsupportedPair(AlmondJoints.AuditPairs(doc, PairRequest(a, doc.Objects.AddBrep(brep))));
        });
        Test("joint: empty pairs rejected", () => ArgumentRejected(() => AlmondJoints.AuditPairs(doc, new JObject { ["pairs"] = new JArray() })));
        Test("joint: same-object pair rejected", () => ArgumentRejected(() => AlmondJoints.AuditPairs(doc, PairRequest(a, a))));
        Test("joint: negative tolerance rejected", () =>
        {
            var request = PairRequest(a, gap); request["tolerance"] = -1;
            ArgumentRejected(() => AlmondJoints.AuditPairs(doc, request));
        });
        Test("joint: pair count budget reports truncation", () =>
        {
            var request = PairRequest(a, gap); ((JArray)request["pairs"]).Add(new JArray(a.ToString(), far.ToString()));
            request["max_pairs"] = 1;
            var result = AlmondJoints.AuditPairs(doc, request);
            Check((bool)result["truncated"] && (string)result["truncation_reason"] == "max_pairs", "Pair cap must be visible.");
            Check((int)result["requested_pairs"] == 2 && (int)result["evaluated_pairs"] == 1, "Requested/evaluated counts must preserve omitted work.");
        });
        Test("joint: byte budget emits whole records within bound", () =>
        {
            var request = PairRequest(a, gap);
            for (int i = 1; i < 32; i++) ((JArray)request["pairs"]).Add(new JArray(a.ToString(), far.ToString()));
            request["max_pairs"] = 64; request["max_bytes"] = 4096;
            var result = AlmondJoints.AuditPairs(doc, request);
            Check((bool)result["truncated"] && (string)result["truncation_reason"] == "max_bytes", "Byte cap must be visible.");
            Check(System.Text.Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) <= 4096, "JSON exceeds requested byte bound.");
            foreach (JObject row in (JArray)result["pairs"]) Check(row["overlap"] is JObject, "Partial record emitted.");
        });
    }

    private static void RunTerrainTests(RhinoDoc doc)
    {
        Guid brep = Box(doc, 100, 200, 300, 10, 20, 30);
        Guid mesh = MeshBox(doc, 100, 200, 300, 10, 20, 30);
        string[] axes = { "X", "Y", "Z" };
        double[] stations = { 105, 210, 315 };
        double[] perimeters = { 100, 80, 60 };
        for (int ai = 0; ai < axes.Length; ai++)
        {
            int axisIndex = ai;
            Test("section: " + axes[ai] + " plane cuts Brep and Mesh boxes", () =>
            {
                var request = new JObject {
                    ["ids"] = new JArray(brep.ToString(), mesh.ToString()),
                    ["axis"] = axes[axisIndex], ["stations"] = new JArray(stations[axisIndex])
                };
                var result = AlmondTerrain.Sections(doc, request);
                var rows = (JArray)result["sections"];
                Check(rows.Count == 2, "Expected one section for each explicit object.");
                foreach (JObject row in rows)
                {
                    Check((string)row["status"] == "observed", "Interior box section must be observed: " + row);
                    Check((int)row["curve_count"] == 1 && (int)row["closed_count"] == 1 && (int)row["open_count"] == 0,
                        "A plane through a box interior must produce one closed rectangle.");
                    var curve = (JObject)row["curves"][0];
                    Near((double)curve["length"], perimeters[axisIndex]);
                    Near((double)curve["bbox"][axisIndex], stations[axisIndex]);
                    Near((double)curve["bbox"][axisIndex + 3], stations[axisIndex]);
                }
                Check((string)result["global_verdict"] == "not_assessed", "Finite sections must not claim whole-model validity.");
            });
        }
        Test("section: sampling preserves input geometry", () =>
        {
            var before = GeometryCrcs(doc, brep, mesh);
            var request = new JObject {
                ["ids"] = new JArray(brep.ToString(), mesh.ToString()), ["axis"] = "Z",
                ["stations"] = new JArray(305, 315, 325), ["sample_points"] = 8
            };
            AlmondTerrain.Sections(doc, request);
            AssertUnchanged(doc, before);
        });
        Test("section: outside Mesh section is empty", () =>
        {
            var result = AlmondTerrain.Sections(doc, new JObject {
                ["ids"] = new JArray(mesh.ToString()), ["axis"] = "Z", ["stations"] = new JArray(350)
            });
            var row = result["sections"][0];
            Check(((string)row["status"] == "observed" || (string)row["status"] == "bbox_disjoint") && (int)row["curve_count"] == 0, "Outside Mesh section must be empty.");
        });
        Test("vertical: one solid interval for Brep and Mesh", () =>
        {
            foreach (Guid id in new[] { brep, mesh })
            {
                var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { id }, 105, 210, 299, 331));
                var ray = result["rays"][0];
                Check((bool)ray["intervals_known"], "Interior box ray must have known filled intervals: " + ray);
                var intervals = (JArray)ray["filled_intervals"];
                Check(intervals.Count == 1, "Single box must yield one filled interval.");
                Near((double)intervals[0][0], 300); Near((double)intervals[0][1], 330);
                Check(!(bool)ray["range_clipped"], "Bounding range encloses this solid.");
                Check(((JArray)ray["hit_z"]).Count == 2, "Coincident triangle hits should be merged.");
            }
        });
        Test("vertical: disconnected closed Mesh yields two filled intervals", () =>
        {
            Guid disconnected;
            using (var first = Mesh.CreateFromBox(new Rhino.Geometry.Box(Plane.WorldXY, new Interval(100, 110), new Interval(200, 220), new Interval(300, 310)), 1, 1, 1))
            using (var second = Mesh.CreateFromBox(new Rhino.Geometry.Box(Plane.WorldXY, new Interval(100, 110), new Interval(200, 220), new Interval(320, 330)), 1, 1, 1))
            {
                first.Append(second);
                disconnected = doc.Objects.AddMesh(first);
            }
            var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { disconnected }, 105, 210, 299, 331));
            var ray = result["rays"][0];
            Check((bool)ray["intervals_known"], "Closed disjoint components must be classifiable.");
            var intervals = (JArray)ray["filled_intervals"];
            Check(intervals.Count == 2, "Two disconnected solids need two filled intervals.");
            Near((double)intervals[0][0], 300); Near((double)intervals[0][1], 310);
            Near((double)intervals[1][0], 320); Near((double)intervals[1][1], 330);
        });
        Test("vertical: intersecting boxes show 15 mm sampled depth", () =>
        {
            Guid shifted = Box(doc, 100, 200, 315, 10, 20, 30);
            var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { brep, shifted }, 105, 210, 299, 346));
            var overlaps = (JArray)result["sampled_overlaps"];
            Check(overlaps.Count == 1, "One overlap interval expected.");
            Near((double)overlaps[0]["depth"], 15);
            Near((double)overlaps[0]["z_interval"][0], 315);
            Near((double)overlaps[0]["z_interval"][1], 330);
        });
        Test("vertical: exterior ray is known empty", () =>
        {
            var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { brep, mesh }, 150, 250, 299, 331));
            foreach (JObject ray in (JArray)result["rays"])
                Check((string)ray["status"] == "bbox_disjoint" && (bool)ray["intervals_known"] && ((JArray)ray["filled_intervals"]).Count == 0,
                    "Exterior closed-object probe must be known empty.");
        });
        Test("vertical: clipped interior range remains explicitly clipped", () =>
        {
            var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { mesh }, 105, 210, 305, 325));
            var ray = result["rays"][0];
            Check((bool)ray["intervals_known"] && (bool)ray["range_clipped"], "The query range is wholly within the solid.");
            Near((double)ray["filled_intervals"][0][0], 305);
            Near((double)ray["filled_intervals"][0][1], 325);
        });
        Test("vertical: open surface has hits but no filled-volume claim", () =>
        {
            Guid open;
            using (var surface = new PlaneSurface(new Plane(new Point3d(100, 200, 315), Vector3d.XAxis, Vector3d.YAxis), new Interval(0, 10), new Interval(0, 20)))
            using (var b = surface.ToBrep()) open = doc.Objects.AddBrep(b);
            var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { open }, 105, 210, 299, 331));
            var ray = result["rays"][0];
            Check((string)ray["status"] == "surface_hits_only" && !(bool)ray["intervals_known"], "Open surface cannot establish filled volume.");
        });
        Test("vertical: valid closed nonmanifold Mesh makes no filled-volume claim", () =>
        {
            Guid nonmanifold;
            // Two individually closed cubes share exactly one edge, with no duplicate faces.
            using (var first = Mesh.CreateFromBox(new Rhino.Geometry.Box(Plane.WorldXY, new Interval(100, 110), new Interval(200, 210), new Interval(300, 310)), 1, 1, 1))
            using (var second = Mesh.CreateFromBox(new Rhino.Geometry.Box(Plane.WorldXY, new Interval(110, 120), new Interval(210, 220), new Interval(300, 310)), 1, 1, 1))
            {
                first.Append(second);
                first.Vertices.CombineIdentical(true, true);
                first.Normals.ComputeNormals();
                first.Compact();
                Check(first.IsValid && first.IsClosed, "Fixture must be valid and closed before testing manifold restrictions.");
                Check(Enumerable.Range(0, first.TopologyEdges.Count).Any(i => first.TopologyEdges.GetConnectedFaces(i).Length > 2),
                    "Fixture must have an edge incident to more than two faces.");
                nonmanifold = doc.Objects.AddMesh(first);
            }
            var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { nonmanifold }, 105, 205, 299, 311));
            var rays = (JArray)result["rays"];
            Check(rays.Count == 1, "Unsupported volume classification must retain its ray observation.");
            var ray = rays[0];
            Check(ray["intervals_known"] != null && !(bool)ray["intervals_known"], "Closed nonmanifold Mesh must not establish filled volume.");
            var intervals = ray["filled_intervals"] as JArray;
            Check(intervals == null || intervals.Count == 0, "No filled intervals may be claimed for a nonmanifold Mesh.");
            Check(((JArray)result["sampled_overlaps"]).Count == 0, "Unsupported volume must not yield overlap claims.");
        });
        Test("vertical: face-coincident boundary ray remains unknown", () =>
        {
            // x=100 is the box's side face; y=210 is strictly between its other side faces.
            foreach (Guid id in new[] { brep, mesh })
            {
                var result = AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { id }, 100, 210, 299, 331));
                var ray = result["rays"][0];
                Check((string)ray["status"] == "unknown", "Boundary-coincident ray must remain unknown.");
                Check(ray["intervals_known"] == null || !(bool)ray["intervals_known"], "Boundary ambiguity cannot establish intervals.");
                var intervals = ray["filled_intervals"] as JArray;
                Check(intervals == null || intervals.Count == 0, "Boundary ray must not claim filled intervals.");
            }
        });
        Test("terrain: missing and unsupported objects stay explicit", () =>
        {
            Guid point = doc.Objects.AddPoint(new Point3d(105, 210, 315));
            var request = RayRequest(new[] { Guid.NewGuid(), point }, 105, 210, 299, 331);
            var result = AlmondTerrain.VerticalProbe(doc, request);
            var objects = (JArray)result["objects"];
            Check((string)objects[0]["status"] == "missing" && (string)objects[1]["status"] == "unsupported_geometry", "Missing/unsupported inputs must remain visible.");
            Check(((JArray)result["rays"]).Count == 0, "Unsupported objects must not produce false empty rays.");
        });
        Test("terrain: unsupported axis rejected", () => ArgumentRejected(() => AlmondTerrain.Sections(doc,
            new JObject { ["ids"] = new JArray(brep.ToString()), ["axis"] = "A", ["stations"] = new JArray(315) })));
        Test("terrain: half-specified z range rejected", () =>
        {
            var request = RayRequest(new[] { brep }, 105, 210, 299, 331); request.Remove("z_max");
            ArgumentRejected(() => AlmondTerrain.VerticalProbe(doc, request));
        });
        Test("terrain: duplicate handles rejected", () => ArgumentRejected(() => AlmondTerrain.VerticalProbe(doc,
            RayRequest(new[] { brep, brep }, 105, 210, 299, 331))));
        Test("terrain: operation budget preserves unperformed count", () =>
        {
            var request = RayRequest(new[] { brep, mesh }, 105, 210, 299, 331);
            ((JArray)request["xy"]).Add(new JArray(106, 211)); request["max_tests"] = 1;
            var result = AlmondTerrain.VerticalProbe(doc, request);
            Check((bool)result["truncated"], "Operation cap must be visible.");
            Check((int)result["performed_tests"] == 1 && (int)result["unperformed_tests"] == 3, "Four requested object/ray tests with one performed must leave three unperformed.");
            Check((int)result["completed_samples"] == 0, "A partly evaluated sample is not complete.");
        });
        Test("terrain: output point budget reports truncated curve sampling", () =>
        {
            var result = AlmondTerrain.Sections(doc, new JObject {
                ["ids"] = new JArray(brep.ToString()), ["axis"] = "Z", ["stations"] = new JArray(315),
                ["sample_points"] = 8, ["max_output_points"] = 2
            });
            Check((bool)result["truncated"], "Point budget truncation must be visible.");
            var curve = result["sections"][0]["curves"][0];
            Check(((JArray)curve["sampled_points"]).Count == 2 && (bool)curve["sampled_points_truncated"], "Requested sampled curve must obey point cap.");
        });
        Test("vertical: observations preserve input geometry", () =>
        {
            var before = GeometryCrcs(doc, brep, mesh);
            AlmondTerrain.VerticalProbe(doc, RayRequest(new[] { brep, mesh }, 105, 210, 299, 331));
            AssertUnchanged(doc, before);
        });
    }

    private static JObject RayRequest(IEnumerable<Guid> ids, double x, double y, double zMin, double zMax)
    {
        return new JObject {
            ["ids"] = new JArray(ids.Select(id => id.ToString())),
            ["xy"] = new JArray { new JArray(x, y) },
            ["z_min"] = zMin, ["z_max"] = zMax, ["tolerance"] = 0.01
        };
    }
}
