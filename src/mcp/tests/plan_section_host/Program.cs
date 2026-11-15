// Exercises the production adapter against API doubles, never a Rhino process/document.
using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
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
        'points':{},'hatch':true,'include_references':false,'request_id':'','small_details':false,
        'near_width':0.09,'far_width':0.04,'near_dark':80,'far_dark':45,
        'expected_model_path':'C:\\offline\\model.3dm'}");
    static Rhino.RhinoDoc Doc() => Rhino.RhinoDoc.ActiveDoc = new Rhino.RhinoDoc { Path = @"C:\offline\model.3dm", Objects = new Rhino.ObjectTable(Id) };
    static JObject Run(JObject request = null)
    {
        ScriptExecutor.Calls = 0;
        return PlanSectionTool.Handle(Doc(), request ?? Request());
    }
    static void Main(string[] args)
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
        Check((int)good["result"]["results"][0]["report"]["sources"] == 2, "actual source count is retained");
        Check((int)good["result"]["results"][0]["generation_conditions"]["drawing_plane"]["origin"][2] == 100,
            "plane conditions survive the production common-depth projector");
        Check(good["result_error"] == null, "required nested conditions remain within 16-container depth limit");
        var conflictSample = good["result"]["results"][0]["report"]["metadata_conflicts"][0];
        Check((string)conflictSample["field"] == "user_text.Phase" && (string)conflictSample["sources"][0] == "block/source" &&
            (string)conflictSample["reason"] == "different_values", "conflict field, source path and reason survive direct delivery");
        Check(python.LoadedSource.StartsWith("__name__ = 'almond_plansection_internal'\n"), "interactive main disabled");
        Check(python.LoadedSource.Contains("def run(doc, operation, clipping_ids"), "packaged algorithm shared");
        var responses = new JObject { ["completed"] = good };

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
        Check(oversized["result"]["result_delivery"] == null && oversized["result_error"] == null &&
            (string)oversized["mutation_state"] == "completed", "oversized ID arrays become direct count summaries");
        Check((int)oversized["result"]["results"][0]["output_object_count"] == 1681, "all generated objects counted without listing IDs");
        Check(oversized["result"]["results"][0]["object_ids"] == null, "generated object IDs are omitted");
        Check(Encoding.UTF8.GetByteCount(oversized.ToString(Formatting.None)) < 65536, "direct summary stays within common budget");
        Check((string)oversized["status"] == "success" && ScriptExecutor.Calls == 1, "summary requires one generation");

        // Offline per-model journal fixture: no Rhino process, model, or DB is opened.
        string journalRoot = Path.Combine(Path.GetTempPath(), "almond-plansection-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(journalRoot);
        string modelPath = Path.Combine(journalRoot, "fixture.3dm");
        var journalDoc = Doc(); journalDoc.Path = modelPath;
        var keyed = Request(); keyed["expected_model_path"] = modelPath;
        keyed["request_id"] = Guid.NewGuid().ToString();
        ScriptExecutor.Calls = 0;
        var first = PlanSectionTool.Handle(journalDoc, keyed);
        Check((string)first["mutation_state"] == "completed" && ScriptExecutor.Calls == 1, "durable keyed generation completes once");
        var replayed = PlanSectionTool.Handle(journalDoc, keyed); responses["replayed"] = replayed;
        Check((bool)replayed["response_replayed"] && ScriptExecutor.Calls == 1, "same-key retry replays without Undo or mutation");
        Check(!(bool)replayed["historical_response"] && !(bool)replayed["current_output_confirmed"], "same-instance replay is execution evidence, not current geometry observation");
        journalDoc.Objects.Missing = true;
        int callsBeforeRecovery = ScriptExecutor.Calls;
        int createsBeforeRecovery = Rhino.Runtime.PythonScript.Creates;
        var missingReplay = PlanSectionTool.Handle(journalDoc, keyed); responses["completed_missing_clip"] = missingReplay;
        Check((bool?)missingReplay["response_replayed"] == true && ScriptExecutor.Calls == callsBeforeRecovery &&
            Rhino.Runtime.PythonScript.Creates == createsBeforeRecovery, "completed journal recovery does not require the clipping to still exist");
        journalDoc.IsReadOnly = true; EditingContext.Stable = false;
        var unavailableEditor = PlanSectionTool.Handle(journalDoc, keyed);
        Check((bool?)unavailableEditor["response_replayed"] == true && ScriptExecutor.Calls == callsBeforeRecovery &&
            Rhino.Runtime.PythonScript.Creates == createsBeforeRecovery, "readonly/editor state does not block nonmutating journal recovery");
        journalDoc.IsReadOnly = false; EditingContext.Stable = true;
        var wrongBinding = (JObject)keyed.DeepClone(); wrongBinding["expected_model_path"] = Path.Combine(journalRoot, "other.3dm");
        var filesBeforeBinding = Directory.GetFiles(Path.Combine(journalRoot, ".almond", "plan-section-requests"));
        var boundError = PlanSectionTool.Handle(journalDoc, wrongBinding); responses["recovery_wrong_binding"] = boundError;
        Check((string)boundError["mutation_state"] == "not_started" && (string)boundError["status"] == "error" &&
            boundError["response_replayed"] == null && ScriptExecutor.Calls == callsBeforeRecovery &&
            Directory.GetFiles(Path.Combine(journalRoot, ".almond", "plan-section-requests")).SequenceEqual(filesBeforeBinding),
            "model binding is checked before journal replay and creates no journal files");
        Rhino.Runtime.PythonScript.Reset();
        journalDoc.RuntimeSerialNumber = 99;
        var restarted = PlanSectionTool.Handle(journalDoc, keyed); responses["historical"] = restarted; responses["historical_missing_clip"] = restarted;
        Check((bool)restarted["response_replayed"] && ScriptExecutor.Calls == 1, "new document instance recovers persisted execution evidence");
        Check((bool)restarted["historical_response"] && (bool)restarted["requires_reconciliation"] && !(bool)restarted["current_output_confirmed"], "new document instance does not confirm unsaved past outputs");
        var changed = (JObject)keyed.DeepClone(); changed["small_details"] = true;
        var conflict = PlanSectionTool.Handle(journalDoc, changed);
        Check((string)conflict["mutation_state"] == "not_started" && ScriptExecutor.Calls == 1 && ((string)conflict["message"]).Contains("request_id"),
            "fingerprint conflict is checked before missing-clipping validation");
        string journalPath = Path.Combine(journalRoot, ".almond", "plan-section-requests", Guid.Parse((string)keyed["request_id"]).ToString("N") + ".json");
        var pending = JObject.Parse(File.ReadAllText(journalPath));
        Check(pending["response"]["result"]["results"][0]["generation_conditions"]["source_layer_names"].Count() == 2 &&
            pending["response"]["result"]["results"][0]["generation_conditions"]["clipping_plane"] != null,
            "completed journal retains mandatory layers and plane conditions");
        Check(pending["process_id"] != null && pending["process_start_ticks"] != null, "journal retains process identity");
        pending["process_start_ticks"] = "previous-process";
        File.WriteAllText(journalPath, pending.ToString(Formatting.None));
        journalDoc.RuntimeSerialNumber = 1;
        var previousProcess = PlanSectionTool.Handle(journalDoc, keyed);
        Check((bool)previousProcess["historical_response"] && (bool)previousProcess["requires_reconciliation"] && ScriptExecutor.Calls == 1,
            "previous process identity makes replay historical without regeneration");
        pending.Remove("response"); pending["state"] = "pending";
        File.WriteAllText(journalPath, pending.ToString(Formatting.None));
        using (var exclusive = new FileStream(journalPath, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        {
            var locked = PlanSectionTool.Handle(journalDoc, keyed);
            Check((string)locked["mutation_state"] == "unknown" && ScriptExecutor.Calls == 1,
                "concurrent writer or reader lock cannot start duplicate generation");
        }
        var uncertain = PlanSectionTool.Handle(journalDoc, keyed); responses["pending_missing_clip"] = uncertain;
        Check((string)uncertain["error_code"] == "plan_section_request_pending" && (string)uncertain["mutation_state"] == "unknown", "pending journal fences retry after response loss");
        Check(ScriptExecutor.Calls == 1, "pending retry never regenerates");
        File.WriteAllText(journalPath, "incomplete journal");
        var unreadable = PlanSectionTool.Handle(journalDoc, keyed);
        Check((string)unreadable["mutation_state"] == "unknown" && ScriptExecutor.Calls == 1, "unreadable existing journal fences retry");
        Check(File.ReadAllText(journalPath) == "incomplete journal", "unreadable evidence is preserved");
        var invalidNew = (JObject)keyed.DeepClone(); invalidNew["request_id"] = Guid.NewGuid().ToString();
        ScriptExecutor.Calls = 0; Rhino.Runtime.PythonScript.Creates = 0;
        int beforeInvalid = ScriptExecutor.Calls, createsBeforeInvalid = Rhino.Runtime.PythonScript.Creates;
        var invalidClip = PlanSectionTool.Handle(journalDoc, invalidNew); responses["new_missing_clip"] = invalidClip;
        Check((string)invalidClip["mutation_state"] == "not_started" && !(bool)invalidClip["requires_reconciliation"] &&
            ScriptExecutor.Calls == beforeInvalid && Rhino.Runtime.PythonScript.Creates == createsBeforeInvalid,
            "new invalid clipping request calls neither Python nor the Undo-owning ScriptExecutor");
        journalDoc.Objects.Missing = false;
        var readonlyNew = (JObject)keyed.DeepClone(); readonlyNew["request_id"] = Guid.NewGuid().ToString();
        journalDoc.IsReadOnly = true;
        var readonlyError = PlanSectionTool.Handle(journalDoc, readonlyNew);
        Check((string)readonlyError["mutation_state"] == "not_started" && ScriptExecutor.Calls == beforeInvalid &&
            Rhino.Runtime.PythonScript.Creates == createsBeforeInvalid, "new readonly mutations remain rejected before Python/Undo");
        journalDoc.IsReadOnly = false; EditingContext.Stable = false;
        var editorNew = (JObject)keyed.DeepClone(); editorNew["request_id"] = Guid.NewGuid().ToString();
        var editorError = PlanSectionTool.Handle(journalDoc, editorNew);
        Check((string)editorError["mutation_state"] == "not_started" && ScriptExecutor.Calls == beforeInvalid &&
            Rhino.Runtime.PythonScript.Creates == createsBeforeInvalid, "new unstable-editor mutations remain rejected before Python/Undo");
        EditingContext.Stable = true;
        keyed["request_id"] = Guid.NewGuid().ToString();
        Rhino.Runtime.PythonScript.FailInvoke = true;
        var failed = PlanSectionTool.Handle(journalDoc, keyed);
        int afterFailure = ScriptExecutor.Calls;
        Rhino.Runtime.PythonScript.Reset();
        var failedReplay = PlanSectionTool.Handle(journalDoc, keyed);
        Check((string)failed["mutation_state"] == "unknown" && (bool)failedReplay["response_replayed"] && ScriptExecutor.Calls == afterFailure,
            "unknown mutation result is retained and never re-executed");
        Rhino.Runtime.PythonScript.Reset();

        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.SourceLayers = Enumerable.Range(0, 8000).Select(i => "Model::Layer" + i).ToList();
        var overflow = Run(); responses["mandatory_overflow"] = overflow;
        Check((string)overflow["mutation_state"] == "unknown", "unexpected mandatory overflow never claims confirmed completion");
        Rhino.Runtime.PythonScript.Reset();
        Rhino.Runtime.PythonScript.Conflicts = new JArray(Enumerable.Range(0, 64).Select(i => new JObject {
            ["field"] = "user_text.Phase", ["sources"] = new JArray("블록/" + new string('한', 1000)), ["reason"] = "different_values" }));
        var optional = Run(); responses["optional_overflow"] = optional;
        var optionalReport = optional["result"]["results"][0]["report"];
        Check((bool)optionalReport["metadata_conflicts_truncated"] && (int)optionalReport["metadata_conflicts_omitted_count"] == 64,
            "oversized optional conflict samples are explicitly truncated");
        Check((int)optionalReport["metadata_conflict_count"] == 64 && optional["result"]["results"][0]["generation_conditions"] != null,
            "required conditions and total conflict count survive optional detail reduction");
        Check(Encoding.UTF8.GetByteCount(optional.ToString(Formatting.None)) < 65536 && optional["result_error"] == null,
            "combined Korean optional diagnostics stay under production 64KiB budget");
        Rhino.Runtime.PythonScript.Reset();
        var combinedRows = new JArray(); var combinedIds = new JArray();
        for (int i = 0; i < 8; i++)
        {
            var id = i == 0 ? Id : Guid.NewGuid();
            Rhino.ObjectTable.AdditionalIds.Add(id); combinedIds.Add(id.ToString());
            var row = (JObject)good["result"]["results"][0].DeepClone();
            row["clipping_id"] = id.ToString(); row["name"] = "한국어도면_" + i;
            row["generation_conditions"]["source_layer_names"] = new JArray("참조::한국어층::벽", "모델::코어::슬래브");
            row["report"]["metadata_conflict_count"] = 64;
            row["report"]["metadata_conflicts"] = new JArray(Enumerable.Range(0, 64).Select(j => new JObject {
                ["field"] = "user_text.메타데이터", ["sources"] = new JArray("참조/블록/" + new string('한', 100)), ["reason"] = "different_values" }));
            combinedRows.Add(row);
        }
        Rhino.Runtime.PythonScript.DrawingOverride = new JObject { ["status"] = "completed", ["requested"] = 8, ["completed"] = 8,
            ["results"] = combinedRows, ["mutation_state"] = "completed", ["requires_reconciliation"] = false };
        var combinedRequest = Request(); combinedRequest["clipping_ids"] = combinedIds;
        var combined = Run(combinedRequest); responses["combined"] = combined;
        Check(combined["result"]["results"].Count() == 8 && combined["result_error"] == null,
            "many Korean clipping conditions survive combined optional-diagnostic reduction");
        Check(Encoding.UTF8.GetByteCount(JsonConvert.SerializeObject(combined, new JsonSerializerSettings { StringEscapeHandling = StringEscapeHandling.EscapeNonAscii })) < 65536,
            "combined Korean clipping, layers and optional metadata fit even ASCII-escaped 64KiB");
        Check(combined["result"]["results"].All(row => row["generation_conditions"]["clipping_plane"] != null &&
            row["generation_conditions"]["source_layer_names"].Count() == 2 && (bool)row["report"]["metadata_conflicts_truncated"]),
            "optional trimming never drops mandatory per-clipping planes or layers");
        Rhino.ObjectTable.AdditionalIds.Clear();
        Rhino.Runtime.PythonScript.Reset();
        int fixtureArgument = Array.IndexOf(args, "--algorithm-fixtures");
        if (fixtureArgument >= 0)
            foreach (var pair in JObject.Parse(File.ReadAllText(args[fixtureArgument + 1], Encoding.UTF8)).Properties())
            {
                Rhino.Runtime.PythonScript.DrawingOverride = (JObject)pair.Value;
                var actual = Run(); responses["algorithm_" + pair.Name] = actual;
                bool preflight = pair.Name == "budget" || pair.Name == "preflight";
                Check((string)actual["mutation_state"] == (preflight ? "not_started" : "unknown"),
                    "actual algorithm outcome crosses production native envelope: " + pair.Name);
                Check(preflight ? (string)actual["status"] == "error" : (bool)actual["requires_reconciliation"],
                    "preflight rejection and rollback uncertainty remain distinct: " + pair.Name);
                if (preflight)
                    Check(actual["drawing_status"] == null && (string)actual["result"]?["status"] == "error" && actual["result_error"] == null,
                        "preflight is a valid error result without a drawing completion state: " + pair.Name);
                Rhino.Runtime.PythonScript.Reset();
            }

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
            responses[state] = result;
            Check((string)result["drawing_status"] == state && (string)result["mutation_state"] == "partial", "partial evidence " + state);
        }
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
    public class RhinoDoc { public static RhinoDoc ActiveDoc; public uint RuntimeSerialNumber = 1; public string Path; public bool IsReadOnly; public ObjectTable Objects; }
    public class ObjectTable
    {
        readonly Guid id;
        public bool Missing;
        public static readonly HashSet<Guid> AdditionalIds = new HashSet<Guid>();
        public ObjectTable(Guid id) { this.id = id; }
        public DocObjects.RhinoObject FindId(Guid value) => !Missing && (value == id || AdditionalIds.Contains(value)) ? new DocObjects.ClippingPlaneObject() : null;
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
        public static int Creates;
        public static bool Unavailable, FailLoad, FailInvoke, FailRemove;
        public static string DrawingStatus = "completed";
        public static JObject DrawingOverride;
        public static JArray DefaultConflicts() => new JArray(new JObject { ["field"] = "user_text.Phase", ["sources"] = new JArray("block/source"), ["reason"] = "different_values" });
        public static JArray Conflicts = DefaultConflicts();
        public static List<string> ObjectIds = new List<string>();
        public static List<string> SourceLayers = new List<string> { "Model::Wall", "Attach::Core" };
        public readonly object OriginalDoc = new object();
        public readonly Action<string> OriginalOutput = text => { };
        public Dictionary<string, object> Variables = new Dictionary<string, object> { ["__name__"] = "original" };
        public object ScriptContextDoc { get; set; }
        public Action<string> Output { get; set; }
        public string LoadedSource;
        public int Invocations;
        public static void Reset() { Creates = 0; Unavailable = FailLoad = FailInvoke = FailRemove = false; DrawingStatus = "completed"; DrawingOverride = null; Conflicts = DefaultConflicts(); ObjectIds = new List<string>(); SourceLayers = new List<string> { "Model::Wall", "Attach::Core" }; }
        public static PythonScript Create()
        {
            Creates++;
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
            if (DrawingOverride != null) { Variables["_almond_result_json"] = DrawingOverride.ToString(); return true; }
            var args = JObject.Parse((string)Variables["_almond_arguments_json"]);
            Variables["_almond_result_json"] = new JObject {
                ["status"] = DrawingStatus, ["requested"] = 1, ["completed"] = DrawingStatus == "completed" ? 1 : 0,
                ["results"] = new JArray(new JObject { ["clipping_id"] = args["clipping_ids"][0].DeepClone(),
                    ["generation_conditions"] = new JObject {
                        ["clipping_plane"] = new JObject { ["origin"] = new JArray(0,0,0), ["xaxis"] = new JArray(1,0,0), ["yaxis"] = new JArray(0,1,0) },
                        ["drawing_plane"] = new JObject { ["origin"] = new JArray(10,20,100), ["xaxis"] = new JArray(1,0,0), ["yaxis"] = new JArray(0,1,0) },
                        ["source_object_count"] = 2, ["source_layer_names"] = new JArray(SourceLayers),
                        ["include_references"] = false, ["reference_objects_included"] = false,
                        ["hidden_objects_included"] = true, ["locked_objects_included"] = false,
                        ["depth"] = JValue.CreateNull(), ["participation_applied"] = true },
                    ["object_ids"] = new JArray(ObjectIds), ["report"] = new JObject { ["metadata_conflict_count"] = Conflicts.Count, ["metadata_conflicts"] = Conflicts.DeepClone(), ["sources"] = 2, ["timestamp_text"] = "2026-11-05T12:00:00Z", ["unicode"] = String.Concat(Enumerable.Repeat("한😀", 1800)) },
                    ["status"] = DrawingStatus == "completed" ? "completed" : "cancelled" }) }.ToString();
            return true;
        }
    }
}
namespace RhinoAlmondBridge
{
    public static class EditingContext
    {
        public static bool Stable = true;
        public static JObject Observe(Rhino.RhinoDoc doc) => new JObject { ["stable"] = Stable, ["mode"] = "model" };
    }
    // Only execution scheduling/Undo/documents are doubles. Projection and runtime_error
    // classification are the production partial source linked by this project.
    public partial class ScriptExecutor
    {
        public static int Calls;
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
            return result;
        }
    }
}
