using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
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
        // IronPython 2's ASCII JSON encoder may decode CLR Unicode strings as bytes.
        // Keep the result as Unicode for the .NET JsonTextReader.
        const string Invoke = @"
_almond_args = json.loads(_almond_arguments_json)
_almond_result_json = json.dumps(run(_almond_doc,
    _almond_args['operation'], _almond_args['clipping_ids'],
    points=_almond_args['points'], output='Document',
    hatch=_almond_args['hatch'],
    small_details=_almond_args['small_details'],
    near_width=_almond_args['near_width'], far_width=_almond_args['far_width'],
    near_dark=_almond_args['near_dark'], far_dark=_almond_args['far_dark'],
    include_attachments=_almond_args.get('include_attachments'),
    section_width_source=_almond_args.get('section_width_source', 'source'),
    observe_attachments=_almond_observe_attachments,
    cancellation_token=_almond_deadline_token), ensure_ascii=False)
";
        static readonly HashSet<string> Fields = new HashSet<string>(new[] {
            "type", "operation", "clipping_ids", "points", "hatch", "small_details",
            "near_width", "far_width", "near_dark", "far_dark", "expected_model_path", "include_attachments", "section_width_source" });

        internal static JObject Validate(RhinoDoc doc, JObject request)
        {
            if (request == null || request.Properties().Any(p => !Fields.Contains(p.Name)))
                throw new ArgumentException("PlanSection accepts typed drawing parameters only.");
            var expected = request["expected_model_path"];
            if (expected?.Type != JTokenType.String || String.IsNullOrWhiteSpace((string)expected) ||
                !Path.IsPathRooted((string)expected) || doc == null || String.IsNullOrWhiteSpace(doc.Path) ||
                !String.Equals(Path.GetFullPath(doc.Path), Path.GetFullPath((string)expected), StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("PlanSection requires the bound saved document.");
            if (doc.IsReadOnly) throw new ArgumentException("The bound document is read-only.");
            if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                throw new ArgumentException("The bound document is no longer active.");
            var editor = EditingContext.Observe(doc);
            if (editor["stable"]?.Type != JTokenType.Boolean || !(bool)editor["stable"] || (string)editor["mode"] != "model")
                throw new ArgumentException("Finish active commands or editing contexts before changing drawings.");
            var operation = request["operation"];
            if (operation?.Type != JTokenType.String || !new[] { "Create", "Update", "Move" }.Contains((string)operation))
                throw new ArgumentException("PlanSection supports Create, Update or Move in the bound document.");
            if (!(request["clipping_ids"] is JArray input) || input.Count == 0)
                throw new ArgumentException("Supply a nonempty clipping GUID list.");
            var widthSource = request["section_width_source"];
            if (widthSource != null && (widthSource.Type != JTokenType.String ||
                !new[] { "source", "output_layer" }.Contains((string)widthSource)))
                throw new ArgumentException("section_width_source must be source or output_layer.");
            var includeAttachments = request["include_attachments"];
            if (includeAttachments != null && includeAttachments.Type != JTokenType.Boolean)
                throw new ArgumentException("include_attachments must be boolean or omitted.");
            Func<uint, bool> attachedModel = (bool?)includeAttachments == true && (string)operation != "Move"
                ? ObserveAttachments(doc)
                : null;
            var ids = new List<string>();
            foreach (var token in input)
            {
                if (token.Type != JTokenType.String || !Guid.TryParse((string)token, out var id) || id == Guid.Empty)
                    throw new ArgumentException("Each clipping ID must be a nonempty GUID string.");
                var obj = doc.Objects.FindId(id);
                if (!(obj is ClippingPlaneObject) || obj.IsDeleted || obj.Attributes.IsInstanceDefinitionObject)
                    throw new ArgumentException("A clipping ID does not identify an available clipping plane.");
                if (obj.IsReference)
                {
                    attachedModel ??= ObserveAttachments(doc);
                    if (!attachedModel(obj.ReferenceModelSerialNumber))
                        throw new ArgumentException("A reference clipping must belong to a current Worksession attachment.");
                }
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
            foreach (var field in new[] { "hatch", "small_details" })
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

        static Func<uint, bool> ObserveAttachments(RhinoDoc doc)
        {
            var warnings = new JArray();
            if (!(WorksessionObservation.Read(doc, warnings) is JArray rows))
                throw new InvalidOperationException("Cannot verify current Worksession attachments. " + String.Join(" ", warnings.Values<string>()));

            var paths = new HashSet<string>(rows.Select(row => (string)row["file_path"]), StringComparer.OrdinalIgnoreCase);
            var bySerial = new Dictionary<uint, bool>();
            var worksession = doc.Worksession;
            return serial =>
            {
                if (serial == 0 || paths.Count == 0) return false;
                if (!bySerial.TryGetValue(serial, out var included))
                {
                    string path = worksession.ModelPathFromSerialNumber(serial);
                    if (String.IsNullOrWhiteSpace(path) || !Path.IsPathFullyQualified(path))
                        throw new InvalidOperationException($"Cannot resolve Worksession reference model serial {serial} to a full path.");
                    included = paths.Contains(Path.GetFullPath(path));
                    bySerial.Add(serial, included);
                }
                return included;
            };
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

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            // The timer can signal while the Rhino UI thread is inside a native call.
            // ScriptExecutor keeps its Undo record until the synchronous action exits.
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(120));
            bool entered = false;
            PythonScript python = null;
            object previousDoc = null;
            Action<string> previousOutput = null;
            Dictionary<string, object> previousVariables = null;
            bool contextCaptured = false;
            var diagnostic = new StringBuilder();
            bool diagnosticTruncated = false;
            JObject response = null;
            try
            {
                var args = Validate(doc, request);
                string source = Source(out var sha256);
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
                python.SetVariable("_almond_deadline_token", deadline.Token);
                python.SetVariable("_almond_observe_attachments", new Func<Func<uint, bool>>(() => ObserveAttachments(doc)));
                Validate(doc, request); // Runtime initialization must not stale the document/editor check.
                JObject drawing = null;
                response = JObject.FromObject(new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    entered = true;
                    if (!python.ExecuteScript(Invoke)) throw new InvalidOperationException("PlanSection did not return an execution result.");
                    using (var reader = new JsonTextReader(new StringReader((string)python.GetVariable("_almond_result_json"))))
                    {
                        reader.DateParseHandling = DateParseHandling.None;
                        drawing = JObject.Load(reader);
                    }
                    drawing["algorithm_sha256"] = sha256;
                    drawing["output"] = "Document";
                    // The fixed algorithm returns detached JSON. ScriptExecutor still owns Undo
                    // and limits results from its general-purpose execution paths.
                    return null;
                }));
                if ((string)response["status"] != "success")
                {
                    response["mutation_state"] = entered ? "unknown" : "not_started";
                    response["requires_reconciliation"] = entered;
                    if (drawing?["results"] is JArray observed)
                    {
                        // The callback returned, but the outer Undo operation failed.
                        // IDs are observations before Undo; only untouched cuts retain a final status.
                        var cuts = new JArray();
                        foreach (var item in observed.OfType<JObject>())
                        {
                            var evidence = new JObject();
                            foreach (string key in new[] { "clipping_id", "name", "object_ids", "error", "cleanup_error", "recovery" })
                                if (item[key] != null) evidence[key] = item[key].DeepClone();
                            evidence["status"] = (string)item["status"] == "not_started" ? "not_started" : "unconfirmed";
                            cuts.Add(evidence);
                        }
                        response["result"] = new JObject { ["status"] = "unconfirmed",
                            ["requested"] = drawing["requested"], ["results"] = cuts };
                    }
                }
                else
                {
                    response["result"] = drawing;
                    response["drawing_status"] = drawing["status"]?.DeepClone();
                    response["mutation_state"] = (string)response["drawing_status"] == "completed" ? "completed" : "partial";
                    if ((string)response["drawing_status"] == "cancelled" && (int?)drawing["completed"] == 0 &&
                        drawing["results"] is JArray cuts && cuts.All(cut =>
                            (string)cut["status"] == "not_started" || (string)cut["status"] == "cancelled"))
                        response["mutation_state"] = "not_started";
                    response["requires_reconciliation"] = (bool?)drawing["requires_reconciliation"] ?? false;
                    if ((bool)response["requires_reconciliation"])
                    {
                        var recovery = (drawing["results"] as JArray)?.OfType<JObject>()
                            .Where(item => item["recovery"] != null).ToArray() ?? new JObject[0];
                        response["recovery"] = new JArray(recovery.Select(item => item.DeepClone()));
                        response["mutation_state"] = recovery.Any(item => (string)item["recovery"]?["mutation_state"] == "partial")
                            ? "partial" : "unknown";
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
                        response.Remove("drawing_status"); // Only the per-cut evidence survived cleanup.
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
            return response;
        }
    }
}
