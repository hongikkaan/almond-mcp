// Runs production hierarchy/containment code against in-memory Rhino API doubles.
// No Rhino process, RHP, native geometry kernel, selection or user document is used.
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace Rhino.Geometry {
    public struct Transform {
        public double X;
        public static Transform Identity => new Transform();
        public static Transform operator *(Transform a, Transform b) => new Transform { X = a.X + b.X };
    }
    public struct Point3d { public double X, Y, Z; }
    public struct BoundingBox {
        public Point3d Min, Max;
        public bool IsValid => true;
        public static BoundingBox Empty => new BoundingBox();
        public Point3d Center => Min;
        public void Union(BoundingBox other) { }
        public void Transform(Transform transform) { Min.X += transform.X; Max.X += transform.X; }
    }
    public class GeometryBase {
        public double MinX, MaxX;
        public BoundingBox GetBoundingBox(bool accurate) => new BoundingBox { Min = new Point3d { X=MinX }, Max = new Point3d { X=MaxX } };
    }
}
namespace Rhino.DocObjects {
    public enum ActiveSpace { ModelSpace, PageSpace }
    public enum ObjectType { Brep, InstanceReference }
    public class ObjectAttributes { public ActiveSpace Space; public int LayerIndex; }
    public class RhinoObject {
        public Guid Id; public string Name = "";
        public bool IsDeleted, IsInstanceDefinitionGeometry, IsLocked, Selected, Visible = true;
        public int IsSelected(bool subobjects) => Selected ? 1 : 0;
        public ObjectType ObjectType = ObjectType.Brep;
        public ObjectAttributes Attributes = new ObjectAttributes();
        public GeometryBase Geometry = new GeometryBase();
    }
    public class InstanceDefinition {
        public string Name = "Block";
        public RhinoObject[] Objects = Array.Empty<RhinoObject>();
        public int ObjectCount => Objects.Length;
        public RhinoObject[] GetObjects() => Objects;
    }
    public class InstanceObject : RhinoObject {
        public InstanceDefinition InstanceDefinition = new InstanceDefinition();
        public Transform InstanceXform = Transform.Identity;
    }
    public class Group { public Guid Id; public string Name; public int Index; public bool IsDeleted; public Guid[] Members; public bool Complete=true; }
    public class ObjectEnumeratorSettings {
        public bool NormalObjects, HiddenObjects, LockedObjects, ReferenceObjects, DeletedObjects, IdefObjects, VisibleFilter;
    }
    public class Layer { public string FullPath = "Model"; public Guid Id, ParentLayerId; public bool IsDeleted, IsLocked; }
}
namespace Rhino {
    public class ObjectTable : List<RhinoObject> {
        public RhinoObject FindId(Guid id) => this.FirstOrDefault(o => o.Id == id);
        public IEnumerable<RhinoObject> GetObjectList(ObjectEnumeratorSettings settings) => this;
        public IEnumerable<RhinoObject> GetSelectedObjects(bool subobjects, bool lights) => this;
    }
    public class GroupTable : List<Group> {
        public ObjectTable Objects;
        public RhinoObject[] GroupMembers(int index) => this[index].Members.Select(id => Objects.FindId(id)).Where(o => o != null).ToArray();
    }
    public class LayerTable : List<Layer> { public Layer FindIndex(int index) => index >= 0 && index < Count ? this[index] : null; }
    public class View { public Rhino.Display.RhinoViewport ActiveViewport = new Rhino.Display.RhinoViewport(); }
    public class Views { public View ActiveView = new View(); }
    public class RhinoDoc {
        public ObjectTable Objects = new ObjectTable();
        public GroupTable Groups = new GroupTable();
        public LayerTable Layers = new LayerTable();
        public Views Views = new Views(); public ActiveSpace ActiveSpace = ActiveSpace.ModelSpace;
        public RhinoDoc() { Groups.Objects = Objects; Layers.Add(new Layer { Id=Guid.NewGuid() }); }
    }
}
namespace Rhino.Display {
    public class RhinoViewport {
        public System.Drawing.Size Size => new System.Drawing.Size(100, 100);
        public bool IsVisible(BoundingBox bounds) => bounds.Max.X >= 0 && bounds.Min.X <= 10;
        public System.Drawing.PointF WorldToClient(Point3d point) => new System.Drawing.PointF();
    }
}
// Pixel labels are compiled but never exercised by this hierarchy-only fixture.
namespace System.Drawing {
    public enum GraphicsUnit { Pixel }
    public class Bitmap { public int Width = 100, Height = 100; }
    public class Font : IDisposable { public Font(string name, float size, GraphicsUnit unit) {} public void Dispose() {} }
    public class SolidBrush : IDisposable { public SolidBrush(Color color) {} public void Dispose() {} }
    public class Graphics : IDisposable {
        public static Graphics FromImage(Bitmap bitmap) => new Graphics();
        public SizeF MeasureString(string text, Font font) => new SizeF(10, 10);
        public void FillRectangle(SolidBrush brush, RectangleF rect) {}
        public void DrawString(string text, Font font, SolidBrush brush, float x, float y) {}
        public void Dispose() {}
    }
}
namespace RhinoAlmondBridge {
    public static class EditingContext {
        public class ObjectScope { }
        public static ObjectScope ObserveObjects(Rhino.RhinoDoc doc) => new ObjectScope();
        public static RhinoObject[] GroupObjects(Rhino.RhinoDoc doc, Group group, ObjectScope scope,
            out bool complete, out string basis) {
            complete = group.Complete; basis = complete ? "document_group_table" : "editor_incomplete";
            return doc.Groups.GroupMembers(group.Index);
        }
    }
    public static partial class ObjectObservation {
        const int MaxBytes = 262144;
        class ValueBudget {}
        static JObject Bounds(BoundingBox box) => new JObject { ["min_x"] = box.Min.X };
        static JObject Error(string code, string message) => new JObject { ["status"] = "error", ["error_code"] = code, ["message"] = message };
        // Metadata serialization is covered by the production build and public contract tests.
        static JObject Describe(Rhino.RhinoDoc doc, RhinoObject obj, HashSet<Guid> matched, HashSet<Guid> visible,
            bool geometry, ValueBudget budget, HashSet<string> fields, int offset, int limit, EditingContext.ObjectScope editing = null) => new JObject {
                ["id"] = obj.Id.ToString(), ["name"] = obj.Name, ["visible"] = obj.Visible, ["selected"] = false };

