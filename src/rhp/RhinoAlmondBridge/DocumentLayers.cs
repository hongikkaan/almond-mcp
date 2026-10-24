using System;
using System.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    // Native document adapter: the caller chooses the path and style.
    public static class DocumentLayers
    {
        public static int Ensure(RhinoDoc doc, string path)
        {
            var parts = (path ?? "").Split(new[] { "::" }, StringSplitOptions.None);
            if (parts.Any(p => String.IsNullOrWhiteSpace(p) || p != p.Trim() || !ModelComponent.IsValidComponentName(p)))
                throw new ArgumentException("Layer path contains an invalid name: " + path);
            Guid parent = Guid.Empty;
            int index = -1;
            foreach (var part in parts)
            {
                var found = doc.Layers.FirstOrDefault(l => !l.IsDeleted && !l.IsReference &&
                    l.ParentLayerId == parent && String.Equals(l.Name, part, StringComparison.OrdinalIgnoreCase));
                index = found?.Index ?? doc.Layers.Add(new Layer { Name = part, ParentLayerId = parent });
                if (index < 0) throw new InvalidOperationException("Cannot create layer: " + path);
                parent = doc.Layers[index].Id;
            }
            return index;
        }
    }
}
