using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    public static class DrawingAssetGeometryTests
    {
        public static string RunAll(string directory)
        {
            var results = new List<string>();
            Run(results, directory, "prepared 3DM derives bounded triangles and preserves source and active document", doc =>
                doc.Objects.AddBrep(new BoundingBox(-5, -10, 0, 5, 10, 30).ToBrep()), (source, output) =>
            {
                string beforeHash = Hash(source);
                var active = RhinoDoc.ActiveDoc;
                uint serial = active?.RuntimeSerialNumber ?? 0;
                int count = active?.Objects.Count ?? 0;
                bool modified = active?.Modified ?? false;
                var reply = Success(Extract(source, output));
                var file = JObject.Parse(File.ReadAllText(output));
                Check((string)reply["source_sha256"] == beforeHash && Hash(source) == beforeHash, "Source changed.");
                Check((string)reply["triangles_sha256"] == Hash(output), "Artifact hash differs.");
                Check((int)reply["triangle_count"] == ((JArray)file["triangles_mm"]).Count && (int)reply["triangle_count"] > 0,
                    "Triangle count differs.");
                Check(JToken.DeepEquals(reply["bounds_mm"], new JArray(-5.0, -10.0, 0.0, 5.0, 10.0, 30.0)), "Unexpected bounds.");
                Check((string)file["units"] == "mm" && (string)file["up_axis"] == "z", "Coordinate declaration differs.");
                Check((RhinoDoc.ActiveDoc?.RuntimeSerialNumber ?? 0) == serial &&
                    (active?.Objects.Count ?? 0) == count && (active?.Modified ?? false) == modified,
                    "Extraction changed the active document.");
            });
            Run(results, directory, "nested block occurrences expand in world coordinates exactly once", doc =>
            {
                int leaf = doc.InstanceDefinitions.Add("leaf", "", Point3d.Origin,
                    new GeometryBase[] { new BoundingBox(-5, -5, 0, 5, 5, 10).ToBrep() }, new[] { new ObjectAttributes() });
                var inner = new InstanceReferenceGeometry(doc.InstanceDefinitions[leaf].Id, Transform.Translation(15, 0, 0));
                int outer = doc.InstanceDefinitions.Add("outer", "", Point3d.Origin,
                    new GeometryBase[] { inner }, new[] { new ObjectAttributes() });
                doc.Objects.AddInstanceObject(outer, Transform.Translation(-30, 0, 0));
                doc.Objects.AddInstanceObject(outer, Transform.Identity);
            }, (source, output) =>
            {
                var reply = Success(Extract(source, output));
                Check(JToken.DeepEquals(reply["bounds_mm"], new JArray(-20.0, -5.0, 0.0, 20.0, 5.0, 10.0)), "Nested transform was lost.");
                var triangles = (JArray)JObject.Parse(File.ReadAllText(output))["triangles_mm"];
                foreach (var point in triangles.SelectMany(t => t.Children()))
                    Check((double)point[0] <= -10 || (double)point[0] >= 10, "Definition geometry was emitted at its unplaced origin.");
            });
            Run(results, directory, "source units remain unchanged while extracted coordinates use millimetres", doc =>
            {
                doc.AdjustModelUnitSystem(UnitSystem.Meters, false);
                doc.Objects.AddBrep(new BoundingBox(-5, -5, 0, 5, 5, 10).ToBrep());
            }, (source, output) =>
            {
                string before = Hash(source);
                var reply = Success(Extract(source, output));
                Check((string)reply["source_units"] == "Meters" && (string)reply["units"] == "mm", "Source and measurement units were conflated.");
                Check(JToken.DeepEquals(reply["bounds_mm"], new JArray(-5000.0, -5000.0, 0.0, 5000.0, 5000.0, 10000.0)), "Source unit scale was lost.");
                Check(Hash(source) == before, "Measuring in mm changed the source file.");
            });
            Run(results, directory, "source origin is preserved without recentering", doc =>
                doc.Objects.AddBrep(new BoundingBox(0, 0, 1, 10, 10, 11).ToBrep()),
                (source, output) =>
                {
                    string before = Hash(source);
                    var reply = Success(Extract(source, output));
                    Check((string)reply["origin"] == "preserved" &&
                        JToken.DeepEquals(reply["bounds_mm"], new JArray(0.0, 0.0, 1.0, 10.0, 10.0, 11.0)), "Origin was reinterpreted.");
                    Check(Hash(source) == before, "Source origin changed.");
                });
            Run(results, directory, "unmeasurable unit system is rejected", doc =>
            {
                doc.AdjustModelUnitSystem(UnitSystem.None, false);
                doc.Objects.AddBrep(new BoundingBox(-5, -5, 0, 5, 5, 10).ToBrep());
            },
                (source, output) => Rejected(source, output));
            Run(results, directory, "unsupported source geometry does not publish a partial asset", doc =>
            {
                doc.Objects.AddBrep(new BoundingBox(-5, -5, 0, 5, 5, 10).ToBrep());
                doc.Objects.AddLine(Point3d.Origin, new Point3d(1, 0, 0));
            }, (source, output) => Rejected(source, output));
            Run(results, directory, "existing artifact cannot be overwritten", doc =>
                doc.Objects.AddBrep(new BoundingBox(-5, -5, 0, 5, 5, 10).ToBrep()), (source, output) =>
            {
                File.WriteAllText(output, "keep");
                Check((string)Extract(source, output)["status"] == "error" && File.ReadAllText(output) == "keep", "Existing output was overwritten.");
            });
            Run(results, directory, "nested external dependencies are reported without partial publication", doc =>
                doc.Objects.AddBrep(new BoundingBox(-5, -5, 0, 5, 5, 10).ToBrep()), (source, output) =>
            {
                string linkedSource = Path.ChangeExtension(source, ".linked.3dm");
                using (var model = Rhino.FileIO.File3dm.Read(source))
                {
                    int nested = model.AllInstanceDefinitions.AddLinked(source, "external dependency", "");
                    Check(nested >= 0 && model.Objects.AddInstanceObject(nested, Transform.Identity) != Guid.Empty, "Dependency fixture creation failed.");
                    Check(model.Write(linkedSource, 8), "Dependency fixture save failed.");
                }
                var reply = Extract(linkedSource, output);
                Check((string)reply["status"] == "error" && (bool?)reply["needs_dependency_support"] == true && !File.Exists(output),
                    "A source-dependent block was published as self-contained geometry.");
            });
            string report = String.Join("\n", results);
            if (results.Any(line => line.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + results.Count + "/" + results.Count + " drawing asset geometry cases.";
        }

        private static void Run(List<string> results, string directory, string name,
            Action<RhinoDoc> prepare, Action<string, string> test)
        {
            try
            {
                string source = Path.Combine(directory, "asset-" + Guid.NewGuid().ToString("N") + ".3dm");
                string output = Path.ChangeExtension(source, ".json");
                using (var doc = RhinoDoc.CreateHeadless(null))
                {
                    doc.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
                    prepare(doc);
                    Check(doc.WriteFile(source, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Fixture save failed.");
                }
                test(source, output);
                results.Add("PASS " + name);
            }
            catch (Exception error) { results.Add("FAIL " + name + ": " + error); }
        }
        private static JObject Extract(string source, string output) => DrawingAssetGeometry.Handle(new JObject {
            ["source_path"] = source, ["output_path"] = output });
        private static JObject Success(JObject value) { Check((string)value["status"] == "success", value.ToString()); return value; }
        private static void Rejected(string source, string output)
        {
            var result = Extract(source, output);
            Check((string)result["status"] == "error" && (bool?)result["mutation_applied"] == false && !File.Exists(output), result.ToString());
        }
        private static string Hash(string path)
        {
            using (var input = File.OpenRead(path))
            using (var algorithm = SHA256.Create()) return BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "");
        }
        private static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
