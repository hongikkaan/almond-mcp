using System;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

var viewport = new RhinoViewport();
var view = new RhinoView(viewport);
var doc = new RhinoDoc();
RhinoDoc.ActiveDoc = doc;
doc.Views.ActiveView = view;
JObject Run(string input) => ViewManipulation.Handle(doc, JObject.Parse(input));
void Require(bool ok, string detail) { if (!ok) throw new Exception(detail); }
bool Near(double x, double y) => Math.Abs(x-y) < 1e-8;

Require((string)Run("""{"operation":"rotate","mode":"look","pitch_deg":90}""")["status"] == "error"
    && viewport.Applies == 0, "vertical result mutated");
var mismatch = Run("""{"operation":"zoom","factor":2,"expected_viewport_id":"57af96db-6b1b-4c02-90a1-232136da5818"}""");
Require((string)mismatch["error_code"] == "viewport_mismatch" && viewport.Applies == 0, "viewport identity not enforced");
RhinoDoc.ActiveDoc = new RhinoDoc();
Require((string)Run("""{"operation":"zoom","factor":2}""")["status"] == "error" && viewport.Applies == 0, "inactive document mutated");
RhinoDoc.ActiveDoc = doc;
doc.Views.ActiveView = new RhinoPageView(viewport);
Require((string)Run("""{"operation":"zoom","factor":2}""")["status"] == "error" && viewport.Applies == 0, "layout mutated");
doc.Views.ActiveView = view;
viewport.IsTwoPointPerspectiveProjection = true;
Require((string)Run("""{"operation":"zoom","factor":2}""")["status"] == "error" && viewport.Applies == 0, "two-point view mutated");
viewport.IsTwoPointPerspectiveProjection = false;
doc.UndoRecordingIsActive = true;
Require((string)Run("""{"operation":"zoom","factor":2}""")["status"] == "error" && viewport.Applies == 0, "undo command accepted");
doc.UndoRecordingIsActive = false;

var look = Run("""{"operation":"rotate","mode":"look","yaw_deg":45,"pitch_deg":30}""");
Require((bool)look["mutation_applied"] && viewport.CameraLocation == new Point3d(0,0,0)
    && viewport.CameraDirection.X > 0 && viewport.CameraDirection.Y > 0 && Near(viewport.CameraDirection.Z,0.5), "look pose");
viewport.Reset();
var orbit = Run("""{"operation":"rotate","mode":"orbit","yaw_deg":45,"pitch_deg":30}""");
Require((bool)orbit["mutation_applied"] && viewport.CameraTarget == new Point3d(0,10,0)
    && viewport.CameraLocation.X > 0 && viewport.CameraLocation.Z > 0
    && Near(viewport.CameraLocation.DistanceTo(viewport.CameraTarget),10), "orbit pose");

var center = viewport.CameraTarget;
var location = viewport.CameraLocation;
var zoom = Run("""{"operation":"zoom","factor":2}""");
Require((bool)zoom["mutation_applied"] && viewport.CameraTarget == center && viewport.CameraLocation == location
    && viewport.Frustum[0] == -2.5 && viewport.Frustum[1] == 0.5 && viewport.Frustum[4] == 1 && viewport.Frustum[5] == 100,
    "optical zoom did not preserve pose and clipping");
Require((bool)Run("""{"operation":"zoom","factor":0.5}""")["mutation_applied"] && viewport.Frustum[0] == -4, "reciprocal zoom");
Require(!(bool)Run("""{"operation":"zoom","factor":1}""")["mutation_applied"], "identity mutated");

viewport.CorruptNext = true;
var verifiedRollback = Run("""{"operation":"zoom","factor":2}""");
Require((string)verifiedRollback["status"] == "error" && !(bool)verifiedRollback["mutation_applied"]
    && !(bool)verifiedRollback["requires_reconciliation"] && viewport.Frustum[0] == -4, "failed verification did not restore");
viewport.CorruptNext = true;
view.AfterRedraw = () => doc.Views.ActiveView = new RhinoView(new RhinoViewport());
var unknown = Run("""{"operation":"zoom","factor":2}""");
Require((string)unknown["status"] == "error" && unknown["mutation_applied"].Type == JTokenType.Null
    && (bool)unknown["requires_reconciliation"], "rollback should not touch an inactive viewport");
Console.WriteLine("""{"verified":true}""");

