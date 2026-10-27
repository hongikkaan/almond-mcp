using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // Semantic records bind persistent group GUIDs; actual groups remain geometry truth.
    public static class ComponentRegistry
    {
        public const int MaxObjects = 4096;
        private const int MaxBytes = 2097152;

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                if (!Path.IsPathRooted(Text(request, "expected_model_path")) || doc == null || String.IsNullOrWhiteSpace(doc.Path) || !String.Equals(Path.GetFullPath(doc.Path),
                    Path.GetFullPath(Text(request, "expected_model_path")), StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException("The Component request must target the current saved document.");
                string action = Text(request, "action");
                var editing = EditingContext.Observe(doc);
                if ((bool?)editing["stable"] != true) return new JObject {
                    ["status"] = "error", ["error_code"] = "unstable_editing_scope", ["editing"] = editing,
                    ["message"] = "Finish group/block editing before observing Component groups.", ["mutation_applied"] = false };
                var records = ComponentSemanticRegistry.Records(doc, request["registrations"] as JArray);
                if (action == "objects") return Bound(new JObject {
                    ["status"] = "success", ["complete"] = true, ["model_path"] = doc.Path,
                    ["objects"] = new JArray(Objects(doc, Ids(request["object_ids"])).Select(o => Describe(doc, o, Owner(doc, records, o.Id)))) });
                if (action == "inspect_many")
                {
                    string[] ids = request["component_ids"] == null || request["component_ids"].Type == JTokenType.Null
                        ? Registered(records).Select(r => (string)r["component_id"]).Union((request["registrations"] as JArray ?? new JArray())
                            .OfType<JObject>().Select(r => (string)r["component_id"]).Where(id => !String.IsNullOrWhiteSpace(id))).ToArray()
                        : Strings(request["component_ids"]);
                    string scene = Text(request, "scene_id", false);
                    bool discoverScene = (bool?)request["discover_scene"] == true;
                    if (discoverScene)
                    {
                        if (scene == "") throw new ArgumentException("Scene discovery needs a Scene handle.");
                        var selected = new HashSet<string>(request["component_ids"] == null || request["component_ids"].Type == JTokenType.Null ? new string[0] : ids);
                        selected.UnionWith(Registered(records).Where(r => r["scene_ids"].Values<string>().Contains(scene)).Select(r => (string)r["component_id"]));
                        ids = selected.OrderBy(id => id).ToArray();
                    }
                    else if (scene != "" && (request["component_ids"] == null || request["component_ids"].Type == JTokenType.Null))
                        ids = ids.Where(id => (records[id]?["scene_ids"] as JArray)?.Values<string>().Contains(scene) == true).ToArray();
                    var closure = new HashSet<string>(); var pendingIds = new Queue<string>(ids);
                    while (pendingIds.Count > 0)
                    {
                        string id = pendingIds.Dequeue();
                        if (!closure.Add(id)) continue;
                        if (closure.Count > 64) throw new ArgumentException("Narrow alignment to at most 64 Components including descendants.");
                        foreach (string child in Children(records[id] as JObject)) pendingIds.Enqueue(child);
                    }
                    ids = closure.OrderBy(id => id).ToArray();
                    var snapshots = new JArray(); var problems = ComponentSemanticRegistry.MigrationProblems(doc);
                    foreach (string id in ids)
                    {
                        try { snapshots.Add(Snapshot(doc, records, id)); }
                        catch (Exception e) { problems.Add(new JObject { ["component_id"] = id, ["code"] = "invalid_binding", ["message"] = e.Message }); }
                    }
                    var current = new HashSet<Guid>(snapshots.OfType<JObject>()
                        .SelectMany(item => item["effective_object_ids"].Values<string>()).Select(Guid.Parse));
                    var absent = new JArray(); var detached = new JArray();
                    foreach (Guid id in Ids(request["prior_object_ids"] ?? new JArray()))
                    {
                        if (current.Contains(id)) continue;
                        var obj = doc.Objects.FindId(id);
                        if (obj == null || obj.IsDeleted) absent.Add(id.ToString("D"));
                        else
                        {
                            try
                            {
                                if (obj.IsReference || obj.IsInstanceDefinitionGeometry || obj.Attributes.Space != ActiveSpace.ModelSpace)
                                    throw new ArgumentException("Cached object is outside editable model space.");
                                // Presence observation cannot claim another registration's owner.
                                detached.Add(Describe(doc, obj, null));
                            }
                            catch (Exception error) { problems.Add(new JObject { ["code"] = "unavailable_cached_object",
                                ["object_id"] = id.ToString("D"), ["message"] = error.Message }); }
                        }
                    }
                    return Bound(new JObject { ["status"] = "success", ["complete"] = true,
                        ["model_path"] = doc.Path, ["editing"] = editing, ["components"] = snapshots, ["problems"] = problems,
                        ["presence_complete"] = true, ["absent_object_ids"] = absent, ["detached_objects"] = detached });
                }
                string target = Text(request, "component_id");
                var prior = records[target] as JObject;
                if (prior != null && Text(request, "rhino_group_id", false) != "" &&
                    Guid.Parse((string)prior["rhino_group_id"]) != Guid.Parse(Text(request, "rhino_group_id")))
                    throw new ArgumentException("Component and persistent group identity disagree.");
                if (action == "inspect" || action == "sync") return Bound(new JObject {
                    ["status"] = "success", ["component"] = Snapshot(doc, records, target),
                    ["affected_components"] = Related(doc, records, target) });
                var proposed = (JObject)records.DeepClone();
                if (action == "unregister")
                {
                    if (prior == null || !Active(prior)) throw new ArgumentException("Unknown semantic registration.");
                    if (Parent(records, target) != null) throw new ArgumentException("Detach the child before unregistering.");
                    var children = Children(prior);
                    proposed[target]["registration_status"] = "unregistered";
                    proposed[target]["child_component_ids"] = new JArray();
                    var acknowledgement = Bound(new JObject { ["status"] = "success", ["component_id"] = target,
                        ["model_path"] = doc.Path, ["rhino_group_id"] = prior["rhino_group_id"].DeepClone(),
                        ["detached_child_component_ids"] = new JArray(children),
                        ["affected_components"] = new JArray(children.Select(id => Snapshot(doc, proposed, id))) });
                    started = true;
                    var removed = new ScriptExecutor().ExecuteAction(doc, () => { ComponentSemanticRegistry.Change(doc, proposed); return null; });
                    return removed.Status == "success" ? acknowledgement : MutationError(removed);
                }
                if (action != "upsert") throw new ArgumentException("Unsupported Component action.");
                string name = Text(request, "name");
                string[] scenes = ComponentSemanticRegistry.Strings(request["scene_ids"], false);
                string[] childrenIds = request["child_component_ids"] == null || request["child_component_ids"].Type == JTokenType.Null
                    ? (prior == null ? new string[0] : Children(prior)) : Strings(request["child_component_ids"]);
                Guid[] direct = Ids(request["object_ids"]); Objects(doc, direct);
                var wanted = new HashSet<Guid>(direct);
                foreach (string child in childrenIds)
                {
                    if (child == target || !(records[child] is JObject r) || !Active(r)) throw new ArgumentException("Missing child Component.");
                    if (Parent(records, child) != null && Parent(records, child) != target) throw new ArgumentException("Detach before reparenting.");
                    wanted.UnionWith(Members(doc, r).Select(o => o.Id));
                }
                if (wanted.Count == 0 || wanted.Count > MaxObjects) throw new ArgumentException("Register a group with 1 to 4096 current members.");
                string gid = prior == null ? Text(request, "rhino_group_id", false) : (string)prior["rhino_group_id"];
                Group group = null;
                if (gid != "")
                {
                    group = doc.Groups.FindId(Guid.Parse(gid));
                    if (group == null || group.IsDeleted || group.IsReference) throw new ArgumentException("The supplied Rhino group is unavailable.");
                    if (!wanted.SetEquals(doc.Groups.GroupMembers(group.Index).Select(o => o.Id)))
                        throw new ArgumentException("Registration must match the actual group; edit Rhino first. Alignment never repairs memberships.");
                }
                else
                {
                    var matches = doc.Groups.Where(g => !g.IsDeleted && !g.IsReference && wanted.SetEquals(doc.Groups.GroupMembers(g.Index).Select(o => o.Id))).ToArray();
                    if (matches.Length > 1) throw new ArgumentException("Several groups have these members; supply the intended group GUID.");
                    group = matches.FirstOrDefault();
                }
                if (group != null && Registered(records).Any(r => (string)r["component_id"] != target && (string)r["rhino_group_id"] == group.Id.ToString("D")))
                    throw new ArgumentException("Group already has another semantic registration.");
                if (group != null && group.Name != name)
                    throw new ArgumentException("Use the current Rhino group name for registration. Rhino group-table renames are not Undo-tracked; edit its name in Rhino and align explicitly.");
                if (group == null && doc.Groups.Any(existing => !doc.Groups.IsDeleted(existing.Index) &&
                    String.Equals(existing.Name, name, StringComparison.OrdinalIgnoreCase)))
                    return new JObject { ["status"] = "error", ["error_code"] = "component_name_collision", ["mutation_applied"] = false,
                        ["message"] = "An ordinary Rhino group already uses this name. Review that group in Rhino or explicitly choose another name. No group was created." };
                foreach (Guid id in direct)
                {
                    string owner = Owner(doc, records, id);
                    if (owner != null && owner != target) throw new ArgumentException("Object is directly owned by another meaning unit.");
                }
                proposed[target] = ComponentSemanticRegistry.Validate(new JObject { ["component_id"] = target,
                    ["rhino_group_id"] = group == null ? Guid.NewGuid().ToString("D") : group.Id.ToString("D"),
                    ["name"] = name, ["scene_ids"] = new JArray(scenes), ["child_component_ids"] = new JArray(childrenIds) });
                Tree(proposed, target, new HashSet<string>());
                if (JToken.DeepEquals(prior, proposed[target])) return Bound(new JObject {
                    ["status"] = "success", ["component"] = Snapshot(doc, records, target), ["affected_components"] = new JArray() });
                started = true; JObject reply = null;
                var changed = new ScriptExecutor().ExecuteAction(doc, () => {
                    if (group == null)
                    {
                        int index = doc.Groups.Add(name, wanted);
                        if (index < 0) throw new InvalidOperationException("Could not create the explicitly requested group.");
                        group = doc.Groups[index]; proposed[target]["rhino_group_id"] = group.Id.ToString("D");
                    }
                    ComponentSemanticRegistry.Change(doc, proposed);
                    reply = Bound(new JObject { ["status"] = "success", ["component"] = Snapshot(doc, proposed, target),
                        ["affected_components"] = Related(doc, proposed, target) }); return null;
                });
                return changed.Status == "success" ? reply : MutationError(changed);
            }
            catch (Exception error) { return new JObject { ["status"] = "error", ["error_code"] = "component_error", ["message"] = error.Message,
                ["mutation_applied"] = started ? JValue.CreateNull() : new JValue(false), ["requires_reconciliation"] = started }; }
        }

        private static JObject Snapshot(RhinoDoc doc, JObject records, string id)
        {
            var record = records[id] as JObject ?? throw new ArgumentException("Unknown semantic registration: " + id);
            var descendants = Descendants(records, id);
            var group = doc.Groups.FindId(Guid.Parse((string)record["rhino_group_id"]));
            bool available = Active(record) && group != null && !group.IsDeleted;
            var members = available ? Members(doc, record) : new RhinoObject[0];
            var children = Active(record) ? Children(record) : new string[0];
            var nested = new HashSet<Guid>(descendants.SelectMany(child => Members(doc, records[child] as JObject)).Select(o => o.Id));
            if (available && !nested.IsSubsetOf(members.Select(o => o.Id))) throw new ArgumentException("A semantic child is outside the actual parent group.");
            var direct = members.Where(o => !nested.Contains(o.Id)).ToArray();
            return new JObject { ["complete"] = true, ["live_verified"] = true, ["component_id"] = id, ["model_path"] = doc.Path,
                ["rhino_group_id"] = record["rhino_group_id"].DeepClone(), ["name"] = group != null && !group.IsDeleted ? group.Name : (string)record["name"],
                ["scene_ids"] = record["scene_ids"].DeepClone(), ["child_component_ids"] = new JArray(children), ["parent_component_id"] = Active(record) ? Parent(records, id) : null,
                ["availability"] = !Active(record) ? "unregistered" : available ? "present" : "missing_group",
                ["registration_status"] = Active(record) ? "registered" : "unregistered",
                ["objects"] = new JArray(direct.Select(o => Describe(doc, o, id))), ["object_ids"] = new JArray(direct.Select(o => o.Id.ToString("D"))),
                ["effective_objects"] = new JArray(members.Select(o => Describe(doc, o, Owner(doc, records, o.Id)))),
                ["effective_object_ids"] = new JArray(members.Select(o => o.Id.ToString("D"))), ["pending_objects"] = new JArray(), ["requires_sync"] = false };
        }
        private static JArray Related(RhinoDoc doc, JObject records, string target)
        {
            var ids = new HashSet<string>(); string parent = Parent(records, target);
            while (parent != null && ids.Add(parent)) parent = Parent(records, parent);
            foreach (string child in Children(records[target] as JObject)) ids.Add(child);
            return new JArray(ids.OrderBy(x => x).Select(id => Snapshot(doc, records, id)));
        }
        private static bool Active(JObject record) => record != null && (string)record["registration_status"] != "unregistered";
        private static IEnumerable<JObject> Registered(JObject records) => records.Properties().Select(p => p.Value as JObject).Where(Active);
        private static string[] Children(JObject record) => record == null ? new string[0] : Strings(record["child_component_ids"] ?? new JArray());
        private static string Parent(JObject records, string id)
        {
            var parents = Registered(records).Where(r => Children(r).Contains(id)).Select(r => (string)r["component_id"]).ToArray();
            if (parents.Length > 1) throw new ArgumentException("A Component has more than one semantic parent."); return parents.FirstOrDefault();
        }
        private static HashSet<string> Descendants(JObject records, string id)
        {
            var result = new HashSet<string>();
            Tree(records, id, new HashSet<string>(), result);
            return result;
        }
        private static void Tree(JObject records, string id, HashSet<string> path, HashSet<string> descendants = null)
        {
            if (!path.Add(id) || path.Count > 64 || !(records[id] is JObject record)) throw new ArgumentException("Invalid or cyclic semantic hierarchy.");
            foreach (string child in Children(record)) { descendants?.Add(child); Tree(records, child, path, descendants); } path.Remove(id);
        }
        private static string Owner(RhinoDoc doc, JObject records, Guid id)
        {
            var containing = Registered(records).Where(r => {
                var g = doc.Groups.FindId(Guid.Parse((string)r["rhino_group_id"]));
                return g != null && !g.IsDeleted && doc.Objects.FindId(id)?.Attributes.IsInGroup(g.Index) == true;
            }).ToArray();
            var deepest = containing.Where(r => !Descendants(records, (string)r["component_id"])
                .Overlaps(containing.Select(c => (string)c["component_id"]))).ToArray();
            if (deepest.Length > 1) throw new ArgumentException("An object is in unrelated semantic groups: " + id);
            return deepest.Length == 0 ? null : (string)deepest[0]["component_id"];
        }
        private static RhinoObject[] Members(RhinoDoc doc, JObject record)
        {
            if (record == null) throw new ArgumentException("A semantic child is missing.");
            var group = doc.Groups.FindId(Guid.Parse((string)record["rhino_group_id"]));
            if (group == null || group.IsDeleted) return new RhinoObject[0];
            if (group.IsReference) throw new ArgumentException("A reference group is unavailable.");
            return Objects(doc, doc.Groups.GroupMembers(group.Index).Select(o => o.Id).ToArray());
        }
        private static RhinoObject[] Objects(RhinoDoc doc, Guid[] ids)
        {
            if (ids.Length > MaxObjects) throw new ArgumentException("Narrow a Component to at most 4096 objects.");
            var objects = ids.Distinct().OrderBy(id => id).Select(id => doc.Objects.FindId(id)).ToArray();
            if (objects.Any(o => o == null || o.IsDeleted || o.IsReference || o.IsInstanceDefinitionGeometry || o.Attributes.Space != ActiveSpace.ModelSpace ||
                !String.IsNullOrEmpty(o.Attributes.GetUserString("$TempBlockEditUserData$")))) throw new ArgumentException("Group members must be available document model objects.");
            return objects;
        }
        private static JObject Describe(RhinoDoc doc, RhinoObject obj, string owner)
        {
            var b = obj.Geometry.GetBoundingBox(true); double scale = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Millimeters);
            if (!b.IsValid || !Double.IsFinite(scale) || scale <= 0) throw new ArgumentException("Invalid member bounds or model units.");
            return new JObject { ["rhino_guid"] = obj.Id.ToString("D"), ["component_id"] = owner, ["object_type"] = obj.ObjectType.ToString(),
                ["name"] = obj.Attributes.Name ?? "", ["bounds_mm"] = new JArray(b.Min.X*scale,b.Min.Y*scale,b.Min.Z*scale,b.Max.X*scale,b.Max.Y*scale,b.Max.Z*scale) };
        }
        private static string[] Strings(JToken value) => ComponentSemanticRegistry.Strings(value, true);
        private static Guid[] Ids(JToken value)
        {
            var result = Strings(value).Select(Guid.Parse).ToArray();
            if (result.Any(id => id == Guid.Empty) || result.Distinct().Count() != result.Length)
                throw new ArgumentException("Group members need distinct nonempty GUIDs."); return result;
        }
        private static string Text(JObject request, string key, bool required = true)
        {
            var value = request?[key];
            if (value == null || value.Type == JTokenType.Null) { if (!required) return ""; throw new ArgumentException(key + " is required."); }
            if (value.Type != JTokenType.String || (required && String.IsNullOrWhiteSpace((string)value))) throw new ArgumentException(key + " must be a nonempty string."); return (string)value;
        }
        private static JObject MutationError(ScriptResult result) => new JObject { ["status"] = "error", ["message"] = result.Message,
            ["error_code"] = "component_mutation_error", ["mutation_applied"] = JValue.CreateNull(), ["requires_reconciliation"] = true };
        private static JObject Bound(JObject result)
        {
            if (Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) > MaxBytes) throw new ArgumentException("Component response exceeds 2 MiB; narrow the scope."); return result;
        }
    }
}
