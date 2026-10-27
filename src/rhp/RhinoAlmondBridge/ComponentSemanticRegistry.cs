using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Commands;
using Rhino.DocObjects;
using Rhino.FileIO;

namespace RhinoAlmondBridge
{
    /// <summary>Document-private meaning bindings. Geometry and group membership stay in Rhino.</summary>
    public static class ComponentSemanticRegistry
    {
        private sealed class DocumentData
        {
            private readonly Dictionary<string, object> values;
            internal DocumentData(Dictionary<string, object> source) { values = source; }
            internal JObject Records { get => (JObject)values["records"]; set => values["records"] = value; }
            internal JArray Problems => (JArray)values["problems"];
            internal bool Initialized { get => (bool)values["initialized"]; set => values["initialized"] = value; }
        }

        private const int MaxArchiveBytes = 4194304;
        private static DocumentData Data(RhinoDoc doc) => new DocumentData(doc.RuntimeData.GetValue(
            "almond:semantic_registry/v1", _ => new Dictionary<string, object> {
                ["records"] = new JObject(), ["problems"] = new JArray(), ["initialized"] = false }));

        internal static JObject Records(RhinoDoc doc, JArray seeds = null)
        {
            var state = Data(doc);
            if (!state.Initialized)
            {
                // Migration only reads existing attributes. A bad legacy host is isolated;
                // its copied owner stamp is never a reason to block an unrelated group.
                state.Initialized = true;
                var conflicted = new HashSet<string>(StringComparer.Ordinal);
                var settings = new ObjectEnumeratorSettings {
                    NormalObjects = true, HiddenObjects = true, LockedObjects = true,
                    ReferenceObjects = false, IdefObjects = false, DeletedObjects = false
                };
                foreach (var obj in doc.Objects.GetObjectList(settings))
                {
                    string raw = obj.Attributes.GetUserString(ModelingMetadata.Key("component_record"));
                    if (String.IsNullOrEmpty(raw)) continue;
                    try
                    {
                        var map = JObject.Parse(raw);
                        var entries = map["component_id"] == null ? map.Properties().Select(p => p.Value) : new[] { map };
                        foreach (var entry in entries)
                        {
                            var record = Validate(entry as JObject);
                            string id = (string)record["component_id"];
                            if (conflicted.Contains(id)) continue;
                            if (state.Records[id] == null) AddObserved(state, id, record);
                            else if (!JToken.DeepEquals(state.Records[id], record))
                            {
                                state.Records.Remove(id);
                                conflicted.Add(id);
                                state.Problems.Add(new JObject { ["component_id"] = id, ["code"] = "legacy_record_conflict" });
                            }
                        }
                    }
                    catch (Exception)
                    {
                        state.Problems.Add(new JObject { ["code"] = "invalid_legacy_record", ["host_id"] = obj.Id.ToString("D") });
                    }
                }
            }
            if (seeds != null)
            {
                    foreach (var seed in seeds)
                    {
                        try
                        {
                            var record = Validate(seed as JObject);
                            string id = (string)record["component_id"];
                            // A saved empty registry may predate the first DB alignment.
                            // Recover only absent identities; archive entries and explicit
                            // unregister/Undo tombstones always win over cached DB seeds.
                            if (state.Records[id] == null)
                                AddObserved(state, id, record);
                        }
                        catch (Exception) { /* The caller's normal item proof reports an invalid seed. */ }
                    }
            }
            return state.Records;
        }

        internal static JArray MigrationProblems(RhinoDoc doc) =>
            (JArray)Data(doc).Problems.DeepClone();

        private static string ArchiveJson(JObject records, bool initialized) => new JObject {
            ["version"] = 1, ["records"] = records.DeepClone(), ["legacy_initialized"] = initialized
        }.ToString(Formatting.None);

        private static void AddObserved(DocumentData state, string id, JObject record)
        {
            var candidate = (JObject)state.Records.DeepClone();
            candidate[id] = record;
            if (System.Text.Encoding.UTF8.GetByteCount(ArchiveJson(candidate, state.Initialized)) > MaxArchiveBytes)
            {
                if (!state.Problems.Any(problem => (string)problem["component_id"] == id && (string)problem["code"] == "registry_budget_exceeded"))
                    state.Problems.Add(new JObject { ["component_id"] = id, ["code"] = "registry_budget_exceeded" });
                return;
            }
            state.Records = candidate;
        }

