using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using Rhino.Geometry.Intersect;

// Read-only probes. Coordinates, lengths and tolerances are in document model units.
public static class AlmondTerrain
{
    private sealed class Target : IDisposable
    {
        public string Id;
        public Brep Brep;
        public Mesh Mesh;
        public bool OwnsBrep;
        public bool Closed;
        public bool Manifold;
        public bool IntervalClassificationSupported;
        public BoundingBox Bounds;
        public void Dispose() { if (OwnsBrep && Brep != null) Brep.Dispose(); }
    }

    private sealed class Budget
    {
        public int Tests;
        public int Results;
        public int Points;
        public int Curves;
        public readonly int MaxTests;
        public readonly int MaxResults;
        public readonly int MaxPoints;
        public readonly int MaxCurves;
        public readonly HashSet<string> Reasons = new HashSet<string>();
        public Budget(JObject q)
        {
            MaxTests = Limit(q, "max_tests", 20000, 100000);
            MaxResults = Limit(q, "max_results", 256, 4096);
            MaxPoints = Limit(q, "max_output_points", 4096, 16384);
            MaxCurves = Limit(q, "max_output_curves", 512, 4096);
        }
        public bool TakeTest()
        {
            if (Tests >= MaxTests) { Reasons.Add("max_tests"); return false; }
            if (Results >= MaxResults) { Reasons.Add("max_results"); return false; }
            Tests++; Results++; return true;
        }
        public bool TakePoint()
        {
            if (Points >= MaxPoints) { Reasons.Add("max_output_points"); return false; }
            Points++; return true;
        }
        public bool TakeCurve()
        {
            if (Curves >= MaxCurves) { Reasons.Add("max_output_curves"); return false; }
            Curves++; return true;
        }
    }

    private sealed class RayObservation
    {
        public string Id;
        public bool Known;
        public List<double[]> Intervals = new List<double[]>();
    }

    private static int Limit(JObject q, string key, int fallback, int ceiling)
    {
        var t = q[key];
        if (t == null) return fallback;
        if (t.Type != JTokenType.Integer) throw new ArgumentException(key + " must be an integer.");
        int n = t.Value<int>();
        if (n < 1 || n > ceiling) throw new ArgumentException(key + " must be in 1.." + ceiling + ".");
        return n;
    }

    private static double Number(JToken t, string name)
    {
        if (t == null || (t.Type != JTokenType.Integer && t.Type != JTokenType.Float))
            throw new ArgumentException(name + " must be a finite number.");
        double v = t.Value<double>();
        if (double.IsNaN(v) || double.IsInfinity(v)) throw new ArgumentException(name + " must be finite.");
        return v;
    }

    private static double Tolerance(RhinoDoc doc, JObject q)
    {
        double t = q["tolerance"] == null ? doc.ModelAbsoluteTolerance : Number(q["tolerance"], "tolerance");
        if (t <= 0 || double.IsNaN(t) || double.IsInfinity(t)) throw new ArgumentException("A positive finite tolerance is required.");
        return t;
    }

    private static JArray Point(Point3d p) { return new JArray(p.X, p.Y, p.Z); }
    private static JArray Box(BoundingBox b)
    {
        return b.IsValid ? new JArray(b.Min.X, b.Min.Y, b.Min.Z, b.Max.X, b.Max.Y, b.Max.Z) : null;
    }

    private static JObject Header(RhinoDoc doc, double tolerance, string method)
    {
        return new JObject {
            ["method"] = method,
            ["units"] = "model_units",
            ["model_unit_system"] = doc.ModelUnitSystem.ToString(),
            ["tolerance"] = tolerance,
            ["mutates_document"] = false,
            ["scope"] = "explicit_top_level_objects",
            ["interpretation"] = "Finite samples only; no whole-model clearance, constructability, or structural verdict."
        };
    }

