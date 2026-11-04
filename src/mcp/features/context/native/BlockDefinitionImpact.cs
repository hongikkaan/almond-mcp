using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    // Count placed occurrences, not just the reusable member IDs in a definition.
    // Read-only and bounded; no definition is made unique or modified here.
    public static class BlockDefinitionImpact
    {
        const int MaxRows = 512, MaxVisits = 100000, MaxDepth = 64;

        public static JObject Observe(RhinoDoc doc, InstanceDefinition target, bool stableModel)
        {
            var occurrences = new JArray();
            var roots = new Dictionary<Guid, InstanceObject>();
            var childrenByDefinition = new Dictionary<Guid, InstanceObject[]>();
            int visits = 0, count = 0, pathBytes = 0, readMembers = 0;
            bool scanComplete = true, stopped = false;
            var limits = new HashSet<string>();
            Action<InstanceObject, InstanceObject, Guid[], HashSet<Guid>> visit = null;
            visit = (item, root, prefix, ancestors) =>
            {
                if (stopped) return;
                if (++visits > MaxVisits) { stopped = true; scanComplete = false; limits.Add("visit_limit"); return; }
                var definition = item.InstanceDefinition;
                if (definition == null || definition.IsDeleted) { scanComplete = false; limits.Add("definition_unavailable"); return; }
                var path = prefix.Concat(new[] { item.Id }).ToArray();
                if (definition.Id == target.Id)
                {
                    count++;
                    roots[root.Id] = root;
                    var row = new JObject {
                        ["root_object_id"] = root.Id.ToString(),
                        ["root_space"] = root.Attributes.Space.ToString(),
                        ["block_path_ids"] = new JArray(path.Skip(1).Select(id => id.ToString())) };
                    int bytes = Encoding.UTF8.GetByteCount(row.ToString(Formatting.None));
                    if (occurrences.Count < MaxRows && pathBytes + bytes <= 96 * 1024)
                    { occurrences.Add(row); pathBytes += bytes; }
                }
                if (ancestors.Contains(definition.Id)) { scanComplete = false; limits.Add("cycle"); return; }
                if (!childrenByDefinition.TryGetValue(definition.Id, out var children))
                {
                    // A repeated definition may contain thousands of ordinary objects.
                    // Read it once, and budget all members, not just block children.
                    if (definition.ObjectCount > MaxVisits - readMembers)
                    { stopped = true; scanComplete = false; limits.Add("definition_member_limit"); return; }
                    var members = definition.GetObjects();
                    readMembers += members.Length;
                    if (readMembers > MaxVisits)
                    { stopped = true; scanComplete = false; limits.Add("definition_member_limit"); return; }
                    children = members.OfType<InstanceObject>().Where(o => !o.IsDeleted).ToArray();
                    childrenByDefinition.Add(definition.Id, children);
                }
                if (path.Length >= MaxDepth && children.Length != 0) { scanComplete = false; limits.Add("depth_limit"); return; }
                var next = new HashSet<Guid>(ancestors) { definition.Id };
                foreach (var child in children)
                {
                    visit(child, root, path, next);
                    if (stopped) break;
                }
            };
            // A definition can also be used in Layout space. Those placements are
            // affected by a definition change even when model-space queries omit them.
            var placed = doc.Objects.GetObjectList(new ObjectEnumeratorSettings {
                NormalObjects = true, HiddenObjects = true, LockedObjects = true,
                ReferenceObjects = true, DeletedObjects = false, IdefObjects = false
            });
            int scanned = 0;
            foreach (var item in placed)
            {
                if (++scanned > MaxVisits) { scanComplete = false; limits.Add("document_object_limit"); break; }
                if (!(item is InstanceObject root) || root.IsDeleted || root.IsInstanceDefinitionGeometry) continue;
                visit(root, root, Array.Empty<Guid>(), new HashSet<Guid>());
                if (stopped) break;
            }
            bool complete = scanComplete && stableModel;
            var containers = target.GetContainers().Where(d => d != null && !d.IsDeleted).ToArray();
            var containerRows = new JArray();
            int containerBytes = 0;
            foreach (var container in containers.Take(MaxRows))
            {
                var row = new JObject { ["definition_id"] = container.Id.ToString(),
                    ["name"] = Name(container.Name), ["is_reference"] = container.IsReference };
                containerBytes += Encoding.UTF8.GetByteCount(row.ToString(Formatting.None));
                if (containerBytes > 32 * 1024) break;
                containerRows.Add(row);
            }
            return new JObject {
                ["definition_id"] = target.Id.ToString(), ["definition_name"] = Name(target.Name),
                ["definition_is_reference"] = target.IsReference, ["update_type"] = target.UpdateType.ToString(),
                ["source_archive_present"] = !String.IsNullOrEmpty(target.SourceArchive),
                ["complete"] = complete, ["document_scan_complete"] = scanComplete,
                ["occurrence_count"] = complete ? new JValue(count) : JValue.CreateNull(),
                ["observed_occurrence_count"] = count,
                ["affected_root_count"] = complete ? new JValue(roots.Count) : JValue.CreateNull(),
                ["observed_affected_root_count"] = roots.Count,
                ["occurrences"] = occurrences, ["occurrences_truncated"] = count > occurrences.Count,
                ["container_definitions"] = containerRows,
                ["container_definitions_truncated"] = containers.Length > containerRows.Count,
                ["limits"] = new JArray(limits.OrderBy(value => value)),
                ["basis"] = "current model and Layout block placements, recursively expanded definition references",
                ["editing_permission"] = "not_granted_by_read_only_analysis",
                ["limitation"] = stableModel
                    ? "A definition edit affects every listed occurrence, including occurrences inside other definitions and Layouts. Container definitions can also be unplaced. Reference/linked definitions require their own supported source-edit workflow. A single-placement intention does not authorize changing a shared definition."
                    : "Editing can hide or replace original placements with working instances. Observed paths are not a complete original impact map; finish editing and inspect again before concluding that a definition has no other uses." };
        }

        static string Name(string value) => value == null || value.Length <= 512 ? value : value.Substring(0, 512) + "…";
    }
}
