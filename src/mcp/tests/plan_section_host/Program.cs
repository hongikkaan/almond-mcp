// Exercises the production adapter against API doubles, never a Rhino process/document.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using RhinoAlmondBridge;

class Program
{
    static readonly Guid Id = Guid.Parse("00000000-0000-0000-0000-000000000001");
    static int checks;
    static void Check(bool value, string message) { if (!value) throw new Exception(message); checks++; }
    static JObject Request() => JObject.Parse(@"{
        'type':'plan_section','operation':'Create','clipping_ids':['00000000-0000-0000-0000-000000000001'],
        'points':{},'hatch':true,'small_details':false,
        'near_width':0.09,'far_width':0.04,'near_dark':80,'far_dark':45,
        'expected_model_path':'C:\\offline\\model.3dm'}");
    static Rhino.RhinoDoc Doc() => Rhino.RhinoDoc.ActiveDoc = new Rhino.RhinoDoc { Path = @"C:\offline\model.3dm", Objects = new Rhino.ObjectTable(Id) };
    static JObject Run(JObject request = null)
    {
        ScriptExecutor.Calls = 0;
        return PlanSectionTool.Handle(Doc(), request ?? Request());
    }
    static int Main(string[] args)
    {
        try
        {
            Verify(args);
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error);
            return 1;
        }
    }

    static void Verify(string[] args)
    {
        Rhino.Runtime.PythonScript.Reset();
        if (args.Contains("--reproduce"))
        {
            var normal = Run();
            Rhino.Runtime.PythonScript.FailInvoke = true;
            Console.WriteLine(new JObject { ["normal"] = normal, ["exception"] = Run(),
                ["projection_source"] = "production ScriptExecutor.Results.cs", ["native_geometry_tested"] = false });
            return;
        }
        var good = Run();
        Check((string)good["status"] == "success" && (string)good["mutation_state"] == "completed", "completed status: " + good);
        var python = Rhino.Runtime.PythonScript.Last;
        Check(ScriptExecutor.Calls == 1 && python.Invocations == 1, "single native Undo-owned invocation");
        Check(python.Variables.Count == 1 && (string)python.Variables["__name__"] == "original", "namespace restored");
        Check(ReferenceEquals(python.ScriptContextDoc, python.OriginalDoc) && python.Output == python.OriginalOutput, "context restored");
        Check(((string)good["result"]["algorithm_sha256"]).Length == 64, "source fingerprint");
        Check((string)good["result"]["output"] == "Document", "document output only");
        Check(good["result"]["results"][0]["report"]["timestamp_text"].Type == JTokenType.String &&
            (string)good["result"]["results"][0]["report"]["timestamp_text"] == "2026-11-05T12:00:00Z", "JSON date-shaped strings retain string identity");
        Check(python.LoadedSource.StartsWith("__name__ = 'almond_plansection_internal'\n"), "interactive main disabled");
        Check(python.LoadedSource.Contains("def run(doc, operation, clipping_ids"), "packaged algorithm shared");
        var responses = new JObject { ["completed"] = good };
        var move = Request(); move["operation"] = "Move";
        Check((string)Run(move)["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0,
            "Move without a target never enters Undo");
        move["points"] = new JObject { [Id.ToString()] = new JArray(12, 34, -9) };
        Check((string)Run(move)["status"] == "success" && ScriptExecutor.Calls == 1, "Move executes once with explicit XYZ");
        Check(Rhino.Runtime.PythonScript.Last.Arguments["operation"].Value<string>() == "Move" &&
            !(bool)Rhino.Runtime.PythonScript.Last.Arguments["small_details"], "Move passes the typed options");
        var referenceDoc = Doc();
        referenceDoc.Objects.Reference = true;
        ScriptExecutor.Calls = 0;
        Check((string)PlanSectionTool.Handle(referenceDoc, Request())["mutation_state"] == "not_started" &&
            ScriptExecutor.Calls == 0, "A non-Worksession reference clipping is rejected");

        referenceDoc.Objects.ReferenceSerial = 1001;
        referenceDoc.Worksession = new Rhino.DocObjects.Worksession(referenceDoc, new[] {
            referenceDoc.Path, @"C:\offline\Attachment.3dm" });
        var include = Request(); include["include_attachments"] = true;
        var attached = PlanSectionTool.Handle(referenceDoc, include);
        Check((string)attached["status"] == "success" &&
            ScriptExecutor.Calls == 1 && (bool)Rhino.Runtime.PythonScript.Last.Arguments["include_attachments"],
            "Attached clipping and explicit combined extraction reach the packaged script");
        Check(Rhino.Runtime.PythonScript.Last.AttachedModelSerials.SequenceEqual(new[] { true, false, false }),
            "The script's ownership predicate requires the serial to resolve to a current attachment");
        ScriptExecutor.Calls = 0;
        Check((string)PlanSectionTool.Handle(referenceDoc, Request())["status"] == "success" && ScriptExecutor.Calls == 1,
            "Attached clipping may define a cut for active-model geometry");
        ScriptExecutor.Calls = 0;
        Check((string)PlanSectionTool.Handle(referenceDoc, move)["status"] == "success" && ScriptExecutor.Calls == 1,
            "Attached clipping may identify a local drawing to move");

        var unknownPath = Doc();
        unknownPath.Objects.Reference = true;
        unknownPath.Objects.ReferenceSerial = 1002;
        unknownPath.Worksession = new Rhino.DocObjects.Worksession(unknownPath, new[] {
            unknownPath.Path, @"C:\offline\Attachment.3dm" });
        ScriptExecutor.Calls = 0;
        Check((string)PlanSectionTool.Handle(unknownPath, include)["mutation_state"] == "not_started" &&
            ScriptExecutor.Calls == 0, "A native reference path outside the current attachment list is rejected");
        unknownPath.Objects.ReferenceSerial = 1003;
        var ownershipUnavailable = PlanSectionTool.Handle(unknownPath, include);
        Check((string)ownershipUnavailable["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0 &&
            ((string)ownershipUnavailable["message"]).Contains("Cannot resolve Worksession reference model serial 1003"),
            "An unavailable reference clipping path reports an observation failure");

        unknownPath.Objects.Reference = false;
        var update = Request(); update["operation"] = "Update"; update["include_attachments"] = true;
        foreach (uint serial in new uint[] { 1003, 1004 })
        {
            Rhino.Runtime.PythonScript.ExtractionReferenceSerial = serial;
            var unresolved = PlanSectionTool.Handle(unknownPath, update);
            Check((string)unresolved["drawing_status"] == "failed" &&
                ((string)unresolved["result"]["results"][0]["error"])
                    .Contains($"Cannot resolve Worksession reference model serial {serial}"),
                "Update reports unavailable or invalid attachment ownership as failure");
        }
        Rhino.Runtime.PythonScript.Reset();
        ScriptExecutor.Calls = 0;
        unknownPath.Worksession.ModelCount = 3;
        Check((string)PlanSectionTool.Handle(unknownPath, include)["mutation_state"] == "not_started" &&
            ScriptExecutor.Calls == 0, "An incomplete attachment observation stops explicitly combined extraction");

        foreach (object unsupported in new object[] { new JObject { ["ok"] = true }, new JValue("text"),
            new Dictionary<string, object> { ["nested"] = new JValue(1) } })
        {
            var captured = ScriptExecutor.CaptureForTest(unsupported);
            Check(captured.Result == null && captured.ResultError.StartsWith("result_unsupported_type:"), "production unsupported JToken contract");
        }
        var exactBytes = ScriptExecutor.CaptureForTest(new string('x', 65534));
        Check(exactBytes.ResultError == null && Encoding.UTF8.GetByteCount(exactBytes.Result.ToString(Formatting.None)) == 65536, "exact 64KiB accepted");
        Check(ScriptExecutor.CaptureForTest(new string('x', 65535)).ResultError.StartsWith("result_too_large:"), "64KiB plus one rejected");
        var unicode = String.Concat(Enumerable.Repeat("한", 21844)) + "aa";
        Check(ScriptExecutor.CaptureForTest(unicode).ResultError == null &&
            ScriptExecutor.CaptureForTest(unicode + "a").ResultError.StartsWith("result_too_large:"), "budget counts UTF8 bytes");
        object nested = "leaf";
        for (int depth = 0; depth < 16; depth++) nested = new List<object> { nested };
        Check(ScriptExecutor.CaptureForTest(nested).ResultError == null, "16 containers accepted");
        Check(ScriptExecutor.CaptureForTest(new List<object> { nested }).ResultError.StartsWith("result_too_deep:"), "17 containers rejected");
        var ids = Enumerable.Repeat(Id.ToString(), 1681).ToList();
        Check(Encoding.UTF8.GetByteCount(JsonConvert.SerializeObject(ids)) == 65560, "single clipping GUID array exceeds budget");
        Rhino.Runtime.PythonScript.ObjectIds = ids;
        var oversized = Run(); responses["oversized"] = oversized;
        Check((string)oversized["status"] == "success" && (string)oversized["mutation_state"] == "completed" &&
            oversized["result_error"] == null, "large typed result returns inline");
        Check(Encoding.UTF8.GetByteCount(oversized["result"].ToString(Formatting.None)) > 65536,
            "dedicated result exceeds the generic script capture limit");
        var full = oversized["result"]["results"][0];
        Check(full["object_ids"].Count() == 1681 && full["draw_plane"]["origin"][2].Value<int>() == -9,
            "inline output preserves every GUID and placement");
        Check((string)full["report"]["unicode"] == String.Concat(Enumerable.Repeat("한😀", 1800)),
            "inline output preserves Unicode");
        Check((string)full["extraction"]["layers"][0] == "model::walls" && ScriptExecutor.Calls == 1 &&
            Rhino.Runtime.PythonScript.Last.Invocations == 1, "extraction evidence returns from a single execution");
        Rhino.Runtime.PythonScript.Reset();

        foreach (var field in new[] { "script", "folder", "output", "language", "project_root", "artifact_dir" })
        {
            var request = Request(); request[field] = "caller input";
            var result = Run(request);
            Check((string)result["mutation_state"] == "not_started" && ScriptExecutor.Calls == 0, "reject unexpected " + field);
        }
        foreach (var change in new Action<JObject>[] {
            r => r["operation"] = "PDF", r => r["hatch"] = 1, r => r["near_width"] = 0,
            r => r["include_attachments"] = 1,
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
        foreach (string state in new[] { "partial", "cancelled", "failed" })
        {
            Rhino.Runtime.PythonScript.DrawingStatus = state;
            var request = Request();
            if (state == "partial") ((JArray)request["clipping_ids"]).Add(Rhino.ObjectTable.SecondClipping.ToString());
            var result = Run(request);
            responses[state] = result;
            Check((string)result["drawing_status"] == state && (string)result["mutation_state"] ==
                (state == "cancelled" ? "not_started" : "partial"), "partial evidence " + state);
        }
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.DrawingStatus = "deadline";
        var interrupted = Request();
        ((JArray)interrupted["clipping_ids"]).Add(Rhino.ObjectTable.SecondClipping.ToString());
        responses["deadline"] = Run(interrupted);
        ScriptExecutor.FailUndoClose = true;
        responses["deadline_undo_error"] = Run(interrupted);
        ScriptExecutor.FailUndoClose = false;
        Rhino.Runtime.PythonScript.FailRemove = true;
        var deadlineCleanupError = Run(interrupted);
        Check((string)deadlineCleanupError["status"] == "error" && deadlineCleanupError["drawing_status"] == null &&
            (int)deadlineCleanupError["result"]["completed"] == 1, "cleanup failure keeps cut evidence without confirming timeout");
        responses["deadline_cleanup_error"] = deadlineCleanupError;
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.FailInvoke = true;
        var runtimeError = Run(); responses["runtime_error"] = runtimeError;
        Check((string)runtimeError["mutation_state"] == "unknown" && (string)runtimeError["status"] == "runtime_error" &&
            runtimeError["error_trace"] != null, "production execution failure status remains uncertain");
        Check(Rhino.Runtime.PythonScript.Last.Variables.Count == 1, "failure cleanup");
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.FailRemove = true;
        var cleanup = Run(); python = Rhino.Runtime.PythonScript.Last;
        Check((string)cleanup["error_code"] == "plan_section_context_restore_failed", "cleanup diagnostic");
        Check(ReferenceEquals(python.ScriptContextDoc, python.OriginalDoc) && python.Output == python.OriginalOutput, "remove failure does not skip doc/output restoration");
        Check(cleanup["result"] != null && cleanup["context_restore_errors"] is JArray, "retain drawing result on cleanup failure");
        Console.WriteLine("PLAN_SECTION_RESULTS=" + new JObject { ["passed"] = checks, ["native_geometry_tested"] = false,
            ["production_result_projector"] = true, ["responses"] = responses }.ToString(Formatting.None));
    }
}

namespace Rhino
{
    public class RhinoDoc
    {
        public static RhinoDoc ActiveDoc;
        public uint RuntimeSerialNumber = 1;
        public string Path;
        public bool IsReadOnly;
        public ObjectTable Objects;
        DocObjects.Worksession worksession;
        public DocObjects.Worksession Worksession
        {
            get => worksession ?? new DocObjects.Worksession(this, Array.Empty<string>());
            set => worksession = value;
        }
    }
    public class ObjectTable
    {
        public static readonly Guid SecondClipping = Guid.Parse("00000000-0000-0000-0000-000000000002");
        readonly Guid id;
        public bool Reference;
        public uint ReferenceSerial;
        public ObjectTable(Guid id) { this.id = id; }
        public DocObjects.RhinoObject FindId(Guid value) => value == id || value == SecondClipping
            ? new DocObjects.ClippingPlaneObject { IsReference = Reference, ReferenceModelSerialNumber = ReferenceSerial }
            : null;
    }
}
namespace Rhino.DocObjects
{
    public class ObjectAttributes { public bool IsInstanceDefinitionObject; }
    public class RhinoObject
    {
        public bool IsDeleted, IsReference;
        public uint ReferenceModelSerialNumber;
        public ObjectAttributes Attributes = new ObjectAttributes();
    }
    public class ClippingPlaneObject : RhinoObject { }
    public class Worksession
    {
        public RhinoDoc Document;
        public uint RuntimeSerialNumber;
        public int ModelCount;
        public string[] ModelPaths;
        public Worksession(RhinoDoc document, string[] paths)
        {
            Document = document;
            ModelPaths = paths;
            ModelCount = paths.Length;
            RuntimeSerialNumber = paths.Length == 0 ? 0u : 51u;
        }
        public string ModelPathFromSerialNumber(uint serial) => serial == 1001
            ? @"c:\offline\attachment.3dm"
            : serial == 1002 ? @"C:\offline\Unattached.3dm"
            : serial == 1004 ? "relative.3dm" : null;
    }
}
namespace Rhino.Runtime
{
    public class PythonScript
    {
        public static PythonScript Last;
        public static bool Unavailable, FailLoad, FailInvoke, FailRemove;
        public static string DrawingStatus = "completed";
        public static List<string> ObjectIds;
        public static uint? ExtractionReferenceSerial;
        public readonly object OriginalDoc = new object();
        public readonly Action<string> OriginalOutput = text => { };
        public Dictionary<string, object> Variables = new Dictionary<string, object> { ["__name__"] = "original" };
        public object ScriptContextDoc { get; set; }
        public Action<string> Output { get; set; }
        public string LoadedSource;
        public int Invocations;
        public JObject Arguments;
        public bool[] AttachedModelSerials;
        public static void Reset() { Unavailable = FailLoad = FailInvoke = FailRemove = false; DrawingStatus = "completed"; ExtractionReferenceSerial = null; ObjectIds = new List<string> { "00000000-0000-0000-0000-000000000003" }; }
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
            if (!(Variables["_almond_deadline_token"] is System.Threading.CancellationToken token) || !token.CanBeCanceled)
                throw new Exception("The dedicated algorithm must receive a cancellable deadline token");
            var args = Arguments = JObject.Parse((string)Variables["_almond_arguments_json"]);
            var includeAttachments = (bool?)args["include_attachments"] == true;
            bool deadline = DrawingStatus == "deadline";
            string drawingStatus = deadline ? "cancelled" : DrawingStatus, attachmentError = null;
            if (includeAttachments && (string)args["operation"] != "Move")
            {
                var observeAttachments = (Func<Func<uint, bool>>)Variables["_almond_observe_attachments"];
                var attachedModel = observeAttachments();
                AttachedModelSerials = new[] { attachedModel(1001), attachedModel(1002), attachedModel(0) };
                if (ExtractionReferenceSerial is uint serial)
                {
                    try { attachedModel(serial); }
                    catch (Exception error) { drawingStatus = "failed"; attachmentError = error.Message; }
                }
            }
            var results = new JArray();
            var clipIds = (JArray)args["clipping_ids"];
            for (int i = 0; i < clipIds.Count; i++)
            {
                bool completed = drawingStatus == "completed" || ((drawingStatus == "partial" || deadline) && i == 0);
                var result = new JObject { ["clipping_id"] = clipIds[i].DeepClone(),
                    ["status"] = completed ? "completed" : deadline ? "not_started" : drawingStatus == "cancelled" ? "cancelled" : "failed" };
                if (attachmentError != null) result["error"] = attachmentError;
                if (completed)
                {
                    result["object_ids"] = new JArray(ObjectIds);
                    result["draw_plane"] = new JObject { ["origin"] = new JArray(12, 34, -9),
                        ["xaxis"] = new JArray(1, 0, 0), ["yaxis"] = new JArray(0, 1, 0) };
                    if ((string)args["operation"] != "Move")
                        result["extraction"] = new JObject { ["layers"] = new JArray("model::walls"),
                            ["source_object_count"] = 3, ["include_hidden"] = true, ["include_locked"] = true,
                            ["include_attachments"] = includeAttachments };
                    result["report"] = new JObject { ["timestamp_text"] = "2026-11-05T12:00:00Z",
                        ["unicode"] = String.Concat(Enumerable.Repeat("한😀", 1800)) };
                }
                results.Add(result);
            }
            var receipt = new JObject {
                ["status"] = drawingStatus, ["requested"] = clipIds.Count,
                ["completed"] = results.Count(r => (string)r["status"] == "completed"), ["results"] = results };
            if (drawingStatus == "cancelled") receipt["stop_reason"] = deadline ? "deadline" : "user";
            Variables["_almond_result_json"] = receipt.ToString();
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
    // Only execution scheduling/Undo/documents are doubles. Projection and runtime_error
    // classification are the production partial source linked by this project.
    public partial class ScriptExecutor
    {
        public static int Calls;
        public static bool FailUndoClose;
        internal static ScriptResult CaptureForTest(object value)
        {
            var result = new ScriptResult(); CaptureResult(result, value); return result;
        }
        internal object ExecuteAction(Rhino.RhinoDoc doc, Func<object> action)
        {
            Calls++;
            var result = new ScriptResult();
            try { CaptureResult(result, action()); }
            catch (Exception error) { SetRuntimeError(result, error); }
            if (FailUndoClose) SetRuntimeError(result, new InvalidOperationException("Undo close failed."));
            return result;
        }
    }
}
