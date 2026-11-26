namespace Rhino
{
    public enum UnitSystem { Meters, Centimeters, Millimeters }
    public static class RhinoMath { public static double UnitScale(UnitSystem a, UnitSystem b) => 1; }
    public sealed class RhinoDoc
    {
        public static RhinoDoc ActiveDoc;
        public UnitSystem ModelUnitSystem => UnitSystem.Millimeters;
        public Objects Objects { get; } = new();
        public Views Views { get; } = new();
        public bool UndoSucceeds { get; init; }
        public bool UndoRecordingIsActive { get; private set; }
        public bool UndoActive => false;
        public bool RedoActive => false;
        public uint CurrentUndoRecordSerialNumber { get; private set; }
        public uint NextUndoRecordSerialNumber { get; private set; } = 1;
        int initialCount;

        public uint BeginUndoRecord(string name)
        {
            initialCount = Objects.Count;
            UndoRecordingIsActive = true;
            return CurrentUndoRecordSerialNumber = NextUndoRecordSerialNumber++;
        }

        public bool EndUndoRecord(uint serial)
        {
            if (!UndoRecordingIsActive || serial != CurrentUndoRecordSerialNumber)
            {
                return false;
            }

            UndoRecordingIsActive = false;
            if (Objects.Count == initialCount)
            {
                Commands.Command.Purge(serial);
            }

            return true;
        }

        public bool Undo()
        {
            if (!UndoSucceeds)
            {
                return false;
            }

            Objects.RemoveRange(initialCount, Objects.Count - initialCount);
            return true;
        }

        public void ClearRedoRecords() { }
    }
    public sealed class Objects : List<Guid>
    {
        public int FailOnAdd { get; set; } = -1;
        int attempts;

        public RhinoObject FindId(Guid id) => null;
        Guid AddGeometry()
        {
            if (++attempts == FailOnAdd)
            {
                return Guid.Empty;
            }

            var id = Guid.NewGuid();
            Add(id);
            return id;
        }
        public Guid AddCurve(Geometry.Curve value) => AddGeometry();
        public Guid AddMesh(Geometry.Mesh value) => AddGeometry();
        public Guid AddBrep(Geometry.Brep value) => AddGeometry();
        public Guid AddPoint(Geometry.Point3d value) => AddGeometry();
    }
    public sealed class RhinoObject { public Geometry.GeometryBase Geometry; }
    public sealed class Views { public void Redraw() { } }
}
namespace Rhino.Commands
{
    public sealed class UndoRedoEventArgs : EventArgs { public uint UndoSerialNumber; public bool IsPurgeRecord; }
    public class Command
    {
        public static event EventHandler<UndoRedoEventArgs> UndoRedo;
        public static void Purge(uint serial) => UndoRedo?.Invoke(null, new() { UndoSerialNumber = serial, IsPurgeRecord = true });
    }
}
namespace Rhino.Geometry
{
    public class GeometryBase { public virtual GeometryBase Duplicate() => this; public void Transform(Transform transform) { } }
    public class Curve : GeometryBase { public Curve DuplicateCurve() => new(); }
    public class Mesh : GeometryBase { public Mesh DuplicateMesh() => new(); public static Mesh[] CreateFromBrep(Brep b, MeshingParameters m) => []; public void Append(Mesh m) { } }
    public class Brep : GeometryBase { public Curve[] Edges => []; public Brep DuplicateBrep() => new(); }
    public class Extrusion : GeometryBase { public Brep ToBrep() => new(); }
    public class Point : GeometryBase { public Point3d Location; }
    public struct Point3d { public double X, Y, Z; public Point3d(double x,double y,double z) { X=x;Y=y;Z=z; } public static Point3d Origin => new(); public static Point3d Unset => new(); }
    public struct Transform { public static Transform Scale(Point3d p, double scale) => new(); }
    public class MeshingParameters { public static MeshingParameters FastRenderMesh => new(); }
}
namespace Grasshopper.Kernel.Types
{
    public interface IGH_Goo { }
    public record GH_Number(double Value) : IGH_Goo;
    public record GH_Integer(int Value) : IGH_Goo;
    public record GH_String(string Value) : IGH_Goo;
    public record GH_Boolean(bool Value) : IGH_Goo;
    public record GH_Point(Rhino.Geometry.Point3d Value) : IGH_Goo;
    public record GH_Curve(Rhino.Geometry.Curve Value) : IGH_Goo;
    public record GH_Mesh(Rhino.Geometry.Mesh Value) : IGH_Goo;
    public record GH_Brep(Rhino.Geometry.Brep Value) : IGH_Goo;
}
namespace Grasshopper.Kernel.Data { public sealed record GH_Path(int Path); }
namespace Grasshopper.Kernel
{
    using Grasshopper.Kernel.Types;
    using Rhino.Geometry;
    public interface IGH_DocumentObject { string NickName { get; } }
    public interface IGH_Param : IGH_DocumentObject
    {
        VolatileTree VolatileData { get; }
        void ExpireSolution(bool recompute);
        void ClearData();
        void AddVolatileDataList(Grasshopper.Kernel.Data.GH_Path path, List<IGH_Goo> goos);
    }
    public interface IGH_ActiveObject { IEnumerable<string> RuntimeMessages(GH_RuntimeMessageLevel level); }
    public enum GH_RuntimeMessageLevel { Error, Warning }
    public enum GH_SolutionMode { Silent }
    public enum GH_Conversion { Both }
    public sealed class VolatileTree { public List<IGH_Goo> Items = new(); public bool IsEmpty => Items.Count == 0; public IEnumerable<IGH_Goo> AllData(bool skip) => Items; }
    public sealed class GH_DocumentIO { public static GH_Document Next; public bool Open(string path) => true; public GH_Document Document => Next; }
    public sealed class GH_Document : IDisposable
    {
        public List<IGH_DocumentObject> Objects = new();
        public bool Enabled;
        public void RequestAbortSolution() { }
        public void NewSolution(bool recompute, GH_SolutionMode mode) { }
        public void Dispose() { }
    }
    public static class GH_Convert
    {
        public static bool ToDouble(IGH_Goo goo, out double value, GH_Conversion mode) { value = goo is GH_Number n ? n.Value : 0; return goo is GH_Number; }
        public static bool ToInt32(IGH_Goo goo, out int value, GH_Conversion mode) { value = goo is GH_Integer n ? n.Value : 0; return goo is GH_Integer; }
        public static bool ToString(IGH_Goo goo, out string value, GH_Conversion mode) { value = goo.ToString(); return true; }
        public static bool ToBoolean(IGH_Goo goo, out bool value, GH_Conversion mode) { value = goo is GH_Boolean n && n.Value; return goo is GH_Boolean; }
        public static bool ToPoint3d(IGH_Goo goo, ref Point3d value, GH_Conversion mode) { if (goo is not GH_Point n) return false; value = n.Value; return true; }
        public static bool ToCurve(IGH_Goo goo, ref Curve value, GH_Conversion mode) { if (goo is not GH_Curve n) return false; value = n.Value; return true; }
        public static bool ToMesh(IGH_Goo goo, ref Mesh value, GH_Conversion mode) { if (goo is not GH_Mesh n) return false; value = n.Value; return true; }
        public static bool ToBrep(IGH_Goo goo, ref Brep value, GH_Conversion mode) { if (goo is not GH_Brep n) return false; value = n.Value; return true; }
    }
}
