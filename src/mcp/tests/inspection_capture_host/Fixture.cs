using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

class Program
{
    static void Main(string[] args)
    {
        var scenario = JObject.Parse(args[0]);
        Bitmap.Raster = Convert.FromBase64String((string)scenario["raster"]);
        var doc = RhinoDoc.ActiveDoc;
        doc.OnCapture = (string)scenario["change"] switch {
            "hide_visible" => () => doc.Objects.First(o => o.Visible).Visible = false,
            "remove_hidden" => () => doc.Objects.RemoveAll(o => !o.Visible),
            "mark_modified" => () => doc.Modified = true,
            _ => () => { }
        };
        var response = InspectionCapture.Handle(doc, (JObject)scenario["request"]);
        Console.WriteLine(new JObject { ["response"] = response, ["scans"] = doc.Scans }.ToString(Formatting.None));
    }
}

class RhinoDoc
{
    public static readonly RhinoDoc ActiveDoc = new RhinoDoc();
    public readonly ViewTable Views = new ViewTable();
    public readonly List<RhinoObject> Objects = new List<RhinoObject> {
        new RhinoObject { Id = Guid.Parse("00000000-0000-0000-0000-000000000001") },
        new InstanceObject { Id = Guid.Parse("00000000-0000-0000-0000-000000000002") },
        new InstanceObject { Id = Guid.Parse("00000000-0000-0000-0000-000000000003"), Visible = false }
    };
    public Action OnCapture;
    public int Scans;
    public bool IsHeadless => false;
    public uint RuntimeSerialNumber => 1;
    public string Path => @"C:\offline\inspection.3dm";
    public string ActiveSpace => "ModelSpace";
    public bool Modified { get; set; }
}
enum ViewTypeFilter { Model }
class ViewTable
{
    public readonly RhinoView ActiveView = new RhinoView();
    public RhinoView[] GetViewList(ViewTypeFilter filter) => new[] { ActiveView };
}
class RhinoView
{
    public readonly RhinoViewport MainViewport = new RhinoViewport();
    public RhinoViewport ActiveViewport => MainViewport;
    public uint RuntimeSerialNumber => 2;
}
class RhinoPageView : RhinoView { }
class RhinoViewport
{
    public readonly Guid Id = Guid.NewGuid();
    public readonly DisplayMode DisplayMode = new DisplayMode();
}
class DisplayMode { public readonly Attributes DisplayAttributes = new Attributes(); }
class Attributes { public Guid RealtimeDisplayId => Guid.Empty; }
class RhinoObject
{
    public Guid Id { get; init; }
    public bool Visible { get; set; } = true;
    public Geometry Geometry => new Geometry();
}
class InstanceObject : RhinoObject { }
class Geometry { public BoundingBox GetBoundingBox(bool accurate) => new BoundingBox(); }
struct BoundingBox
{
    public static BoundingBox Empty => new BoundingBox();
    public bool IsValid => true;
    public void Union(BoundingBox other) { }
}
static class ObjectObservation
{
    public static void ValidateDocument(RhinoDoc doc, JObject request) { }
    public static Guid[] ReadIds(JToken token, int max, bool required) =>
        token == null ? Array.Empty<Guid>() : token.Values<string>().Select(Guid.Parse).ToArray();
    public static RhinoObject[] ModelObjects(RhinoDoc doc)
    {
        doc.Scans++;
        return doc.Objects.ToArray();
    }
    public static string SnapshotToken(RhinoDoc doc, JObject scope, RhinoObject[] model, JObject editor) =>
        String.Join(",", model.Select(o => o.Id));
}
static class DocumentObservation
{
    public const int MaxImageBytes = 4 * 1024 * 1024;
}
static class DisplayModeMenu
{
    public static DisplayMode Resolve(string name) => null;
}
class EditingContext
{
    public readonly JObject State = new JObject();
    public static EditingContext ObserveObjects(RhinoDoc doc) => new EditingContext();
    public static bool CanObserve(JObject editor) => true;
}
// Fixed raster supplied by the test. Drawing these pixels exercises no viewport or Rhino SDK.
enum PixelFormat { Format24bppRgb }
enum ImageFormat { Png }
class Bitmap : IDisposable
{
    public static byte[] Raster;
    public int Width { get; }
    public int Height { get; }
    public Bitmap(int width, int height, PixelFormat format) { Width = width; Height = height; }
    public void Save(Stream stream, ImageFormat format) => stream.Write(Raster);
    public void Dispose() { }
}
class Graphics : IDisposable
{
    public static Graphics FromImage(Bitmap bitmap) => new Graphics();
    public void Clear(Color color) { }
    public void DrawImageUnscaled(Bitmap bitmap, int x, int y) { }
    public void Dispose() { }
}
static class InspectionCapture
{
    static JObject ViewState(RhinoViewport view) => new JObject();
    static HashSet<Guid> Selected(RhinoDoc doc) => new HashSet<Guid>();
    static void DrawCaption(Graphics graphics, Rectangle rectangle, JObject tile) { }
    static Bitmap Capture(RhinoDoc doc, RhinoViewport source, RhinoObject[] objects, BoundingBox bounds,
        string direction, DisplayMode mode, Size size, bool explicitFilter, bool frameObjects, JObject metadata)
    {
        doc.OnCapture();
        return new Bitmap(size.Width, size.Height, PixelFormat.Format24bppRgb);
    }

    // CAPTURE_HANDLER
}
