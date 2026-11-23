using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    public static partial class ObjectObservation
    {
        static bool IsNamedFilter(string key) => key == "layer" || key == "name" || key == "object_type" ||
            key == "block" || key == "group" || key == "material";

        // Resolve both include and exclude even when the current object scope is empty.
        static Func<string, string> ReferenceResolver(string key, IEnumerable<(Guid Id, string Name)> entries,
                                                     Dictionary<Guid, Guid> aliases = null)
        {
            var rows = entries.ToArray();
            var ids = rows.Select(row => row.Id).ToHashSet();
            Guid Canonical(Guid id) => aliases != null && aliases.TryGetValue(id, out var render) ? render : id;
            var names = rows.ToLookup(row => row.Name, row => Canonical(row.Id), StringComparer.OrdinalIgnoreCase);
            return value => {
                if (Guid.TryParse(value, out Guid id) && ids.Contains(id)) return Canonical(id).ToString();
                var matches = names[value].Distinct().ToArray();
                if (matches.Length == 1) return matches[0].ToString();
                throw new ArgumentException(matches.Length == 0
                    ? $"Unknown filters.{key} reference: {value}."
                    : $"Ambiguous filters.{key} reference: {value}. Use its GUID.");
            };
        }

        static Guid FrontMaterialId(RhinoObject obj)
        {
            var render = obj.GetRenderMaterial(true);
            if (render != null) return render.Id;
            var material = obj.GetMaterial(true);
            if (material == null) return Guid.Empty;
            return material.RenderMaterialInstanceId != Guid.Empty ? material.RenderMaterialInstanceId : material.Id;
        }

        static IEnumerable<Func<RhinoObject, bool>> GroupFilters(RhinoDoc doc, JObject sides, EditingContext.ObjectScope editing)
        {
            foreach (var field in sides.Properties())
                if (field.Name != "include" && field.Name != "exclude" && field.Name != "include_mode" && field.Name != "exclude_mode")
                    throw new ArgumentException($"Unsupported filters.group.{field.Name}.");
            var groups = doc.Groups.Where(g => g != null && !g.IsDeleted).ToDictionary(g => g.Id);
            var resolve = ReferenceResolver("group", groups.Values.Select(g => (g.Id, g.Name)));
            editing = editing ?? EditingContext.ObserveObjects(doc);
            foreach (string side in new[] { "include", "exclude" })
            {
                string modeKey = side + "_mode";
                var mode = sides[modeKey];
                if (sides[side] == null && mode == null) continue;
                if (!(sides[side] is JArray list) || list.Count < 1 || list.Count > 64 ||
                    list.Any(v => v.Type != JTokenType.String || String.IsNullOrEmpty((string)v)))
                    throw new ArgumentException($"filters.group.{side} requires 1..64 group names or GUIDs.");
                if (list.Count == 1 && mode != null)
                    throw new ArgumentException($"filters.group.{modeKey} is valid only with multiple {side} values.");
                if (list.Count > 1 && (mode?.Type != JTokenType.String || ((string)mode != "any" && (string)mode != "all")))
                    throw new ArgumentException($"Multiple filters.group.{side} values require {modeKey}=any or all.");
                var ids = list.Values<string>().Select(value => Guid.Parse(resolve(value))).Distinct().ToArray();
                HashSet<Guid> members = null;
                foreach (var id in ids)
                {
                    var group = groups[id];
                    var objects = EditingContext.GroupObjects(doc, group, editing, out bool complete, out _);
                    if (!complete)
                        throw new ArgumentException($"filters.group.{side} membership is uncertain during editing: {group.Name} ({id}). Finish editing before filtering this group.");
                    var objectIds = objects.Where(o => o != null && !o.IsDeleted).Select(o => o.Id);
                    if (members == null) members = objectIds.ToHashSet();
                    else if ((string)mode == "all") members.IntersectWith(objectIds);
                    else members.UnionWith(objectIds);
                }
                bool include = side == "include";
                yield return obj => members.Contains(obj.Id) == include;
            }
        }

        static List<Func<RhinoObject, bool>> NamedFilters(RhinoDoc doc, JObject filters, EditingContext.ObjectScope editing = null)
        {
            var predicates = new List<Func<RhinoObject, bool>>();
            foreach (var field in filters.Properties().Where(p => IsNamedFilter(p.Name)))
            {
                string key = field.Name;
                if (!(field.Value is JObject sides) || sides.Count == 0)
                    throw new ArgumentException($"filters.{key} requires include or exclude.");
                if (key == "group")
                {
                    predicates.AddRange(GroupFilters(doc, sides, editing));
                    continue;
                }
                Func<RhinoObject, string> getValue;
                Func<string, string> resolve = value => value;
                switch (key)
                {
                    case "layer":
                        resolve = ReferenceResolver(key, doc.Layers.Where(l => l != null && !l.IsDeleted).Select(l => (l.Id, l.FullPath)));
                        getValue = obj => doc.Layers.FindIndex(obj.Attributes.LayerIndex)?.Id.ToString();
                        break;
                    case "block":
                        resolve = ReferenceResolver(key, doc.InstanceDefinitions.Where(d => d != null && !d.IsDeleted).Select(d => (d.Id, d.Name)));
                        getValue = obj => (obj as InstanceObject)?.InstanceDefinition?.Id.ToString();
                        break;
                    case "material":
                        var materials = doc.Materials.Where(m => m != null && !m.IsDeleted).ToArray();
                        var aliases = materials.Where(m => m.RenderMaterialInstanceId != Guid.Empty)
                            .ToDictionary(m => m.Id, m => m.RenderMaterialInstanceId);
                        resolve = ReferenceResolver(key, materials.Select(m => (m.Id, m.Name))
                            .Concat(doc.RenderMaterials.Select(m => (m.Id, m.Name))), aliases);
                        getValue = obj => FrontMaterialId(obj).ToString();
                        break;
                    case "object_type":
                        var types = new HashSet<string>(Enum.GetNames(typeof(ObjectType)), StringComparer.OrdinalIgnoreCase);
                        resolve = value => types.Contains(value) ? value : throw new ArgumentException($"Unknown filters.object_type: {value}.");
                        getValue = obj => obj.ObjectType.ToString();
                        break;
                    default:
                        getValue = obj => obj.Name;
                        break;
                }
                foreach (var side in sides.Properties())
                {
                    if (side.Name != "include" && side.Name != "exclude")
                        throw new ArgumentException($"Unsupported filters.{key}.{side.Name}.");
                    if (!(side.Value is JArray list) || list.Count == 0 || list.Count > 64 ||
                        list.Any(v => v.Type != JTokenType.String || String.IsNullOrEmpty((string)v)))
                        throw new ArgumentException($"filters.{key}.{side.Name} requires 1..64 nonempty strings.");
                    var terms = new HashSet<string>(list.Values<string>().Select(resolve), StringComparer.OrdinalIgnoreCase);
                    bool include = side.Name == "include";
                    predicates.Add(obj => terms.Contains(getValue(obj)) == include);
                }
            }
            return predicates;
        }
    }
}
