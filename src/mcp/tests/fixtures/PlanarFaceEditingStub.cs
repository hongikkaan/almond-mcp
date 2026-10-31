// Offline test doubles. This executable does not reference or load RhinoCommon.
using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

var scenario = args[0];
var original = new Brep();
bool hasDictionary = !scenario.StartsWith("no_dictionary");
if (hasDictionary) original.UserDictionary.Values["kept"] = "geometry metadata";
original.SetUserString("source", "retained geometry string");
if (scenario == "empty_user_strings") original.Strings.Clear();
int originalDictionaryReads = original.DictionaryGetterCalls;
var attributes = new ObjectAttributes { Name = "column", Groups = new[] { 4, 9 } };
var objectId = new Guid("2fc35662-7448-48a9-ab20-27d3e774734e");
var obj = new RhinoObject { Id = objectId, Geometry = original, Attributes = attributes };
var doc = new RhinoDoc { Path = Path.GetFullPath("offline-face-stub.3dm") };
doc.Objects.Current = obj;
var request = new JObject { ["object_id"] = objectId.ToString(), ["face_index"] = 0,
    ["expected_geometry_crc"] = 123, ["translation"] = new JArray(0, 0, 10), ["expected_model_path"] = doc.Path };
switch (scenario)
{
    case "wrong_path": request["expected_model_path"] = Path.GetFullPath("other-stub.3dm"); break;
    case "read_only": doc.IsReadOnly = true; break;
    case "editor": RhinoAlmondBridge.EditingContext.Stable = false; break;
    case "stable_editor": RhinoAlmondBridge.EditingContext.Mode = "group"; break;
    case "missing": doc.Objects.Current = null; break;
    case "reference": obj.IsReference = true; break;
    case "definition": obj.IsInstanceDefinitionGeometry = true; break;
    case "locked": obj.IsLocked = true; break;
    case "custom_managed_data": original.UserData.Items.Add(new Rhino.DocObjects.Custom.UserDictionary()); break;
    case "custom_native_data": original.UserData.NativeIds.Add(Guid.NewGuid()); break;
    case "locked_layer": doc.Layers.Items[0].IsLocked = true; break;
    case "locked_parent": doc.Layers.Items[1].IsLocked = true; break;
    case "missing_layer": attributes.LayerIndex = 99; break;
    case "broken_parent": doc.Layers.Items[0].ParentLayerId = Guid.NewGuid(); break;
    case "cyclic_parent": doc.Layers.Items[1].ParentLayerId = doc.Layers.Items[0].Id; break;
    case "page": attributes.Space = ActiveSpace.PageSpace; break;
    case "extrusion": obj.Geometry = new GeometryBase(); break;
    case "stale": request["expected_geometry_crc"] = 122; break;
    case "face_index": request["face_index"] = 99; break;
    case "curved_face": original.Faces[0].Planar = false; break;
    case "curved_neighbour": original.Faces[1].Planar = false; break;
    case "tangent": request["translation"] = new JArray(10, 0, 0); break;
    case "too_small": request["translation"] = new JArray(0, 0, 0.001); break;
    case "bad_original": original.IsSolid = false; break;
    case "replace_failure": doc.Objects.ReplaceSucceeds = false; break;
    case "no_dictionary_nochange": original.Outcome = "nochange"; break;
    default: original.Outcome = scenario; break;
}
if (scenario.StartsWith("batch_"))
{
    original.Outcome = "success";
    var secondId = new Guid("2fc35662-7448-48a9-ab20-27d3e774734f");
    var thirdId = new Guid("2fc35662-7448-48a9-ab20-27d3e7747350");
    doc.Objects.Others[secondId] = new RhinoObject { Id = secondId, Geometry = original.DuplicateBrep(), Attributes = attributes };
    doc.Objects.Others[thirdId] = new RhinoObject { Id = thirdId, Geometry = original.DuplicateBrep(), Attributes = attributes };
    JObject Edit(Guid id) => new JObject { ["object_id"] = id.ToString(), ["face_index"] = 0,
        ["expected_geometry_crc"] = 123, ["translation"] = new JArray(0, 0, 10) };
    request = new JObject { ["expected_model_path"] = doc.Path,
        ["edits"] = new JArray(Edit(objectId), Edit(secondId), Edit(thirdId)) };
    if (scenario == "batch_stale") request["edits"][1]["expected_geometry_crc"] = 122;
    if (scenario == "batch_invalid_result") ((Brep)doc.Objects.Others[secondId].Geometry).Outcome = "open";
    if (scenario == "batch_duplicate") request["edits"][1]["object_id"] = objectId.ToString();
    if (scenario == "batch_replace_failure") doc.Objects.FailReplaceAt = 2;
    if (scenario == "batch_throw_after_replace") doc.Objects.ThrowAfterReplaceAt = 2;
    if (scenario == "batch_throw_after_last_replace") doc.Objects.ThrowAfterReplaceAt = 3;
    if (scenario == "batch_unknown_replace") { doc.Objects.ThrowAfterReplaceAt = 2; doc.Objects.UnknownAfterReplace = true; }
}
JObject result = null;
string error = null;
JObject response = null;
int originalUserDataCount = original.UserData.Count;
try
{
    response = scenario.StartsWith("batch_") ? RhinoAlmondBridge.PlanarFaceEditing.HandleBatch(doc, request)
        : RhinoAlmondBridge.PlanarFaceEditing.Handle(doc, request);
    result = response["result"] as JObject;
    if ((string)response["status"] != "success") error = (string)response["message"];
}
catch (Exception ex) { error = ex.Message; }
Console.WriteLine(new JObject {
    ["result"] = result, ["error"] = error, ["replace_calls"] = doc.Objects.ReplaceCalls,
    ["response"] = response, ["result_error"] = response?["result_error"],
    ["executor_calls"] = RhinoAlmondBridge.ScriptExecutor.Calls, ["mutation_state"] = response?["mutation_state"],
    ["document_crcs"] = new JArray(new[] { objectId, new Guid("2fc35662-7448-48a9-ab20-27d3e774734f"),
        new Guid("2fc35662-7448-48a9-ab20-27d3e7747350") }.Select(id => doc.Objects.FindId(id)?.Geometry.DataCRC(0))),
    ["push_calls"] = Brep.PushCalls, ["original_untouched"] = !original.Touched && original.Crc == 123 &&
        original.DictionaryGetterCalls == originalDictionaryReads && original.UserData.Count == originalUserDataCount,
    ["attributes_preserved"] = ReferenceEquals(doc.Objects.Current?.Attributes, attributes) && attributes.Groups.Length == 2,
    ["dictionary_preserved"] = hasDictionary
        ? doc.Objects.Current?.Geometry.ExistingDictionary?.Values.TryGetValue("kept", out var kept) == true && kept == "geometry metadata"
        : doc.Objects.Current?.Geometry.UserData.Items.Count == 0,
    ["user_strings_preserved"] = doc.Objects.Current?.Geometry.GetUserStrings()["source"] == original.GetUserStrings()["source"]
}.ToString(Formatting.None));