    private static List<Target> Targets(RhinoDoc doc, JObject q, JArray inventory)
    {
        var ids = q["ids"] as JArray;
        if (ids == null || ids.Count == 0 || ids.Count > 128) throw new ArgumentException("ids must contain 1..128 explicit GUIDs.");
        var seen = new HashSet<Guid>();
        var parsed = new List<Guid>();
        foreach (var token in ids)
        {
            Guid id;
            if (token.Type != JTokenType.String || !Guid.TryParse(token.Value<string>(), out id) || id == Guid.Empty)
                throw new ArgumentException("Every ids item must be a nonempty GUID string.");
            if (!seen.Add(id)) throw new ArgumentException("ids must not contain duplicate GUIDs.");
            parsed.Add(id);
        }
        var targets = new List<Target>();
        try
        {
            foreach (var id in parsed)
            {
                var row = new JObject { ["id"] = id.ToString() };
                inventory.Add(row);
                var obj = doc.Objects.FindId(id);
                if (obj == null) { row["status"] = "missing"; continue; }
                if (obj.IsInstanceDefinitionGeometry) { row["status"] = "definition_member_unsupported"; continue; }
                var g = obj.Geometry;
                row["type"] = g == null ? "null" : g.GetType().Name;
                if (g == null || !g.IsValid) { row["status"] = "invalid_geometry"; continue; }
                var target = new Target { Id = id.ToString() };
                target.Brep = g as Brep;
                target.Mesh = g as Mesh;
                var extrusion = g as Extrusion;
                if (extrusion != null) { target.Brep = extrusion.ToBrep(); target.OwnsBrep = true; }
                if (target.Brep == null && target.Mesh == null)
                { target.Dispose(); row["status"] = "unsupported_geometry"; continue; }
                var geometry = target.Brep != null ? (GeometryBase)target.Brep : target.Mesh;
                if (!geometry.IsValid)
                { target.Dispose(); row["status"] = "invalid_converted_geometry"; continue; }
                target.Bounds = geometry.GetBoundingBox(true);
                if (!target.Bounds.IsValid)
                { target.Dispose(); row["status"] = "invalid_bounds"; continue; }
                target.Closed = target.Brep != null ? target.Brep.IsSolid : target.Mesh.IsClosed;
                if (target.Brep != null)
                {
                    target.Manifold = target.Brep.IsManifold;
                    row["manifold_test"] = "Brep.IsManifold";
                }
                else
                {
                    bool oriented, hasBoundary;
                    target.Manifold = target.Mesh.IsManifold(false, out oriented, out hasBoundary);
                    row["manifold_test"] = "Mesh.IsManifold";
                    row["mesh_manifold_topological_test"] = false;
                    row["mesh_manifold_edge_mode"] = "indexed_edges";
                    row["mesh_oriented"] = oriented;
                    row["mesh_has_boundary"] = hasBoundary;
                }
                target.IntervalClassificationSupported = target.Closed && target.Manifold;
                row["status"] = "ready";
                row["closed"] = target.Closed;
                row["manifold"] = target.Manifold;
                row["interval_classification_supported"] = target.IntervalClassificationSupported;
                row["bbox"] = Box(target.Bounds);
                targets.Add(target);
            }
            return targets;
        }
        catch { foreach (var target in targets) target.Dispose(); throw; }
    }

    private static void Finish(JObject output, Budget budget, long requestedTests, int completedSamples)
    {
        output["requested_tests_for_ready_objects"] = requestedTests;
        output["performed_tests"] = budget.Tests;
        output["unperformed_tests"] = requestedTests - budget.Tests;
        output["completed_samples"] = completedSamples;
        output["limits"] = new JObject { ["max_tests"] = budget.MaxTests, ["max_results"] = budget.MaxResults, ["max_output_points"] = budget.MaxPoints, ["max_output_curves"] = budget.MaxCurves };
        output["truncated"] = budget.Reasons.Count > 0;
        output["truncation_reasons"] = new JArray(budget.Reasons.OrderBy(x => x));
        output["global_verdict"] = "not_assessed";
    }

