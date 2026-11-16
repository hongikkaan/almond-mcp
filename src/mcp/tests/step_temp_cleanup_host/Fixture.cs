using System;
using System.Collections.Generic;
using System.Linq;
using System.Collections.Specialized;
using System.Runtime.Serialization;
using Newtonsoft.Json.Linq;

namespace Rhino
{
    public static class RhinoApp
    {
        public static bool RejectLog;
        public static string LastLog;
        public static void WriteLine(string text)
        {
            if (RejectLog)
                throw new InvalidOperationException("Log unavailable");
            LastLog = text;
        }
    }

    public sealed class RhinoDoc
    {
        public string Path { get; set; }
        public bool IsReadOnly { get; set; }
        public Rhino.DocObjects.LayerTable Layers { get; } = new();
        public Rhino.DocObjects.ObjectTable Objects { get; } = new();
        public Rhino.DocObjects.LightTable Lights { get; } = new();
        public Rhino.DocObjects.InstanceDefinitionTable InstanceDefinitions { get; } = new();
    }
}

namespace Rhino.Geometry
{
    public sealed class GeometryBase
    {
        public readonly uint Code;
        public GeometryBase(uint code) { Code = code; }
        public uint DataCRC(uint seed) => Code;
    }

    public readonly record struct Transform(int FixtureTransform);
}

namespace Rhino.FileIO
{
    public sealed class SerializationOptions
    {
        public bool WriteUserData { get; set; }
    }
}

namespace Rhino.DocObjects
{
    using Rhino.Geometry;
    public sealed class Layer
    {
        public Guid Id = Guid.NewGuid(), ParentLayerId;
        public string Name;
        public int Index;
        public bool IsDeleted, IsReference, IsVisible = true, IsLocked;
    }

    public sealed class LayerTable : List<Layer>
    {
        public int CurrentLayerIndex;
        public int FailedLayer = -1;
        public int Add()
        {
            Add(new Layer { Name = "Layer 01", Index = Count });
            return Count - 1;
        }
        public bool SetCurrentLayerIndex(int index, bool quiet)
        {
            if (!quiet || this[index].IsDeleted || this[index].IsReference ||
                !this[index].IsVisible || this[index].IsLocked)
                return false;
            CurrentLayerIndex = index;
            return true;
        }
        public bool Delete(int index, bool quiet)
        {
            var layer = this[index];
            if (!quiet || index == FailedLayer || index == CurrentLayerIndex || layer.IsReference ||
                this.Any(child => child.ParentLayerId == layer.Id && !child.IsDeleted))
                return false;
            return layer.IsDeleted = true;
        }
    }

    public sealed class ObjectAttributes : IDisposable
    {
        public int LayerIndex;
        public bool IsInstanceDefinitionObject;
        public Guid ObjectId;
        public string Name;
        public int CopyCount;
        public List<object> UserData { get; } = new();
        public NameValueCollection UserStrings { get; } = new();
        public NameValueCollection GetUserStrings() => UserStrings;
        public DictionaryArchive UserDictionary { get; } = new();

        public ObjectAttributes Duplicate() => (ObjectAttributes)MemberwiseClone();
        public string ToJSON(Rhino.FileIO.SerializationOptions options) => new JObject {
            ["data"] = $"{LayerIndex}|{IsInstanceDefinitionObject}|{ObjectId}|{Name}" +
                (options.WriteUserData ? $"|{CopyCount}" : "")
        }.ToString();
        public void Dispose() { }
    }

    public sealed class DictionaryArchive
    {
        public byte Version;
        public void GetObjectData(SerializationInfo archive, StreamingContext context) =>
            archive.AddValue("data", new byte[] { Version });
    }

    public enum InstanceDefinitionUpdateType { Static, Linked }

    public sealed class InstanceDefinition
    {
        public Guid Id = Guid.NewGuid();
        public int Index;
        public string Name = "Fixture block";
        public bool IsDeleted, IsReference;
        public InstanceDefinitionUpdateType UpdateType;
        public RhinoObject[] Members;
        public InstanceObject[] Instances;
        public RhinoObject[] GetObjects() => Members;
        public InstanceObject[] GetReferences(int scope) => (Instances ?? Array.Empty<InstanceObject>())
            .Where(obj => !obj.IsDeleted && (scope == 1 || obj.Attributes.IsInstanceDefinitionObject == (scope == 2)))
            .ToArray();
    }