namespace RhinoAlmondBridge
{
    public static class EditingContext
    {
        public static bool Stable = true;
        public static string Mode = "model";
        public static JObject Observe(RhinoDoc doc) => new JObject { ["stable"] = Stable && !doc.UndoRecordingIsActive, ["mode"] = Mode };
    }
    public sealed class ScriptResult
    {
        [JsonProperty("status")] public string Status = "success";
        [JsonProperty("message")] public string Message;
        [JsonProperty("result")] public JToken Result;
        [JsonProperty("result_error")] public string ResultError;
    }
    public sealed partial class ScriptExecutor
    {
        public static int Calls;
        internal ScriptResult ExecuteAction(RhinoDoc doc, Func<object> action)
        {
            Calls++;
            doc.UndoRecordingIsActive = true;
            try
            {
                var result = new ScriptResult();
                // The other partial file links production CaptureResult/ResultProjector.
                CaptureResult(result, action());
                return result;
            }
            catch (Exception ex) { return new ScriptResult { Status = "error", Message = ex.Message }; }
            finally { doc.UndoRecordingIsActive = false; }
        }
    }
}
namespace Rhino
{
    public sealed class RhinoDoc
    {
        public string Path;
        public bool IsReadOnly;
        public bool UndoRecordingIsActive;
        public double ModelAbsoluteTolerance = 0.01;
        public string ModelUnitSystem = "Millimeters";
        public ObjectTable Objects = new ObjectTable();
        public LayerTable Layers = new LayerTable();
    }
    public sealed class ObjectTable
    {
        public RhinoObject Current;
        public Dictionary<Guid, RhinoObject> Others = new Dictionary<Guid, RhinoObject>();
        public bool ReplaceSucceeds = true;
        public int ReplaceCalls;
        public int FailReplaceAt, ThrowAfterReplaceAt;
        public bool UnknownAfterReplace;
        public RhinoObject FindId(Guid id) => Current?.Id == id ? Current : Others.TryGetValue(id, out var value) ? value : null;
        public bool Replace(Guid id, Brep brep)
        {
            ReplaceCalls++;
            if (!ReplaceSucceeds || ReplaceCalls == FailReplaceAt) return false;
            var original = FindId(id);
            var updated = new RhinoObject { Id = id, Attributes = original.Attributes, Geometry = brep.DuplicateBrep() };
            if (Current?.Id == id) Current = updated; else Others[id] = updated;
            if (ReplaceCalls == ThrowAfterReplaceAt)
            {
                if (UnknownAfterReplace) updated.Geometry.Crc = 789;
                throw new InvalidOperationException("An event failed after replacement.");
            }
            return true;
        }
    }
    public sealed class LayerTable
    {
        public List<Layer> Items = new List<Layer> {
            new Layer { Id = new Guid("00000000-0000-0000-0000-000000000001"),
                ParentLayerId = new Guid("00000000-0000-0000-0000-000000000002") },
            new Layer { Id = new Guid("00000000-0000-0000-0000-000000000002") }
        };
        public Layer FindIndex(int index) => index >= 0 && index < Items.Count ? Items[index] : null;
        public Layer FindId(Guid id) => Items.Find(l => l.Id == id);
    }
}
namespace Rhino.DocObjects
{
    public enum ActiveSpace { ModelSpace, PageSpace }
    public sealed class ObjectAttributes
    {
        public ActiveSpace Space = ActiveSpace.ModelSpace;
        public string Name;
        public int[] Groups;
        public int LayerIndex;
    }
    public sealed class Layer
    {
        public Guid Id, ParentLayerId;
        public bool IsDeleted, IsLocked;
    }
    public sealed class RhinoObject
    {
        public Guid Id;
        public GeometryBase Geometry;
        public ObjectAttributes Attributes;
        public bool IsDeleted, IsReference, IsInstanceDefinitionGeometry, IsLocked;
    }
}
namespace Rhino.DocObjects.Custom
{
    public class UserDictionary
    {
        public Rhino.Collections.ArchivableDictionary Dictionary = new Rhino.Collections.ArchivableDictionary();
    }
    internal sealed class SharedUserDictionary : UserDictionary { }
    public sealed class UserDataList
    {
        public List<UserDictionary> Items = new List<UserDictionary>();
        public HashSet<Guid> NativeIds = new HashSet<Guid>();
        public int Count => Items.Count + NativeIds.Count;
        public UserDictionary Find(Type type) => Items.Find(item => item.GetType() == type);
        public bool Contains(Guid id) => NativeIds.Contains(id);
    }
}
namespace Rhino.Collections
{
    public sealed class ArchivableDictionary
    {
        public Dictionary<string, string> Values = new Dictionary<string, string>();
        public ArchivableDictionary Clone() { var copy = new ArchivableDictionary(); copy.ReplaceContentsWith(this); return copy; }
        public void ReplaceContentsWith(ArchivableDictionary other) { Values = new Dictionary<string, string>(other.Values); }
    }
}
namespace Rhino.Geometry
{
    public class GeometryBase
    {
        public uint Crc = 123;
        public int Shape = 123;
        public bool StringsWritable = true;
        public NameValueCollection Strings = new NameValueCollection();
        public Rhino.DocObjects.Custom.UserDataList UserData = new Rhino.DocObjects.Custom.UserDataList();
        public int DictionaryGetterCalls;
        public Rhino.Collections.ArchivableDictionary ExistingDictionary =>
            UserData.Find(typeof(Rhino.DocObjects.Custom.SharedUserDictionary))?.Dictionary;
        public Rhino.Collections.ArchivableDictionary UserDictionary
        {
            get
            {
                DictionaryGetterCalls++;
                if (ExistingDictionary == null) UserData.Items.Add(new Rhino.DocObjects.Custom.SharedUserDictionary());
                return ExistingDictionary;
            }
        }
        public uint DataCRC(uint initial) => Crc;
        public static bool GeometryEquals(GeometryBase first, GeometryBase second) => first.Shape == second.Shape;
        public NameValueCollection GetUserStrings() => new NameValueCollection(Strings);
        public bool SetUserString(string key, string value)
        {
            if (!StringsWritable) return false;
            Strings[key] = value;
            UserData.NativeIds.Add(new Guid("CE28DE29-F4C5-4FAA-A50A-C3A6849B6329"));
            return true;
        }
    }
    public struct Vector3d
    {
        public double X, Y, Z;
        public Vector3d(double x, double y, double z) { X = x; Y = y; Z = z; }
        public double Length => Math.Sqrt(X * X + Y * Y + Z * Z);
        public bool IsValid => Double.IsFinite(X) && Double.IsFinite(Y) && Double.IsFinite(Z);
        public static double Multiply(Vector3d a, Vector3d b) => a.X * b.X + a.Y * b.Y + a.Z * b.Z;
    }
    public struct Plane { public Vector3d Normal; }
    public struct Transform { public static Transform Translation(Vector3d vector) => new Transform(); }
    public sealed class Face
    {
        public bool Planar = true;
        public bool TryGetPlane(out Plane plane, double tolerance)
        { plane = new Plane { Normal = new Vector3d(0, 0, 1) }; return Planar; }
        public bool IsPlanar(double tolerance) => Planar;
        public int[] AdjacentFaces() => new[] { 1, 2 };
    }
    public sealed class Brep : GeometryBase, IDisposable
    {
        public static int PushCalls;
        public List<Face> Faces = new List<Face> { new Face(), new Face(), new Face() };
        public bool IsValid = true, IsSolid = true, IsManifold = true, Touched;
        public int SolidOrientation = 1;
        public double Volume = 100;
        public string Outcome = "success";
        public Brep DuplicateBrep()
        {
            var copy = (Brep)MemberwiseClone();
            copy.UserData = new Rhino.DocObjects.Custom.UserDataList();
            copy.UserData.NativeIds = new HashSet<Guid>(UserData.NativeIds);
            copy.Strings = new NameValueCollection(Strings);
            if (ExistingDictionary != null)
                copy.UserData.Items.Add(new Rhino.DocObjects.Custom.SharedUserDictionary { Dictionary = ExistingDictionary.Clone() });
            return copy;
        }
        public Brep PushPullExtend(int face, Transform transform, double tolerance)
        {
            PushCalls++;
            Touched = true;
            if (Outcome == "null") return null;
            var result = new Brep { Crc = 456, Shape = 456, Volume = 150 };
            switch (Outcome)
            {
                case "invalid": result.IsValid = false; break;
                case "open": result.IsSolid = false; break;
                case "nonmanifold": result.IsManifold = false; break;
                case "inward": result.SolidOrientation = -1; break;
                case "zero": result.Volume = 0; break;
                case "nonfinite": result.Volume = Double.NaN; break;
                case "nochange": result.Crc = 123; result.Shape = 123; break;
                case "metadata_only": result.Shape = 123; break;
                case "strings_failure": result.StringsWritable = false; break;
            }
            return result;
        }
        public void Dispose() { }
    }
    public sealed class VolumeMassProperties : IDisposable
    {
        public double Volume;
        public static VolumeMassProperties Compute(Brep brep) => new VolumeMassProperties { Volume = brep.Volume };
        public void Dispose() { }
    }
}