namespace RhinoAlmondBridge
{
    static class ObjectObservation { public static void ValidateDocument(RhinoDoc document, JObject request) {} }
}
namespace Rhino
{
    class RhinoDoc
    {
        static uint nextSerial;
        public static RhinoDoc ActiveDoc;
        public uint RuntimeSerialNumber { get; } = ++nextSerial;
        public bool IsHeadless, UndoRecordingIsActive, UndoActive, RedoActive;
        public ViewTable Views { get; } = new();
    }
    class ViewTable { public RhinoView ActiveView; }
}
namespace Rhino.Commands
{
    static class Command { public static bool InCommand() => false; }
}
namespace Rhino.Display
{
    class RhinoView(RhinoViewport viewport)
    {
        public RhinoViewport ActiveViewport => viewport;
        public Action AfterRedraw;
        public void Redraw() => AfterRedraw?.Invoke();
    }
    class RhinoPageView(RhinoViewport viewport) : RhinoView(viewport) {}
    class RhinoViewport
    {
        public Guid Id { get; } = Guid.NewGuid();
        public bool IsPerspectiveProjection = true, IsTwoPointPerspectiveProjection, CorruptNext;
        public int Applies;
        public Point3d CameraLocation = new(0,0,0), CameraTarget = new(0,10,0);
        public Vector3d CameraDirection = new(0,1,0), CameraUp = new(0,0,1);
        public double[] Frustum = [-4,2,-2,2,1,100];
        public void Reset() { CameraLocation = new(0,0,0); CameraTarget = new(0,10,0); CameraDirection = new(0,1,0); CameraUp = new(0,0,1); }
        public bool GetFrustum(out double l,out double r,out double b,out double t,out double n,out double f)
        { l=Frustum[0]; r=Frustum[1]; b=Frustum[2]; t=Frustum[3]; n=Frustum[4]; f=Frustum[5]; return true; }
        public bool SetViewProjection(ViewportInfo plan, bool updateTarget)
        {
            Applies++;
            CameraLocation=plan.Location; CameraDirection=plan.Direction; CameraUp=plan.Up; Frustum=(double[])plan.Frustum.Clone();
            if (updateTarget) throw new Exception("target changed implicitly");
            if (CorruptNext) { Frustum[0] -= 1; CorruptNext = false; }
            return true;
        }
        public void SetCameraTarget(Point3d target, bool updateLocation)
        { if (updateLocation) throw new Exception("camera location changed implicitly"); CameraTarget=target; }
    }
}
namespace Rhino.DocObjects
{
    class ViewportInfo(RhinoViewport viewport)
    {
        public Point3d Location=viewport.CameraLocation;
        public Vector3d Direction=viewport.CameraDirection, Up=viewport.CameraUp;
        public double[] Frustum=(double[])viewport.Frustum.Clone();
        public bool SetCameraLocation(Point3d value) { Location=value; return true; }
        public bool SetCameraDirection(Vector3d value) { Direction=value; return true; }
        public bool SetCameraUp(Vector3d value) { Up=value; return true; }
        public bool SetFrustum(double l,double r,double b,double t,double n,double f) { Frustum=[l,r,b,t,n,f]; return true; }
    }
}
namespace Rhino.Geometry
{
    readonly record struct Point3d(double X,double Y,double Z)
    {
        public bool IsValid => double.IsFinite(X) && double.IsFinite(Y) && double.IsFinite(Z);
        public double DistanceTo(Point3d other) => (this-other).Length;
        public static Point3d operator +(Point3d a,Vector3d b) => new(a.X+b.X,a.Y+b.Y,a.Z+b.Z);
        public static Vector3d operator -(Point3d a,Point3d b) => new(a.X-b.X,a.Y-b.Y,a.Z-b.Z);
    }
    readonly record struct Vector3d(double X,double Y,double Z)
    {
        public bool IsValid => double.IsFinite(X) && double.IsFinite(Y) && double.IsFinite(Z);
        public double Length => Math.Sqrt(X*X+Y*Y+Z*Z);
        public static Vector3d CrossProduct(Vector3d a,Vector3d b) => new(a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X);
        public static Vector3d operator +(Vector3d a,Vector3d b) => new(a.X+b.X,a.Y+b.Y,a.Z+b.Z);
        public static Vector3d operator -(Vector3d a,Vector3d b) => new(a.X-b.X,a.Y-b.Y,a.Z-b.Z);
        public static Vector3d operator *(Vector3d a,double s) => new(a.X*s,a.Y*s,a.Z*s);
    }
}
