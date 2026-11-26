using Newtonsoft.Json.Linq;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    internal static class GeometryJson
    {
        // Keep model-space coordinates in XYZ order without remapping their values.
        internal static JArray Point(Point3d point) => new JArray(point.X, point.Y, point.Z);
    }
}
