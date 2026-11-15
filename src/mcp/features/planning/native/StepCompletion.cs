using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    /// <summary>One automatic, undoable cleanup of the complete top-level temp hierarchy.</summary>
    public static class StepCompletion
    {
        // Relational metadata protects existing items; it never selects external items for deletion.
        private static readonly string[] ProtectedKeys = {
            "almond:component_id", "almond:component_record", "almond:sheet_id", "almond:sheet_metadata",
            "ps:generator", "ps:sources", "ps:clip", "ps:source_layer", "ps:placement", "ps:inherited_keys", "$TempBlockEditUserData$"
        };
        private sealed class LayerState { internal int Index, Depth; internal string Stamp; }
        private sealed class Snapshot
        {
            internal uint DocumentSerial;
            internal string ModelPath;
            internal Dictionary<Guid, string> Objects = new Dictionary<Guid, string>();
            internal Dictionary<Guid, LayerState> Layers = new Dictionary<Guid, LayerState>();
            internal Dictionary<Guid, string> OutsideObjects, OutsideLayers;
        }
        private sealed class Progress
        {
            internal bool Entered;
            // Successful Delete calls, not persisted deletions after failed Undo recovery.
            internal int Objects, Layers;
        }

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            var progress = new Progress();
            try
            {
                if (request == null || request.Properties().Any(p => p.Name != "type" && p.Name != "expected_model_path") ||
                    request["type"]?.Type != JTokenType.String || (string)request["type"] != "step_completion" ||
                    request["expected_model_path"]?.Type != JTokenType.String)
                    throw new ArgumentException("Step cleanup accepts only type and the bound expected_model_path.");
                RequireDocument(doc, (string)request["expected_model_path"]);
                var editor = EditingContext.Observe(doc);
                if ((bool?)editor["stable"] != true || (string)editor["mode"] != "model")
                    throw new ArgumentException("Finish commands and group/block editing before completing this Step.");
                var snapshot = Observe(doc, captureOutside: true);
                if (snapshot.Layers.Count == 0)
                    return new JObject { ["status"] = "success", ["result"] = JObject.FromObject(Completed(doc, progress)) };
                // Same native UI call; validation precedes the existing executor's Undo scope.
                var response = JObject.FromObject(new ScriptExecutor().ExecuteAction(doc, () => {
                    progress.Entered = true;
                    return Apply(doc, snapshot, progress);
                }));
                if ((string)response["status"] != "success" || response["result_error"]?.Type == JTokenType.String ||
                    (bool?)response["result"]?["cleanup_complete"] != true)
                    Failed(response, progress);
                return response;
            }
            catch (Exception error)
            {
                var response = new JObject { ["status"] = "error", ["error_code"] = "step_cleanup_failed", ["message"] = error.Message };
                Failed(response, progress);
                return response;
            }
        }
        private static void Failed(JObject response, Progress progress)
        {
            response["cleanup_complete"] = false;
            response["mutation_state"] = progress.Entered ? "unknown" : "not_started";
            response["requires_reconciliation"] = progress.Entered;
            response["deleted_object_count"] = progress.Entered ? JValue.CreateNull() : new JValue(0);
            response["deleted_layer_count"] = progress.Entered ? JValue.CreateNull() : new JValue(0);
            response["attempted_object_count"] = progress.Objects;
            response["attempted_layer_count"] = progress.Layers;
        }
        private static void RequireDocument(RhinoDoc doc, string expected)
        {
            if (doc == null || String.IsNullOrWhiteSpace(doc.Path) || String.IsNullOrWhiteSpace(expected) ||
                !Path.IsPathRooted(expected) || !String.Equals(Path.GetFullPath(doc.Path), Path.GetFullPath(expected), StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("Step cleanup requires the bound saved document.");
            if (doc.IsReadOnly || RhinoDoc.ActiveDoc == null || RhinoDoc.ActiveDoc.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                throw new ArgumentException("The bound document must be writable and active.");
        }
        private static ObjectEnumeratorSettings ObjectSettings(int? layerIndex = null, bool idefObjects = false)
        {
            var settings = new ObjectEnumeratorSettings {
                NormalObjects = true, HiddenObjects = true, LockedObjects = true, ReferenceObjects = true,
                ActiveObjects = true, IdefObjects = idefObjects, DeletedObjects = false, IncludeLights = true,
                IncludeGrips = true, IncludePhantoms = true
            };
            if (layerIndex.HasValue) settings.LayerIndexFilter = layerIndex.Value;
            return settings;
        }
        // IdefObjects=true selects definition geometry; it does not include active objects.
        // Keep both passes so ordinary/locked objects are observed and definitions remain protected.
        private static RhinoObject[] Objects(RhinoDoc doc, int? layerIndex = null) =>
            doc.Objects.GetObjectList(ObjectSettings(layerIndex))
            .Concat(doc.Objects.GetObjectList(ObjectSettings(layerIndex, idefObjects: true)))
            .Where(o => o != null && !o.IsDeleted).GroupBy(o => o.Id).Select(g => g.First()).ToArray();
        private static object UserText(NameValueCollection text) => text?.AllKeys.OrderBy(k => k, StringComparer.Ordinal)
            .Select(key => new[] { key, text[key] }).ToArray();
        private static string ObjectStamp(RhinoObject obj) => JsonConvert.SerializeObject(new object[] {
            obj.Id, obj.Geometry?.DataCRC(0), obj.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions()),
            obj.IsLocked, obj.IsReference, obj.IsInstanceDefinitionGeometry, obj is GripObject, UserText(obj.Geometry?.GetUserStrings())
        });
        private static string LayerStamp(Layer layer) => JsonConvert.SerializeObject(new object[] {
            layer.Id, layer.Index, layer.ParentLayerId, layer.FullPath, layer.DataCRC(0), layer.IsCurrent,
            layer.IsLocked, layer.IsReference, layer.IsReferenceParentLayer, UserText(layer.GetUserStrings())
        });
        private static bool Protected(Func<string, string> read, NameValueCollection strings) =>
            ProtectedKeys.Any(key => !String.IsNullOrEmpty(read(key))) ||
            strings?.AllKeys.Any(key => key != null && key.StartsWith("ps:clip:", StringComparison.Ordinal)) == true;
        private static void RequireNoRegisteredGroup(RhinoDoc doc, RhinoObject obj, JObject records)
        {
            foreach (var record in records.Properties().Select(p => p.Value as JObject))
            {
                if (record == null || (string)record["registration_status"] == "unregistered") continue;
                var group = doc.Groups.FindId(Guid.Parse((string)record["rhino_group_id"]));
                if (group != null && !group.IsDeleted && obj.Attributes.IsInGroup(group.Index))
                    throw new ArgumentException("A registered Holon group protects a temp member from automatic cleanup.");
            }
        }
        private static bool RegistryProtects(RhinoDoc doc, HashSet<Guid> candidates)
        {
            if (candidates.Count == 0) return false;
            int index = doc.Layers.FindByFullPath("Drawing", -1);
            if (index < 0) return false;
            var layer = doc.Layers[index];
            if (layer == null || layer.IsDeleted || layer.ParentLayerId != Guid.Empty) return false;
            bool protects = false;
            foreach (string key in layer.GetUserStrings()?.AllKeys ?? Array.Empty<string>())
            {
                if (key == null || !key.StartsWith("ps:clip:", StringComparison.Ordinal) ||
                    !Guid.TryParse(key.Substring("ps:clip:".Length), out var source) || source == Guid.Empty) continue;
                string text = layer.GetUserString(key);
                if (String.IsNullOrEmpty(text)) continue;
                try
                {
                    using (var data = System.Text.Json.JsonDocument.Parse(text))
                    {
                        if (data.RootElement.ValueKind != System.Text.Json.JsonValueKind.Array)
                            throw new ArgumentException("The Drawing update registry cannot be read safely.");
                        foreach (var value in data.RootElement.EnumerateArray())
                        {
                            if (value.ValueKind != System.Text.Json.JsonValueKind.String || !Guid.TryParse(value.GetString(), out var id))
                                throw new ArgumentException("The Drawing update registry cannot be read safely.");
                            protects |= candidates.Contains(id);
                        }
                    }
                }
                catch (System.Text.Json.JsonException) { throw new ArgumentException("The Drawing update registry cannot be read safely."); }
            }
            return protects;
        }
        private static Snapshot Observe(RhinoDoc doc, bool captureOutside)
        {
            var snapshot = new Snapshot { DocumentSerial = doc.RuntimeSerialNumber, ModelPath = Path.GetFullPath(doc.Path) };
            var allLayers = doc.Layers.Where(l => !l.IsDeleted).ToArray();
            var roots = allLayers.Where(l => l.ParentLayerId == Guid.Empty && String.Equals(l.FullPath, "temp", StringComparison.OrdinalIgnoreCase)).ToArray();
            if (roots.Length > 1) throw new ArgumentException("The top-level temp layer is ambiguous.");
            if (roots.Length == 0) return snapshot;
            var ids = new HashSet<Guid>(roots.Select(l => l.Id));
            bool changed;
            do {
                changed = false;
                foreach (var layer in allLayers) if (ids.Contains(layer.ParentLayerId) && ids.Add(layer.Id)) changed = true;
            } while (changed);
            foreach (var layer in allLayers.Where(l => ids.Contains(l.Id)).OrderBy(l => l.FullPath, StringComparer.Ordinal))
            {
                var seen = new HashSet<Guid>(); var ancestor = layer;
                while (ancestor != null)
                {
                    if (!seen.Add(ancestor.Id)) throw new ArgumentException("Invalid temp layer ancestry.");
                    if (ancestor.IsLocked || ancestor.IsReference || ancestor.IsReferenceParentLayer)
                        throw new ArgumentException("A temp layer or ancestor is locked or referenced.");
                    ancestor = ancestor.ParentLayerId == Guid.Empty ? null : allLayers.FirstOrDefault(l => l.Id == ancestor.ParentLayerId);
                }
                if (layer.IsCurrent || Protected(layer.GetUserString, layer.GetUserStrings()))
                    throw new ArgumentException("A current or protected temp layer prevents automatic cleanup.");
                snapshot.Layers.Add(layer.Id, new LayerState { Index = layer.Index, Depth = layer.FullPath.Count(c => c == ':'), Stamp = LayerStamp(layer) });
            }
            var allObjects = Objects(doc);
            var indices = new HashSet<int>(snapshot.Layers.Values.Select(l => l.Index));
            JObject semanticRecords = null;
            foreach (var obj in allObjects.Where(o => indices.Contains(o.Attributes.LayerIndex)).OrderBy(o => o.Id))
            {
                if (obj.IsLocked || obj.IsReference || obj.IsInstanceDefinitionGeometry || obj is GripObject || obj.Attributes.Space != ActiveSpace.ModelSpace ||
                    Protected(obj.Attributes.GetUserString, obj.Attributes.GetUserStrings()) ||
                    obj.Geometry != null && Protected(obj.Geometry.GetUserString, obj.Geometry.GetUserStrings()))
                    throw new ArgumentException("A locked, referenced, definition, page-space, grip or protected temp object prevents automatic cleanup.");
                RequireNoRegisteredGroup(doc, obj, semanticRecords ?? (semanticRecords = ComponentSemanticRegistry.Records(doc)));
                snapshot.Objects.Add(obj.Id, ObjectStamp(obj));
            }
            var objectIds = new HashSet<Guid>(snapshot.Objects.Keys);
            if (RegistryProtects(doc, objectIds)) throw new ArgumentException("The Drawing registry protects a temp output.");
            foreach (var layer in allLayers)
                foreach (string key in layer.GetUserStrings()?.AllKeys ?? Array.Empty<string>())
                    if (key != null && key.StartsWith("ps:clip:", StringComparison.Ordinal) &&
                        Guid.TryParse(key.Substring("ps:clip:".Length), out var source) && objectIds.Contains(source))
                        throw new ArgumentException("An existing PlanSection update registry protects a temp source.");
            var sourceIds = new HashSet<string>(objectIds.Select(id => id.ToString()), StringComparer.Ordinal);
            if (allObjects.Any(o => !objectIds.Contains(o.Id) && !o.IsReference && !o.IsInstanceDefinitionGeometry &&
                o.Attributes.GetUserString("ps:generator") == "PlanSection/2" && sourceIds.Contains(o.Attributes.GetUserString("ps:clip") ?? "")))
                throw new ArgumentException("An existing legacy PlanSection output protects a temp source.");
            if (captureOutside)
            {
                snapshot.OutsideObjects = allObjects.Where(o => !objectIds.Contains(o.Id)).ToDictionary(o => o.Id, ObjectStamp);
                snapshot.OutsideLayers = allLayers.Where(l => !ids.Contains(l.Id)).ToDictionary(l => l.Id, LayerStamp);
            }
            return snapshot;
        }
        private static Layer RequireLayer(RhinoDoc doc, Guid id, LayerState state)
        {
            var layer = state.Index >= 0 && state.Index < doc.Layers.Count ? doc.Layers[state.Index] : null;
            if (layer == null || layer.IsDeleted || layer.Id != id || layer.Index != state.Index || LayerStamp(layer) != state.Stamp)
                throw new InvalidOperationException("A temp layer changed during cleanup; no further candidate was deleted.");
            return layer;
        }
        private static void RequireNoUpdateReference(RhinoDoc doc, Guid source, HashSet<Guid> candidateIds)
        {
            string sourceId = source.ToString();
            if (doc.Layers.Any(l => !l.IsDeleted && l.GetUserString("ps:clip:" + sourceId) != null) || RegistryProtects(doc, new HashSet<Guid> { source }))
                throw new InvalidOperationException("A live Drawing update relation protects this temp item; it was not deleted.");
            var matches = doc.Objects.FindByUserString("ps:clip", sourceId, true, false, true, ObjectSettings());
            if (matches != null && matches.Any(o => o != null && !o.IsDeleted && !o.IsReference && !o.IsInstanceDefinitionGeometry &&
                !candidateIds.Contains(o.Id) && o.Attributes.GetUserString("ps:generator") == "PlanSection/2" && o.Attributes.GetUserString("ps:clip") == sourceId))
                throw new InvalidOperationException("A live legacy PlanSection output protects this temp source; it was not deleted.");
        }
        private static object Apply(RhinoDoc doc, Snapshot snapshot, Progress progress)
        {
            RequireDocument(doc, snapshot.ModelPath);
            var current = Observe(doc, captureOutside: false);
            if (current.DocumentSerial != snapshot.DocumentSerial || current.Objects.Count != snapshot.Objects.Count || current.Layers.Count != snapshot.Layers.Count ||
                current.Objects.Any(p => !snapshot.Objects.TryGetValue(p.Key, out var stamp) || stamp != p.Value) ||
                current.Layers.Any(p => !snapshot.Layers.TryGetValue(p.Key, out var state) || state.Stamp != p.Value.Stamp))
                throw new InvalidOperationException("The temp hierarchy changed while entering the cleanup Undo record.");
            var objectIds = new HashSet<Guid>(snapshot.Objects.Keys);
            foreach (var candidate in snapshot.Objects)
            {
                RequireDocument(doc, snapshot.ModelPath);
                foreach (var layer in snapshot.Layers) RequireLayer(doc, layer.Key, layer.Value);
                RequireNoUpdateReference(doc, candidate.Key, objectIds);
                var live = doc.Objects.FindId(candidate.Key);
                if (live == null || live.IsDeleted)
                    throw new InvalidOperationException("A temp object is no longer available; it was not deleted.");
                // Registration Change/Restore replaces the records object. Read it again for each Delete.
                RequireNoRegisteredGroup(doc, live, ComponentSemanticRegistry.Records(doc));
                if (ObjectStamp(live) != candidate.Value)
                    throw new InvalidOperationException("A temp object moved or changed during cleanup; it was not deleted.");
                if (!doc.Objects.Delete(candidate.Key, true)) throw new InvalidOperationException("Rhino did not delete a temp object.");
                progress.Objects++;
            }
            foreach (var candidate in snapshot.Layers.OrderByDescending(p => p.Value.Depth))
            {
                RequireDocument(doc, snapshot.ModelPath);
                var layer = RequireLayer(doc, candidate.Key, candidate.Value);
                if (Objects(doc, layer.Index).Length != 0 ||
                    doc.Layers.Any(l => !l.IsDeleted && l.ParentLayerId == layer.Id))
                    throw new InvalidOperationException("A temp layer is no longer empty; no cascade deletion was attempted.");
                if (!doc.Layers.Delete(layer.Index, true)) throw new InvalidOperationException("Rhino did not delete an empty temp layer.");
                progress.Layers++;
            }
            var remaining = Objects(doc);
            if (remaining.Length != snapshot.OutsideObjects.Count || remaining.Any(o => !snapshot.OutsideObjects.TryGetValue(o.Id, out var stamp) || stamp != ObjectStamp(o)) ||
                doc.Layers.Count(l => !l.IsDeleted) != snapshot.OutsideLayers.Count ||
                doc.Layers.Any(l => !l.IsDeleted && (!snapshot.OutsideLayers.TryGetValue(l.Id, out var stamp) || stamp != LayerStamp(l))) ||
                progress.Objects != snapshot.Objects.Count || progress.Layers != snapshot.Layers.Count)
                throw new InvalidOperationException("Cleanup did not remove the complete temp hierarchy while preserving outside items.");
            return Completed(doc, progress);
        }
        private static Dictionary<string, object> Completed(RhinoDoc doc, Progress progress) => new Dictionary<string, object> {
            ["cleanup_complete"] = true, ["document_serial"] = doc.RuntimeSerialNumber,
            ["deleted_object_count"] = progress.Objects, ["deleted_layer_count"] = progress.Layers,
            ["mutation_state"] = progress.Layers == 0 ? "not_needed" : "applied"
        };
    }
}
