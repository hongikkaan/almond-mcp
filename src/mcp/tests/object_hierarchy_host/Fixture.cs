// Runs production hierarchy/containment code against in-memory Rhino API doubles.
// No Rhino process, RHP, native geometry kernel, selection or user document is used.
using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace Rhino.Geometry {
    public struct Transform {
        public double A, B, C, D, X, Y;
        public static Transform Identity => new Transform { A = 1, D = 1 };
        public static Transform operator *(Transform a, Transform b) => new Transform {
            A = a.A*b.A + a.B*b.C, B = a.A*b.B + a.B*b.D,
            C = a.C*b.A + a.D*b.C, D = a.C*b.B + a.D*b.D,
            X = a.A*b.X + a.B*b.Y + a.X, Y = a.C*b.X + a.D*b.Y + a.Y
        };
    }
    public struct Point3d {
        public double X, Y, Z;
        public static Point3d operator -(Point3d point) => new Point3d { X = -point.X, Y = -point.Y, Z = -point.Z };
    }
    public struct Plane { public Point3d Origin, XAxis, YAxis, Normal; }
    public struct BoundingBox {
        public Point3d Min, Max;
        public bool IsValid => Min.X <= Max.X && Min.Y <= Max.Y;
        public static BoundingBox Empty => new BoundingBox {
            Min = new Point3d { X = double.PositiveInfinity, Y = double.PositiveInfinity },
            Max = new Point3d { X = double.NegativeInfinity, Y = double.NegativeInfinity }
        };
        public Point3d Center => Min;
        public void Union(BoundingBox other) {
            Min.X = Math.Min(Min.X, other.Min.X);
            Max.X = Math.Max(Max.X, other.Max.X);
            Min.Y = Math.Min(Min.Y, other.Min.Y);
            Max.Y = Math.Max(Max.Y, other.Max.Y);
        }
        public void Transform(Transform transform) {
            if (!IsValid) return;
            var box = Empty;
            foreach (double x in new[] { Min.X, Max.X })
            foreach (double y in new[] { Min.Y, Max.Y }) {
                var point = new Point3d { X = transform.A*x + transform.B*y + transform.X,
                    Y = transform.C*x + transform.D*y + transform.Y };
                box.Union(new BoundingBox { Min = point, Max = point });
            }
            Min = box.Min;
            Max = box.Max;
        }
    }
    public class GeometryBase : Rhino.Runtime.CommonObject {
        public double MinX, MaxX, MinY, MaxY;
        public int BoundsReads, CrcReads;
        public uint Crc;
        public bool IsValid => true;
        public uint DataCRC(uint current) {
            CrcReads++;
            return Crc;
        }
        public BoundingBox GetBoundingBox(bool accurate) {
            BoundsReads++;
            return new BoundingBox { Min = new Point3d { X=MinX, Y=MinY }, Max = new Point3d { X=MaxX, Y=MaxY } };
        }
    }
    public class Brep : GeometryBase {
        public bool IsSolid, IsManifold;
        public List<BrepFace> Faces = new List<BrepFace>();
        public List<BrepEdge> Edges = new List<BrepEdge>();
    }
    public class BrepFace : GeometryBase {
        public bool OrientationIsReversed;
        public int FaceIndex;
        public bool TryGetPlane(out Plane plane, double tolerance) { plane = default; return false; }
        public int[] AdjacentEdges() => Array.Empty<int>();
        public bool IsPlanar(double tolerance) => false;
    }
    public class BrepEdge { public int[] AdjacentFaces() => Array.Empty<int>(); }
    public class VolumeMassProperties : IDisposable {
        public double Volume => 0;
        public static VolumeMassProperties Compute(Brep brep) => null;
        public void Dispose() { }
    }
}
namespace Rhino.FileIO { public class SerializationOptions { } }
namespace Rhino.DocObjects {
    public enum ActiveSpace { ModelSpace, PageSpace }
    public enum ObjectType { Brep, InstanceReference }
    public class ObjectAttributes : Rhino.Runtime.CommonObject {
        public ActiveSpace Space; public int LayerIndex; public JObject Text = new JObject();
        public string GetUserString(string key) => (string)Text[key];
        public string Name;
        public int MaterialIndex, MaterialSource, ColorSource, Mode;
        public System.Drawing.Color ObjectColor;
        public List<int> Groups = new List<int>();
        public int[] GetGroupList() => Groups.ToArray();
        public int GroupCount => Groups.Count;
        public string ToJSON(Rhino.FileIO.SerializationOptions options) => Text.ToString(Newtonsoft.Json.Formatting.None);
        public NameValueCollection GetUserStrings() {
            var values = new NameValueCollection();
            foreach (var property in Text.Properties()) values.Add(property.Name, (string)property.Value);
            return values;
        }
    }
    public class RhinoObject {
        public Guid Id; public string Name = "";
        public bool IsDeleted, IsInstanceDefinitionGeometry, IsLocked, IsReference, Selected, Visible = true;
        public bool IsHidden => !Visible;
        public int IsSelected(bool subobjects) => Selected ? 1 : 0;
        public ObjectType ObjectType = ObjectType.Brep;
        public ObjectAttributes Attributes = new ObjectAttributes();
        public GeometryBase Geometry = new GeometryBase();
        public Material Front; public Rhino.Render.RenderMaterial Render;
        public Material GetMaterial(bool front) => front ? Front : null;
        public Rhino.Render.RenderMaterial GetRenderMaterial(bool front) => front ? Render : null;
    }
    public class InstanceDefinition {
        public Guid Id; public bool IsDeleted;
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
    public class Layer { public string FullPath = "Model"; public Guid Id, ParentLayerId; public bool IsDeleted, IsLocked, IsVisible = true; }
    public class Material { public Guid Id, RenderMaterialInstanceId; public string Name; public bool IsDeleted; }
}
namespace Rhino.Render { public class RenderMaterial { public Guid Id; public string Name; } }
namespace Rhino.Collections { public class ArchivableDictionary : Dictionary<string,object> {} }
namespace Rhino.Runtime { public class CommonObject { public Rhino.Collections.ArchivableDictionary Dictionary; } }
namespace Rhino {
    public class ObjectTable : List<RhinoObject> {
        public RhinoObject FindId(Guid id) => this.FirstOrDefault(o => o.Id == id);
        public IEnumerable<RhinoObject> GetObjectList(ObjectEnumeratorSettings settings) => this;
        public IEnumerable<RhinoObject> GetSelectedObjects(bool subobjects, bool lights) => this;
    }
    public class GroupTable : List<Group> {
        public ObjectTable Objects;
        public int MemberReads;
        public RhinoObject[] GroupMembers(int index) {
            MemberReads++;
            return this[index].Members.Select(id => Objects.FindId(id)).Where(o => o != null).ToArray();
        }
    }
    public class LayerTable : List<Layer> { public Layer FindIndex(int index) => index >= 0 && index < Count ? this[index] : null; }
    public class View { public Rhino.Display.RhinoViewport ActiveViewport = new Rhino.Display.RhinoViewport(); }
    public class Views { public View ActiveView = new View(); }
    public class RhinoDoc {
        public ObjectTable Objects = new ObjectTable();
        public GroupTable Groups = new GroupTable();
        public LayerTable Layers = new LayerTable();
        public List<InstanceDefinition> InstanceDefinitions = new List<InstanceDefinition>();
        public List<Material> Materials = new List<Material>();
        public List<Rhino.Render.RenderMaterial> RenderMaterials = new List<Rhino.Render.RenderMaterial>();
        public Views Views = new Views(); public ActiveSpace ActiveSpace = ActiveSpace.ModelSpace;
        public string Path = System.IO.Path.GetFullPath("hierarchy-fixture.3dm");
        public string ModelUnitSystem = "Millimeters";
        public double ModelAbsoluteTolerance = 0.001;
        public uint RuntimeSerialNumber = 1;
        public bool EditorStable = true;
        public RhinoDoc() { Groups.Objects = Objects; Layers.Add(new Layer { Id=Guid.Parse("00000000-0000-0000-0000-000000000001") }); }
    }
}
namespace Rhino.Display {
    public class RhinoViewport {
        public Guid Id;
        public Point3d CameraLocation, CameraDirection, CameraUp;
        public bool IsParallelProjection;
        public bool GetFrustum(out double left, out double right, out double bottom, out double top, out double near, out double far) {
            left = bottom = near = 0; right = top = far = 10;
            return true;
        }
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
    public static class GeometryJson {
        public static JArray Point(Point3d point) => new JArray(point.X, point.Y, point.Z);
    }
    public static class IntersectionAnalysis {
        public static JObject QueryForPreview(Rhino.RhinoDoc doc, Guid[] ids, int maxPairs, bool includeBlocks, string cursor, object accept, bool stop) => throw new NotSupportedException();
    }
    public static class ComponentOperations {
        public static JObject CheckIntersectVolumes(Rhino.RhinoDoc doc, Guid[] ids, int maxPairs, bool includeBlocks, string cursor) => throw new NotSupportedException();
    }
    public static class EditingContext {
        public class ObjectScope { public JObject State; }
        public static ObjectScope ObserveObjects(Rhino.RhinoDoc doc) => new ObjectScope { State = new JObject { ["stable"] = doc.EditorStable } };
        public static RhinoObject[] GroupObjects(Rhino.RhinoDoc doc, Group group, ObjectScope scope,
            out bool complete, out string basis) {
            complete = group.Complete; basis = complete ? "document_group_table" : "editor_incomplete";
            return doc.Groups.GroupMembers(group.Index);
        }
    }
    public static partial class ObjectObservation {
        static Rhino.Collections.ArchivableDictionary ExistingDictionary(Rhino.Runtime.CommonObject obj) => obj.Dictionary;
        static void LoadDictionary(Rhino.Runtime.CommonObject obj, JToken input) {
            if (!(input is JObject properties)) return;
            obj.Dictionary = new Rhino.Collections.ArchivableDictionary();
            foreach (var p in properties.Properties())
                obj.Dictionary[p.Name] = p.Value is JArray arr ? arr.Select(t => ((JValue)t).Value).ToArray() : ((JValue)p.Value).Value;
        }
        public static JObject Run(JObject input) {
            var doc = new Rhino.RhinoDoc { EditorStable = (bool?)input["editor_stable"] ?? true };
            foreach (var row in input["materials"] ?? new JArray())
                doc.Materials.Add(new Material { Id=Guid.Parse((string)row["id"]), Name=(string)row["name"],
                    RenderMaterialInstanceId=(Guid?)row["render"] ?? Guid.Empty });
            foreach (var row in input["render_materials"] ?? new JArray())
                doc.RenderMaterials.Add(new Rhino.Render.RenderMaterial { Id=Guid.Parse((string)row["id"]), Name=(string)row["name"] });
            if (input["layers"] is JArray layers) {
                doc.Layers.Clear();
                foreach (var row in layers) doc.Layers.Add(new Layer { Id=Guid.Parse((string)row["id"]), FullPath=(string)row["path"] ?? "Model",
                    ParentLayerId=row["parent"] == null ? Guid.Empty : Guid.Parse((string)row["parent"]), IsLocked=(bool?)row["locked"] ?? false });
            }
            foreach (var item in input["objects"]) {
                RhinoObject obj = item["members"] == null ? new RhinoObject() : new InstanceObject();
                obj.Id = Guid.Parse((string)item["id"]); obj.Name = (string)item["name"] ?? "";
                obj.Front = doc.Materials.FirstOrDefault(m => m.Id == (Guid?)item["front"]);
                obj.Render = doc.RenderMaterials.FirstOrDefault(m => m.Id == (Guid?)item["render"]);
                obj.Attributes.Text = (JObject)item["text"] ?? new JObject();
                LoadDictionary(obj.Attributes,item["attribute_data"]); LoadDictionary(obj.Geometry,item["geometry_data"]);
                obj.IsInstanceDefinitionGeometry = (bool?)item["definition"] ?? false;
                obj.Visible = !((bool?)item["hidden"] ?? false); obj.IsLocked = (bool?)item["locked"] ?? false;
                obj.Selected = (bool?)item["selected"] ?? false; obj.Attributes.LayerIndex = (int?)item["layer"] ?? 0;
                if (item["faces"] is JArray faces) {
                    obj.Geometry = new Brep { IsSolid = true, IsManifold = true,
                        Faces = faces.Values<int>().Select(index => new BrepFace { FaceIndex = index }).ToList() };
                }
                obj.Geometry.MinX = (double?)item["min_x"] ?? 0; obj.Geometry.MaxX = (double?)item["max_x"] ?? 0;
                obj.Geometry.MinY = (double?)item["min_y"] ?? 0; obj.Geometry.MaxY = (double?)item["max_y"] ?? 0;
                obj.Geometry.Crc = (uint?)item["crc"] ?? 0;
                if (obj is InstanceObject block) {
                    var id = item["definition_id"] == null ? obj.Id : Guid.Parse((string)item["definition_id"]);
                    var definition = doc.InstanceDefinitions.Find(d => d.Id == id);
                    if (definition == null) {
                        definition = new InstanceDefinition { Id = id, Name = (string)item["definition_name"] ?? "Block" };
                        doc.InstanceDefinitions.Add(definition);
                    }
                    block.InstanceDefinition = definition;
                    block.ObjectType = ObjectType.InstanceReference;
                    var matrix = (JArray)item["xy_matrix"];
                    block.InstanceXform = new Transform { A = (double?)matrix?[0] ?? 1, B = (double?)matrix?[1] ?? 0,
                        C = (double?)matrix?[2] ?? 0, D = (double?)matrix?[3] ?? 1,
                        X = (double?)item["x"] ?? 0, Y = (double?)item["y"] ?? 0 };
                }
                doc.Objects.Add(obj);
            }
            foreach (var item in input["objects"].Where(o => o["members"] != null))
                ((InstanceObject)doc.Objects.FindId(Guid.Parse((string)item["id"]))).InstanceDefinition.Objects =
                    item["members"].Values<string>().Select(id => doc.Objects.FindId(Guid.Parse(id))).ToArray();
            foreach (var item in input["groups"] ?? new JArray()) {
                var group = new Group { Id = Guid.Parse((string)item["id"]), Name = (string)item["name"] ?? "",
                    Index = doc.Groups.Count, Members = item["members"].Values<string>().Select(Guid.Parse).ToArray(),
                    Complete = (bool?)item["complete"] ?? true };
                doc.Groups.Add(group);
                foreach (var id in group.Members) doc.Objects.FindId(id)?.Attributes.Groups.Add(group.Index);
            }
            if (input["public_group_source"] is JObject publicSource) {
                var selected = publicSource["members"]?.Values<string>().Select(Guid.Parse).Select(doc.Objects.FindId).ToArray();
                var supplied = new ObservationEntities.Entity { Members = selected };
                if (publicSource["bounds"] is JArray suppliedBounds) {
                    supplied.Bounds = new BoundingBox {
                        Min = new Point3d { X = (double)suppliedBounds[0] },
                        Max = new Point3d { X = (double)suppliedBounds[1] }
                    };
                }
                var root = ObservationEntities.Roots(doc, doc.Objects.ToArray(), groupSource: group => supplied)
                    .Single(entity => entity.Kind == "Group");
                return new JObject { ["bounds"] = Bounds(root.Bounds), ["member_reads"] = doc.Groups.MemberReads };
            }
            if (input["request"] is JObject request) {
                request["type"] = "get_rhino_objects";
                request["expected_model_path"] = doc.Path;
                var response = Handle(doc, request);
                var rows = response["objects"] as JArray;
                var independent = true;
                if (rows?.Count > 1 && rows[0]["groups"]?.FirstOrDefault() is JObject first &&
                    rows[1]["groups"]?.FirstOrDefault() is JObject second) {
                    var ids = (JArray)first["member_ids"];
                    int count = ((JArray)second["member_ids"]).Count;
                    ids.Add("fixture_probe");
                    independent = ((JArray)second["member_ids"]).Count == count;
                    ids.RemoveAt(ids.Count - 1);
                }
                return new JObject { ["response"] = response, ["member_reads"] = doc.Groups.MemberReads,
                    ["bounds_reads"] = doc.Objects.Sum(o => o.Geometry.BoundsReads),
                    ["crc_reads"] = doc.Objects.Sum(o => o.Geometry.CrcReads), ["independent_rows"] = independent };
            }
            var groupIds = (input["group_ids"] ?? new JArray()).Values<string>().Select(Guid.Parse).ToArray();
            var groupReads = new ObservedGroups(doc, EditingContext.ObserveObjects(doc));
            if ((bool?)input["group_metadata"] == true)
                return GroupMembership(groupReads, new HashSet<Guid>(), new HashSet<Guid>())(doc.Groups[0]);
            string scope = (string)input["scope"] ?? (groupIds.Length == 0 ? "selected" : "groups");
            var requestedGroups = groupIds.Length == 0 ? null : groupReads.Requested(groupIds);
            var source = scope == "groups" ? requestedGroups.SelectMany(g => g.Members).Distinct().ToArray()
                : (input["selected"] ?? new JArray(doc.Objects.Where(o => !o.IsInstanceDefinitionGeometry).Select(o => o.Id.ToString())))
                    .Values<string>().Select(id => doc.Objects.FindId(Guid.Parse(id))).ToArray();
            if (scope == "current") source = CurrentObjects(doc, source, (bool?)input["current_selected"] ?? false, (bool?)input["inside_window"] ?? false);
            var matched = input["matched"] == null ? source : source.Where(o => input["matched"].Values<string>().Contains(o.Id.ToString())).ToArray();
            if (input["filters"] is JObject filters) {
                ValidateMetadataFilter(filters["user_text"],"user_text",ValidateUserText);
                ValidateUserDictionary(filters["user_dictionary"]);
                var conditions = NamedFilters(doc, filters, groupReads);
                matched = matched.Where(o => conditions.All(condition => condition(o)) &&
                    MatchesObjectMetadata(o, filters["user_text"], filters["user_dictionary"])).ToArray();
            }
            if ((bool?)input["matched_ids_only"] == true)
                return new JObject { ["ids"] = new JArray(matched.Select(o => o.Id.ToString())) };
            return Hierarchy(doc, scope, requestedGroups, source, matched, new HashSet<Guid>(source.Select(o => o.Id)), null,
                (bool?)input["expand_groups"] ?? false, (bool?)input["expand_blocks"] ?? false,
                (int?)input["depth"] ?? 1, (int?)input["offset"] ?? 0, (int?)input["limit"] ?? 200, groupReads, ReadCrc);
        }
    }
}
class Program {
    static void Main() {
        try { Console.WriteLine(RhinoAlmondBridge.ObjectObservation.Run(JObject.Parse(Console.In.ReadToEnd())).ToString(Newtonsoft.Json.Formatting.None)); }
        catch (Exception ex) { Console.WriteLine(new JObject { ["status"] = "error", ["message"] = ex.Message }.ToString(Newtonsoft.Json.Formatting.None)); }
    }
}
