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

        public static JObject IsolateAndZoomSelected(RhinoDoc doc, Guid[] objectIds) => FocusObjects(doc, objectIds, true);

        // Shared by Holon focus and current-view capture; geometry type is not filtered.
        public static JObject FocusObjects(RhinoDoc doc, Guid[] objectIds, bool isolate)
        {
            bool started = false;
            string stage = "validate";
            var changes = new JObject { ["selection_changed"] = false, ["isolated"] = false,
                ["zoom_selected"] = false, ["display_mode_changed"] = false };
            var observations = new JObject();
            RhinoViewport viewport = null;
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
                viewport = view.ActiveViewport;
                // Bound the complete acknowledgement before any selection/view mutation.
                var result = Bounded(new JObject
                {
                    ["status"] = "success", ["model_path"] = doc.Path,
                    ["viewport_id"] = viewportId.ToString("D"),
                    ["selected_ids"] = new JArray(objects.Select(o => o.Id.ToString("D"))),
                    ["isolated"] = isolate, ["zoom_selected"] = true,
                    ["locked_context_remains_visible"] = isolate,
                    ["restore_visibility_command"] = isolate ? "Unisolate" : null
                });
                started = true;
                stage = "select";
                changes["selection_changed"] = JValue.CreateNull();
                doc.Objects.UnselectAll();
                foreach (var obj in objects)
                    if (obj.Select(true, true, true, false, false, false) == 0)
                        throw new InvalidOperationException("Rhino could not select target: " + obj.Id);
                changes["selection_changed"] = true;
                // Fixed Rhino command preserves its native Isolate/Unisolate bookkeeping.
                if (isolate)
                {
                    stage = "isolate";
                    changes["isolated"] = JValue.CreateNull();
                    if (!RhinoApp.RunScript("_Isolate", false))
                        throw new InvalidOperationException("Rhino did not complete Isolate.");
                    changes["isolated"] = true;
                    changes["restore_visibility_command"] = "Unisolate";
                }
                stage = "verify_selection";
                if (RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber ||
                    doc.Views.ActiveView?.ActiveViewport.Id != viewportId)
                    throw new InvalidOperationException("The document or active view changed while isolating Components.");
                var wanted = new HashSet<Guid>(objects.Select(o => o.Id));
                var selected = doc.Objects.GetSelectedObjects(false, false).Select(o => o.Id);
                if (!wanted.SetEquals(selected)) throw new InvalidOperationException("Selection changed while isolating Components.");
                stage = "zoom_selected";
                observations["before_zoom"] = FocusViewState(viewport);
                observations["target_count"] = objects.Length;
                // Diagnostic reads must not prevent the requested native zoom.
                BoundingBox? zoomBounds = null;
                try
                {
                    var bounds = BoundingBox.Empty;
                    foreach (var obj in objects)
                    {
                        var targetBounds = obj.Geometry.GetBoundingBox(true);
                        if (!targetBounds.IsValid) throw new InvalidOperationException("Target bounds are unavailable: " + obj.Id);
                        bounds.Union(targetBounds);
                    }
                    if (bounds.IsValid)
                    {
                        zoomBounds = bounds;
                        observations["target_bounds"] = new JObject { ["min"] = Coordinates(bounds.Min), ["max"] = Coordinates(bounds.Max) };
                    }
                    else observations["target_bounds_error"] = "Target bounds are unavailable.";
                }
                catch (Exception error) { observations["target_bounds_error"] = error.Message; }
                changes["zoom_selected"] = JValue.CreateNull();
                string zoomMethod = "selected";
                if (!viewport.ZoomExtentsSelected())
                {
                    observations["zoom_extents_selected"] = false;
                    if (!zoomBounds.HasValue)
                        throw new InvalidOperationException("Rhino could not zoom to the selected Components.");
                    observations["zoom_bounding_box"] = JValue.CreateNull();
                    bool zoomed = viewport.ZoomBoundingBox(zoomBounds.Value);
                    observations["zoom_bounding_box"] = zoomed;
                    if (!zoomed)
                        throw new InvalidOperationException("Rhino could not zoom to the selected Components or their bounds.");
                    zoomMethod = "bounding_box";
                }
                changes["zoom_selected"] = true;
                changes["zoom_method"] = zoomMethod;
                stage = "redraw";
                doc.Views.Redraw();
                result["view_change"] = changes;
                return result;
            }
            catch (Exception error)
            {
                var result = Error("component_focus_error", error, started);
                result["view_change"] = changes;
                result["failed_stage"] = stage;
                if (viewport != null) observations["after_failure"] = FocusViewState(viewport);
                result["focus_observation"] = observations;
                return result;
            }
        }

        private static JArray Coordinates(Point3d point) => new JArray(point.X, point.Y, point.Z);

        private static JObject FocusViewState(RhinoViewport viewport)
        {
            try
            {
                var state = new JObject { ["viewport_id"] = viewport.Id.ToString("D"),
                    ["parallel_projection"] = viewport.IsParallelProjection,
                    ["camera_location"] = Coordinates(viewport.CameraLocation),
                    ["camera_target"] = Coordinates(viewport.CameraTarget) };
                if (viewport.GetFrustum(out double left, out double right, out double bottom,
                    out double top, out double near, out double far))
                    state["frustum"] = new JArray(left, right, bottom, top, near, far);
                return state;
            }
            catch (Exception error) { return new JObject { ["observation_error"] = error.Message }; }
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
