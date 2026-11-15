using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Runtime;

namespace RhinoAlmondBridge
{
    /// <summary>Fixed packaged PlanSection algorithm; no caller-authored code or paths.</summary>
    public static class PlanSectionTool
    {
        const string Resource = "RhinoAlmondBridge.PlanSection.py";
        const string Invoke = @"
_almond_args = json.loads(_almond_arguments_json)
_almond_result_json = json.dumps(run(_almond_doc,
    _almond_args['operation'], _almond_args['clipping_ids'],
    points=_almond_args['points'], output='Document', response_budget=32000,
    hatch=_almond_args['hatch'], elevation=True,
    include_references=_almond_args['include_references'],
    small_details=_almond_args['small_details'],
    near_width=_almond_args['near_width'], far_width=_almond_args['far_width'],
    near_dark=_almond_args['near_dark'], far_dark=_almond_args['far_dark']))
";
        static readonly HashSet<string> Fields = new HashSet<string>(new[] {
            "type", "operation", "clipping_ids", "points", "hatch", "small_details", "include_references", "request_id",
            "near_width", "far_width", "near_dark", "far_dark", "expected_model_path" });

        internal static JObject Validate(RhinoDoc doc, JObject request)
        {
            if (request == null || request.Properties().Any(p => !Fields.Contains(p.Name)))
                throw new ArgumentException("PlanSection accepts typed drawing parameters only.");
            var expected = request["expected_model_path"];
            if (expected?.Type != JTokenType.String || String.IsNullOrWhiteSpace((string)expected) ||
                !Path.IsPathRooted((string)expected) || doc == null || String.IsNullOrWhiteSpace(doc.Path) ||
                !String.Equals(Path.GetFullPath(doc.Path), Path.GetFullPath((string)expected), StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("PlanSection requires the bound saved document.");
            var operation = request["operation"];
            if (operation?.Type != JTokenType.String || ((string)operation != "Create" && (string)operation != "Update" && (string)operation != "Move"))
                throw new ArgumentException("PlanSection supports Create, Update or Move Document output.");
            if (!(request["clipping_ids"] is JArray input) || input.Count == 0)
                throw new ArgumentException("Supply a nonempty clipping GUID list.");
            var ids = new List<string>();
            foreach (var token in input)
            {
                if (token.Type != JTokenType.String || !Guid.TryParse((string)token, out var id) || id == Guid.Empty)
                    throw new ArgumentException("Each clipping ID must be a nonempty GUID string.");
                if (!ids.Contains(id.ToString())) ids.Add(id.ToString());
            }
            if (!(request["points"] is JObject points))
                throw new ArgumentException("points must be a GUID-to-coordinate object.");
            if ((string)operation == "Update" && points.Count != 0)
                throw new ArgumentException("Update keeps saved placement and does not accept points.");
            var placements = new JObject();
            foreach (var item in points.Properties())
            {
                if (!Guid.TryParse(item.Name, out var id) || !ids.Contains(id.ToString()) || placements[id.ToString()] != null ||
                    !(item.Value is JArray point) || (point.Count != 2 && point.Count != 3))
                    throw new ArgumentException("Placement must name a requested clipping once with two or three coordinates.");
                foreach (var number in point) Finite(number);
                placements[id.ToString()] = point.DeepClone();
            }
            if ((string)operation == "Move" && placements.Count != ids.Count)
                throw new ArgumentException("Move requires a placement point for every clipping GUID.");
            var key = request["request_id"];
            if (key?.Type != JTokenType.String || (!String.IsNullOrEmpty((string)key) && (!Guid.TryParse((string)key, out var requestId) || requestId == Guid.Empty)))
                throw new ArgumentException("request_id must be empty or a nonempty UUID.");
            foreach (var field in new[] { "hatch", "small_details", "include_references" })
                if (request[field]?.Type != JTokenType.Boolean) throw new ArgumentException(field + " must be boolean.");
            double nearWidth = Finite(request["near_width"]), farWidth = Finite(request["far_width"]),
                nearDark = Finite(request["near_dark"]), farDark = Finite(request["far_dark"]);
            if (!(farWidth > 0 && nearWidth >= farWidth && farDark >= 0 && nearDark >= farDark && nearDark <= 100))
                throw new ArgumentException("Require 0 < far_width <= near_width and 0 <= far_dark <= near_dark <= 100.");
            var args = (JObject)request.DeepClone();
            args.Remove("type"); args.Remove("expected_model_path");
            args["clipping_ids"] = new JArray(ids);
            args["points"] = placements;
            return args;
        }

        // Recovery reads stored execution evidence. Only a new mutation needs
        // the current clipping/editor to remain usable; never gate a pending fence on them.
        static void ValidateMutation(RhinoDoc doc, JObject args)
        {
            if (doc.IsReadOnly) throw new ArgumentException("The bound document is read-only.");
            if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                throw new ArgumentException("The bound document is no longer active.");
            var editor = EditingContext.Observe(doc);
            if (editor["stable"]?.Type != JTokenType.Boolean || !(bool)editor["stable"] || (string)editor["mode"] != "model")
                throw new ArgumentException("Finish active commands or editing contexts before changing drawings.");
            foreach (var token in (JArray)args["clipping_ids"])
            {
                var obj = doc.Objects.FindId(Guid.Parse((string)token));
                if (!(obj is ClippingPlaneObject) || obj.IsDeleted || obj.Attributes.IsInstanceDefinitionObject)
                    throw new ArgumentException("A clipping ID does not identify an available document clipping plane.");
            }
        }

        static double Finite(JToken value)
        {
            if (value == null || (value.Type != JTokenType.Integer && value.Type != JTokenType.Float))
                throw new ArgumentException("Coordinates, line widths and darkness must be numbers.");
            double number = (double)value;
            if (Double.IsInfinity(number) || Double.IsNaN(number)) throw new ArgumentException("Numeric values must be finite.");
            return number;
        }

        internal static string Source(out string sha256)
        {
            using (var stream = typeof(PlanSectionTool).Assembly.GetManifestResourceStream(Resource))
            using (var copy = new MemoryStream())
            {
                if (stream == null) throw new InvalidOperationException("The packaged PlanSection algorithm is unavailable.");
                stream.CopyTo(copy);
                byte[] bytes = copy.ToArray();
                using (var hash = SHA256.Create()) sha256 = BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
                return "__name__ = 'almond_plansection_internal'\n" + Encoding.UTF8.GetString(bytes).TrimStart('\uFEFF');
            }
        }

        // ScriptExecutor deliberately accepts CLR data containers, not JTokens.
        // Keep its size/depth/type limits unchanged and let CaptureResult enforce them.
        static object ResultData(JToken token)
        {
            if (token is JObject obj)
                return obj.Properties().ToDictionary(p => p.Name, p => ResultData(p.Value));
            if (token is JArray array)
                return array.Select(ResultData).ToList();
            return ((JValue)token).Value;
        }

        // Summaries carry actual conditions and counts. Output IDs and verbose conflict
        // samples never force a second public tool call or exceed the common result budget.
        static object Deliver(RhinoDoc doc, JObject drawing)
        {
            foreach (var item in (drawing["results"] as JArray ?? new JArray()).OfType<JObject>())
            {
                if (item["object_ids"] is JArray ids)
                {
                    item["output_object_count"] = ids.Count;
                    item.Remove("object_ids");
                }
                if (item["report"] is JObject report)
                {
                    foreach (var property in report.Properties().Where(p => !new[] {
                        "sources", "section", "hatch", "elevation", "metadata_conflict_count", "metadata_conflicts", "cleanup", "skipped"
                    }.Contains(p.Name)).ToArray()) property.Remove();
                }
            }
            if (Encoding.UTF8.GetByteCount(drawing.ToString(Formatting.None)) <= 48000)
                return ResultData(drawing);
            // Preserve conflict samples while they fit; optional detail is reduced
            // before giving up required per-clipping conditions.
            var reports = (drawing["results"] as JArray ?? new JArray()).OfType<JObject>()
                .Select(item => item["report"] as JObject).Where(report => report != null).ToArray();
            foreach (var report in reports)
                if (report["metadata_conflicts"] is JArray conflicts && conflicts.Count != 0)
                {
                    report["metadata_conflicts_omitted_count"] = conflicts.Count;
                    report["metadata_conflicts_truncated"] = true;
                    conflicts.Clear();
                }
            if (Encoding.UTF8.GetByteCount(drawing.ToString(Formatting.None)) <= 48000)
                return ResultData(drawing);
            foreach (var report in reports)
            {
                report.Remove("cleanup"); report.Remove("skipped");
                report["diagnostics_truncated"] = true;
            }
            if (Encoding.UTF8.GetByteCount(drawing.ToString(Formatting.None)) > 48000)
                throw new InvalidOperationException("Required PlanSection response exceeded its preflight budget; completion is uncertain. Inspect the document before continuing.");
            return ResultData(drawing);
        }

        // A client supplies the UUID before dispatch. A completed response can then
        // be replayed after total response loss and a Bridge restart without mutation.
        // Pending/unknown is deliberately a fence, never permission to re-execute.
        static string JournalPath(RhinoDoc doc, string id)
        {
            string root = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(doc.Path)), ".almond");
            string directory = Path.Combine(root, "plan-section-requests");
            foreach (string path in new[] { root, directory })
            {
                if (Directory.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
                    throw new ArgumentException("PlanSection journals cannot traverse links.");
                Directory.CreateDirectory(path);
                if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
                    throw new ArgumentException("PlanSection journals cannot traverse links.");
            }
            string result = Path.Combine(directory, Guid.Parse(id).ToString("N") + ".json");
            if (File.Exists(result) && (File.GetAttributes(result) & FileAttributes.ReparsePoint) != 0)
                throw new ArgumentException("PlanSection journal files cannot be links.");
            return result;
        }

        static string RequestFingerprint(RhinoDoc doc, JObject args, string algorithm)
        {
            var value = (JObject)args.DeepClone();
            value.Remove("request_id");
            value["model_path"] = Path.GetFullPath(doc.Path).ToUpperInvariant();
            value["algorithm_sha256"] = algorithm;
            // JObject property order is canonicalized recursively for semantic retries.
            using (var hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(Canonical(value).ToString(Formatting.None)))).Replace("-", "").ToLowerInvariant();
        }
        static JToken Canonical(JToken token)
        {
            if (token is JObject obj) return new JObject(obj.Properties().OrderBy(p => p.Name, StringComparer.Ordinal).Select(p => new JProperty(p.Name, Canonical(p.Value))));
            if (token is JArray array) return new JArray(array.Select(Canonical));
            return token.DeepClone();
        }
        static void WriteJournal(string path, JObject value, bool create)
        {
            string destination = create ? path : path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                using (var stream = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    byte[] bytes = Encoding.UTF8.GetBytes(value.ToString(Formatting.None));
                    stream.Write(bytes, 0, bytes.Length);
                    stream.Flush(true);
                }
                if (!create) File.Replace(destination, path, null);
            }
            finally
            {
                if (!create && File.Exists(destination)) File.Delete(destination);
            }
        }
        static JObject BeginJournal(RhinoDoc doc, JObject args, string algorithm, out string path, out JObject journal)
        {
            path = null; journal = null;
            string id = (string)args["request_id"];
            if (String.IsNullOrEmpty(id)) return null;
            path = JournalPath(doc, id);
            string fingerprint = RequestFingerprint(doc, args, algorithm);
            journal = new JObject { ["version"] = 1, ["request_id"] = Guid.Parse(id).ToString(), ["fingerprint"] = fingerprint,
                ["model_path"] = Path.GetFullPath(doc.Path), ["document_serial"] = doc.RuntimeSerialNumber,
                ["process_id"] = Process.GetCurrentProcess().Id,
                ["process_start_ticks"] = Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks.ToString(),
                ["state"] = "pending", ["created_utc"] = DateTime.UtcNow.ToString("O") };
            try { WriteJournal(path, journal, true); return null; }
            catch (IOException) when (File.Exists(path))
            {
                string existingPath = path;
                path = null; journal = null; // The caller does not own this existing fence.
                JObject previous;
                try { previous = JObject.Parse(File.ReadAllText(existingPath, Encoding.UTF8)); }
                catch (Exception error)
                {
                    return new JObject { ["status"] = "error", ["error_code"] = "plan_section_request_unreadable",
                        ["request_id"] = id, ["mutation_state"] = "unknown", ["requires_reconciliation"] = true,
                        ["message"] = "Existing request journal cannot be read; the request was not executed again: " + error.Message };
                }
                if ((int?)previous["version"] != 1 || (string)previous["fingerprint"] != fingerprint)
                    throw new ArgumentException("request_id already names a different PlanSection request. Keep the original inputs for response recovery.");
                if (previous["response"] is JObject response)
                {
                    var replay = (JObject)response.DeepClone();
                    replay["response_replayed"] = true;
                    replay["current_output_confirmed"] = false;
                    bool sameInstance = (uint?)previous["document_serial"] == doc.RuntimeSerialNumber &&
                        (int?)previous["process_id"] == Process.GetCurrentProcess().Id &&
                        (string)previous["process_start_ticks"] == Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks.ToString();
                    replay["historical_response"] = !sameInstance;
                    if (!sameInstance) replay["requires_reconciliation"] = true;
                    replay["observation"] = sameInstance
                        ? "Stored execution response; current geometry was not regenerated or re-observed."
                        : "Historical completion from another process/document instance. Unsaved outputs may not exist in the current document; inspect it before continuing. No drawing was regenerated.";
                    return replay;
                }
                return new JObject { ["status"] = "error", ["error_code"] = "plan_section_request_pending",
                    ["request_id"] = id, ["mutation_state"] = "unknown", ["requires_reconciliation"] = true,
                    ["message"] = "This request is pending or its completion was not recorded. It was not executed again. Inspect existing drawings and execution state before deciding how to continue." };
            }
        }

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool entered = false;
            PythonScript python = null;
            object previousDoc = null;
            Action<string> previousOutput = null;
            Dictionary<string, object> previousVariables = null;
            bool contextCaptured = false;
            var diagnostic = new StringBuilder();
            bool diagnosticTruncated = false;
            JObject response = null;
            string journalPath = null;
            JObject journal = null;
            try
            {
                var args = Validate(doc, request);
                string source = Source(out var sha256);
                var replay = BeginJournal(doc, args, sha256, out journalPath, out journal);
                if (replay != null) return replay;
                ValidateMutation(doc, args);
                python = PythonScript.Create();
                if (python == null) throw new InvalidOperationException("Rhino's built-in Python runtime is unavailable; no drawing was changed.");
                previousDoc = python.ScriptContextDoc;
                previousOutput = python.Output;
                previousVariables = python.GetVariableNames().ToDictionary(name => name, name => python.GetVariable(name));
                contextCaptured = true;
                python.ScriptContextDoc = doc;
                // No global search paths, imported module replacement, or process cwd changes.
                python.Output = text =>
                {
                    if (String.IsNullOrEmpty(text)) return;
                    // Retain the tail so a late traceback is not hidden by progress output.
                    if (diagnostic.Length + text.Length > 8192) diagnosticTruncated = true;
                    if (text.Length >= 8192)
                    {
                        diagnostic.Clear();
                        diagnostic.Append(text, text.Length - 8192, 8192);
                    }
                    else
                    {
                        int excess = diagnostic.Length + text.Length - 8192;
                        if (excess > 0) diagnostic.Remove(0, excess);
                        diagnostic.Append(text);
                    }
                };
                if (!python.ExecuteScript(source)) throw new InvalidOperationException("The packaged PlanSection algorithm could not be loaded.");
                python.SetVariable("_almond_doc", doc);
                python.SetVariable("_almond_arguments_json", args.ToString(Formatting.None));
                Validate(doc, request); // Runtime initialization must not stale binding or mutation checks.
                ValidateMutation(doc, args);
                response = JObject.FromObject(new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    entered = true;
                    if (!python.ExecuteScript(Invoke)) throw new InvalidOperationException("PlanSection did not return an execution result.");
                    JObject drawing;
                    using (var reader = new JsonTextReader(new StringReader((string)python.GetVariable("_almond_result_json"))))
                    {
                        reader.DateParseHandling = DateParseHandling.None;
                        drawing = JObject.Load(reader);
                    }
                    drawing["algorithm_sha256"] = sha256;
                    drawing["output"] = "Document";
                    return Deliver(doc, drawing);
                }));
                if ((string)response["status"] != "success" || response["result_error"] != null)
                {
                    response["mutation_state"] = entered ? "unknown" : "not_started";
                    response["requires_reconciliation"] = entered;
                }
                else
                {
                    response["drawing_status"] = response["result"]?["status"]?.DeepClone();
                    bool uncertain = (string)response["result"]?["mutation_state"] == "unknown" ||
                        (bool?)response["result"]?["requires_reconciliation"] == true;
                    response["mutation_state"] = uncertain ? "unknown" : (string)response["drawing_status"] == "completed" ? "completed" : "partial";
                    if (uncertain) response["requires_reconciliation"] = true;
                    if ((string)response["result"]?["mutation_state"] == "not_started")
                    {
                        response["status"] = "error";
                        response.Remove("drawing_status"); // Preflight did not produce a drawing.
                        response["mutation_state"] = "not_started";
                        response["requires_reconciliation"] = false;
                        response["error_code"] = response["result"]?["error_code"]?.DeepClone();
                        response["message"] = response["result"]?["message"]?.DeepClone();
                    }
                }
            }
            catch (Exception error)
            {
                response = new JObject { ["status"] = "error", ["error_code"] = "plan_section_error",
                    ["message"] = error.Message, ["mutation_state"] = entered ? "unknown" : "not_started",
                    ["requires_reconciliation"] = entered };
            }
            finally
            {
                if (python != null && contextCaptured)
                {
                    var errors = new List<string>();
                    Action<string, Action> restore = (label, action) =>
                    {
                        try { action(); }
                        catch (Exception error) { errors.Add(label + ": " + error.Message); }
                    };
                    if (previousVariables != null)
                    {
                        string[] names = null;
                        restore("enumerate namespace", () => names = python.GetVariableNames().ToArray());
                        if (names != null)
                            foreach (string name in names.Where(name => !previousVariables.ContainsKey(name)))
                                restore("remove " + name, () => python.RemoveVariable(name));
                        foreach (var pair in previousVariables)
                            restore("restore " + pair.Key, () => python.SetVariable(pair.Key, pair.Value));
                    }
                    restore("scriptcontext.doc", () => python.ScriptContextDoc = previousDoc);
                    restore("output", () => python.Output = previousOutput);
                    if (errors.Count != 0)
                    {
                        response = response ?? new JObject();
                        response["status"] = "error";
                        response["error_code"] = "plan_section_context_restore_failed";
                        response["context_restore_errors"] = new JArray(errors);
                        response["mutation_state"] = entered ? "unknown" : "not_started";
                        response["requires_reconciliation"] = entered;
                    }
                }
            }
            if ((string)response?["status"] != "success" && diagnostic.Length != 0)
            {
                response["python_diagnostic"] = diagnostic.ToString();
                response["python_diagnostic_truncated"] = diagnosticTruncated;
            }
            if (!String.IsNullOrEmpty((string)request?["request_id"])) response["request_id"] = request["request_id"].DeepClone();
            if (journalPath != null && journal != null)
            {
                try
                {
                    journal["state"] = (string)response["mutation_state"];
                    journal["response"] = response.DeepClone();
                    WriteJournal(journalPath, journal, false);
                }
                catch (Exception error)
                {
                    response["journal_error"] = error.Message;
                    response["requires_reconciliation"] = true;
                    // The initial pending fence remains. A retry cannot regenerate.
                }
            }
            return response;
        }
    }
}
