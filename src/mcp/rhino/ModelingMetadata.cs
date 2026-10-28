using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    public static class ModelingMetadata
    {
        private static readonly JObject Policy = Load();

        private static JObject Load()
        {
            using (var stream = typeof(ModelingMetadata).Assembly.GetManifestResourceStream("RhinoAlmondBridge.modeling_policy.json"))
            {
                if (stream == null) throw new InvalidDataException("The shared modeling metadata policy is missing.");
                using (var reader = new StreamReader(stream)) return JObject.Parse(reader.ReadToEnd());
            }
        }

        public static string Key(string name)
        {
            foreach (var mapping in new[] { "public_object_keys", "internal_object_keys", "group_keys" })
                if (Policy[mapping]?[name]?.Type == JTokenType.String) return (string)Policy[mapping][name];
            throw new ArgumentException("Unknown modeling metadata key: " + name);
        }

        internal static bool IsMaterialAssignmentKey(string key) =>
            ((JArray)Policy["material_assignment_keys"]).Values<string>().Any(name => Key(name) == key);

    }
}
