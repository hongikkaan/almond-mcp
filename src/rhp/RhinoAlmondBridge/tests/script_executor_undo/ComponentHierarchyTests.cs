using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    // Separate from the existing single-level modeling tests; root owns runner wiring.
    public static class ComponentHierarchyTests
    {
        public static string RunAll(string directory)
        {
            var results = new List<string>();
            Run(results, directory, "parent group selects two child Components without owning child objects", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid b = doc.Objects.AddPoint(new Point3d(10, 20, 30));
                Guid g1 = Register(doc, "wall", new[] { a });
                Guid g2 = Register(doc, "door", new[] { b });
                var parent = Success(ComponentRegistry.Handle(doc,
                    Request(doc, "upsert", "facade", new Guid[0], new[] { "wall", "door" })));
                Guid parentGroup = Guid.Parse((string)parent["rhino_group_id"]);
                Check(parentGroup != g1 && parentGroup != g2, "Parent lacks its own group.");
                Check(((JArray)parent["objects"]).Count == 0 && ((JArray)parent["object_ids"]).Count == 0,
                    "Aggregate parent falsely owns child geometry.");
                Check(new HashSet<string>(parent["effective_object_ids"].Values<string>())
                    .SetEquals(new[] { a.ToString("D"), b.ToString("D") }), "Parent effective union differs.");
                Check(doc.Groups.GroupMembers(doc.Groups.FindId(parentGroup).Index).Select(o => o.Id).ToHashSet()
                    .SetEquals(new[] { a, b }), "Parent physical Rhino group must select descendant members.");
                Check(doc.Objects.FindId(a).Attributes.GetUserString("almond:component_id") == "wall" &&
                    doc.Objects.FindId(b).Attributes.GetUserString("almond:component_id") == "door",
                    "Parent stole a descendant's direct owner.");
                var wall = Inspect(doc, "wall", g1);
                Check((string)wall["parent_component_id"] == "facade", "Derived parent link is absent.");
                Check(((JArray)wall["child_component_ids"]).Count == 0, "Leaf gained unexpected descendants.");
                Check(new[] { a, b }.Any(id => JObject.Parse(
                    doc.Objects.FindId(id).Attributes.GetUserString("almond:component_record"))
                    .Properties().Count() >= 2),
                    "An existing member must host both child and parent group records.");
            });
            Run(results, directory, "leaf changes propagate ancestor group selection and affected snapshots", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid b = doc.Objects.AddPoint(new Point3d(10, 0, 0));
                Guid extra = doc.Objects.AddPoint(new Point3d(20, 0, 0));
                Guid leaf = Register(doc, "wall", new[] { a });
                Register(doc, "door", new[] { b });
                Guid parent = Register(doc, "facade", new Guid[0], new[] { "wall", "door" });
                var update = Request(doc, "upsert", "wall", new[] { a, extra });
                update["rhino_group_id"] = leaf.ToString("D");
                update["expected_object_ids"] = new JArray(a.ToString("D"));
                var reply = ComponentRegistry.Handle(doc, update);
                var wall = Success(reply);
                var affected = (JArray)reply["affected_components"];
                Check(affected.Any(item => (string)item["component_id"] == "facade"), "Ancestor change was omitted from affected_components.");
                Check(((JArray)wall["objects"]).Count == 2, "Leaf direct owner set did not update.");
                Check(doc.Groups.GroupMembers(doc.Groups.FindId(parent).Index).Select(o => o.Id).ToHashSet()
                    .SetEquals(new[] { a, extra, b }), "Parent group missed newly added leaf object.");
                Undo(doc);
                Check(!doc.Groups.GroupMembers(doc.Groups.FindId(parent).Index).Any(o => o.Id == extra) &&
                    doc.Objects.FindId(extra).Attributes.GetUserString("almond:component_id") == null,
                    "Undo did not restore the original ancestor membership and direct owner.");
                Redo(doc);
                Check(doc.Groups.GroupMembers(doc.Groups.FindId(parent).Index).Any(o => o.Id == extra),
                    "Redo did not restore the updated parent group.");
            });
            Run(results, directory, "inspect discovers manually added TextDots and sync adopts at deepest group", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid leaf = Register(doc, "panel", new[] { a });
                Guid parent = Register(doc, "facade", new Guid[0], new[] { "panel" });
                Guid note = doc.Objects.AddTextDot("fastener @ grid C", new Point3d(12, 34, 56));
                ManuallyAdd(doc, note, leaf);
                var observed = Inspect(doc, "facade", parent);
                Check((bool)observed["requires_sync"], "Read-only inspection hid a newly grouped note.");
                var pending = (JArray)observed["pending_objects"];
                Check(pending.Any(p => (string)p["rhino_guid"] == note.ToString("D") &&
                    (string)p["text"] == "fastener @ grid C" &&
                    Math.Abs((double)p["point_mm"][0] - 12) < 1e-8), "Pending TextDot text and world location were lost.");
                Check(observed["effective_object_ids"].Values<string>().Contains(note.ToString("D")),
                    "Pending TextDot absent from the effective IDs needed by outline.");
                Check(doc.Objects.FindId(note).Attributes.GetUserString("almond:component_id") == null,
                    "Read-only inspect silently adopted the note.");
                var syncRequest = Request(doc, "sync", "panel", null, null, leaf);
                syncRequest["expected_object_ids"] = new JArray(a.ToString("D"));
                syncRequest["expected_child_component_ids"] = new JArray();
                syncRequest["expected_effective_object_ids"] = new JArray(a.ToString("D"));
                var syncReply = ComponentRegistry.Handle(doc, syncRequest);
                Success(syncReply);
                Check(doc.Objects.FindId(note).Attributes.GetUserString("almond:component_id") == "panel",
                    "Explicit sync did not adopt an unambiguous pending TextDot.");
                Check(doc.Groups.GroupMembers(doc.Groups.FindId(parent).Index).Any(o => o.Id == note),
                    "Sync failed to normalize ancestor Rhino group membership.");
                Check(!(bool)Inspect(doc, "panel", leaf)["requires_sync"] &&
                    !(bool)Inspect(doc, "facade", parent)["requires_sync"], "Dirty flags remain after successful sync.");
                uint next = doc.NextUndoRecordSerialNumber;
                var unchanged = ComponentRegistry.Handle(doc, Request(doc, "sync", "panel", null, null, leaf));
                Success(unchanged);
                Check(doc.NextUndoRecordSerialNumber == next, "Unchanged sync created an Undo record.");
                Undo(doc);
                Check(doc.Objects.FindId(note).Attributes.GetUserString("almond:component_id") == null &&
                    !doc.Groups.GroupMembers(doc.Groups.FindId(parent).Index).Any(o => o.Id == note),
                    "Sync Undo did not restore pending ownership and parent membership.");
                Redo(doc);
                Check(doc.Objects.FindId(note).Attributes.GetUserString("almond:component_id") == "panel",
                    "Sync Redo failed.");
            });
            Run(results, directory, "parent-only TextDot adopts without stealing descendant owners", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Register(doc, "leaf", new[] { a });
                Guid root = Register(doc, "root", new Guid[0], new[] { "leaf" });
                Guid note = doc.Objects.AddTextDot("facade assembly note", new Point3d(1, 2, 3));
                ManuallyAdd(doc, note, root);
                var pending = Inspect(doc, "root", root);
                Check((bool)pending["requires_sync"] && ((JArray)pending["pending_objects"]).Count == 1,
                    "Parent-level annotation was not discovered.");
                Success(ComponentRegistry.Handle(doc, Request(doc, "sync", "root", null, null, root)));
                Check(doc.Objects.FindId(note).Attributes.GetUserString("almond:component_id") == "root" &&
                    doc.Objects.FindId(a).Attributes.GetUserString("almond:component_id") == "leaf",
                    "Parent sync changed descendant ownership.");
            });
            Run(results, directory, "multi-parent and cyclic relations reject; explicit detach enables reparent", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid b = doc.Objects.AddPoint(new Point3d(3, 0, 0));
                Guid c = doc.Objects.AddPoint(new Point3d(6, 0, 0));
                Guid leaf = Register(doc, "leaf", new[] { a });
                Register(doc, "other", new[] { b });
                Guid first = Register(doc, "parent1", new Guid[0], new[] { "leaf", "other" });
                Guid second = Register(doc, "parent2", new[] { c });
                var attach = Request(doc, "upsert", "parent2", new[] { c }, new[] { "leaf" }, second);
                Rejected(ComponentRegistry.Handle(doc, attach));
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "upsert", "leaf", new[] { a }, new[] { "parent1" }, leaf)));
                Check((string)Inspect(doc, "leaf", leaf)["parent_component_id"] == "parent1",
                    "Rejected topology mutation changed the parent.");
                Success(ComponentRegistry.Handle(doc, Request(doc, "upsert", "parent1", new Guid[0],
                    new[] { "other" }, first)));
                Check(Inspect(doc, "leaf", leaf)["parent_component_id"].Type == JTokenType.Null,
                    "Explicit detach did not release the child.");
                Success(ComponentRegistry.Handle(doc, attach));
                Check((string)Inspect(doc, "leaf", leaf)["parent_component_id"] == "parent2",
                    "Explicit reparent did not update the child's derived parent.");
                Check(doc.Groups.GroupMembers(doc.Groups.FindId(first).Index).Select(o => o.Id)
                    .ToHashSet().SetEquals(new[] { b }), "Old parent retained detached child geometry.");
                Check(doc.Groups.GroupMembers(doc.Groups.FindId(second).Index).Select(o => o.Id)
                    .ToHashSet().SetEquals(new[] { a, c }), "New parent did not select direct and child geometry.");
            });
            Run(results, directory, "stale copied owner and component record cannot be silently synced", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid b = doc.Objects.AddPoint(new Point3d(3, 0, 0));
                Guid leaf = Register(doc, "leaf", new[] { a });
                var attrs = doc.Objects.FindId(b).Attributes.Duplicate();
                attrs.SetUserString("almond:component_id", "leaf");
                Check(doc.Objects.ModifyAttributes(b, attrs, true), "Fixture owner stamp copy failed.");
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "inspect", "leaf", null, null, leaf)));
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "sync", "leaf", null, null, leaf)));
            });
            Run(results, directory, "legacy single-record metadata remains readable and migrates on edit", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid leaf = Register(doc, "legacy", new[] { a });
                var attrs = doc.Objects.FindId(a).Attributes.Duplicate();
                var map = JObject.Parse(attrs.GetUserString("almond:component_record"));
                var previous = (JObject)map[leaf.ToString("D")].DeepClone();
                previous.Remove("child_component_ids");
                Check(attrs.SetUserString("almond:component_record", previous.ToString(Formatting.None)) &&
                    doc.Objects.ModifyAttributes(a, attrs, true), "Could not simulate the old singleton record.");
                var read = Inspect(doc, "legacy", leaf);
                Check(((JArray)read["child_component_ids"]).Count == 0, "Old singleton failed read-only migration.");
                var request = Request(doc, "upsert", "legacy", new[] { a }, null, leaf);
                request["name"] = "Updated legacy";
                Success(ComponentRegistry.Handle(doc, request));
                var rewritten = JObject.Parse(doc.Objects.FindId(a).Attributes.GetUserString("almond:component_record"));
                Check(rewritten[leaf.ToString("D")] is JObject &&
                    (string)Inspect(doc, "legacy", leaf)["name"] == "Updated legacy",
                    "Legacy record was not migrated to undoable group-keyed map.");
                Undo(doc);
                Check((string)Inspect(doc, "legacy", leaf)["name"] == "Facade",
                    "Legacy-format record was not restored by Undo.");
            });
            Run(results, directory, "linked parent/child unregister requires explicit separation", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid b = doc.Objects.AddPoint(new Point3d(2, 0, 0));
                Guid leaf = Register(doc, "leaf", new[] { a });
                Register(doc, "other", new[] { b });
                Guid parent = Register(doc, "parent", new Guid[0], new[] { "leaf", "other" });
                Rejected(ComponentRegistry.Handle(doc, Request(doc, "unregister", "leaf", null, null, leaf)));
                var detach = Request(doc, "upsert", "parent", new Guid[0], new[] { "other" }, parent);
                Success(ComponentRegistry.Handle(doc, detach));
                var removed = ComponentRegistry.Handle(doc, Request(doc, "unregister", "leaf", null, null, leaf));
                Check((string)removed["status"] == "success", "Leaf unregistration after explicit detach failed.");
                Check(doc.Objects.FindId(a) != null && doc.Groups.FindId(leaf) != null &&
                    doc.Objects.FindId(a).Attributes.GetUserString("almond:component_id") == null &&
                    doc.Groups.GroupMembers(doc.Groups.FindId(parent).Index).Select(o => o.Id)
                        .ToHashSet().SetEquals(new[] { b }),
                    "Unregister removed Rhino geometry or an unrelated child.");
            });
            Run(results, directory, "root aggregate unregister preserves child ownership and proves recovery", doc =>
            {
                Guid a = doc.Objects.AddPoint(Point3d.Origin);
                Guid leaf = Register(doc, "leaf", new[] { a });
                Guid root = Register(doc, "root", new Guid[0], new[] { "leaf" });
                var remove = Request(doc, "unregister", "root", null, null, root);
                remove["expected_object_ids"] = new JArray();
                remove["expected_child_component_ids"] = new JArray("leaf");
                remove["expected_effective_object_ids"] = new JArray(a.ToString("D"));
                var result = ComponentRegistry.Handle(doc, remove);
                Check((string)result["status"] == "success" &&
                    ((JArray)result["detached_child_component_ids"]).Values<string>().SequenceEqual(new[] { "leaf" }) &&
                    ((JArray)result["affected_components"]).Any(item =>
                        (string)item["component_id"] == "leaf" &&
                        item["parent_component_id"].Type == JTokenType.Null),
                    "Root unregister response lacks detached-child snapshots: " + result);
                Check(doc.Groups.FindId(root) != null &&
                    doc.Groups.GroupMembers(doc.Groups.FindId(root).Index).Select(o => o.Id).ToHashSet()
                        .SetEquals(new[] { a }) &&
                    doc.Objects.FindId(a).Attributes.GetUserString("almond:component_id") == "leaf",
                    "Root removal changed the former ordinary group or descendant ownership.");
                Check(Inspect(doc, "leaf", leaf)["parent_component_id"].Type == JTokenType.Null,
                    "Removed root did not detach the child's derived parent.");
                var inspect = Request(doc, "inspect", "root", null, null, root);
                inspect["expected_object_ids"] = new JArray();
                inspect["expected_child_component_ids"] = new JArray("leaf");
                inspect["expected_effective_object_ids"] = new JArray(a.ToString("D"));
                var proof = ComponentRegistry.Handle(doc, inspect);
                Check((string)proof["status"] == "success" &&
                    (string)proof["component"]["registration_status"] == "unregistered" &&
                    (bool)proof["component"]["complete"] &&
                    proof["component"]["effective_object_ids"].Values<string>().SequenceEqual(new[] { a.ToString("D") }) &&
                    ((JArray)proof["affected_components"]).Any(item =>
                        (string)item["component_id"] == "leaf"),
                    "Explicit inspect failed to prove unregister after an uncertain DB commit: " + proof);
                Undo(doc);
                Check((string)Inspect(doc, "leaf", leaf)["parent_component_id"] == "root" &&
                    (string)Inspect(doc, "root", root)["component_id"] == "root",
                    "Root unregister Undo did not restore the hierarchy.");
                Redo(doc);
                Check((string)ComponentRegistry.Handle(doc, inspect)["component"]["registration_status"] == "unregistered",
                    "Root unregister Redo lost reconciliation proof.");
            });
            string report = String.Join("\n", results);
            if (results.Any(row => row.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + results.Count + "/" + results.Count + " Component hierarchy cases.";
        }

        private static Guid Register(RhinoDoc doc, string id, Guid[] owned, string[] children = null)
        {
            JObject response = ComponentRegistry.Handle(doc, Request(doc, "upsert", id, owned, children));
            JObject component = Success(response);
            return Guid.Parse((string)component["rhino_group_id"]);
        }

        private static JObject Request(RhinoDoc doc, string action, string id, Guid[] owned, string[] children = null,
            Guid group = default(Guid))
        {
            var request = new JObject {
                ["type"] = "design_component", ["action"] = action, ["expected_model_path"] = doc.Path,
                ["component_id"] = id, ["rhino_group_id"] = group == Guid.Empty ? "" : group.ToString("D"),
                ["name"] = "Facade", ["scene_ids"] = new JArray("inside"),
                ["object_ids"] = new JArray((owned ?? new Guid[0]).Select(v => v.ToString("D")))
            };
            if (children != null) request["child_component_ids"] = new JArray(children);
            return request;
        }

        private static JObject Inspect(RhinoDoc doc, string id, Guid group) =>
            Success(ComponentRegistry.Handle(doc, Request(doc, "inspect", id, null, null, group)));

        private static JObject Success(JObject result)
        {
            Check((string)result["status"] == "success", result.ToString(Formatting.None));
            return (JObject)result["component"];
        }
        private static void Rejected(JObject response) =>
            Check((string)response["status"] == "error" && (bool?)response["mutation_applied"] == false, response.ToString(Formatting.None));
        private static void ManuallyAdd(RhinoDoc doc, Guid id, Guid group)
        {
            var attrs = doc.Objects.FindId(id).Attributes.Duplicate();
            attrs.AddToGroup(doc.Groups.FindId(group).Index);
            Check(doc.Objects.ModifyAttributes(id, attrs, true), "Could not simulate manual group addition.");
        }
        private static void Check(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
        private static void Undo(RhinoDoc doc) => UndoRedo(doc, false);
        private static void Redo(RhinoDoc doc) => UndoRedo(doc, true);
        private static void UndoRedo(RhinoDoc doc, bool redo)
        {
            Check(!doc.UndoRecordingIsActive, "Undo record already active.");
            uint next = doc.NextUndoRecordSerialNumber;
            try { Check(redo ? doc.Redo() : doc.Undo(), "Undo/Redo failed."); }
            finally
            {
                if (doc.UndoRecordingIsActive && doc.CurrentUndoRecordSerialNumber == next)
                    Check(doc.EndUndoRecord(next), "Could not finish Undo/Redo record.");
            }
        }
        private static void Run(List<string> results, string directory, string name, Action<RhinoDoc> test)
        {
            string file = Path.Combine(directory, "hierarchy-" + Guid.NewGuid().ToString("N") + ".3dm");
            using (var original = RhinoDoc.CreateHeadless(null))
            {
                original.AdjustModelUnitSystem(UnitSystem.Millimeters, false);
                Check(original.WriteFile(file, new Rhino.FileIO.FileWriteOptions { SuppressDialogBoxes = true }),
                    "Failed to save disposable hierarchy fixture.");
            }
            using (var doc = RhinoDoc.OpenHeadless(file))
            {
                try
                {
                    Check(doc != null && !String.IsNullOrWhiteSpace(doc.Path), "Could not open disposable hierarchy fixture.");
                    doc.UndoRecordingEnabled = true;
                    test(doc);
                    Check(!doc.UndoRecordingIsActive && !doc.UndoActive && !doc.RedoActive,
                        "Component hierarchy test leaked an Undo record.");
                    results.Add("PASS " + name);
                }
                catch (Exception error) { results.Add("FAIL " + name + ": " + error); }
            }
        }
    }
}
