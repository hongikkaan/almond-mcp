using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;

namespace Rhino
{
    public enum UnitSystem { None, CustomUnits, Millimeters }
    public sealed class RhinoDoc
    {
        public static RhinoDoc ActiveDoc;
        public uint RuntimeSerialNumber;
        public string Path;
        public UnitSystem ModelUnitSystem = UnitSystem.Millimeters;
        public double ModelAbsoluteTolerance = .01;
        public Objects Objects = new(); public Views Views = new();
        public int InCommand(bool ignore) => 0;
    }
    public sealed class Objects
    {
        public List<DocObjects.RhinoObject> Items = new();
        public IEnumerable<DocObjects.RhinoObject> GetSelectedObjects(bool a,bool b) => Items;
        public DocObjects.RhinoObject FindId(Guid id) => Items.SingleOrDefault(x => x.Id == id);
        public void UnselectAll() { } public void Select(Guid id) { }
    }
    public sealed class Views { public void Redraw() { } }
    public static class RhinoApp { public static bool RunScript(string command,bool echo) { RhinoAlmondBridge.AnalysisWorkspace.Run(RhinoDoc.ActiveDoc); return true; } }
}
namespace Rhino.Commands
{
    public enum Result { Cancel, Success }
    public enum RunMode { Interactive }
    public abstract class Command { public abstract string EnglishName { get; } protected abstract Result RunCommand(RhinoDoc doc,RunMode mode); }
}
namespace Rhino.DocObjects
{
    [Flags] public enum ObjectType { Curve=1, Surface=2, Brep=4, Mesh=8, Point=16 }
    public sealed class RhinoObject { public Guid Id = Guid.NewGuid(); public GeometryBase Geometry = new Curve(); public Attributes Attributes = new(); }
    public sealed class Attributes
    {
        public uint Revision; public string Name = "fixture"; public int LayerIndex;
        public System.Collections.Specialized.NameValueCollection GetUserStrings() => new() { ["fixture_revision"] = Revision.ToString() };
    }
}
namespace Rhino.Geometry
{
    public class GeometryBase : IDisposable { public uint Revision; public uint DataCRC(uint seed) => Revision; public void Dispose() { } }
    public class Curve : GeometryBase { public bool TryGetPolyline(out Polyline p) { p = new(); return false; } public double[] DivideByCount(int n,bool b) => []; public Point3d PointAt(double t) => new(); }
    public class InstanceReferenceGeometry : GeometryBase { }
    public class Mesh : GeometryBase { public List<int> Faces = new(); public Polyline[] GetNakedEdges() => []; }
    public class Brep : GeometryBase { public List<int> Faces = new(); }
    public class Polyline : List<Point3d> { }
    public struct Point3d { public double X,Y,Z; }
}
namespace Rhino.Input { public enum GetResult { Object } }
namespace Rhino.Input.Custom
{
    public sealed class GetObject : IDisposable
    {
        public Rhino.DocObjects.ObjectType GeometryFilter; public bool SubObjectSelect;
        public void SetCommandPrompt(string text) { } public Rhino.Input.GetResult GetMultiple(int min,int max) => Rhino.Input.GetResult.Object;
        public ObjRef[] Objects() => []; public void Dispose() { }
    }
    public sealed class ObjRef { public Rhino.DocObjects.RhinoObject Object() => null; }
}
namespace Rhino.UI { public static class RhinoEtoApp { public static object MainWindow => null; } }
namespace Eto.Forms
{
    public sealed class Application
    {
        public static Application Instance = new();
        readonly System.Threading.Channels.Channel<Action> queue = System.Threading.Channels.Channel.CreateUnbounded<Action>();
        public void AsyncInvoke(Action action) => queue.Writer.TryWrite(action);
        public async Task RunNext() => (await queue.Reader.ReadAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(5)))();
    }
    public enum DialogResult { Ok, Cancel }
    public sealed class SaveFileDialog { public string Title,FileName; public List<FileFilter> Filters = new(); public DialogResult ShowDialog(object window) => DialogResult.Cancel; }
    public sealed class FileFilter { public FileFilter(string name,string ext) { } }
}
namespace RhinoAlmondBridge
{
    // Rhino-facing extraction and rendering adapters are inert; this fixture tests scheduling/identity, not structural maths.
    internal static class LibraryPlacement { internal static bool Busy; }
    internal static class AnalysisResults { internal static int Published; internal static void Publish(JObject report) => Published++; internal static void Open(RhinoDoc doc) { } }
    internal static class StructureView
    {
        internal static int Draws;
        internal static string Handle(RhinoDoc doc,JObject value) => "{}";
        internal static string HandleDraw(RhinoDoc doc,JObject value) { Draws++; return "{}"; }
    }
    internal static class StructureModelExport { internal static string Handle(RhinoDoc doc,JObject request) => "{\"status\":\"ok\"}"; }
    internal static class AssetPlacementExport { internal static string Handle(RhinoDoc doc,JObject request) => "{}"; }
    internal static class KarambaAdapter { internal static bool IsAvailable(out string reason) { reason="fixture";return false; } }
    internal static class NativeSolver
    {
        internal sealed class Command { internal string Label; }
        internal static Command Resolve(out string missing) { missing="fixture";return null; }
        internal static TaskCompletionSource<bool> Entered; internal static TaskCompletionSource<JObject> Reply;
        internal static void Reset() { Entered = new(TaskCreationOptions.RunContinuationsAsynchronously); Reply = new(TaskCreationOptions.RunContinuationsAsynchronously); }
        internal static Task<JObject> RunAsync(JObject request,int timeout) { Entered.SetResult(true);return Reply.Task; }
    }
    internal sealed class ValidationRequest
    {
        public List<string> Guids; public string StructureType,Material; public double LoadKN;
        public bool RequireKaramba,IncludeSelfWeight,FixedRotations,ExplicitSupports; public double? BeamDiameterMM,BeamWallMM;
    }
    internal sealed class StructuralValidator { internal StructuralValidator(string path) { } internal object Validate(RhinoDoc doc,ValidationRequest request) => new(); }
    internal sealed class ModelConditioner { internal Model Condition(RhinoDoc doc,List<string> ids) => new(); }
    internal sealed class Model { internal List<Beam> Beams = new(); internal List<Shell> Shells = new(); internal double UnitScaleToMeters=1; internal List<Point3d> AnchorPoints=new(); internal List<string> Warnings=new(); }
    internal sealed class Beam { internal Curve Axis; internal List<string> SourceGuids; internal Section Section; }
    internal sealed class Shell { internal Mesh Mesh; }
    internal sealed class Section { internal string Source; }
}
