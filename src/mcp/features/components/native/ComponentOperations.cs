using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // The caller resolves Component descendants in the same native UI callback.
    // These operations consume current object identities; native helpers remain MCP-owned.
    public static class ComponentOperations
    {
        private const int MaxBytes = 262144;
        private const int MaxIntersectionObjects = 512;
        private const int MaxFocusObjects = 4096;

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            try
            {
                var ids = request?["component_ids"] as JArray;
                string action = (string)request?["action"];
                if ((action != "intersections" && action != "focus") || ids == null || ids.Count == 0 || ids.Count > 32 ||
                    ids.Any(id => id.Type != JTokenType.String || String.IsNullOrWhiteSpace((string)id)))
                    throw new ArgumentException("Use intersections or focus with 1 to 32 Component IDs.");
                var objects = new HashSet<Guid>();
                foreach (string id in ids.Values<string>().Distinct(StringComparer.Ordinal))
                {
                    var observed = ComponentRegistry.Handle(doc, new JObject {
                        ["action"] = "inspect", ["expected_model_path"] = request["expected_model_path"]?.DeepClone(),
                        ["component_id"] = id
                    });
                    if ((string)observed["status"] != "success") return observed;
                    var component = observed["component"] as JObject;
                    if ((string)component?["availability"] != "present")
                        throw new ArgumentException("Every requested Component must be present before intersections or focus: " + id);
                    foreach (string guid in component["effective_object_ids"].Values<string>())
                        objects.Add(Guid.Parse(guid));
                }
                JObject result;
                if (action == "focus") result = IsolateAndZoomSelected(doc, objects.ToArray());
                else
                {
                    var budget = request["max_pairs"];
                    if (budget != null && budget.Type != JTokenType.Integer)
                        throw new ArgumentException("max_pairs must be an integer.");
                    if (request["include_blocks"] != null && request["include_blocks"].Type != JTokenType.Boolean)
                        throw new ArgumentException("include_blocks must be a boolean.");
                    if (request["cursor"] != null && request["cursor"].Type != JTokenType.String)
                        throw new ArgumentException("cursor must be a string.");
                    result = CheckIntersectVolumes(doc, objects.ToArray(), budget == null ? 64 : (int)budget,
                        (bool?)request["include_blocks"] ?? false, (string)request["cursor"] ?? "");
                }
                result["component_ids"] = new JArray(ids.Values<string>().Distinct(StringComparer.Ordinal));
                return result;
            }
            catch (Exception error) { return Error("component_operation_error", error, false); }
        }

        public static JObject CheckIntersectVolumes(RhinoDoc doc, Guid[] objectIds, int maxPairs = 64,
            bool includeBlocks = false, string cursor = "")
        {
            try { return IntersectionAnalysis.Query(doc, objectIds, maxPairs, includeBlocks, cursor); }
            catch (Exception error) { return Error("component_intersection_error", error, false); }
        }

        public static JObject IsolateAndZoomSelected(RhinoDoc doc, Guid[] objectIds)
        {
            bool started = false;
            try
            {
                var objects = Objects(doc, objectIds, MaxFocusObjects);
                if (doc.IsHeadless || RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber)
                    throw new ArgumentException("Focusing requires the current regular Rhino document.");
                var view = doc.Views.ActiveView;
                if (view == null || view is RhinoPageView)
                    throw new ArgumentException("Activate a model view before isolating Components.");
                if (Rhino.Commands.Command.InCommand() || doc.UndoRecordingIsActive || doc.UndoActive || doc.RedoActive)
                    throw new ArgumentException("Finish the current command or Undo/Redo operation before focusing Components.");
                foreach (var obj in objects)
                    if (!obj.IsSelectable(true, false, false, false))
                        throw new ArgumentException("Every target must be visible and selectable; cannot focus: " + obj.Id);
                Guid viewportId = view.ActiveViewport.Id;
                // Bound the complete acknowledgement before any selection/view mutation.
                var result = Bounded(new JObject
                {
                    ["status"] = "success", ["model_path"] = doc.Path,
                    ["viewport_id"] = viewportId.ToString("D"),
                    ["selected_ids"] = new JArray(objects.Select(o => o.Id.ToString("D"))),
                    ["isolated"] = true, ["zoom_selected"] = true,
                    ["locked_context_remains_visible"] = true,
                    ["restore_visibility_command"] = "Unisolate"
                });
                started = true;
                doc.Objects.UnselectAll();
                foreach (var obj in objects)
                    if (obj.Select(true, true, true, false, false, false) == 0)
                        throw new InvalidOperationException("Rhino could not select target: " + obj.Id);
                // Fixed Rhino command preserves its native Isolate/Unisolate bookkeeping.
                if (!RhinoApp.RunScript("_Isolate", false))
                    throw new InvalidOperationException("Rhino did not complete Isolate.");
                if (RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber ||
                    doc.Views.ActiveView?.ActiveViewport.Id != viewportId)
                    throw new InvalidOperationException("The document or active view changed while isolating Components.");
                var wanted = new HashSet<Guid>(objects.Select(o => o.Id));
                var selected = doc.Objects.GetSelectedObjects(false, false).Select(o => o.Id);
                if (!wanted.SetEquals(selected)) throw new InvalidOperationException("Selection changed while isolating Components.");
                if (!view.ActiveViewport.ZoomExtentsSelected())
                    throw new InvalidOperationException("Rhino could not zoom to the selected Components.");
                doc.Views.Redraw();
                return result;
            }
            catch (Exception error) { return Error("component_focus_error", error, started); }
        }

        private static RhinoObject[] Objects(RhinoDoc doc, Guid[] objectIds, int max)
        {
            if (doc == null) throw new ArgumentException("No Rhino document is available.");
            if (objectIds == null || objectIds.Length == 0 || objectIds.Any(id => id == Guid.Empty))
                throw new ArgumentException("Resolve a nonempty set of current object GUIDs first.");
            // Ancestors and descendants can legitimately resolve to the same physical member.
            var ids = objectIds.Distinct().OrderBy(id => id).ToArray();
            if (ids.Length > max) throw new ArgumentException("Narrow the resolved scope to at most " + max + " objects.");
            var objects = ids.Select(id => doc.Objects.FindId(id)).ToArray();
            if (objects.Any(o => o == null || o.IsDeleted || o.IsInstanceDefinitionGeometry || o.Attributes.Space != ActiveSpace.ModelSpace))
                throw new ArgumentException("Every resolved GUID must identify a current top-level model-space object.");
            return objects;
        }

        private static JObject Bounded(JObject value)
        {
            if (Encoding.UTF8.GetByteCount(value.ToString(Formatting.None)) > MaxBytes)
                throw new ArgumentException("Component operation response exceeds 256 KiB; narrow the scope or pair budget.");
            return value;
        }

        private static JObject Error(string code, Exception error, bool started) => new JObject
        {
            ["status"] = "error", ["error_code"] = code, ["message"] = error.Message,
            ["mutation_applied"] = started ? JValue.CreateNull() : new JValue(false),
            ["requires_reconciliation"] = started
        };
    }
}
