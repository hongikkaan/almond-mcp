using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    /// <summary>Defined-view capture and live selection/Isolate/Zoom Selected capture.</summary>
    public static class ViewCaptureTools
    {
        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            var changes = new JObject { ["selection_changed"] = false, ["isolated"] = false,
                ["zoom_selected"] = false, ["display_mode_changed"] = false };
            try
            {
                ObjectObservation.ValidateDocument(doc, request);
                int scale = Integer(request, "scale_percent", 75, 1, 100);
                int depth = Integer(request, "depth", 1, 1, 8);
                int width = Integer(request, "width", 0, 128, 2048);
                int height = Integer(request, "height", 0, 128, 2048);
                if ((width == 0) != (height == 0) || (width != 0 && scale != 100))
                    throw new ArgumentException("Explicit width and height require both dimensions and scale_percent=100.");
                bool labels = Boolean(request, "labels", false);
                string displayMode = Text(request, "display_mode", "");
                if (displayMode.Length > 512) throw new ArgumentException("display_mode exceeds 512 characters.");
                if ((string)request["type"] == "get_defined_viewcapture")
                {
                    string kind = Text(request, "target_kind", "");
                    string target = Text(request, "target", "");
                    Guid id = ResolveDefinedView(doc, kind, target);
                    int actualScale = scale;
                    JObject capture;
                    do
                    {
                        capture = DocumentObservation.GetViewportImage(doc, id.ToString(), actualScale, displayMode, labels, depth,
                            "view", "", width, height, kind);
                        if ((string)capture["error_code"] != "image_too_large" || width != 0 || actualScale == 1) break;
                        actualScale = Math.Max(1, actualScale / 2);
                    } while (true);
                    capture["scale_percent"] = actualScale;
                    if (actualScale != scale)
                        ((JArray)capture["warnings"]).Add("Capture scale reduced to " + actualScale + "% to fit the PNG delivery budget; paper proportions are preserved.");
                    return capture;
                }
                if ((string)request["type"] != "get_current_viewcapture")
                    throw new ArgumentException("Unknown capture request.");
                bool isolate = Boolean(request, "isolate", false);
                string targetKind = Text(request, "target_kind", "object");
                var ids = Strings(request["target_ids"]);
                if (!new[] { "object", "group", "block", "holon" }.Contains(targetKind))
                    throw new ArgumentException("target_kind must identify object, group, block or holon IDs.");
                if (ids.Length == 0 && (isolate || targetKind != "object"))
                    throw new ArgumentException("Target IDs are required for isolation or a nondefault target_kind.");
                var view = doc.Views.ActiveView;
                if (doc.IsHeadless || RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber || view == null)
                    throw new ArgumentException("A current regular Rhino document and model viewport are required.");
                if (view is RhinoPageView)
                    throw new ArgumentException("Activate a model viewport; use get_defined_viewcapture for Layout paper.");
                var mode = displayMode == "" ? null : ResolveMode(displayMode);
                bool modeChange = mode != null && view.ActiveViewport.DisplayMode.Id != mode.Id;
                var targets = ids.Length == 0 ? Array.Empty<RhinoObject>() : ResolveObjects(doc, request, targetKind, ids);
                if (targets.Length != 0 || modeChange)
                {
                    if (Rhino.Commands.Command.InCommand() || doc.UndoRecordingIsActive || doc.UndoActive || doc.RedoActive)
                        throw new ArgumentException("Finish the current command or Undo/Redo operation before changing the view.");
                    if (isolate && doc.IsReadOnly) throw new ArgumentException("The document is read-only; isolation was not started.");
                    if (targets.Length != 0)
                    {
                        var focused = ComponentOperations.FocusObjects(doc, targets.Select(o => o.Id).ToArray(), isolate);
                        if (focused["view_change"] is JObject focusChanges)
                            changes = (JObject)focusChanges.DeepClone();
                        if ((string)focused["status"] != "success")
                        {
                            focused["view_change"] = changes;
                            return focused;
                        }
                        started = true;
                        changes["selection_changed"] = true;
                        changes["isolated"] = isolate;
                        changes["zoom_selected"] = true;
                        if (isolate) changes["restore_visibility_command"] = "Unisolate";
                    }
                    if (modeChange)
                    {
                        started = true;
                        changes["display_mode_changed"] = JValue.CreateNull();
                        view.ActiveViewport.DisplayMode = mode;
                        changes["display_mode_changed"] = true;
                    }
                    doc.Views.Redraw();
                }
                var result = DocumentObservation.GetViewportImage(doc, "", scale, "", labels, depth, "view", "", width, height);
                if (ids.Length != 0 || displayMode != "") result["mutation_applied"] = started;
                if (started)
                {
                    result["view_change"] = changes;
                    result["mutation_applied"] = true;
                    if (isolate)
                        ((JArray)result["warnings"]).Add("Native Isolate retains locked context; use Unisolate to restore its visibility. Selection and camera remain at the captured targets.");
                }
                return result;
            }
            catch (Exception error)
            {
                return new JObject { ["status"] = "error", ["error_code"] = "view_capture_error", ["message"] = error.Message,
                    ["view_change"] = changes, ["mutation_applied"] = started ? JValue.CreateNull() : new JValue(false),
                    ["requires_reconciliation"] = started, ["warnings"] = new JArray() };
            }
        }

        private static RhinoObject[] ResolveObjects(RhinoDoc doc, JObject request, string kind, string[] ids)
        {
            var resolved = new HashSet<Guid>();
            foreach (var id in ids)
            {
                if (kind == "holon")
                {
                    var observed = ComponentRegistry.Handle(doc, new JObject { ["action"] = "inspect",
                        ["component_id"] = id, ["expected_model_path"] = request["expected_model_path"]?.DeepClone() });
                    if ((string)observed["status"] != "success" || (string)observed["component"]?["availability"] != "present")
                        throw new ArgumentException("Holon is not available in this document: " + id);
                    foreach (var member in observed["component"]["effective_object_ids"].Values<string>()) resolved.Add(Guid.Parse(member));
                }
                else
                {
                    if (!Guid.TryParse(id, out var guid) || guid == Guid.Empty) throw new ArgumentException("Invalid target GUID: " + id);
                    if (kind == "group")
                    {
                        var group = doc.Groups.FindId(guid);
                        if (group == null || group.IsDeleted) throw new ArgumentException("Unknown group: " + id);
                        foreach (var member in doc.Groups.GroupMembers(group.Index) ?? Array.Empty<RhinoObject>()) resolved.Add(member.Id);
                    }
                    else resolved.Add(guid); // Block instances are ordinary object IDs; no geometry allowlist.
                }
            }
            if (resolved.Count == 0) throw new ArgumentException("The targets resolve to no current objects.");
            var objects = resolved.Select(doc.Objects.FindId).ToArray();
            if (objects.Any(o => o == null || o.IsDeleted || o.IsInstanceDefinitionGeometry || o.Attributes.Space != ActiveSpace.ModelSpace))
                throw new ArgumentException("Use existing model-space object IDs, not deleted objects, Layout objects or block-definition members.");
            return objects;
        }

        private static Guid ResolveDefinedView(RhinoDoc doc, string kind, string target)
        {
            if ((kind != "named_view" && kind != "layout") || String.IsNullOrWhiteSpace(target))
                throw new ArgumentException("Specify target_kind named_view/layout and a name or ID.");
            var entries = kind == "named_view"
                ? doc.NamedViews.Select(v => (Name: v.Name, Id: v.NamedViewId)).ToArray()
                : doc.Views.GetViewList(ViewTypeFilter.Page).Select(v => (Name: v.MainViewport.Name, Id: v.MainViewport.Id)).ToArray();
            Guid.TryParse(target, out var id);
            var matches = entries.Where(v => (id != Guid.Empty && v.Id == id) || String.Equals(v.Name, target, StringComparison.OrdinalIgnoreCase)).ToArray();
            if (matches.Length != 1) throw new ArgumentException("The view name/ID is missing or ambiguous; use a unique ID from get_rhino_context.");
            return matches[0].Id;
        }

        private static DisplayModeDescription ResolveMode(string name)
        {
            Guid.TryParse(name, out var id);
            var modes = DisplayModeDescription.GetDisplayModes().Where(m => m.Id == id ||
                String.Equals(m.EnglishName, name, StringComparison.OrdinalIgnoreCase) ||
                String.Equals(m.LocalName, name, StringComparison.OrdinalIgnoreCase)).ToArray();
            if (modes.Length != 1) throw new ArgumentException("Display mode is missing or ambiguous; use get_rhino_context.");
            if (modes[0].DisplayAttributes.RealtimeDisplayId != Guid.Empty)
                throw new ArgumentException("Realtime display mode changes require asynchronous rendering; choose an installed raster mode.");
            return modes[0];
        }

        private static string[] Strings(JToken token)
        {
            if (token == null) return Array.Empty<string>();
            if (!(token is JArray values) || values.Count == 0 || values.Any(v => v.Type != JTokenType.String || String.IsNullOrWhiteSpace((string)v)))
                throw new ArgumentException("target_ids must be a nonempty string array when supplied.");
            return values.Values<string>().Distinct(StringComparer.Ordinal).ToArray();
        }
        private static string Text(JObject r, string key, string fallback)
        {
            if (r[key] == null) return fallback;
            if (r[key].Type != JTokenType.String) throw new ArgumentException(key + " must be a string.");
            return (string)r[key];
        }
        private static bool Boolean(JObject r, string key, bool fallback)
        {
            if (r[key] == null) return fallback;
            if (r[key].Type != JTokenType.Boolean) throw new ArgumentException(key + " must be boolean.");
            return (bool)r[key];
        }
        private static int Integer(JObject r, string key, int fallback, int min, int max)
        {
            if (r[key] == null) return fallback;
            if (r[key].Type != JTokenType.Integer || (long)r[key] < min || (long)r[key] > max)
                throw new ArgumentException(key + " is outside its integer range.");
            return (int)r[key];
        }
    }
}
