using System;
using System.Collections.Generic;
using System.Drawing;
using Newtonsoft.Json;
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

            uint undoRecord = 0;
            try
            {
                var definitions = ValidateDefinitions(request.Layers);
                foreach (var definition in definitions)
                {
                    var existing = FindExactLinetype(doc, definition.Key);
                    if (existing != null && !MatchesSegments(existing, definition.Value))
                        throw PatternConflict(definition.Key);
                }

                // Invalid or conflicting definitions fail before layers, linetypes
                // or an Undo record are changed.
                undoRecord = doc.BeginUndoRecord("Apply Almond drawing style");
                foreach (var specification in request.Layers)
                {
                    string name = LinetypeName(specification.Linetype);
                    definitions.TryGetValue(name, out var segments);
                    int linetypeIndex = EnsureLinetype(doc, name, segments);
                    int layerIndex = DocumentLayers.Ensure(doc, specification.Path);
                    var layer = doc.Layers[layerIndex];
                    layer.EnsurePrivateCopy();
                    layer.Color = ReadColor(specification.Color, Color.Black);
                    layer.PlotColor = ReadColor(specification.PlotColor, layer.Color);
                    layer.PlotWeight = Math.Max(0.0, specification.PlotWeightMm);
                    layer.LinetypeIndex = linetypeIndex;
                    if (!doc.Layers.Modify(layer, layerIndex, true))
                        throw new InvalidOperationException(
                            $"Rhino failed to update drawing layer {specification.Path}."
                        );

                    result.Layers.Add(new DrawingLayerResult
                    {
                        Path = specification.Path,
                        Role = specification.Role,
                        LayerIndex = layerIndex,
                        PlotWeightMm = layer.PlotWeight,
                        Linetype = layer.LinetypeIndex < 0
                            ? "Continuous"
                            : doc.Linetypes[layer.LinetypeIndex]?.Name ?? "Continuous"
                    });
                }
                doc.Views.Redraw();
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
            finally
            {
                if (undoRecord != 0)
                    doc.EndUndoRecord(undoRecord);
            }
        }

        internal static Dictionary<string, List<DrawingLinetypeSegment>> ValidateDefinitions(
            IReadOnlyList<DrawingLayerSpecification> layers)
        {
            if (layers == null || layers.Count == 0)
                throw new ArgumentException("Drawing recipe must contain at least one layer.");
            var definitions = new Dictionary<string, List<DrawingLinetypeSegment>>(StringComparer.OrdinalIgnoreCase);
            foreach (var specification in layers)
            {
                if (specification == null || string.IsNullOrWhiteSpace(specification.Path))
                    throw new ArgumentException("Drawing layer path cannot be empty.");
                var segments = specification.LinetypeSegments;
                if (segments == null)
                    continue; // Existing recipes keep their name-only behaviour.
                string name = LinetypeName(specification.Linetype);
                if (string.Equals(name, "Continuous", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "ByLayer", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "ByParent", StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException("Explicit segments require a named custom linetype.");
                if (segments.Count == 0)
                    throw new ArgumentException($"Linetype {name} must contain at least one segment.");
                bool hasStroke = false;
                foreach (var segment in segments)
                {
                    if (segment == null || double.IsNaN(segment.Length) || double.IsInfinity(segment.Length) ||
                        segment.Length <= 0 || !segment.IsSolid.HasValue)
                        throw new ArgumentException($"Linetype {name} needs positive finite lengths and explicit is_solid values.");
                    hasStroke |= segment.IsSolid.Value;
                }
                if (!hasStroke)
                    throw new ArgumentException($"Linetype {name} must contain a solid segment.");
                if (definitions.TryGetValue(name, out var prior) && !SameSegments(prior, segments))
                    throw PatternConflict(name);
                definitions[name] = segments;
            }
            return definitions;
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
            return existing != null && string.Equals(existing.Name, name, StringComparison.OrdinalIgnoreCase)
                ? existing : null;
        }

        private static bool SameSegment(double firstLength, bool firstSolid, double secondLength, bool secondSolid)
        {
            return firstSolid == secondSolid && Math.Abs(firstLength - secondLength) <=
                1e-9 * Math.Max(1.0, Math.Max(Math.Abs(firstLength), Math.Abs(secondLength)));
        }

        private static bool SameSegments(IReadOnlyList<DrawingLinetypeSegment> first,
            IReadOnlyList<DrawingLinetypeSegment> second)
        {
            if (first.Count != second.Count)
                return false;
            for (int i = 0; i < first.Count; i++)
                if (!SameSegment(first[i].Length, first[i].IsSolid.Value, second[i].Length, second[i].IsSolid.Value))
                    return false;
            return true;
        }

        private static bool MatchesSegments(Linetype existing, IReadOnlyList<DrawingLinetypeSegment> requested)
        {
            if (existing.SegmentCount != requested.Count)
                return false;
            for (int i = 0; i < requested.Count; i++)
            {
                existing.GetSegment(i, out double length, out bool solid);
                if (!SameSegment(length, solid, requested[i].Length, requested[i].IsSolid.Value))
                    return false;
            }
            return true;
        }

        private static ArgumentException PatternConflict(string name)
        {
            return new ArgumentException($"Linetype {name} has a different segment definition. Use a matching definition or a distinct linetype name.");
        }

        private static int EnsureLinetype(RhinoDoc doc, string name, IReadOnlyList<DrawingLinetypeSegment> segments)
        {
            var existing = FindExactLinetype(doc, name);
            if (existing != null)
            {
                if (segments != null && !MatchesSegments(existing, segments))
                    throw PatternConflict(name);
                return existing.Index;
            }
            if (string.Equals(name, "Continuous", StringComparison.OrdinalIgnoreCase))
                return -1;

            var created = new Linetype { Name = name };
            if (segments != null)
            {
                foreach (var segment in segments)
                    created.AppendSegment(segment.Length, segment.IsSolid.Value);
            }
            else if (name.IndexOf("DashDot", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                created.AppendSegment(8.0, true);
                created.AppendSegment(3.0, false);
                created.AppendSegment(1.0, true);
                created.AppendSegment(3.0, false);
            }
            else
            {
                created.AppendSegment(6.0, true);
                created.AppendSegment(3.0, false);
            }
            int index = doc.Linetypes.Add(created);
            if (index < 0)
                throw new InvalidOperationException($"Could not create linetype {name}.");
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

        [JsonProperty("layers")]
        public List<DrawingLayerSpecification> Layers { get; set; }
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

        [JsonProperty("linetype_segments")]
        public List<DrawingLinetypeSegment> LinetypeSegments { get; set; }
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