    public static JObject Sections(RhinoDoc doc, JObject q)
    {
        if (doc == null || q == null) throw new ArgumentNullException(doc == null ? "doc" : "q");
        string axis = q["axis"] == null ? "Z" : q["axis"].Value<string>().ToUpperInvariant();
        if (axis != "X" && axis != "Y" && axis != "Z") throw new ArgumentException("axis must be X, Y, or Z.");
        var stations = q["stations"] as JArray;
        if (stations == null || stations.Count == 0 || stations.Count > 256) throw new ArgumentException("stations must contain 1..256 model-coordinate positions.");
        var positions = stations.Select((t, i) => Number(t, "stations[" + i + "]")).ToArray();
        double tol = Tolerance(doc, q);
        int maxCurves = Limit(q, "max_curves_per_section", 32, 256);
        int samples = 0;
        if (q["sample_points"] != null)
        {
            if (q["sample_points"].Type != JTokenType.Integer) throw new ArgumentException("sample_points must be an integer.");
            samples = q["sample_points"].Value<int>();
            if (samples != 0 && (samples < 2 || samples > 64)) throw new ArgumentException("sample_points must be 0 or 2..64.");
        }
        var output = Header(doc, tol, "plane_sections");
        output["axis"] = axis;
        output["stations"] = new JArray(positions);
        output["sample_points_semantics"] = "Optional sampled display points; not exact polylines or a topology certificate.";
        var inventory = new JArray(); output["objects"] = inventory;
        var results = new JArray(); output["sections"] = results;
        var budget = new Budget(q);
        var targets = Targets(doc, q, inventory);
        int completed = 0;
        try
        {
            for (int si = 0; si < positions.Length; si++)
            {
                double station = positions[si];
                var origin = axis == "X" ? new Point3d(station, 0, 0) : axis == "Y" ? new Point3d(0, station, 0) : new Point3d(0, 0, station);
                var normal = axis == "X" ? Vector3d.XAxis : axis == "Y" ? Vector3d.YAxis : Vector3d.ZAxis;
                var plane = new Plane(origin, normal);
                bool complete = true;
                foreach (var target in targets)
                {
                    if (!budget.TakeTest()) { complete = false; break; }
                    var row = new JObject { ["sample_index"] = si, ["station"] = station, ["id"] = target.Id };
                    results.Add(row);
                    try
                    {
                        double minimum = axis == "X" ? target.Bounds.Min.X : axis == "Y" ? target.Bounds.Min.Y : target.Bounds.Min.Z;
                        double maximum = axis == "X" ? target.Bounds.Max.X : axis == "Y" ? target.Bounds.Max.Y : target.Bounds.Max.Z;
                        if (station < minimum - tol || station > maximum + tol)
                        {
                            row["status"] = "bbox_disjoint"; row["curve_count"] = 0;
                            row["closed_count"] = 0; row["open_count"] = 0;
                            row["curves"] = new JArray(); continue;
                        }
                        if (target.Brep != null) BrepSection(target.Brep, plane, tol, samples, maxCurves, budget, row);
                        else MeshSection(target.Mesh, plane, samples, maxCurves, budget, row);
                    }
                    catch (Exception e) { row["status"] = "unknown"; row["error"] = e.GetType().Name + ": " + e.Message; }
                }
                if (!complete) break;
                completed++;
            }
            Finish(output, budget, (long)positions.Length * targets.Count, completed);
            return output;
        }
        finally { foreach (var target in targets) target.Dispose(); }
    }

