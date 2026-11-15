using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using RhinoAlmondBridge;

// Production manager with table doubles only: no Rhino process/document/native API.
namespace Rhino.DocObjects
{
    public class Linetype
    {
        public string Name; public int Index;
        public readonly List<(double Length, bool Solid)> Segments = new();
        public void AppendSegment(double length, bool solid) => Segments.Add((length, solid));
    }
    public class Layer
    {
        public Color Color, PlotColor; public double PlotWeight; public int LinetypeIndex;
        public void EnsurePrivateCopy() { }
    }
}
namespace Rhino
{
    public class LinetypeTable : List<DocObjects.Linetype>
    {
        public DocObjects.Linetype FindName(string name) => this.FirstOrDefault(v => string.Equals(v.Name, name, StringComparison.OrdinalIgnoreCase))
            ?? new DocObjects.Linetype { Name = "Continuous", Index = -1 };
        public new int Add(DocObjects.Linetype value) { value.Index = Count; base.Add(value); return value.Index; }
    }
    public class LayerTable : List<DocObjects.Layer>
    {
        public readonly Dictionary<string, int> Names = new();
        public bool Modify(DocObjects.Layer value, int index, bool quiet) { this[index] = value; return true; }
    }
    public class Views { public void Redraw() { } }
    public class RhinoDoc
    {
        public static RhinoDoc ActiveDoc;
        public readonly LinetypeTable Linetypes = new(); public readonly LayerTable Layers = new();
        public readonly Views Views = new(); public int UndoRecords;
        public uint BeginUndoRecord(string name) { UndoRecords++; return 1; }
        public void EndUndoRecord(uint number) { }
    }
}
namespace RhinoAlmondBridge
{
    static class DocumentLayers
    {
        public static int Ensure(Rhino.RhinoDoc doc, string path)
        {
            if (!doc.Layers.Names.TryGetValue(path, out var index))
            { index = doc.Layers.Count; doc.Layers.Add(new Rhino.DocObjects.Layer()); doc.Layers.Names[path] = index; }
            return index;
        }
    }
}
static class Program
{
    static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    static DrawingLayerSpecification Layer(string path, string name, double length) => new()
    { Path = path, Linetype = name, LinetypeSegments = new() {
        new() { Length = length, IsSolid = true }, new() { Length = 2, IsSolid = false } } };
    static void Main()
    {
        var doc = new Rhino.RhinoDoc(); var manager = new DrawingStyleManager();
        var existing = new Rhino.DocObjects.Linetype { Name = "Existing" };
        existing.AppendSegment(42, true); existing.AppendSegment(7, false);
        int retainedIndex = doc.Linetypes.Add(existing);
        // Existing objects/layers retain their index; another unrelated layer is untouched.
        int objectReference = retainedIndex;
        doc.Layers.Add(new Rhino.DocObjects.Layer { LinetypeIndex = retainedIndex });
        var request = new DrawingStyleRequest { Layers = new() { Layer("Draw::existing", "existing", 3), Layer("Draw::new", "New", 6) } };
        Check(manager.Apply(doc, request).Status == "success", "Different document definition must be reused.");
        Check(doc.Linetypes.Count == 2 && ReferenceEquals(existing, doc.Linetypes[0]), "No replacement/duplicate existing name.");
        Check(existing.Segments[0].Length == 42 && existing.Segments[1].Length == 7, "Existing segments unchanged.");
        Check(objectReference == 0 && doc.Layers[0].LinetypeIndex == 0 && doc.Layers[1].LinetypeIndex == 0, "Existing references preserved and reused.");
        Check(doc.Linetypes[1].Segments[0] == (6, true), "New name uses explicit profile segments.");
        Check(manager.Apply(doc, request).Status == "success" && doc.Linetypes.Count == 2 && doc.Layers.Count == 3, "Repeat is stable.");
        request.Layers[0].LinetypeSegments[0].Length = 42;
        request.Layers[0].LinetypeSegments[1].Length = 7;
        Check(manager.Apply(doc, request).Status == "success" && doc.Linetypes.Count == 2, "Same definition also reuses the name.");
        int before = doc.UndoRecords;
        request.Layers.Add(Layer("Invalid", "Invalid", double.NaN));
        Check(manager.Apply(doc, request).Status == "error" && doc.UndoRecords == before && doc.Layers.Count == 3, "Invalid segments fail before mutation.");

        var shared = new DrawingStyleRequest { Layers = new() { Layer("Shared::a", "Existing", 3), Layer("Shared::b", "existing", 9) } };
        Check(manager.Apply(doc, shared).Status == "success", "Conflicting request copies must reuse the existing document name.");
        Check(existing.Segments[0].Length == 42 && doc.Linetypes.Count == 2 &&
            doc.Layers[doc.Layers.Names["Shared::a"]].LinetypeIndex == retainedIndex &&
            doc.Layers[doc.Layers.Names["Shared::b"]].LinetypeIndex == retainedIndex, "Both layers retain the document definition.");
        before = doc.UndoRecords;
        shared.Layers[1].LinetypeSegments[0].Length = 0;
        Check(manager.Apply(doc, shared).Status == "error" && doc.UndoRecords == before, "Existing names still validate every request segment.");
        shared.Layers = new() { Layer("Missing::a", "Missing", 3), Layer("Missing::b", "missing", 9) };
        Check(manager.Apply(doc, shared).Status == "error" && doc.UndoRecords == before && doc.Linetypes.Count == 2,
            "Conflicting definitions for a new name still fail before mutation.");

        var reserved = new DrawingStyleRequest { Layers = new() };
        foreach (string name in new[] { "Continuous", "ByLayer", " byparent " })
            reserved.Layers.Add(new DrawingLayerSpecification { Path = "Reserved::" + name, Linetype = name });
        Check(manager.Apply(doc, reserved).Status == "success" && doc.Linetypes.Count == 2,
            "Reserved names do not require profile segments or create custom patterns.");
        foreach (var spec in reserved.Layers)
            Check(doc.Layers[doc.Layers.Names[spec.Path]].LinetypeIndex == -1, "Reserved layer patterns resolve to Continuous.");
        before = doc.UndoRecords;
        reserved.Layers[1].LinetypeSegments = Layer("unused", "unused", 3).LinetypeSegments;
        Check(manager.Apply(doc, reserved).Status == "error" && doc.UndoRecords == before,
            "Explicit segments for reserved inputs remain invalid.");
        Console.WriteLine("PASS: named definitions/references/repeat; existing/new duplicate preflight; reserved names; invalid segments");
    }
}
