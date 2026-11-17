using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;
using RhinoAlmondBridge;

string root = Path.GetFullPath(args.Single());
Directory.CreateDirectory(root);
string manifest = Path.Combine(root, "fixture.capsule.json");
File.WriteAllText(Path.Combine(root, "fixture.ghx"), "fixture path only");
File.WriteAllText(manifest, JsonConvert.SerializeObject(new CapsuleManifest {
    CapsuleId = "fixture", DefinitionFile = "fixture.ghx", Audited = true,
    Outputs = new() { new() { Name = "ALMOND_OUT_FIRST", Type = "curve[]" }, new() { Name = "ALMOND_OUT_SECOND", Type = "curve[]" } }
}));
var runner = new GhDefinitionRunner(root, root);

RhinoDoc Document() { var doc = new RhinoDoc(); doc.Objects.AddCurve(new Curve()); RhinoDoc.ActiveDoc = doc; return doc; }
GH_Document Definition(bool complete = true) => GH_DocumentIO.Next = new GH_Document {
    Objects = complete ? new() { Port("ALMOND_OUT_FIRST"), Port("ALMOND_OUT_SECOND") } : new() { Port("ALMOND_OUT_FIRST") }
};
Param Port(string name) => new() { NickName = name, VolatileData = new() { Items = new() { new GH_Curve(new Curve()) } } };
Definition(); var noUndo = Document(); noUndo.AllowUndo = false;
var denied = runner.Run(manifest, new JObject(), 60, null);
Require(denied.Status == "error" && denied.MutationState == "none" && noUndo.Objects.Count == 1, "Undo denial allowed a bake");
Definition(); var commandOwned = Document(); uint commandRecord = commandOwned.BeginUndoRecord("Existing Rhino command"); commandOwned.AllowUndo = false;
var commandDenied = runner.Run(manifest, new JObject(), 60, null);
Require(commandDenied.Status == "error" && commandDenied.MutationState == "none" && commandOwned.UndoRecordingIsActive &&
    commandOwned.CurrentUndoRecordSerialNumber == commandRecord && commandOwned.Undos == 0,
    "Modeless capsule execution ended or undid the command owner's record");

Definition(false); var missing = Document();
var broken = runner.Run(manifest, new JObject(), 60, null);
Require(broken.Status == "error" && broken.BakedGuids.Count == 0 && missing.Objects.Count == 1 && missing.Begins == 0,
    "Missing second output was detected only after the first geometry was baked");

Definition(); var partial = Document(); partial.Objects.FailOnAdd = 3;
var rollback = runner.Run(manifest, new JObject(), 60, null);
Require(rollback.Status == "error" && rollback.MutationState == "rolled_back" && !rollback.RequiresReconciliation &&
    rollback.BakedGuids.Count == 0 && partial.Objects.Count == 1 && partial.Undos == 1,
    "Partial bake failure did not roll back only its own record");

Definition(); var unknown = Document(); unknown.Objects.FailOnAdd = 3; unknown.UndoSucceeds = false;
var uncertain = runner.Run(manifest, new JObject(), 60, null);
Require(uncertain.Status == "error" && uncertain.MutationState == "unknown" && uncertain.RequiresReconciliation &&
    uncertain.BakedGuids.Count == 1 && unknown.Objects.Count == 2, "Failed rollback hid retained geometry evidence");

var switchedDefinition = Definition(); var original = Document();
switchedDefinition.OnSolve = () => RhinoDoc.ActiveDoc = new RhinoDoc();
var switched = runner.Run(original, manifest, new JObject(), 60, null);
Require(switched.Status == "error" && original.Objects.Count == 1 && RhinoDoc.ActiveDoc.Objects.Count == 0,
    "Document switch during solve baked into another document");

Definition(); var success = Document();
var ok = runner.Run(manifest, new JObject(), 60, null);
Require(ok.Status == "ok" && ok.MutationState == "completed" && ok.BakedGuids.Count == 2 && success.Objects.Count == 3 && !success.UndoRecordingIsActive,
    "Successful two-output bake lost a single owned Undo record");
Console.WriteLine("PASS: production GH output preflight, Undo denial, partial rollback, uncertain evidence, document switch and success");
static void Require(bool value, string message) { if (!value) throw new Exception(message); }

sealed class Param : IGH_Param
{
    public string NickName { get; set; }
    public VolatileTree VolatileData { get; set; }
    public void ExpireSolution(bool recompute) { }
    public void ClearData() { }
    public void AddVolatileDataList(Grasshopper.Kernel.Data.GH_Path path, List<IGH_Goo> goos) { }
}
