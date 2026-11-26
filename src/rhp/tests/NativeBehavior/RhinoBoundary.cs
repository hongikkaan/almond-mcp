namespace Rhino
{
    public sealed class RhinoDoc
    {
        public static RhinoDoc? ActiveDoc { get; set; }
        public required string Path { get; init; }
        public required uint RuntimeSerialNumber { get; init; }
        public bool Changed { get; set; }
    }

    public static class RhinoApp
    {
        public static void InvokeOnUiThread(Action action) => action();
        public static void WriteLine(string value) { }
    }
}

namespace Rhino.PlugIns
{
    public class PlugIn
    {
        public static PlugIn? Loaded { get; set; }
        public static PlugIn? Find(Guid id) =>
            id == new Guid("c337dbb8-394a-4593-9c2b-a3d7cfc91893") ? Loaded : null;
    }
}
