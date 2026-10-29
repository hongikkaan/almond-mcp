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
    // These operations consume the resulting current top-level object identities.
    public static class ComponentOperations
    {
        private const int MaxBytes = 262144;
        private const int MaxIntersectionObjects = 512;
        private const int MaxFocusObjects = 4096;

        private sealed class Solid
        {
            internal Guid Id;
            internal BoundingBox Bounds;
        }

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
                    result = CheckIntersectVolumes(doc, objects.ToArray(), budget == null ? 64 : (int)budget);
                }
                result["component_ids"] = new JArray(ids.Values<string>().Distinct(StringComparer.Ordinal));
                return result;
            }
            catch (Exception error) { return Error("component_operation_error", error, false); }
        }

        public static JObject CheckIntersectVolumes(RhinoDoc doc, Guid[] objectIds, int maxPairs = 64)
        {
            try
            {
                var objects = Objects(doc, objectIds, MaxIntersectionObjects);
                if (maxPairs < 1 || maxPairs > 64) throw new ArgumentException("max_pairs must be between 1 and 64.");
                double tolerance = doc.ModelAbsoluteTolerance;
                if (!Double.IsFinite(tolerance) || tolerance <= 0)
                    throw new ArgumentException("The document must have a finite positive absolute tolerance.");
                var unsupported = new JArray();
                var solids = new List<Solid>();
                foreach (var obj in objects)
                {
                    string reason = Unsupported(obj);
                    if (reason != null)
                    {
                        unsupported.Add(new JObject { ["rhino_guid"] = obj.Id.ToString("D"), ["reason"] = reason });
                        continue;
                    }
                    var bounds = obj.Geometry.GetBoundingBox(true);
                    if (!bounds.IsValid) throw new ArgumentException("An object has invalid world bounds: " + obj.Id);
                    solids.Add(new Solid { Id = obj.Id, Bounds = bounds });
                }

                // Bounded sweep-and-prune. Count every candidate, but send at most
                // the requested kernel budget to the existing pair observer.
                var ordered = solids.OrderBy(s => s.Bounds.Min.X).ThenBy(s => s.Id).ToArray();
                var pairs = new JArray();
                int candidates = 0;
                for (int i = 0; i < ordered.Length; i++)
                {
                    var a = ordered[i];
                    for (int j = i + 1; j < ordered.Length; j++)
                    {
                        var b = ordered[j];
                        if (b.Bounds.Min.X - a.Bounds.Max.X > tolerance) break;
                        if (b.Bounds.Min.Y - a.Bounds.Max.Y > tolerance || a.Bounds.Min.Y - b.Bounds.Max.Y > tolerance ||
                            b.Bounds.Min.Z - a.Bounds.Max.Z > tolerance || a.Bounds.Min.Z - b.Bounds.Max.Z > tolerance) continue;
                        candidates++;
                        if (pairs.Count < maxPairs) pairs.Add(new JArray(a.Id.ToString("D"), b.Id.ToString("D")));
                    }
                }

                var audit = pairs.Count == 0 ? null : SolidIntersections.AuditPairs(doc, new JObject
                {
                    ["pairs"] = pairs, ["max_pairs"] = maxPairs, ["max_bytes"] = 196608,
                    ["tolerance"] = tolerance
                });
                var observed = audit?["pairs"] as JArray ?? new JArray();
                int positives = observed.Count(p => (string)p["overlap"]?["status"] == "positive_volume");
                int unknown = observed.Count(p => (string)p["overlap"]?["status"] != "positive_volume" &&
                    (string)p["overlap"]?["status"] != "zero_volume");
                bool auditTruncated = audit != null && (bool?)audit["truncated"] == true;
                bool truncated = candidates > observed.Count || auditTruncated;
                bool complete = !truncated && unsupported.Count == 0 && unknown == 0;
                string truncationReason = auditTruncated ? (string)audit["truncation_reason"] :
                    candidates > observed.Count ? "max_pairs" : null;
                return Bounded(new JObject
                {
                    ["status"] = "success", ["schema"] = "almond-component-intersections/v1",
                    ["model_path"] = doc.Path, ["document_units"] = doc.ModelUnitSystem.ToString(),
                    ["tolerance_model_units"] = tolerance,
                    ["object_ids"] = new JArray(objects.Select(o => o.Id.ToString("D"))),
                    ["object_count"] = objects.Length, ["supported_object_count"] = solids.Count,
                    ["unsupported_objects"] = unsupported,
                    ["candidate_pair_count"] = candidates,
                    ["bbox_pruned_pair_count"] = solids.Count * (solids.Count - 1) / 2 - candidates,
                    ["evaluated_pairs"] = observed.Count, ["max_pairs"] = maxPairs, ["pairs"] = observed,
                    ["positive_pair_count"] = positives, ["unknown_pair_count"] = unknown,
                    ["truncated"] = truncated, ["truncation_reason"] = truncationReason,
                    ["complete"] = complete,
                    ["has_positive_overlap"] = positives > 0 ? new JValue(true) : complete ? new JValue(false) : JValue.CreateNull(),
                    ["limitations"] = new JArray(
                        "All distinct pairs within the resolved object set are considered, including pairs inside one Component.",
                        "Only valid closed document-level Breps and Extrusions are supported; blocks are not exploded or changed.",
                        "Unsupported objects, truncated work and unknown kernel results prevent a complete no-overlap conclusion.",
                        "Pair volumes are not summed because their overlapping regions may overlap each other.")
                });
            }
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

        private static string Unsupported(RhinoObject obj)
        {
            var geometry = obj.Geometry;
            if (obj is InstanceObject) return "block_requires_world_space_geometry";
            if (!(geometry is Brep) && !(geometry is Extrusion)) return "only_brep_or_extrusion_supported";
            if (!geometry.IsValid) return "invalid_geometry";
            if (geometry is Brep brep)
            {
                if (!brep.IsSolid) return "valid_closed_solid_required";
                if (brep.SolidOrientation != BrepSolidOrientation.Outward && brep.SolidOrientation != BrepSolidOrientation.Inward)
                    return "unresolved_solid_orientation";
            }
            else if (!((Extrusion)geometry).IsSolid) return "valid_closed_solid_required";
            return null;
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
