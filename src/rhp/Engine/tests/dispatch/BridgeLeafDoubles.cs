using Newtonsoft.Json.Linq;
using Rhino;

namespace RhinoAlmondBridge;

// Inert Rhino-facing leaf adapters; the entire production BridgeServer switch and context checks are compiled.
static class Leaf
{
    internal static RhinoDoc? Document;
    internal static Action? OnObservation;
    internal static JObject Observe(RhinoDoc doc, JObject request) { Document = doc; OnObservation?.Invoke(); return request; }
}
static class DocumentObservation
{
    internal static string HandleContext(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value).ToString(Newtonsoft.Json.Formatting.None);
    internal static string HandleViewportImage(RhinoDoc doc,JObject value) => HandleContext(doc,value);
}
static class ViewCaptureTools { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class ObjectObservation { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class InspectionCapture { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class PlanarFaceEditing { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); internal static JObject HandleBatch(RhinoDoc doc,JObject value) => Handle(doc,value); }
static class PlanSectionTool { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class StepTempCleanup { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class IntersectionTools { internal static JObject PreviewHandle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); internal static JObject ResolveHandle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class IntersectionReview { internal static JObject Capture(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class DocumentSave { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class BlockAnalysis { internal static JObject Analyze(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class ComponentRegistry { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class ComponentOperations { internal static JObject Handle(RhinoDoc doc,JObject value) => Leaf.Observe(doc,value); }
static class DrawingAssetGeometry { internal static JObject Handle(JObject value) => value; }
sealed class FurniturePlacementRequest { }
sealed class FurnitureAssetManager
{
    internal FurnitureAssetManager(string a,string b,string c,string d,string e,string[] f) { }
    internal object Place(RhinoDoc doc,FurniturePlacementRequest value) => new { };
    internal object ImportHatchPatterns(RhinoDoc doc,string value) => new { };
}
sealed class DrawingStyleRequest { }
sealed class DrawingStyleManager { internal object Apply(RhinoDoc doc,DrawingStyleRequest value) => new { }; }
sealed class GlbExportRequest { }
sealed class GlbExporter { internal object Export(RhinoDoc doc,GlbExportRequest value) => new { }; }
sealed class ValidationRequest { }
sealed class ValidationResult { public string Status = "ok", Verdict = "fixture"; }
sealed class StructuralValidator { internal StructuralValidator(string a,string b) { } internal ValidationResult Validate(RhinoDoc doc,ValidationRequest value) => new(); }
static class StructureModelExport { internal static string Handle(RhinoDoc doc,JObject value) => DocumentObservation.HandleContext(doc,value); }
static class AssetPlacementExport { internal static string Handle(RhinoDoc doc,JObject value) => DocumentObservation.HandleContext(doc,value); }
static class StructureView { internal static string Handle(RhinoDoc doc,JObject value) => DocumentObservation.HandleContext(doc,value); internal static string HandleDraw(RhinoDoc doc,JObject value) => Handle(doc,value); }
sealed class ScriptExecutor { internal object Execute(string value,RhinoDoc doc) => new { }; }
sealed class ManagedFiles : IDisposable { internal static IDisposable Bind(RhinoDoc doc,string a,string b) => new ManagedFiles(); public void Dispose() { } }
sealed class Manifest { public string Confidence = "template", CapsuleId = "fixture"; }
sealed class RunResult
{
    public string Status = "ok", CapsuleId = "fixture", Error = "", MutationState = "none";
    public Dictionary<string,object> Outputs = new(); public List<string> BakedGuids = new(), Warnings = new(); public bool RequiresReconciliation;
}
sealed class GhDefinitionRunner
{
    internal GhDefinitionRunner(string a,string b) { }
    internal string FindManifestPath(string id) => "fixture";
    internal static Manifest LoadManifest(string path,out string error) { error = ""; return new(); }
    internal RunResult Run(RhinoDoc doc,string path,JObject input,double timeout,int? seed) => new();
}
