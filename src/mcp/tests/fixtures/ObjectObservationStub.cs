// Offline behavioral doubles. No reference to or loading of the real RhinoCommon.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Collections;
using Rhino.DocObjects;
using Rhino.Geometry;
using Rhino.Runtime;

var scenario = args[0];
var first = new RhinoObject { Id = new Guid("10000000-0000-0000-0000-000000000001"), Selected = true };
var second = new RhinoObject { Id = new Guid("10000000-0000-0000-0000-000000000002") };
first.Geometry.Crc = 123;
second.Geometry.Crc = 456;
first.Attributes.Name = "first";
second.Attributes.Name = "second";
first.Attributes.Groups = second.Attributes.Groups = new[] { 0 };
var doc = new RhinoDoc { Path = Path.GetFullPath("offline-object-observation.3dm") };
doc.Objects.Items.AddRange(new[] { first, second });
doc.Groups.Members = new[] { first, second };
var request = new JObject { ["type"] = "get_rhino_objects", ["scope"] = "document", ["expected_model_path"] = doc.Path };

void SetDictionary(CommonObject owner, object value)
{
    owner.UserData.Value = new Rhino.DocObjects.Custom.SharedUserDictionary();
    owner.UserData.Value.Dictionary.Add("Floor", value);
}
void Filter(string source, string value)
{
    request["filters"] = new JObject { ["user_dictionary"] = new JArray(new JObject {
        ["source"] = source, ["key"] = "Floor", ["any_of"] = new JArray(value) }) };
}
if (scenario.StartsWith("long_"))
{
    string source = scenario.Contains("attributes") ? "attributes" : "geometry";
    SetDictionary(source == "attributes" ? (CommonObject)first.Attributes : first.Geometry,
        Enumerable.Range(0, 257).Select(i => "floor-" + i).ToArray());
    Filter(source, scenario.EndsWith("first") ? "floor-0" : "floor-256");
}
else switch (scenario)
{
    case "scalar_exact":
        SetDictionary(first.Attributes, new[] { "GF", "B1" });
        SetDictionary(second.Attributes, "GF,B1");
        Filter("attributes", "GF"); break;
    case "missing_dictionary": break;
    case "missing_geometry_dictionary": request["include_geometry"] = true; break;
    case "missing_filter": Filter("geometry", "GF"); break;
    case "selected": request["scope"] = "selected"; break;
    case "ids": request["scope"] = "ids"; request["object_ids"] = new JArray(first.Id.ToString()); break;
    case "layer_hidden": second.Visible = false; break;
    case "visible": second.Visible = false; request["scope"] = "visible"; break;
    case "unsupported": SetDictionary(first.Attributes, new UnsafeMetadata()); break;
    case "filter_over_budget":
        SetDictionary(first.Attributes, Enumerable.Range(0, 4097).Select(i => "floor-" + i).ToArray());
        Filter("attributes", "floor-4096"); break;
    case "non_model_objects":
        doc.Objects.Items.Add(new RhinoObject { Id = Guid.NewGuid(), IsDeleted = true });
        doc.Objects.Items.Add(new RhinoObject { Id = Guid.NewGuid(), IsInstanceDefinitionGeometry = true });
        doc.Objects.Items.Add(new RhinoObject { Id = Guid.NewGuid(), Attributes = new ObjectAttributes { Space = ActiveSpace.PageSpace } });
        break;
    case "summary":
    case "summary_page":
        request["result_mode"] = "summary";
        second.Attributes.LayerIndex = 1; second.Kind = ObjectType.Mesh; second.Visible = false;
        GeometryBase.FailHeavy = true; GroupTable.FailReads = true;
        if (scenario == "summary_page") { request["offset"] = 1; request["limit"] = 1; }
        break;
    case "ids_only":
        request["fields"] = new JArray("id"); GeometryBase.FailHeavy = true; GroupTable.FailReads = true; break;
    case "named_fields":
        request["fields"] = new JArray("id", "name", "layer_path"); GeometryBase.FailHeavy = true; GroupTable.FailReads = true; break;
    case "type_filter":
        second.Kind = ObjectType.Mesh;
        request["filters"] = new JObject { ["object_types"] = new JArray("mesh") }; break;
    case "faces_first":
    case "faces_next":
    case "faces_stale":
    case "faces_missing_crc":
        first.Geometry = new Brep { Crc = 123, Faces = Enumerable.Range(0, 130).Select(i => new Face { FaceIndex = i }).ToList() };
        request["scope"] = "ids"; request["object_ids"] = new JArray(first.Id.ToString());
        request["fields"] = new JArray("faces");
        if (scenario != "faces_first") request["face_offset"] = 128;
        if (scenario == "faces_next" || scenario == "faces_stale")
            request["expected_geometry_crcs"] = new JObject { [first.Id.ToString()] = scenario == "faces_stale" ? 122 : 123 };
        break;
    case "invalid_fields": request["fields"] = new JArray("secret"); break;
    case "invalid_type": request["filters"] = new JObject { ["object_types"] = new JArray("Brep,Mesh") }; break;
    default: throw new ArgumentException("Unknown scenario: " + scenario);
}
var dictionaries = doc.Objects.Items.SelectMany(o => new[] { o.Attributes.UserData.Value, o.Geometry.UserData.Value }).ToArray();
string MetadataContents(CommonObject owner) => owner.UserData.Value == null ? "missing" :
    String.Join("|", owner.UserData.Value.Dictionary.Select(item => item.Key + ":" +
        (item.Value is string[] items ? String.Join(",", items) : item.Value is string text ? text : item.Value?.GetType().FullName)));
