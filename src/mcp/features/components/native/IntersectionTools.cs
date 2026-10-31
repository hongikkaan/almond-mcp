using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    public static class IntersectionTools
    {
        static readonly Dictionary<uint, Preview> Previews = new Dictionary<uint, Preview>();

        // The existing duu alias can call this through an IronPython entry script. The
        // same analysis, geometry ownership and viewport-scoped conduit serve MCP.
        public static void RunInteractive()
        {
            var doc = RhinoDoc.ActiveDoc;
            if (doc == null || doc.IsHeadless || doc.Views.ActiveView == null || doc.Views.ActiveView is RhinoPageView)
            { RhinoApp.WriteLine("[TrueOverlap] Activate a Rhino model viewport."); return; }
            var regions = new List<GeometryBase>();
            var labels = new List<string>();
            bool cancelled = false;
            EventHandler escape = (sender, args) => cancelled = true;
            try
            {
                Guid[] ids;
                bool includeBlocks;
                using (var input = new Rhino.Input.Custom.GetObject())
                {
                    input.SetCommandPrompt("Select closed solids/Meshes for overlap preview");
                    input.GeometryFilter = ObjectType.Brep | ObjectType.Extrusion | ObjectType.Mesh | ObjectType.InstanceReference;
                    input.SubObjectSelect = false; input.GroupSelect = true;
                    var blocks = new Rhino.Input.Custom.OptionToggle(false, "No", "Yes");
                    input.AddOptionToggle("IncludeBlocks", ref blocks);
                    int all = input.AddOption("All");
                    int clear = input.AddOption("Clear");
                    while (true)
                    {
                        var status = input.GetMultiple(1, 0);
                        if (status == Rhino.Input.GetResult.Option)
                        {
                            if (input.OptionIndex() == clear) { Clear(doc); RhinoApp.WriteLine("[TrueOverlap] Preview cleared."); return; }
                            if (input.OptionIndex() == all)
                            {
                                ids = ObjectObservation.ModelObjects(doc).Where(o => o.IsSelectable(true, true, false, false) &&
                                    (o.Geometry is Brep || o.Geometry is Extrusion || o.Geometry is Mesh || o is InstanceObject))
                                    .Select(o => o.Id).ToArray();
                                break;
                            }
                            continue;
                        }
                        if (status != Rhino.Input.GetResult.Object) return;
                        ids = Enumerable.Range(0, input.ObjectCount).Select(i => input.Object(i).ObjectId).Distinct().ToArray();
                        break;
                    }
                    includeBlocks = blocks.CurrentValue;
                }
                if (ids.Length == 0) { RhinoApp.WriteLine("[TrueOverlap] No eligible objects selected."); return; }
                Guid viewId = doc.Views.ActiveView.ActiveViewport.Id;
                RhinoApp.EscapeKeyPressed += escape;
                string cursor = "", scopeState = null;
                int evaluated = 0, positive = 0, unknown = 0, unsupported = 0;
                do
                {
                    var result = IntersectionAnalysis.QueryForPreview(doc, ids, 64, includeBlocks, cursor, observed =>
                    {
                        RhinoApp.Wait();
                        if (cancelled) throw new OperationCanceledException("Preview cancelled; no document geometry was changed.");
                        if (regions.Count + observed.Regions.Count > 2048)
                            throw new ArgumentException("More than 2048 overlap solids; select a smaller scope for display.");
                        foreach (var geometry in observed.Regions)
                        { regions.Add(geometry); labels.Add((string)observed.Report["pair_id"]); }
                        observed.Regions.Clear(); // Ownership moves to this invocation, then Preview clones it.
                    });
                    evaluated += (int)result["evaluated_pairs"]; positive += (int)result["positive_pair_count"];
                    unknown += (int)result["unknown_pair_count"]; unsupported = ((JArray)result["unsupported_objects"]).Count;
                    scopeState = (string)result["scope_state"];
                    cursor = (string)result["next_cursor"] ?? "";
                    RhinoApp.WriteLine(String.Format("[TrueOverlap] Checked {0}, positive {1}, unknown {2}, remaining {3}.",
                        evaluated, positive, unknown, (int)result["remaining_candidate_pairs"]));
                } while (cursor.Length != 0);
                if (RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber || doc.Views.ActiveView?.ActiveViewport.Id != viewId ||
                    scopeState != IntersectionAnalysis.CurrentScopeState(doc, ids, includeBlocks))
                    throw new InvalidOperationException("Document, viewport or geometry changed while calculating; inspect again.");
                Clear(doc);
                if (regions.Count != 0)
                {
                    var preview = new Preview(doc, viewId, regions, "overlap", labels);
                    Previews[doc.RuntimeSerialNumber] = preview; preview.Attach(); doc.Views.Redraw();
                }
                RhinoApp.WriteLine(String.Format("[TrueOverlap] {0} positive pairs, {1} displayed solids, {2} unknown pairs, {3} unsupported occurrences.",
                    positive, regions.Count, unknown, unsupported));
            }
            catch (Exception ex) { RhinoApp.WriteLine("[TrueOverlap] " + ex.Message); }
            finally
            {
                RhinoApp.EscapeKeyPressed -= escape;
                foreach (var region in regions) region?.Dispose();
            }
        }

        public static JObject PreviewHandle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                ObjectObservation.ValidateDocument(doc, request);
                if (request["clear"] != null && request["clear"].Type != JTokenType.Boolean)
                    throw new ArgumentException("clear must be a boolean.");
                if ((bool?)request["clear"] == true)
                { started = true; Clear(doc); return new JObject { ["status"] = "success", ["displayed"] = false, ["cleared"] = true }; }
                var view = doc.Views.ActiveView;
                if (doc.IsHeadless || RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber || view == null || view is RhinoPageView)
                    throw new ArgumentException("A current Rhino model view is required for the preview.");
                IntersectionAnalysis.Scope sa = null, sb = null;
                try
                {
                    var a = IntersectionAnalysis.ResolveHandle(doc, request["a"] as JObject, out sa);
                    var b = IntersectionAnalysis.ResolveHandle(doc, request["b"] as JObject, out sb);
                    ValidatePair(doc, a, b, (string)request["pair_state"]);
                    using (var observed = IntersectionAnalysis.Observe(doc, a, b))
                    {
                        started = true;
                        Clear(doc);
                        var result = (JObject)observed.Report.DeepClone();
                        result["status"] = "success";
                        result["displayed"] = observed.Regions.Count != 0;
                        if (observed.Regions.Count != 0)
                        {
                            var preview = new Preview(doc, view.ActiveViewport.Id, observed.Regions,
                                (string)observed.Report["pair_id"]);
                            Previews[doc.RuntimeSerialNumber] = preview;
                            preview.Attach();
                            doc.Views.Redraw();
                        }
                        else result["display_reason"] = "No confirmed overlap geometry is available; the observation and uncertainty are retained.";
                        return result;
                    }
                }
                finally { sa?.Dispose(); sb?.Dispose(); }
            }
            catch (Exception ex) { return Error("intersection_preview_failed", ex, started); }
        }

        public static JObject ResolveHandle(RhinoDoc doc, JObject request)
        {
            bool started = false;
            try
            {
                ObjectObservation.ValidateDocument(doc, request);
                if (doc.IsReadOnly) throw new ArgumentException("The document is read-only.");
                var editor = EditingContext.Observe(doc);
                if ((bool?)editor["stable"] != true || (string)editor["mode"] != "model")
                    throw new ArgumentException("Finish the current group/block editing context before changing document-level solids.");
                IntersectionAnalysis.Scope sk = null, st = null;
                try
                {
                    var keep = IntersectionAnalysis.ResolveHandle(doc, request["keep"] as JObject, out sk);
                    var trim = IntersectionAnalysis.ResolveHandle(doc, request["trim"] as JObject, out st);
                    ValidatePair(doc, keep, trim, (string)request["pair_state"]);
                    if (keep.Path.Length != 0 || trim.Path.Length != 0 || keep.Geometry is InstanceReferenceGeometry || trim.Geometry is InstanceReferenceGeometry)
                        throw new ArgumentException("Automatic subtraction of block or linked-source members is not supported. Their occurrence can be inspected without editing the definition.");
                    if (!keep.Supported || !trim.Supported) throw new ArgumentException("Both operands must be supported closed solids.");
                    var target = doc.Objects.FindId(trim.RootId);
                    RequireEditable(doc, target);
                    if (keep.Geometry is Mesh && !(trim.Geometry is Mesh))
                        throw new ArgumentException("A Mesh cutter cannot be subtracted while preserving a Brep target; this operation is not supported.");
                    if (!(keep.Geometry is Mesh) && trim.Geometry is Mesh)
                        throw new ArgumentException("Mixed Brep/Mesh pairs can be inspected approximately; automatic mixed-representation subtraction is not supported.");
                    if (target.Geometry.UserData.Count != 0 || target.Geometry.GetUserStrings()?.Count > 0)
                        throw new ArgumentException("Subtraction cannot currently preserve custom geometry user data; the original is unchanged.");
                    if (target.Geometry is Mesh textured && (textured.TextureCoordinates.Count != 0 || textured.VertexColors.Count != 0))
                        throw new ArgumentException("Subtraction of textured or vertex-coloured meshes requires verified attribute transfer; the original is unchanged.");
                    uint before = target.Geometry.DataCRC(0);
                    double overlapVolume, overlapError;
                    using (var observation = IntersectionAnalysis.Observe(doc, keep, trim))
                    {
                        if ((string)observation.Report["overlap"]?["status"] != "positive_volume")
                            throw new ArgumentException("A confirmed positive overlap is required before subtraction.");
                        overlapVolume = (double)observation.Report["overlap"]["volume_model_units3"];
                        overlapError = (double?)observation.Report["overlap"]["numeric_uncertainty_model_units3"] ?? 0.0;
                    }
                    using (var replacement = Difference(doc, keep.Geometry, trim.Geometry))
                    {
                        if (replacement == null || IntersectionAnalysis.Unsupported(replacement) != null)
                            throw new InvalidOperationException("Subtraction did not produce one valid closed solid object; the original is unchanged.");
                        using (var extrusionBrep = trim.Geometry is Extrusion ? ((Extrusion)trim.Geometry).ToBrep() : null)
                        using (var originalMass = IntersectionAnalysis.Mass(extrusionBrep ?? trim.Geometry))
                        using (var resultMass = IntersectionAnalysis.Mass(replacement))
                        {
                            if (originalMass == null || resultMass == null || !IntersectionAnalysis.Finite(resultMass.Volume) ||
                                Math.Abs(resultMass.Volume) <= 0 || Math.Abs(resultMass.Volume) >= Math.Abs(originalMass.Volume))
                                throw new InvalidOperationException("Subtraction did not establish a smaller positive remaining volume; the original is unchanged.");
                            double tolerance = IntersectionAnalysis.Tolerance(doc);
                            double allowance = Math.Max(tolerance * tolerance * tolerance,
                                10 * (Math.Abs(originalMass.VolumeError) + Math.Abs(resultMass.VolumeError) + overlapError));
                            if (!IntersectionAnalysis.Finite(allowance) ||
                                Math.Abs(Math.Abs(originalMass.Volume) - Math.Abs(resultMass.Volume) - overlapVolume) > allowance)
                                throw new InvalidOperationException("Subtraction volume does not match the observed overlap within numeric uncertainty; the original is unchanged.");
                        }
                        uint after = replacement.DataCRC(0);
                        if (before == after) throw new InvalidOperationException("Subtraction produced no distinguishable geometry change.");
                        // Compute and validate before entering the mutation boundary. A single Replace retains
                        // the object ID, document attributes and group membership.
                        started = true;
                        return JObject.FromObject(new ScriptExecutor().ExecuteAction(doc, () =>
                        {
                            var current = doc.Objects.FindId(trim.RootId);
                            if (current == null || current.Geometry.DataCRC(0) != before ||
                                doc.Objects.FindId(keep.RootId)?.Geometry.DataCRC(0) != keep.Info.Value<uint>("geometry_crc"))
                                throw new InvalidOperationException("An operand changed before subtraction was applied.");
                            RequireEditable(doc, current);
                            var result = new Dictionary<string, object> {
                                ["edited"] = true, ["keep_id"] = keep.RootId.ToString("D"), ["trim_id"] = trim.RootId.ToString("D"),
                                ["previous_geometry_crc"] = before, ["geometry_crc"] = after,
                                ["operation"] = "subtract_keep_from_trim", ["geometry_kind"] = replacement.GetType().Name,
                                ["object_id_preserved"] = true
                            };
                            bool replaced = replacement is Mesh mesh ? doc.Objects.Replace(trim.RootId, mesh)
                                : doc.Objects.Replace(trim.RootId, (Brep)replacement);
                            if (!replaced) throw new InvalidOperationException("Rhino did not replace the trimmed object.");
                            Clear(doc);
                            return result;
                        }));
                    }
                }
                finally { sk?.Dispose(); st?.Dispose(); }
            }
            catch (Exception ex) { return Error("intersection_resolution_failed", ex, started); }
        }

        static GeometryBase Difference(RhinoDoc doc, GeometryBase keep, GeometryBase trim)
        {
            if (trim is Mesh)
            {
                using (var a = IntersectionAnalysis.AsMesh(trim, IntersectionAnalysis.Tolerance(doc)))
                using (var b = IntersectionAnalysis.AsMesh(keep, IntersectionAnalysis.Tolerance(doc)))
                {
                    var pieces = Mesh.CreateBooleanDifference(new[] { a }, new[] { b },
                        new MeshBooleanOptions { Tolerance = IntersectionAnalysis.MeshTolerance(doc) }, out var outcome);
                    try
                    {
                        if (outcome != Rhino.Commands.Result.Success || pieces == null || pieces.Length == 0)
                            throw new InvalidOperationException("Mesh subtraction failed or would remove the entire target; no edit was made.");
                        var result = new Mesh();
                        try { foreach (var piece in pieces) { if (piece == null || IntersectionAnalysis.Unsupported(piece) != null) throw new InvalidOperationException("Invalid mesh subtraction result."); result.Append(piece); } return result; }
                        catch { result.Dispose(); throw; }
                    }
                    finally { if (pieces != null) foreach (var piece in pieces) piece?.Dispose(); }
                }
            }
            using (var a = IntersectionAnalysis.AsBrep(trim)) using (var b = IntersectionAnalysis.AsBrep(keep))
            {
                var pieces = Brep.CreateBooleanDifference(a, b, IntersectionAnalysis.Tolerance(doc));
                try
                {
                    if (pieces == null || pieces.Length != 1 || pieces[0] == null)
                        throw new InvalidOperationException("Brep subtraction failed, removes the target, or creates multiple objects; no edit was made.");
                    var result = pieces[0]; pieces[0] = null;
                    return result;
                }
                finally { if (pieces != null) foreach (var piece in pieces) piece?.Dispose(); }
            }
        }

        static void RequireEditable(RhinoDoc doc, RhinoObject obj)
        {
            if (obj == null || obj.IsDeleted || obj.IsLocked || obj.IsReference || obj.IsInstanceDefinitionGeometry || obj.Attributes.Space != ActiveSpace.ModelSpace)
                throw new ArgumentException("The trim target must be an editable top-level model object.");
            var seen = new HashSet<Guid>(); var layer = doc.Layers.FindIndex(obj.Attributes.LayerIndex);
            while (layer != null)
            {
                if (!seen.Add(layer.Id) || layer.IsLocked) throw new ArgumentException("The target layer or an ancestor is locked.");
                layer = layer.ParentLayerId == Guid.Empty ? null : doc.Layers.FindId(layer.ParentLayerId);
            }
        }

        static void ValidatePair(RhinoDoc doc, IntersectionAnalysis.Member a, IntersectionAnalysis.Member b, string state)
        {
            if (a.Key == b.Key) throw new ArgumentException("Choose two distinct occurrences.");
            if (String.IsNullOrEmpty(state) || state != IntersectionAnalysis.PairState(doc, a, b))
                throw new ArgumentException("The pair state changed or was not supplied; inspect this pair again.");
        }

        public static void Clear(RhinoDoc doc)
        {
            if (Previews.TryGetValue(doc.RuntimeSerialNumber, out var old)) { Previews.Remove(doc.RuntimeSerialNumber); old.Dispose(); }
            doc.Views.Redraw();
        }

        static JObject Error(string code, Exception ex, bool started) => new JObject {
            ["status"] = "error", ["error_code"] = code, ["message"] = ex.Message,
            ["mutation_state"] = started ? "unknown" : "not_started", ["requires_reconciliation"] = started
        };

        sealed class Preview : DisplayConduit, IDisposable
        {
            readonly uint docSerial;
            readonly Guid viewId;
            readonly List<Mesh> meshes = new List<Mesh>();
            readonly List<Brep> breps = new List<Brep>();
            readonly List<string> labels = new List<string>();
            readonly DisplayMaterial material = new DisplayMaterial(Color.FromArgb(235, 35, 55), 0.65);
            readonly string label;
            BoundingBox bounds = BoundingBox.Empty;
            bool attached, disposed;
            internal Preview(RhinoDoc doc, Guid viewportId, IEnumerable<GeometryBase> regions, string pairId, IList<string> regionLabels = null)
            {
                docSerial = doc.RuntimeSerialNumber; viewId = viewportId; label = pairId.Substring(0, Math.Min(8, pairId.Length));
                try
                {
                    foreach (var geometry in regions)
                    {
                        var mesh = IntersectionAnalysis.AsMesh(geometry, IntersectionAnalysis.Tolerance(doc));
                        meshes.Add(mesh); bounds.Union(mesh.GetBoundingBox(true));
                        breps.Add(geometry is Brep brep ? brep.DuplicateBrep() : null);
                        labels.Add(regionLabels == null ? label : regionLabels[labels.Count].Substring(0, 8));
                        if (meshes.Sum(m => (long)m.Faces.Count) > 2000000)
                            throw new ArgumentException("Preview exceeds two million mesh faces; narrow the scope.");
                    }
                }
                catch { Dispose(); throw; }
            }
            internal void Attach()
            {
                RhinoDoc.AddRhinoObject += Changed; RhinoDoc.DeleteRhinoObject += Changed; RhinoDoc.UndeleteRhinoObject += Changed;
                RhinoDoc.ReplaceRhinoObject += Replaced; RhinoDoc.ModifyObjectAttributes += Attributes;
                RhinoDoc.InstanceDefinitionTableEvent += Definition; RhinoDoc.CloseDocument += Closed;
                attached = true; Enabled = true;
            }
            bool Matches(DrawEventArgs e) => !disposed && e.RhinoDoc?.RuntimeSerialNumber == docSerial && e.Viewport.Id == viewId;
            protected override void CalculateBoundingBox(CalculateBoundingBoxEventArgs e) { if (!disposed && e.RhinoDoc?.RuntimeSerialNumber == docSerial && e.Viewport.Id == viewId) e.IncludeBoundingBox(bounds); }
            protected override void DrawForeground(DrawEventArgs e)
            {
                if (!Matches(e)) return;
                for (int i = 0; i < meshes.Count; i++)
                {
                    e.Display.DrawMeshShaded(meshes[i], material);
                    if (breps[i] != null) e.Display.DrawBrepWires(breps[i], Color.White, 1);
                    else e.Display.DrawMeshWires(meshes[i], Color.White, 1);
                    e.Display.DrawDot(meshes[i].GetBoundingBox(true).Center, labels[i], Color.DarkRed, Color.White);
                }
            }
            void Changed(object sender, RhinoObjectEventArgs e) { if (e.TheObject?.Document?.RuntimeSerialNumber == docSerial) Drop(); }
            void Replaced(object sender, RhinoReplaceObjectEventArgs e) { if (e.Document?.RuntimeSerialNumber == docSerial) Drop(); }
            void Attributes(object sender, RhinoModifyObjectAttributesEventArgs e) { if (e.Document?.RuntimeSerialNumber == docSerial) Drop(); }
            void Definition(object sender, Rhino.DocObjects.Tables.InstanceDefinitionTableEventArgs e) { if (e.Document?.RuntimeSerialNumber == docSerial) Drop(); }
            void Closed(object sender, DocumentEventArgs e) { if (e.Document?.RuntimeSerialNumber == docSerial) Drop(); }
            void Drop() { Previews.Remove(docSerial); Dispose(); }
            public void Dispose()
            {
                if (disposed) return; disposed = true; Enabled = false;
                if (attached)
                {
                    RhinoDoc.AddRhinoObject -= Changed; RhinoDoc.DeleteRhinoObject -= Changed; RhinoDoc.UndeleteRhinoObject -= Changed;
                    RhinoDoc.ReplaceRhinoObject -= Replaced; RhinoDoc.ModifyObjectAttributes -= Attributes;
                    RhinoDoc.InstanceDefinitionTableEvent -= Definition; RhinoDoc.CloseDocument -= Closed;
                }
                foreach (var mesh in meshes) mesh.Dispose(); meshes.Clear();
                foreach (var brep in breps) brep?.Dispose(); breps.Clear(); material.Dispose();
            }
        }
    }
}
