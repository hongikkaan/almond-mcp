using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using RhinoAlmondBridge;

string manifestPath = Path.Combine(AppContext.BaseDirectory, Path.GetRandomFileName());
try
{
    VerifyStyleApplication(manifestPath);
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
      "recipe_id": "architectural_plan_section_a4_v1",
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
