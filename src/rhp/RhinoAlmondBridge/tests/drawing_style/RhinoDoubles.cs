using System.Drawing;
using Rhino.DocObjects;

namespace Rhino
{
    public sealed class RhinoDoc
    {
        public static RhinoDoc ActiveDoc { get; set; }
        public LinetypeTable Linetypes { get; } = new();
        public LayerTable Layers { get; } = new();
        public ObjectTable Objects { get; } = new();
        public ViewTable Views { get; } = new();
        public uint UndoRecord { get; set; } = 1;
        public bool UndoSucceeds { get; set; } = true;
        public bool UndoRecordingIsActive { get; private set; }
        public bool UndoActive => false;
        public bool RedoActive => false;
        public uint CurrentUndoRecordSerialNumber { get; private set; }
        public uint NextUndoRecordSerialNumber { get; private set; } = 1;
        private int initialLayers, initialLinetypes;
        public uint BeginUndoRecord(string name)
        {
            initialLayers = Layers.Count; initialLinetypes = Linetypes.Count;
            if (UndoRecord == 0) return 0;
            UndoRecordingIsActive = true; return CurrentUndoRecordSerialNumber = NextUndoRecordSerialNumber++;
        }
        public bool EndUndoRecord(uint record) { UndoRecordingIsActive = false; return true; }
        public bool Undo()
        {
            if (!UndoSucceeds) return false;
            Layers.RemoveRange(initialLayers, Layers.Count - initialLayers);
            Linetypes.RemoveRange(initialLinetypes, Linetypes.Count - initialLinetypes);
            return true;
        }
        public void ClearRedoRecords() { }
    }

    public sealed class ObjectTable : List<RhinoObject>
    {
        public RhinoObject[] FindByLayer(Layer layer) => this.Where(obj => obj.Attributes.LayerIndex == layer.Index).ToArray();
    }

    public sealed class LinetypeTable : List<Linetype>
    {
        private readonly Linetype _continuous = new() { Name = "Continuous", Index = -1 };

        public int NameLookups { get; private set; }

        public Linetype FindName(string name)
        {
            NameLookups++;
            return Find(item => string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase)) ?? _continuous;
        }

        public new int Add(Linetype definition)
        {
            definition.Index = Count;
            base.Add(definition);
            return definition.Index;
        }
        public bool Modify(Linetype definition, int index, bool quiet)
        {
            definition.Index = index;
            this[index] = definition;
            return true;
        }
    }

    public sealed class LayerTable : List<Layer>
    {
        public int FailModifyAt = -1, Modifications;
        public new int Add(Layer layer)
        {
            layer.Index = Count;
            base.Add(layer);
            return layer.Index;
        }

        public bool Modify(Layer layer, int index, bool quiet)
        {
            if (++Modifications == FailModifyAt) return false;
            this[index] = layer;
            return true;
        }
    }

    public sealed class ViewTable
    {
        public void Redraw() { }
    }
}

namespace Rhino.Commands
{
    public class UndoRedoEventArgs : EventArgs { public uint UndoSerialNumber; public bool IsPurgeRecord; }
    public class Command { public static event EventHandler<UndoRedoEventArgs> UndoRedo; }
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
        public int SegmentCount => Segments.Count;
        public void GetSegment(int index, out double length, out bool solid) =>
            (length, solid) = Segments[index];
        public void AppendSegment(double length, bool isSolid) => Segments.Add((length, isSolid));
    }

    public enum ObjectLinetypeSource { LinetypeFromLayer, LinetypeFromObject }
    public sealed class ObjectAttributes
    {
        public int LayerIndex { get; set; }
        public int LinetypeIndex { get; set; }
        public ObjectLinetypeSource LinetypeSource { get; set; }
    }
    public sealed class RhinoObject { public ObjectAttributes Attributes { get; } = new(); }

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
        public int LinetypeIndex { get; set; } = -1;
        public void EnsurePrivateCopy() { }
    }
}
