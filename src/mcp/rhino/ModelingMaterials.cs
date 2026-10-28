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
        private static Color ColorFor(JToken rgb) => Color.FromArgb((int)rgb[0], (int)rgb[1], (int)rgb[2]);

        private static RenderMaterial EnsureMaterial(RhinoDoc doc, JObject recipe, bool overwrite = false,
            bool reuseLegacyMaterial = true)
        {
            string name = (string)recipe["name"], legacy = "ALMOND::" + (string)recipe["material_id"];
            foreach (var material in doc.Materials.Where(m => !m.IsDeleted &&
                (m.Name == name || (reuseLegacyMaterial && m.Name == legacy))))
            {
                string existingId = material.GetUserString(ModelingMetadata.Key("material_id"));
                if (!String.IsNullOrEmpty(existingId) && existingId != (string)recipe["material_id"])
                    throw new ArgumentException("The named Rhino material has a conflicting material_id: " + material.Name);
            }
            var matches = doc.RenderMaterials.Where(m => m != null &&
                (m.Name == name || (reuseLegacyMaterial && m.Name == legacy))).ToArray();
            var existing = matches.FirstOrDefault(m => m.Name == name) ?? matches.FirstOrDefault();
            if (existing != null && !overwrite) return existing;
            var targets = matches.Length > 0 ? matches : new[] {
                RenderContent.Create(doc, ContentUuids.PhysicallyBasedMaterialType) as RenderMaterial
            };
            int preferred = existing == null ? 0 : Array.IndexOf(targets, existing);
            for (int i = 0; i < targets.Length; i++)
            {
                var material = targets[i];
                if (material == null) throw new InvalidOperationException("Cannot create material: " + name);
                if (material.TypeId != ContentUuids.PhysicallyBasedMaterialType)
                    material = targets[i] = Utilities.ChangeContentType(material, ContentUuids.PhysicallyBasedMaterialType, false) as RenderMaterial;
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
            }
            return targets[preferred];
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
                    material.SetUserString(ModelingMetadata.Key("material_id"), (string)recipe["material_id"]);
                    index = doc.Materials.Add(material);
                }
                if (index < 0) throw new InvalidOperationException("Cannot assign material: " + render.Name);
                attributes.MaterialIndex = index;
                attributes.MaterialSource = ObjectMaterialSource.MaterialFromObject;
            }
            if (attachMetadata)
            {
                if (applyRenderMaterial) attributes.SetUserString(ModelingMetadata.Key("material_id"), (string)recipe["material_id"]);
                if (metadata != null)
                    foreach (var pair in metadata) attributes.SetUserString(pair.Key, pair.Value);
            }
            return attributes;
        }

        private static void ValidateMetadata(IDictionary<string, string> metadata)
        {
            if (metadata == null) return;
            foreach (var pair in metadata)
                if (!ModelingMetadata.IsMaterialAssignmentKey(pair.Key) || pair.Value == null)
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
            var applied = new List<string>();
            var changed = new List<string>();
            foreach (var obj in objects)
            {
                if (!applyRenderMaterial && (!attachMetadata || metadata == null || metadata.Count == 0)) continue;
                var attributes = CreateAttributes(doc, recipeJson, metadata, obj.Attributes, applyRenderMaterial, attachMetadata);
                if (!SameAssignment(doc, obj.Attributes, attributes))
                {
                    if (!doc.Objects.ModifyAttributes(obj.Id, attributes, true))
                        throw new InvalidOperationException("Rhino refused material attributes for object " + obj.Id);
                    changed.Add(obj.Id.ToString());
                }
                applied.Add(obj.Id.ToString());
            }
            return new {
                material_id = (string)recipe["material_id"], applied_guids = applied, changed_guids = changed,
                layer_path = (string)null, metadata_attached = attachMetadata && (applyRenderMaterial || (metadata != null && metadata.Count != 0)),
                render_material_applied = applyRenderMaterial
            };
        }

        public static object Register(RhinoDoc doc, string recipesJson, bool? overwrite = null)
        {
            if (!overwrite.HasValue)
            {
                using var choice = new Rhino.Input.Custom.GetOption();
                choice.SetCommandPrompt("Overwrite materials with matching names?");
                int yes = choice.AddOption("Yes");
                choice.AddOption("No");
                choice.AcceptNothing(true);
                var answer = choice.Get();
                if (answer == Rhino.Input.GetResult.Cancel) return new { cancelled = true };
                overwrite = answer == Rhino.Input.GetResult.Option && choice.OptionIndex() == yes;
            }
            int updated = 0, skipped = 0;
            foreach (var recipe in JArray.Parse(recipesJson).OfType<JObject>())
            {
                string name = (string)recipe["name"], legacy = "ALMOND::" + (string)recipe["material_id"];
                bool exists = doc.RenderMaterials.Any(m => m != null && (m.Name == name || m.Name == legacy));
                if (exists && !overwrite.Value) { skipped++; continue; }
                EnsureMaterial(doc, recipe, overwrite.Value);
                updated++;
            }
            doc.Views.Redraw();
            return new { updated_materials = updated, skipped_materials = skipped };
        }

        public static object ApplyLayers(RhinoDoc doc, string specificationsJson)
        {
            int count = 0;
            foreach (var specification in JArray.Parse(specificationsJson).OfType<JObject>())
            {
                string path = (string)specification["path"];
                int index = DocumentLayers.Ensure(doc, path);
                var recipe = specification["material"] as JObject;
                if (recipe != null) doc.Layers[index].RenderMaterial = EnsureMaterial(doc, recipe);
                var layer = doc.Layers[index];
                layer.EnsurePrivateCopy();
                layer.Color = layer.PlotColor = ColorFor(specification["color"]);
                if (!doc.Layers.Modify(layer, index, true)) throw new InvalidOperationException("Cannot style layer: " + path);
                count++;
            }
            doc.Views.Redraw();
            return new { applied_layers = count };
        }
    }
}
