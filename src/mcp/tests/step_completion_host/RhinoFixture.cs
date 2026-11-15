using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Rhino.Runtime
{
    public class CommonObject
    {
        public Dictionary<string, string> Text = new Dictionary<string, string>();
        public string GetUserString(string key) => Text.TryGetValue(key, out var value) ? value : null;
        public NameValueCollection GetUserStrings() { var result = new NameValueCollection(); foreach (var pair in Text) result.Add(pair.Key, pair.Value); return result; }
    }
}
namespace Rhino.FileIO
{
    public class SerializationOptions { }
    public class BinaryArchiveWriter { public void Write3dmChunkVersion(int major, int minor) { } public void WriteString(string text) { } }
    public class BinaryArchiveReader { public void Read3dmChunkVersion(out int major, out int minor) { major = 1; minor = 0; } public string ReadString() => ""; }
    public class FileReadOptions { public bool OpenMode, ImportMode, InsertMode, NewMode, ImportReferenceMode; }
}
namespace Rhino.DocObjects
{
    public enum ActiveSpace { ModelSpace, PageSpace }
    public class ObjectAttributes : Rhino.Runtime.CommonObject
    {
        public int LayerIndex;
        public ActiveSpace Space = ActiveSpace.ModelSpace;
        public string RenderMaterial = "original-material", ObjectColor = "12,34,56";
        public List<int> GroupIndices = new List<int>();
        public bool IsInGroup(int index) => GroupIndices.Contains(index);
        public void AddToGroup(int index) { if (!IsInGroup(index)) GroupIndices.Add(index); }
        public void RemoveFromGroup(int index) { GroupIndices.Remove(index); }
        [JsonIgnore] public int JsonCalls;
        public string ToJSON(Rhino.FileIO.SerializationOptions options) { JsonCalls++; return JsonConvert.SerializeObject(this); }
        public ObjectAttributes Duplicate() => JsonConvert.DeserializeObject<ObjectAttributes>(JsonConvert.SerializeObject(this));
    }
    public class Geometry : Rhino.Runtime.CommonObject { public uint Crc = 23; [JsonIgnore] public int CrcCalls; public uint DataCRC(uint seed) { CrcCalls++; return Crc; } }
    public class RhinoObject
    {
        public Guid Id = Guid.NewGuid();
        public bool IsDeleted, IsLocked, IsReference, IsInstanceDefinitionGeometry;
        public Geometry Geometry = new Geometry();
        public ObjectAttributes Attributes = new ObjectAttributes();
    }
    public class GripObject : RhinoObject { }
    public class ClippingPlaneObject : RhinoObject { }
    public class Layer : Rhino.Runtime.CommonObject
    {
        public Guid Id = Guid.NewGuid(), ParentLayerId;
        public int Index;
        public string FullPath;
        public bool IsDeleted, IsLocked, IsReference, IsReferenceParentLayer, IsCurrent;
        public uint Crc = 31;
        public uint DataCRC(uint seed) => Crc;
    }
    public class ObjectEnumeratorSettings
    {
        public bool NormalObjects, HiddenObjects, LockedObjects, ReferenceObjects, ActiveObjects,
            IdefObjects, DeletedObjects, IncludeLights, IncludeGrips, IncludePhantoms;
        public int LayerIndexFilter = -1;
    }
    public class ObjectTable
    {
        public List<RhinoObject> Rows = new List<RhinoObject>();
        public Rhino.RhinoDoc Doc;
        public Guid FailDelete;
        public Action AfterDelete;
        public List<Guid> DeletedIds = new List<Guid>();
        public int ScanCalls, FullScanCalls, LayerScanCalls, FindUserCalls;
        private void Check(ObjectEnumeratorSettings s)
        { if (!s.NormalObjects || !s.HiddenObjects || !s.LockedObjects || !s.ReferenceObjects || !s.ActiveObjects || s.DeletedObjects || !s.IncludeLights || !s.IncludeGrips || !s.IncludePhantoms) throw new Exception("Enumeration flags changed."); }
        public IEnumerable<RhinoObject> GetObjectList(ObjectEnumeratorSettings settings)
        {
            ScanCalls++;
            if (settings.LayerIndexFilter < 0) FullScanCalls++; else LayerScanCalls++;
            return Rows.Where(o => !o.IsDeleted && (settings.ReferenceObjects || !o.IsReference) &&
                // Actual Rhino 8: true selects definition geometry instead of adding it to active objects.
                settings.IdefObjects == o.IsInstanceDefinitionGeometry && (settings.IncludeGrips || !(o is GripObject)) &&
                (settings.LayerIndexFilter < 0 || o.Attributes.LayerIndex == settings.LayerIndexFilter));
        }
        public RhinoObject[] FindByUserString(string key, string value, bool caseSensitive, bool searchGeometry, bool searchAttributes, ObjectEnumeratorSettings settings)
        {
            Check(settings); FindUserCalls++;
            if (!caseSensitive || searchGeometry || !searchAttributes || key != "ps:clip") throw new Exception("Legacy query must use exact attributes.");
            var matches = GetObjectList(settings).Where(o => o.Attributes.GetUserString(key) == value).ToArray();
            return matches.Length == 0 ? null : matches;
        }
        public RhinoObject FindId(Guid id) => Rows.FirstOrDefault(o => !o.IsDeleted && o.Id == id);
        public bool ModifyAttributes(Guid id, ObjectAttributes attributes, bool quiet) { Rows.Single(o => o.Id == id).Attributes = attributes; Doc.Changed = true; return true; }
        public bool Delete(Guid id, bool quiet)
        {
            Doc.Events.Add("delete_object");
            if (id == FailDelete) return false;
            Rows.Single(o => o.Id == id).IsDeleted = true; DeletedIds.Add(id); Doc.Changed = true;
            AfterDelete?.Invoke(); return true;
        }
    }
    public class LayerTable : List<Layer>
    {
        public Rhino.RhinoDoc Doc;
        public Guid FailDelete;
        public Action AfterDelete;
        public List<Guid> DeletedIds = new List<Guid>();
        public int FindByFullPath(string path, int notFound) => this.FirstOrDefault(l => !l.IsDeleted && String.Equals(l.FullPath, path, StringComparison.OrdinalIgnoreCase))?.Index ?? notFound;
        public bool Delete(int index, bool quiet)
        {
            Doc.Events.Add("delete_layer"); var layer = this.Single(l => l.Index == index);
            if (layer.Id == FailDelete || this.Any(l => !l.IsDeleted && l.ParentLayerId == layer.Id) || Doc.Objects.Rows.Any(o => !o.IsDeleted && o.Attributes.LayerIndex == index)) return false;
            layer.IsDeleted = true; DeletedIds.Add(layer.Id); Doc.Changed = true; AfterDelete?.Invoke(); return true;
        }
    }
    public class Group { public Guid Id = Guid.NewGuid(); public int Index; public string Name; public bool IsDeleted, IsReference; }
    public class GroupTable : List<Group>
    {
        public Rhino.RhinoDoc Doc;
        public int Add(string name, IEnumerable<Guid> members)
        {
            int index = Count; base.Add(new Group { Index = index, Name = name });
            foreach (var id in members) Doc.Objects.FindId(id).Attributes.AddToGroup(index);
            Doc.Changed = true; return index;
        }
        public Group FindId(Guid id) => this.FirstOrDefault(group => group.Id == id);
        public RhinoObject[] GroupMembers(int index) => Doc.Objects.Rows.Where(o => !o.IsDeleted && o.Attributes.IsInGroup(index)).ToArray();
    }
}
namespace Rhino.Commands
{
    public class UndoRedoEventArgs : EventArgs { public uint UndoSerialNumber; public bool IsPurgeRecord; }
    public class CustomUndoEventArgs : EventArgs { public Rhino.RhinoDoc Document; public object Tag; public string ActionDescription; }
    public static class Command
    {
        public static event EventHandler<UndoRedoEventArgs> UndoRedo;
        public static void Purge(uint serial) => UndoRedo?.Invoke(null, new UndoRedoEventArgs { UndoSerialNumber = serial, IsPurgeRecord = true });
    }
}
namespace Rhino
{
    public class RuntimeData
    {
        private readonly Dictionary<string, object> values = new Dictionary<string, object>();
        public T GetValue<T>(string key, Func<string, T> create) { if (!values.TryGetValue(key, out var value)) values[key] = value = create(key); return (T)value; }
    }
    public static class RhinoApp { public static void WriteLine(string text) { } }
    public class ViewTable { public bool FailRedraw; public int Redraws; public void Redraw() { Redraws++; if (FailRedraw) throw new Exception("display failed"); } }
    public class RhinoDoc
    {
        public static RhinoDoc ActiveDoc;
        public string Path = @"C:\offline\model.3dm";
        public uint RuntimeSerialNumber = 7;
        public bool IsReadOnly, UndoRecordingIsActive, UndoActive, RedoActive, StableEditor = true, UiThread = true;
        public bool Changed, Modified, FailBeginUndo, FailEndUndo, FailUndo;
        public uint CurrentUndoRecordSerialNumber;
        private uint nextSerial = 1;
        public uint NextUndoRecordSerialNumber => nextSerial;
        public List<string> Events = new List<string>();
        public List<string> NamedViews = new List<string> { "existing-named-view" }, Layouts = new List<string> { "existing-layout" };
        public Action BeforeUndo;
        public int UndoCalls, UndoRecords, ClearedRedo;
        public DocObjects.LayerTable Layers = new DocObjects.LayerTable();
        public DocObjects.ObjectTable Objects = new DocObjects.ObjectTable();
        public DocObjects.GroupTable Groups = new DocObjects.GroupTable();
        public RuntimeData RuntimeData = new RuntimeData();
        public ViewTable Views = new ViewTable();
        private string startLayers, startObjects, startGroups, lastLayers, lastObjects, lastGroups;
        private List<Action> customUndo = new List<Action>(), lastCustomUndo = new List<Action>();
        private bool recoveryRecord;
        public RhinoDoc() { Layers.Doc = this; Objects.Doc = this; Groups.Doc = this; ActiveDoc = this; }
        public bool AddCustomUndoEvent(string description, EventHandler<Rhino.Commands.CustomUndoEventArgs> handler, object tag)
        {
            if (!UndoRecordingIsActive) return false;
            customUndo.Add(() => handler(this, new Rhino.Commands.CustomUndoEventArgs { Document = this, Tag = tag, ActionDescription = description }));
            Changed = true; return true;
        }
        public uint BeginUndoRecord(string name)
        {
            Events.Add("begin_undo"); UndoCalls++;
            if (FailBeginUndo || UndoRecordingIsActive) return 0;
            CurrentUndoRecordSerialNumber = nextSerial++; UndoRecordingIsActive = true; Changed = false;
            startLayers = JsonConvert.SerializeObject(Layers); startObjects = JsonConvert.SerializeObject(Objects.Rows);
            startGroups = JsonConvert.SerializeObject(Groups); customUndo = new List<Action>();
            BeforeUndo?.Invoke(); return CurrentUndoRecordSerialNumber;
        }
        public bool EndUndoRecord(uint serial)
        {
            if (FailEndUndo || !UndoRecordingIsActive || CurrentUndoRecordSerialNumber != serial) return false;
            Events.Add("end_undo"); UndoRecordingIsActive = false; CurrentUndoRecordSerialNumber = 0;
            if (recoveryRecord) { recoveryRecord = false; UndoActive = false; return true; }
            bool changed = Changed || startLayers != JsonConvert.SerializeObject(Layers) || startObjects != JsonConvert.SerializeObject(Objects.Rows);
            if (!changed) Rhino.Commands.Command.Purge(serial);
            else { lastLayers = startLayers; lastObjects = startObjects; lastGroups = startGroups; lastCustomUndo = customUndo; UndoRecords++; }
            return true;
        }
        public bool Undo()
        {
            Events.Add("undo_recovery");
            if (FailUndo || lastLayers == null || UndoRecordingIsActive) return false;
            Layers.Clear(); Layers.AddRange(JsonConvert.DeserializeObject<List<DocObjects.Layer>>(lastLayers));
            Objects.Rows = JsonConvert.DeserializeObject<List<DocObjects.RhinoObject>>(lastObjects);
            Groups.Clear(); Groups.AddRange(JsonConvert.DeserializeObject<List<DocObjects.Group>>(lastGroups));
            CurrentUndoRecordSerialNumber = nextSerial++; UndoRecordingIsActive = true; UndoActive = true; recoveryRecord = true;
            var restore = lastCustomUndo.ToArray(); customUndo = new List<Action>();
            foreach (var callback in restore.Reverse()) callback();
            lastLayers = lastObjects = null; return true;
        }
        public bool ManualUndo() { if (!Undo()) return false; return EndUndoRecord(CurrentUndoRecordSerialNumber); }
        public void ClearRedoRecords() { ClearedRedo++; customUndo.Clear(); }
    }
}
namespace RhinoAlmondBridge
{
    // Only the metadata-name adapter is stubbed; semantic registry behavior is the linked actual source.
    public static class ModelingMetadata { public static string Key(string name) => name == "component_record" ? "almond:component_record" : throw new ArgumentException(name); }
    public static class EditingContext
    {
        public static JObject Observe(Rhino.RhinoDoc doc)
        {
            doc.Events.Add("observe_editor");
            return new JObject { ["stable"] = doc.StableEditor && doc.UiThread && !doc.UndoRecordingIsActive && !doc.UndoActive && !doc.RedoActive, ["mode"] = "model" };
        }
    }
}
