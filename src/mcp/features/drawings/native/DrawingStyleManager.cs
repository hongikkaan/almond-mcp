using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    public class DrawingStyleManager
    {
        public DrawingStyleResult Apply(DrawingStyleRequest request)
        {
            return Apply(RhinoDoc.ActiveDoc, request);
        }

        internal DrawingStyleResult Apply(RhinoDoc doc, DrawingStyleRequest request)
        {
            var result = new DrawingStyleResult
            {
                Status = "error",
                RecipeId = request?.RecipeId,
                Layers = new List<DrawingLayerResult>()
            };
            if (request?.Layers == null || request.Layers.Count == 0)
            {
                result.Message = "Drawing recipe must contain at least one layer.";
                return result;
            }
            if (doc == null)
            {
                result.Message = "No active Rhino document.";
                return result;
            }

            try
            {
                bool standard = string.Equals(request.RecipeId, "standard_d", StringComparison.Ordinal);
                bool overwrite = request.Overwrite ?? !standard;
                bool standardOverwrite = request.Overwrite == true;
                bool StandardLayer(DrawingLayerSpecification layer) => standard ||
                    (request.IncludeStandardD && layer.Path.StartsWith("D::", StringComparison.OrdinalIgnoreCase));
                var neededDefinitions = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                var linetypeIndices = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
                foreach (var specification in request.Layers)
                {
                    if (specification == null || string.IsNullOrWhiteSpace(specification.Path))
                        throw new ArgumentException("Drawing layer path cannot be empty.");
                    if (StandardLayer(specification) && (!specification.Path.StartsWith("D::", StringComparison.OrdinalIgnoreCase)
                        || specification.Path.Equals("D::PlanSection", StringComparison.OrdinalIgnoreCase)
                        || specification.Path.StartsWith("D::PlanSection::", StringComparison.OrdinalIgnoreCase)))
                        throw new ArgumentException($"Not a manual standard D layer: {specification.Path}.");

                    string name = LinetypeName(specification.Linetype);
                    var existing = FindExactLinetype(doc, name);
                    bool continuous = string.Equals(name, "Continuous", StringComparison.OrdinalIgnoreCase);
                    if (existing != null)
                        linetypeIndices[name] = existing.Index;
                    else if (continuous)
                        linetypeIndices[name] = -1;
                    if (!continuous && (StandardLayer(specification) || existing == null))
                        neededDefinitions.Add(name);
                }

                var definitions = ReadDefinitions(request.LinetypeManifestPath, neededDefinitions);
                var changedPatterns = new List<string>();
                var conflicts = new List<string>();
                if (standard || request.IncludeStandardD)
                {
                    foreach (var definition in definitions.Values)
                    {
                        if (!linetypeIndices.TryGetValue(definition.Name, out int index)
                            || PatternMatches(doc.Linetypes[index], definition))
                            continue;
                        if (standardOverwrite)
                        {
                            var generated = FindLocalLayer(doc, "D::PlanSection");
                            if (generated != null && SubtreeUsesLinetype(doc, generated, index))
                                throw new InvalidOperationException($"Linetype {definition.Name} is used by D::PlanSection and cannot be overwritten by the manual template.");
                        }
                        changedPatterns.Add(definition.Name);
                        if (!standardOverwrite) conflicts.Add($"linetype {definition.Name}");
                    }
                }

                var updates = new List<DrawingLayerSpecification>();
                foreach (var specification in request.Layers)
                {
                    var existing = FindLocalLayer(doc, specification.Path);
                    if (existing != null)
                    {
                        var name = LinetypeName(specification.Linetype);
                        if (linetypeIndices.TryGetValue(name, out int index)
                            && LayerMatches(existing, specification, index))
                            continue;
                        if (!(StandardLayer(specification) ? standardOverwrite : overwrite))
                            conflicts.Add(specification.Path);
                    }
                    updates.Add(specification);
                }
                if (conflicts.Count != 0)
                {
                    result.Message = $"Existing definitions differ: {string.Join(", ", conflicts)}. No changes made. Use overwrite=true to replace them.";
                    return result;
                }

                if (updates.Count == 0 && changedPatterns.Count == 0)
                {
                    ReadResultLayers();
                    result.Status = "success";
                    result.Message = $"All {result.Layers.Count} drawing layers already match.";
                    return result;
                }

                var mutation = AlmondEngine.NativeUndoRecord.Run(doc, "Apply Almond drawing style", () =>
                {
                    foreach (var name in changedPatterns)
                        if (!doc.Linetypes.Modify(CreateLinetype(definitions[name]), linetypeIndices[name], true))
                            throw new InvalidOperationException($"Could not replace linetype {name}.");

                    foreach (var specification in updates)
                    {
                        string name = LinetypeName(specification.Linetype);
                        if (!linetypeIndices.TryGetValue(name, out int linetypeIndex))
                        {
                            linetypeIndex = AddLinetype(doc, definitions[name]);
                            linetypeIndices.Add(name, linetypeIndex);
                        }
                        int layerIndex = DocumentLayers.Ensure(doc, specification.Path);
                        var layer = doc.Layers[layerIndex];
                        layer.EnsurePrivateCopy();
                        layer.Color = ReadColor(specification.Color, Color.Black);
                        layer.PlotColor = ReadColor(specification.PlotColor, layer.Color);
                        layer.PlotWeight = Math.Max(0.0, specification.PlotWeightMm);
                        layer.LinetypeIndex = linetypeIndex;
                        if (!doc.Layers.Modify(layer, layerIndex, true))
                            throw new InvalidOperationException($"Rhino failed to update drawing layer {specification.Path}.");
                    }

                    ReadResultLayers();
                });

                void ReadResultLayers()
                {
                    foreach (var specification in request.Layers)
                    {
                        var layer = FindLocalLayer(doc, specification.Path);
                        if (layer == null)
                            throw new InvalidOperationException($"Drawing layer {specification.Path} could not be resolved.");
                        result.Layers.Add(new DrawingLayerResult
                        {
                            Path = specification.Path,
                            Role = specification.Role,
                            LayerIndex = layer.Index,
                            PlotWeightMm = layer.PlotWeight,
                            Linetype = layer.LinetypeIndex < 0
                                ? "Continuous"
                                : doc.Linetypes[layer.LinetypeIndex]?.Name ?? "Continuous"
                        });
                    }
                }

                result.MutationState = mutation.State;
                result.RequiresReconciliation = mutation.State == "unknown";
                if (!mutation.Success)
                {
                    result.Message = mutation.Error;
                    if (mutation.State == "rolled_back") result.Layers.Clear();
                    return result;
                }
                try { doc.Views.Redraw(); } catch { /* Display failure does not change the committed operation. */ }
                result.Status = "success";
                result.Message = $"Applied {result.Layers.Count} drawing layers.";
                return result;
            }
            catch (Exception ex)
            {
                result.Message = ex.Message;
                result.ErrorTrace = ex.ToString();
                return result;
            }
        }

        private static Dictionary<string, DrawingLinetypeDefinition> ReadDefinitions(
            string manifestPath, HashSet<string> missingNames)
        {
            var definitions = new Dictionary<string, DrawingLinetypeDefinition>(StringComparer.OrdinalIgnoreCase);
            if (missingNames.Count == 0)
                return definitions;
            if (string.IsNullOrWhiteSpace(manifestPath))
                throw new ArgumentException("Almond linetype manifest path is unavailable.");

            JObject manifest;
            try
            {
                manifest = JObject.Parse(File.ReadAllText(manifestPath), new JsonLoadSettings
                {
                    DuplicatePropertyNameHandling = DuplicatePropertyNameHandling.Error
                });
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException || ex is JsonException)
            {
                throw new InvalidOperationException(
                    $"Could not read the Almond linetype manifest at {manifestPath}: {ex.Message}", ex);
            }

            foreach (var entry in manifest.Properties())
            {
                string name = entry.Name.Trim();
                if (!missingNames.Contains(name))
                    continue;
                if (definitions.ContainsKey(name))
                    throw new ArgumentException($"Linetype {name} is defined more than once in {manifestPath}.");
                var segments = entry.Value.ToObject<List<DrawingLinetypeSegment>>();
                ValidateSegments(name, segments);
                definitions.Add(name, new DrawingLinetypeDefinition(name, segments));
            }

            foreach (string name in missingNames)
                if (!definitions.ContainsKey(name))
                    throw new ArgumentException($"Linetype {name} is missing from the Almond linetype manifest at {manifestPath}.");
            return definitions;
        }

        private static void ValidateSegments(string name, List<DrawingLinetypeSegment> segments)
        {
            if (segments == null || segments.Count == 0)
                throw new ArgumentException($"Linetype {name} must contain at least one segment.");
            bool hasStroke = false;
            foreach (var segment in segments)
            {
                if (segment == null || !double.IsFinite(segment.Length) || segment.Length <= 0 || !segment.IsSolid.HasValue)
                    throw new ArgumentException($"Linetype {name} needs positive finite lengths and explicit is_solid values.");
                hasStroke |= segment.IsSolid.Value;
            }
            if (!hasStroke)
                throw new ArgumentException($"Linetype {name} must contain a solid segment.");
        }

        private static string LinetypeName(string requestedName)
        {
            return string.IsNullOrWhiteSpace(requestedName) ? "Continuous" : requestedName.Trim();
        }

        private static Linetype FindExactLinetype(RhinoDoc doc, string name)
        {
            // Default linetypes (Continuous, ByLayer, ByParent) do not
            // enumerate in the linetype table, and table index 0 is not
            // Continuous in Rhino 8 (verified live: index 0 was "Hidden").
            // A missing custom name can also resolve to Continuous. A non-null
            // result alone therefore does not prove the requested name exists.
            var existing = doc.Linetypes.FindName(name);
            return existing != null && !existing.IsDeleted && string.Equals(existing.Name, name, StringComparison.OrdinalIgnoreCase)
                ? existing : null;
        }

        private sealed record DrawingLinetypeDefinition(string Name, List<DrawingLinetypeSegment> Segments);

        private static Layer FindLocalLayer(RhinoDoc doc, string path)
        {
            Guid parent = Guid.Empty;
            Layer found = null;
            foreach (var part in path.Split(new[] { "::" }, StringSplitOptions.None))
            {
                found = doc.Layers.FirstOrDefault(l => !l.IsDeleted && !l.IsReference
                    && l.ParentLayerId == parent && string.Equals(l.Name, part, StringComparison.OrdinalIgnoreCase));
                if (found == null) return null;
                parent = found.Id;
            }
            return found;
        }

        private static bool SubtreeUsesLinetype(RhinoDoc doc, Layer layer, int index)
        {
            var objects = doc.Objects.FindByLayer(layer);
            return layer.LinetypeIndex == index || (objects != null && objects.Any(obj =>
                obj.Attributes.LinetypeSource == ObjectLinetypeSource.LinetypeFromObject &&
                obj.Attributes.LinetypeIndex == index)) || doc.Layers.Any(child => !child.IsDeleted
                && child.ParentLayerId == layer.Id && SubtreeUsesLinetype(doc, child, index));
        }

        private static bool LayerMatches(Layer layer, DrawingLayerSpecification specification, int index)
        {
            var color = ReadColor(specification.Color, Color.Black);
            return layer.Color.ToArgb() == color.ToArgb()
                && layer.PlotColor.ToArgb() == ReadColor(specification.PlotColor, color).ToArgb()
                && Math.Abs(layer.PlotWeight - Math.Max(0, specification.PlotWeightMm)) < 1e-6
                && layer.LinetypeIndex == index;
        }

        private static bool PatternMatches(Linetype pattern, DrawingLinetypeDefinition definition)
        {
            if (pattern.SegmentCount != definition.Segments.Count) return false;
            for (int i = 0; i < pattern.SegmentCount; i++)
            {
                pattern.GetSegment(i, out double length, out bool solid);
                var expected = definition.Segments[i];
                if (solid != expected.IsSolid.Value || Math.Abs(length - expected.Length) >= 1e-6)
                    return false;
            }
            return true;
        }

        private static Linetype CreateLinetype(DrawingLinetypeDefinition definition)
        {
            var created = new Linetype { Name = definition.Name };
            foreach (var segment in definition.Segments)
                created.AppendSegment(segment.Length, segment.IsSolid.Value);
            return created;
        }

        private static int AddLinetype(RhinoDoc doc, DrawingLinetypeDefinition definition)
        {
            int index = doc.Linetypes.Add(CreateLinetype(definition));
            if (index < 0)
                throw new InvalidOperationException($"Could not create linetype {definition.Name}.");
            return index;
        }

        private static Color ReadColor(int[] values, Color fallback)
        {
            if (values == null || values.Length != 3)
                return fallback;
            return Color.FromArgb(
                Math.Max(0, Math.Min(255, values[0])),
                Math.Max(0, Math.Min(255, values[1])),
                Math.Max(0, Math.Min(255, values[2]))
            );
        }
    }

    public class DrawingStyleRequest
    {
        [JsonProperty("recipe_id")]
        public string RecipeId { get; set; }

        [JsonProperty("overwrite")]
        public bool? Overwrite { get; set; }

        [JsonProperty("include_standard_d")]
        public bool IncludeStandardD { get; set; }

        [JsonProperty("layers")]
        public List<DrawingLayerSpecification> Layers { get; set; }

        [JsonProperty("linetype_manifest_path")]
        public string LinetypeManifestPath { get; set; }
    }

    public class DrawingLayerSpecification
    {
        [JsonProperty("path")]
        public string Path { get; set; }

        [JsonProperty("role")]
        public string Role { get; set; }

        [JsonProperty("color")]
        public int[] Color { get; set; }

        [JsonProperty("plot_color")]
        public int[] PlotColor { get; set; }

        [JsonProperty("plot_weight_mm")]
        public double PlotWeightMm { get; set; }

        [JsonProperty("linetype")]
        public string Linetype { get; set; }
    }

    public class DrawingLinetypeSegment
    {
        [JsonProperty("length")]
        public double Length { get; set; }

        [JsonProperty("is_solid")]
        public bool? IsSolid { get; set; }
    }

    public class DrawingStyleResult
    {
        [JsonProperty("mutation_state")]
        public string MutationState { get; set; } = "none";
        [JsonProperty("requires_reconciliation")]
        public bool RequiresReconciliation { get; set; }

        [JsonProperty("status")]
        public string Status { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }

        [JsonProperty("recipe_id")]
        public string RecipeId { get; set; }

        [JsonProperty("layers")]
        public List<DrawingLayerResult> Layers { get; set; }

        [JsonProperty("error_trace")]
        public string ErrorTrace { get; set; }
    }

    public class DrawingLayerResult
    {
        [JsonProperty("path")]
        public string Path { get; set; }

        [JsonProperty("role")]
        public string Role { get; set; }

        [JsonProperty("layer_index")]
        public int LayerIndex { get; set; }

        [JsonProperty("plot_weight_mm")]
        public double PlotWeightMm { get; set; }

        [JsonProperty("linetype")]
        public string Linetype { get; set; }
    }
}
