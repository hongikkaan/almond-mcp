using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.FileIO;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    /// <summary>Clear the bound document's local temp tree while retaining its root layer.</summary>
    public static class StepTempCleanup
    {
        private readonly record struct AttributeStamp(string Common, string UserStrings, string UserDictionary, int UserDataCount);
        private readonly record struct MemberStamp(uint? GeometryCrc, AttributeStamp Attributes, Guid DefinitionId, Transform? Transform);
        private readonly record struct InstanceStamp(Guid Id, Guid ParentId, Guid DefinitionId, int LayerIndex, Transform Transform, AttributeStamp Attributes);
        private readonly record struct NestedInstance(Guid ParentId, InstanceObject Object);
        private sealed record DefinitionEdit(Guid Id, string Name, MemberStamp[] Before, MemberStamp[] Retained,
            InstanceStamp[] Instances, int Removed);

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                string path = (string)request["expected_model_path"];
                if (doc == null || string.IsNullOrWhiteSpace(doc.Path) || string.IsNullOrWhiteSpace(path) ||
                    !Path.IsPathRooted(path) ||
                    !string.Equals(Path.GetFullPath(doc.Path), Path.GetFullPath(path), StringComparison.OrdinalIgnoreCase))
                    return Error("The cleanup target differs from the bound model.", "not_started");
                if (doc.IsReadOnly)
                    return Error("The bound document is read-only.", "not_started");

                var editor = EditingContext.Observe(doc);
                if ((bool?)editor["stable"] != true || (string)editor["mode"] != "model")
                    return Error("Finish the active Rhino editor or command before removing temp.", "not_started");

                var layers = doc.Layers.Where(layer => layer != null && !layer.IsDeleted).ToArray();
                var root = layers.SingleOrDefault(layer => layer.ParentLayerId == Guid.Empty &&
                    !layer.IsReference && string.Equals(layer.Name, "temp", StringComparison.OrdinalIgnoreCase));
                if (root == null)
                    return Success(0, 0);

                var branch = new List<Layer> { root };
                var children = layers.ToLookup(layer => layer.ParentLayerId);
                for (int i = 0; i < branch.Count; ++i)
                    branch.AddRange(children[branch[i].Id]);
                if (branch.Any(layer => layer.IsReference))
                    return Error("The temp tree contains reference layers. The document was left unchanged.", "not_started");

                var targetLayers = branch.Select(layer => (layer.Id, layer.Index)).ToArray();
                var deletedLayers = targetLayers.Skip(1).ToArray();
                var indices = targetLayers.Select(layer => layer.Index).ToHashSet();
                var objects = doc.Objects.GetObjectList(new ObjectEnumeratorSettings {
                    ActiveObjects = true, NormalObjects = true, HiddenObjects = true, LockedObjects = true,
                    ReferenceObjects = true, IdefObjects = false, IncludeLights = true, IncludeGrips = false,
                    DeletedObjects = false
                }).Where(obj => indices.Contains(obj.Attributes.LayerIndex)).ToArray();
                if (objects.Any(obj => obj.IsReference))
                    return Error("The temp tree contains reference objects. The document was left unchanged.", "not_started");
                var definitionEdits = PlanDefinitionEdits(doc, indices);
                var targetObjects = objects.Select(obj => (obj.Id, obj.Attributes.LayerIndex)).ToArray();
                int previousCurrent = doc.Layers.CurrentLayerIndex;
                int addedLayer = -1;
                string failureMessage = "Rhino did not confirm successful temp cleanup.";
                var result = new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    started = true;
                    try
                    {
                        if (indices.Contains(previousCurrent) && previousCurrent != root.Index)
                        {
                            var fallback = root.IsVisible && !root.IsLocked ? root : layers.FirstOrDefault(layer =>
                                layer.ParentLayerId == Guid.Empty && !layer.IsReference && !indices.Contains(layer.Index) &&
                                layer.IsVisible && !layer.IsLocked);
                            int next = fallback?.Index ?? (addedLayer = doc.Layers.Add());
                            if (next < 0 || !doc.Layers.SetCurrentLayerIndex(next, true))
                                throw new InvalidOperationException("Rhino could not set a current layer outside the temp descendants.");
                        }
                        foreach (var edit in definitionEdits)
                        {
                            var definition = doc.InstanceDefinitions.FindId(edit.Id);
                            var mismatch = MemberMismatch(definition, edit.Before);
                            if (mismatch != null)
                                throw new InvalidOperationException($"Block '{edit.Name}' changed before cleanup: {mismatch}.");
                            var retained = definition.GetObjects().Where(obj => !indices.Contains(obj.Attributes.LayerIndex)).ToArray();
                            if (!doc.InstanceDefinitions.ModifyGeometry(definition.Index,
                                retained.Select(obj => obj.Geometry), retained.Select(obj => obj.Attributes)))
                            {
                                throw new InvalidOperationException(retained.Length == 0
                                    ? $"Rhino declined to remove the last members of block definition '{edit.Name}'."
                                    : $"Rhino could not remove temp members from block definition '{edit.Name}'.");
                            }
                        }

                        foreach (var target in targetObjects)
                        {
                            var obj = FindObject(doc, target.Id);
                            if (obj == null || obj.IsReference || obj.Attributes.LayerIndex != target.LayerIndex ||
                                obj.Attributes.IsInstanceDefinitionObject || !DeleteObject(doc, obj))
                                throw new InvalidOperationException($"Rhino could not delete temp object {target.Id}.");
                        }
                        // Parent-first traversal in reverse deletes each descendant before its parent.
                        foreach (var target in deletedLayers.Reverse())
                        {
                            if (!LayerExists(doc, target.Id, target.Index) || doc.Layers[target.Index].IsReference ||
                                !doc.Layers.Delete(target.Index, true))
                                throw new InvalidOperationException($"Rhino could not delete temp layer {target.Id}.");
                        }
                        if (!LayerExists(doc, root.Id, root.Index) ||
                            deletedLayers.Any(layer => LayerExists(doc, layer.Id, layer.Index)) ||
                            targetObjects.Any(obj => FindObject(doc, obj.Id) != null))
                            throw new InvalidOperationException("Rhino did not retain the temp root or remove all targeted layers and objects.");
                        var nested = definitionEdits.Count == 0 ? null : ActiveNestedInstances(doc);
                        foreach (var edit in definitionEdits)
                        {
                            var definition = doc.InstanceDefinitions.FindId(edit.Id);
                            var mismatch = MemberMismatch(definition, edit.Retained) ?? InstanceMismatch(definition, nested[edit.Id],
                                edit.Instances.Where(instance => !indices.Contains(instance.LayerIndex)));
                            if (mismatch != null)
                                throw new InvalidOperationException($"Rhino could not verify block '{edit.Name}' after temp cleanup: {mismatch}.");
                        }
                        return null;
                    }
                    catch (Exception error)
                    {
                        failureMessage = error.Message;
                        try { RhinoApp.WriteLine($"Almond Step temp cleanup failed before rollback: {error}"); }
                        catch { /* Undo is required even if the command log is unavailable. */ }
                        throw;
                    }
                });
                if (result.Status == "success" && result.ResultError == null)
                    return Success(deletedLayers.Length, targetObjects.Length + definitionEdits.Sum(edit => edit.Removed));
                if (!started)
                    return Error("Rhino could not start the temp cleanup in the bound document.", "not_started");

                var restoredNested = definitionEdits.Count == 0 ? null : ActiveNestedInstances(doc);
                bool restored = targetLayers.All(layer => LayerExists(doc, layer.Id, layer.Index)) &&
                    targetObjects.All(obj => FindObject(doc, obj.Id)?.Attributes.LayerIndex == obj.LayerIndex) &&
                    definitionEdits.All(edit =>
                    {
                        var definition = doc.InstanceDefinitions.FindId(edit.Id);
                        return MemberMismatch(definition, edit.Before) == null &&
                            InstanceMismatch(definition, restoredNested[edit.Id], edit.Instances) == null;
                    }) &&
                    (addedLayer < 0 || addedLayer >= doc.Layers.Count ||
                        doc.Layers[addedLayer] == null || doc.Layers[addedLayer].IsDeleted);
                if (restored && doc.Layers.CurrentLayerIndex != previousCurrent)
                    restored = doc.Layers.SetCurrentLayerIndex(previousCurrent, true);
                return Error(failureMessage, restored ? "rolled_back" : "unknown");
            }
            catch (Exception error)
            {
                return Error(error.Message, started ? "unknown" : "not_started");
            }
        }

        private static List<DefinitionEdit> PlanDefinitionEdits(RhinoDoc doc, HashSet<int> indices)
        {
            var edits = new List<DefinitionEdit>();
            ILookup<Guid, NestedInstance> nested = null;
            foreach (var definition in doc.InstanceDefinitions)
            {
                if (definition == null || definition.IsDeleted || definition.IsReference)
                    continue;
                var members = definition.GetObjects();
                var targeted = members.Where(obj => indices.Contains(obj.Attributes.LayerIndex)).ToArray();
                if (targeted.Length == 0)
                    continue;
                if (definition.UpdateType != InstanceDefinitionUpdateType.Static || targeted.Any(obj => obj.IsReference))
                    throw new InvalidOperationException(
                        $"Block definition '{definition.Name}' contains linked or reference geometry on temp.");
                var retained = members.Where(obj => !indices.Contains(obj.Attributes.LayerIndex));
                nested ??= ActiveNestedInstances(doc);
                edits.Add(new DefinitionEdit(definition.Id, definition.Name, Stamps(members), Stamps(retained),
                    InstanceStamps(definition, nested[definition.Id]).ToArray(), targeted.Length));
            }
            return edits;
        }

        private static MemberStamp[] Stamps(IEnumerable<RhinoObject> members) =>
            members.Select(obj =>
            {
                var instance = obj as InstanceObject;
                // Updating a child definition can change the CRC of its instance-reference geometry.
                return new MemberStamp(instance == null ? obj.Geometry.DataCRC(0) : null, StampAttributes(obj),
                    instance?.InstanceDefinition.Id ?? Guid.Empty, instance?.InstanceXform);
            }).ToArray();

        private static AttributeStamp StampAttributes(RhinoObject obj)
        {
            using var attributes = obj.Attributes.Duplicate();
            // Rhino can assign new IDs to the definition members recreated by ModifyGeometry.
            if (attributes == null)
                throw new InvalidOperationException($"Rhino could not read attributes for block object {obj.Id}.");
            attributes.ObjectId = Guid.Empty;
            string data = (string)JObject.Parse(attributes.ToJSON(new SerializationOptions { WriteUserData = false }))["data"];
            if (string.IsNullOrEmpty(data))
                throw new InvalidOperationException($"Rhino could not serialize attributes for block object {obj.Id}.");
            // Rhino increments internal userdata copy counters when it recreates definition members.
            int userDataCount = attributes.UserData.Count;
            var strings = attributes.GetUserStrings();
            var userStrings = new JObject();
            if (strings != null)
                foreach (var key in strings.AllKeys.OrderBy(key => key, StringComparer.Ordinal))
                    userStrings[key] = strings[key];
            var dictionary = attributes.UserDictionary;
            // Use Rhino's typed dictionary archive without the owning userdata record and its copy counter.
#pragma warning disable SYSLIB0050
            var archive = new SerializationInfo(dictionary.GetType(), new FormatterConverter());
            dictionary.GetObjectData(archive, default);
#pragma warning restore SYSLIB0050
            return new AttributeStamp(data, userStrings.ToString(Newtonsoft.Json.Formatting.None),
                Convert.ToBase64String((byte[])archive.GetValue("data", typeof(byte[]))), userDataCount);
        }

        private static ILookup<Guid, NestedInstance> ActiveNestedInstances(RhinoDoc doc) =>
            // GetReferences(2) can include previous members no longer owned by an active definition.
            doc.InstanceDefinitions.Where(owner => owner != null && !owner.IsDeleted)
                .SelectMany(owner => owner.GetObjects().OfType<InstanceObject>()
                    .Where(instance => !instance.IsDeleted && instance.InstanceDefinition != null)
                    .Select(instance => new NestedInstance(owner.Id, instance)))
                .ToLookup(entry => entry.Object.InstanceDefinition.Id);

        private static IEnumerable<InstanceStamp> InstanceStamps(InstanceDefinition definition, IEnumerable<NestedInstance> nested)
        {
            InstanceStamp Stamp(InstanceObject obj, Guid id, Guid parentId) => new InstanceStamp(id, parentId, obj.InstanceDefinition.Id,
                obj.Attributes.LayerIndex, obj.InstanceXform, StampAttributes(obj));
            // Definition members can get new object IDs. Their content and placement must still match.
            return definition.GetReferences(0).Select(obj => Stamp(obj, obj.Id, Guid.Empty))
                .Concat(nested.Select(entry => Stamp(entry.Object, Guid.Empty, entry.ParentId)));
        }

        private static string InstanceMismatch(InstanceDefinition definition, IEnumerable<NestedInstance> nested,
            IEnumerable<InstanceStamp> expected)
        {
            var before = expected.ToLookup(instance => instance);
            var after = InstanceStamps(definition, nested).ToLookup(instance => instance);
            if (before.Count == after.Count && before.All(group => group.Count() == after[group.Key].Count()))
                return null;
            return $"retained instance identities, transforms or attributes differ (expected {before.Sum(group => group.Count())}, observed {after.Sum(group => group.Count())})";
        }

        private static string MemberMismatch(InstanceDefinition definition, MemberStamp[] expected)
        {
            if (definition == null || definition.IsDeleted)
                return "definition missing";
            var actual = Stamps(definition.GetObjects());
            if (actual.Length != expected.Length)
                return $"expected {expected.Length} retained members, observed {actual.Length}";
            for (int index = 0; index < expected.Length; ++index)
            {
                if (actual[index].GeometryCrc != expected[index].GeometryCrc)
                    return $"member {index + 1} geometry differs";
                if (actual[index].DefinitionId != expected[index].DefinitionId || actual[index].Transform != expected[index].Transform)
                    return $"member {index + 1} nested definition or placement differs";
                if (actual[index].Attributes != expected[index].Attributes)
                    return $"member {index + 1} attributes or user data differ";
            }
            return null;
        }

        private static RhinoObject FindObject(RhinoDoc doc, Guid id) =>
            doc.Objects.FindId(id) ?? doc.Lights.FindId(id);

        private static bool DeleteObject(RhinoDoc doc, RhinoObject obj) => obj is LightObject light
            ? doc.Lights.Delete(light.Index, true)
            : doc.Objects.Delete(obj, true, true);

        private static bool LayerExists(RhinoDoc doc, Guid id, int index)
        {
            var layer = index >= 0 && index < doc.Layers.Count ? doc.Layers[index] : null;
            return layer != null && !layer.IsDeleted && layer.Id == id;
        }

        private static JObject Success(int layers, int objects) => new JObject {
            ["status"] = "success",
            ["cleanup"] = new JObject { ["deleted_layers"] = layers, ["deleted_objects"] = objects }
        };

        private static JObject Error(string message, string state) => new JObject {
            ["status"] = "error", ["message"] = message, ["cleanup_state"] = state
        };
    }
}