    public sealed class InstanceDefinitionTable : List<InstanceDefinition>
    {
        public string Corruption;
        public InstanceDefinition FindId(Guid id) => this.FirstOrDefault(d => d.Id == id && !d.IsDeleted);
        public bool ModifyGeometry(int index, IEnumerable<GeometryBase> geometry, IEnumerable<ObjectAttributes> attributes)
        {
            var definition = this[index];
            var retained = attributes.ToArray();
            if (definition.UpdateType != InstanceDefinitionUpdateType.Static || Corruption == "block-empty-declined" ||
                !geometry.SequenceEqual(definition.Members.Where(o => retained.Contains(o.Attributes)).Select(o => o.Geometry)))
                return false;
            foreach (var member in definition.Members.Where(o => !retained.Contains(o.Attributes)))
                member.IsDeleted = true;
            definition.Members = definition.Members.Where(o => retained.Contains(o.Attributes)).ToArray();
            if (Corruption == "block-attributes")
                definition.Members[0].Attributes.Name = "lost retained attributes";
            if (Corruption == "block-user-dictionary")
                definition.Members[0].Attributes.UserDictionary.Version++;
            if (Corruption == "block-user-strings")
                definition.Members[0].Attributes.UserStrings["Contents"] = "changed value";
            foreach (var member in definition.Members)
                member.Attributes.CopyCount++;
            if (Corruption == "block-order")
                Array.Reverse(definition.Members);
            if (Corruption == "block-nested")
                definition.GetReferences(2)[0].InstanceXform = new Transform(99);
            if (Corruption == "block-nested-filter")
                foreach (var instance in definition.Members.OfType<InstanceObject>())
                {
                    var ghost = new InstanceObject { Id = instance.Id, Attributes = instance.Attributes.Duplicate(),
                        InstanceDefinition = instance.InstanceDefinition, InstanceXform = instance.InstanceXform };
                    instance.InstanceDefinition.Instances = instance.InstanceDefinition.Instances.Append(ghost).ToArray();
                    instance.Id = Guid.NewGuid();
                    instance.Geometry = new GeometryBase(405);
                }
            return true;
        }
    }

    public sealed class InstanceObject : RhinoObject
    {
        public InstanceDefinition InstanceDefinition;
        public Transform InstanceXform;
    }

    public class RhinoObject
    {
        public Guid Id = Guid.NewGuid();
        public ObjectAttributes Attributes = new();
        public GeometryBase Geometry = new GeometryBase(0);
        public bool IsReference, IsDeleted, IsLocked, IsHidden;
    }

    public sealed class LightObject : RhinoObject
    {
        public int Index;
    }

    public sealed class LightTable : List<LightObject>
    {
        public LightObject FindId(Guid id) => this.FirstOrDefault(light => light.Id == id && !light.IsDeleted);
        public bool Delete(int index, bool quiet)
        {
            if (!quiet || this[index].IsReference) return false;
            return this[index].IsDeleted = true;
        }
    }

    public sealed class ObjectEnumeratorSettings
    {
        public bool ActiveObjects, NormalObjects, HiddenObjects, LockedObjects, ReferenceObjects,
            IdefObjects, IncludeLights, IncludeGrips, DeletedObjects;
    }

    public sealed class ObjectTable : List<RhinoObject>
    {
        public IEnumerable<RhinoObject> GetObjectList(ObjectEnumeratorSettings settings) => this.Where(o =>
            (settings.DeletedObjects || !o.IsDeleted) && (settings.ReferenceObjects || !o.IsReference) &&
            (settings.IdefObjects || !o.Attributes.IsInstanceDefinitionObject) &&
            (settings.IncludeLights || o is not LightObject) &&
            (o.IsHidden ? settings.HiddenObjects : o.IsLocked ? settings.LockedObjects : settings.NormalObjects));
        public RhinoObject FindId(Guid id) => this.FirstOrDefault(o => o.Id == id && !o.IsDeleted && o is not LightObject);
        public bool Delete(RhinoObject obj, bool quiet, bool ignoreModes)
        {
            if (!quiet || obj.IsReference || obj.Attributes.IsInstanceDefinitionObject || obj is LightObject ||
                (!ignoreModes && (obj.IsLocked || obj.IsHidden)))
                return false;
            return obj.IsDeleted = true;
        }
    }
}

namespace RhinoAlmondBridge
{
    using Rhino;
    using Rhino.DocObjects;

