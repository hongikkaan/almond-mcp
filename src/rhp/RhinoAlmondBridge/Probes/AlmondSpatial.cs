using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

// Helpers for nested block traversal, note ownership, and block occurrence resolution.
// No selection or geometry edits.
public static class AlmondSpatial
{
    static void CheckOptions(JObject options, params string[] names)
    {
        if (options == null) throw new ArgumentNullException(nameof(options));
        var unsupported = options.Properties().Select(p => p.Name).Except(names).ToArray();
        if (unsupported.Length > 0)
            throw new ArgumentException("Unsupported options: " + String.Join(", ", unsupported));
    }

    public static RhinoObject[] TopObjects(RhinoDoc doc)
    {
        var s = new ObjectEnumeratorSettings {
            NormalObjects = true, HiddenObjects = true, LockedObjects = true
        };
        return doc.Objects.GetObjectList(s).Where(o => !o.IsDeleted && !o.IsInstanceDefinitionGeometry).ToArray();
    }

    static Guid[] ReadIds(JToken value)
    {
        if (value == null) return new Guid[0];
        var a = value as JArray;
        if (a == null) throw new ArgumentException("IDs/path must be a JSON array.");
        return a.Select(x => Guid.Parse((string)x)).ToArray();
    }

    static bool Editable(RhinoObject o)
    {
        return o.IsSelectable(true, false, false, false);
    }

    static string Short(string value)
    {
        if (value == null) return null;
        return value.Length <= 512 ? value : value.Substring(0, 512) + "…";
    }

    static JArray Point(Point3d p) { return new JArray(p.X, p.Y, p.Z); }

