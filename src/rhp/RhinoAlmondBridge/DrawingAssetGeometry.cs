using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.FileIO;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    /// <summary>Read a prepared 3DM without importing or changing the active document.</summary>
    public static class DrawingAssetGeometry
    {
        private const int MaxTriangles = 250000;
        private const long MaxSourceBytes = 100000000;

        public static JObject Handle(JObject request)
        {
            string output = null;
            bool created = false;
            try
            {
                string source = AbsoluteFile(request, "source_path", ".3dm");
                output = AbsoluteFile(request, "output_path", ".json");
                if (!File.Exists(source) || new FileInfo(source).Length > MaxSourceBytes)
                    throw new ArgumentException("Use an existing 3DM of at most 100 MB.");
                if (File.Exists(output) || !Directory.Exists(Path.GetDirectoryName(output)))
                    throw new ArgumentException("output_path must be a new file in an existing artifact directory.");
                string sourceHash = Hash(source);
                var triangles = new List<Point3d[]>();
                BoundingBox bounds = BoundingBox.Empty;
                using (var model = File3dm.Read(source))
                {
                    if (model == null) throw new ArgumentException("Rhino could not read the 3DM.");
                    if (model.Settings.ModelUnitSystem != UnitSystem.Millimeters)
                        throw new ArgumentException("Prepare the drawing asset in millimetres before registration.");
                    var objects = model.Objects.ToDictionary(obj => obj.Id);
                    var definitions = model.AllInstanceDefinitions.ToDictionary(definition => definition.Id);
                    int occurrences = 0;

                    void AddTriangle(Point3d a, Point3d b, Point3d c)
                    {
                        if (triangles.Count >= MaxTriangles)
                            throw new ArgumentException("Asset exceeds the 250,000 derived triangle limit; simplify the source first.");
                        foreach (var point in new[] { a, b, c })
                        {
                            if (!point.IsValid || Math.Abs(point.X) > 1e9 || Math.Abs(point.Y) > 1e9 || Math.Abs(point.Z) > 1e9)
                                throw new ArgumentException("Asset coordinates must be finite millimetres within +/-1e9.");
                            bounds.Union(point);
                        }
                        triangles.Add(new[] { a, b, c });
                    }

                    void Append(Mesh mesh, Transform world)
                    {
                        if (mesh == null || !mesh.IsValid || mesh.Faces.Count == 0)
                            throw new ArgumentException("A source object could not produce valid mesh geometry.");
                        Point3d Vertex(int index)
                        {
                            Point3d point = mesh.Vertices.Point3dAt(index);
                            point.Transform(world);
                            return point;
                        }
                        foreach (var face in mesh.Faces)
                        {
                            AddTriangle(Vertex(face.A), Vertex(face.B), Vertex(face.C));
                            if (face.IsQuad) AddTriangle(Vertex(face.A), Vertex(face.C), Vertex(face.D));
                        }
                    }

                    void BrepMeshes(Brep brep, Transform world)
                    {
                        var meshes = Mesh.CreateFromBrep(brep, MeshingParameters.Default);
                        if (meshes == null || meshes.Length == 0)
                            throw new ArgumentException("A source Brep could not be meshed.");
                        try { foreach (var mesh in meshes) Append(mesh, world); }
                        finally { foreach (var mesh in meshes) mesh?.Dispose(); }
                    }

                    void Visit(File3dmObject item, Transform world, HashSet<Guid> ancestors)
                    {
                        if (++occurrences > 10000 || ancestors.Count > 64)
                            throw new ArgumentException("Asset has too many objects or nested block levels.");
                        if (item.Attributes.Space != ActiveSpace.ModelSpace)
                            throw new ArgumentException("Prepare a model-space-only asset; Layout geometry is not a 3D drawing asset.");
                        var geometry = item.Geometry;
                        if (geometry == null || !geometry.IsValid)
                            throw new ArgumentException("Source asset contains invalid geometry: " + item.Id);
                        if (geometry is InstanceReferenceGeometry instance)
                        {
                            if (!ancestors.Add(instance.ParentIdefId) || !definitions.TryGetValue(instance.ParentIdefId, out var definition))
                                throw new ArgumentException("Asset has a missing or cyclic block definition.");
                            Transform transform = world * instance.Xform;
                            if (!transform.IsValid || !transform.IsAffine)
                                throw new ArgumentException("Asset block has an invalid transform.");
                            foreach (Guid id in definition.GetObjectIds())
                            {
                                if (!objects.TryGetValue(id, out File3dmObject child))
                                    throw new ArgumentException("Block definition geometry is missing: " + id);
                                Visit(child, transform, ancestors);
                            }
                            ancestors.Remove(instance.ParentIdefId);
                        }
                        else if (geometry is Mesh mesh) Append(mesh, world);
                        else if (geometry is Brep brep) BrepMeshes(brep, world);
                        else if (geometry is Extrusion extrusion)
                        {
                            using (var converted = extrusion.ToBrep()) BrepMeshes(converted, world);
                        }
                        else if (geometry is SubD subd)
                        {
                            using (var limitMesh = Mesh.CreateFromSubD(subd, 3)) Append(limitMesh, world);
                        }
                        else if (geometry is Surface surface)
                        {
                            using (var converted = surface.ToBrep()) BrepMeshes(converted, world);
                        }
                        else throw new ArgumentException("Unsupported 3DM geometry " + geometry.ObjectType + ": " + item.Id +
                            "; prepare a mesh, surface, solid or block asset before registration.");
                    }

                    foreach (var item in model.Objects.Where(item => !item.Attributes.IsInstanceDefinitionObject))
                        Visit(item, Transform.Identity, new HashSet<Guid>());
                }
                if (triangles.Count == 0 || !bounds.IsValid)
                    throw new ArgumentException("The asset contains no model-space triangle geometry.");
                if (Math.Abs((bounds.Min.X + bounds.Max.X) / 2) > 0.01 ||
                    Math.Abs((bounds.Min.Y + bounds.Max.Y) / 2) > 0.01 || Math.Abs(bounds.Min.Z) > 0.01)
                    throw new ArgumentException("Prepare the asset with its bounding-box bottom centre at the origin before registration.");
                if (Hash(source) != sourceHash)
                    throw new IOException("The source 3DM changed during extraction; registration was not published.");
                var metadata = new JObject {
                    ["schema"] = "almond-triangles/v1", ["units"] = "mm", ["up_axis"] = "z", ["origin"] = "bottom_center",
                    ["source_sha256"] = sourceHash, ["triangle_count"] = triangles.Count,
                    ["bounds_mm"] = new JArray(bounds.Min.X, bounds.Min.Y, bounds.Min.Z, bounds.Max.X, bounds.Max.Y, bounds.Max.Z)
                };
                using (var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    created = true;
                    using (var writer = new JsonTextWriter(new StreamWriter(stream, new UTF8Encoding(false))))
                    {
                        writer.WriteStartObject();
                        foreach (var property in metadata.Properties()) property.WriteTo(writer);
                        writer.WritePropertyName("triangles_mm");
                        writer.WriteStartArray();
                        foreach (var triangle in triangles)
                        {
                            writer.WriteStartArray();
                            foreach (var point in triangle)
                            {
                                writer.WriteStartArray();
                                writer.WriteValue(point.X); writer.WriteValue(point.Y); writer.WriteValue(point.Z);
                                writer.WriteEndArray();
                            }
                            writer.WriteEndArray();
                        }
                        writer.WriteEndArray(); writer.WriteEndObject();
                    }
                }
                metadata["status"] = "success";
                metadata["complete"] = true;
                metadata["source_path"] = source;
                metadata["output_path"] = output;
                metadata["triangles_sha256"] = Hash(output);
                return metadata;
            }
            catch (Exception error)
            {
                if (created && output != null && File.Exists(output)) File.Delete(output);
                return new JObject { ["status"] = "error", ["error_code"] = "drawing_asset_extract_error",
                    ["message"] = error.Message, ["mutation_applied"] = false };
            }
        }

        private static string AbsoluteFile(JObject request, string field, string extension)
        {
            if (request?[field]?.Type != JTokenType.String || !Path.IsPathRooted((string)request[field]))
                throw new ArgumentException(field + " must be an absolute path.");
            string path = Path.GetFullPath((string)request[field]);
            if (!String.Equals(Path.GetExtension(path), extension, StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException(field + " must end in " + extension);
            return path;
        }

        private static string Hash(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var algorithm = SHA256.Create())
                return BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "");
        }
    }
}
