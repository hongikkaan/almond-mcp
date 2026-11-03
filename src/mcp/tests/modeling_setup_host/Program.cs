using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json.Linq;
using RhinoAlmondBridge;

// Executes the production orchestration against table doubles. Rhino adapters are compiled,
// but no Rhino API is invoked and no Rhino document/process is created.
static class Program
{
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static JObject Recipe(string name) => new JObject { ["name"] = name, ["material_id"] = name,
        ["base_color"] = new JArray(10, 20, 30), ["metallic"] = 0.0, ["roughness"] = 0.5, ["opacity"] = 1.0 };
    static JObject Material(JObject recipe) => new JObject { ["name"] = recipe["name"].DeepClone(),
        ["type"] = "pbr", ["base_color"] = recipe["base_color"].DeepClone(),
        ["metallic"] = recipe["metallic"].DeepClone(), ["roughness"] = recipe["roughness"].DeepClone(),
        ["opacity"] = recipe["opacity"].DeepClone() };
    static JObject Layer(string path, JObject recipe) => new JObject { ["path"] = path,
        ["color"] = new JArray(10, 20, 30), ["material"] = recipe.DeepClone() };

    sealed class Tables
    {
        internal readonly Dictionary<string, JObject> Materials = new();
        internal readonly Dictionary<string, JObject> Layers = new();
        internal readonly List<string> Writes = new();
        internal string FailMaterial, RefuseLayer;
        internal JObject Run(bool overwrite)
        {
            var oak = Recipe("Oak"); var steel = Recipe("Steel");
            return ModelingSetup.Apply(new JArray(oak, steel), new JArray(Layer("M::wood", oak), Layer("M::steel", steel)), overwrite,
                recipe => Materials.TryGetValue((string)recipe["name"], out var m) ? new JArray(m.DeepClone()) : new JArray(),
                recipe => {
                    string name = (string)recipe["name"]; Writes.Add("material:" + name);
                    Materials[name] = Material(recipe);
                    if (name == FailMaterial) throw new Exception("Failure after a table mutation");
                },
                spec => Layers.TryGetValue((string)spec["path"], out var l) ? (JObject)l.DeepClone() : null,
                spec => {
                    string path = (string)spec["path"]; Writes.Add("layer:" + path);
                    if (path == RefuseLayer) return;
                    Layers[path] = new JObject { ["color"] = spec["color"].DeepClone(), ["plot_color"] = spec["color"].DeepClone(),
                        ["material"] = spec["material"]["name"].DeepClone() };
                });
        }
    }

    static void Main()
    {
        var tables = new Tables();
        var created = tables.Run(false);
        Check((bool)created["applied"], "Missing materials/layers must be created with overwrite=false.");
        Check(tables.Writes.SequenceEqual(new[] { "material:Oak", "material:Steel", "layer:M::wood", "layer:M::steel" }), "Material before Layer order.");
        tables.Writes.Clear();
        Check((bool)tables.Run(false)["applied"] && tables.Writes.Count == 0, "Repeat false must not mutate existing tables.");

        tables.Materials["Oak"]["roughness"] = 0.2;
        tables.Layers["M::wood"]["color"] = new JArray(1, 2, 3);
        tables.Layers["M::wood"]["material"] = "User material";
        var originalMaterial = tables.Materials["Oak"].ToString(); var originalLayer = tables.Layers["M::wood"].ToString();
        tables.Materials.Remove("Steel"); tables.Layers.Remove("M::steel"); tables.Writes.Clear();
        var preserved = tables.Run(false);
        Check(!(bool)preserved["applied"] && ((JArray)preserved["differences"]).Count == 3, "Report every preserved predefined-property difference.");
        Check(originalMaterial == tables.Materials["Oak"].ToString() && originalLayer == tables.Layers["M::wood"].ToString(), "Preserve existing values verbatim.");
        Check(tables.Writes.SequenceEqual(new[] { "material:Steel", "layer:M::steel" }), "Only missing entries may be written.");
        Check((bool)tables.Run(true)["applied"], "Overwrite true reconciles both kinds.");

        var failure = new Tables { FailMaterial = "Oak" };
        var failed = failure.Run(false);
        Check(!(bool)failed["applied"] && ((JArray)failed["errors"]).Count == 2, "Report failed material and dependent Layer.");
        Check(!failure.Layers.ContainsKey("M::wood"), "Do not assign an unconfirmed material to a dependent Layer.");
        Check(failure.Materials.ContainsKey("Steel") && failure.Layers.ContainsKey("M::steel"), "Other targets still processed.");
        Check(failure.Writes.Count(w => w == "material:Oak") == 1, "No automatic mutation retry.");
        var refusal = new Tables { RefuseLayer = "M::wood" }.Run(false);
        Check(!(bool)refusal["applied"] && ((JArray)refusal["errors"]).Count == 1, "Unconfirmed missing Layer is an error.");

        // A writer that returns normally but leaves a wrong value cannot claim applied=true.
        tables.Layers["M::wood"]["plot_color"] = new JArray(9, 9, 9); tables.RefuseLayer = "M::wood";
        var retained = tables.Run(true);
        Check(!(bool)retained["applied"] && ((JArray)retained["differences"]).Count == 1, "Verify requested values after writes.");
        var capture = typeof(ScriptExecutor).GetMethod("CaptureResult", BindingFlags.NonPublic | BindingFlags.Static);
        foreach (var payload in new[] { created, preserved, failed, refusal, retained })
        {
            var raw = new ScriptResult();
            capture.Invoke(null, new object[] { raw, payload });
            Check(raw.ResultError != null, "Reproduce unsupported JToken capture in the actual executor.");
            var captured = new ScriptResult();
            capture.Invoke(null, new object[] { captured, ModelingSetup.ToResultData(payload) });
            Check(captured.ResultError == null && JToken.DeepEquals(payload, captured.Result),
                "Actual executor must preserve every nested difference/error and applied flag.");
        }
        Console.WriteLine("PASS: create, preserve, differences, overwrite, ordering, repeat, partial failure, no retry, post-write verification");
    }
}
