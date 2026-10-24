using System;
using System.Collections.Generic;
using Rhino;
using Rhino.DocObjects;
using Rhino.DocObjects.Tables;

namespace RhinoAlmondBridge
{
    // Observe a single operation; apply after callers finish setting attributes.
    internal sealed class MaterialLayerChanges : IDisposable
    {
        private readonly RhinoDoc document;
        private readonly HashSet<Guid> objects = new HashSet<Guid>();
        private readonly HashSet<int> materials = new HashSet<int>();
        private bool observing = true;

        internal MaterialLayerChanges(RhinoDoc doc)
        {
            document = doc;
            RhinoDoc.AddRhinoObject += Added;
            RhinoDoc.ModifyObjectAttributes += AttributesChanged;
            RhinoDoc.MaterialTableEvent += MaterialChanged;
        }

        private bool Owns(RhinoDoc doc)
        {
            return doc != null && doc.RuntimeSerialNumber == document.RuntimeSerialNumber;
        }

        private void Added(object sender, RhinoObjectEventArgs e)
        {
            if (e.TheObject != null && Owns(e.TheObject.Document)) objects.Add(e.ObjectId);
        }

        private void AttributesChanged(object sender, RhinoModifyObjectAttributesEventArgs e)
        {
            if (!Owns(e.Document)) return;
            if (e.OldAttributes.MaterialIndex != e.NewAttributes.MaterialIndex ||
                e.OldAttributes.MaterialSource != e.NewAttributes.MaterialSource)
                objects.Add(e.RhinoObject.Id);
        }

        private void MaterialChanged(object sender, MaterialTableEventArgs e)
        {
            if (Owns(e.Document) && e.EventType == MaterialTableEventType.Modified)
                materials.Add(e.Index);
        }

        internal void Apply()
        {
            Dispose();
            if (materials.Count != 0)
            {
                var settings = new ObjectEnumeratorSettings
                {
                    NormalObjects = true, HiddenObjects = true, LockedObjects = true,
                    ReferenceObjects = false, IdefObjects = false, DeletedObjects = false
                };
                foreach (var obj in document.Objects.GetObjectList(settings))
                    if (obj.Attributes.MaterialSource == ObjectMaterialSource.MaterialFromObject &&
                        materials.Contains(obj.Attributes.MaterialIndex)) objects.Add(obj.Id);
            }
            foreach (var id in objects)
            {
                var obj = document.Objects.FindId(id);
                if (obj != null && !obj.IsDeleted && !obj.IsReference && !obj.IsInstanceDefinitionGeometry)
                    ModelingMaterials.RouteObject(document, obj);
            }
        }

        public void Dispose()
        {
            if (!observing) return;
            observing = false;
            RhinoDoc.AddRhinoObject -= Added;
            RhinoDoc.ModifyObjectAttributes -= AttributesChanged;
            RhinoDoc.MaterialTableEvent -= MaterialChanged;
        }
    }
}
