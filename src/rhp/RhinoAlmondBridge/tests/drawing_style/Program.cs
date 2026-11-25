using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using RhinoAlmondBridge;

if (args.SequenceEqual(new[] { "--apply" }))
{
    var request = JObject.Parse(Console.In.ReadToEnd()).ToObject<DrawingStyleRequest>();
    var applied = new DrawingStyleManager().Apply(new RhinoDoc(), request);
    Console.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(applied));
    return;
}

string manifestPath = Path.Combine(AppContext.BaseDirectory, Path.GetRandomFileName());
try
{
    VerifyStyleApplication(manifestPath);
    VerifyStandardTemplate(manifestPath);
    var noUndo = new RhinoDoc { UndoRecord = 0 };
    var rejected = new DrawingStyleManager().Apply(noUndo,
        ReadRequest(manifestPath, """{"layers":[{"path":"Must not be created"}]}"""));
    Require(rejected.Status == "error" && noUndo.Layers.Count == 0,
        "A modeless style operation must not mutate without owning an Undo record.");
    foreach (bool rollback in new[] { true, false })
    {
        var partial = new RhinoDoc { UndoSucceeds = rollback };
        partial.Layers.FailModifyAt = 2;
        var result = new DrawingStyleManager().Apply(partial,
            ReadRequest(manifestPath, """{"layers":[{"path":"First"},{"path":"Second"}]}"""));
        Require(result.Status == "error" && result.MutationState == (rollback ? "rolled_back" : "unknown") &&
            result.RequiresReconciliation == !rollback && partial.Layers.Count == (rollback ? 0 : 2),
            "Partial layer update did not preserve truthful rollback/uncertain evidence.");
    }
    Console.WriteLine("Drawing style fixture passed.");
}
finally
{
    File.Delete(manifestPath);
}

static void VerifyStyleApplication(string manifestPath)
{
    var document = new RhinoDoc();
    RhinoDoc.ActiveDoc = document;
    var original = new Linetype { Name = "ALMOND A4 Hidden" };
    original.AppendSegment(13, true);
    original.AppendSegment(9, false);
    int originalIndex = document.Linetypes.Add(original);
    int originalLayer = document.Layers.Add(new Layer { Name = "Existing drawing", LinetypeIndex = originalIndex });
    var documentOnly = new Linetype { Name = "Existing document linetype" };
    documentOnly.AppendSegment(2, true);
    int documentOnlyIndex = document.Linetypes.Add(documentOnly);

    File.WriteAllText(manifestPath, """
    {
      "ALMOND A4 Hidden": [
        { "length": 3, "is_solid": true }, { "length": 1.5, "is_solid": false }
      ],
      "ALMOND A4 DashDot": [
        { "length": 11, "is_solid": true }, { "length": 2.75, "is_solid": false },
        { "length": 0.75, "is_solid": true }, { "length": 2.75, "is_solid": false }
      ]
    }
    """);
    var request = ReadRequest(manifestPath, """
    {
      "recipe_id": "fixture_plan",
      "layers": [
        { "path": "ALMOND-DRAW::HIDDEN", "linetype": "almond a4 hidden" },
        { "path": "ALMOND-DRAW::OVERHEAD", "linetype": "almond a4 dashdot" },
        { "path": "ALMOND-DRAW::DETAIL", "linetype": "Existing document linetype" }
      ]
    }
    """);

    var manager = new DrawingStyleManager();
    int newIndex = -1;
    for (int application = 0; application < 2; application++)
    {
        if (application > 0)
            File.Delete(manifestPath);
        var result = manager.Apply(request);
        Require(result.Status == "success", result.Message);
        Require(document.Linetypes.Count == 3, "The style should add a single new definition.");
        Require(document.Layers[result.Layers[2].LayerIndex].LinetypeIndex == documentOnlyIndex,
            "A document-only linetype should be reusable on its own.");
        Require(document.Linetypes[originalIndex].Segments.SequenceEqual(new[] { (13.0, true), (9.0, false) }),
            "The document's differing same-name definition changed.");
        Require(document.Layers[originalLayer].LinetypeIndex == originalIndex &&
            document.Layers[result.Layers[0].LayerIndex].LinetypeIndex == originalIndex,
            "Existing and newly styled layers must reference the same original definition.");
        Require(result.Layers[0].Linetype == "ALMOND A4 Hidden", "The result must show the document's linetype name.");

        var added = document.Linetypes.FindName("ALMOND A4 DashDot");
        Require(added.Segments.SequenceEqual(new[] { (11.0, true), (2.75, false), (0.75, true), (2.75, false) }),
            "The new linetype must have the linetype manifest's dash and gap lengths.");
        Require(document.Layers[result.Layers[1].LayerIndex].LinetypeIndex == added.Index,
            "The overhead layer must reference the new definition.");
        if (application == 0)
            newIndex = added.Index;
        Require(added.Index == newIndex, "Repeat application changed the linetype reference.");
    }

    int layerCount = document.Layers.Count;
    var unknownName = ReadRequest(manifestPath, """
    {
      "layers": [
        { "path": "Must not be created" },
        { "path": "Unknown style layer", "linetype": "Missing definition" }
      ]
    }
    """);
    var missingFile = manager.Apply(unknownName);
    Require(missingFile.Status == "error" && missingFile.Message.Contains(manifestPath),
        "An unavailable linetype manifest should give the path to inspect.");
    File.WriteAllText(manifestPath, "{}");
    var missingPattern = manager.Apply(unknownName);
    Require(missingPattern.Status == "error" && missingPattern.Message.Contains("Missing definition"),
        "A new linetype without a definition should give a named error.");
    Require(missingPattern.Layers.Count == 0 && document.Layers.Count == layerCount && document.Linetypes.Count == 3,
        "Missing definitions must be found before any layer or linetype is changed.");
}

