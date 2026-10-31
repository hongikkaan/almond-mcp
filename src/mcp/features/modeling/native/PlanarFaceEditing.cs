using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    /// <summary>Bounded planar-face extension using ScriptExecutor's existing Undo scope.</summary>
    public static class PlanarFaceEditing
    {
        private static readonly Type SharedDictionaryType = typeof(Rhino.DocObjects.Custom.UserDictionary).Assembly
            .GetType("Rhino.DocObjects.Custom.SharedUserDictionary", throwOnError: true);
        // ON_UserStringList class ID from OpenNURBS opennurbs_userdata.cpp.
        private static readonly Guid UserStringListId = new Guid("CE28DE29-F4C5-4FAA-A50A-C3A6849B6329");

        private sealed class PreparedEdit : IDisposable
        {
            internal Guid Id;
            internal uint BeforeCrc;
            internal Brep Replacement;
            internal Dictionary<string, object> Result;
            public void Dispose() => Replacement?.Dispose();
        }

        private static void ValidateTarget(RhinoDoc doc, JObject request)
        {
            string expected = (string)request["expected_model_path"];
            if (doc == null || String.IsNullOrWhiteSpace(doc.Path) || String.IsNullOrWhiteSpace(expected) ||
                !Path.IsPathRooted(expected) || !String.Equals(Path.GetFullPath(doc.Path),
                    Path.GetFullPath(expected), StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("The face-edit target differs from the bound model.");
            if (doc.IsReadOnly) throw new ArgumentException("The bound document is read-only.");
            var editor = EditingContext.Observe(doc);
            if (editor["stable"]?.Type != JTokenType.Boolean || !(bool)editor["stable"] || (string)editor["mode"] != "model")
                throw new ArgumentException("Finish group/block editing before editing this model-space face.");
        }

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                // Observe before entering our Undo scope; observation rejects any active record.
                // Handle and ExecuteAction run synchronously on the same Rhino UI thread.
                ValidateTarget(doc, request);
                started = true;
                return JObject.FromObject(new ScriptExecutor().ExecuteAction(doc, () => ApplyCore(doc, request)));
            }
            catch (Exception error)
            {
                return new JObject { ["status"] = "error", ["error_code"] = "face_edit_error", ["message"] = error.Message,
                    ["mutation_state"] = started ? "unknown" : "not_started", ["requires_reconciliation"] = started };
            }
        }

        private static Dictionary<string, object> ApplyCore(RhinoDoc doc, JObject request)
        {
            using (var prepared = Prepare(doc, request))
            {
                if (!doc.Objects.Replace(prepared.Id, prepared.Replacement))
                    throw new InvalidOperationException("Rhino did not replace the target Brep.");
                return prepared.Result;
            }
        }

        public static JObject HandleBatch(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                ValidateTarget(doc, request);
                if (!(request["edits"] is JArray edits) || edits.Count < 1 || edits.Count > 32 || edits.Any(t => !(t is JObject)))
                    throw new ArgumentException("edits must contain 1..32 face-edit objects.");
                var ids = new HashSet<Guid>();
                foreach (JObject item in edits)
                {
                    if (!Guid.TryParse((string)item["object_id"], out var id) || id == Guid.Empty || !ids.Add(id))
                        throw new ArgumentException("Each batch item must target a distinct nonempty object GUID; observe changed faces before another edit of the same object.");
                    if (item.Properties().Any(p => p.Name != "object_id" && p.Name != "face_index" &&
                        p.Name != "expected_geometry_crc" && p.Name != "translation"))
                        throw new ArgumentException("Batch items accept object_id, face_index, expected_geometry_crc and translation only.");
                }
                started = true;
                var response = JObject.FromObject(new ScriptExecutor().ExecuteAction(doc, () => ApplyBatch(doc, edits)));
                if ((string)response["result"]?["status"] == "error")
                {
                    response["status"] = "error";
                    foreach (string key in new[] { "error_code", "message", "mutation_state", "requires_reconciliation" })
                        response[key] = response["result"][key]?.DeepClone();
                }
                else if ((string)response["status"] != "success" || response["result_error"]?.Type == JTokenType.String)
                {
                    response["mutation_state"] = "unknown";
                    response["requires_reconciliation"] = true;
                }
                return response;
            }
            catch (Exception error)
            {
                return new JObject { ["status"] = "error", ["error_code"] = "face_edit_batch_error", ["message"] = error.Message,
                    ["mutation_state"] = started ? "unknown" : "not_started", ["requires_reconciliation"] = started };
            }
        }

        private static Dictionary<string, object> ApplyBatch(RhinoDoc doc, JArray edits)
        {
            var prepared = new List<PreparedEdit>();
            var items = edits.Select(item => new Dictionary<string, object> {
                ["object_id"] = (string)item["object_id"], ["status"] = "not_attempted", ["edited"] = false
            }).ToArray();
            var result = new Dictionary<string, object> {
                ["status"] = "success", ["complete"] = false, ["requested_count"] = edits.Count,
                ["applied_count"] = 0, ["mutation_state"] = "not_started", ["items"] = items
            };
            Dictionary<string, object> Fail(string code, string message, bool uncertain = false)
            {
                int count = items.Count(item => item["edited"] is bool value && value);
                result["status"] = "error"; result["error_code"] = code; result["message"] = message;
                result["applied_count"] = count;
                result["mutation_state"] = uncertain ? "unknown" : count == edits.Count ? "applied" : count > 0 ? "partial" : "not_started";
                result["requires_reconciliation"] = uncertain;
                return result;
            }
            try
            {
                for (int i = 0; i < edits.Count; i++)
                {
                    try { prepared.Add(Prepare(doc, (JObject)edits[i])); }
                    catch (Exception error)
                    {
                        items[i]["status"] = "rejected"; items[i]["stage"] = "prepare"; items[i]["message"] = error.Message;
                        return Fail("face_edit_batch_preparation_failed", "No objects were replaced: " + error.Message);
                    }
                }
                // All detached results are ready before the first replacement. The single Undo
                // record is user recovery, not a claim of automatic rollback on later failure.
                for (int i = 0; i < prepared.Count; i++)
                {
                    var edit = prepared[i];
                    var current = doc.Objects.FindId(edit.Id);
                    if (current == null || current.Geometry.DataCRC(0) != edit.BeforeCrc)
                    {
                        items[i]["status"] = "rejected"; items[i]["stage"] = "recheck";
                        return Fail("face_edit_batch_stale", "A target changed before batch replacement; no objects were replaced.");
                    }
                }
                for (int i = 0; i < prepared.Count; i++)
                {
                    var edit = prepared[i];
                    try
                    {
                        var current = doc.Objects.FindId(edit.Id);
                        if (current == null || current.Geometry.DataCRC(0) != edit.BeforeCrc)
                            throw new InvalidOperationException("The target changed during batch replacement.");
                        if (!doc.Objects.Replace(edit.Id, edit.Replacement))
                            throw new InvalidOperationException("Rhino did not replace the target Brep.");
                        items[i] = edit.Result;
                        items[i]["status"] = "applied";
                    }
                    catch (Exception error)
                    {
                        bool unknown = true;
                        try
                        {
                            var actual = doc.Objects.FindId(edit.Id);
                            uint? crc = actual?.Geometry.DataCRC(0);
                            if (crc == edit.BeforeCrc) { items[i]["status"] = "failed"; unknown = false; }
                            else if (crc == (uint)edit.Result["geometry_crc"])
                            {
                                items[i] = edit.Result; items[i]["status"] = "applied"; unknown = false;
                            }
                            else { items[i]["status"] = "unknown"; items[i]["edited"] = null; }
                        }
                        catch { items[i]["status"] = "unknown"; items[i]["edited"] = null; }
                        items[i]["stage"] = "replace"; items[i]["message"] = error.Message;
                        return Fail("face_edit_batch_replace_failed", "Batch stopped; inspect item outcomes before any further edit. " + error.Message, unknown);
                    }
                }
                result["complete"] = true; result["applied_count"] = prepared.Count; result["mutation_state"] = "applied";
                return result;
            }
            finally { foreach (var item in prepared) item.Dispose(); }
        }

        private static PreparedEdit Prepare(RhinoDoc doc, JObject request)
        {
            Guid id;
            if (!Guid.TryParse((string)request["object_id"], out id) || id == Guid.Empty)
                throw new ArgumentException("A current model-space object GUID is required.");
            var faceValue = request["face_index"];
            var crcValue = request["expected_geometry_crc"];
            if (faceValue?.Type != JTokenType.Integer || (long)faceValue < 0 || (long)faceValue > Int32.MaxValue ||
                crcValue?.Type != JTokenType.Integer || (long)crcValue < 0 || (long)crcValue > UInt32.MaxValue)
                throw new ArgumentException("A nonnegative face index and uint32 geometry CRC are required.");
            int faceIndex = (int)faceValue;
            uint expectedCrc = (uint)crcValue;
            var values = request["translation"] as JArray;
            if (values == null || values.Count != 3)
                throw new ArgumentException("translation needs three finite document-unit coordinates.");
            foreach (var value in values)
                if ((value.Type != JTokenType.Integer && value.Type != JTokenType.Float) || !Finite((double)value))
                    throw new ArgumentException("translation needs three finite document-unit coordinates.");
            var translation = new Vector3d((double)values[0], (double)values[1], (double)values[2]);
            double tolerance = doc.ModelAbsoluteTolerance;
            if (!Finite(tolerance) || tolerance <= 0 || !translation.IsValid ||
                !Finite(translation.Length) || translation.Length <= tolerance)
                throw new ArgumentException("Face translation must exceed the document's positive absolute tolerance.");

            var obj = doc.Objects.FindId(id);
            if (obj == null || obj.IsDeleted || obj.IsReference || obj.IsInstanceDefinitionGeometry || obj.IsLocked ||
                obj.Attributes.Space != ActiveSpace.ModelSpace)
                throw new ArgumentException("The target must be an editable top-level model-space Brep.");
            RequireUnlockedLayer(doc, obj.Attributes.LayerIndex);
            var original = obj.Geometry as Brep;
            if (original == null)
                throw new ArgumentException("Planar face editing accepts a Brep, not a converted extrusion or block definition.");
            uint beforeCrc = original.DataCRC(0);
            if (beforeCrc != expectedCrc)
                throw new ArgumentException("Stale face reference: the object's geometry CRC changed. Observe its faces again.");
            // Count includes native user data that .NET enumeration may expose only as null.
            // Reject unhandled payloads before duplication could silently discard them.
            var dictionary = (original.UserData.Find(SharedDictionaryType) as
                Rhino.DocObjects.Custom.UserDictionary)?.Dictionary;
            int supportedData = (dictionary == null ? 0 : 1) + (original.UserData.Contains(UserStringListId) ? 1 : 0);
            if (original.UserData.Count != supportedData)
                throw new ArgumentException("This face edit cannot preserve custom geometry user data; the original was not edited.");
            RequireSolid(original, "The original");
            if (faceIndex >= original.Faces.Count)
                throw new ArgumentException("face_index is outside the current Brep's face collection.");
            Plane plane;
            if (!original.Faces[faceIndex].TryGetPlane(out plane, tolerance))
                throw new ArgumentException("The selected face must be planar.");
            foreach (int adjacent in original.Faces[faceIndex].AdjacentFaces())
                if (!original.Faces[adjacent].IsPlanar(tolerance))
                    throw new ArgumentException("Every face adjacent to the selected face must be planar.");
            if (Math.Abs(Vector3d.Multiply(plane.Normal, translation)) <= tolerance)
                throw new ArgumentException("Translation must move the selected plane by more than the document tolerance.");
            double volumeBefore = Volume(original);
            using (var working = original.DuplicateBrep())
            {
                if (working == null) throw new InvalidOperationException("Could not duplicate the target Brep.");
                var replacement = working.PushPullExtend(faceIndex, Transform.Translation(translation), tolerance);
                try
                {
                    if (replacement == null)
                        throw new InvalidOperationException("Rhino could not extend this planar face. The original is unchanged.");
                    RequireSolid(replacement, "The edited");
                    if (replacement.SolidOrientation != original.SolidOrientation)
                        throw new InvalidOperationException("The face edit changed the solid orientation.");
                    double volumeAfter = Volume(replacement);
                    if (GeometryBase.GeometryEquals(original, replacement))
                        throw new InvalidOperationException("The face edit produced no geometry change.");
                    // CommonObject.UserDictionary attaches a dictionary when absent. Read only the
                    // existing source user data; attaching to the detached replacement is safe.
                    if (dictionary != null)
                        replacement.UserDictionary.ReplaceContentsWith(dictionary.Clone());
                    var userStrings = original.GetUserStrings();
                    if (userStrings != null)
                        foreach (string key in userStrings.AllKeys)
                            if (!replacement.SetUserString(key, userStrings[key]))
                                throw new InvalidOperationException("Could not preserve the geometry user strings.");
                    uint afterCrc = replacement.DataCRC(0);
                    if (afterCrc == beforeCrc)
                        throw new InvalidOperationException("The face edit produced no distinguishable geometry change.");
                    var current = doc.Objects.FindId(id);
                    if (current == null || current.Geometry.DataCRC(0) != expectedCrc)
                        throw new InvalidOperationException("The target changed during face-edit preparation.");
                    // Replace retains the object GUID and all attributes, including group membership.
                    // Prepare all result data before the only document mutation.
                    // ScriptExecutor's bounded projector accepts CLR data containers, not JTokens.
                    var result = new Dictionary<string, object>
                    {
                        ["edited"] = true, ["object_id"] = id.ToString("D"),
                        ["previous_geometry_crc"] = beforeCrc, ["geometry_crc"] = afterCrc,
                        ["face_index"] = faceIndex, ["translation"] = new[] { translation.X, translation.Y, translation.Z },
                        ["volume_before"] = volumeBefore, ["volume_after"] = volumeAfter,
                        ["face_count_before"] = original.Faces.Count, ["face_count_after"] = replacement.Faces.Count,
                        ["units"] = doc.ModelUnitSystem.ToString(), ["tolerance"] = tolerance,
                        ["valid"] = true, ["closed"] = true
                    };
                    return new PreparedEdit { Id = id, BeforeCrc = beforeCrc, Replacement = replacement, Result = result };
                }
                catch { replacement?.Dispose(); throw; }
            }
        }

        private static bool Finite(double value) => !Double.IsNaN(value) && !Double.IsInfinity(value);

        private static void RequireUnlockedLayer(RhinoDoc doc, int layerIndex)
        {
            var seen = new HashSet<Guid>();
            var layer = doc.Layers.FindIndex(layerIndex);
            while (layer != null)
            {
                if (layer.IsDeleted || layer.IsLocked || !seen.Add(layer.Id))
                    throw new ArgumentException("The target layer and every parent layer must be unlocked and valid.");
                if (layer.ParentLayerId == Guid.Empty) return;
                layer = doc.Layers.FindId(layer.ParentLayerId);
            }
            throw new ArgumentException("The target's layer hierarchy could not be verified.");
        }

        private static void RequireSolid(Brep brep, string label)
        {
            if (!brep.IsValid || !brep.IsSolid || !brep.IsManifold)
                throw new ArgumentException(label + " Brep must be valid, closed and manifold.");
        }

        private static double Volume(Brep brep)
        {
            using (var mass = VolumeMassProperties.Compute(brep))
            {
                if (mass == null || !Finite(mass.Volume) || Math.Abs(mass.Volume) <= 0)
                    throw new InvalidOperationException("Could not verify a finite, positive solid volume.");
                return Math.Abs(mass.Volume);
            }
        }
    }
}
