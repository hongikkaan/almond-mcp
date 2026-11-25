using System;
using System.Collections.Generic;
using RhinoAlmondBridge;

// Exercise the native selection and metadata rules without opening a Rhino document.
static class Program
{
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static void CheckMaterialLayerSelection()
    {
        const string path = "M::wood::oak";
        var unrelated = new ModelingMaterials.LayerCandidate(1, "D::oak", null, true, false);
        var legacy = new ModelingMaterials.LayerCandidate(2, "M::wood::old assembly::member", null, true, false);
        Check(ModelingMaterials.SelectAssignmentLayer(path, "oak", new[] { unrelated, legacy }) == null,
            "Drawing and legacy nested assembly layers must not become material targets.");
        var existing = new ModelingMaterials.LayerCandidate(3, "m::Wood::Hand Renamed Oak", "oak", true, false);
        Check(ModelingMaterials.SelectAssignmentLayer(path, "oak", new[] { unrelated, existing }) == existing,
            "The existing material layer must be reused without resetting its path or style.");
        var canonical = new ModelingMaterials.LayerCandidate(4, path, null, true, false);
        Check(ModelingMaterials.SelectAssignmentLayer(path, "oak", new[] { canonical }) == canonical,
            "A canonical layer with an exact material binding is identifiable without an internal marker.");
        void Reject(params ModelingMaterials.LayerCandidate[] candidates)
        {
            try { ModelingMaterials.SelectAssignmentLayer(path, "oak", candidates); }
            catch (InvalidOperationException) { return; }
            throw new Exception("Expected a conflicting material assignment layer to be rejected.");
        }
        Reject(existing, canonical);
        Reject(canonical with { HasMaterial = false });
        Reject(canonical with { MaterialId = "ash" });
        Reject(existing with { Unavailable = true });
        Reject(existing with { Path = "M::metal::oak" });
    }

    static void Main()
    {
        CheckMaterialLayerSelection();
        ModelingMaterials.ValidateMetadata(new Dictionary<string, string> {
            ["floor"] = "2F", ["construction_detail"] = "Slab",
            ["construction_reference"] = "{\"kind\":\"construction_system\",\"id\":\"slab\"}",
            ["structural_role"] = "slab",
        });
        void RejectMetadata(string key, string value)
        {
            try { ModelingMaterials.ValidateMetadata(new Dictionary<string, string> { [key] = value }); }
            catch (ArgumentException) { return; }
            throw new Exception("Expected invalid assignment metadata to be rejected: " + key);
        }
        RejectMetadata("material_id", "unrelated");
        RejectMetadata("material_category", "Wood");
        RejectMetadata("Floor", "2F");
        RejectMetadata("floor", null);
        RejectMetadata("construction_reference", "{\"kind\":\"unrecognized\",\"id\":\"slab\"}");
        Check(ModelingMetadata.Key("sheet_id") == "sheet_id", "Existing document registry metadata must remain available.");
        Console.WriteLine("PASS: material layer selection and metadata validation");
    }
}