    private static void BrepSection(Brep brep, Plane plane, double tol, int samplePoints, int maxCurves, Budget budget, JObject row)
    {
        Curve[] raw = null;
        Curve[] joined = null;
        Point3d[] isolated = null;
        try
        {
            bool ok = Intersection.BrepPlane(brep, plane, tol, out raw, out isolated);
            row["kernel_success"] = ok;
            row["raw_curve_count"] = raw == null ? 0 : raw.Length;
            row["isolated_point_count"] = isolated == null ? 0 : isolated.Length;
            // A false kernel result is not evidence of a clear section.
            if (!ok) { row["status"] = "unknown"; row["reason"] = "BrepPlane returned false"; return; }
            joined = raw == null || raw.Length == 0 ? new Curve[0] : Curve.JoinCurves(raw, tol);
            if (joined == null) { row["status"] = "unknown"; row["reason"] = "JoinCurves returned null"; return; }
            row["curve_count"] = joined.Length;
            row["closed_count"] = joined.Count(c => c != null && c.IsClosed);
            row["open_count"] = joined.Count(c => c != null && !c.IsClosed);
            var curves = new JArray(); row["curves"] = curves;
            for (int i = 0; i < Math.Min(joined.Length, maxCurves); i++)
            {
                if (!budget.TakeCurve()) break;
                var curve = joined[i];
                if (curve == null) { curves.Add(new JObject { ["status"] = "unknown_null_curve" }); continue; }
                var item = new JObject { ["closed"] = curve.IsClosed, ["length"] = curve.GetLength(), ["bbox"] = Box(curve.GetBoundingBox(true)) };
                curves.Add(item);
                if (samplePoints > 0)
                {
                    var points = new JArray(); item["sampled_points"] = points;
                    for (int p = 0; p < samplePoints; p++)
                    { if (!budget.TakePoint()) break; points.Add(Point(curve.PointAtNormalizedLength((double)p / (samplePoints - 1)))); }
                    item["sampled_points_truncated"] = points.Count < samplePoints;
                }
            }
            row["omitted_curves"] = joined.Length - curves.Count;
            if (joined.Length > maxCurves) budget.Reasons.Add("max_curves_per_section");
            row["status"] = "observed";
        }
        finally
        {
            if (joined != null) foreach (var curve in joined) if (curve != null) curve.Dispose();
            if (raw != null) foreach (var curve in raw) if (curve != null) curve.Dispose();
        }
    }

    private static void MeshSection(Mesh mesh, Plane plane, int samplePoints, int maxCurves, Budget budget, JObject row)
    {
        var lines = Intersection.MeshPlane(mesh, plane);
        // Rhino returns null when no mesh/plane intersection exists.
        if (lines == null) lines = new Polyline[0];
        row["curve_count"] = lines.Length;
        row["closed_count"] = lines.Count(p => p.IsClosed);
        row["open_count"] = lines.Count(p => !p.IsClosed);
        var curves = new JArray(); row["curves"] = curves;
        for (int i = 0; i < Math.Min(lines.Length, maxCurves); i++)
        {
            if (!budget.TakeCurve()) break;
            var line = lines[i];
            var item = new JObject { ["closed"] = line.IsClosed, ["length"] = line.Length, ["bbox"] = Box(line.BoundingBox), ["vertex_count"] = line.Count };
            curves.Add(item);
            if (samplePoints > 0)
            {
                var points = new JArray(); item["sampled_points"] = points;
                int count = Math.Min(samplePoints, line.Count);
                for (int p = 0; p < count; p++)
                {
                    if (!budget.TakePoint()) break;
                    int index = count == 1 ? 0 : (int)Math.Round((double)p * (line.Count - 1) / (count - 1));
                    points.Add(Point(line[index]));
                }
                item["sampled_points_truncated"] = points.Count < count;
                item["sampled_points_semantics"] = "Subsample of original vertices; intermediate corners may be omitted.";
            }
        }
        row["omitted_curves"] = lines.Length - curves.Count;
        if (lines.Length > maxCurves) budget.Reasons.Add("max_curves_per_section");
        row["status"] = "observed";
    }

