using System;
using System.Collections.Generic;
using System.Collections.Specialized;
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

    static void CheckAssignmentFields()
    {
        var inputs = new Dictionary<string, string> { ["Floor"] = "2F", ["structural_role"] = "joist" };
        var fields = ModelingMaterials.AssignmentFields.Read(inputs);
        var dictionary = new Rhino.Collections.ArchivableDictionary();
        dictionary.Set("Floor", "old floor");
        dictionary.Set("unrelated", "keep");
        const string detail = "construction_detail", reference = "construction_reference";
        var text = new NameValueCollection {
            ["floor"] = "legacy", ["structural_role"] = "joist", ["section"] = "rect 300x640",
            ["release"] = "pinned_start", ["structural_material"] = "Wood",
            [detail] = "old detail", [reference] = "old ref",
        };

        void ApplyText(Dictionary<string, string> writes)
        {
            foreach (var pair in writes)
            {
                Check(!String.IsNullOrEmpty(pair.Value), "Never call the User Text setter with a deletion value.");
                text[pair.Key] = pair.Value;
            }
        }

        var writes = fields.UserTextToWrite(text);
        Check(writes.Count == 1 && writes["structural_role"] == "joist", "Omitted existing keys must receive no writes.");
        text.Remove(reference);
        writes = fields.UserTextToWrite(text);
        Check(!writes.ContainsKey(detail) && writes[reference] == " ", "Initialize only the missing key.");
        ApplyText(writes);
        Check(text[detail] == "old detail" && text[reference] == " ", "Keys must be resolved independently per object.");
        Check(fields.UserTextToWrite(text).Count == 1, "Repeated calls must skip existing blank keys.");

        text.Remove(detail);
        text.Remove(reference);
        writes = fields.UserTextToWrite(text);
        Check(writes[detail] == " " && writes[reference] == " ", "Both missing keys must get one ASCII space.");
        ApplyText(writes);
        const string timber = """{"kind":"construction_system","id":"timber"}""";
        var withReference = ModelingMaterials.AssignmentFields.Read(new Dictionary<string, string>(inputs) {
            [detail] = "", [reference] = timber,
        });
        writes = withReference.UserTextToWrite(text);
        Check(!writes.ContainsKey(detail) && writes[reference] == timber, "A reference alone must not write an existing detail.");
        ApplyText(writes);
        var withDetail = ModelingMaterials.AssignmentFields.Read(new Dictionary<string, string>(inputs) { [detail] = "new detail" });
        writes = withDetail.UserTextToWrite(text);
        Check(writes[detail] == "new detail" && !writes.ContainsKey(reference), "A detail alone must not write an existing reference.");
        ApplyText(writes);
        Check(text[detail] == "new detail" && text[reference] == timber, "Explicit values must replace placeholders.");
        text[detail] = "";
        Check(!fields.UserTextToWrite(text).ContainsKey(detail), "Even an existing zero-length entry must receive no write.");
        var existingKeys = new NameValueCollection { ["Construction_Detail"] = null, [reference] = " " };
        Check(fields.UserTextToWrite(existingKeys).Count == 1, "Test key presence independent of case or stored value.");
        Check(text["floor"] == "legacy" && text["section"] == "rect 300x640" && text["release"] == "pinned_start" &&
            text["structural_material"] == "Wood" && dictionary.GetString("unrelated") == "keep", "Preserve independent metadata.");
        dictionary.Set("Floor", 2);
        Check(!fields.MatchesFloor(dictionary), "A Floor-only difference, including its type, requires a write.");
        dictionary.Set("Floor", fields.Floor);
        Check(fields.MatchesFloor(dictionary), "Confirm the recorded floor.");
        foreach (var key in new[] { "floor", "section", "release", "structural_material" }) {
            var invalid = new Dictionary<string, string>(inputs) { [key] = "value" };
            try { ModelingMaterials.AssignmentFields.Read(invalid); }
            catch (ArgumentException) { continue; }
            throw new Exception(key + " must not be an assignment field");
        }
        foreach (var key in new[] { "Floor", "structural_role" }) {
            var invalid = new Dictionary<string, string>(inputs) { [key] = " " };
            try { ModelingMaterials.AssignmentFields.Read(invalid); }
            catch (ArgumentException) { continue; }
            throw new Exception(key + " must be nonblank");
        }
    }

    static void Main()
    {
        CheckMaterialLayerSelection();
        CheckAssignmentFields();
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
