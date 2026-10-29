using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    public static partial class ObservationTests
    {
        // Pure recipe validation: no document is created or edited.
        public static string RunDrawingStyleValidation()
        {
            var valid = JsonConvert.DeserializeObject<DrawingStyleRequest>(
                @"{""recipe_id"":""a4"",""layers"":[{""path"":""A4::HIDDEN"",""linetype"":""ALMOND A4 Hidden"",
                ""linetype_segments"":[{""length"":3,""is_solid"":true},{""length"":1.5,""is_solid"":false}]}]}");
            var definitions = DrawingStyleManager.ValidateDefinitions(valid.Layers);
            Check(definitions.Count == 1 && definitions["ALMOND A4 Hidden"][0].IsSolid == true &&
                definitions["ALMOND A4 Hidden"][1].IsSolid == false, "Recipe JSON lost its explicit segment kinds.");

            foreach (var invalid in new[] {
                new List<DrawingLinetypeSegment>(),
                new List<DrawingLinetypeSegment> { null },
                Segments((0, true)), Segments((-1, true)), Segments((double.NaN, true)),
                Segments((double.PositiveInfinity, true)), Segments((2, false)),
                new List<DrawingLinetypeSegment> { new DrawingLinetypeSegment { Length = 3 } }
            })
                InvalidDrawingDefinition(() => DrawingStyleManager.ValidateDefinitions(
                    new[] { StyleLayer("A4::INVALID", "Invalid custom pattern", invalid) }));

            InvalidDrawingDefinition(() => DrawingStyleManager.ValidateDefinitions(new[] {
                StyleLayer("A4::ONE", "Same name", Segments((3, true), (1.5, false))),
                StyleLayer("A4::TWO", "same NAME", Segments((6, true), (1.5, false)))
            }));
            InvalidDrawingDefinition(() => DrawingStyleManager.ValidateDefinitions(new[] {
                StyleLayer("A4::ONE", "Continuous", Segments((3, true)))
            }));
            InvalidDrawingDefinition(() => DrawingStyleManager.ValidateDefinitions(new[] {
                StyleLayer("A4::VALID", "Continuous"), StyleLayer(" ", "Continuous")
            }));
            Check(DrawingStyleManager.ValidateDefinitions(new[] {
                StyleLayer("A4::LEGACY", "Legacy name only")
            }).Count == 0, "A legacy recipe unexpectedly requires explicit segments.");
            Check(DrawingStyleManager.ValidateDefinitions(new[] {
                StyleLayer("A4::ONE", "Shared", Segments((3, true), (1.5, false))),
                StyleLayer("A4::TWO", "shared", Segments((3, true), (1.5, false))),
                StyleLayer("A4::THREE", "Shared")
            }).Count == 1, "Agreeing definitions and name-only references were rejected or duplicated.");
            return "PASS: drawing recipe JSON, finite segment validation, explicit segment kinds, conflicting definitions and legacy references.";
        }

        private static DrawingLayerSpecification StyleLayer(string path, string name,
            List<DrawingLinetypeSegment> segments = null)
        {
            return new DrawingLayerSpecification { Path = path, Role = "detail", Color = new[] { 0, 0, 0 },
                PlotColor = new[] { 0, 0, 0 }, PlotWeightMm = 0.1, Linetype = name, LinetypeSegments = segments };
        }

        private static List<DrawingLinetypeSegment> Segments(params (double Length, bool Solid)[] values)
        {
            return values.Select(value => new DrawingLinetypeSegment { Length = value.Length, IsSolid = value.Solid }).ToList();
        }

        private static void InvalidDrawingDefinition(Action action)
        {
            try { action(); }
            catch (ArgumentException) { return; }
            throw new InvalidOperationException("An invalid drawing definition was accepted.");
        }

    }
}