    public static JArray Matrix(Transform t)
    {
        var a = new JArray();
        for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++) a.Add(t[r, c]);
        return a;
    }

    static JObject Row(RhinoDoc doc, RhinoObject o)
    {
        var layer = doc.Layers[o.Attributes.LayerIndex];
        var r = new JObject {
            ["id"] = o.Id.ToString(), ["type"] = o.ObjectType.ToString(),
            ["name"] = Short(o.Name), ["layer"] = layer == null ? null : Short(layer.FullPath),
            ["hidden"] = o.IsHidden, ["locked"] = o.IsLocked
        };
        var block = o as InstanceObject;
        if (block != null) {
            r["definition"] = Short(block.InstanceDefinition.Name);
            r["definition_id"] = block.InstanceDefinition.Id.ToString();
        }
        return r;
    }

    static JObject Types(IEnumerable<RhinoObject> objects)
    {
        var r = new JObject();
        foreach (var g in objects.GroupBy(o => o.ObjectType.ToString())) r[g.Key] = g.Count();
        return r;
    }

    public sealed class Budget
    {
        public readonly JObject Result;
        public readonly JArray Records = new JArray();
        readonly int maxItems, maxBytes;
        public bool Stopped { get; private set; }
        public Budget(int items, int bytes)
        {
            if (items < 1 || items > 5000 || bytes < 2048 || bytes > 262144)
                throw new ArgumentException("max_items: 1..5000; max_bytes: 2048..262144.");
            maxItems = items; maxBytes = bytes;
            Result = new JObject {
                ["records"] = Records, ["items"] = 0, ["truncated"] = false,
                ["reason"] = null, ["depth_limited"] = false,
                ["max_items"] = items, ["max_bytes"] = bytes
            };
        }
        public bool Add(JObject row)
        {
            if (Stopped) return false;
            if (Records.Count >= maxItems) return Stop("max_items");
            Records.Add(row);
            Result["items"] = Records.Count;
            // Reserve space for the final truncation flags.
            if (Encoding.UTF8.GetByteCount(Result.ToString(Formatting.None)) > maxBytes - 128) {
                Records.RemoveAt(Records.Count - 1);
                Result["items"] = Records.Count;
                return Stop("max_bytes");
            }
            return true;
        }
        bool Stop(string reason)
        {
            Stopped = true; Result["truncated"] = true; Result["reason"] = reason;
            return false;
        }
    }

    sealed class Index
    {
        readonly RhinoDoc doc;
        readonly JObject q;
        readonly Budget budget;
        readonly HashSet<Guid> owners = new HashSet<Guid>();
        readonly Dictionary<Guid, RhinoObject[]> members = new Dictionary<Guid, RhinoObject[]>();
        readonly bool geometry, annotations, objects, transforms;
        readonly int depth;
        public Index(RhinoDoc d, JObject request, Budget b, HashSet<string> fields)
        {
            doc = d; q = request; budget = b;
            geometry = (bool?)q["include_geometry"] ?? false;
            annotations = (bool?)q["annotations"] ?? true;
            objects = fields.Contains("objects") || fields.Contains("transforms");
            transforms = fields.Contains("transforms");
            depth = (int?)q["depth"] ?? 64;
            if (depth < 0 || depth > 64) throw new ArgumentException("depth: 0..64.");
        }
        RhinoObject[] Members(InstanceDefinition d)
        {
            RhinoObject[] a;
            if (!members.TryGetValue(d.Id, out a)) {
                a = d.GetObjects(); members.Add(d.Id, a);
            }
            return a;
        }
        public void Owner(Guid key, string name, RhinoObject[] objects, HashSet<Guid> allowedNotes = null)
        {
            if (!annotations || !owners.Add(key) || budget.Stopped) return;
            if (!budget.Add(new JObject {
                ["kind"] = "owner", ["owner"] = key == Guid.Empty ? "DOCUMENT" : key.ToString(),
                ["name"] = Short(name), ["member_types"] = Types(objects)
            })) return;
            string ownerKey = key == Guid.Empty ? "DOCUMENT" : key.ToString();
            string layerFilter = (string)q["annotation_layer"];
            foreach (var obj in objects) {
                var dot = obj.Geometry as TextDot;
                if (dot == null || (allowedNotes != null && !allowedNotes.Contains(obj.Id))) continue;
                var layer = doc.Layers[obj.Attributes.LayerIndex];
                string layerName = layer == null ? "" : layer.FullPath;
                if (layerFilter != null &&
                    !String.Equals(layerName, layerFilter, StringComparison.OrdinalIgnoreCase) &&
                    !layerName.StartsWith(layerFilter + "::", StringComparison.OrdinalIgnoreCase)) continue;
                if (!budget.Add(new JObject {
                    ["kind"] = "note", ["owner"] = ownerKey, ["id"] = obj.Id.ToString(),
                    ["name"] = Short(obj.Name), ["text"] = Short(dot.Text),
                    ["text_limited"] = dot.Text != null && dot.Text.Length > 512,
                    ["layer"] = Short(layerName), ["point_local"] = Point(dot.Point)
                })) return;
                if (String.IsNullOrEmpty(obj.Name)) continue;
                foreach (var target in objects) {
                    if (target.Geometry is TextDot || target.Name != obj.Name) continue;
                    var row = Row(doc, target);
                    row["kind"] = "note_target"; row["owner"] = ownerKey; row["note_id"] = obj.Id.ToString();
                    if (!budget.Add(row)) return;
                }
            }
        }
        public void Visit(RhinoObject obj, Transform parent, List<Guid> prefix, HashSet<Guid> ancestors, int level)
        {
            if (budget.Stopped) return;
            var block = obj as InstanceObject;
            if (block == null && (!geometry || obj.Geometry is TextDot)) return;
            var path = new List<Guid>(prefix); path.Add(obj.Id);
            var world = block == null ? parent : parent * block.InstanceXform;
            var row = Row(doc, obj);
            row["kind"] = "occurrence";
            row["path"] = new JArray(path.Select(x => x.ToString()));
            if (transforms) row[block == null ? "geometry_to_world" : "definition_to_world"] = Matrix(world);
            if (this.objects && !budget.Add(row)) return;
            if (block == null) return;
            var definition = block.InstanceDefinition;
            if (ancestors.Contains(definition.Id)) {
                row["cycle"] = true; budget.Result["truncated"] = true;
                budget.Result["reason"] = "cycle"; return;
            }
            var objects = Members(definition);
            Owner(definition.Id, definition.Name, objects);
            if (level >= depth) {
                if (objects.Any(o => o is InstanceObject || (geometry && !(o.Geometry is TextDot))))
                    budget.Result["depth_limited"] = true;
                return;
            }
            var next = new HashSet<Guid>(ancestors); next.Add(definition.Id);
            foreach (var child in objects) {
                Visit(child, world, path, next, level + 1);
                if (budget.Stopped) break;
            }
        }
    }

    public static JObject Outline(RhinoDoc doc, JObject q)
    {
        CheckOptions(q, "scope", "ids", "path", "depth", "include_geometry",
            "annotations", "annotation_layer", "max_items", "max_bytes", "field_groups");
        var supplied = q["field_groups"] as JArray;
        if (q["field_groups"] != null && (supplied == null || supplied.Count == 0 || supplied.Any(t => t.Type != JTokenType.String)))
            throw new ArgumentException("field_groups must be a nonempty array of summary, objects, annotations or transforms.");
        // Explicit legacy detail flags retain their meaning; new default observations are summaries.
        var fields = new HashSet<string>(supplied == null ?
            (q["include_geometry"] != null || q["annotations"] != null ? new[] { "summary", "objects", "annotations", "transforms" } : new[] { "summary" }) :
            supplied.Values<string>());
        if (fields.Except(new[] { "summary", "objects", "annotations", "transforms" }).Any())
            throw new ArgumentException("Unknown outline field group.");
        if (q["path"] != null && q["ids"] != null)
            throw new ArgumentException("Choose path for one branch or ids for roots.");
        var b = new Budget((int?)q["max_items"] ?? 200, (int?)q["max_bytes"] ?? 48000);
        var detail = (JObject)q.DeepClone();
        detail["annotations"] = fields.Contains("annotations") && ((bool?)q["annotations"] ?? true);
        detail["include_geometry"] = (bool?)q["include_geometry"] ?? (fields.Contains("objects") || fields.Contains("transforms"));
        var index = new Index(doc, detail, b, fields);
        var branch = ReadIds(q["path"]);
        if (q["path"] != null) {
            if (branch.Length == 0) throw new ArgumentException("path must contain 1..65 IDs.");
            Transform parent;
            var obj = PathObject(doc, branch, out parent);
            if (fields.Contains("summary")) AddSummary(b, new[] { obj }, (int?)q["max_bytes"] ?? 48000);
            if (fields.Any(field => field != "summary"))
                index.Visit(obj, parent, branch.Take(branch.Length - 1).ToList(), new HashSet<Guid>(), 0);
            return b.Result;
        }
        var top = TopObjects(doc);
        var ids = ReadIds(q["ids"]);
        string scope = (string)q["scope"] ?? "selected";
        RhinoObject[] roots;
        if (q["ids"] != null) {
            var found = new HashSet<Guid>(top.Select(o => o.Id));
            if (ids.Any(id => !found.Contains(id))) throw new ArgumentException("Stale or non-editor root IDs.");
            var chosen = new HashSet<Guid>(ids); roots = top.Where(o => chosen.Contains(o.Id)).ToArray();
        } else if (scope == "selected") roots = top.Where(o => o.IsSelected(false) != 0).ToArray();
        else if (scope == "document") roots = top;
        else if (scope == "viewport") roots = VisibleRoots(doc);
        else throw new ArgumentException("scope: selected, viewport, document.");
        if (fields.Contains("summary")) AddSummary(b, roots, (int?)q["max_bytes"] ?? 48000);
        if (!fields.Any(field => field != "summary")) return b.Result;
        bool temporary = top.Any(o => !String.IsNullOrEmpty(o.Attributes.GetUserString("$TempBlockEditUserData$")));
        index.Owner(Guid.Empty, temporary ? "CURRENT_EDITOR_HINT" : "DOCUMENT",
            temporary ? top.Where(Editable).ToArray() : top, new HashSet<Guid>(roots.Select(o => o.Id)));
        foreach (var root in roots) {
            index.Visit(root, Transform.Identity, new List<Guid>(), new HashSet<Guid>(), 0);
            if (b.Stopped) break;
        }
        return b.Result;
    }

    static void AddSummary(Budget budget, RhinoObject[] roots, int maxBytes)
    {
        var names = new JArray(roots.Select(o => Short(String.IsNullOrWhiteSpace(o.Name) && o is InstanceObject
            ? ((InstanceObject)o).InstanceDefinition.Name : o.Name)).Where(name => !String.IsNullOrWhiteSpace(name)).Take(20));
        var summary = new JObject { ["kind"] = "summary", ["root_count"] = roots.Length,
            ["types"] = Types(roots), ["names"] = names, ["names_truncated"] = roots.Length > names.Count };
        while (names.Count > 0 && Encoding.UTF8.GetByteCount(summary.ToString(Formatting.None)) > maxBytes - 512)
        {
            names.RemoveAt(names.Count - 1);
            summary["names_truncated"] = true;
        }
        summary["detail_hint"] = "Request field_groups objects/annotations/transforms and narrow ids/path/depth when more detail is needed.";
        budget.Add(summary);
    }

    static RhinoObject[] VisibleRoots(RhinoDoc doc)
    {
        var view = doc.Views.ActiveView;
        if (view == null) throw new InvalidOperationException("No active view; specify IDs.");
        var s = new ObjectEnumeratorSettings {
            NormalObjects = true, HiddenObjects = false, LockedObjects = true,
            VisibleFilter = true, ViewportFilter = view.ActiveViewport
        };
        return doc.Objects.GetObjectList(s).Where(o =>
            !o.IsInstanceDefinitionGeometry && view.ActiveViewport.IsVisible(o.Geometry.GetBoundingBox(false))).ToArray();
    }

    public static RhinoObject PathObject(RhinoDoc doc, Guid[] path, out Transform parent)
    {
        if (path.Length == 0 || path.Length > 65) throw new ArgumentException("path must contain 1..65 IDs.");
        RhinoObject current = doc.Objects.FindId(path[0]);
        if (current == null || current.IsDeleted || current.IsInstanceDefinitionGeometry)
            throw new ArgumentException("Stale document/editor root.");
        parent = Transform.Identity;
        for (int i = 1; i < path.Length; i++) {
            var block = current as InstanceObject;
            if (block == null) throw new ArgumentException("Path parent is not a block.");
            parent = parent * block.InstanceXform;
            current = block.InstanceDefinition.GetObjects().SingleOrDefault(o => o.Id == path[i]);
            if (current == null) throw new ArgumentException("Stale direct member in path.");
        }
        return current;
    }

    public static JObject ResolveBlock(RhinoDoc doc, Guid[] path)
    {
        Transform parent;
        var wanted = PathObject(doc, path, out parent) as InstanceObject;
        if (wanted == null) throw new ArgumentException("Path target is not a block.");
        var world = parent * wanted.InstanceXform;
        if (path.Length == 1) {
            if (!Editable(wanted)) throw new InvalidOperationException("The explicit root is not currently editable.");
            var root = Row(doc, wanted); root["definition_to_world"] = Matrix(world);
            root["match_rule"] = "explicit_root_id"; root["editor_owner_verified"] = false;
            return root;
        }
        var matches = TopObjects(doc).OfType<InstanceObject>().Where(o =>
            Editable(o) && o.InstanceDefinition.Id == wanted.InstanceDefinition.Id &&
            SameTransform(o.InstanceXform, world, doc.ModelAbsoluteTolerance)).ToArray();
        if (matches.Length != 1)
            throw new InvalidOperationException("Expected one editable occurrence; found " + matches.Length +
                ". Refresh editor level/path; do not select the first match.");
        var row = Row(doc, matches[0]); row["definition_to_world"] = Matrix(world);
        row["match_rule"] = "definition_and_world_transform";
        row["editor_owner_verified"] = false;
        return row;
    }

    static bool SameTransform(Transform a, Transform b, double tolerance)
    {
        for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++)
            if (Math.Abs(a[r, c] - b[r, c]) > (c == 3 && r < 3 ? tolerance * 0.01 : 1e-10)) return false;
        return true;
    }
}
