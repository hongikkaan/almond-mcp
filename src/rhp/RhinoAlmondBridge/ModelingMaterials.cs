using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Render;

namespace RhinoAlmondBridge
{
    // Callers own their Undo record. Loading the catalog never creates document state.
    public static class ModelingMaterials
    {
        private sealed class ManifestCache
        {
            internal DateTime Modified;
            internal long Length;
            internal JObject Value;
        }

        private static readonly Dictionary<string, ManifestCache> Manifests =
            new Dictionary<string, ManifestCache>(StringComparer.OrdinalIgnoreCase);

        private static string LibraryRoot(string variable, string folder)
        {
            string configured = System.Environment.GetEnvironmentVariable(variable);
            return Path.GetFullPath(String.IsNullOrEmpty(configured)
                ? Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData), "Almond", folder)
                : configured);
        }

        public static string MaterialLibraryRoot => LibraryRoot("RHINO_MCP_MATERIAL_DIR", "Materialfiles");

        private static JObject Manifest(string root)
        {
            string path = Path.Combine(root, "manifest.json");
            var file = new FileInfo(path);
            if (!file.Exists) throw new FileNotFoundException("Modeling library manifest was not found.", path);
            lock (Manifests)
            {
                if (Manifests.TryGetValue(path, out var cached) && cached.Modified == file.LastWriteTimeUtc && cached.Length == file.Length)
                    return cached.Value;
                var value = JObject.Parse(File.ReadAllText(path));
                Manifests[path] = new ManifestCache { Modified = file.LastWriteTimeUtc, Length = file.Length, Value = value };
                return value;
            }
        }

        private static JObject FindMaterial(string id, bool required)
        {
            string root = MaterialLibraryRoot;
            if (!required && !File.Exists(Path.Combine(root, "manifest.json"))) return null;
            var rows = Manifest(root)["materials"] as JArray;
            if (rows == null) throw new InvalidDataException("Material manifest must contain a materials array.");
            var matches = rows.OfType<JObject>().Where(m => (string)m["material_id"] == id).ToArray();
            if (matches.Length > 1) throw new InvalidDataException("Duplicate material_id: " + id);
            if (matches.Length == 0)
            {
                if (required) throw new ArgumentException("Unknown material_id: " + id);
                return null;
            }
            var material = matches[0];
            foreach (string field in new[] { "material_id", "name", "category", "ue_material_slot" })
                if (material[field]?.Type != JTokenType.String || String.IsNullOrWhiteSpace((string)material[field]))
                    throw new InvalidDataException("Invalid material " + field + ": " + id);
            var rgb = material["base_color"] as JArray;
            if (rgb == null || rgb.Count != 3 || rgb.Any(v => v.Type != JTokenType.Integer || (long)v < 0 || (long)v > 255))
                throw new InvalidDataException("Invalid material base_color: " + id);
            foreach (string field in new[] { "metallic", "roughness", "opacity" })
            {
                var token = material[field];
                if (token == null || (token.Type != JTokenType.Float && token.Type != JTokenType.Integer) ||
                    !Double.IsFinite((double)token) || (double)token < 0 || (double)token > 1)
                    throw new InvalidDataException("Invalid material " + field + ": " + id);
            }
            ModelingMetadata.MaterialLayerPath(material);
            return material;
        }

        private static Color ColorFor(JObject material)
        {
            var rgb = material["base_color"];
            return Color.FromArgb((int)rgb[0], (int)rgb[1], (int)rgb[2]);
        }

        public static bool TryLayerForMaterial(RhinoDoc doc, int materialIndex, out string layerPath)
        {
            layerPath = null;
            if (doc == null || materialIndex < 0 || materialIndex >= doc.Materials.Count) return false;
            var material = doc.Materials[materialIndex];
            if (material == null || material.IsDeleted) return false;
            string id = material.GetUserString(ModelingMetadata.Key("material_id"));
            string name = material.Name ?? "";
            if (String.IsNullOrWhiteSpace(id) && name.StartsWith("ALMOND::", StringComparison.Ordinal))
                id = name.Substring(8).Split(new[] { "::" }, StringSplitOptions.None)[0];
            if (!String.IsNullOrWhiteSpace(id))
            {
                var recipe = FindMaterial(id, false);
                if (recipe != null)
                {
                    layerPath = ModelingMetadata.MaterialLayerPath(recipe);
                    return true;
                }
            }
            string safeName = Regex.Replace(name, ModelingMetadata.Setting("document_material_name_pattern"), "_").Trim(' ', '_', '.');
            Guid identity = material.RenderMaterialInstanceId == Guid.Empty ? material.Id : material.RenderMaterialInstanceId;
            if (String.IsNullOrWhiteSpace(safeName) || identity == Guid.Empty) return false;
            string suffix = identity.ToString("N").Substring(0, ModelingMetadata.IntegerSetting("document_material_id_suffix_length"));
            layerPath = ModelingMetadata.Setting("document_material_layer_root") + "::" + safeName + "__" + suffix;
            ModelingMetadata.ValidateLayerPath(layerPath);
            return true;
        }

        public static bool TryResolveMaterialLayer(RhinoDoc doc, RhinoObject obj, out string layerPath)
        {
            layerPath = null;
            return obj != null && !obj.IsDeleted && !obj.IsReference && !obj.IsInstanceDefinitionGeometry &&
                obj.Attributes.MaterialSource == ObjectMaterialSource.MaterialFromObject &&
                TryLayerForMaterial(doc, obj.Attributes.MaterialIndex, out layerPath);
        }

        public static int EnsureLayer(RhinoDoc doc, string layerPath, Color color)
        {
            if (doc == null) throw new ArgumentNullException(nameof(doc));
            ModelingMetadata.ValidateLayerPath(layerPath);
            string[] parts = layerPath.Split(new[] { "::" }, StringSplitOptions.None);
            Guid parentId = Guid.Empty;
            int index = -1;
            for (int i = 0; i < parts.Length; i++)
            {
                var found = doc.Layers.FirstOrDefault(layer => layer != null && !layer.IsDeleted && layer.ParentLayerId == parentId &&
                    String.Equals(layer.Name, parts[i], StringComparison.OrdinalIgnoreCase));
                index = found?.Index ?? doc.Layers.Add(new Layer {
                    Name = parts[i], ParentLayerId = parentId, Color = i == parts.Length - 1 ? color : Color.Black
                });
                if (index < 0) throw new InvalidOperationException("Rhino failed to create material layer: " + layerPath);
                parentId = doc.Layers[index].Id;
            }
            return index;
        }

        public static bool RouteObject(RhinoDoc doc, RhinoObject obj)
        {
            if (!TryResolveMaterialLayer(doc, obj, out string path)) return false;
            var current = obj.Attributes.LayerIndex >= 0 && obj.Attributes.LayerIndex < doc.Layers.Count
                ? doc.Layers[obj.Attributes.LayerIndex] : null;
            if (current != null && String.Equals(current.FullPath, path, StringComparison.OrdinalIgnoreCase)) return false;
            int index = EnsureLayer(doc, path, doc.Materials[obj.Attributes.MaterialIndex].DiffuseColor);
            var attributes = obj.Attributes.Duplicate();
            attributes.LayerIndex = index;
            if (!doc.Objects.ModifyAttributes(obj.Id, attributes, true))
                throw new InvalidOperationException("Rhino refused the material layer for object " + obj.Id);
            return true;
        }

        private static Guid CreateSharedRenderMaterial(RhinoDoc doc, Material material)
        {
            // Create records content Undo. RenderMaterials.Add alone does not;
            // the Rhino 8 ContentUndoHelper wrapper cannot accept a null parent.
            var render = RenderContent.Create(doc, ContentUuids.PhysicallyBasedMaterialType) as RenderMaterial;
            if (render == null)
                throw new InvalidOperationException("Rhino could not create the shared PBR material. The host must load its PBR content provider.");
            render.BeginChange(RenderContent.ChangeContexts.Program);
            try
            {
                var pbr = material.PhysicallyBased;
                if (!render.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.BaseColor, pbr.BaseColor) ||
                    !render.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.Metallic, pbr.Metallic) ||
                    !render.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.Roughness, pbr.Roughness) ||
                    !render.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.Opacity, pbr.Opacity))
                    throw new InvalidOperationException("Rhino refused the shared PBR material parameters.");
                render.Name = material.Name;
            }
            finally { render.EndChange(); }
            return render.Id;
        }

        private static int EnsureMaterial(RhinoDoc doc, JObject recipe)
        {
            string id = (string)recipe["material_id"], name = "ALMOND::" + id;
            var existing = doc.Materials.FirstOrDefault(m => m != null && !m.IsDeleted && m.Name == name);
            if (existing != null)
            {
                string existingId = existing.GetUserString(ModelingMetadata.Key("material_id"));
                if (!String.IsNullOrWhiteSpace(existingId) && existingId != id)
                    throw new ArgumentException("The named Rhino material has a conflicting material_id: " + name);
                return existing.Index;
            }
            var material = new Material { Name = name, DiffuseColor = ColorFor(recipe), Transparency = 1 - (double)recipe["opacity"] };
            material.ToPhysicallyBased();
            material.PhysicallyBased.BaseColor = new Rhino.Display.Color4f(material.DiffuseColor);
            material.PhysicallyBased.Metallic = (double)recipe["metallic"];
            material.PhysicallyBased.Roughness = (double)recipe["roughness"];
            material.PhysicallyBased.Opacity = (double)recipe["opacity"];
            material.SetUserString(ModelingMetadata.Key("material_id"), id);
            material.RenderMaterialInstanceId = CreateSharedRenderMaterial(doc, material);
            int index = doc.Materials.Add(material);
            if (index < 0) throw new InvalidOperationException("Rhino failed to create material: " + id);
            return index;
        }

        private static void ValidateMetadata(IDictionary<string, string> metadata)
        {
            if (metadata == null) return;
            foreach (var pair in metadata)
                if (!ModelingMetadata.IsMaterialAssignmentKey(pair.Key) || pair.Value == null)
                    throw new ArgumentException("Material metadata accepts only floor, construction_detail, construction_reference and structural_role with non-null values: " + pair.Key);
            if (metadata.TryGetValue(ModelingMetadata.Key("construction_reference"), out string reference))
            {
                var value = JObject.Parse(reference);
                if (value.Properties().Any(p => p.Name != "kind" && p.Name != "id") ||
                    (string)value["kind"] != "construction_system" || value["id"]?.Type != JTokenType.String)
                    throw new ArgumentException("construction_reference requires kind=construction_system and a known id.");
                var systems = Manifest(LibraryRoot("RHINO_MCP_CONSTRUCTION_DIR", "Constructionfiles"))["systems"] as JArray;
                if (systems == null || !systems.OfType<JObject>().Any(s => (string)s["system_id"] == (string)value["id"]))
                    throw new ArgumentException("Unknown construction reference id: " + (string)value["id"]);
            }
        }

        public static ObjectAttributes CreateAttributes(RhinoDoc doc, string materialId,
            IDictionary<string, string> metadata = null, ObjectAttributes source = null,
            bool applyRenderMaterial = true, bool attachMetadata = true)
        {
            if (doc == null) throw new ArgumentNullException(nameof(doc));
            ValidateMetadata(metadata);
            var recipe = FindMaterial(materialId, true);
            var attributes = source?.Duplicate() ?? new ObjectAttributes { LayerIndex = doc.Layers.CurrentLayerIndex };
            if (applyRenderMaterial)
            {
                attributes.MaterialIndex = EnsureMaterial(doc, recipe);
                attributes.MaterialSource = ObjectMaterialSource.MaterialFromObject;
                attributes.LayerIndex = EnsureLayer(doc, ModelingMetadata.MaterialLayerPath(recipe), ColorFor(recipe));
            }
            if (attachMetadata)
            {
                // PBR channels stay on the material; metadata-only calls do not claim a material change.
                if (applyRenderMaterial) attributes.SetUserString(ModelingMetadata.Key("material_id"), materialId);
                if (metadata != null)
                    foreach (var pair in metadata) attributes.SetUserString(pair.Key, pair.Value);
            }
            return attributes;
        }

        private static bool SameAssignment(RhinoDoc doc, ObjectAttributes before, ObjectAttributes after)
        {
            var beforeText = before.GetUserStrings();
            var afterText = after.GetUserStrings();
            bool sameMaterial = before.MaterialIndex == after.MaterialIndex;
            if (!sameMaterial && before.MaterialIndex >= 0 && before.MaterialIndex < doc.Materials.Count &&
                after.MaterialIndex >= 0 && after.MaterialIndex < doc.Materials.Count)
            {
                var previous = doc.Materials[before.MaterialIndex];
                var next = doc.Materials[after.MaterialIndex];
                // Rhino may keep one legacy material row per object while all
                // rows refer to the same reusable RenderMaterial.
                sameMaterial = previous != null && next != null && !previous.IsDeleted && !next.IsDeleted &&
                    previous.RenderMaterialInstanceId != Guid.Empty &&
                    previous.RenderMaterialInstanceId == next.RenderMaterialInstanceId &&
                    previous.GetUserString(ModelingMetadata.Key("material_id")) == next.GetUserString(ModelingMetadata.Key("material_id"));
            }
            return before.LayerIndex == after.LayerIndex && sameMaterial &&
                before.MaterialSource == after.MaterialSource && (beforeText?.Count ?? 0) == (afterText?.Count ?? 0) &&
                (afterText == null || afterText.AllKeys.All(key => beforeText?[key] == afterText[key]));
        }

        public static object Apply(RhinoDoc doc, string materialId, IEnumerable<Guid> ids,
            IDictionary<string, string> metadata = null, bool applyRenderMaterial = true, bool attachMetadata = true)
        {
            if (doc == null) throw new ArgumentNullException(nameof(doc));
            var requested = ids?.Distinct().ToArray() ?? throw new ArgumentNullException(nameof(ids));
            if (requested.Length == 0) throw new ArgumentException("At least one object GUID is required.");
            ValidateMetadata(metadata);
            var recipe = FindMaterial(materialId, true);
            var objects = requested.Select(id => doc.Objects.FindId(id)).ToArray();
            if (objects.Any(o => o == null || o.IsDeleted || o.IsReference || o.IsInstanceDefinitionGeometry))
                throw new ArgumentException("Material targets must be existing editable document objects; refresh missing or referenced GUIDs.");
            var applied = new List<string>();
            var changed = new List<string>();
            foreach (var obj in objects)
            {
                if (!applyRenderMaterial && (!attachMetadata || metadata == null || metadata.Count == 0)) continue;
                var attributes = CreateAttributes(doc, materialId, metadata, obj.Attributes, applyRenderMaterial, attachMetadata);
                if (!SameAssignment(doc, obj.Attributes, attributes))
                {
                    if (!doc.Objects.ModifyAttributes(obj.Id, attributes, true))
                        throw new InvalidOperationException("Rhino refused material attributes for object " + obj.Id);
                    changed.Add(obj.Id.ToString());
                }
                applied.Add(obj.Id.ToString());
            }
            return new {
                material_id = materialId, applied_guids = applied, changed_guids = changed,
                layer_path = applyRenderMaterial ? ModelingMetadata.MaterialLayerPath(recipe) : null,
                metadata_attached = attachMetadata && (applyRenderMaterial || (metadata != null && metadata.Count != 0)),
                material_metadata_attached = applyRenderMaterial && attachMetadata,
                render_material_applied = applyRenderMaterial
            };
        }
    }
}
