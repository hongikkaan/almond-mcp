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

        internal static string Setting(string name) => (string)Policy[name];
        internal static int IntegerSetting(string name) => (int)Policy[name];

        internal static bool IsMaterialAssignmentKey(string key)
        {
            return ((JArray)Policy["material_assignment_keys"]).Values<string>()
                .Any(name => Key(name) == key);
        }

        internal static string MaterialLayerPath(JObject material)
        {
            var supplied = material["layer_path"];
            if (supplied != null && supplied.Type != JTokenType.Null && supplied.Type != JTokenType.String)
                throw new InvalidDataException("material layer_path must be a string.");
            string path = (string)supplied ?? Setting("material_layer_root") + "::" +
                (string)material["category"] + "::" + (string)material["material_id"];
            ValidateLayerPath(path);
            return path;
        }

        internal static void ValidateLayerPath(string path)
        {
            string[] parts = (path ?? "").Split(new[] { "::" }, StringSplitOptions.None);
            if (parts.Length < 2 || parts[0] != Setting("material_layer_root") ||
                parts.Any(p => String.IsNullOrWhiteSpace(p) || p != p.Trim() ||
                    p.Any(c => c < 32 || ":<>\"/\\|?*".IndexOf(c) >= 0)))
                throw new ArgumentException("Material layer path must contain valid nonempty names beneath M::.");
        }
    }
}
