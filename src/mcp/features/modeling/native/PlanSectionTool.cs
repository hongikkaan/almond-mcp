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
    points=_almond_args['points'], output='Document',
    hatch=_almond_args['hatch'], elevation=_almond_args['elevation'],
    small_details=_almond_args['small_details'],
    near_width=_almond_args['near_width'], far_width=_almond_args['far_width'],
    near_dark=_almond_args['near_dark'], far_dark=_almond_args['far_dark']))
";
        static readonly HashSet<string> Fields = new HashSet<string>(new[] {
            "type", "operation", "clipping_ids", "points", "hatch", "elevation", "small_details",
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
            if (doc.IsReadOnly) throw new ArgumentException("The bound document is read-only.");
            if (RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                throw new ArgumentException("The bound document is no longer active.");
            var editor = EditingContext.Observe(doc);
            if (editor["stable"]?.Type != JTokenType.Boolean || !(bool)editor["stable"] || (string)editor["mode"] != "model")
                throw new ArgumentException("Finish active commands or editing contexts before changing drawings.");
            var operation = request["operation"];
            if (operation?.Type != JTokenType.String || ((string)operation != "Create" && (string)operation != "Update"))
                throw new ArgumentException("PlanSection supports Create or Update Document output.");
            if (!(request["clipping_ids"] is JArray input) || input.Count == 0)
                throw new ArgumentException("Supply a nonempty clipping GUID list.");
            var ids = new List<string>();
            foreach (var token in input)
            {
                if (token.Type != JTokenType.String || !Guid.TryParse((string)token, out var id) || id == Guid.Empty)
                    throw new ArgumentException("Each clipping ID must be a nonempty GUID string.");
                var obj = doc.Objects.FindId(id);
                if (!(obj is ClippingPlaneObject) || obj.IsDeleted || obj.Attributes.IsInstanceDefinitionObject)
                    throw new ArgumentException("A clipping ID does not identify an available document clipping plane.");
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
            foreach (var field in new[] { "hatch", "elevation", "small_details" })
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
                Validate(doc, request); // Runtime initialization must not stale the document/editor check.
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
                    return ResultData(drawing);
                }));
                if ((string)response["status"] != "success" || response["result_error"] != null)
                {
                    response["mutation_state"] = entered ? "unknown" : "not_started";
                    response["requires_reconciliation"] = entered;
                }
                else
                {
                    response["drawing_status"] = response["result"]?["status"]?.DeepClone();
                    response["mutation_state"] = (string)response["drawing_status"] == "completed" ? "completed" : "partial";
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
            return response;
        }
    }
}
