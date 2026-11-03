using System;
using System.Collections.Generic;
using System.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    public static partial class ObjectObservation
    {
        internal static RhinoObject[] CurrentObjects(RhinoDoc doc, RhinoObject[] objects, bool selected, bool insideWindow)
        {
            if (selected && insideWindow) throw new ArgumentException("Choose selected or inside_window, not both.");
            var viewport = insideWindow ? doc.Views.ActiveView?.ActiveViewport : null;
            if (insideWindow && (viewport == null || doc.ActiveSpace != ActiveSpace.ModelSpace))
                throw new ArgumentException("inside_window requires an active model viewport or model Detail.");
            return objects.Where(o => o.Visible && !o.IsLocked && UnlockedLayer(doc, o.Attributes.LayerIndex) &&
                (!selected || o.IsSelected(false) != 0) &&
                (!insideWindow || viewport.IsVisible(o.Geometry.GetBoundingBox(true)))).ToArray();
        }

        static bool UnlockedLayer(RhinoDoc doc, int index)
        {
            var layer = doc.Layers.FindIndex(index);
            var visited = new HashSet<Guid>();
            while (layer != null)
            {
                if (layer.IsDeleted || layer.IsLocked || !visited.Add(layer.Id)) return false;
                if (layer.ParentLayerId == Guid.Empty) return true;
                layer = doc.Layers.FirstOrDefault(value => value != null && value.Id == layer.ParentLayerId);
            }
            return false;
        }
    }
}
