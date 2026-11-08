using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    // Shared unchanged result contract, also linked by offline adapter tests.
    public partial class ScriptExecutor
    {
        private static void SetRuntimeError(ScriptResult result, Exception ex)
        {
            result.Result = null;
            result.ResultError = null;
            result.Status = "runtime_error";
            result.Message = ex.Message;
            result.ErrorTrace = ex.ToString();
            result.Guids.Clear();
        }

        private const int MaxResultBytes = 64 * 1024;
        private const int MaxResultDepth = 16;
        private const string ResultErrorNotice =
            " The script already completed. Any model changes have already been applied " +
            "and were not rolled back. Do not retry automatically.";

        private static void CaptureResult(ScriptResult result, object value)
        {
            result.Result = null;
            result.ResultError = null;
            if (value == null)
                return;
            try
            {
                var detached = new ResultProjector().Project(value, 0);
                // This serialization is bounded by the incremental budget below and
                // only visits detached JSON values, never user properties again.
                if (Encoding.UTF8.GetByteCount(detached.ToString(Formatting.None)) > MaxResultBytes)
                    throw new ResultCaptureException("result_too_large: JSON exceeds 65536 UTF-8 bytes.");
                result.Result = detached;
            }
            catch (ResultCaptureException ex)
            {
                result.ResultError = ex.Message + ResultErrorNotice;
            }
            catch (Exception)
            {
                // Do not read an arbitrary exception's Message or retain the object:
                // it can itself execute user code or contain unbounded text.
                result.ResultError = "result_conversion_failed: A returned value could not be read " +
                    "(for example, a property getter threw an exception)." + ResultErrorNotice;
            }
        }

        private sealed class ResultCaptureException : Exception
        {
            public ResultCaptureException(string message) : base(message) { }
        }

        private sealed class ResultProjector
        {
            private int remainingBytes = MaxResultBytes;
            private readonly List<object> ancestors = new List<object>();

            public JToken Project(object value, int depth)
            {
                if (value == null)
                {
                    Reserve(4);
                    return JValue.CreateNull();
                }

                if ((value is double d && (double.IsNaN(d) || double.IsInfinity(d))) ||
                    (value is float f && (float.IsNaN(f) || float.IsInfinity(f))))
                    throw new ResultCaptureException("result_non_finite: NaN and Infinity are not JSON numbers.");

                if (value is string || value is char || value is bool || value is Guid ||
                    value is byte || value is sbyte || value is short || value is ushort ||
                    value is int || value is uint || value is long || value is ulong ||
                    value is float || value is double || value is decimal)
                {
                    if (value is string text)
                        CheckStringLength(text);
                    var scalar = new JValue(value);
                    Reserve(Encoding.UTF8.GetByteCount(scalar.ToString(Formatting.None)));
                    return scalar;
                }

                if (ancestors.Any(ancestor => ReferenceEquals(ancestor, value)))
                    throw new ResultCaptureException("result_reference_cycle: Returned data contains a reference cycle.");
                if (depth >= MaxResultDepth)
                    throw new ResultCaptureException("result_too_deep: JSON exceeds 16 nested containers.");

                Reserve(2); // Object or array delimiters, including empty containers.
                ancestors.Add(value);
                try
                {
                    if (value is IDictionary dictionary)
                    {
                        var obj = new JObject();
                        foreach (DictionaryEntry entry in dictionary)
                        {
                            if (!(entry.Key is string key))
                                throw new ResultCaptureException("result_invalid_key: Dictionary keys must be strings.");
                            ReserveProperty(key, obj.Count > 0);
                            obj.Add(key, Project(entry.Value, depth + 1));
                        }
                        return obj;
                    }

                    if (value is IList list)
                    {
                        if (value is Array array && array.Rank != 1)
                            throw new ResultCaptureException("result_unsupported_type: Only one-dimensional arrays are supported.");
                        var items = new JArray();
                        int count = list.Count;
                        for (int i = 0; i < count; i++)
                        {
                            if (i > 0)
                                Reserve(1);
                            items.Add(Project(list[i], depth + 1));
                        }
                        return items;
                    }

                    // Only compiler-generated anonymous objects are data containers.
                    // Arbitrary POCO/native getters, lazy sequences, custom JSON
                    // converters and serialization callbacks are not invoked.
                    var type = value.GetType();
                    if (!type.IsClass || !type.IsSealed ||
                        !type.IsDefined(typeof(System.Runtime.CompilerServices.CompilerGeneratedAttribute), false) ||
                        !type.Name.StartsWith("<>f__AnonymousType", StringComparison.Ordinal))
                        throw new ResultCaptureException("result_unsupported_type: Return JSON scalars, dictionaries, lists, or anonymous objects.");

                    var data = new JObject();
                    foreach (var property in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
                    {
                        if (property.GetIndexParameters().Length != 0 || property.GetGetMethod() == null)
                            continue;
                        // Reserve the key before calling a getter. Both traversal and
                        // the detached tree are bounded by the emitted JSON budget.
                        ReserveProperty(property.Name, data.Count > 0);
                        data.Add(property.Name, Project(property.GetValue(value, null), depth + 1));
                    }
                    return data;
                }
                finally
                {
                    ancestors.RemoveAt(ancestors.Count - 1);
                }
            }

            private void ReserveProperty(string name, bool comma)
            {
                CheckStringLength(name);
                Reserve(Encoding.UTF8.GetByteCount(JsonConvert.ToString(name)) + (comma ? 2 : 1));
            }

            private void CheckStringLength(string value)
            {
                // UTF-8 plus JSON escaping cannot be shorter than this UTF-16
                // length. Check before allocating an escaped copy (at most 6x).
                if (value.Length > remainingBytes - 2)
                    throw new ResultCaptureException("result_too_large: JSON exceeds 65536 UTF-8 bytes.");
            }

            private void Reserve(int bytes)
            {
                if (bytes > remainingBytes)
                    throw new ResultCaptureException("result_too_large: JSON exceeds 65536 UTF-8 bytes.");
                remainingBytes -= bytes;
            }
        }

    }

    /// <summary>
    /// Result object sent back to the MCP server after script execution.
    /// </summary>
    public class ScriptResult
    {
        [JsonProperty("status")]
        public string Status { get; set; } = "success";

        [JsonProperty("message")]
        public string Message { get; set; } = "";

        [JsonProperty("guids")]
        public List<string> Guids { get; set; } = new List<string>();

        [JsonProperty("error_trace")]
        public string ErrorTrace { get; set; }

        [JsonProperty("result", NullValueHandling = NullValueHandling.Ignore)]
        public JToken Result { get; set; }

        [JsonProperty("result_error", NullValueHandling = NullValueHandling.Ignore)]
        public string ResultError { get; set; }
    }
}
