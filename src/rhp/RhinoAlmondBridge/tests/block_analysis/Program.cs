using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using Newtonsoft.Json.Linq;

internal static class Program
{
    static readonly string RhinoSystem = Environment.GetEnvironmentVariable("RHINO_SYSTEM_DIR")
        ?? @"C:\Program Files\Rhino 8\System";
    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length < 2) throw new ArgumentException("mode report_path [request_path]");
        string reportPath = Path.GetFullPath(args[1]);
        if (File.Exists(reportPath)) throw new ArgumentException("Report must be new.");
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) => {
            var file = Path.Combine(RhinoSystem, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(file) ? Assembly.LoadFrom(file) : null;
        };
        try {
            string report = Run(args[0], reportPath, args.Length > 2 ? args[2] : null);
            File.WriteAllText(reportPath, report, new System.Text.UTF8Encoding(false));
            Console.WriteLine(report);
            return 0;
        } catch (Exception ex) {
            File.WriteAllText(reportPath, ex.ToString(), new System.Text.UTF8Encoding(false));
            Console.Error.WriteLine(ex);
            return 1;
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    static string Run(string mode, string reportPath, string requestPath)
    {
        using (var core = new Rhino.Runtime.InProcess.RhinoCore(
            new[] { "/NOSPLASH", "/NOTEMPLATE" }, Rhino.Runtime.InProcess.WindowStyle.NoWindow))
        {
            if (mode == "smoke") {
                using (var doc = Rhino.RhinoDoc.CreateHeadless(null))
                using (var box = new Rhino.Geometry.BoundingBox(0, 0, 0, 10, 10, 10).ToBrep())
                using (var volume = Rhino.Geometry.VolumeMassProperties.Compute(box)) {
                    if (volume == null || Math.Abs(volume.Volume - 1000) > 0.000001)
                        throw new Exception("Native box volume is incorrect.");
                    doc.AdjustModelUnitSystem(Rhino.UnitSystem.Millimeters, false);
                    doc.ModelAbsoluteTolerance = 0.001;
                    var id = doc.Objects.AddBrep(box, new Rhino.DocObjects.ObjectAttributes { Name = "analysis cube" });
                    Guid otherId;
                    using (var other = new Rhino.Geometry.BoundingBox(5, 0, 0, 15, 10, 10).ToBrep())
                        otherId = doc.Objects.AddBrep(other, new Rhino.DocObjects.ObjectAttributes { Name = "overlap cube" });
                    int definition = doc.InstanceDefinitions.Add("analysis-block", "isolated fixture", Rhino.Geometry.Point3d.Origin,
                        new Rhino.Geometry.GeometryBase[] { box }, new[] { new Rhino.DocObjects.ObjectAttributes { Name = "block cube" } });
                    if (definition < 0) throw new Exception("Could not create fixture block.");
                    var blockId = doc.Objects.AddInstanceObject(definition, Rhino.Geometry.Transform.Translation(30, 0, 0));
                    string model = Path.Combine(Path.GetDirectoryName(reportPath), "fixture-" + Guid.NewGuid().ToString("N") + ".3dm");
                    if (!doc.WriteFile(model, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }))
                        throw new Exception("Could not write isolated fixture.");
                    return new JObject { ["status"] = "ok", ["rhino"] = Rhino.RhinoApp.Version.ToString(),
                        ["volume"] = volume.Volume, ["model_path"] = model, ["cube_id"] = id.ToString(),
                        ["other_id"] = otherId.ToString(), ["block_id"] = blockId.ToString(),
                        ["artifact_dir"] = Path.GetDirectoryName(reportPath) }.ToString();
                }
            }
            if (mode == "tests") {
                var type = typeof(Program).Assembly.GetType("IntersectionTests", true);
                return (string)type.GetMethod("RunAll", BindingFlags.Public | BindingFlags.Static).Invoke(null, null);
            }
            if (mode == "analysis") {
                var request = JObject.Parse(File.ReadAllText(requestPath));
                using (var doc = Rhino.RhinoDoc.OpenHeadless((string)request["expected_model_path"])) {
                    if (doc == null) throw new Exception("Could not open isolated fixture.");
                    if (new[] { "A-WALL", "A-STRC", "A-GLAZ" }.Any(name => doc.Layers.FindName(name) != null))
                        throw new Exception("Fixture already contains executor-created layers.");
                    doc.UndoRecordingEnabled = true;
                    doc.Modified = false;
                    var before = Snapshot(doc);
                    var result = RhinoAlmondBridge.BlockAnalysis.Analyze(doc, request);
                    if (!JToken.DeepEquals(before, Snapshot(doc))) throw new Exception("Analysis changed document state.");
                    var wrongDocument = (JObject)request.DeepClone();
                    wrongDocument["expected_model_path"] = Path.Combine(Path.GetDirectoryName(doc.Path), "wrong.3dm");
                    if ((string)RhinoAlmondBridge.BlockAnalysis.Analyze(doc, wrongDocument)["error_code"] != "document_mismatch")
                        throw new Exception("Analysis accepted a different document.");
                    var invalid = (JObject)request.DeepClone();
                    invalid["mode"] = "execute";
                    invalid["script"] = "doc.Objects.Clear();";
                    if ((string)RhinoAlmondBridge.BlockAnalysis.Analyze(doc, invalid)["error_code"] != "invalid_arguments")
                        throw new Exception("Analysis accepted an arbitrary execution request.");
                    if (!JToken.DeepEquals(before, Snapshot(doc))) throw new Exception("Rejected analysis changed document state.");
                    return new JObject { ["status"] = "ok", ["document_unchanged"] = true,
                        ["invalid_requests_rejected"] = true, ["analysis_result"] = result }.ToString();
                }
            }
            throw new ArgumentException("Unknown mode.");
        }
    }

    static JObject Snapshot(Rhino.RhinoDoc doc)
    {
        return new JObject {
            ["modified"] = doc.Modified,
            ["undo_enabled"] = doc.UndoRecordingEnabled,
            ["recording"] = doc.UndoRecordingIsActive,
            ["current_record"] = doc.CurrentUndoRecordSerialNumber,
            ["next_record"] = doc.NextUndoRecordSerialNumber,
            ["layers"] = new JArray(doc.Layers.OrderBy(l => l.Id).Select(l => new JObject {
                ["id"] = l.Id.ToString(), ["index"] = l.Index, ["crc"] = l.DataCRC(0), ["deleted"] = l.IsDeleted })),
            ["objects"] = new JArray(doc.Objects.OrderBy(o => o.Id).Select(o => new JObject {
                ["id"] = o.Id.ToString(), ["crc"] = o.Geometry.DataCRC(0), ["selected"] = o.IsSelected(false),
                ["attributes"] = o.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions { WriteUserData = true }) }))
        };
    }
}
