using System;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    public static class ModelingMetadata { public static string Key(string name) => name == "component_record" ? "almond:component_record" : throw new ArgumentException(name); }
    // Signature-only compile check against installed RhinoCommon. Never instantiated.
    public static class EditingContext { public static JObject Observe(RhinoDoc doc) => throw new NotSupportedException(); }
    public sealed class ScriptExecutor { public object ExecuteAction(RhinoDoc doc, Func<object> action) => throw new NotSupportedException(); }
    internal static class AttributeTransferContract
    {
        internal static JObject AutomaticCleanup(RhinoDoc doc) => StepCompletion.Handle(doc,
            new JObject { ["type"] = "step_completion", ["expected_model_path"] = doc.Path });
        // Compile the same existing movement pattern against the installed SDK.
        internal static bool Move(RhinoDoc doc, RhinoObject obj, int existingLayerIndex)
        {
            var attributes = obj.Attributes.Duplicate();
            attributes.LayerIndex = existingLayerIndex;
            return doc.Objects.ModifyAttributes(obj.Id, attributes, true);
        }
        // Real SDK: saved NamedViews and Layout views have separate table APIs.
        internal static int SeparateViewTables(RhinoDoc doc) => doc.NamedViews.Count + doc.Views.GetPageViews().Length;
    }
}
