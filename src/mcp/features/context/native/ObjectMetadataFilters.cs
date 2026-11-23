using System;
using System.Collections;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino.Collections;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    public static partial class ObjectObservation
    {
        static void ValidateMetadataFilter(JToken token, string key, Action<JToken> validate)
        {
            if (token == null) return;
            if (!(token is JObject sides)) { validate(token); return; }
            if (sides.Count == 0) throw new ArgumentException($"filters.{key} requires include or exclude.");
            foreach (var side in sides.Properties())
            {
                if ((side.Name != "include" && side.Name != "exclude") || !(side.Value is JArray list) || list.Count != 1)
                    throw new ArgumentException($"filters.{key}.{side.Name} requires one include or exclude condition.");
                validate(list);
            }
        }

        static void ValidateDictionary(JToken token)
        {
            if (!(token is JArray conditions) || conditions.Count > 16) throw new ArgumentException("user_dictionary must contain at most 16 conditions.");
            foreach (var item in conditions)
            {
                var c = item as JObject;
                if (c == null || c.Properties().Any(p => p.Name != "source" && p.Name != "key" && p.Name != "any_of") ||
                    ((string)c["source"] != "attributes" && (string)c["source"] != "geometry") ||
                    c["key"]?.Type != JTokenType.String || String.IsNullOrEmpty((string)c["key"]) ||
                    !(c["any_of"] is JArray values) || values.Count < 1 || values.Count > 64 || values.Any(v => !Scalar(v)))
                    throw new ArgumentException("Each dictionary condition requires source=attributes|geometry, key and 1..64 scalar any_of values.");
            }
        }

        static bool Scalar(JToken token) => token.Type == JTokenType.String || token.Type == JTokenType.Boolean ||
            token.Type == JTokenType.Integer || token.Type == JTokenType.Float;
        internal static void ValidateUserText(JToken token)
        {
            if (token != null)
            {
                if (!(token is JArray textConditions) || textConditions.Count > 16)
                    throw new ArgumentException("filters.user_text must be an array of up to 16 conditions.");
                foreach (var item in textConditions)
                {
                    if (!(item is JObject condition) || condition.Properties().Any(p => p.Name != "key" && p.Name != "any_of") ||
                        condition["key"]?.Type != JTokenType.String || String.IsNullOrEmpty((string)condition["key"]) ||
                        !(condition["any_of"] is JArray options) || options.Count < 1 || options.Count > 64 ||
                        options.Any(value => value.Type != JTokenType.String))
                        throw new ArgumentException("Each user_text condition requires a nonempty key and 1..64 strings in any_of.");
                }
            }
        }
        internal static bool MatchesUserText(Func<string, string> read, JArray conditions)
        {
            foreach (var condition in conditions)
            {
                string actual = read((string)condition["key"]);
                if (actual == null || !condition["any_of"].Values<string>().Contains(actual, StringComparer.Ordinal))
                    return false;
            }
            return true;
        }
        static bool MatchesMetadata(JToken filter, Func<JArray, bool> matches)
        {
            if (filter is JArray legacy) return matches(legacy);
            if (!(filter is JObject sides)) return true;
            return (!(sides["include"] is JArray include) || matches(include)) &&
                   (!(sides["exclude"] is JArray exclude) || !matches(exclude));
        }

        static bool MatchesDictionary(RhinoObject obj, JArray conditions)
        {
            foreach (var c in conditions)
            {
                var dictionary = ExistingDictionary((string)c["source"] == "attributes" ? (Rhino.Runtime.CommonObject)obj.Attributes : obj.Geometry);
                string key = (string)c["key"];
                if (dictionary == null || !dictionary.ContainsKey(key)) return false;
                var raw = dictionary[key];
                object[] values;
                if (!(raw is string) && raw is IEnumerable sequence && !(raw is ArchivableDictionary))
                {
                    values = sequence.Cast<object>().Take(4097).ToArray();
                    if (values.Length > 4096) throw new ArgumentException("Dictionary filter value exceeds 4096 items; narrow the object set.");
                }
                else values = new[] { raw };
                if (!values.Select(ScalarValue).Where(v => v != null).Any(v => ((JArray)c["any_of"]).Any(expected => JToken.DeepEquals(v, expected)))) return false;
            }
            return true;
        }

        static JToken ScalarValue(object value)
        {
            if (value is string || value is bool || value is byte || value is short || value is int || value is long ||
                value is sbyte || value is ushort || value is uint || value is ulong || value is float || value is double || value is decimal)
                return JToken.FromObject(value);
            return null;
        }
    }
}
