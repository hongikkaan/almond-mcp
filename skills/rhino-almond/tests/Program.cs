using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Newtonsoft.Json.Linq;

internal static class Program
{
    static readonly string RhinoSystem = Environment.GetEnvironmentVariable("RHINO_SYSTEM_DIR")
        ?? @"C:\Program Files\Rhino 8\System";
    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length < 2) throw new ArgumentException("mode report_path [manifest_path]");
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
    static string Run(string mode, string reportPath, string manifestPath)
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
                    var id = doc.Objects.AddBrep(box, new Rhino.DocObjects.ObjectAttributes { Name = "probe cube" });
                    Guid otherId;
                    using (var other = new Rhino.Geometry.BoundingBox(5, 0, 0, 15, 10, 10).ToBrep())
                        otherId = doc.Objects.AddBrep(other, new Rhino.DocObjects.ObjectAttributes { Name = "overlap cube" });
                    int definition = doc.InstanceDefinitions.Add("probe-block", "isolated fixture", Rhino.Geometry.Point3d.Origin,
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
                var type = typeof(Program).Assembly.GetType("NativeTests", true);
                return (string)type.GetMethod("RunAll", BindingFlags.Public | BindingFlags.Static).Invoke(null, null);
            }
            if (mode == "script") {
                var manifest = JObject.Parse(File.ReadAllText(manifestPath));
                string source = File.ReadAllText((string)manifest["script_path"]);
                using (var doc = Rhino.RhinoDoc.OpenHeadless((string)manifest["model_path"])) {
                    if (doc == null) throw new Exception("Could not open isolated fixture.");
                    var before = doc.Objects.Select(o => o.Id.ToString() + ":" + o.Geometry.DataCRC(0)).OrderBy(x => x).ToArray();
                    var tree = CSharpSyntaxTree.ParseText(source);
                    var refs = AppDomain.CurrentDomain.GetAssemblies()
                        .Where(a => !a.IsDynamic && !String.IsNullOrEmpty(a.Location))
                        .Select(a => a.Location).Distinct()
                        .Select(p => MetadataReference.CreateFromFile(p)).ToList();
                    var compilation = CSharpCompilation.Create("Probe_" + Guid.NewGuid().ToString("N"),
                        new[] { tree }, refs, new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
                    using (var stream = new MemoryStream()) {
                        var emitted = compilation.Emit(stream);
                        if (!emitted.Success) throw new Exception(String.Join("\n", emitted.Diagnostics
                            .Where(x => x.Severity == DiagnosticSeverity.Error).Select(x => x.ToString())));
                        var assembly = Assembly.Load(stream.ToArray());
                        var returned = assembly.GetType("Script", true).GetMethod("Run").Invoke(null, new object[] { doc }) as List<Guid>;
                        if (returned == null || returned.Count != 0) throw new Exception("Query returned created geometry.");
                    }
                    var after = doc.Objects.Select(o => o.Id.ToString() + ":" + o.Geometry.DataCRC(0)).OrderBy(x => x).ToArray();
                    if (!before.SequenceEqual(after)) throw new Exception("Query changed document geometry.");
                    return new JObject { ["status"] = "ok", ["compiled_and_executed"] = true,
                        ["geometry_unchanged"] = true, ["helper_result"] = JObject.Parse(File.ReadAllText((string)manifest["result_path"])) }.ToString();
                }
            }
            throw new ArgumentException("Unknown mode.");
        }
    }
}
