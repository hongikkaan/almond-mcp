using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // One read-only entity model is shared by selection summaries and pixel labels.
    // Group containment is derived from strict member-set inclusion, never group index order.
    public static class ObservationEntities
    {
        public sealed class Entity
        {
            public Guid Id;
            public string Name, Kind, Layer;
            public RhinoObject Object;
            public RhinoObject[] Members;
            public Transform ToWorld = Transform.Identity;
            public Guid[] Path;
            public BoundingBox Bounds;
        }

        public static RhinoObject[] ModelObjects(RhinoDoc doc)
        {
            return doc.Objects.GetObjectList(new ObjectEnumeratorSettings
            {
                NormalObjects = true, HiddenObjects = false, LockedObjects = true,
                ReferenceObjects = true, DeletedObjects = false, IdefObjects = false, VisibleFilter = true
            }).Where(o => o != null && !o.IsDeleted && !o.IsInstanceDefinitionGeometry).ToArray();
        }

        public static Entity ObjectEntity(RhinoDoc doc, RhinoObject obj, Transform parent, Guid[] prefix)
        {
            var block = obj as InstanceObject;
            var bounds = obj.Geometry.GetBoundingBox(true);
            bounds.Transform(parent);
            var layer = doc.Layers.FindIndex(obj.Attributes.LayerIndex);
            return new Entity
            {
                Id = obj.Id, Object = obj, Kind = block == null ? obj.ObjectType.ToString() : "Block",
                Name = String.IsNullOrWhiteSpace(obj.Name) && block != null ? block.InstanceDefinition.Name : obj.Name ?? "",
                Layer = layer == null ? null : layer.FullPath,
                ToWorld = block == null ? parent : parent * block.InstanceXform,
                Path = (prefix ?? Array.Empty<Guid>()).Concat(new[] { obj.Id }).ToArray(), Bounds = bounds
            };
        }

        public static List<Entity> Roots(RhinoDoc doc, RhinoObject[] objects, Guid? excludedGroup = null)
        {
            var present = new HashSet<Guid>(objects.Select(o => o.Id));
            var groups = new List<Entity>();
            foreach (var group in doc.Groups)
            {
                if (group == null || group.IsDeleted || group.Id == excludedGroup) continue;
                var members = doc.Groups.GroupMembers(group.Index) ?? Array.Empty<RhinoObject>();
                if (members.Length == 0 || members.Any(o => o == null || !present.Contains(o.Id))) continue;
                if (excludedGroup.HasValue && members.Length >= objects.Length) continue;
                var bounds = BoundingBox.Empty;
                foreach (var member in members) bounds.Union(member.Geometry.GetBoundingBox(true));
                groups.Add(new Entity { Id = group.Id, Name = group.Name ?? "", Kind = "Group",
                    Members = members, Bounds = bounds, Path = new[] { group.Id } });
            }
            var roots = groups.Where(g => !groups.Any(parent => parent.Id != g.Id &&
                parent.Members.Length > g.Members.Length &&
                !g.Members.Select(o => o.Id).Except(parent.Members.Select(o => o.Id)).Any())).ToList();
            var covered = new HashSet<Guid>(roots.SelectMany(g => g.Members).Select(o => o.Id));
            roots.AddRange(objects.Where(o => !covered.Contains(o.Id)).Select(o => ObjectEntity(doc, o, Transform.Identity, null)));
            return roots.OrderBy(e => e.Kind).ThenBy(e => e.Name, StringComparer.Ordinal).ThenBy(e => e.Id).ToList();
        }

        public static List<Entity> Expand(RhinoDoc doc, IEnumerable<Entity> roots, int depth, int limit,
            out bool truncated, out bool depthLimited, Func<Entity, bool> visible = null)
        {
            var rows = new List<Entity>();
            bool stopped = false, limited = false;
            Action<Entity, int, HashSet<Guid>> visit = null;
            visit = (entity, level, ancestors) =>
            {
                if (visible != null && !visible(entity)) return;
                if (rows.Count >= limit) { stopped = true; return; }
                rows.Add(entity);
                if (entity.Kind != "Group" && !(entity.Object is InstanceObject)) return;
                if (level >= depth) { limited = true; return; }
                if (ancestors.Contains(entity.Id)) { limited = true; return; }
                var next = new HashSet<Guid>(ancestors) { entity.Id };
                IEnumerable<Entity> children;
                if (entity.Kind == "Group")
                {
                    // Equal-member groups have no authoritative parent relation.
                    children = Roots(doc, entity.Members, entity.Id).Where(e => e.Kind != "Group" ||
                        e.Members.Length < entity.Members.Length);
                }
                else
                {
                    var block = (InstanceObject)entity.Object;
                    children = block.InstanceDefinition.GetObjects().Select(o => ObjectEntity(doc, o, entity.ToWorld, entity.Path));
                }
                foreach (var child in children)
                {
                    visit(child, level + 1, next);
                    if (stopped) break;
                }
            };
            foreach (var root in roots)
            {
                visit(root, 1, new HashSet<Guid>());
                if (stopped) break;
            }
            truncated = stopped;
            depthLimited = limited;
            return rows;
        }

        public static JObject Selection(RhinoDoc doc, int limit, bool recursive, int depth)
        {
            var selected = doc.Objects.GetSelectedObjects(true, false).ToArray();
            var roots = Roots(doc, selected);
            bool truncated, depthLimited;
            var rows = Expand(doc, roots, recursive ? depth : 1, limit, out truncated, out depthLimited);
            return new JObject
            {
                ["total"] = roots.Count, ["selected_object_count"] = selected.Length, ["returned"] = rows.Count,
                ["truncated"] = truncated, ["depth_limited"] = recursive && depthLimited,
                ["recursive"] = recursive,
                ["objects"] = new JArray(rows.Select(e => new JObject
                {
                    ["id"] = e.Id.ToString(), ["name"] = e.Name, ["layer"] = e.Layer,
                    ["type"] = e.Object == null ? e.Kind : e.Object.ObjectType.ToString(),
                    ["member_count"] = e.Members == null ? (e.Object as InstanceObject)?.InstanceDefinition.ObjectCount : e.Members.Length,
                    ["path_ids"] = new JArray(e.Path.Select(id => id.ToString()))
                }))
            };
        }

        public static List<Entity> CaptureRoots(RhinoDoc doc, string kind, Guid id)
        {
            if (kind == "group")
            {
                var group = doc.Groups.FirstOrDefault(g => g != null && !g.IsDeleted && g.Id == id);
                if (group == null) throw new ArgumentException("The group GUID is stale or unavailable.");
                var members = doc.Groups.GroupMembers(group.Index) ?? Array.Empty<RhinoObject>();
                if (members.Length == 0) throw new ArgumentException("The group has no live members.");
                var bounds = BoundingBox.Empty;
                foreach (var member in members) bounds.Union(member.Geometry.GetBoundingBox(true));
                return new List<Entity> { new Entity { Id = group.Id, Name = group.Name ?? "", Kind = "Group",
                    Members = members, Bounds = bounds, Path = new[] { group.Id } } };
            }
            var block = doc.Objects.FindId(id) as InstanceObject;
            if (block == null || block.IsDeleted || block.IsInstanceDefinitionGeometry)
                throw new ArgumentException("The block instance GUID is stale or unavailable; definition GUIDs are not capture targets.");
            return new List<Entity> { ObjectEntity(doc, block, Transform.Identity, null) };
        }

        public static void DrawLabels(RhinoDoc doc, Bitmap bitmap, RhinoViewport viewport,
            IEnumerable<Entity> roots, int depth, JArray warnings)
        {
            bool truncated, depthLimited;
            var rows = Expand(doc, roots, depth, 200, out truncated, out depthLimited,
                entity => entity.Bounds.IsValid && viewport.IsVisible(entity.Bounds));
            if (truncated) warnings.Add("labels: limited to 200 entities; capture a group/block or lower depth for a smaller scope.");
            using (var graphics = Graphics.FromImage(bitmap))
            using (var font = new System.Drawing.Font("Segoe UI", 9f, GraphicsUnit.Pixel))
            using (var background = new SolidBrush(Color.FromArgb(220, 22, 27, 35)))
            using (var foreground = new SolidBrush(Color.White))
            {
                var occupied = new List<RectangleF>();
                foreach (var entity in rows)
                {
                    if (!entity.Bounds.IsValid || !viewport.IsVisible(entity.Bounds)) continue;
                    var point = viewport.WorldToClient(entity.Bounds.Center);
                    float x = (float)(point.X * bitmap.Width / viewport.Size.Width);
                    float y = (float)(point.Y * bitmap.Height / viewport.Size.Height);
                    string name = entity.Name.Length > 64 ? entity.Name.Substring(0, 64) + "…" : entity.Name;
                    string text = (String.IsNullOrWhiteSpace(name) ? entity.Kind : name) + "\n" + entity.Id;
                    var size = graphics.MeasureString(text, font);
                    var rect = new RectangleF(Math.Max(0, Math.Min(x, bitmap.Width - size.Width - 8)),
                        Math.Max(0, Math.Min(y, bitmap.Height - size.Height - 4)), size.Width + 8, size.Height + 4);
                    // A bounded vertical nudge keeps nearby labels readable without hiding entities silently.
                    for (int step = 0; step < 8 && occupied.Any(r => r.IntersectsWith(rect)); step++)
                        rect.Y = Math.Max(0, Math.Min(rect.Y + size.Height + 4, bitmap.Height - rect.Height));
                    occupied.Add(rect);
                    graphics.FillRectangle(background, rect);
                    graphics.DrawString(text, font, foreground, rect.X + 4, rect.Y + 2);
                }
            }
        }
    }
}
