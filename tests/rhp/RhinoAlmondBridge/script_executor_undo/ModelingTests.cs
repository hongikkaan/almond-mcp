using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.DocObjects.Tables;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    public static class ModelingTests
    {
        public static string RunAll(string directory)
        {
            var lines = new List<string>();
            Run(lines, directory, "factory works with batch RhinoCommon additions and one Undo", doc =>
            {
                string before = MaterialState(doc);
                using var events = new MaterialEventTrace(doc);
                var result = new ScriptExecutor().Execute(
                    "public class Script { public static object Run(RhinoDoc doc) { " +
                    "var a = RhinoAlmondBridge.ModelingMaterials.CreateAttributes(doc, \"wood-oak\"); " +
                    "a.Name = \"free object name\"; for (int i=0;i<100;i++) doc.Objects.AddPoint(new Point3d(i,0,0), a); " +
                    "doc.Objects.AddBrep(new BoundingBox(0,0,0,10,10,10).ToBrep(), a); " +
                    "return new { count = 101 }; } }", doc);
                Check(result.Status == "success", result.Message);
                var all = doc.Objects.GetObjectList(ObjectType.AnyObject).ToArray();
                Check(all.Length == 101 && all.All(o => doc.Layers[o.Attributes.LayerIndex].FullPath == "M::wood::wood-oak"), "Batch layer assignment failed.");
                Check(all.All(o => o.Attributes.Name == "free object name"), "Names were changed.");
                Check(doc.Layers.Count(l => !l.IsDeleted) == 4 && doc.RenderMaterials.Count(m => m != null) == 1,
                    "Unused layers or materials were created. Before: " + before + "; after: " + MaterialState(doc) + "; " + events);
                var shared = doc.RenderMaterials.First(m => m != null);
                Guid renderId = shared.Id;
                Check(all.All(o => doc.Materials[o.Attributes.MaterialIndex].RenderMaterialInstanceId == renderId),
                    "Batch objects do not share one render material identity.");
                using (var simulation = shared.ToMaterial(Rhino.Render.RenderTexture.TextureGeneration.Allow))
                {
                    var expected = doc.Materials[all[0].Attributes.MaterialIndex].PhysicallyBased;
                    Check(simulation.IsPhysicallyBased && Math.Abs(simulation.PhysicallyBased.Metallic - expected.Metallic) < 0.00001 &&
                        Math.Abs(simulation.PhysicallyBased.Roughness - expected.Roughness) < 0.00001 &&
                        Math.Abs(simulation.PhysicallyBased.Opacity - expected.Opacity) < 0.00001 &&
                        Math.Abs(simulation.PhysicallyBased.BaseColor.R - expected.BaseColor.R) < 0.00001 &&
                        Math.Abs(simulation.PhysicallyBased.BaseColor.G - expected.BaseColor.G) < 0.00001 &&
                        Math.Abs(simulation.PhysicallyBased.BaseColor.B - expected.BaseColor.B) < 0.00001,
                        "Shared rendering PBR channels differ from the material recipe.");
                }
                Check(all.All(o => o.Attributes.GetUserStrings().Count == 1), "Duplicated material metadata was stamped.");
                var repeated = new ScriptExecutor().ExecuteAction(doc, () =>
                    ModelingMaterials.Apply(doc, "wood-oak", all.Select(o => o.Id)));
                Success(repeated);
                Check(((JArray)repeated.Result["changed_guids"]).Count == 0 && doc.RenderMaterials.Count(m => m != null) == 1,
                    "Repeated assignment created changes or another shared render material.");
                Undo(doc);
                Check(!doc.Objects.GetObjectList(ObjectType.AnyObject).Any() && !doc.RenderMaterials.Any(m => m != null),
                    "Batch Undo left geometry or render material.");
                Redo(doc);
                Check(doc.Objects.GetObjectList(ObjectType.AnyObject).Count() == 101 && doc.RenderMaterials.Find(renderId) != null,
                    "Batch Redo lost geometry or the shared render material identity.");
            });
            Run(lines, directory, "postprocess sees final direct attributes after Add", doc =>
            {
                using var events = new MaterialEventTrace(doc);
                int material = CustomMaterial(doc, "Final / concrete");
                Guid id = Guid.Empty;
                Success(new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    id = doc.Objects.AddPoint(Point3d.Origin);
                    var attrs = doc.Objects.FindId(id).Attributes.Duplicate();
                    attrs.MaterialSource = ObjectMaterialSource.MaterialFromObject;
                    attrs.MaterialIndex = material;
                    Check(doc.Objects.ModifyAttributes(id, attrs, true), "Final attrs failed.");
                    return null;
                }));
                Check(ModelingMaterials.TryLayerForMaterial(doc, material, out string layer), "No custom layer path.");
                Check(Layer(doc, id) == layer && layer.StartsWith("M::Custom::Final _ concrete__"),
                    "Final material not routed. actual=" + Layer(doc, id) + "; expected=" + layer + "; " + MaterialState(doc) + "; " + events);
                Undo(doc);
                Check(doc.Objects.FindId(id) == null, "Object not undone.");
                Redo(doc);
                Check(Layer(doc, id) == layer, "Postprocess layer not redone.");
            }, foreground: true);
            Run(lines, directory, "direct material reassignment and rename route existing objects", doc =>
            {
                using var events = new MaterialEventTrace(doc);
                var id = doc.Objects.AddPoint(Point3d.Origin);
                int material = CustomMaterial(doc, "first");
                Success(new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    var attrs = doc.Objects.FindId(id).Attributes.Duplicate();
                    attrs.MaterialIndex = material;
                    attrs.MaterialSource = ObjectMaterialSource.MaterialFromObject;
                    doc.Objects.ModifyAttributes(id, attrs, true);
                    return null;
                }));
                string firstLayer = Layer(doc, id);
                Success(new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    var changed = new Material(doc.Materials[material]);
                    changed.Name = "second";
                    Check(doc.Materials.Modify(changed, material, true), "Material rename failed.");
                    return null;
                }));
                Check(Layer(doc, id) != firstLayer && Layer(doc, id).Contains("second__"),
                    "Material table change not routed. first=" + firstLayer + "; actual=" + Layer(doc, id) + "; " + MaterialState(doc) + "; " + events);
                Undo(doc);
                Check(Layer(doc, id) == firstLayer && doc.Materials[material].Name == "first", "Material/layer Undo diverged.");
            }, foreground: true);
            Run(lines, directory, "ByLayer ByParent and unrelated name edits retain layers", doc =>
            {
                int custom = doc.Layers.Add("Intentional", Color.Blue);
                Guid a = Guid.Empty, b = Guid.Empty;
                Success(new ScriptExecutor().ExecuteAction(doc, () =>
                {
                    a = doc.Objects.AddPoint(Point3d.Origin, new ObjectAttributes { LayerIndex = custom });
                    b = doc.Objects.AddPoint(new Point3d(1,0,0), new ObjectAttributes {
                        LayerIndex = custom, MaterialSource = ObjectMaterialSource.MaterialFromParent });
                    return null;
                }));
                Check(Layer(doc, a) == "Intentional" && Layer(doc, b) == "Intentional", "Inherited material was guessed.");
                int material = CustomMaterial(doc, "explicit");
                var attrs = doc.Objects.FindId(a).Attributes.Duplicate();
                attrs.MaterialIndex = material; attrs.MaterialSource = ObjectMaterialSource.MaterialFromObject;
                doc.Objects.ModifyAttributes(a, attrs, true);
                Check(Layer(doc, a) == "Intentional", "Collector leaked outside its operation.");
                Success(new ScriptExecutor().ExecuteAction(doc, () => {
                    var next = doc.Objects.FindId(a).Attributes.Duplicate(); next.Name = "only name";
                    doc.Objects.ModifyAttributes(a, next, true); return null;
                }));
                Check(Layer(doc, a) == "Intentional", "Unrelated attribute edit rerouted material.");
            }, foreground: true);
            Run(lines, directory, "metadata-only material operation keeps actual material and no dimensions", doc =>
            {
                Guid id = Guid.Empty;
                Success(new ScriptExecutor().ExecuteAction(doc, () => {
                    id = doc.Objects.AddPoint(Point3d.Origin, ModelingMaterials.CreateAttributes(doc, "wood-oak"));
                    return null;
                }));
                var before = doc.Objects.FindId(id).Attributes.Duplicate();
                int materials = doc.Materials.Count, layers = doc.Layers.Count;
                Success(new ScriptExecutor().ExecuteAction(doc, () => ModelingMaterials.Apply(doc, "steel-galvanized",
                    new[] { id }, new Dictionary<string,string> { ["almond:floor"] = "L02", ["almond:construction_detail"] = "Facade head A" }, false, true)));
                var after = doc.Objects.FindId(id).Attributes;
                Check(after.MaterialIndex == before.MaterialIndex && after.LayerIndex == before.LayerIndex &&
                    after.GetUserString("almond:material_id") == "wood-oak", "Metadata-only changed material identity.");
                Check(after.GetUserString("almond:floor") == "L02" && after.GetUserString("almond:construction_detail") == "Facade head A", "Missing requested metadata.");
                Check(doc.Materials.Count == materials && doc.Layers.Count == layers &&
                    doc.Objects.GetObjectList(ObjectType.AnyObject).Count() == 1, "Metadata created material/layer/dimensions.");
                Success(new ScriptExecutor().ExecuteAction(doc, () => ModelingMaterials.Apply(doc, "wood-oak", new[] { id }, null, false, false)));
                Check(doc.Objects.FindId(id).Attributes.GetUserStrings().Count == 3, "No-op changed metadata.");
            });
            Run(lines, directory, "material metadata rejects ownership and provenance before mutation", doc =>
            {
                var id = doc.Objects.AddPoint(Point3d.Origin);
                int materials = doc.Materials.Count, layers = doc.Layers.Count;
                var blocked = new[] { "component_id", "component_record", "sheet_id", "sheet_metadata", "asset_id",
                    "asset_metadata", "passport", "material_id", "section", "base_color" }
                    .Select(ModelingMetadata.Key).Concat(new[] { "almond:component_name", "almond:scene_ids", "custom:unapproved" });
                foreach (string key in blocked)
                {
                    var metadata = new Dictionary<string,string> { ["almond:floor"] = "L02", [key] = "must reject" };
                    foreach (bool existing in new[] { false, true })
                    {
                        bool rejected = false;
                        try
                        {
                            if (existing) ModelingMaterials.Apply(doc, "wood-oak", new[] { id }, metadata);
                            else ModelingMaterials.CreateAttributes(doc, "wood-oak", metadata);
                        }
                        catch (ArgumentException) { rejected = true; }
                        Check(rejected, "Accepted protected metadata: " + key);
                    }
                }
                Check(doc.Materials.Count == materials && doc.Layers.Count == layers &&
                    doc.Objects.FindId(id).Attributes.GetUserStrings().Count == 0,
                    "Rejected metadata created document state.");
            });
            Run(lines, directory, "material changes preserve source ownership provenance and names", doc =>
            {
                var source = new ObjectAttributes { Name = "Existing component member" };
                source.SetUserString("almond:component_id", "owner-1");
                source.SetUserString("almond:passport", "existing provenance");
                source.SetUserString("custom:keep", "original");
                var metadata = new Dictionary<string,string> {
                    ["almond:floor"] = "L02", ["almond:construction_detail"] = "Wall A",
                    ["almond:structural_role"] = "column"
                };
                Guid id = Guid.Empty;
                Success(new ScriptExecutor().ExecuteAction(doc, () => {
                    var attrs = ModelingMaterials.CreateAttributes(doc, "wood-oak", metadata, source);
                    id = doc.Objects.AddPoint(Point3d.Origin, attrs);
                    return null;
                }));
                Success(new ScriptExecutor().ExecuteAction(doc, () =>
                    ModelingMaterials.Apply(doc, "steel-galvanized", new[] { id }, metadata)));
                var after = doc.Objects.FindId(id).Attributes;
                Check(after.Name == source.Name && after.GetUserString("almond:component_id") == "owner-1" &&
                    after.GetUserString("almond:passport") == "existing provenance" &&
                    after.GetUserString("custom:keep") == "original", "Material change overwrote source metadata.");
                Check(after.GetUserString("almond:floor") == "L02" && after.GetUserString("almond:construction_detail") == "Wall A" &&
                    after.GetUserString("almond:structural_role") == "column" &&
                    after.GetUserString("almond:material_id") == "steel-galvanized", "Allowed material metadata was lost.");
                Check(source.GetUserStrings().Count == 3, "Factory changed the caller's source attributes.");
            });
            Run(lines, directory, "conflicting material identity rejects before changing the model", doc =>
            {
                var material = new Material { Name = "ALMOND::wood-oak", DiffuseColor = Color.Red };
                material.SetUserString("almond:material_id", "steel-galvanized");
                int index = doc.Materials.Add(material);
                var id = doc.Objects.AddPoint(Point3d.Origin);
                int materials = doc.Materials.Count, layers = doc.Layers.Count;
                var result = new ScriptExecutor().ExecuteAction(doc, () =>
                    ModelingMaterials.Apply(doc, "wood-oak", new[] { id }));
                Check(result.Status == "runtime_error" && result.Message.Contains("conflicting material_id"),
                    "Conflicting identity was accepted: " + result.Message);
                var attrs = doc.Objects.FindId(id).Attributes;
                Check(doc.Materials.Count == materials && doc.Layers.Count == layers &&
                    attrs.MaterialSource == ObjectMaterialSource.MaterialFromLayer && attrs.GetUserStrings().Count == 0 &&
                    doc.Materials[index].GetUserString("almond:material_id") == "steel-galvanized",
                    "Rejected identity changed existing material or object attributes.");
            });
            Run(lines, directory, "failed factory batch rolls back material layers and objects", doc =>
            {
                var result = new ScriptExecutor().ExecuteAction(doc, () => {
                    var attrs = ModelingMaterials.CreateAttributes(doc, "wood-oak");
                    doc.Objects.AddPoint(Point3d.Origin, attrs);
                    throw new InvalidOperationException("expected");
                });
                Check(result.Status == "runtime_error", result.Message);
                Check(!doc.Objects.GetObjectList(ObjectType.AnyObject).Any() &&
                    doc.Layers.Count(l => !l.IsDeleted) == 1 && doc.Materials.All(m => m.IsDeleted) &&
                    !doc.RenderMaterials.Any(m => m != null), "Failed batch left state.");
            });
            Run(lines, directory, "lost Undo ownership prevents material postprocess", doc =>
            {
                int material = CustomMaterial(doc, "ownership");
                Guid id = Guid.Empty;
                var result = new ScriptExecutor().ExecuteAction(doc, () => {
                    id = doc.Objects.AddPoint(Point3d.Origin, new ObjectAttributes {
                        MaterialIndex = material, MaterialSource = ObjectMaterialSource.MaterialFromObject });
                    doc.EndUndoRecord(doc.CurrentUndoRecordSerialNumber);
                    return null;
                });
                Check(result.Status == "runtime_error" && result.Message.Contains("protect other work"), "Lost ownership not reported.");
                Check(Layer(doc, id) == "Default" && doc.Layers.Count == 1, "Postprocess ran outside owned record.");
            }, foreground: true);
            Run(lines, directory, "component group metadata persists through update Undo Redo and reopen", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin), b = doc.Objects.AddPoint(new Point3d(10,20,30));
                var created = ComponentRegistry.Handle(doc, Request(doc, "upsert", "c1", new[] {a,b}));
                NativeSuccess(created);
                Guid groupId = Guid.Parse((string)created["component"]["rhino_group_id"]);
                var update = Request(doc, "upsert", "c1", new[] {a,b}, groupId);
                update["name"] = "Renamed facade"; update["scene_ids"] = new JArray("inside", "outside");
                update["expected_object_ids"] = new JArray(a.ToString(), b.ToString());
                NativeSuccess(ComponentRegistry.Handle(doc, update));
                Check((string)ComponentRegistry.Handle(doc, Request(doc, "inspect", "c1", null, groupId))["component"]["name"] == "Renamed facade", "Name update missing.");
                Undo(doc);
                var old = ComponentRegistry.Handle(doc, Request(doc, "inspect", "c1", null, groupId));
                NativeSuccess(old);
                Check((string)old["component"]["name"] == "Facade" && ((JArray)old["component"]["scene_ids"]).Count == 1, "Group metadata was not undone.");
                Redo(doc);
                NativeSuccess(ComponentRegistry.Handle(doc, Request(doc, "inspect", "c1", null, groupId)));
                Check((string)ComponentRegistry.Handle(doc, Request(doc, "inspect", "c1", null, groupId))["component"]["name"] == "Renamed facade", "Group metadata was not redone.");
                Check(doc.WriteFile(doc.Path, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Save failed.");
                using (var reopened = RhinoDoc.OpenHeadless(doc.Path))
                    NativeSuccess(ComponentRegistry.Handle(reopened, Request(reopened, "inspect", "c1", null, groupId)));
            });
            Run(lines, directory, "one Component owner while ordinary groups remain usable", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                int ordinary = doc.Groups.Add("Ordinary", new[] { a });
                var request = Request(doc, "upsert", "c1", new[] {a}, doc.Groups[ordinary].Id);
                NativeSuccess(ComponentRegistry.Handle(doc, request));
                var second = ComponentRegistry.Handle(doc, Request(doc, "upsert", "c2", new[] {a}));
                Rejected(second);
                Check(doc.Groups.Count(g => !g.IsDeleted) == 1 && doc.Groups.GroupMembers(ordinary).Length == 1, "Rejection changed groups.");
            });
            Run(lines, directory, "component unregister keeps geometry and ordinary group and Undo restores ownership", doc =>
            {
                var id = doc.Objects.AddPoint(Point3d.Origin);
                var made = ComponentRegistry.Handle(doc, Request(doc, "upsert", "c1", new[] {id}));
                NativeSuccess(made);
                var gid = Guid.Parse((string)made["component"]["rhino_group_id"]);
                var remove = Request(doc, "unregister", "c1", new[] {id}, gid);
                remove["expected_object_ids"] = new JArray(id.ToString());
                NativeSuccess(ComponentRegistry.Handle(doc, remove));
                Check(doc.Objects.FindId(id) != null && doc.Groups.GroupMembers(doc.Groups.FindId(gid).Index).Length == 1 &&
                    String.IsNullOrEmpty(doc.Objects.FindId(id).Attributes.GetUserString("almond:component_id")), "Unregister removed geometry/group or retained ownership.");
                Undo(doc);
                NativeSuccess(ComponentRegistry.Handle(doc, Request(doc, "inspect", "c1", null, gid)));
                Redo(doc);
                Check(String.IsNullOrEmpty(doc.Objects.FindId(id).Attributes.GetUserString("almond:component_record")), "Unregister redo left Component metadata.");
                var inspect = Request(doc, "inspect", "c1", null, gid);
                inspect["expected_object_ids"] = new JArray(id.ToString());
                var proof = ComponentRegistry.Handle(doc, inspect);
                NativeSuccess(proof);
                Check((string)proof["component"]["registration_status"] == "unregistered", "Unregistration cannot be reconciled by inspection.");
            });
            Run(lines, directory, "changed membership and stale detached stamps require explicit repair", doc =>
            {
                var a = doc.Objects.AddPoint(Point3d.Origin);
                var b = doc.Objects.AddPoint(new Point3d(1,0,0));
                var made = ComponentRegistry.Handle(doc, Request(doc, "upsert", "c1", new[] {a,b}));
                NativeSuccess(made);
                var gid = Guid.Parse((string)made["component"]["rhino_group_id"]);
                var attrs = doc.Objects.FindId(a).Attributes.Duplicate();
                attrs.RemoveFromGroup(doc.Groups.FindId(gid).Index);
                doc.Objects.ModifyAttributes(a, attrs, true);
                var remove = Request(doc, "unregister", "c1", new[] {a,b}, gid);
                remove["expected_object_ids"] = new JArray(a.ToString(), b.ToString());
                Rejected(ComponentRegistry.Handle(doc, remove));
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "inspect", "c1", null, gid)));
                Check(doc.Objects.FindId(b).Attributes.GetUserString("almond:component_id") == "c1", "Rejected reconciliation cleared ownership.");
            });
            Run(lines, directory, "nested block occurrence bounds are world millimetres without tagging definitions", doc =>
            {
                doc.AdjustModelUnitSystem(UnitSystem.Meters, false);
                using (var box = new BoundingBox(0,0,0,1,1,1).ToBrep())
                {
                    int inner = doc.InstanceDefinitions.Add("inner", "", Point3d.Origin, new[] { box }, new[] { new ObjectAttributes() });
                    using (var nested = new InstanceReferenceGeometry(doc.InstanceDefinitions[inner].Id, Transform.Translation(2,0,0)))
                    {
                        int outer = doc.InstanceDefinitions.Add("outer", "", Point3d.Origin, new GeometryBase[] { nested }, new[] { new ObjectAttributes() });
                        var id = doc.Objects.AddInstanceObject(outer, Transform.Translation(10,0,0));
                        var made = ComponentRegistry.Handle(doc, Request(doc, "upsert", "c1", new[] {id}));
                        NativeSuccess(made);
                        var bounds = made["component"]["objects"][0]["bounds_mm"].Values<double>().ToArray();
                        Check(Math.Abs(bounds[0] - 12000) < 0.001 && Math.Abs(bounds[3] - 13000) < 0.001, "Block bounds ignored nesting, transform or units.");
                        Check(doc.InstanceDefinitions[inner].GetObjects().All(o => String.IsNullOrEmpty(o.Attributes.GetUserString("almond:component_id"))), "Shared definition was stamped.");
                        Rejected(ComponentRegistry.Handle(doc, Request(doc, "upsert", "c2", doc.InstanceDefinitions[inner].GetObjects().Select(o => o.Id).ToArray())));
                    }
                }
            });
            Run(lines, directory, "wrong document missing GUID empty scenes and BlockEdit clones reject before mutation", doc =>
            {
                var id = doc.Objects.AddPoint(Point3d.Origin);
                var request = Request(doc, "upsert", "c1", new[] {id});
                request["expected_model_path"] = Path.Combine(directory, "wrong.3dm");
                Rejected(ComponentRegistry.Handle(doc, request));
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "upsert", "c1", new[] {Guid.NewGuid()})));
                request = Request(doc, "upsert", "c1", new[] {id}); request["scene_ids"] = new JArray();
                Rejected(ComponentRegistry.Handle(doc, request));
                var attrs = doc.Objects.FindId(id).Attributes.Duplicate();
                attrs.SetUserString("$TempBlockEditUserData$", "fixture");
                doc.Objects.ModifyAttributes(id, attrs, true);
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "upsert", "c1", new[] {id})));
                Check(doc.Groups.Count == 0, "Rejected input created a group.");
            });
            string report = String.Join("\n", lines);
            if (lines.Any(l => l.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + lines.Count + "/" + lines.Count + " modeling cases.";
        }

        private static void Run(List<string> lines, string directory, string name, Action<RhinoDoc> test, bool foreground = false)
        {
            string path = Path.Combine(directory, "modeling-" + Guid.NewGuid().ToString("N") + ".3dm");
            using (var fixture = RhinoDoc.CreateHeadless(null))
            {
                fixture.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
                Check(fixture.WriteFile(path, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }), "Fixture save failed.");
            }
            // The test runner owns a separate Rhino process. Rhino 8
            // static document events are raised only for foreground documents.
            bool alreadyOpen = false;
            using (var doc = foreground ? RhinoDoc.Open(path, out alreadyOpen) : RhinoDoc.OpenHeadless(path))
            {
                try
                {
                    Check(doc != null && !alreadyOpen, "Fixture document could not be opened fresh.");
                    Check(doc.IsHeadless != foreground, "Fixture document mode does not match the requested event contract.");
                    doc.UndoRecordingEnabled = true;
                    Check(!String.IsNullOrEmpty(doc.Path), "Fixture has no saved path.");
                    test(doc);
                    Check(!doc.UndoRecordingIsActive && !doc.UndoActive && !doc.RedoActive, "Leaked Undo operation.");
                    lines.Add("PASS " + name);
                }
                catch (Exception error) { lines.Add("FAIL " + name + ": " + error); }
                finally { if (doc != null) doc.Modified = false; }
            }
        }
        private static JObject Request(RhinoDoc doc, string action, string id, Guid[] objects, Guid group = default(Guid))
        {
            return new JObject { ["type"] = "design_component", ["action"] = action,
                ["expected_model_path"] = doc.Path, ["component_id"] = id, ["name"] = "Facade",
                ["object_ids"] = new JArray((objects ?? new Guid[0]).Select(g => g.ToString())),
                ["scene_ids"] = new JArray("inside"), ["rhino_group_id"] = group == Guid.Empty ? "" : group.ToString() };
        }
        private static string MaterialState(RhinoDoc doc)
        {
            return "headless=" + doc.IsHeadless + "; layer-table=" + doc.Layers.Count + "; live-layers=[" +
                String.Join(", ", doc.Layers.Where(l => !l.IsDeleted).Select(l => l.Index + ":" + l.FullPath)) +
                "]; material-table=" + doc.Materials.Count + "; live-material-groups=[" +
                String.Join(", ", doc.Materials.Where(m => !m.IsDeleted)
                    .GroupBy(m => m.Name + ":render=" + m.RenderMaterialInstanceId)
                    .Select(g => g.Key + " x" + g.Count())) + "]; render-table=" + doc.RenderMaterials.Count +
                "; render-materials=[" + String.Join(", ", doc.RenderMaterials.Where(m => m != null).Select(m =>
                    m.Id + ":" + m.Name + ":hidden=" + m.Hidden + ":auto=" + m.IsHiddenByAutoDelete)) + "]";
        }
        private sealed class MaterialEventTrace : IDisposable
        {
            private readonly RhinoDoc doc;
            private int adds, ownedAdds, attributes, ownedAttributes, materials, ownedMaterials, modified;
            public MaterialEventTrace(RhinoDoc document)
            {
                doc = document;
                RhinoDoc.AddRhinoObject += Added;
                RhinoDoc.ModifyObjectAttributes += Attributes;
                RhinoDoc.MaterialTableEvent += Materials;
            }
            private void Added(object sender, RhinoObjectEventArgs e)
            {
                adds++;
                if (e.TheObject?.Document?.RuntimeSerialNumber == doc.RuntimeSerialNumber) ownedAdds++;
            }
            private void Attributes(object sender, RhinoModifyObjectAttributesEventArgs e)
            {
                attributes++;
                if (e.Document?.RuntimeSerialNumber == doc.RuntimeSerialNumber) ownedAttributes++;
            }
            private void Materials(object sender, MaterialTableEventArgs e)
            {
                materials++;
                if (e.Document?.RuntimeSerialNumber == doc.RuntimeSerialNumber) ownedMaterials++;
                if (e.EventType == MaterialTableEventType.Modified) modified++;
            }
            public override string ToString()
            {
                return "static-events all/owned: Add=" + adds + "/" + ownedAdds + ", Attributes=" +
                    attributes + "/" + ownedAttributes + ", Materials=" + materials + "/" + ownedMaterials +
                    ", MaterialModified=" + modified;
            }
            public void Dispose()
            {
                RhinoDoc.AddRhinoObject -= Added;
                RhinoDoc.ModifyObjectAttributes -= Attributes;
                RhinoDoc.MaterialTableEvent -= Materials;
            }
        }
        private static int CustomMaterial(RhinoDoc doc, string name) { return doc.Materials.Add(new Material { Name = name, DiffuseColor = Color.Gray }); }
        private static string Layer(RhinoDoc doc, Guid id) { return doc.Layers[doc.Objects.FindId(id).Attributes.LayerIndex].FullPath; }
        private static void Success(ScriptResult result) { Check(result.Status == "success", result.Message); }
        private static void NativeSuccess(JObject result) { Check((string)result["status"] == "success", result.ToString()); }
        private static void Rejected(JObject result) { Check((string)result["status"] == "error" && (bool?)result["mutation_applied"] == false, result.ToString()); }
        private static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        private static void Undo(RhinoDoc doc) { UndoRedo(doc, false); }
        private static void Redo(RhinoDoc doc) { UndoRedo(doc, true); }
        private static void UndoRedo(RhinoDoc doc, bool redo)
        {
            Check(!doc.UndoRecordingIsActive, "Record active before Undo/Redo.");
            uint next = doc.NextUndoRecordSerialNumber;
            try { Check(redo ? doc.Redo() : doc.Undo(), "Undo/Redo failed."); }
            finally
            {
                if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == next)
                    Check(doc.EndUndoRecord(next), "Could not close Undo/Redo record.");
            }
        }
    }
}
