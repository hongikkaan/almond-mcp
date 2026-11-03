using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    public static partial class ObjectObservation
    {
        static ObservationEntities.Entity GroupEntity(RhinoDoc doc, Group group, EditingContext.ObjectScope editing)
        {
            var members = EditingContext.GroupObjects(doc, group, editing, out bool complete, out string basis)
                .Where(o => o != null && !o.IsDeleted && !o.IsInstanceDefinitionGeometry &&
                    o.Attributes.Space != ActiveSpace.PageSpace).ToArray();
            var bounds = BoundingBox.Empty;
            foreach (var member in members) bounds.Union(member.Geometry.GetBoundingBox(true));
            return new ObservationEntities.Entity { Id = group.Id, Name = group.Name ?? "", Kind = "Group",
                Members = members, Bounds = bounds, Path = Array.Empty<Guid>(),
                MembershipComplete = complete, MembershipBasis = basis };
        }

        static List<ObservationEntities.Entity> RequestedGroups(RhinoDoc doc, Guid[] ids, EditingContext.ObjectScope editing = null)
        {
            editing = editing ?? EditingContext.ObserveObjects(doc);
            var result = new List<ObservationEntities.Entity>();
            foreach (var id in ids.OrderBy(value => value))
            {
                var group = doc.Groups.FirstOrDefault(g => g != null && !g.IsDeleted && g.Id == id);
                if (group == null) throw new ArgumentException("Unknown group GUID: " + id);
                result.Add(GroupEntity(doc, group, editing));
            }
            return result;
        }

        static JObject Hierarchy(RhinoDoc doc, string scope, Guid[] groupIds, RhinoObject[] candidates,
            RhinoObject[] matched, HashSet<Guid> visible, HashSet<string> fields,
            bool expandGroups, bool expandBlocks, int depth, int offset, int limit, EditingContext.ObjectScope editing = null)
        {
            editing = editing ?? EditingContext.ObserveObjects(doc);
            var matchedIds = new HashSet<Guid>(matched.Select(o => o.Id));
            Func<Group, ObservationEntities.Entity> groupSource = g => GroupEntity(doc, g, editing);
            var roots = groupIds.Length != 0 ? RequestedGroups(doc, groupIds, editing) :
                ObservationEntities.Roots(doc, matched, null, groupSource, includePartial: scope == "current" || scope == "document");
            // Explicit group roots retain their identity even when filtering selects only some members.
            // The traversal below sees only matched members, so it cannot widen the requested scope.
            var rows = new JArray();
            var budget = new ValueBudget();
            int count = 0, bytes = 0;
            bool depthLimited = false, cycleLimited = false, membershipIncomplete = false;
            Action<ObservationEntities.Entity, int?, int, HashSet<Guid>> visit = null;
            visit = (entity, parent, level, ancestors) =>
            {
                if (++count > 100000) throw new ArgumentException("Hierarchy exceeds 100000 occurrences; narrow scope or depth.");
                int number = count;
                bool group = entity.Kind == "Group";
                var block = entity.Object as InstanceObject;
                var members = group ? entity.Members.Where(o => matchedIds.Contains(o.Id)).ToArray() : null;
                if (group && entity.DefinitionOccurrence)
                    members = entity.Members; // Definition members are already scoped by their root occurrence.
                membershipIncomplete |= group && !entity.MembershipComplete;
                bool hasChildren = group ? members.Length > 0 : block != null && block.InstanceDefinition.ObjectCount > 0;
                bool expand = group ? expandGroups : block != null && expandBlocks;
                string state = group && !entity.MembershipComplete && !hasChildren ? "unavailable" :
                    !hasChildren ? "leaf" : !expand ? "collapsed" : level >= depth ? "depth_limit" :
                    ancestors.Contains(entity.Id) ? "cycle" : "expanded";
                depthLimited |= state == "depth_limit";
                cycleLimited |= state == "cycle";
                if (number > offset && rows.Count < limit)
                {
                    JObject row;
                    if (group)
                    {
                        row = new JObject { ["member_count"] = entity.MembershipComplete ? new JValue(entity.Members.Length) : JValue.CreateNull(),
                            ["observed_member_count"] = entity.Members.Length, ["matched_member_count"] = members.Length,
                            ["membership_complete"] = entity.MembershipComplete,
                            ["all_members_in_scope"] = members.Length == entity.Members.Length,
                            ["membership_basis"] = entity.MembershipBasis };
                        if (fields == null || fields.Contains("id")) row["id"] = entity.Id.ToString();
                        if (fields == null || fields.Contains("name")) row["name"] = entity.Name;
                        if (fields == null || fields.Contains("bounds")) row["bounds"] = Bounds(entity.Bounds);
                    }
                    else
                    {
                        row = Describe(doc, entity.Object, matchedIds, visible, false, budget, fields, 0, 128);
                        if (fields == null || fields.Contains("name")) row["name"] = entity.Name;
                        bool definitionMember = entity.Path.Length > 1;
                        row["root_object_id"] = entity.Path[0].ToString();
                        row["block_path_ids"] = new JArray(entity.Path.Skip(1).Select(id => id.ToString()));
                        row["document_object"] = !definitionMember;
                        if (fields == null || fields.Contains("bounds")) row["bounds"] = Bounds(entity.Bounds);
                        if (definitionMember)
                        {
                            // Definition attributes are not effective inherited occurrence visibility/selection.
                            if (row.ContainsKey("visible")) row["visible"] = JValue.CreateNull();
                            if (row.ContainsKey("selected")) row["selected"] = JValue.CreateNull();
                            row["state_basis"] = "definition attributes; effective occurrence visibility/selection is not evaluated";
                        }
                    }
                    row["entity_kind"] = group ? "group" : block == null ? "object" : "block";
                    row["number"] = number;
                    row["parent_number"] = parent.HasValue ? new JValue(parent.Value) : JValue.CreateNull();
                    row["depth"] = level;
                    row["children_state"] = state;
                    bytes += Encoding.UTF8.GetByteCount(row.ToString(Formatting.None));
                    if (bytes > MaxBytes - 4096) throw new ArgumentException("Hierarchy response exceeds 256 KiB; reduce limit or fields.");
                    rows.Add(row);
                }
                if (state != "expanded") return;
                var next = new HashSet<Guid>(ancestors) { entity.Id };
                IEnumerable<ObservationEntities.Entity> children;
                if (group)
                {
                    children = ObservationEntities.Roots(doc, members, entity.Id, entity.DefinitionOccurrence ? null : groupSource);
                    if (entity.DefinitionOccurrence)
                        children = children.Select(e => Place(doc, e, entity.ToWorld, entity.Path));
                }
                else children = ObservationEntities.Roots(doc, block.InstanceDefinition.GetObjects())
                    .Select(e => Place(doc, e, entity.ToWorld, entity.Path));
                foreach (var child in children) visit(child, number, level + 1, next);
            };
            foreach (var root in roots) visit(root, null, 1, new HashSet<Guid>());
            var answer = new JObject {
                ["status"] = "success", ["schema"] = "almond-object-hierarchy/v1", ["scope"] = scope,
                ["result_mode"] = "hierarchy", ["source_count"] = candidates.Length, ["matched_count"] = matched.Length,
                ["root_count"] = roots.Count, ["hierarchy_count"] = count, ["nodes"] = rows,
                ["offset"] = offset, ["limit"] = limit, ["depth"] = depth,
                ["next_offset"] = offset + rows.Count < count ? new JValue(offset + rows.Count) : JValue.CreateNull(),
                ["complete"] = offset == 0 && rows.Count == count && !membershipIncomplete,
                ["page_complete"] = offset == 0 && rows.Count == count,
                ["membership_complete"] = !membershipIncomplete, ["depth_limited"] = depthLimited,
                ["cycle_limited"] = cycleLimited,
                ["limitations"] = new JArray(
                    "Filters select top-level model objects before grouping or block traversal. Expanded block members retain definition metadata and world bounds.",
                    "Group containment uses strict member-set inclusion. Overlapping/equal-member groups remain separate; an object can appear under several groups.",
                    "number/parent_number describe this traversal, including parents on earlier pages; they are not persistent object handles. Repeat pages with unchanged scope, options and model.",
                    "complete describes pagination at the requested expansion depth; collapsed/depth_limit/cycle nodes do not describe all descendants.",
                    "Only document_object=true rows supply directly editable document object IDs. Block members require root_object_id plus block_path_ids; they are not standalone edit targets.")
            };
            if (Encoding.UTF8.GetByteCount(answer.ToString(Formatting.None)) > MaxBytes)
                return Error("observation_too_large", "Hierarchy response exceeds 256 KiB; reduce limit or fields.");
            return answer;
        }

        static ObservationEntities.Entity Place(RhinoDoc doc, ObservationEntities.Entity entity, Transform parent, Guid[] prefix)
        {
            if (entity.Kind != "Group") return ObservationEntities.ObjectEntity(doc, entity.Object, parent, prefix);
            entity.ToWorld = parent; entity.Path = prefix; entity.DefinitionOccurrence = true;
            var bounds = entity.Bounds; bounds.Transform(parent); entity.Bounds = bounds;
            return entity;
        }
    }
}