    public static JObject VerticalProbe(RhinoDoc doc, JObject q)
    {
        if (doc == null || q == null) throw new ArgumentNullException(doc == null ? "doc" : "q");
        var xy = q["xy"] as JArray;
        if (xy == null || xy.Count == 0 || xy.Count > 20000) throw new ArgumentException("xy must contain 1..20000 [x,y] pairs.");
        var positions = new List<double[]>();
        for (int i = 0; i < xy.Count; i++)
        {
            var pair = xy[i] as JArray;
            if (pair == null || pair.Count != 2) throw new ArgumentException("Each xy entry must contain exactly two numbers.");
            positions.Add(new[] { Number(pair[0], "x"), Number(pair[1], "y") });
        }
        double tol = Tolerance(doc, q);
        var budget = new Budget(q);
        int maxHits = Limit(q, "max_hits_per_object", 128, 2048);
        int maxOverlaps = Limit(q, "max_overlaps", 256, 4096);
        int maxOverlapTests = Limit(q, "max_overlap_tests", 20000, 100000);
        int overlapTests = 0;
        var output = Header(doc, tol, "vertical_line_probes");
        output["requested_sample_count"] = positions.Count;
        output["interval_semantics"] = "Midpoint-classified segments between sorted intersections within the stated z range. Only valid closed manifold objects are classified; boundary-coincident and unresolved cases remain unknown.";
        var inventory = new JArray(); output["objects"] = inventory;
        var results = new JArray(); output["rays"] = results;
        var overlaps = new JArray(); output["sampled_overlaps"] = overlaps;
        var targets = Targets(doc, q, inventory);
        int completed = 0;
        try
        {
            if ((q["z_min"] == null) != (q["z_max"] == null)) throw new ArgumentException("Supply both z_min and z_max or neither.");
            double zmin, zmax;
            if (q["z_min"] != null)
            { zmin = Number(q["z_min"], "z_min"); zmax = Number(q["z_max"], "z_max"); }
            else if (targets.Count > 0)
            {
                double low = targets.Min(t => t.Bounds.Min.Z), high = targets.Max(t => t.Bounds.Max.Z);
                double margin = Math.Max(10 * tol, (high - low) * 0.01);
                zmin = low - margin; zmax = high + margin;
            }
            else
            {
                output["z_range"] = JValue.CreateNull();
                output["reason"] = "No supported valid objects; no rays were evaluated.";
                Finish(output, budget, 0, 0); return output;
            }
            if (double.IsInfinity(zmin) || double.IsInfinity(zmax) || zmax - zmin <= 2 * tol)
                throw new ArgumentException("z_max - z_min must exceed twice tolerance and bounds must be finite.");
            output["z_range"] = new JArray(zmin, zmax);
            output["z_range_source"] = q["z_min"] == null ? "target_bbox_with_margin" : "explicit_clipped_range";
            for (int si = 0; si < positions.Count; si++)
            {
                var position = positions[si];
                var line = new Line(new Point3d(position[0], position[1], zmin), new Point3d(position[0], position[1], zmax));
                var observed = new List<RayObservation>();
                bool complete = true;
                foreach (var target in targets)
                {
                    if (!budget.TakeTest()) { complete = false; break; }
                    var row = new JObject { ["sample_index"] = si, ["xy"] = new JArray(position), ["id"] = target.Id };
                    results.Add(row);
                    try { observed.Add(Ray(target, line, tol, maxHits, budget, row)); }
                    catch (Exception e)
                    { row["status"] = "unknown"; row["error"] = e.GetType().Name + ": " + e.Message; observed.Add(new RayObservation { Id = target.Id }); }
                }
                // Report only demonstrated positive-length overlaps, never infer absence from unknown rays.
                for (int a = 0; a < observed.Count && overlapTests < maxOverlapTests; a++)
                for (int b = a + 1; b < observed.Count && overlapTests < maxOverlapTests; b++)
                {
                    if (!observed[a].Known || !observed[b].Known) continue;
                    // Both interval lists are sorted and disjoint: advance one boundary at a time.
                    int ai = 0, bi = 0;
                    while (ai < observed[a].Intervals.Count && bi < observed[b].Intervals.Count)
                    {
                        if (overlapTests >= maxOverlapTests) { budget.Reasons.Add("max_overlap_tests"); break; }
                        overlapTests++;
                        var ia = observed[a].Intervals[ai]; var ib = observed[b].Intervals[bi];
                        double low = Math.Max(ia[0], ib[0]), high = Math.Min(ia[1], ib[1]);
                        if (high - low > tol)
                        {
                            if (overlaps.Count >= maxOverlaps) budget.Reasons.Add("max_overlaps");
                            else overlaps.Add(new JObject { ["sample_index"] = si, ["xy"] = new JArray(position), ["a"] = observed[a].Id, ["b"] = observed[b].Id, ["z_interval"] = new JArray(low, high), ["depth"] = high - low });
                        }
                        if (ia[1] <= ib[1]) ai++; else bi++;
                    }
                }
                if (overlapTests >= maxOverlapTests) budget.Reasons.Add("max_overlap_tests");
                if (!complete) break;
                completed++;
            }
            output["overlap_interpretation"] = "Positive sampled interval overlap between closed manifold objects. Zero reported overlaps is not a global clearance result; unsupported, open, nonmanifold, boundary, and untested cases are excluded.";
            output["overlap_interval_comparisons"] = overlapTests;
            output["max_overlap_tests"] = maxOverlapTests;
            Finish(output, budget, (long)positions.Count * targets.Count, completed);
            return output;
        }
        finally { foreach (var target in targets) target.Dispose(); }
    }

