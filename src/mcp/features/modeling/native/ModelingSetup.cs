using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    // Policy and result accounting are independent of Rhino. The adapter owns table operations.
    internal static class ModelingSetup
    {
        // ScriptExecutor accepts detached dictionaries/lists/scalars, not JToken.
        internal static object ToResultData(JToken value)
        {
            if (value == null || value.Type == JTokenType.Null) return null;
            if (value is JObject obj)
                return obj.Properties().ToDictionary(p => p.Name, p => ToResultData(p.Value));
            if (value is JArray array)
                return array.Select(ToResultData).ToList();
            if (value is JValue scalar) return scalar.Value;
            throw new InvalidOperationException("Unsupported setup result token: " + value.Type);
        }

        private static bool Same(JToken left, JToken right)
        {
            if (left == null || right == null) return left == right;
            if ((left.Type == JTokenType.Float || left.Type == JTokenType.Integer) &&
                (right.Type == JTokenType.Float || right.Type == JTokenType.Integer))
                return Math.Abs((double)left - (double)right) <= 0.000001;
            return JToken.DeepEquals(left, right);
        }

        private static void Compare(string kind, string name, JObject actual, JObject expected, JArray differences)
        {
            foreach (var property in expected.Properties())
                if (!Same(actual[property.Name], property.Value))
                    differences.Add(new JObject {
                        ["kind"] = kind, ["name"] = name, ["property"] = property.Name,
                        ["current"] = actual[property.Name]?.DeepClone() ?? JValue.CreateNull(),
                        ["expected"] = property.Value.DeepClone()
                    });
        }

        public static JObject Apply(JArray recipes, JArray layers, bool overwrite,
            Func<JObject, JArray> readMaterials, Action<JObject> writeMaterial,
            Func<JObject, JObject> readLayer, Action<JObject> writeLayer)
        {
            var differences = new JArray();
            var errors = new JArray();
            var failedMaterials = new HashSet<string>(StringComparer.Ordinal);
            // Material registration precedes Layer creation/assignment within one caller-owned Undo record.
            foreach (var recipe in recipes.Cast<JObject>())
            {
                string name = (string)recipe["name"];
                try
                {
                    var actual = readMaterials(recipe);
                    if (actual.Count == 0 || overwrite)
                    {
                        writeMaterial(recipe);
                        actual = readMaterials(recipe);
                    }
                    if (actual.Count == 0) throw new InvalidOperationException("Material is missing after registration.");
                    var expected = new JObject { ["name"] = name, ["type"] = "pbr" };
                    foreach (string key in new[] { "base_color", "metallic", "roughness", "opacity" })
                        expected[key] = recipe[key].DeepClone();
                    foreach (var material in actual.Cast<JObject>()) Compare("material", name, material, expected, differences);
                }
                catch (Exception exc)
                {
                    failedMaterials.Add(name);
                    errors.Add(new JObject { ["kind"] = "material", ["name"] = name, ["message"] = exc.Message });
                }
            }
            foreach (var specification in layers.Cast<JObject>())
            {
                string path = (string)specification["path"];
                try
                {
                    if (specification["material"] is JObject required && failedMaterials.Contains((string)required["name"]))
                        throw new InvalidOperationException("Required material could not be confirmed: " + (string)required["name"]);
                    var actual = readLayer(specification);
                    if (actual == null || overwrite)
                    {
                        writeLayer(specification);
                        actual = readLayer(specification);
                    }
                    if (actual == null) throw new InvalidOperationException("Layer is missing after registration.");
                    var expected = new JObject {
                        ["color"] = specification["color"].DeepClone(),
                        ["plot_color"] = specification["color"].DeepClone()
                    };
                    // Containers have no prescribed material. Preserve unrelated Layer properties.
                    if (specification["material"] is JObject recipe) expected["material"] = recipe["name"].DeepClone();
                    Compare("layer", path, actual, expected, differences);
                }
                catch (Exception exc)
                {
                    errors.Add(new JObject { ["kind"] = "layer", ["name"] = path, ["message"] = exc.Message });
                }
            }
            return new JObject { ["applied"] = differences.Count == 0 && errors.Count == 0,
                ["differences"] = differences, ["errors"] = errors };
        }
    }
}
