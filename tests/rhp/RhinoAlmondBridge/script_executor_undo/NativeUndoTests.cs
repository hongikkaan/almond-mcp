using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    // Runs the linked production executor against Rhino's real native Undo stack.
    // Invoke from a modeless UI callback in Rhino, not from a command RunCommand.
    public static class NativeUndoTests
    {
        public static string RunAll()
        {
            var lines = new List<string>();

            Run(lines, "successful script is one Undo/Redo operation", doc =>
            {
                var result = Execute(doc, "var id = doc.Objects.AddPoint(Point3d.Origin); return new List<Guid> { id };");
                Check(result.Status == "success", result.Message);
                var id = Guid.Parse(result.Guids.Single());
                Check(Live(doc, id), "Successful script did not create its point.");
                Idle(doc);
                Undo(doc);
                Check(!Live(doc, id) && Count(doc) == 0, "Undo left successful script objects.");
                Check(doc.Layers.FindName("A-WALL") == null, "Layer initialization was outside the script record.");
                Redo(doc);
                Check(Live(doc, id), "Redo did not restore the successful script.");
            });

            Run(lines, "partial creation rolls back and later Delete/Undo/Redo works", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                int before = Count(doc);
                Failed(Execute(doc, "doc.Objects.AddPoint(new Point3d(10, 0, 0)); throw new InvalidOperationException(\"expected\");"));
                Check(Live(doc, previous) && Count(doc) == before, "Rollback changed previous work or left new geometry.");
                DeleteUndoRedo(doc, previous);
            });

            Run(lines, "empty failure preserves previous work and adds no Undo step", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                Failed(Execute(doc, "throw new InvalidOperationException(\"expected\");"));
                Check(Live(doc, previous), "Empty failure undid the previous successful action.");
                Idle(doc);
                Undo(doc);
                Check(!Live(doc, previous), "An empty failure added an extra Undo step.");
                Redo(doc);
                Check(Live(doc, previous), "Previous action lost its Redo.");
            });

            Run(lines, "failed deletion restores the existing object", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                Failed(Execute(doc, "doc.Objects.Delete(new Guid(\"" + previous + "\"), true); throw new InvalidOperationException(\"expected\");"));
                Check(Live(doc, previous), "Failed deletion was not rolled back.");
                Idle(doc);
            });

            Run(lines, "failed attribute edit restores the existing attributes", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                string originalName = doc.Objects.FindId(previous).Attributes.Name;
                Failed(Execute(doc, "var id = new Guid(\"" + previous + "\"); var a = doc.Objects.FindId(id).Attributes.Duplicate(); a.Name = \"temporary\"; doc.Objects.ModifyAttributes(id, a, true); throw new InvalidOperationException(\"expected\");"));
                Check(doc.Objects.FindId(previous).Attributes.Name == originalName, "Failed attribute edit was not rolled back.");
                Idle(doc);
            });

            Run(lines, "reflection invocation failure preserves previous work", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                var result = new ScriptExecutor().Execute("public class Script { public static void Run() {} }", doc);
                Check(result.Status == "runtime_error", "Invalid Run arguments did not fail.");
                Check(Live(doc, previous), "Generic exception recovery undid previous work.");
                Idle(doc);
            });

            Run(lines, "first-call failure rolls back layers and next call recreates them", doc =>
            {
                Failed(Execute(doc, "doc.Objects.AddPoint(Point3d.Origin); throw new InvalidOperationException(\"expected\");"));
                Check(Count(doc) == 0, "First-call failure left geometry.");
                Check(doc.Layers.FindName("A-WALL") == null, "First-call failure left created layers.");
                Idle(doc);
                Prepare(doc);
                Check(doc.Layers.FindName("A-WALL") != null, "Layer initialization stayed incorrectly cached after rollback.");
            });

            Run(lines, "compile error does not initialize layers or history", doc =>
            {
                int layers = doc.Layers.Count;
                var result = new ScriptExecutor().Execute("this is not C#;", doc);
                Check(result.Status == "compile_error", "Expected compilation failure.");
                Check(doc.Layers.Count == layers && Count(doc) == 0, "Compilation failure changed the document.");
                Idle(doc);
            });

            Run(lines, "missing entry point does not initialize layers or history", doc =>
            {
                int layers = doc.Layers.Count;
                var result = new ScriptExecutor().Execute("public class MissingEntry {}", doc);
                Check(result.Status == "error", "Missing Run method was accepted.");
                Check(doc.Layers.Count == layers && Count(doc) == 0, "Entry validation changed the document.");
                Idle(doc);
            });

            Run(lines, "caller-owned record is neither joined nor closed", doc =>
            {
                uint owner = doc.BeginUndoRecord("caller-owned");
                Check(owner != 0, "Could not create caller's record.");
                var previous = doc.Objects.AddPoint(Point3d.Origin);
                var result = Execute(doc, "doc.Objects.AddPoint(new Point3d(10, 0, 0)); return new List<Guid>();");
                Check(result.Status == "error", "Script executed without owning a record.");
                Check(doc.CurrentUndoRecordSerialNumber == owner && doc.UndoRecordingIsActive, "Executor closed caller's record.");
                Check(Count(doc) == 1 && Live(doc, previous), "Rejected script changed caller's document.");
                Check(doc.Layers.FindName("A-WALL") == null, "Rejected script initialized layers.");
                Check(doc.EndUndoRecord(owner), "Could not finish caller's record.");
                Undo(doc);
                Check(!Live(doc, previous), "Caller lost its Undo history.");
            });

            Run(lines, "disabled Undo rejects execution before document changes", doc =>
            {
                doc.UndoRecordingEnabled = false;
                int layers = doc.Layers.Count;
                var result = Execute(doc, "doc.Objects.AddPoint(Point3d.Origin); return new List<Guid>();");
                Check(result.Status == "error", "Script ran with Undo disabled.");
                Check(!doc.UndoRecordingEnabled && Count(doc) == 0 && doc.Layers.Count == layers, "Rejected script changed the document or Undo setting.");
                Idle(doc);
            });

            Run(lines, "empty failure preserves an existing Redo chain", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                Undo(doc);
                Failed(Execute(doc, "throw new InvalidOperationException(\"expected\");"));
                Idle(doc);
                Redo(doc);
                Check(Live(doc, previous), "Empty failure destroyed the existing Redo.");
            });

            Run(lines, "successful no-op preserves an existing Redo chain", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                Undo(doc);
                Prepare(doc);
                Redo(doc);
                Check(Live(doc, previous), "Successful no-op destroyed the existing Redo.");
            });

            Run(lines, "script-closed record cannot roll back earlier work", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                var result = Execute(doc, "doc.EndUndoRecord(doc.CurrentUndoRecordSerialNumber); throw new InvalidOperationException(\"expected\");");
                Check(result.Status == "runtime_error" && result.Message.Contains("protect other work"), "Lost record ownership was not reported.");
                Check(Live(doc, previous), "Executor undid earlier work after losing its record.");
                Idle(doc);
            });

            Run(lines, "script-created replacement record stays under script ownership", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                var result = Execute(doc, "doc.EndUndoRecord(doc.CurrentUndoRecordSerialNumber); doc.BeginUndoRecord(\"replacement\"); doc.Objects.AddPoint(new Point3d(10, 0, 0)); throw new InvalidOperationException(\"expected\");");
                Check(result.Status == "runtime_error" && result.Message.Contains("protect other work"), "Replacement record was not reported.");
                Check(doc.UndoRecordingIsActive && Count(doc) == 2 && Live(doc, previous), "Executor changed or closed the replacement record.");
                Check(doc.EndUndoRecord(doc.CurrentUndoRecordSerialNumber), "Test could not close its replacement record.");
                Undo(doc);
                Check(Count(doc) == 1 && Live(doc, previous), "Replacement record lost its own Undo.");
            });

            Run(lines, "void Run remains supported and undoable", doc =>
            {
                Prepare(doc);
                var result = new ScriptExecutor().Execute("public class Script { public static void Run(RhinoDoc doc) { doc.Objects.AddPoint(Point3d.Origin); } }", doc);
                Check(result.Status == "success" && Count(doc) == 1, "Existing void Run compatibility changed.");
                Idle(doc);
                Undo(doc);
                Check(Count(doc) == 0, "Void Run changes were not undoable.");
            });

            Run(lines, "immediate Redo cannot replay a failed creation", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                Failed(Execute(doc, "doc.Objects.AddPoint(new Point3d(10, 0, 0)); throw new InvalidOperationException(\"expected\");"));
                Check(Count(doc) == 1 && Live(doc, previous), "Failed creation was not rolled back.");
                bool redone = TryRedo(doc);
                Check(!redone && Count(doc) == 1 && Live(doc, previous), "Immediate Redo replayed the failed creation.");
            });

            Run(lines, "immediate Redo cannot replay a failed deletion", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                Failed(Execute(doc, "doc.Objects.Delete(new Guid(\"" + previous + "\"), true); throw new InvalidOperationException(\"expected\");"));
                Check(Live(doc, previous), "Failed deletion was not rolled back.");
                bool redone = TryRedo(doc);
                Check(!redone && Count(doc) == 1 && Live(doc, previous), "Immediate Redo replayed the failed deletion.");
            });

            Run(lines, "immediate Redo cannot replay a failed attribute edit", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                string originalName = doc.Objects.FindId(previous).Attributes.Name;
                Failed(Execute(doc, "var id = new Guid(\"" + previous + "\"); var a = doc.Objects.FindId(id).Attributes.Duplicate(); a.Name = \"temporary\"; doc.Objects.ModifyAttributes(id, a, true); throw new InvalidOperationException(\"expected\");"));
                Check(doc.Objects.FindId(previous).Attributes.Name == originalName, "Failed attribute edit was not rolled back.");
                bool redone = TryRedo(doc);
                Check(!redone && doc.Objects.FindId(previous).Attributes.Name == originalName, "Immediate Redo replayed the failed attribute edit.");
            });

            Run(lines, "immediate Redo cannot replay failed first-call layer initialization", doc =>
            {
                Failed(Execute(doc, "throw new InvalidOperationException(\"expected\");"));
                Check(Count(doc) == 0 && doc.Layers.FindName("A-WALL") == null, "First-call layer initialization was not rolled back.");
                bool redone = TryRedo(doc);
                Check(!redone && Count(doc) == 0 && doc.Layers.FindName("A-WALL") == null, "Immediate Redo replayed failed first-call layer initialization.");
            });

            Run(lines, "nonempty failure preserves two earlier Undo/Redo records", doc =>
            {
                Prepare(doc);
                var first = Seed(doc);
                var second = Seed(doc);
                Failed(Execute(doc, "doc.Objects.AddPoint(new Point3d(10, 0, 0)); throw new InvalidOperationException(\"expected\");"));
                Check(Count(doc) == 2 && Live(doc, first) && Live(doc, second), "Failure changed earlier work.");
                Check(!TryRedo(doc), "Failed script remained available to Redo.");
                Undo(doc);
                Check(Count(doc) == 1 && Live(doc, first) && !Live(doc, second), "First Undo did not remove only the second successful object.");
                Undo(doc);
                Check(Count(doc) == 0 && !Live(doc, first) && !Live(doc, second), "Second Undo did not remove the first successful object.");
                Redo(doc);
                Check(Count(doc) == 1 && Live(doc, first) && !Live(doc, second), "First Redo did not restore only the first successful object.");
                Redo(doc);
                Check(Count(doc) == 2 && Live(doc, first) && Live(doc, second), "Second Redo did not restore only the two successful objects.");
                Check(!TryRedo(doc) && Count(doc) == 2, "Failed geometry survived beyond the earlier successful Redo records.");
            });

            RunResultCases(lines);

            string report = "Rhino " + RhinoApp.Version + "\n" + string.Join("\n", lines);
            int failures = lines.Count(line => line.StartsWith("FAIL "));
            if (failures != 0)
                throw new InvalidOperationException(report + "\n" + failures + " test(s) failed.");

            return report + "\nPASS: " + lines.Count + "/" + lines.Count + " native Undo regression cases.";
        }

        private static void RunResultCases(List<string> lines)
        {
            Run(lines, "structured returned data survives final response serialization", doc =>
            {
                var result = ExecuteValue(doc,
                    "return new { label = \"한글 \\\"quoted\\\"\\nline\", enabled = true, " +
                    "count = 17, distance = 12.5, missing = (object)null, " +
                    "id = new Guid(\"11111111-2222-3333-4444-555555555555\"), " +
                    "coordinates = new[] { 1.25, -2.5, 3.0 }, nested = new { reason = \"kept\" } };");
                var wire = Wire(result);
                Check(result.Status == "success" && !HasResultError(wire), result.Message);
                var data = wire["result"] as JObject;
                Check(data != null, "The returned object was not included in the JSON response.");
                Check((string)data["label"] == "한글 \"quoted\"\nline", "Unicode, quotes or newlines were changed.");
                Check((bool)data["enabled"] && (int)data["count"] == 17 && (double)data["distance"] == 12.5,
                    "Primitive values changed during result conversion.");
                Check(data["missing"] != null && data["missing"].Type == JTokenType.Null, "Nested null was lost.");
                Check((string)data["id"] == "11111111-2222-3333-4444-555555555555", "A data GUID did not survive JSON serialization.");
                Check(((JArray)data["coordinates"]).Values<double>().SequenceEqual(new[] { 1.25, -2.5, 3.0 }),
                    "Returned coordinates changed.");
                Check((string)data["nested"]["reason"] == "kept", "Nested data was lost.");
                Check(((JArray)wire["guids"]).Count == 0, "Data was misinterpreted as created GUIDs.");
            });

            Run(lines, "shared acyclic objects are not rejected as a reference cycle", doc =>
            {
                var wire = Wire(ExecuteValue(doc,
                    "var child = new Dictionary<string, object> { { \"value\", 23 } }; " +
                    "return new Dictionary<string, object> { { \"left\", child }, { \"right\", child } };"));
                Check((string)wire["status"] == "success" && !HasResultError(wire), "A shared child was treated as a cycle.");
                Check((int)wire["result"]["left"]["value"] == 23 && (int)wire["result"]["right"]["value"] == 23,
                    "A shared acyclic value was omitted.");
            });

            Run(lines, "returned data is detached from the script-owned object graph", doc =>
            {
                string typeName = "ReturnedValueFixture_" + Guid.NewGuid().ToString("N");
                string source = "public class " + typeName + " { " +
                    "public static Dictionary<string, object> Shared = new Dictionary<string, object> { " +
                    "{ \"marker\", \"before\" }, { \"values\", new List<object> { 1, 2 } } }; " +
                    "public static object Run(RhinoDoc doc) { return Shared; } }";
                var result = new ScriptExecutor().Execute(source, doc);
                var before = Wire(result);
                Check(result.Status == "success" && !HasResultError(before), "The detachable fixture result failed.");
                var scriptType = AppDomain.CurrentDomain.GetAssemblies()
                    .Select(assembly => assembly.GetType(typeName, false)).FirstOrDefault(type => type != null);
                Check(scriptType != null, "Could not locate the fixture's script-owned data.");
                var shared = (Dictionary<string, object>)scriptType.GetField("Shared").GetValue(null);
                shared["marker"] = "after";
                ((List<object>)shared["values"])[0] = 99;
                var after = Wire(result);
                Check(JToken.DeepEquals(before["result"], after["result"]), "Later script-owned mutations changed the saved result.");
                Check((string)after["result"]["marker"] == "before" && (int)after["result"]["values"][0] == 1,
                    "The returned graph was not copied at execution time.");
            });

            Run(lines, "explicit null and void never reuse a previous returned value", doc =>
            {
                var executor = new ScriptExecutor();
                var first = Wire(ExecuteValue(doc, "return new { marker = \"previous\" };", null, executor));
                Check((string)first["result"]["marker"] == "previous", "The seed returned value was not available.");
                var empty = Wire(ExecuteValue(doc, "return null;", null, executor));
                Check((string)empty["status"] == "success" && !HasResultError(empty), "Explicit null was rejected.");
                NoReturnedData(empty);
                var noReturn = Wire(executor.Execute("public class Script { public static void Run(RhinoDoc doc) { } }", doc));
                Check((string)noReturn["status"] == "success" && !HasResultError(noReturn), "Legacy void execution changed.");
                NoReturnedData(noReturn);
            });

            Run(lines, "legacy GUID result remains serialized and undoable", doc =>
            {
                var result = Execute(doc, "var id = doc.Objects.AddPoint(Point3d.Origin); return new List<Guid> { id };");
                var wire = Wire(result);
                Check(result.Status == "success" && !HasResultError(wire), result.Message);
                Check(((JArray)wire["guids"]).Count == 1, "Legacy GUID array was lost.");
                NoReturnedData(wire);
                var id = Guid.Parse((string)wire["guids"][0]);
                Check(result.Guids.Single() == id.ToString() && Live(doc, id), "Serialized GUID does not identify the created object.");
                Undo(doc);
                Check(!Live(doc, id), "Legacy returned GUID creation was not undoable.");
                Redo(doc);
                Check(Live(doc, id), "Legacy returned GUID creation lost Redo.");
            });

            Run(lines, "returned JSON permits the 64 KiB UTF-8 boundary", doc =>
            {
                var wire = Wire(ExecuteValue(doc, "return new string('x', 65534);"));
                Check((string)wire["status"] == "success" && !HasResultError(wire), "A 65536-byte JSON string was rejected.");
                var value = wire["result"];
                Check(value != null && value.Type == JTokenType.String && ((string)value).Length == 65534,
                    "The boundary result was truncated or missing.");
                Check(Encoding.UTF8.GetByteCount(value.ToString(Formatting.None)) == 65536,
                    "The boundary fixture is not exactly 64 KiB of JSON.");
            });

            Run(lines, "oversized returned JSON reports conversion failure without rollback", doc =>
                ConversionErrorKeepsEdit(doc, "return new string('x', 65535);"));

            Run(lines, "result size is measured in UTF-8 bytes rather than characters", doc =>
                ConversionErrorKeepsEdit(doc, "return new string('한', 21845);"));

            Run(lines, "result size includes JSON escaping", doc =>
                ConversionErrorKeepsEdit(doc, "return new string('\"', 32768);"));

            Run(lines, "a cyclic result cannot escape into final response serialization", doc =>
                ConversionErrorKeepsEdit(doc,
                    "var value = new Dictionary<string, object>(); value[\"self\"] = value; return value;"));

            Run(lines, "sixteen nested JSON containers remain within the depth limit", doc =>
            {
                var wire = Wire(ExecuteValue(doc,
                    "object value = 7; for (int i = 0; i < 16; i++) value = new object[] { value }; return value;"));
                Check((string)wire["status"] == "success" && !HasResultError(wire), "The allowed container depth of sixteen was rejected.");
                var value = wire["result"];
                for (int i = 0; i < 16; i++)
                {
                    Check(value is JArray && ((JArray)value).Count == 1, "The nested boundary value was truncated.");
                    value = value[0];
                }
                Check(value.Type == JTokenType.Integer && (int)value == 7, "The deepest allowed value was changed.");
            });

            Run(lines, "seventeen nested JSON containers report conversion failure without rollback", doc =>
                ConversionErrorKeepsEdit(doc,
                    "object value = 1; for (int i = 0; i < 17; i++) value = new object[] { value }; return value;"));

            Run(lines, "unsupported returned objects are rejected before invoking their getters", doc =>
            {
                string typeName = "RejectedReturnedValue_" + Guid.NewGuid().ToString("N");
                ConversionErrorKeepsEdit(doc, "return new " + typeName + "();",
                    "public class " + typeName + " { public static int GetterCalls; " +
                    "public string Value { get { GetterCalls++; throw new InvalidOperationException(\"getter-fixture\"); } } }");
                var scriptType = AppDomain.CurrentDomain.GetAssemblies()
                    .Select(assembly => assembly.GetType(typeName, false)).FirstOrDefault(type => type != null);
                Check(scriptType != null, "Could not locate the unsupported result fixture.");
                Check((int)scriptType.GetField("GetterCalls").GetValue(null) == 0,
                    "Result conversion invoked an unsupported object's getter.");
            });

            foreach (var expression in new[] { "double.NaN", "double.PositiveInfinity", "double.NegativeInfinity" })
            {
                var nonFinite = expression;
                Run(lines, "non-finite result is rejected: " + nonFinite, doc =>
                    ConversionErrorKeepsEdit(doc, "return new { value = " + nonFinite + " };"));
            }

            Run(lines, "execution exception rolls back and clears returned data", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                var executor = new ScriptExecutor();
                var first = Wire(ExecuteValue(doc, "return new { marker = \"previous\" };", null, executor));
                Check((string)first["result"]["marker"] == "previous", "Could not seed prior result.");
                var failed = ExecuteValue(doc,
                    "doc.Objects.AddPoint(new Point3d(10, 0, 0)); throw new InvalidOperationException(\"expected\");",
                    null, executor);
                Failed(failed);
                var wire = Wire(failed);
                NoReturnedData(wire);
                Check(!HasResultError(wire), "Execution failure was confused with result conversion failure.");
                Check(!string.IsNullOrEmpty((string)wire["error_trace"]) &&
                    ((string)wire["error_trace"]).Contains("InvalidOperationException"), "Execution exception trace was lost.");
                Check(Count(doc) == 1 && Live(doc, previous), "Object-returning failure did not roll back its edit.");
                Check(!TryRedo(doc), "Failed object-returning execution survived on Redo.");
                DeleteUndoRedo(doc, previous);
            });

            Run(lines, "compile failure never carries data from a previous execution", doc =>
            {
                Prepare(doc);
                var executor = new ScriptExecutor();
                var first = Wire(ExecuteValue(doc, "return new { marker = \"previous\" };", null, executor));
                Check((string)first["result"]["marker"] == "previous", "Could not seed prior result.");
                uint nextUndo = doc.NextUndoRecordSerialNumber;
                int count = Count(doc), layers = doc.Layers.Count;
                var wire = Wire(executor.Execute("this is not C#;", doc));
                Check((string)wire["status"] == "compile_error", "Invalid source did not produce a compile error.");
                NoReturnedData(wire);
                Check(!HasResultError(wire), "Compile failure was confused with result conversion failure.");
                Check(Count(doc) == count && doc.Layers.Count == layers && doc.NextUndoRecordSerialNumber == nextUndo,
                    "Compilation failure changed the document or history.");
            });

            Run(lines, "Undo ownership failure clears already collected result data", doc =>
            {
                Prepare(doc);
                var previous = Seed(doc);
                var result = ExecuteValue(doc,
                    "doc.EndUndoRecord(doc.CurrentUndoRecordSerialNumber); return new { marker = \"must-not-escape\" };");
                var wire = Wire(result);
                Check(result.Status == "runtime_error" && result.Message.Contains("protect other work"),
                    "Lost Undo ownership was not reported.");
                NoReturnedData(wire);
                Check(!HasResultError(wire), "Undo failure was confused with result conversion failure.");
                Check(((JArray)wire["guids"]).Count == 0 && Count(doc) == 1 && Live(doc, previous),
                    "Undo failure exposed stale IDs or changed prior work.");
                Idle(doc);
                Undo(doc);
                Check(!Live(doc, previous), "Lost ownership damaged the previous successful record.");
            });
        }

        private static ScriptResult ExecuteValue(RhinoDoc doc, string body, string supportingTypes = null,
            ScriptExecutor executor = null)
        {
            string source = "public class Script { public static object Run(RhinoDoc doc) { " + body + " } } " +
                (supportingTypes ?? "");
            return (executor ?? new ScriptExecutor()).Execute(source, doc);
        }

        private static JObject Wire(ScriptResult result)
        {
            // Match BridgeServer's final serialization, not only ScriptResult properties.
            var wire = JObject.Parse(JsonConvert.SerializeObject(result));
            Check((string)wire["status"] == result.Status && (string)wire["message"] == result.Message,
                "Existing status/message fields changed during serialization.");
            var guids = wire["guids"] as JArray;
            Check(guids != null && guids.Values<string>().SequenceEqual(result.Guids),
                "Existing GUID field changed during serialization.");
            return wire;
        }

        private static bool HasResultError(JObject wire)
        {
            var error = wire["result_error"];
            return error != null && error.Type == JTokenType.String && !string.IsNullOrWhiteSpace((string)error);
        }

        private static void NoReturnedData(JObject wire)
        {
            Check(wire.Property("result") == null, "A failed, empty or legacy execution exposed a result field.");
        }

        private static void ConversionErrorKeepsEdit(RhinoDoc doc, string body, string supportingTypes = null)
        {
            Prepare(doc);
            var previous = Seed(doc);
            var before = doc.Objects.GetObjectList(ObjectType.AnyObject).Select(obj => obj.Id).ToArray();
            var result = ExecuteValue(doc, "doc.Objects.AddPoint(new Point3d(10, 0, 0)); " + body, supportingTypes);
            var wire = Wire(result);
            Check(result.Status == "success" && HasResultError(wire), "Result conversion failure changed execution success or was hidden.");
            Check(string.IsNullOrEmpty(result.ErrorTrace), "Result conversion failure overwrote the execution exception channel.");
            NoReturnedData(wire);
            Check(((JArray)wire["guids"]).Count == 0, "Non-GUID result conversion produced stale object IDs.");
            var added = doc.Objects.GetObjectList(ObjectType.AnyObject).Select(obj => obj.Id).Except(before).ToArray();
            Check(added.Length == 1 && Count(doc) == before.Length + 1 && Live(doc, previous),
                "Result conversion failure rolled back or changed the successful edit.");
            Idle(doc);
            Undo(doc);
            Check(Count(doc) == before.Length && !Live(doc, added[0]) && Live(doc, previous),
                "The successful edit lost its own Undo after a result conversion error.");
            Redo(doc);
            Check(Live(doc, added[0]) && Live(doc, previous), "The successful edit lost its Redo after a result conversion error.");
        }

        private static void Run(List<string> lines, string name, Action<RhinoDoc> test)
        {
            using (var doc = RhinoDoc.CreateHeadless(null))
            {
                doc.UndoRecordingEnabled = true;
                try
                {
                    test(doc);
                    Idle(doc);
                    lines.Add("PASS " + name);
                }
                catch (Exception ex)
                {
                    lines.Add("FAIL " + name + ": " + ex);
                }
            }
        }

        private static ScriptResult Execute(RhinoDoc doc, string body)
        {
            string source = "public class Script { public static List<Guid> Run(RhinoDoc doc) { " + body + " } }";
            return new ScriptExecutor().Execute(source, doc);
        }

        private static void Prepare(RhinoDoc doc)
        {
            var result = Execute(doc, "return new List<Guid>();");
            Check(result.Status == "success", result.Message);
            Idle(doc);
        }

        private static Guid Seed(RhinoDoc doc)
        {
            uint sn = doc.BeginUndoRecord("previous successful point");
            Check(sn != 0, "Could not start seed record.");
            var id = doc.Objects.AddPoint(Point3d.Origin);
            Check(id != Guid.Empty && doc.EndUndoRecord(sn), "Could not finish seed record.");
            return id;
        }

        private static void Failed(ScriptResult result)
        {
            Check(result.Status == "runtime_error" && result.Message == "expected", "Unexpected failure result: " + result.Message);
            Check(result.Guids.Count == 0, "Failure returned stale object IDs.");
        }

        private static bool Live(RhinoDoc doc, Guid id)
        {
            var obj = doc.Objects.FindId(id);
            return obj != null && !obj.IsDeleted;
        }

        private static int Count(RhinoDoc doc)
        {
            return doc.Objects.GetObjectList(ObjectType.AnyObject).Count();
        }

        private static void Idle(RhinoDoc doc)
        {
            Check(!doc.UndoActive && !doc.RedoActive && !doc.UndoRecordingIsActive &&
                doc.CurrentUndoRecordSerialNumber == 0, "Undo/Redo operation or record was left active.");
        }

        private static void Undo(RhinoDoc doc) { UndoOrRedo(doc, false); }
        private static void Redo(RhinoDoc doc) { UndoOrRedo(doc, true); }

        private static void UndoOrRedo(RhinoDoc doc, bool redo)
        {
            // These are modeless native calls as well. Check BEFORE cleanup so
            // the test cannot hide a record leaked by the production executor.
            Idle(doc);
            uint sn = doc.NextUndoRecordSerialNumber;
            try
            {
                Check(redo ? doc.Redo() : doc.Undo(), redo ? "Redo failed." : "Undo failed.");
            }
            finally
            {
                if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == sn)
                    Check(doc.EndUndoRecord(sn), "Could not finish the test's Undo/Redo.");
            }
            Idle(doc);
        }

        private static void DeleteUndoRedo(RhinoDoc doc, Guid id)
        {
            Idle(doc);
            uint sn = doc.BeginUndoRecord("later manual deletion");
            Check(sn != 0, "Later Delete could not start an Undo record.");
            Check(doc.Objects.Delete(id, true) && doc.EndUndoRecord(sn), "Later Delete failed.");
            Check(!Live(doc, id), "Delete left the point live.");
            Undo(doc);
            Check(Live(doc, id), "Later Undo did not restore the deleted point.");
            Redo(doc);
            Check(!Live(doc, id), "Later Redo did not delete the point again.");
        }

        private static bool TryRedo(RhinoDoc doc)
        {
            Idle(doc);
            uint sn = doc.NextUndoRecordSerialNumber;
            bool redone;
            try
            {
                // Do not make another edit before this call: an edit would clear
                // Redo itself and hide a failed script left by the executor.
                redone = doc.Redo();
            }
            finally
            {
                if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == sn)
                    Check(doc.EndUndoRecord(sn), "Could not finish the test's immediate Redo.");
            }
            Idle(doc);
            return redone;
        }

        private static void Check(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