    private static RayObservation Ray(Target target, Line line, double tol, int maxHits, Budget budget, JObject row)
    {
        var result = new RayObservation { Id = target.Id };
        double low = line.From.Z, high = line.To.Z;
        // Bbox disjointness establishes an empty sample without relying on kernel false/null conventions.
        var b = target.Bounds;
        if (line.From.X < b.Min.X - tol || line.From.X > b.Max.X + tol || line.From.Y < b.Min.Y - tol || line.From.Y > b.Max.Y + tol || high < b.Min.Z - tol || low > b.Max.Z + tol)
        {
            row["status"] = "bbox_disjoint"; row["hit_z"] = new JArray();
            result.Known = target.IntervalClassificationSupported;
            row["intervals_known"] = result.Known;
            if (result.Known) row["filled_intervals"] = new JArray();
            return result;
        }
        var hits = new List<double>();
        bool boundary = false;
        if (target.Brep != null)
        {
            Curve[] coincident = null;
            Point3d[] points = null;
            try
            {
                using (var curve = new LineCurve(line))
                {
                    bool ok = Intersection.CurveBrep(curve, target.Brep, tol, out coincident, out points);
                    row["kernel_success"] = ok;
                    if (!ok) { row["status"] = "unknown"; row["reason"] = "CurveBrep returned false"; return result; }
                }
                boundary = coincident != null && coincident.Length > 0;
                if (points != null) foreach (var point in points) hits.Add(point.Z);
            }
            finally { if (coincident != null) foreach (var curve in coincident) if (curve != null) curve.Dispose(); }
        }
        else
        {
            var points = Intersection.MeshLine(target.Mesh, line);
            if (points != null) foreach (var point in points) hits.Add(point.Z);
        }
        hits = hits.Where(z => !double.IsNaN(z) && !double.IsInfinity(z) && z >= low - tol && z <= high + tol).OrderBy(z => z).ToList();
        var merged = new List<double>();
        foreach (var z in hits) if (merged.Count == 0 || z - merged[merged.Count - 1] > tol) merged.Add(Math.Max(low, Math.Min(high, z)));
        row["raw_hit_count"] = hits.Count;
        row["unique_hit_count"] = merged.Count;
        var shownHits = new JArray(); row["hit_z"] = shownHits;
        foreach (double z in merged.Take(maxHits))
        { if (!budget.TakePoint()) break; shownHits.Add(z); }
        row["omitted_hits"] = merged.Count - shownHits.Count;
        if (shownHits.Count < Math.Min(merged.Count, maxHits))
        { row["status"] = "unknown"; row["reason"] = "Output point budget exhausted; intervals were not classified."; return result; }
        if (merged.Count > maxHits)
        { budget.Reasons.Add("max_hits_per_object"); row["status"] = "unknown"; row["reason"] = "Hit limit exceeded; intervals were not classified."; return result; }
        if (!target.Closed)
        { row["status"] = "surface_hits_only"; row["intervals_known"] = false; row["reason"] = "Open geometry has no established filled volume."; return result; }
        if (!target.IntervalClassificationSupported)
        { row["status"] = "unknown"; row["intervals_known"] = false; row["reason"] = "Closed geometry is nonmanifold; surface hits do not establish filled volume."; return result; }
        if (boundary)
        { row["status"] = "unknown"; row["intervals_known"] = false; row["reason"] = "Probe overlaps a Brep boundary curve."; return result; }
        var cuts = new List<double> { low };
        cuts.AddRange(merged.Where(z => z > low + tol && z < high - tol));
        cuts.Add(high);
        var intervals = new JArray(); row["filled_intervals"] = intervals;
        for (int i = 0; i + 1 < cuts.Count; i++)
        {
            if (cuts[i + 1] - cuts[i] <= 2 * tol)
            { row["status"] = "unknown"; row["intervals_known"] = false; row["reason"] = "A segment is too short to classify outside boundary tolerance."; row.Remove("filled_intervals"); result.Intervals.Clear(); return result; }
            var midpoint = new Point3d(line.From.X, line.From.Y, (cuts[i] + cuts[i + 1]) / 2);
            bool nearBoundary;
            if (target.Brep != null)
            {
                var nearest = target.Brep.ClosestPoint(midpoint);
                nearBoundary = !nearest.IsValid || nearest.DistanceTo(midpoint) <= tol;
            }
            else
            {
                var nearest = target.Mesh.ClosestMeshPoint(midpoint, tol);
                nearBoundary = nearest != null && nearest.Point.DistanceTo(midpoint) <= tol;
            }
            if (nearBoundary)
            { row["status"] = "unknown"; row["intervals_known"] = false; row["reason"] = "A segment midpoint touches the boundary within tolerance."; row.Remove("filled_intervals"); result.Intervals.Clear(); return result; }
            bool strict = target.Brep != null ? target.Brep.IsPointInside(midpoint, tol, true) : target.Mesh.IsPointInside(midpoint, tol, true);
            bool loose = target.Brep != null ? target.Brep.IsPointInside(midpoint, tol, false) : target.Mesh.IsPointInside(midpoint, tol, false);
            if (strict != loose)
            { row["status"] = "unknown"; row["intervals_known"] = false; row["reason"] = "A segment midpoint is within boundary tolerance."; row.Remove("filled_intervals"); result.Intervals.Clear(); return result; }
            if (strict)
            {
                if (!budget.TakePoint() || !budget.TakePoint())
                { row["status"] = "unknown"; row["intervals_known"] = false; row["reason"] = "Output point budget exhausted; intervals were not returned."; row.Remove("filled_intervals"); result.Intervals.Clear(); return result; }
                result.Intervals.Add(new[] { cuts[i], cuts[i + 1] });
                intervals.Add(new JArray(cuts[i], cuts[i + 1]));
            }
        }
        row["status"] = "observed";
        row["intervals_known"] = true;
        row["range_clipped"] = result.Intervals.Any(i => Math.Abs(i[0] - low) <= tol || Math.Abs(i[1] - high) <= tol);
        result.Known = true;
        return result;
    }
}