static void VerifyStandardTemplate(string manifestPath)
{
    File.WriteAllText(manifestPath, """
    {"ALMOND D ISO 02 Dashed": [{"length": 2.16, "is_solid": true}, {"length": 0.54, "is_solid": false}]}
    """);
    var doc = new RhinoDoc();
    var manager = new DrawingStyleManager();
    var style = ReadRequest(manifestPath, """
    {
      "recipe_id": "standard_d",
      "layers": [
        {"path": "D::Section", "plot_weight_mm": 0.50, "role": "Cut profiles"},
        {"path": "D::Line::Hidden", "linetype": "ALMOND D ISO 02 Dashed", "plot_weight_mm": 0.18},
        {"path": "D::Line::Overhead", "linetype": " almond d iso 02 DASHED "}
      ]
    }
    """);
    int generatedIndex = DocumentLayers.Ensure(doc, "D::PlanSection::Section");
    var generated = doc.Layers[generatedIndex];
    generated.PlotWeight = 1.0;
    var first = manager.Apply(doc, style);
    Require(first.Status == "success" && first.MutationState == "completed", first.Message);
    int sectionIndex = first.Layers[0].LayerIndex;
    int patternIndex = doc.Layers[first.Layers[1].LayerIndex].LinetypeIndex;
    Require(doc.Linetypes.NameLookups == 2 && doc.Linetypes.Count == 1 &&
        doc.Layers[first.Layers[2].LayerIndex].LinetypeIndex == patternIndex,
        "Look up each distinct linetype once and share the new document index between layers.");
    Require(first.Layers[0].Role == "Cut profiles" && doc.Layers[sectionIndex].PlotWeight == .50,
        "A manual role must resolve to its styled local layer.");
    Require(doc.Linetypes[patternIndex].Segments.SequenceEqual(new[] { (2.16, true), (.54, false) }),
        "A missing standard pattern must be materialized from the linetype manifest.");

    int changes = doc.Layers.Modifications;
    doc.UndoRecord = 0;
    var repeat = manager.Apply(doc, style);
    Require(repeat.Status == "success" && repeat.MutationState == "none" &&
        repeat.Layers[0].LayerIndex == sectionIndex && doc.Layers.Modifications == changes,
        "Matching layers must resolve without any mutation or Undo record.");
    doc.UndoRecord = 1;

    doc.Layers[sectionIndex].PlotWeight = .8;
    doc.Linetypes[patternIndex].Segments[0] = (6, true);
    var protectedStyle = manager.Apply(doc, style);
    Require(protectedStyle.Status == "error" && protectedStyle.Message.Contains("overwrite=true") &&
        protectedStyle.Message.Contains("D::Section") && protectedStyle.Message.Contains("ISO 02") &&
        doc.Layers[sectionIndex].PlotWeight == .8 && doc.Linetypes[patternIndex].Segments[0].Length == 6 &&
        doc.Layers.Modifications == changes,
        "Conflicting definitions must not change by default.");

    style.Overwrite = true;
    generated.LinetypeIndex = patternIndex;
    var generatedInUse = manager.Apply(doc, style);
    Require(generatedInUse.Status == "error" && generatedInUse.Message.Contains("D::PlanSection"),
        "Even overwrite must not change a shared pattern referenced by a generated layer.");
    generated.LinetypeIndex = -1;
    var drawingObject = new RhinoObject();
    drawingObject.Attributes.LayerIndex = generatedIndex;
    drawingObject.Attributes.LinetypeIndex = patternIndex;
    drawingObject.Attributes.LinetypeSource = ObjectLinetypeSource.LinetypeFromObject;
    doc.Objects.Add(drawingObject);
    var objectInUse = manager.Apply(doc, style);
    Require(objectInUse.Status == "error" && objectInUse.Message.Contains("D::PlanSection") &&
        doc.Linetypes[patternIndex].Segments[0].Length == 6, "Object-level linetypes on generated output must survive overwrite.");
    drawingObject.Attributes.LinetypeSource = ObjectLinetypeSource.LinetypeFromLayer;
    style.RecipeId = "bundled";
    style.IncludeStandardD = true;
    style.Overwrite = null;
    style.Layers.Add(new DrawingLayerSpecification { Path = "Drawing::Profile", PlotWeightMm = .35 });
    var mixed = manager.Apply(doc, style);
    Require(mixed.Status == "error" && !doc.Layers.Any(layer => layer.Name == "Profile") &&
        doc.Layers.Modifications == changes, "A standard conflict must stop the entire mixed recipe before writes.");
    style.Overwrite = true;
    style.Layers.RemoveAt(style.Layers.Count - 1);
    var overwrite = manager.Apply(doc, style);
    Require(overwrite.Status == "success" && doc.Layers[sectionIndex].PlotWeight == .50 &&
        doc.Linetypes[patternIndex].Segments[0].Length == 2.16 && doc.Layers.Modifications == changes + 1 &&
        doc.Layers[generatedIndex].PlotWeight == 1.0,
        "Overwrite must repair only differing manual definitions and leave PlanSection as-is.");

    var legacy = new DrawingLayerSpecification { Path = "Drawing::Profile", PlotWeightMm = .35 };
    int legacyIndex = DocumentLayers.Ensure(doc, legacy.Path);
    style.Layers.Add(legacy);
    style.Overwrite = null;
    Require(manager.Apply(doc, style).Status == "success" && doc.Layers[legacyIndex].PlotWeight == .35,
        "An omitted overwrite must retain the bundled recipe's legacy layer behavior.");
    style.Layers[0].Path = "d::plansection::SECTION";
    var forged = manager.Apply(doc, style);
    Require(forged.Status == "error" && doc.Layers[generatedIndex].PlotWeight == 1.0,
        "The native standard D action must reject the PlanSection subtree.");
}

static DrawingStyleRequest ReadRequest(string manifestPath, string requestJson)
{
    var request = JObject.Parse(requestJson);
    request["linetype_manifest_path"] = manifestPath;
    return request.ToObject<DrawingStyleRequest>();
}

static void Require(bool condition, string message)
{
    if (!condition)
        throw new InvalidOperationException(message);
}
