// Exercises the production adapter against API doubles, never a Rhino process/document.
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using RhinoAlmondBridge;

class Program
{
    static readonly Guid Id = Guid.Parse("00000000-0000-0000-0000-000000000001");
    static int checks;
    static void Check(bool value, string message) { if (!value) throw new Exception(message); checks++; }
    static JObject Request() => JObject.Parse(@"{
        'type':'plan_section','operation':'Create','clipping_ids':['00000000-0000-0000-0000-000000000001'],
        'points':{},'hatch':true,'elevation':true,'small_details':true,
        'near_width':0.09,'far_width':0.04,'near_dark':80,'far_dark':45,
        'expected_model_path':'C:\\offline\\model.3dm'}");
    static Rhino.RhinoDoc Doc() => Rhino.RhinoDoc.ActiveDoc = new Rhino.RhinoDoc { Path = @"C:\offline\model.3dm", Objects = new Rhino.ObjectTable(Id) };
    static JObject Run(JObject request = null)
    {
        ScriptExecutor.Calls = 0;
        return PlanSectionTool.Handle(Doc(), request ?? Request());
    }
    static void Main()
    {
        Rhino.Runtime.PythonScript.Reset();
        var good = Run();
        Check((string)good["status"] == "success" && (string)good["mutation_state"] == "completed", "completed status: " + good);
        var python = Rhino.Runtime.PythonScript.Last;
        Check(ScriptExecutor.Calls == 1 && python.Invocations == 1, "single native Undo-owned invocation");
        Check(python.Variables.Count == 1 && (string)python.Variables["__name__"] == "original", "namespace restored");
        Check(ReferenceEquals(python.ScriptContextDoc, python.OriginalDoc) && python.Output == python.OriginalOutput, "context restored");
        Check(((string)good["result"]["algorithm_sha256"]).Length == 64, "source fingerprint");
        Check((string)good["result"]["output"] == "Document", "document output only");
        Check(python.LoadedSource.StartsWith("__name__ = 'almond_plansection_internal'\n"), "interactive main disabled");
        Check(python.LoadedSource.Contains("def run(doc, operation, clipping_ids"), "packaged algorithm shared");

        foreach (var field in new[] { "script", "folder", "output", "language", "project_root", "artifact_dir" })
        {
            var request = Request(); request[field] = "caller input";
            var result = Run(request);
            Check((string)result["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0, "reject unexpected " + field);
        }
        foreach (var change in new Action<JObject>[] {
            r => r["operation"] = "PDF", r => r["hatch"] = 1, r => r["near_width"] = 0,
            r => r["clipping_ids"] = new JArray(Guid.Empty.ToString()),
            r => r["clipping_ids"] = new JArray(Guid.NewGuid().ToString()),
            r => r["expected_model_path"] = @"C:\other.3dm",
            r => r["points"] = JObject.Parse("{'00000000-0000-0000-0000-000000000001':[true,0]}") })
        {
            var request = Request(); change(request); var result = Run(request);
            Check((string)result["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0, "invalid request before Undo");
        }
        Rhino.Runtime.PythonScript.Unavailable = true;
        Check((string)Run()["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0, "missing runtime before mutation");
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.FailLoad = true;
        Check((string)Run()["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0, "load failure before mutation");
        Check(Rhino.Runtime.PythonScript.Last.Variables.Count == 1, "load failure namespace restored");
        var loadError = Run();
        Check(((string)loadError["python_diagnostic"]).Length == 8192 && (bool)loadError["python_diagnostic_truncated"] &&
            ((string)loadError["python_diagnostic"]).EndsWith("import failure"), "bounded load failure diagnostic retains late failure");
        Check(good["python_diagnostic"] == null, "successful progress output omitted");
        Rhino.Runtime.PythonScript.Reset();
        foreach (string state in new[] { "partial", "cancelled" })
        {
            Rhino.Runtime.PythonScript.DrawingStatus = state;
            var result = Run();
            Check((string)result["drawing_status"] == state && (string)result["mutation_state"] == "partial", "partial evidence " + state);
        }
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.FailInvoke = true;
        Check((string)Run()["mutation_state"] == "unknown", "execution failure remains uncertain");
        Check(Rhino.Runtime.PythonScript.Last.Variables.Count == 1, "failure cleanup");
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.FailRemove = true;
        var cleanup = Run(); python = Rhino.Runtime.PythonScript.Last;
        Check((string)cleanup["error_code"] == "plan_section_context_restore_failed", "cleanup diagnostic");
        Check(ReferenceEquals(python.ScriptContextDoc, python.OriginalDoc) && python.Output == python.OriginalOutput, "remove failure does not skip doc/output restoration");
        Check(cleanup["result"] != null && cleanup["context_restore_errors"] is JArray, "retain drawing result on cleanup failure");
        Console.WriteLine(new JObject { ["passed"] = checks, ["native_geometry_tested"] = false }.ToString());
    }
}

namespace Rhino
{
    public class RhinoDoc { public static RhinoDoc ActiveDoc; public uint RuntimeSerialNumber = 1; public string Path; public bool IsReadOnly; public ObjectTable Objects; }
    public class ObjectTable
    {
        readonly Guid id;
        public ObjectTable(Guid id) { this.id = id; }
        public DocObjects.RhinoObject FindId(Guid value) => value == id ? new DocObjects.ClippingPlaneObject() : null;
    }
}
namespace Rhino.DocObjects
{
    public class ObjectAttributes { public bool IsInstanceDefinitionObject; }
    public class RhinoObject { public bool IsDeleted; public ObjectAttributes Attributes = new ObjectAttributes(); }
    public class ClippingPlaneObject : RhinoObject { }
}
namespace Rhino.Runtime
{
    public class PythonScript
    {
        public static PythonScript Last;
        public static bool Unavailable, FailLoad, FailInvoke, FailRemove;
        public static string DrawingStatus = "completed";
        public readonly object OriginalDoc = new object();
        public readonly Action<string> OriginalOutput = text => { };
        public Dictionary<string, object> Variables = new Dictionary<string, object> { ["__name__"] = "original" };
        public object ScriptContextDoc { get; set; }
        public Action<string> Output { get; set; }
        public string LoadedSource;
        public int Invocations;
        public static void Reset() { Unavailable = FailLoad = FailInvoke = FailRemove = false; DrawingStatus = "completed"; }
        public static PythonScript Create()
        {
            if (Unavailable) return null;
            Last = new PythonScript(); Last.ScriptContextDoc = Last.OriginalDoc; Last.Output = Last.OriginalOutput; return Last;
        }
        public IEnumerable<string> GetVariableNames() => Variables.Keys.ToArray();
        public object GetVariable(string name) => Variables[name];
        public void SetVariable(string name, object value) { Variables[name] = value; }
        public void RemoveVariable(string name)
        {
            if (FailRemove && name == "_almond_doc") throw new Exception("remove failed");
            Variables.Remove(name);
        }
        public bool ExecuteScript(string source)
        {
            if (source.StartsWith("__name__"))
            {
                LoadedSource = source; Variables["__name__"] = "almond_plansection_internal";
                Variables["run"] = new object();
                Output?.Invoke(FailLoad ? new string('x', 9000) + "import failure" : "loaded");
                return !FailLoad;
            }
            Invocations++;
            if (FailInvoke) throw new Exception("native drawing failed");
            var args = JObject.Parse((string)Variables["_almond_arguments_json"]);
            Variables["_almond_result_json"] = new JObject {
                ["status"] = DrawingStatus, ["requested"] = 1, ["completed"] = DrawingStatus == "completed" ? 1 : 0,
                ["results"] = new JArray(new JObject { ["clipping_id"] = args["clipping_ids"][0].DeepClone(),
                    ["status"] = DrawingStatus == "completed" ? "completed" : "cancelled" }) }.ToString();
            return true;
        }
    }
}
namespace RhinoAlmondBridge
{
    public static class EditingContext
    {
        public static JObject Observe(Rhino.RhinoDoc doc) => new JObject { ["stable"] = true, ["mode"] = "model" };
    }
    public class ScriptExecutor
    {
        public static int Calls;
        internal object ExecuteAction(Rhino.RhinoDoc doc, Func<object> action)
        {
            Calls++;
            try { return new JObject { ["status"] = "success", ["result"] = JToken.FromObject(action()) }; }
            catch (Exception error) { return new JObject { ["status"] = "error", ["message"] = error.Message }; }
        }
    }
}