var metadataBefore = doc.Objects.Items.SelectMany(o => new[] { MetadataContents(o.Attributes), MetadataContents(o.Geometry) }).ToArray();
var memberCount = doc.Objects.Items.Count;
var result = RhinoAlmondBridge.ObjectObservation.Handle(doc, request);
var after = doc.Objects.Items.SelectMany(o => new[] { o.Attributes.UserData.Value, o.Geometry.UserData.Value }).ToArray();
var metadataAfter = doc.Objects.Items.SelectMany(o => new[] { MetadataContents(o.Attributes), MetadataContents(o.Geometry) }).ToArray();
Console.WriteLine(new JObject {
    ["result"] = result, ["user_dictionary_getter_calls"] = CommonObject.DictionaryGetterCalls,
    ["source_unchanged"] = dictionaries.SequenceEqual(after) && metadataBefore.SequenceEqual(metadataAfter) && memberCount == doc.Objects.Items.Count &&
        first.Geometry.Crc == 123 && second.Geometry.Crc == 456 && first.Selected && !second.Selected &&
        first.Attributes.Groups.SequenceEqual(new[] { 0 }) && second.Attributes.Groups.SequenceEqual(new[] { 0 })
}.ToString(Formatting.None));

public sealed class UnsafeMetadata
{
    public string Secret => throw new InvalidOperationException("Arbitrary metadata getter was invoked.");
}
namespace RhinoAlmondBridge
{
    public static class ComponentOperations
    {
        public static JObject CheckIntersectVolumes(RhinoDoc doc, Guid[] ids, int maxPairs, bool includeBlocks = false, string cursor = "") =>
            throw new InvalidOperationException("An object query unexpectedly invoked intersections.");
    }
}
namespace Rhino.Runtime
{
    public class CommonObject
    {
        public static int DictionaryGetterCalls;
        public UserDataList UserData = new UserDataList();
        public ArchivableDictionary UserDictionary
        {
            get { DictionaryGetterCalls++; throw new InvalidOperationException("UserDictionary getter mutates source user data."); }
        }
    }
    public sealed class UserDataList
    {
        public Rhino.DocObjects.Custom.UserDictionary Value;
        public object Find(Type type) => Value != null && type.IsInstanceOfType(Value) ? Value : null;
    }
}
namespace Rhino.DocObjects.Custom
{
    public class UserDictionary { public ArchivableDictionary Dictionary = new ArchivableDictionary(); }
    public sealed class SharedUserDictionary : UserDictionary { }
}
namespace Rhino.Collections
{
    public sealed class ArchivableDictionary : Dictionary<string, object> { }
}
namespace Rhino
{
    public sealed class RhinoDoc
    {
        public string Path;
        public string ModelUnitSystem = "Millimeters";
        public double ModelAbsoluteTolerance = 0.01;
        public ObjectTable Objects = new ObjectTable();
        public LayerTable Layers = new LayerTable();
        public GroupTable Groups = new GroupTable();
    }
    public sealed class ObjectTable
    {
        public List<RhinoObject> Items = new List<RhinoObject>();
        public IEnumerable<RhinoObject> GetObjectList(ObjectEnumeratorSettings settings) => Items;
    }
    public sealed class Layer { public string FullPath = "M::wall::test"; }
    public sealed class LayerTable { public Layer FindIndex(int index) => new Layer { FullPath = index == 1 ? "M::floor::test" : "M::wall::test" }; }
    public sealed class Group { public Guid Id = new Guid("20000000-0000-0000-0000-000000000001"); public string Name = "shared"; }
    public sealed class GroupTable
    {
        public static bool FailReads;
        public RhinoObject[] Members;
        public Group this[int index] => new Group();
        public RhinoObject[] GroupMembers(int index) => FailReads ? throw new InvalidOperationException("Unrequested group expansion") : Members;
    }
}
namespace Rhino.DocObjects
{
    public enum ActiveSpace { ModelSpace, PageSpace }
    public enum ObjectType { Brep, Mesh }
    public sealed class ObjectEnumeratorSettings
    {
        public bool NormalObjects, HiddenObjects, LockedObjects, ReferenceObjects, DeletedObjects, IdefObjects;
    }
    public sealed class ObjectAttributes : CommonObject
    {
        public ActiveSpace Space = ActiveSpace.ModelSpace;
        public string Name;
        public int LayerIndex;
        public int[] Groups = Array.Empty<int>();
        public int GroupCount => Groups.Length;
        public int[] GetGroupList() => Groups;
    }
    public sealed class RhinoObject
    {
        public Guid Id;
        public GeometryBase Geometry = new GeometryBase();
        public ObjectAttributes Attributes = new ObjectAttributes();
        public string Name => Attributes.Name;
        public ObjectType Kind = ObjectType.Brep;
        public ObjectType ObjectType => Kind;
        public bool IsDeleted, IsInstanceDefinitionGeometry, IsLocked, IsReference, IsHidden, Selected;
        public bool Visible = true;
        public int IsSelected(bool checkSubObjects) => Selected ? 1 : 0;
    }
}
namespace Rhino.Geometry
{
    public class GeometryBase : CommonObject
    {
        public static bool FailHeavy;
        public uint Crc;
        public bool IsValid = true;
        public uint DataCRC(uint initial) => FailHeavy ? throw new InvalidOperationException("Unrequested CRC") : Crc;
        public BoundingBox GetBoundingBox(bool accurate) => FailHeavy ? throw new InvalidOperationException("Unrequested bounds") : new BoundingBox { IsValid = true };
    }
    public struct Point3d { public double X, Y, Z; }
    public struct BoundingBox { public bool IsValid; public Point3d Min, Max; }
    public struct Vector3d
    {
        public double X, Y, Z;
        public static Vector3d operator -(Vector3d value) => new Vector3d { X = -value.X, Y = -value.Y, Z = -value.Z };
    }
    public struct Plane { public Point3d Origin; public Vector3d Normal; }
    public sealed class Brep : GeometryBase
    {
        public bool IsSolid = true, IsManifold = true;
        public List<Face> Faces = new List<Face>();
        public List<Edge> Edges = new List<Edge>();
    }
    public sealed class Face : GeometryBase
    {
        public bool OrientationIsReversed;
        public int FaceIndex;
        public bool TryGetPlane(out Plane plane, double tolerance) { plane = new Plane(); return true; }
        public int[] AdjacentEdges() => Array.Empty<int>();
        public bool IsPlanar(double tolerance) => true;
    }
    public sealed class Edge { public int[] AdjacentFaces() => Array.Empty<int>(); }
    public sealed class VolumeMassProperties : IDisposable
    {
        public double Volume = 100;
        public static VolumeMassProperties Compute(Brep brep) => new VolumeMassProperties();
        public void Dispose() { }
    }
}