        public static JObject Run(JObject input) {
            var doc = new Rhino.RhinoDoc();
            if (input["layers"] is JArray layers) {
                doc.Layers.Clear();
                foreach (var row in layers) doc.Layers.Add(new Layer { Id=Guid.Parse((string)row["id"]),
                    ParentLayerId=row["parent"] == null ? Guid.Empty : Guid.Parse((string)row["parent"]), IsLocked=(bool?)row["locked"] ?? false });
            }
            foreach (var item in input["objects"]) {
                RhinoObject obj = item["members"] == null ? new RhinoObject() : new InstanceObject();
                obj.Id = Guid.Parse((string)item["id"]); obj.Name = (string)item["name"] ?? "";
                obj.IsInstanceDefinitionGeometry = (bool?)item["definition"] ?? false;
                obj.Visible = !((bool?)item["hidden"] ?? false); obj.IsLocked = (bool?)item["locked"] ?? false;
                obj.Selected = (bool?)item["selected"] ?? false; obj.Attributes.LayerIndex = (int?)item["layer"] ?? 0;
                obj.Geometry.MinX = (double?)item["min_x"] ?? 0; obj.Geometry.MaxX = (double?)item["max_x"] ?? 0;
                if (obj is InstanceObject block) {
                    block.ObjectType = ObjectType.InstanceReference;
                    block.InstanceXform = new Transform { X = (double?)item["x"] ?? 0 };
                }
                doc.Objects.Add(obj);
            }
            foreach (var item in input["objects"].Where(o => o["members"] != null))
                ((InstanceObject)doc.Objects.FindId(Guid.Parse((string)item["id"]))).InstanceDefinition.Objects =
                    item["members"].Values<string>().Select(id => doc.Objects.FindId(Guid.Parse(id))).ToArray();
            foreach (var item in input["groups"] ?? new JArray())
                doc.Groups.Add(new Group { Id = Guid.Parse((string)item["id"]), Name = (string)item["name"] ?? "",
                    Index = doc.Groups.Count, Members = item["members"].Values<string>().Select(Guid.Parse).ToArray(),
                    Complete = (bool?)item["complete"] ?? true });
            var groupIds = (input["group_ids"] ?? new JArray()).Values<string>().Select(Guid.Parse).ToArray();
            if ((bool?)input["group_metadata"] == true)
                return GroupMembership(doc, doc.Groups[0], new HashSet<Guid>(), new HashSet<Guid>(), EditingContext.ObserveObjects(doc));
            string scope = (string)input["scope"] ?? (groupIds.Length == 0 ? "selected" : "groups");
            var source = scope == "groups" ? RequestedGroups(doc, groupIds).SelectMany(g => g.Members).Distinct().ToArray()
                : (input["selected"] ?? new JArray(doc.Objects.Where(o => !o.IsInstanceDefinitionGeometry).Select(o => o.Id.ToString())))
                    .Values<string>().Select(id => doc.Objects.FindId(Guid.Parse(id))).ToArray();
            if (scope == "current") source = CurrentObjects(doc, source, (bool?)input["current_selected"] ?? false, (bool?)input["inside_window"] ?? false);
            var matched = input["matched"] == null ? source : source.Where(o => input["matched"].Values<string>().Contains(o.Id.ToString())).ToArray();
            return Hierarchy(doc, scope, groupIds, source, matched, new HashSet<Guid>(source.Select(o => o.Id)), null,
                (bool?)input["expand_groups"] ?? false, (bool?)input["expand_blocks"] ?? false,
                (int?)input["depth"] ?? 1, (int?)input["offset"] ?? 0, (int?)input["limit"] ?? 200);
        }
    }
}
class Program {
    static void Main() {
        try { Console.WriteLine(RhinoAlmondBridge.ObjectObservation.Run(JObject.Parse(Console.In.ReadToEnd())).ToString(Newtonsoft.Json.Formatting.None)); }
        catch (Exception ex) { Console.WriteLine(new JObject { ["status"] = "error", ["message"] = ex.Message }.ToString(Newtonsoft.Json.Formatting.None)); }
    }
}