        internal static JObject Validate(JObject record)
        {
            if (record == null) throw new ArgumentException("A semantic registration must be an object.");
            string id = (string)record["component_id"];
            if (String.IsNullOrWhiteSpace(id) || id.Length > 160 ||
                !System.Text.RegularExpressions.Regex.IsMatch(id, @"^[A-Za-z0-9_.:-]+$"))
                throw new ArgumentException("A semantic registration needs a stable Component handle.");
            if (!Guid.TryParse((string)record["rhino_group_id"], out Guid group) || group == Guid.Empty)
                throw new ArgumentException("A semantic registration needs a persistent group GUID.");
            var scenes = Strings(record["scene_ids"], false);
            var children = Strings(record["child_component_ids"] ?? new JArray(), true);
            return new JObject {
                ["component_id"] = id, ["rhino_group_id"] = group.ToString("D"),
                ["name"] = (string)record["name"] ?? id,
                ["scene_ids"] = new JArray(scenes), ["child_component_ids"] = new JArray(children),
                ["registration_status"] = (string)record["registration_status"] == "unregistered" ? "unregistered" : "registered"
            };
        }

        internal static string[] Strings(JToken value, bool allowEmpty)
        {
            if (!(value is JArray values) || (!allowEmpty && values.Count == 0) ||
                values.Any(v => v.Type != JTokenType.String || String.IsNullOrWhiteSpace((string)v)))
                throw new ArgumentException("Expected distinct nonempty string handles.");
            var result = values.Values<string>().ToArray();
            if (result.Distinct(StringComparer.Ordinal).Count() != result.Length)
                throw new ArgumentException("Duplicate semantic handles are not allowed.");
            return result;
        }

        internal static void Change(RhinoDoc doc, JObject records)
        {
            var state = Data(doc);
            var before = (JObject)state.Records.DeepClone();
            if (JToken.DeepEquals(before, records)) return;
            if (System.Text.Encoding.UTF8.GetByteCount(records.ToString(Formatting.None)) > MaxArchiveBytes - 64)
                throw new InvalidOperationException("Component document registry exceeds its archive budget.");
            if (!doc.AddCustomUndoEvent("ontological_component registration", Restore, before))
                throw new InvalidOperationException("Could not record semantic registration Undo.");
            state.Records = (JObject)records.DeepClone();
            doc.Modified = true;
        }

        private static void Restore(object sender, CustomUndoEventArgs args)
        {
            var state = Data(args.Document);
            var previous = (JObject)args.Tag;
            if (!args.Document.AddCustomUndoEvent(args.ActionDescription, Restore, state.Records.DeepClone()))
                throw new InvalidOperationException("Could not record semantic registration Redo.");
            var restored = (JObject)previous.DeepClone();
            // An undone registration remains an explicit non-active identity. A later
            // DB seed must not resurrect it, while unrelated legacy seeds stay usable.
            foreach (var property in state.Records.Properties())
                if (restored[property.Name] == null)
                {
                    var removed = (JObject)property.Value.DeepClone();
                    removed["registration_status"] = "unregistered";
                    removed["child_component_ids"] = new JArray();
                    restored[property.Name] = removed;
                }
            state.Records = restored;
            state.Initialized = true;
        }

        public static string Export(RhinoDoc doc)
        {
            // Save hooks run inside native commands and may see an editing scope.
            // Serialize only private data; defer first legacy object observation
            // to Records(), which the public boundary calls after its stable gate.
            var state = Data(doc);
            string json = ArchiveJson(state.Records, state.Initialized);
            if (System.Text.Encoding.UTF8.GetByteCount(json) > MaxArchiveBytes)
                throw new InvalidOperationException("Component document registry exceeds 4 MiB.");
            return json;
        }

        public static void Import(RhinoDoc doc, string json)
        {
            if (String.IsNullOrEmpty(json) || System.Text.Encoding.UTF8.GetByteCount(json) > MaxArchiveBytes)
                throw new ArgumentException("Invalid Component document registry size.");
            var source = JObject.Parse(json);
            if ((int?)source["version"] != 1 || !(source["records"] is JObject records))
                throw new ArgumentException("Unsupported Component document registry version.");
            var validated = new JObject();
            foreach (var property in records.Properties())
            {
                var record = Validate(property.Value as JObject);
                if (property.Name != (string)record["component_id"])
                    throw new ArgumentException("Component document identity disagrees with its key.");
                validated[property.Name] = record;
            }
            var state = Data(doc);
            state.Records = validated;
            state.Initialized = (bool?)source["legacy_initialized"] ?? true;
        }

        public static void Write(RhinoDoc doc, BinaryArchiveWriter archive)
        {
            archive.Write3dmChunkVersion(1, 0);
            archive.WriteString(Export(doc));
        }

        public static void Read(RhinoDoc doc, BinaryArchiveReader archive, FileReadOptions options)
        {
            // Import/insert/template/reference data belongs to another semantic
            // document. It must not replace this document's registrations or tombstones.
            if (options == null || !options.OpenMode || options.ImportMode || options.InsertMode ||
                options.NewMode || options.ImportReferenceMode) return;
            if (archive == null) throw new ArgumentNullException(nameof(archive));
            archive.Read3dmChunkVersion(out int major, out int minor);
            if (major != 1) throw new ArgumentException("Unsupported Component document registry archive.");
            Import(doc, archive.ReadString());
        }
    }
}
