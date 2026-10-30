using System;
using System.Collections.Generic;
using System.IO;
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

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                string expected = (string)request["expected_model_path"];
                if (doc == null || String.IsNullOrWhiteSpace(doc.Path) || String.IsNullOrWhiteSpace(expected) ||
                    !Path.IsPathRooted(expected) || !String.Equals(Path.GetFullPath(doc.Path),
                        Path.GetFullPath(expected), StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException("The face-edit target differs from the bound model.");
                if (doc.IsReadOnly)
                    throw new ArgumentException("The bound document is read-only.");
                // Observe before entering our Undo scope; observation rejects any active record.
                // Handle and ExecuteAction run synchronously on the same Rhino UI thread.
                var editor = EditingContext.Observe(doc);
                if (editor["stable"]?.Type != JTokenType.Boolean || !(bool)editor["stable"] || (string)editor["mode"] != "model")
                    throw new ArgumentException("Finish group/block editing before editing this model-space face.");
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
                using (var replacement = working.PushPullExtend(faceIndex, Transform.Translation(translation), tolerance))
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
                    if (!doc.Objects.Replace(id, replacement))
                        throw new InvalidOperationException("Rhino did not replace the target Brep.");
                    return result;
                }
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
