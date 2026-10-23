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
    /// <summary>
    /// Explicit Rhino groups form a single-parent Component tree. A group's physical
    /// members are its directly owned objects and all descendant objects. Direct
    /// ownership is the sole almond:component_id stamp on each top-level object.
    /// Metadata is carried in undoable object attributes, never Group.UserStrings.
    /// </summary>
    public static class ComponentRegistry
    {
        public const int MaxObjects = 4096;
        private const int MaxBytes = 2097152;
        private const int MaxDepth = 64;
        private static string OwnerKey => ModelingMetadata.Key("component_id");
        private static string RecordKey => ModelingMetadata.Key("component_record");
        private static string[] Fields => new[] { "component_id", "rhino_group_id", "name", "scene_ids", "child_component_ids" };

        private sealed class Node
        {
            internal string Id;
            internal string Name;
            internal string[] Scenes;
            internal string[] Children;
            internal string Parent;
            internal Group Group;
            internal Guid GroupId;
            internal Guid HostId;
            internal HashSet<Guid> Actual = new HashSet<Guid>();
            internal HashSet<Guid> Direct = new HashSet<Guid>();
            internal HashSet<Guid> Pending = new HashSet<Guid>();
            internal HashSet<Guid> Effective = new HashSet<Guid>();
            internal bool RequiresSync;
            internal JObject ToRecord() => new JObject {
                ["component_id"] = Id, ["rhino_group_id"] = GroupId.ToString("D"),
                ["name"] = Name, ["scene_ids"] = new JArray(Scenes),
                ["child_component_ids"] = new JArray(Children)
            };
            internal Node Copy() => new Node {
                Id = Id, Name = Name, Scenes = Scenes.ToArray(), Children = Children.ToArray(),
                Parent = Parent, Group = Group, GroupId = GroupId, HostId = HostId,
                Actual = new HashSet<Guid>(Actual), Direct = new HashSet<Guid>(Direct),
                Pending = new HashSet<Guid>(Pending), Effective = new HashSet<Guid>(Effective),
                RequiresSync = RequiresSync
            };
        }

        private sealed class State
        {
            internal readonly RhinoDoc Doc;
            internal readonly Dictionary<Guid, RhinoObject> Objects;
            internal readonly Dictionary<string, Node> Nodes = new Dictionary<string, Node>(StringComparer.Ordinal);
            internal readonly Dictionary<Guid, JObject> Maps = new Dictionary<Guid, JObject>();
            internal readonly Dictionary<Guid, string> RawMaps = new Dictionary<Guid, string>();
            internal readonly Dictionary<Guid, string> Owners = new Dictionary<Guid, string>();
            internal readonly Dictionary<Guid, string> PendingOwners = new Dictionary<Guid, string>();

            internal State(RhinoDoc doc)
            {
                Doc = doc;
                var settings = new ObjectEnumeratorSettings {
                    NormalObjects = true, HiddenObjects = true, LockedObjects = true,
                    ReferenceObjects = false, IdefObjects = false, DeletedObjects = false
                };
                Objects = doc.Objects.GetObjectList(settings).Where(o => o != null && !o.IsDeleted &&
                    !o.IsInstanceDefinitionGeometry && o.Attributes.Space == ActiveSpace.ModelSpace)
                    .ToDictionary(o => o.Id);
                var groups = doc.Groups.Where(g => !g.IsDeleted).ToDictionary(g => g.Id);
                foreach (var obj in Objects.Values)
                {
                    string raw = obj.Attributes.GetUserString(RecordKey);
                    if (!String.IsNullOrEmpty(raw))
                    {
                        if (Encoding.UTF8.GetByteCount(raw) > 65536)
                            throw new ArgumentException("Component metadata exceeds 64 KiB: " + obj.Id);
                        var map = ParseMap(raw);
                        Maps[obj.Id] = map;
                        RawMaps[obj.Id] = raw;
                        foreach (var field in map.Properties())
                        {
                            var record = (JObject)field.Value;
                            var node = ParseNode(record);
                            if (!groups.TryGetValue(node.GroupId, out Group group))
                                throw new ArgumentException("Component metadata names a missing Rhino group: " + node.Id);
                            if (!doc.Groups.GroupMembers(group.Index).Any(member => member.Id == obj.Id))
                                throw new ArgumentException("Detached or copied Component metadata: " + obj.Id);
                            if (Nodes.ContainsKey(node.Id) || Nodes.Values.Any(n => n.GroupId == node.GroupId))
                                throw new ArgumentException("Duplicate Component record or group identity: " + node.Id);
                            node.Group = group;
                            node.HostId = obj.Id;
                            node.Actual = new HashSet<Guid>(doc.Groups.GroupMembers(group.Index).Select(member => member.Id));
                            Nodes.Add(node.Id, node);
                        }
                    }
                    string owner = obj.Attributes.GetUserString(OwnerKey);
                    if (!String.IsNullOrEmpty(owner)) Owners.Add(obj.Id, owner);
                }
                RecomputeParents();
                foreach (var own in Owners)
                {
                    if (!Nodes.TryGetValue(own.Value, out Node node) || !node.Actual.Contains(own.Key))
                        throw new ArgumentException("Copied or detached Component ownership stamp: " + own.Key);
                }
                var memberships = new Dictionary<Guid, List<Node>>();
                foreach (var node in Nodes.Values)
                {
                    foreach (var id in node.Actual)
                    {
                        if (!Objects.TryGetValue(id, out RhinoObject obj) || obj.IsReference ||
                            !String.IsNullOrEmpty(obj.Attributes.GetUserString("$TempBlockEditUserData$")))
                            throw new ArgumentException("A registered group contains an unavailable, referenced or BlockEdit object: " + id);
                        if (!memberships.TryGetValue(id, out List<Node> membershipsForObject))
                        {
                            membershipsForObject = new List<Node>();
                            memberships.Add(id, membershipsForObject);
                        }
                        membershipsForObject.Add(node);
                    }
                }
                foreach (var pair in memberships)
                {
                    Owners.TryGetValue(pair.Key, out string owner);
                    if (owner != null)
                    {
                        if (pair.Value.Any(node => node.Id != owner && !IsAncestor(node.Id, owner)))
                            throw new ArgumentException("A group contains an object owned by an unrelated Component: " + pair.Key);
                        continue;
                    }
                    var deepest = pair.Value.Where(node => !pair.Value.Any(other =>
                        other.Id != node.Id && IsAncestor(node.Id, other.Id))).ToArray();
                    if (deepest.Length != 1 || pair.Value.Any(node =>
                        node.Id != deepest[0].Id && !IsAncestor(node.Id, deepest[0].Id)))
                        throw new ArgumentException("An unowned group member has incomparable registered groups: " + pair.Key);
                    PendingOwners.Add(pair.Key, deepest[0].Id);
                }
                Recompute();
                foreach (var node in Nodes.Values)
                    if (node.Effective.Count == 0)
                        throw new ArgumentException("Registered Component has an empty subtree: " + node.Id);
            }

            internal void RecomputeParents()
            {
                foreach (var node in Nodes.Values) node.Parent = null;
                foreach (var parent in Nodes.Values)
                    foreach (string id in parent.Children)
                    {
                        if (!Nodes.TryGetValue(id, out Node child))
                            throw new ArgumentException("Child Component is missing from this saved document: " + id);
                        if (child.Id == parent.Id)
                            throw new ArgumentException("A Component cannot contain itself.");
                        if (child.Parent != null)
                            throw new ArgumentException("Child already has a parent; detach explicitly before reparenting: " + id);
                        child.Parent = parent.Id;
                    }
                foreach (var node in Nodes.Values)
                {
                    var seen = new HashSet<string>();
                    string current = node.Id;
                    while (current != null)
                    {
                        if (!seen.Add(current))
                            throw new ArgumentException("Component hierarchy contains a cycle: " + node.Id);
                        if (seen.Count > MaxDepth)
                            throw new ArgumentException("Component hierarchy depth exceeds 64.");
                        current = Nodes[current].Parent;
                    }
                }
            }

            internal void Recompute()
            {
                RecomputeParents();
                foreach (var node in Nodes.Values)
                {
                    node.Direct.Clear(); node.Pending.Clear(); node.Effective.Clear();
                    node.RequiresSync = false;
                }
                foreach (var own in Owners)
                {
                    if (!Nodes.TryGetValue(own.Value, out Node node))
                        throw new ArgumentException("An object refers to an unknown Component: " + own.Key);
                    node.Direct.Add(own.Key);
                }
                foreach (var pending in PendingOwners)
                {
                    if (!Owners.ContainsKey(pending.Key))
                    {
                        if (!Nodes.TryGetValue(pending.Value, out Node node))
                            throw new ArgumentException("A pending object refers to an unknown Component.");
                        node.Pending.Add(pending.Key);
                    }
                }
                foreach (var node in Nodes.Values) Compute(node.Id, new HashSet<string>());
                foreach (var node in Nodes.Values)
                    node.RequiresSync = node.Effective.Any(id => PendingOwners.ContainsKey(id)) ||
                        !node.Actual.SetEquals(node.Effective);
            }

            private HashSet<Guid> Compute(string id, HashSet<string> visited)
            {
                var node = Nodes[id];
                if (visited.Contains(id)) return node.Effective;
                visited.Add(id);
                node.Effective.UnionWith(node.Direct);
                node.Effective.UnionWith(node.Pending);
                foreach (var child in node.Children) node.Effective.UnionWith(Compute(child, visited));
                return node.Effective;
            }

            internal bool IsAncestor(string possibleAncestor, string child)
            {
                if (!Nodes.ContainsKey(child)) return false;
                string parent = Nodes[child].Parent;
                while (parent != null)
                {
                    if (parent == possibleAncestor) return true;
                    parent = Nodes[parent].Parent;
                }
                return false;
            }

            internal HashSet<string> Ancestors(string id)
            {
                var result = new HashSet<string>();
                while (Nodes.TryGetValue(id, out Node node) && node.Parent != null)
                {
                    result.Add(node.Parent);
                    id = node.Parent;
                }
                return result;
            }

            internal HashSet<string> Subtree(string id)
            {
                var result = new HashSet<string>();
                void Add(string current)
                {
                    if (!result.Add(current)) return;
                    foreach (var child in Nodes[current].Children) Add(child);
                }
                Add(id);
                return result;
            }

            internal JObject Snapshot(string id)
            {
                Node node = Nodes[id];
                var direct = node.Direct.OrderBy(value => value).ToArray();
                var effective = node.Effective.OrderBy(value => value).ToArray();
                var pending = effective.Where(value => !Owners.ContainsKey(value)).ToArray();
                var pendingRows = Describe(pending);
                foreach (JObject row in pendingRows)
                {
                    var obj = Objects[Guid.Parse((string)row["rhino_guid"])];
                    if (obj.Geometry is TextDot note)
                    {
                        row["text"] = note.Text == null ? null : note.Text.Substring(0, Math.Min(note.Text.Length, 512));
                        row["text_limited"] = note.Text != null && note.Text.Length > 512;
                        row["point_mm"] = new JArray(note.Point.X * UnitScale(Doc), note.Point.Y * UnitScale(Doc),
                            note.Point.Z * UnitScale(Doc));
                    }
                }
                return new JObject {
                    ["complete"] = true, ["live_verified"] = true,
                    ["component_id"] = node.Id, ["model_path"] = Doc.Path,
                    ["rhino_group_id"] = node.GroupId.ToString("D"), ["name"] = node.Name,
                    ["scene_ids"] = new JArray(node.Scenes), ["child_component_ids"] = new JArray(node.Children),
                    ["parent_component_id"] = node.Parent == null ? JValue.CreateNull() : new JValue(node.Parent),
                    ["objects"] = Describe(direct), ["object_ids"] = new JArray(direct.Select(value => value.ToString("D"))),
                    ["effective_objects"] = Describe(effective),
                    ["effective_object_ids"] = new JArray(effective.Select(value => value.ToString("D"))),
                    ["pending_objects"] = pendingRows,
                    ["requires_sync"] = node.RequiresSync
                };
            }

            internal JArray Describe(IEnumerable<Guid> ids)
            {
                var result = new JArray();
                double scale = UnitScale(Doc);
                foreach (var id in ids)
                {
                    if (!Objects.TryGetValue(id, out RhinoObject obj))
                        throw new ArgumentException("Object is no longer available: " + id);
                    var box = obj.Geometry?.GetBoundingBox(true) ?? BoundingBox.Empty;
                    if (!box.IsValid) throw new ArgumentException("Object has invalid world bounds: " + id);
                    double[] b = { box.Min.X * scale, box.Min.Y * scale, box.Min.Z * scale,
                        box.Max.X * scale, box.Max.Y * scale, box.Max.Z * scale };
                    if (b.Any(v => !Double.IsFinite(v)))
                        throw new ArgumentException("Object has nonfinite bounds: " + id);
                    result.Add(new JObject {
                        ["rhino_guid"] = id.ToString("D"), ["component_id"] = Owners.TryGetValue(id, out string owner)
                            ? new JValue(owner) : JValue.CreateNull(),
                        ["object_type"] = obj.ObjectType.ToString(), ["bounds_mm"] = new JArray(b)
                    });
                }
                return result;
            }
        }

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool mutationStarted = false;
            try
            {
                CheckDocument(doc, request);
                string action = Text(request, "action");
                if (action == "objects")
                {
                    var ids = Ids(request, "object_ids", true);
                    var objects = CurrentObjects(doc, ids);
                    var snapshot = new JArray();
                    double scale = UnitScale(doc);
                    foreach (var obj in objects)
                    {
                        var b = obj.Geometry.GetBoundingBox(true);
                        snapshot.Add(new JObject {
                            ["rhino_guid"] = obj.Id.ToString("D"),
                            ["component_id"] = obj.Attributes.GetUserString(OwnerKey),
                            ["object_type"] = obj.ObjectType.ToString(),
                            ["bounds_mm"] = new JArray(b.Min.X * scale, b.Min.Y * scale, b.Min.Z * scale,
                                b.Max.X * scale, b.Max.Y * scale, b.Max.Z * scale)
                        });
                    }
                    return Bounded(new JObject { ["status"] = "success", ["complete"] = true,
                        ["model_path"] = doc.Path, ["objects"] = snapshot });
                }
                if (action != "upsert" && action != "inspect" && action != "sync" && action != "unregister")
                    throw new ArgumentException("Unsupported Component action.");
                string componentId = Text(request, "component_id");
                var before = new State(doc);
                string groupText = Text(request, "rhino_group_id", false);
                Guid suppliedGroupId = String.IsNullOrEmpty(groupText) ? Guid.Empty : Guid.Parse(groupText);
                if (action == "inspect")
                {
                    if (before.Nodes.TryGetValue(componentId, out Node present))
                    {
                        if (suppliedGroupId != Guid.Empty && suppliedGroupId != present.GroupId)
                            throw new ArgumentException("Component ID and Rhino group ID disagree.");
                        return Bounded(new JObject { ["status"] = "success",
                            ["component"] = before.Snapshot(componentId),
                            ["affected_components"] = RelatedSnapshots(before, componentId, request) });
                    }
                    if (suppliedGroupId == Guid.Empty || request["expected_object_ids"] == null)
                        throw new ArgumentException("The registered Component group is missing.");
                    var group = doc.Groups.FindId(suppliedGroupId);
                    if (group == null || group.IsDeleted)
                        throw new ArgumentException("The registered Rhino group is missing.");
                    Guid[] oldDirect = Ids(request, "expected_object_ids", true);
                    string[] oldChildren = request["expected_child_component_ids"] == null
                        ? new string[0] : Strings(request, "expected_child_component_ids", true);
                    Guid[] oldEffective = request["expected_effective_object_ids"] == null
                        ? oldDirect : Ids(request, "expected_effective_object_ids", true);
                    var proof = UnregisteredSnapshot(doc, before, group, componentId,
                        oldDirect, oldChildren, oldEffective);
                    return Bounded(new JObject { ["status"] = "success", ["component"] = proof,
                        ["affected_components"] = new JArray(oldChildren.Select(id => before.Snapshot(id))) });
                }
                before.Nodes.TryGetValue(componentId, out Node prior);
                if (prior != null && suppliedGroupId != Guid.Empty && prior.GroupId != suppliedGroupId)
                    throw new ArgumentException("The Component cannot be rebound to another Rhino group.");
                if (action == "unregister")
                {
                    if (prior == null) throw new ArgumentException("The registered Component is missing.");
                    CheckExpected(before, prior, request);
                    if (prior.Parent != null)
                        throw new ArgumentException("Detach the Component from its parent before unregistering.");
                    if (prior.RequiresSync)
                        throw new ArgumentException("Component group changed; explicitly sync before unregistering.");
                    var direct = new HashSet<Guid>(prior.Direct);
                    var formerChildren = prior.Children.ToArray();
                    var formerEffective = prior.Effective.OrderBy(id => id).ToArray();
                    JObject proof = null;
                    JObject acknowledgement = null;
                    mutationStarted = true;
                    var change = new ScriptExecutor().ExecuteAction(doc, () =>
                    {
                        var maps = CloneMaps(before);
                        RemoveRecord(maps, prior.GroupId);
                        foreach (var id in direct)
                        {
                            var obj = doc.Objects.FindId(id);
                            var attrs = obj.Attributes.Duplicate();
                            attrs.SetUserString(OwnerKey, null);
                            SetMap(attrs, maps, id);
                            if (!doc.Objects.ModifyAttributes(id, attrs, true))
                                throw new InvalidOperationException("Unable to unregister Component owner: " + id);
                        }
                        foreach (var id in maps.Keys.Except(direct))
                        {
                            if (RecordChanged(before, maps, id))
                            {
                                var attrs = doc.Objects.FindId(id).Attributes.Duplicate();
                                SetMap(attrs, maps, id);
                                if (!doc.Objects.ModifyAttributes(id, attrs, true))
                                    throw new InvalidOperationException("Unable to clear the Component record: " + id);
                            }
                        }
                        var after = new State(doc);
                        proof = UnregisteredSnapshot(doc, after, prior.Group, componentId,
                            direct.OrderBy(id => id).ToArray(), formerChildren, formerEffective);
                        var detached = new JArray(formerChildren);
                        var affected = new JArray(formerChildren.Select(id => after.Snapshot(id)));
                        acknowledgement = Bounded(new JObject { ["status"] = "success",
                            ["component_id"] = componentId, ["model_path"] = doc.Path,
                            ["rhino_group_id"] = prior.GroupId.ToString("D"),
                            ["detached_child_component_ids"] = detached,
                            ["affected_components"] = affected });
                        Bounded(new JObject { ["status"] = "success", ["component"] = proof,
                            ["affected_components"] = affected.DeepClone() });
                        return null;
                    });
                    if (change.Status != "success") return MutationError(change);
                    return acknowledgement;
                }
                if (action == "sync")
                {
                    if (prior == null) throw new ArgumentException("The registered Component is missing.");
                    CheckExpected(before, prior, request);
                    var touched = before.Subtree(componentId);
                    touched.UnionWith(before.Ancestors(componentId));
                    var proposal = CopyNodes(before.Nodes);
                    var desiredOwners = new Dictionary<Guid, string>(before.Owners);
                    foreach (var pending in before.PendingOwners)
                        if (before.IsAncestor(componentId, pending.Value) || pending.Value == componentId)
                            desiredOwners.Add(pending.Key, pending.Value);
                    return ApplyChange(doc, before, proposal, desiredOwners, touched, componentId,
                        new HashSet<string>(StringComparer.Ordinal), ref mutationStarted,
                        includeRelatedSnapshots: true);
                }
                // UPsert: a complete list of DIRECT owners, plus an explicit child list.
                string name = Text(request, "name");
                string[] sceneIds = Strings(request, "scene_ids", false);
                Guid[] wanted = Ids(request, "object_ids", true);
                CurrentObjects(doc, wanted);
                string[] children = request["child_component_ids"] == null ||
                    request["child_component_ids"].Type == JTokenType.Null
                    ? (prior?.Children ?? new string[0]) : Strings(request, "child_component_ids", true);
                CheckExpected(before, prior, request);
                foreach (var id in children)
                    if (!before.Nodes.ContainsKey(id))
                        throw new ArgumentException("Missing child Component: " + id);
                Group ordinaryGroup = null;
                if (prior == null && suppliedGroupId != Guid.Empty)
                {
                    ordinaryGroup = doc.Groups.FindId(suppliedGroupId);
                    if (ordinaryGroup == null || ordinaryGroup.IsDeleted || ordinaryGroup.IsReference)
                        throw new ArgumentException("The supplied ordinary Rhino group is unavailable.");
                    if (before.Nodes.Values.Any(node => node.GroupId == suppliedGroupId))
                        throw new ArgumentException("The group is registered to a different Component.");
                }
                var proposalNodes = CopyNodes(before.Nodes);
                var target = prior == null ? new Node { Id = componentId, GroupId = suppliedGroupId,
                    Group = ordinaryGroup, Name = name, Scenes = sceneIds, Children = children,
                    Actual = ordinaryGroup == null ? new HashSet<Guid>() :
                        new HashSet<Guid>(doc.Groups.GroupMembers(ordinaryGroup.Index).Select(o => o.Id)) }
                    : proposalNodes[componentId];
                target.Name = name; target.Scenes = sceneIds; target.Children = children;
                if (prior == null) proposalNodes.Add(componentId, target);
                RecomputeParents(proposalNodes);
                foreach (string childId in children)
                {
                    string oldParent = before.Nodes[childId].Parent;
                    if (oldParent != null && oldParent != componentId)
                        throw new ArgumentException("Detach the child from its old parent before attaching: " + childId);
                }
                var desired = new Dictionary<Guid, string>(before.Owners);
                if (prior != null)
                    foreach (var id in prior.Direct) desired.Remove(id);
                foreach (var id in wanted)
                {
                    if (desired.TryGetValue(id, out string other) && other != componentId)
                        throw new ArgumentException("Object already belongs to another Component: " + id);
                    if (before.PendingOwners.TryGetValue(id, out string pendingOwner) && pendingOwner != componentId)
                        throw new ArgumentException("Adopt pending group objects through their deepest Component: " + id);
                    desired[id] = componentId;
                }
                var projected = Projection(before, proposalNodes, desired);
                if (projected[componentId].Effective.Count == 0)
                    throw new ArgumentException("A Component must contain a direct object or a nonempty descendant.");
                if (ordinaryGroup != null && !projected[componentId].Effective.SetEquals(target.Actual))
                    throw new ArgumentException("Adopt an ordinary Rhino group with its exact direct/descendant member set.");
                var touchedNodes = new HashSet<string>(StringComparer.Ordinal) { componentId };
                if (prior != null) touchedNodes.UnionWith(before.Ancestors(componentId));
                touchedNodes.UnionWith(Ancestors(proposalNodes, componentId));
                return ApplyChange(doc, before, proposalNodes, desired, touchedNodes, componentId,
                    new HashSet<string>(StringComparer.Ordinal) { componentId }, ref mutationStarted);
            }
            catch (Exception error)
            {
                return new JObject { ["status"] = "error", ["error_code"] = "component_error",
                    ["message"] = error.Message,
                    ["mutation_applied"] = mutationStarted ? JValue.CreateNull() : new JValue(false),
                    ["requires_reconciliation"] = mutationStarted };
            }
        }

        private static JObject ApplyChange(RhinoDoc doc, State before, Dictionary<string, Node> proposed,
            Dictionary<Guid, string> owners, HashSet<string> touched, string primary,
            HashSet<string> changedRecords, ref bool mutationStarted, bool includeRelatedSnapshots = false)
        {
            var projection = Projection(before, proposed, owners);
            foreach (var node in projection.Values)
                if (node.Effective.Count == 0) throw new ArgumentException("Component subtree is empty: " + node.Id);
            // Affected snapshots also cover children whose derived parent changes.
            var reportIds = new HashSet<string>(touched, StringComparer.Ordinal);
            reportIds.UnionWith(before.Nodes.ContainsKey(primary) ? before.Subtree(primary) : new HashSet<string>());
            reportIds.UnionWith(Subtree(projection, primary));
            var oldSnapshots = new Dictionary<string, JObject>(StringComparer.Ordinal);
            foreach (var id in reportIds)
                if (before.Nodes.ContainsKey(id)) oldSnapshots[id] = before.Snapshot(id);

            bool memberDelta = touched.Any(id => !projection[id].Actual.SetEquals(projection[id].Effective));
            bool ownerDelta = before.Owners.Count != owners.Count ||
                before.Owners.Any(pair => !owners.TryGetValue(pair.Key, out string owner) || owner != pair.Value);
            bool recordDelta = changedRecords.Any(id => !before.Nodes.TryGetValue(id, out Node old) ||
                !RecordEqual(old, projection[id]));
            // Explicit sync of an already clean Component performs no Rhino mutation.
            if (!memberDelta && !ownerDelta && !recordDelta)
            {
                var related = new JArray();
                if (includeRelatedSnapshots)
                    foreach (var id in reportIds.OrderBy(value => value, StringComparer.Ordinal))
                        if (id != primary && before.Nodes.ContainsKey(id))
                            related.Add(before.Snapshot(id));
                return Bounded(new JObject { ["status"] = "success", ["component"] = before.Snapshot(primary),
                    ["affected_components"] = related });
            }

            mutationStarted = true;
            JObject reply = null;
            var update = new ScriptExecutor().ExecuteAction(doc, () =>
            {
                Node newNode = projection[primary];
                if (newNode.Group == null)
                {
                    int index = doc.Groups.Add("Component " + primary);
                    if (index < 0) throw new InvalidOperationException("Could not create the Component group.");
                    newNode.Group = doc.Groups[index];
                    newNode.GroupId = newNode.Group.Id;
                    newNode.Actual.Clear();
                }
                var maps = CloneMaps(before);
                var recordGroups = new HashSet<Guid>();
                foreach (var id in touched)
                {
                    Node node = projection[id];
                    if (node.GroupId == Guid.Empty || node.Group == null)
                        throw new InvalidOperationException("A registered group has no stable Rhino group GUID.");
                    // A record can remain on its old host only while that host is still in this group.
                    var old = before.Nodes.TryGetValue(id, out Node existing) ? existing : null;
                    if (changedRecords.Contains(id) || old == null ||
                        !node.Effective.Contains(old.HostId))
                        recordGroups.Add(node.GroupId);
                }
                foreach (Guid groupId in recordGroups) RemoveRecord(maps, groupId);
                foreach (var id in touched)
                {
                    Node node = projection[id];
                    if (!recordGroups.Contains(node.GroupId)) continue;
                    Guid host = before.Nodes.TryGetValue(id, out Node old) && node.Effective.Contains(old.HostId)
                        ? old.HostId : node.Effective.OrderBy(value => value).First();
                    if (!maps.TryGetValue(host, out JObject hostMap))
                        maps[host] = hostMap = new JObject();
                    hostMap[node.GroupId.ToString("D")] = node.ToRecord();
                }
                var affectedObjects = new HashSet<Guid>(owners.Keys);
                affectedObjects.UnionWith(before.Owners.Keys);
                affectedObjects.UnionWith(maps.Keys);
                affectedObjects.UnionWith(before.Maps.Keys);
                foreach (var id in touched)
                {
                    affectedObjects.UnionWith(projection[id].Effective);
                    if (before.Nodes.TryGetValue(id, out Node previous))
                        affectedObjects.UnionWith(previous.Actual);
                }
                foreach (var id in affectedObjects.OrderBy(value => value))
                {
                    if (!before.Objects.ContainsKey(id))
                        throw new InvalidOperationException("An object disappeared during Component mutation: " + id);
                    var obj = doc.Objects.FindId(id);
                    if (obj == null || obj.IsDeleted)
                        throw new InvalidOperationException("An object disappeared during Component mutation: " + id);
                    var attrs = obj.Attributes.Duplicate();
                    bool changed = false;
                    foreach (var nodeId in touched)
                    {
                        Node node = projection[nodeId];
                        bool has = (attrs.GetGroupList() ?? new int[0]).Contains(node.Group.Index);
                        bool want = node.Effective.Contains(id);
                        if (has == want) continue;
                        if (want) attrs.AddToGroup(node.Group.Index);
                        else attrs.RemoveFromGroup(node.Group.Index);
                        changed = true;
                    }
                    string owner = owners.TryGetValue(id, out string value) ? value : null;
                    if (obj.Attributes.GetUserString(OwnerKey) != owner)
                    {
                        attrs.SetUserString(OwnerKey, owner);
                        changed = true;
                    }
                    if (RecordChanged(before, maps, id))
                    {
                        SetMap(attrs, maps, id);
                        changed = true;
                    }
                    if (changed && !doc.Objects.ModifyAttributes(id, attrs, true))
                        throw new InvalidOperationException("Could not change Component member: " + id);
                }
                var after = new State(doc);
                if (!after.Nodes.ContainsKey(primary))
                    throw new InvalidOperationException("Native Component record did not survive the group update.");
                if (!after.Nodes[primary].Children.SequenceEqual(projection[primary].Children) ||
                    !after.Nodes[primary].Direct.SetEquals(projection[primary].Direct) ||
                    after.Nodes[primary].Name != projection[primary].Name ||
                    !after.Nodes[primary].Scenes.SequenceEqual(projection[primary].Scenes))
                    throw new InvalidOperationException("Native Component mutation differs from the requested identity and ownership.");
                foreach (var id in touched)
                    if (!after.Nodes[id].Actual.SetEquals(projection[id].Effective))
                        throw new InvalidOperationException("Native group aggregation differs from the expected subtree: " + id);
                var affected = new JArray();
                foreach (string id in reportIds.OrderBy(value => value, StringComparer.Ordinal))
                {
                    if (id == primary || !after.Nodes.ContainsKey(id)) continue;
                    var current = after.Snapshot(id);
                    if (includeRelatedSnapshots || !oldSnapshots.TryGetValue(id, out JObject previous) ||
                        !JToken.DeepEquals(previous, current))
                        affected.Add(current);
                }
                reply = Bounded(new JObject { ["status"] = "success",
                    ["component"] = after.Snapshot(primary), ["affected_components"] = affected });
                return null;
            });
            if (update.Status != "success") return MutationError(update);
            return reply;
        }

        private static Dictionary<string, Node> Projection(State before,
            Dictionary<string, Node> nodes, Dictionary<Guid, string> owners)
        {
            var pending = new Dictionary<Guid, string>(before.PendingOwners);
            foreach (var id in owners.Keys) pending.Remove(id);
            RecomputeParents(nodes);
            foreach (var node in nodes.Values)
            {
                node.Direct.Clear();
                node.Pending.Clear();
                node.Effective.Clear();
                node.RequiresSync = false;
            }
            foreach (var pair in owners)
            {
                if (!nodes.TryGetValue(pair.Value, out Node node))
                    throw new ArgumentException("A proposed direct owner is missing: " + pair.Value);
                node.Direct.Add(pair.Key);
            }
            foreach (var pair in pending)
                if (nodes.TryGetValue(pair.Value, out Node node)) node.Pending.Add(pair.Key);
            var visited = new HashSet<string>();
            HashSet<Guid> Compute(string id)
            {
                Node node = nodes[id];
                if (visited.Contains(id)) return node.Effective;
                visited.Add(id);
                node.Effective.UnionWith(node.Direct);
                node.Effective.UnionWith(node.Pending);
                foreach (var child in node.Children) node.Effective.UnionWith(Compute(child));
                return node.Effective;
            }
            foreach (var node in nodes.Values) Compute(node.Id);
            return nodes;
        }

        private static Dictionary<string, Node> CopyNodes(Dictionary<string, Node> source) =>
            source.ToDictionary(pair => pair.Key, pair => pair.Value.Copy(), StringComparer.Ordinal);

        private static void RecomputeParents(Dictionary<string, Node> nodes)
        {
            foreach (var node in nodes.Values) node.Parent = null;
            foreach (var node in nodes.Values)
                foreach (var childId in node.Children)
                {
                    if (!nodes.TryGetValue(childId, out Node child))
                        throw new ArgumentException("Child Component does not exist: " + childId);
                    if (node.Id == child.Id || child.Parent != null)
                        throw new ArgumentException("A child may have only one parent and cannot contain itself: " + childId);
                    child.Parent = node.Id;
                }
            foreach (var node in nodes.Values)
            {
                var seen = new HashSet<string>();
                string id = node.Id;
                while (id != null)
                {
                    if (!seen.Add(id)) throw new ArgumentException("Component hierarchy is cyclic: " + id);
                    if (seen.Count > MaxDepth) throw new ArgumentException("Component hierarchy exceeds 64 levels.");
                    id = nodes[id].Parent;
                }
            }
        }

        private static HashSet<string> Ancestors(Dictionary<string, Node> nodes, string id)
        {
            var result = new HashSet<string>(StringComparer.Ordinal);
            while (nodes.TryGetValue(id, out Node node) && node.Parent != null)
            {
                result.Add(node.Parent);
                id = node.Parent;
            }
            return result;
        }

        private static HashSet<string> Subtree(Dictionary<string, Node> nodes, string id)
        {
            var result = new HashSet<string>(StringComparer.Ordinal);
            void Visit(string nodeId)
            {
                if (!result.Add(nodeId)) return;
                foreach (var child in nodes[nodeId].Children) Visit(child);
            }
            Visit(id);
            return result;
        }

        private static bool RecordEqual(Node a, Node b) => a.Name == b.Name &&
            a.Scenes.SequenceEqual(b.Scenes) && a.Children.SequenceEqual(b.Children) &&
            a.GroupId == b.GroupId;

        private static void CheckExpected(State state, Node node, JObject request)
        {
            if (request["expected_object_ids"] != null)
            {
                var expected = new HashSet<Guid>(Ids(request, "expected_object_ids", true));
                if (node == null ? expected.Count != 0 : !node.Direct.SetEquals(expected))
                    throw new ArgumentException("Cached direct object ownership changed; inspect and reconcile before editing.");
            }
            if (request["expected_child_component_ids"] != null)
            {
                var expected = Strings(request, "expected_child_component_ids", true);
                if (node == null ? expected.Length != 0 :
                    !new HashSet<string>(node.Children).SetEquals(expected))
                    throw new ArgumentException("Cached child Component relationships changed; inspect before editing.");
            }
            if (request["expected_parent_component_id"] != null)
            {
                string expected = request["expected_parent_component_id"].Type == JTokenType.Null ? null :
                    Text(request, "expected_parent_component_id", false);
                if ((node?.Parent ?? null) != (String.IsNullOrEmpty(expected) ? null : expected))
                    throw new ArgumentException("Cached parent Component relationship changed; inspect before editing.");
            }
            if (request["expected_effective_object_ids"] != null)
            {
                var expected = new HashSet<Guid>(Ids(request, "expected_effective_object_ids", true));
                // Manually added unowned TextDots/objects are not in the cached
                // ownership ledger. They are admissible pending additions for
                // explicit sync, rather than stale owned-member conflicts.
                var registered = node == null ? new HashSet<Guid>() : new HashSet<Guid>(node.Effective);
                registered.ExceptWith(state.PendingOwners.Keys);
                if (!registered.SetEquals(expected))
                    throw new ArgumentException("Cached effective subtree membership changed; inspect and reconcile before editing.");
            }
        }

        // Inspection supplies snapshots for registered ancestors, descendants, and
        // previous cached relationship peers so the ledger can reconcile Undo.
        private static JArray RelatedSnapshots(State state, string componentId, JObject request)
        {
            var ids = state.Ancestors(componentId);
            ids.UnionWith(state.Subtree(componentId));
            string formerParent = request["expected_parent_component_id"]?.Type == JTokenType.String
                ? (string)request["expected_parent_component_id"] : null;
            if (!String.IsNullOrEmpty(formerParent) && state.Nodes.ContainsKey(formerParent))
            {
                ids.Add(formerParent);
                ids.UnionWith(state.Ancestors(formerParent));
            }
            if (request["expected_child_component_ids"] is JArray expectedChildren)
                foreach (var token in expectedChildren)
                {
                    string id = (string)token;
                    if (id == null || !state.Nodes.ContainsKey(id)) continue;
                    ids.UnionWith(state.Subtree(id));
                    ids.UnionWith(state.Ancestors(id));
                }
            ids.Remove(componentId);
            return new JArray(ids.OrderBy(id => id, StringComparer.Ordinal)
                .Select(id => state.Snapshot(id)));
        }

        private static JObject UnregisteredSnapshot(RhinoDoc doc, State state, Group group,
            string componentId, Guid[] expectedDirect, string[] expectedChildren, Guid[] expectedEffective)
        {
            if (group.IsReference || group.IsDeleted)
                throw new ArgumentException("The former Rhino group is unavailable.");
            if (expectedChildren.Distinct(StringComparer.Ordinal).Count() != expectedChildren.Length)
                throw new ArgumentException("Former child identities are duplicated.");
            var effective = new HashSet<Guid>(expectedDirect);
            foreach (string childId in expectedChildren)
            {
                if (!state.Nodes.TryGetValue(childId, out Node child) || child.Parent != null)
                    throw new ArgumentException("A detached child is missing, still parented, or its registration changed: " + childId);
                effective.UnionWith(child.Effective);
            }
            if (!effective.SetEquals(expectedEffective))
                throw new ArgumentException("Former direct/child subtree and cached effective membership disagree.");
            var members = doc.Groups.GroupMembers(group.Index);
            if (!new HashSet<Guid>(members.Select(obj => obj.Id)).SetEquals(effective))
                throw new ArgumentException("Retained ordinary group no longer matches the former Component subtree.");
            foreach (var id in expectedDirect)
            {
                var obj = doc.Objects.FindId(id);
                if (obj == null || obj.IsDeleted)
                    throw new ArgumentException("Former direct owner object is missing: " + id);
                if (!String.IsNullOrEmpty(obj.Attributes.GetUserString(OwnerKey)) ||
                    (state.Maps.TryGetValue(obj.Id, out JObject map) && map.Property(group.Id.ToString("D")) != null))
                    throw new ArgumentException("Former direct member still has ownership or parent group metadata.");
            }
            if (state.Owners.Values.Any(owner => owner == componentId) ||
                state.Nodes.ContainsKey(componentId))
                throw new ArgumentException("A Component owner or record remains outside the retained group.");
            if (state.Maps.Values.Any(map => map.Property(group.Id.ToString("D")) != null))
                throw new ArgumentException("A copied or detached former Component group record remains.");
            return new JObject { ["complete"] = true, ["registration_status"] = "unregistered",
                ["component_id"] = componentId, ["model_path"] = doc.Path,
                ["rhino_group_id"] = group.Id.ToString("D"), ["scene_ids"] = new JArray(),
                ["objects"] = state.Describe(expectedDirect.OrderBy(id => id)),
                ["object_ids"] = new JArray(expectedDirect.OrderBy(id => id).Select(id => id.ToString("D"))),
                ["effective_objects"] = state.Describe(effective.OrderBy(id => id)),
                ["effective_object_ids"] = new JArray(effective.OrderBy(id => id).Select(id => id.ToString("D"))),
                ["child_component_ids"] = new JArray(),
                ["detached_child_component_ids"] = new JArray(expectedChildren),
                ["parent_component_id"] = JValue.CreateNull(), ["pending_objects"] = new JArray(),
                ["requires_sync"] = false, ["live_verified"] = true };
        }

        private static JObject ParseMap(string raw)
        {
            var parsed = JObject.Parse(raw);
            if (parsed.Property("component_id") != null && parsed.Property("rhino_group_id") != null)
            {
                // Unshipped single-level records are readable without rewriting Rhino on inspect.
                var legacyId = Guid.Parse(Text(parsed, "rhino_group_id")).ToString("D");
                if (parsed["child_component_ids"] == null) parsed["child_component_ids"] = new JArray();
                return new JObject { [legacyId] = parsed };
            }
            var normalized = new JObject();
            foreach (var entry in parsed.Properties())
            {
                if (!Guid.TryParse(entry.Name, out Guid key) || key == Guid.Empty ||
                    !(entry.Value is JObject record))
                    throw new ArgumentException("Component record map requires group GUID keys and record objects.");
                string canonical = key.ToString("D");
                if (normalized.Property(canonical) != null)
                    throw new ArgumentException("Duplicate Component group GUID in record map.");
                if (record["child_component_ids"] == null) record["child_component_ids"] = new JArray();
                if (Guid.Parse(Text(record, "rhino_group_id")) != key)
                    throw new ArgumentException("Component map key and embedded group GUID differ.");
                normalized[canonical] = record;
            }
            return normalized;
        }

        private static Node ParseNode(JObject record)
        {
            if (record.Properties().Any(field => !Fields.Contains(field.Name)))
                throw new ArgumentException("Component metadata contains unsupported record fields.");
            Guid groupId = Guid.Parse(Text(record, "rhino_group_id"));
            if (groupId == Guid.Empty) throw new ArgumentException("Component group GUID is empty.");
            return new Node { Id = Text(record, "component_id"), GroupId = groupId,
                Name = Text(record, "name"), Scenes = Strings(record, "scene_ids", false),
                Children = Strings(record, "child_component_ids", true) };
        }

        private static Dictionary<Guid, JObject> CloneMaps(State state) =>
            state.Maps.ToDictionary(pair => pair.Key, pair => (JObject)pair.Value.DeepClone());

        private static void RemoveRecord(Dictionary<Guid, JObject> maps, Guid groupId)
        {
            string key = groupId.ToString("D");
            foreach (var map in maps.Values) map.Remove(key);
        }

        private static bool RecordChanged(State before, Dictionary<Guid, JObject> maps, Guid objectId)
        {
            var prior = before.Maps.TryGetValue(objectId, out JObject previous) ? previous : new JObject();
            var next = maps.TryGetValue(objectId, out JObject current) ? current : new JObject();
            // A legacy singleton can be read as a one-record map without rewriting
            // unrelated objects. Convert it only when this object's records change.
            return !JToken.DeepEquals(prior, next);
        }

        private static void SetMap(ObjectAttributes attrs, Dictionary<Guid, JObject> maps, Guid objectId)
        {
            string value = maps.TryGetValue(objectId, out JObject map) && map.Count > 0
                ? map.ToString(Formatting.None) : null;
            if (!attrs.SetUserString(RecordKey, value))
                throw new InvalidOperationException("Could not store undoable Component record.");
        }

        private static RhinoObject[] CurrentObjects(RhinoDoc doc, Guid[] ids)
        {
            if (ids.Length > MaxObjects) throw new ArgumentException("Component exceeds 4096 direct objects.");
            var result = ids.Select(id => doc.Objects.FindId(id)).ToArray();
            if (result.Any(o => o == null || o.IsDeleted || o.IsReference || o.IsInstanceDefinitionGeometry ||
                o.Attributes.Space != ActiveSpace.ModelSpace ||
                !String.IsNullOrEmpty(o.Attributes.GetUserString("$TempBlockEditUserData$"))))
                throw new ArgumentException("Use editable top-level model objects; references and BlockEdit clones are excluded.");
            foreach (var obj in result)
                if (obj.Geometry == null || !obj.Geometry.GetBoundingBox(true).IsValid)
                    throw new ArgumentException("Object has invalid world bounds: " + obj.Id);
            return result;
        }

        private static void CheckDocument(RhinoDoc doc, JObject request)
        {
            if (doc == null) throw new ArgumentException("No active Rhino document.");
            if (request == null || Encoding.UTF8.GetByteCount(request.ToString(Formatting.None)) > MaxBytes)
                throw new ArgumentException("Missing or oversized Component request.");
            string expected = Text(request, "expected_model_path");
            if (!Path.IsPathRooted(expected) || String.IsNullOrWhiteSpace(doc.Path) ||
                !String.Equals(Path.GetFullPath(expected), Path.GetFullPath(doc.Path), StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("The active saved Rhino document differs from expected_model_path.");
        }

        private static string Text(JObject request, string key, bool required = true)
        {
            var token = request[key];
            if (token == null && !required) return "";
            if (token?.Type != JTokenType.String)
                throw new ArgumentException(key + " must be a string.");
            string value = (string)token;
            if ((required && String.IsNullOrWhiteSpace(value)) || value.Length > 1024)
                throw new ArgumentException(key + " is empty or too long.");
            return value;
        }

        private static string[] Strings(JObject request, string key, bool allowEmpty)
        {
            if (!(request[key] is JArray array) || array.Count > MaxObjects ||
                (!allowEmpty && array.Count == 0) ||
                array.Any(token => token.Type != JTokenType.String ||
                    String.IsNullOrWhiteSpace((string)token) || ((string)token).Length > 1024))
                throw new ArgumentException(key + " must be a bounded array of nonempty strings.");
            var result = array.Values<string>().ToArray();
            if (result.Distinct(StringComparer.Ordinal).Count() != result.Length)
                throw new ArgumentException(key + " contains duplicates.");
            return result;
        }

        private static Guid[] Ids(JObject request, string key, bool allowEmpty)
        {
            var ids = Strings(request, key, allowEmpty).Select(Guid.Parse).ToArray();
            if (ids.Any(id => id == Guid.Empty) || ids.Distinct().Count() != ids.Length)
                throw new ArgumentException("Object GUIDs must be unique and nonempty.");
            return ids;
        }

        private static double UnitScale(RhinoDoc doc)
        {
            double scale = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Millimeters);
            if (doc.ModelUnitSystem == UnitSystem.None || !Double.IsFinite(scale) || scale <= 0)
                throw new ArgumentException("Set supported model units before registering Components.");
            return scale;
        }

        private static JObject MutationError(ScriptResult result) =>
            new JObject { ["status"] = "error", ["error_code"] = "component_update_failed",
                ["message"] = result.Message, ["requires_reconciliation"] = true,
                ["mutation_applied"] = JValue.CreateNull() };

        private static JObject Bounded(JObject value)
        {
            if (Encoding.UTF8.GetByteCount(value.ToString(Formatting.None)) > MaxBytes)
                throw new ArgumentException("Component response exceeds 2 MiB; narrow the hierarchy.");
            return value;
        }
    }
}