    public static class EditingContext
    {
        public static JObject Observe(RhinoDoc doc) => new() { ["stable"] = true, ["mode"] = "model" };
    }

    public sealed class ScriptResult
    {
        public string Status = "success", ResultError, Message;
    }

    public sealed class ScriptExecutor
    {
        internal ScriptResult ExecuteAction(RhinoDoc doc, Func<object> action)
        {
            int originalLayerCount = doc.Layers.Count;
            var originalMembers = doc.InstanceDefinitions.Select(d => d.Members).ToArray();
            try { action(); return new ScriptResult(); }
            catch (Exception error)
            {
                doc.Layers.RemoveRange(originalLayerCount, doc.Layers.Count - originalLayerCount);
                foreach (var layer in doc.Layers) layer.IsDeleted = false;
                foreach (var obj in doc.Objects) obj.IsDeleted = false;
                for (int i = 0; i < originalMembers.Length; ++i) doc.InstanceDefinitions[i].Members = originalMembers[i];
                return new ScriptResult { Status = "error", Message = error.Message };
            }
        }
    }

    public static class Program
    {
        public static void Main(string[] args)
        {
            var path = System.IO.Path.GetFullPath("fixture.3dm");
            var doc = new RhinoDoc { Path = path };
            Layer AddLayer(string name, Layer parent = null, bool reference = false)
            {
                var layer = new Layer { Name = name, ParentLayerId = parent?.Id ?? Guid.Empty,
                    Index = doc.Layers.Count, IsReference = reference };
                doc.Layers.Add(layer);
                return layer;
            }
            RhinoObject AddObject(Layer layer, bool reference = false)
            {
                var obj = new RhinoObject { IsReference = reference };
                obj.Attributes.LayerIndex = layer.Index;
                doc.Objects.Add(obj);
                return obj;
            }
            var drawing = AddLayer("Drawing");
            var temp = AddLayer("Temp");
            var child = AddLayer("tests", temp);
            var grandchild = AddLayer("empty", child);
            var attachment = AddLayer("temp", reference: true);
            AddLayer("temp", drawing);
            var keptDrawing = AddObject(drawing);
            var attachedObject = AddObject(attachment, reference: true);
            AddObject(temp).IsLocked = true;
            var hidden = AddObject(child);
            hidden.IsHidden = true;
            doc.Layers.CurrentLayerIndex = child.Index;
            if (args[0] == "root-only")
            {
                child.IsDeleted = grandchild.IsDeleted = true;
                hidden.IsDeleted = true;
                doc.Layers.CurrentLayerIndex = temp.Index;
            }
            if (args[0] == "locked-layer-rollback") doc.Layers.FailedLayer = child.Index;
            if (args[0] == "log-unavailable")
            {
                doc.Layers.FailedLayer = child.Index;
                RhinoApp.RejectLog = true;
            }
            InstanceDefinition definition = null, parentDefinition = null;
            InstanceObject keptInstance = null, tempInstance = null, keptNested = null;
            Guid nestedOriginalId = Guid.Empty;
            if (args[0].StartsWith("block-"))
            {
                var removed = AddObject(temp);
                removed.Geometry = new Rhino.Geometry.GeometryBase(101);
                removed.Attributes.IsInstanceDefinitionObject = true;
                var retained = AddObject(drawing);
                retained.Geometry = new Rhino.Geometry.GeometryBase(202);
                retained.Attributes.IsInstanceDefinitionObject = true;
                definition = new InstanceDefinition { Members = new[] { removed, retained } };
                if (args[0] is "block-empty" or "block-empty-declined")
                {
                    doc.Objects.Remove(retained);
                    definition.Members = new[] { removed };
                }
                if (args[0] == "block-linked") definition.UpdateType = InstanceDefinitionUpdateType.Linked;
                if (args[0] == "block-rollback") doc.Layers.FailedLayer = child.Index;
                keptInstance = new InstanceObject { InstanceDefinition = definition, InstanceXform = new Rhino.Geometry.Transform(10) };
                keptInstance.Attributes.LayerIndex = drawing.Index;
                tempInstance = new InstanceObject { InstanceDefinition = definition, InstanceXform = new Rhino.Geometry.Transform(20) };
                tempInstance.Attributes.LayerIndex = child.Index;
                doc.Objects.AddRange(new[] { keptInstance, tempInstance });
                definition.Instances = new[] { keptInstance, tempInstance };
                doc.InstanceDefinitions.Add(definition);
                doc.InstanceDefinitions.Corruption = args[0];
                if (args[0] == "block-order")
                {
                    var secondRetained = AddObject(drawing);
                    secondRetained.Geometry = new Rhino.Geometry.GeometryBase(303);
                    secondRetained.Attributes.IsInstanceDefinitionObject = true;
                    definition.Members = new[] { retained, removed, secondRetained };
                }
                if (args[0] is "block-nested" or "block-nested-filter")
                {
                    keptNested = new InstanceObject { InstanceDefinition = definition,
                        Geometry = new Rhino.Geometry.GeometryBase(404), InstanceXform = new Rhino.Geometry.Transform(30) };
                    nestedOriginalId = keptNested.Id;
                    keptNested.Attributes.LayerIndex = drawing.Index;
                    keptNested.Attributes.Name = "nested retained";
                    keptNested.Attributes.IsInstanceDefinitionObject = true;
                    definition.Instances = new[] { keptInstance, tempInstance, keptNested };
                    parentDefinition = new InstanceDefinition { Index = 1, Members = new RhinoObject[] { keptNested } };
                    if (args[0] == "block-nested-filter")
                    {
                        var tempNested = new InstanceObject { InstanceDefinition = definition,
                            Geometry = new Rhino.Geometry.GeometryBase(606), InstanceXform = new Rhino.Geometry.Transform(40) };
                        tempNested.Attributes.LayerIndex = child.Index;
                        tempNested.Attributes.IsInstanceDefinitionObject = true;
                        var sibling = AddObject(drawing);
                        sibling.Geometry = new Rhino.Geometry.GeometryBase(505);
                        sibling.Attributes.IsInstanceDefinitionObject = true;
                        definition.Instances = definition.Instances.Append(tempNested).ToArray();
                        parentDefinition.Members = new RhinoObject[] { keptNested, tempNested, sibling };
                    }
                    doc.InstanceDefinitions.Add(parentDefinition);
                }
            }
            if (args[0] == "ref-object") AddObject(child, reference: true);
            if (args[0] == "other-document") path += ".other";
            if (args[0] == "no-local-temp") temp.Name = "Study";
            if (args[0] == "light")
            {
                var light = new LightObject();
                light.Attributes.LayerIndex = child.Index;
                doc.Lights.Add(light);
                doc.Objects.Add(light);
            }
            if (args[0] == "new-current")
            {
                drawing.IsVisible = false;
                temp.IsVisible = false;
            }
            var result = StepTempCleanup.Handle(doc, new JObject { ["expected_model_path"] = path });
            Console.WriteLine(new JObject {
                ["result"] = result,
                ["layers"] = JArray.FromObject(doc.Layers.Where(l => !l.IsDeleted).Select(l => l.Name)),
                ["objects"] = doc.Objects.Count(o => !o.IsDeleted),
                ["current_layer"] = doc.Layers.CurrentLayerIndex,
                ["error_log"] = RhinoApp.LastLog,
                ["drawing_preserved"] = !keptDrawing.IsDeleted && keptDrawing.Attributes.LayerIndex == drawing.Index,
                ["attachment_preserved"] = !attachedObject.IsDeleted && attachedObject.Attributes.LayerIndex == attachment.Index,
                ["definition_members"] = definition == null ? null : JArray.FromObject(definition.Members.Select(o => o.Geometry.Code)),
                ["definition_preserved"] = definition != null && doc.InstanceDefinitions.FindId(definition.Id) == definition,
                ["parent_members"] = parentDefinition == null ? null : JArray.FromObject(parentDefinition.Members.Select(o => o.Geometry.Code)),
                ["nested_instance_preserved"] = keptNested != null && keptNested.Id != nestedOriginalId &&
                    keptNested.InstanceDefinition == definition && keptNested.Attributes.Name == "nested retained" &&
                    keptNested.InstanceXform.FixtureTransform == 30,
                ["outside_instance_preserved"] = keptInstance != null && doc.Objects.FindId(keptInstance.Id) == keptInstance &&
                    keptInstance.InstanceDefinition == definition && keptInstance.Attributes.LayerIndex == drawing.Index &&
                    keptInstance.InstanceXform.FixtureTransform == 10,
                ["temp_instance_deleted"] = tempInstance?.IsDeleted == true
            }.ToString(Newtonsoft.Json.Formatting.None));
        }
    }
}
