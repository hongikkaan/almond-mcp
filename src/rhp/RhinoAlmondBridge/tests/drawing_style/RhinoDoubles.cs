using System.Drawing;
using Rhino.DocObjects;

namespace Rhino
{
    public sealed class RhinoDoc
    {
        public static RhinoDoc ActiveDoc { get; set; }
        public LinetypeTable Linetypes { get; } = new();
        public LayerTable Layers { get; } = new();
        public ViewTable Views { get; } = new();
        public uint BeginUndoRecord(string name) => 1;
        public void EndUndoRecord(uint record) { }
    }

    public sealed class LinetypeTable : List<Linetype>
    {
        private readonly Linetype _continuous = new() { Name = "Continuous", Index = -1 };

        public Linetype FindName(string name) =>
            Find(item => string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase)) ?? _continuous;

        public new int Add(Linetype definition)
        {
            definition.Index = Count;
            base.Add(definition);
            return definition.Index;
        }
    }

    public sealed class LayerTable : List<Layer>
    {
        public new int Add(Layer layer)
        {
            layer.Index = Count;
            base.Add(layer);
            return layer.Index;
        }

        public bool Modify(Layer layer, int index, bool quiet)
        {
            this[index] = layer;
            return true;
        }
    }

    public sealed class ViewTable
    {
        public void Redraw() { }
    }
}

namespace Rhino.DocObjects
{
    public class ModelComponent
    {
        public static bool IsValidComponentName(string name) => name.Length > 0;
    }

    public sealed class Linetype
    {
        public string Name { get; set; }
        public int Index { get; set; }
        public bool IsDeleted { get; set; }
        public List<(double Length, bool IsSolid)> Segments { get; } = new();
        public void AppendSegment(double length, bool isSolid) => Segments.Add((length, isSolid));
    }

    public sealed class Layer
    {
        public string Name { get; set; }
        public Guid Id { get; } = Guid.NewGuid();
        public Guid ParentLayerId { get; set; }
        public int Index { get; set; }
        public bool IsDeleted { get; set; }
        public bool IsReference { get; set; }
        public Color Color { get; set; }
        public Color PlotColor { get; set; }
        public double PlotWeight { get; set; }
        public int LinetypeIndex { get; set; }
        public void EnsurePrivateCopy() { }
    }
}
