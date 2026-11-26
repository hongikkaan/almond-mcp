using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;
using RhinoAlmondBridge;

var root = Directory.CreateDirectory(Path.GetFullPath(args.Single())).FullName;
var manifestPath = Path.Combine(root, "stairs.capsule.json");
File.WriteAllText(Path.Combine(root, "stairs.ghx"), "Fixture with two curve outputs.");
var manifest = new CapsuleManifest
{
    CapsuleId = "stairs",
    DefinitionFile = "stairs.ghx",
    Audited = true,
    Outputs = new()
    {
        new() { Name = "ALMOND_OUT_STRINGER", Type = "curve[]" },
        new() { Name = "ALMOND_OUT_HANDRAIL", Type = "curve[]" }
    }
};
File.WriteAllText(manifestPath, JsonConvert.SerializeObject(manifest));
var runner = new GhDefinitionRunner(root, root);

// The handrail fails to bake after the stringer has been added. The user's model already has a curve.
var (original, existing, rolledBack) = RunFailedBake(Recovery.Available);
Require(rolledBack.Status == "error" && rolledBack.MutationState == "rolled_back" &&
    rolledBack.BakedGuids.Count == 0 && original.Objects.SequenceEqual(new[] { existing }),
    "Failed capsule bake did not restore the model's original geometry.");

var (repair, prior, uncertain) = RunFailedBake(Recovery.Unavailable);
var retained = repair.Objects.Where(id => id != prior).Select(id => id.ToString());
Require(uncertain.Status == "error" && uncertain.MutationState == "unknown" &&
    uncertain.RequiresReconciliation && repair.Objects.Contains(prior) &&
    uncertain.BakedGuids.Count == 1 && uncertain.BakedGuids.SequenceEqual(retained),
    "A failed recovery did not identify the exact geometry retained in the document.");
Console.WriteLine("PASS: partial Grasshopper bake preserves prior geometry and reports retained additions");

(RhinoDoc Doc, Guid Existing, DefinitionRunResult Result) RunFailedBake(Recovery recovery)
{
    GH_DocumentIO.Next = new GH_Document
    {
        Objects = new() { new Output("ALMOND_OUT_STRINGER"), new Output("ALMOND_OUT_HANDRAIL") }
    };
    var doc = new RhinoDoc { UndoSucceeds = recovery == Recovery.Available };
    RhinoDoc.ActiveDoc = doc;
    var existing = doc.Objects.AddCurve(new Curve());
    doc.Objects.FailOnAdd = 3;
    return (doc, existing, runner.Run(manifestPath, new JObject(), 60, null));
}

static void Require(bool condition, string detail)
{
    if (!condition)
    {
        throw new InvalidOperationException(detail);
    }
}

enum Recovery { Available, Unavailable }

sealed class Output(string name) : IGH_Param
{
    public string NickName => name;
    public VolatileTree VolatileData { get; } = new() { Items = new() { new GH_Curve(new Curve()) } };

    public void ExpireSolution(bool recompute) { }
    public void ClearData() { }
    public void AddVolatileDataList(Grasshopper.Kernel.Data.GH_Path path, List<IGH_Goo> goos) { }
}
