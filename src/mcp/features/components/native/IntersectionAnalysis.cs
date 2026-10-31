using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // Detached observations. A handle identifies a world-space occurrence, never a definition to edit.
    public static class IntersectionAnalysis
    {
        internal const int MaxLeaves = 2048;
        internal const int MaxCandidates = 20000;
        internal const int MaxMeshFaces = 500000;

        internal sealed class Member : IDisposable
        {
            internal Guid RootId;
            internal Guid[] Path;
            internal GeometryBase Geometry;
            internal JObject Info;
            internal string Key;
            internal string Fingerprint;
            internal bool Supported;
            internal BoundingBox Bounds;
            public void Dispose() { Geometry?.Dispose(); Geometry = null; }
        }

        internal sealed class Scope : IDisposable
        {
            internal readonly List<Member> Members = new List<Member>();
            internal readonly JArray Unsupported = new JArray();
            public void Dispose() { foreach (var member in Members) member.Dispose(); }
        }

        internal sealed class Observation : IDisposable
        {
            internal JObject Report;
            internal readonly List<GeometryBase> Regions = new List<GeometryBase>();
            public void Dispose() { foreach (var region in Regions) region?.Dispose(); Regions.Clear(); }
        }

        public static JObject Query(RhinoDoc doc, Guid[] ids, int maxPairs = 64,
            bool includeBlocks = false, string cursor = "")
            => QueryForPreview(doc, ids, maxPairs, includeBlocks, cursor, null);

        internal static JObject QueryForPreview(RhinoDoc doc, Guid[] ids, int maxPairs,
            bool includeBlocks, string cursor, Action<Observation> accept)
        {
            if (doc == null) throw new ArgumentException("No Rhino document is available.");
            if (ids == null || ids.Length < 1 || ids.Length > 512 || ids.Any(id => id == Guid.Empty))
                throw new ArgumentException("Supply 1..512 current top-level object GUIDs.");
            if (maxPairs < 1 || maxPairs > 64) throw new ArgumentException("max_pairs must be between 1 and 64.");
            if (cursor == null || cursor.Length > 256) throw new ArgumentException("cursor must be a string of at most 256 characters.");
            double tolerance = Tolerance(doc);
            using (var scope = Resolve(doc, ids.Distinct().OrderBy(id => id), includeBlocks))
            {
                var supported = scope.Members.Where(m => m.Supported).OrderBy(m => m.Bounds.Min.X)
                    .ThenBy(m => m.Key, StringComparer.Ordinal).ToArray();
                string fingerprint = ScopeState(doc, scope, includeBlocks);
                int offset = DecodeCursor(cursor, fingerprint);
                var candidates = new List<Tuple<Member, Member>>();
                for (int i = 0; i < supported.Length; i++)
                    for (int j = i + 1; j < supported.Length; j++)
                    {
                        var a = supported[i]; var b = supported[j];
                        if (b.Bounds.Min.X - a.Bounds.Max.X > tolerance) break;
                        if (BoxDistance(a.Bounds, b.Bounds) > tolerance) continue;
                        candidates.Add(Tuple.Create(a, b));
                        if (candidates.Count > MaxCandidates)
                            throw new ArgumentException("More than 20000 candidate pairs; narrow the object scope.");
                    }
                if (offset > candidates.Count) throw new ArgumentException("Cursor is outside this unchanged candidate set.");
                var rows = new JArray();
                var answer = new JObject {
                    ["status"] = "success", ["schema"] = "almond-component-intersections/v2",
                    ["model_path"] = doc.Path, ["document_units"] = doc.ModelUnitSystem.ToString(),
                    ["tolerance_model_units"] = tolerance, ["include_blocks"] = includeBlocks,
                    ["object_ids"] = new JArray(ids.Distinct().OrderBy(id => id).Select(id => id.ToString("D"))),
                    ["object_count"] = ids.Distinct().Count(), ["occurrence_count"] = scope.Members.Count,
                    ["supported_object_count"] = supported.Select(m => m.RootId).Distinct().Count(),
                    ["supported_occurrence_count"] = supported.Length, ["unsupported_objects"] = scope.Unsupported,
                    ["candidate_pair_count"] = candidates.Count,
                    ["bbox_pruned_pair_count"] = (long)supported.Length * (supported.Length - 1) / 2 - candidates.Count,
                    ["offset"] = offset, ["max_pairs"] = maxPairs, ["pairs"] = rows,
                    ["scope_state"] = fingerprint,
                    ["limitations"] = new JArray(
                        "All distinct resolved occurrence pairs are considered, including members of one block. Groups do not expand the set.",
                        "Only valid closed Breps, Extrusions and oriented manifold Meshes support volume observations. Block expansion is optional and read-only.",
                        "Mixed Brep/Mesh pairs use a temporary meshed Brep approximation; the method and meshing tolerance are reported.",
                        "Empty or failed Boolean results remain unknown. Separate page results must be accumulated; complete refers to this response's coverage.",
                        "Pair volumes are not summed because different overlap regions may overlap each other.")
                };
                for (int i = offset; i < candidates.Count && rows.Count < maxPairs; i++)
                {
                    using (var observation = Observe(doc, candidates[i].Item1, candidates[i].Item2))
                    {
                        observation.Report["pair_index"] = i;
                        rows.Add(observation.Report);
                        if (Encoding.UTF8.GetByteCount(answer.ToString(Formatting.None)) > 248000)
                        {
                            rows.RemoveAt(rows.Count - 1);
                            if (rows.Count == 0) throw new ArgumentException("A pair report exceeds the response budget; narrow block scope.");
                            break;
                        }
                        accept?.Invoke(observation);
                    }
                }
                int next = offset + rows.Count;
                int positives = rows.Count(p => (string)p["overlap"]?["status"] == "positive_volume");
                int unknown = rows.Count(p => (string)p["overlap"]?["status"] != "positive_volume" &&
                    (string)p["overlap"]?["status"] != "zero_volume");
                bool complete = offset == 0 && next == candidates.Count && scope.Unsupported.Count == 0 && unknown == 0;
                answer["evaluated_pairs"] = rows.Count;
                answer["positive_pair_count"] = positives;
                answer["unknown_pair_count"] = unknown;
                answer["remaining_candidate_pairs"] = candidates.Count - next;
                answer["next_cursor"] = next < candidates.Count ? fingerprint + ":" + next.ToString(CultureInfo.InvariantCulture) : null;
                answer["pagination_complete"] = next == candidates.Count;
                answer["truncated"] = next < candidates.Count;
                answer["truncation_reason"] = next < candidates.Count ? "page_limit" : null;
                answer["complete"] = complete;
                answer["has_positive_overlap"] = positives > 0 ? new JValue(true) : complete ? new JValue(false) : JValue.CreateNull();
                if (Encoding.UTF8.GetByteCount(answer.ToString(Formatting.None)) > 262144)
                    throw new ArgumentException("Scope report exceeds 256 KiB; narrow the object scope.");
                return answer;
            }
        }

        internal static string CurrentScopeState(RhinoDoc doc, Guid[] ids, bool includeBlocks)
        { using (var scope = Resolve(doc, ids.Distinct().OrderBy(id => id), includeBlocks)) return ScopeState(doc, scope, includeBlocks); }
        static string ScopeState(RhinoDoc doc, Scope scope, bool includeBlocks) => Hash(DocumentIdentity(doc) + ":" + includeBlocks + ":" +
            String.Join(";", scope.Members.OrderBy(m => m.Key, StringComparer.Ordinal).Select(m => m.Fingerprint)));

        internal static Scope Resolve(RhinoDoc doc, IEnumerable<Guid> roots, bool includeBlocks)
        {
            var scope = new Scope();
            try
            {
                foreach (Guid id in roots)
                {
                    var obj = doc.Objects.FindId(id);
                    if (obj == null || obj.IsDeleted || obj.IsInstanceDefinitionGeometry || obj.Attributes.Space != ActiveSpace.ModelSpace)
                        throw new ArgumentException("Not a current top-level model object: " + id);
                    Expand(doc, scope, obj, id, Array.Empty<Guid>(), Transform.Identity, includeBlocks, new HashSet<Guid>());
                }
                return scope;
            }
            catch { scope.Dispose(); throw; }
        }

        static void Expand(RhinoDoc doc, Scope scope, RhinoObject obj, Guid root, Guid[] path,
            Transform parent, bool includeBlocks, HashSet<Guid> definitions)
        {
            if (scope.Members.Count >= MaxLeaves) throw new ArgumentException("Block expansion exceeds 2048 occurrences; narrow the scope.");
            if (path.Length > 32) throw new ArgumentException("Block expansion exceeds 32 nested levels.");
            if (obj is InstanceObject instance && includeBlocks)
            {
                var definition = instance.InstanceDefinition;
                if (definition == null || definition.IsDeleted) throw new ArgumentException("A block definition is unavailable.");
                if (!definitions.Add(definition.Id)) throw new ArgumentException("Cyclic block definition path.");
                try
                {
                    var children = definition.GetObjects();
                    if (children == null || children.Length == 0) throw new ArgumentException("A block definition has no readable members.");
                    foreach (var child in children.OrderBy(o => o.Id))
                        Expand(doc, scope, child, root, path.Concat(new[] { child.Id }).ToArray(),
                            parent * instance.InstanceXform, true, definitions);
                }
                finally { definitions.Remove(definition.Id); }
                return;
            }
            var member = new Member { RootId = root, Path = path, Key = root.ToString("D") + "/" + String.Join("/", path) };
            scope.Members.Add(member);
            string reason = null;
            var geometry = obj.Geometry;
            member.Geometry = geometry?.Duplicate();
            if (member.Geometry == null) reason = "geometry_unavailable";
            else if (!member.Geometry.Transform(parent)) reason = "world_transform_failed";
            else if (obj is InstanceObject) reason = "block_excluded";
            else reason = Unsupported(member.Geometry);
            member.Bounds = member.Geometry?.GetBoundingBox(true) ?? BoundingBox.Empty;
            if (reason == null && !member.Bounds.IsValid) reason = "invalid_world_bounds";
            member.Supported = reason == null;
            var handle = new JObject { ["object_id"] = root.ToString("D"), ["path"] = new JArray(path.Select(id => id.ToString("D"))) };
            member.Info = new JObject {
                ["handle"] = handle, ["object_id"] = root.ToString("D"), ["member_id"] = obj.Id.ToString("D"),
                ["name"] = Short(obj.Attributes.Name ?? "", 160),
                ["layer_path"] = Short(doc.Layers.FindIndex(obj.Attributes.LayerIndex)?.FullPath ?? "", 512),
                ["object_type"] = obj.ObjectType.ToString(), ["geometry_crc"] = geometry?.DataCRC(0),
                ["world_geometry_crc"] = member.Geometry?.DataCRC(0),
                ["supported"] = member.Supported, ["reason"] = reason,
                ["bounds"] = member.Bounds.IsValid ? Box(member.Bounds) : null,
                ["from_block"] = path.Length != 0, ["is_reference"] = obj.IsReference
            };
            if (member.Geometry is Mesh mesh) member.Info["disjoint_piece_count"] = mesh.DisjointMeshCount;
            member.Fingerprint = Hash(member.Key + ":" + member.Info.ToString(Formatting.None) + ":" + parent.ToString());
            if (!member.Supported) scope.Unsupported.Add(member.Info.DeepClone());
        }

        internal static Member ResolveHandle(RhinoDoc doc, JObject handle, out Scope scope)
        {
            if (handle == null || handle["object_id"]?.Type != JTokenType.String ||
                !Guid.TryParse((string)handle["object_id"], out var root) || root == Guid.Empty)
                throw new ArgumentException("A returned occurrence handle with object_id and path is required.");
            if (handle["path"] != null && !(handle["path"] is JArray)) throw new ArgumentException("Handle path must be an array.");
            var path = handle["path"] as JArray ?? new JArray();
            if (path.Count > 32 || path.Any(v => v.Type != JTokenType.String || !Guid.TryParse((string)v, out var id) || id == Guid.Empty))
                throw new ArgumentException("Handle path must contain at most 32 member GUIDs.");
            string key = root.ToString("D") + "/" + String.Join("/", path.Values<string>().Select(s => Guid.Parse(s)));
            scope = Resolve(doc, new[] { root }, path.Count != 0);
            var found = scope.Members.SingleOrDefault(m => m.Key == key);
            if (found == null) { scope.Dispose(); scope = null; throw new ArgumentException("The block occurrence no longer exists; inspect it again."); }
            return found;
        }

        internal static string PairState(RhinoDoc doc, Member a, Member b) => Hash(DocumentIdentity(doc) + ":" +
            String.Join(":", new[] { a.Fingerprint, b.Fingerprint }.OrderBy(v => v, StringComparer.Ordinal)));

        internal static Observation Observe(RhinoDoc doc, Member a, Member b)
        {
            var value = new Observation();
            value.Report = new JObject {
                ["a_id"] = a.RootId.ToString("D"), ["b_id"] = b.RootId.ToString("D"),
                ["a"] = a.Info.DeepClone(), ["b"] = b.Info.DeepClone(),
                ["pair_id"] = Hash(String.Join(":", new[] { a.Key, b.Key }.OrderBy(v => v, StringComparer.Ordinal))).Substring(0, 24),
                ["pair_state"] = PairState(doc, a, b), ["status"] = "observed"
            };
            try
            {
                if (!a.Supported || !b.Supported)
                { value.Report["status"] = "unsupported_input"; value.Report["overlap"] = Unknown("One or both occurrence geometries are unsupported."); return value; }
                double distance = BoxDistance(a.Bounds, b.Bounds);
                value.Report["bbox_distance_lower_bound"] = distance;
                value.Report["surface_gap_status"] = "not_measured";
                if (distance > Tolerance(doc))
                    value.Report["overlap"] = new JObject { ["status"] = "zero_volume", ["volume_model_units3"] = 0.0,
                        ["method"] = "disjoint_bounding_boxes", ["boolean_intersection_performed"] = false };
                else if (!(a.Geometry is Mesh) && !(b.Geometry is Mesh))
                {
                    using (var ab = AsBrep(a.Geometry)) using (var bb = AsBrep(b.Geometry))
                    {
                        var report = SolidIntersections.IntersectDetached(ab, bb, Tolerance(doc), out var pieces);
                        if (pieces != null) value.Regions.AddRange(pieces);
                        value.Report["overlap"] = report;
                    }
                }
                else
                {
                    using (var am = AsMesh(a.Geometry, Tolerance(doc))) using (var bm = AsMesh(b.Geometry, Tolerance(doc)))
                    {
                        bool approximate = !(a.Geometry is Mesh) || !(b.Geometry is Mesh);
                        value.Report["overlap"] = MeshIntersection(am, bm, MeshTolerance(doc), value.Regions);
                        value.Report["overlap"]["approximate"] = approximate;
                        value.Report["overlap"]["meshing_tolerance"] = approximate ? new JValue(Tolerance(doc)) : JValue.CreateNull();
                    }
                }
                var regions = new JArray();
                int index = 0;
                foreach (var geometry in value.Regions)
                {
                    if (index >= 64) break;
                    using (var mass = Mass(geometry))
                    {
                        regions.Add(new JObject { ["region_index"] = index++, ["bounds"] = Box(geometry.GetBoundingBox(true)),
                            ["centroid"] = mass == null ? null : Point(mass.Centroid),
                            ["volume_model_units3"] = mass == null ? JValue.CreateNull() : new JValue(Math.Abs(mass.Volume)) });
                    }
                }
                value.Report["regions"] = regions;
                value.Report["region_count"] = value.Regions.Count;
                value.Report["regions_truncated"] = value.Regions.Count > regions.Count;
                value.Report["preview_geometry_available"] = value.Regions.Count != 0;
            }
            catch (Exception ex)
            { value.Report["status"] = "unknown"; value.Report["overlap"] = Unknown(Short(ex.Message, 320)); value.Dispose(); }
            return value;
        }

        internal static string Unsupported(GeometryBase geometry)
        {
            if (geometry == null || !geometry.IsValid) return "invalid_geometry";
            if (geometry is Brep brep)
            {
                if (!brep.IsSolid || !brep.IsManifold) return "closed_manifold_brep_required";
                return brep.SolidOrientation == BrepSolidOrientation.Outward || brep.SolidOrientation == BrepSolidOrientation.Inward
                    ? null : "unresolved_solid_orientation";
            }
            if (geometry is Extrusion extrusion) return extrusion.IsSolid ? null : "closed_extrusion_required";
            if (geometry is Mesh mesh)
            {
                if (mesh.Faces.Count > MaxMeshFaces) return "mesh_exceeds_500000_faces";
                if (!mesh.IsClosed || !mesh.IsManifold(true, out bool oriented, out bool boundary) || !oriented || boundary)
                    return "closed_oriented_manifold_mesh_required";
                return mesh.SolidOrientation() == 0 ? "unresolved_mesh_solid_orientation" : null;
            }
            return "only_brep_extrusion_mesh_supported";
        }

        internal static Brep AsBrep(GeometryBase geometry)
        {
            var result = geometry is Brep brep ? brep.DuplicateBrep() : ((Extrusion)geometry).ToBrep();
            if (result == null) throw new InvalidOperationException("Brep conversion failed.");
            if (result.SolidOrientation == BrepSolidOrientation.Inward) result.Flip();
            return result;
        }

        internal static Mesh AsMesh(GeometryBase geometry, double tolerance)
        {
            Mesh result = null;
            try
            {
                if (geometry is Mesh mesh) result = mesh.DuplicateMesh();
                else
                    using (var brep = AsBrep(geometry))
                    using (var parameters = new MeshingParameters { Tolerance = tolerance, MinimumEdgeLength = 0,
                        RefineGrid = true, SimplePlanes = true, JaggedSeams = false })
                    {
                        var pieces = Mesh.CreateFromBrep(brep, parameters);
                        if (pieces == null || pieces.Length == 0) throw new InvalidOperationException("Temporary Brep meshing failed.");
                        result = new Mesh();
                        try { foreach (var piece in pieces) { result.Append(piece); if (result.Faces.Count > MaxMeshFaces) throw new ArgumentException("Temporary mesh exceeds 500000 faces."); } }
                        finally { foreach (var piece in pieces) piece?.Dispose(); }
                    }
                if (result == null || Unsupported(result) != null) throw new InvalidOperationException("A valid closed oriented mesh is required after conversion.");
                if (result.SolidOrientation() < 0) result.Flip(true, true, true);
                return result;
            }
            catch { result?.Dispose(); throw; }
        }

        static JObject MeshIntersection(Mesh a, Mesh b, double tolerance, List<GeometryBase> regions)
        {
            Mesh[] pieces = null;
            try
            {
                pieces = Mesh.CreateBooleanIntersection(new[] { a }, new[] { b },
                    new MeshBooleanOptions { Tolerance = tolerance }, out var result);
                if (result != Rhino.Commands.Result.Success || pieces == null || pieces.Length == 0)
                    return Unknown("Mesh BooleanIntersection did not return a confirmed nonempty result: " + result + ".");
                double volume = 0, uncertainty = 0;
                foreach (var piece in pieces)
                {
                    if (Unsupported(piece) != null) return Unknown("Mesh intersection returned invalid/open/unoriented geometry.");
                    using (var mass = VolumeMassProperties.Compute(piece))
                    {
                        if (mass == null || !Finite(mass.Volume) || !Finite(mass.VolumeError)) return Unknown("Mesh intersection volume is unavailable.");
                        volume += Math.Abs(mass.Volume); uncertainty += Math.Abs(mass.VolumeError);
                    }
                }
                if (!Finite(volume) || !Finite(uncertainty) || volume <= uncertainty)
                    return Unknown("Mesh volume does not establish positive overlap above numeric uncertainty.");
                // Keep disconnected output pieces together as returned by the kernel. Splitting nested
                // shells into independent solids would incorrectly fill cavities.
                regions.AddRange(pieces); pieces = null;
                return new JObject { ["status"] = "positive_volume", ["volume_model_units3"] = volume,
                    ["numeric_uncertainty_model_units3"] = uncertainty, ["method"] = "mesh_boolean_intersection",
                    ["boolean_intersection_performed"] = true, ["mesh_boolean_tolerance"] = tolerance,
                    ["result_count"] = regions.Count };
            }
            finally { if (pieces != null) foreach (var piece in pieces) piece?.Dispose(); }
        }

        internal static VolumeMassProperties Mass(GeometryBase geometry) => geometry is Mesh mesh
            ? VolumeMassProperties.Compute(mesh) : VolumeMassProperties.Compute((Brep)geometry);
        internal static JObject Unknown(string reason) => new JObject { ["status"] = "unknown", ["volume_model_units3"] = null, ["reason"] = reason };
        internal static double Tolerance(RhinoDoc doc)
        { double value = doc.ModelAbsoluteTolerance; if (!Finite(value) || value <= 0) throw new ArgumentException("Document tolerance must be finite and positive."); return value; }
        internal static double MeshTolerance(RhinoDoc doc)
        { double value = Tolerance(doc) * Rhino.Geometry.Intersect.Intersection.MeshIntersectionsTolerancesCoefficient; if (!Finite(value) || value <= 0) throw new ArgumentException("Mesh intersection tolerance must be finite and positive."); return value; }
        internal static string DocumentIdentity(RhinoDoc doc) => doc.RuntimeSerialNumber + ":" + doc.Path + ":" + doc.ModelUnitSystem + ":" +
            Tolerance(doc).ToString("R", CultureInfo.InvariantCulture) + ":" + MeshTolerance(doc).ToString("R", CultureInfo.InvariantCulture);
        internal static string Hash(string value) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-", "").ToLowerInvariant(); }
        static int DecodeCursor(string cursor, string fingerprint)
        {
            if (cursor.Length == 0) return 0;
            var parts = cursor.Split(':');
            if (parts.Length != 2 || parts[0] != fingerprint || !Int32.TryParse(parts[1], NumberStyles.None, CultureInfo.InvariantCulture, out int offset) || offset < 0)
                throw new ArgumentException("The cursor no longer matches this document, geometry or scope; start a new inspection.");
            return offset;
        }
        internal static double BoxDistance(BoundingBox a, BoundingBox b)
        { double x = Math.Max(0, Math.Max(a.Min.X - b.Max.X, b.Min.X - a.Max.X)); double y = Math.Max(0, Math.Max(a.Min.Y - b.Max.Y, b.Min.Y - a.Max.Y)); double z = Math.Max(0, Math.Max(a.Min.Z - b.Max.Z, b.Min.Z - a.Max.Z)); return Math.Sqrt(x * x + y * y + z * z); }
        internal static JArray Box(BoundingBox box) => new JArray(Point(box.Min), Point(box.Max));
        internal static JArray Point(Point3d p) => new JArray(p.X, p.Y, p.Z);
        internal static string Short(string value, int length) => value.Length <= length ? value : value.Substring(0, length);
        internal static bool Finite(double value) => !Double.IsNaN(value) && !Double.IsInfinity(value);
    }
}
