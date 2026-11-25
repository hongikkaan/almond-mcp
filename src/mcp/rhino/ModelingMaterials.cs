using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Render;

namespace RhinoAlmondBridge
{
    // MCP-owned modeling operations, compiled into the Bridge for Rhino's UI thread.
    // Recipes/paths/metadata are resolved by MCP; no library IO or implicit routing.
    // The caller owns the Undo record.
    public static class ModelingMaterials
    {
        private const string MaterialIdKey = "material_id";

        private static Color ColorFor(JToken rgb) => Color.FromArgb((int)rgb[0], (int)rgb[1], (int)rgb[2]);

        private static RenderMaterial EnsureMaterial(RhinoDoc doc, JObject recipe, bool reuseLegacyMaterial = true)
        {
            string name = (string)recipe["name"], legacy = "ALMOND::" + (string)recipe["material_id"];
            foreach (var tableMaterial in doc.Materials.Where(m => !m.IsDeleted &&
                (m.Name == name || (reuseLegacyMaterial && m.Name == legacy))))
            {
                string existingId = tableMaterial.GetUserString(MaterialIdKey);
                if (!String.IsNullOrEmpty(existingId) && existingId != (string)recipe["material_id"])
                    throw new ArgumentException("The named Rhino material has a conflicting material_id: " + tableMaterial.Name);
            }
            var matches = doc.RenderMaterials.Where(m => m != null &&
                (m.Name == name || (reuseLegacyMaterial && m.Name == legacy))).ToArray();
            var existing = matches.FirstOrDefault(m => m.Name == name) ?? matches.FirstOrDefault();
            if (existing != null) return existing;
            var material = RenderContent.Create(doc, ContentUuids.PhysicallyBasedMaterialType) as RenderMaterial;
            if (material == null) throw new InvalidOperationException("Cannot create material: " + name);
            if (material.TypeId != ContentUuids.PhysicallyBasedMaterialType)
                material = Utilities.ChangeContentType(material, ContentUuids.PhysicallyBasedMaterialType, false) as RenderMaterial;
            if (material == null) throw new InvalidOperationException("Cannot convert material to PBR: " + name);
            material.BeginChange(RenderContent.ChangeContexts.Program);
            try
            {
                if (!material.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.BaseColor,
                        new Rhino.Display.Color4f(ColorFor(recipe["base_color"]))) ||
                    !material.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.Metallic, (double)recipe["metallic"]) ||
                    !material.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.Roughness, (double)recipe["roughness"]) ||
                    !material.SetParameter(Rhino.Render.ParameterNames.PhysicallyBased.Opacity, (double)recipe["opacity"]))
                    throw new InvalidOperationException("Cannot update PBR material: " + name);
                material.Name = name;
            }
            finally { material.EndChange(); }
            return material;
        }

        public static ObjectAttributes CreateAttributes(RhinoDoc doc, string recipeJson,
            IDictionary<string, string> metadata = null, ObjectAttributes source = null,
            bool applyRenderMaterial = true, bool attachMetadata = false, bool reuseLegacyMaterial = true)
        {
            if (doc == null) throw new ArgumentNullException(nameof(doc));
            ValidateMetadata(metadata);
            var recipe = JObject.Parse(recipeJson);
            var attributes = source?.Duplicate() ?? new ObjectAttributes { LayerIndex = doc.Layers.CurrentLayerIndex };
            if (applyRenderMaterial)
            {
                var render = EnsureMaterial(doc, recipe, reuseLegacyMaterial: reuseLegacyMaterial);
                var existing = doc.Materials.FirstOrDefault(m => !m.IsDeleted && m.RenderMaterialInstanceId == render.Id);
                int index = existing?.Index ?? -1;
                if (index < 0)
                {
                    using var material = render.ToMaterial(RenderTexture.TextureGeneration.Allow);
                    material.Name = render.Name;
                    material.RenderMaterialInstanceId = render.Id;
                    material.SetUserString(MaterialIdKey, (string)recipe["material_id"]);
                    index = doc.Materials.Add(material);
                }
                if (index < 0) throw new InvalidOperationException("Cannot assign material: " + render.Name);
                attributes.MaterialIndex = index;
                attributes.MaterialSource = ObjectMaterialSource.MaterialFromObject;
            }
            if (attachMetadata)
            {
                if (applyRenderMaterial) attributes.SetUserString(MaterialIdKey, (string)recipe["material_id"]);
                if (metadata != null)
                    foreach (var pair in metadata) attributes.SetUserString(pair.Key, pair.Value);
            }
            return attributes;
        }

        // Preserve the legacy assignment field even though it is no longer a general metadata mapping.
        private static readonly HashSet<string> AssignmentMetadataKeys = new HashSet<string>(
            new[] { "floor", "construction_detail", "construction_reference" }.Select(ModelingMetadata.Key)
                .Concat(new[] { "structural_role" }), StringComparer.Ordinal);

        internal static void ValidateMetadata(IDictionary<string, string> metadata)
        {
            if (metadata == null) return;
            foreach (var pair in metadata)
                if (!AssignmentMetadataKeys.Contains(pair.Key) || pair.Value == null)
                    throw new ArgumentException("Unexpected material-assignment metadata: " + pair.Key);
            if (metadata.TryGetValue(ModelingMetadata.Key("construction_reference"), out string reference))
            {
                var value = JObject.Parse(reference);
                if (value.Properties().Any(p => p.Name != "kind" && p.Name != "id") ||
                    (string)value["kind"] != "construction_system" || value["id"]?.Type != JTokenType.String ||
                    String.IsNullOrWhiteSpace((string)value["id"]))
                    throw new ArgumentException("construction_reference requires kind=construction_system and a nonempty id.");
            }
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
                sameMaterial = !previous.IsDeleted && !next.IsDeleted && previous.RenderMaterialInstanceId != Guid.Empty &&
                    previous.RenderMaterialInstanceId == next.RenderMaterialInstanceId;
            }
            return before.LayerIndex == after.LayerIndex && sameMaterial && before.MaterialSource == after.MaterialSource &&
                (beforeText?.Count ?? 0) == (afterText?.Count ?? 0) &&
                (afterText == null || afterText.AllKeys.All(key => beforeText?[key] == afterText[key]));
        }

        private static string ParentPath(string path)
        {
            int separator = path.LastIndexOf("::", StringComparison.Ordinal);
            return separator >= 0 ? path.Substring(0, separator) : "";
        }

        internal sealed record LayerCandidate(int Index, string Path, string MaterialId, bool HasMaterial, bool Unavailable);

        internal static LayerCandidate SelectAssignmentLayer(string path, string id, IEnumerable<LayerCandidate> candidates)
        {
            string category = ParentPath(path);
            bool Equal(string a, string b) => String.Equals(a, b, StringComparison.OrdinalIgnoreCase);
            var matches = candidates.Where(l => Equal(l.Path, path)
                || Equal(l.MaterialId, id) || (l.HasMaterial && Equal(ParentPath(l.Path), category))).ToArray();
            if (matches.Length > 1)
                throw new InvalidOperationException("Multiple candidate layers for material: " + id);
            var match = matches.SingleOrDefault();
            if (match != null && (match.Unavailable || !Equal(ParentPath(match.Path), category)
                || (!String.IsNullOrEmpty(match.MaterialId) && !Equal(match.MaterialId, id)) || !match.HasMaterial))
                throw new InvalidOperationException("Layer is unavailable or has a conflicting material: " + match.Path);
            return match;
        }

        private static Layer AssignmentLayer(RhinoDoc doc, JObject recipe, out string action)
        {
            var settings = recipe["layer_settings"] as JObject
                ?? throw new ArgumentException("Missing material layer settings.");
            string path = (string)settings["path"];
            var parts = (path ?? "").Split(new[] { "::" }, StringSplitOptions.None);
            if (parts.Length != 3 || parts.Any(p => p != p.Trim() || !ModelComponent.IsValidComponentName(p)))
                throw new ArgumentException("Invalid material layer path: " + path);

            string id = (string)recipe["material_id"], name = (string)recipe["name"];
            bool Named(string value) => String.Equals(value, name, StringComparison.OrdinalIgnoreCase)
                || String.Equals(value, "ALMOND::" + id, StringComparison.OrdinalIgnoreCase);
            var tableMaterials = doc.Materials.Where(m => !m.IsDeleted && Named(m.Name)).ToArray();
            var named = doc.RenderMaterials.Where(m => m != null && Named(m.Name)).ToArray();
            if (named.Length > 1 || tableMaterials.Any(m =>
                (!String.IsNullOrEmpty(m.GetUserString(MaterialIdKey)) && m.GetUserString(MaterialIdKey) != id)
                || !named.Any(r => r.Id == m.RenderMaterialInstanceId)))
                throw new InvalidOperationException("Ambiguous or conflicting material identity: " + name);
            var render = named.SingleOrDefault();
            var layers = doc.Layers.Where(l => !l.IsDeleted).ToArray();
            string parentPath = ParentPath(path);
            bool Equal(string a, string b) => String.Equals(a, b, StringComparison.OrdinalIgnoreCase);
            if (layers.Any(l => (Equal(l.FullPath, parts[0]) || Equal(l.FullPath, parentPath))
                && (l.IsReference || l.IsLocked)))
                throw new InvalidOperationException("Material layer parent is unavailable: " + parentPath);
            var existing = SelectAssignmentLayer(path, id, layers.Select(l => new LayerCandidate(
                l.Index, l.FullPath, l.GetUserString(MaterialIdKey),
                render != null && Equal(ParentPath(l.FullPath), parentPath) && l.RenderMaterial?.Id == render.Id,
                l.IsReference || l.IsLocked)));
            if (existing != null)
            {
                action = "reused";
                return doc.Layers[existing.Index];
            }
            int? linetype = null;
            if (settings["linetype"] != null)
            {
                string value = (string)settings["linetype"];
                var match = doc.Linetypes.FindName(value);
                if (match != null && !match.IsDeleted && Equal(match.Name, value))
                    linetype = match.Index;
                else if (Equal(value, "Continuous"))
                    linetype = -1;
                else
                    throw new ArgumentException("Unknown layer linetype: " + value);
            }

            render = render ?? EnsureMaterial(doc, recipe);
            int parentIndex = DocumentLayers.Ensure(doc, parentPath);
            using var newLayer = new Layer { Name = parts[2], ParentLayerId = doc.Layers[parentIndex].Id };
            newLayer.SetUserString(MaterialIdKey, id);
            if (settings["color"] != null) newLayer.Color = ColorFor(settings["color"]);
            if (settings["plot_color"] != null) newLayer.PlotColor = ColorFor(settings["plot_color"]);
            if (settings["plot_weight_mm"] != null) newLayer.PlotWeight = (double)settings["plot_weight_mm"];
            if (linetype.HasValue) newLayer.LinetypeIndex = linetype.Value;
            int index = doc.Layers.Add(newLayer);
            if (index < 0) throw new InvalidOperationException("Cannot create material layer: " + path);
            doc.Layers[index].RenderMaterial = render;
            var created = doc.Layers[index];
            if (created.RenderMaterial?.Id != render.Id)
                throw new InvalidOperationException("Rhino did not bind the material to layer: " + path);
            action = "created";
            return created;
        }

        public static object Apply(RhinoDoc doc, string recipeJson, IEnumerable<Guid> ids,
            IDictionary<string, string> metadata = null, bool applyRenderMaterial = true, bool attachMetadata = false)
        {
            if (doc == null) throw new ArgumentNullException(nameof(doc));
            var requested = ids?.Distinct().ToArray() ?? throw new ArgumentNullException(nameof(ids));
            if (requested.Length == 0) throw new ArgumentException("At least one object GUID is required.");
            ValidateMetadata(metadata);
            var recipe = JObject.Parse(recipeJson);
            var objects = requested.Select(doc.Objects.FindId).ToArray();
            if (objects.Any(o => o == null || o.IsDeleted || o.IsReference || o.IsInstanceDefinitionGeometry))
                throw new ArgumentException("Material targets must be existing editable document objects.");
            if (applyRenderMaterial && objects.Any(o => o.IsLocked || doc.Layers[o.Attributes.LayerIndex].IsLocked))
                throw new ArgumentException("Material targets and their source layers must not be locked.");
            string layerAction = "not_applied";
            var layer = applyRenderMaterial ? AssignmentLayer(doc, recipe, out layerAction) : null;
            var applied = new List<string>();
            var changed = new List<string>();
            var layerChanged = new List<string>();
            foreach (var obj in objects)
            {
                if (!applyRenderMaterial && (!attachMetadata || metadata == null || metadata.Count == 0)) continue;
                var attributes = CreateAttributes(doc, recipeJson, metadata, obj.Attributes,
                    applyRenderMaterial: false, attachMetadata: attachMetadata);
                if (layer != null)
                {
                    attributes.LayerIndex = layer.Index;
                    attributes.MaterialIndex = -1;
                    attributes.MaterialSource = ObjectMaterialSource.MaterialFromLayer;
                    if (attachMetadata) attributes.SetUserString(MaterialIdKey, (string)recipe["material_id"]);
                }
                bool moved = obj.Attributes.LayerIndex != attributes.LayerIndex;
                if (!SameAssignment(doc, obj.Attributes, attributes))
                {
                    if (!doc.Objects.ModifyAttributes(obj.Id, attributes, true))
                        throw new InvalidOperationException("Rhino refused material attributes for object " + obj.Id);
                    changed.Add(obj.Id.ToString());
                    if (moved) layerChanged.Add(obj.Id.ToString());
                }
                if (layer != null)
                {
                    var confirmed = doc.Objects.FindId(obj.Id)?.Attributes;
                    if (confirmed?.LayerIndex != layer.Index ||
                        confirmed.MaterialSource != ObjectMaterialSource.MaterialFromLayer)
                        throw new InvalidOperationException("Rhino did not retain ByLayer material for object " + obj.Id);
                }
                applied.Add(obj.Id.ToString());
            }
            return new {
                material_id = (string)recipe["material_id"], applied_guids = applied, changed_guids = changed,
                layer_path = layer?.FullPath, layer_action = layerAction, layer_changed_guids = layerChanged,
                metadata_attached = attachMetadata && (applyRenderMaterial || (metadata != null && metadata.Count != 0)),
                render_material_applied = applyRenderMaterial
            };
        }
    }
}
