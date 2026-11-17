using Newtonsoft.Json.Linq;
using Rhino;
using RhinoAlmondBridge;

foreach (string change in new[] { "none", "document", "geometry", "attributes", "closed", "renamed", "disposed" })
{
    var doc = new RhinoDoc { RuntimeSerialNumber = 17, Path = "fixture.3dm" };
    doc.Objects.Items.Add(new Rhino.DocObjects.RhinoObject());
    RhinoDoc.ActiveDoc = doc;
    var replies = new List<JObject>();
    var workspace = new AnalysisWorkspace(replies.Add);
    AnalysisResults.Published = 0; StructureView.Draws = 0; NativeSolver.Reset();
    workspace.Request("capture", "{}");
    await Eto.Forms.Application.Instance.RunNext();
    Require(replies.Any(value => (string)value["kind"] == "capture"), "Capture did not execute");
    workspace.Request("analyze", "{}");
    await Eto.Forms.Application.Instance.RunNext();
    await NativeSolver.Entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
    switch (change)
    {
        case "document": RhinoDoc.ActiveDoc = new RhinoDoc { RuntimeSerialNumber = 18, Path = doc.Path }; break;
        case "geometry": doc.Objects.Items[0].Geometry.Revision++; break;
        case "attributes": doc.Objects.Items[0].Attributes.Revision++; break;
        case "closed": RhinoDoc.ActiveDoc = null; break;
        case "renamed": doc.Path = "renamed.3dm"; break;
        case "disposed": workspace.Dispose(); break;
    }
    NativeSolver.Reply.SetResult(new JObject { ["validation"] = new JObject(), ["draw"] = new JObject() });
    await Eto.Forms.Application.Instance.RunNext();
    bool current = change == "none";
    Require(AnalysisResults.Published == (current ? 1 : 0) && StructureView.Draws == (current ? 1 : 0),
        "Async analysis applied a stale result after " + change);
    Require(!AnalysisWorkspace.Solving, "Solver ownership was retained after completion");
    if (!current && change != "disposed") Require(replies.Any(value => (string)value["kind"] == "error"), "Stale result was silently dropped");
}
// A document switch before Rhino starts the queued command must not capture the other document.
RhinoDoc.ActiveDoc = new RhinoDoc { RuntimeSerialNumber = 1 };
var queuedReplies = new List<JObject>();
new AnalysisWorkspace(queuedReplies.Add).Request("capture", "{}");
RhinoDoc.ActiveDoc = new RhinoDoc { RuntimeSerialNumber = 2 };
await Eto.Forms.Application.Instance.RunNext();
Require(queuedReplies.Single().Value<string>("kind") == "error", "Queued panel action targeted a later document");
Console.WriteLine("PASS: production analysis scheduling and async completion reject document, geometry, attributes, close and rename changes");
static void Require(bool value, string message) { if (!value) throw new Exception(message); }
