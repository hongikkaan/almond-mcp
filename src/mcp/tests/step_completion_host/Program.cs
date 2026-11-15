using System;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using RhinoAlmondBridge;

internal static class Program
{
    private static int tests;
    private static Guid Id(int n) => Guid.Parse(n.ToString("x32"));
    private static void Check(bool condition, string name) { if (!condition) throw new Exception(name); tests++; }
    private static RhinoDoc Fixture(int n = 2, int layers = 2, int outside = 2)
    {
        var doc = new RhinoDoc();
        doc.Layers.Add(new Layer { Index = 0, FullPath = "Final", IsCurrent = true });
        doc.Layers.Add(new Layer { Index = 1, FullPath = "temp" });
        for (int i = 1; i < layers; i++) doc.Layers.Add(new Layer { Index = i + 1, FullPath = "temp::study" + i, ParentLayerId = doc.Layers[1].Id });
        doc.Layers.Add(new Layer { Index = layers + 1, FullPath = "temp2" });
        for (int i = 0; i < n; i++) doc.Objects.Rows.Add(new RhinoObject { Id = Id(i + 1), Attributes = new ObjectAttributes { LayerIndex = 1 + i % layers } });
        for (int i = 0; i < outside; i++) doc.Objects.Rows.Add(new RhinoObject { Id = Id(1000000 + i), Attributes = new ObjectAttributes { LayerIndex = i % 2 == 0 ? 0 : layers + 1, RenderMaterial = "preserved" + i } });
        return doc;
    }
    private static RhinoDoc RegistryFixture(out string key)
    {
        var doc = Fixture(); doc.Layers.Add(new Layer { Index = 4, FullPath = "Drawing" });
        key = "ps:clip:" + doc.Objects.Rows[2].Id; return doc;
    }
    private static JObject Request(RhinoDoc doc) => new JObject { ["type"] = "step_completion", ["expected_model_path"] = doc.Path };
    private static JObject Cleanup(RhinoDoc doc) => StepCompletion.Handle(doc, Request(doc));
    private static void Register(RhinoDoc doc, int group, string id = "holon_protected", string status = "registered")
    {
        var records = (JObject)ComponentSemanticRegistry.Records(doc).DeepClone();
        records[id] = ComponentSemanticRegistry.Validate(new JObject {
            ["component_id"] = id, ["rhino_group_id"] = doc.Groups[group].Id.ToString("D"), ["name"] = "registered group",
            ["scene_ids"] = new JArray("scene_fixture"), ["child_component_ids"] = new JArray(), ["registration_status"] = status
        });
        ComponentSemanticRegistry.Change(doc, records);
    }
    private static void RegisterBeforeCleanup(RhinoDoc doc, int group, string status = "registered")
    {
        uint undo = doc.BeginUndoRecord("registration fixture"); Register(doc, group, status: status);
        if (!doc.EndUndoRecord(undo)) throw new Exception("Could not prepare semantic registration fixture.");
        doc.UndoCalls = 0; doc.Events.Clear();
    }
    private static bool Success(JObject r, int objects, int layers) => (string)r["status"] == "success" &&
        (bool?)r["result"]?["cleanup_complete"] == true && (int?)r["result"]?["deleted_object_count"] == objects &&
        (int?)r["result"]?["deleted_layer_count"] == layers && (int?)r["result"]?["document_serial"] == 7 &&
        (string)r["result"]?["mutation_state"] == (layers == 0 ? "not_needed" : "applied");
    private static bool NotStarted(JObject r, RhinoDoc doc) => (bool?)r["cleanup_complete"] == false &&
        (string)r["mutation_state"] == "not_started" && (int?)r["deleted_object_count"] == 0 && doc.Objects.DeletedIds.Count == 0 && doc.UndoCalls == 0;
    private static bool Unknown(JObject r) => (bool?)r["cleanup_complete"] == false && (string)r["mutation_state"] == "unknown" &&
        (bool?)r["requires_reconciliation"] == true && r["deleted_object_count"]?.Type == JTokenType.Null && r["deleted_layer_count"]?.Type == JTokenType.Null;

    public static void Main()
    {
        var locked = Fixture(); locked.Objects.Rows[0].IsLocked = true;
        Check(NotStarted(Cleanup(locked), locked), "actual Rhino enumeration includes a locked temp object before Undo or any Delete");
        var doc = Fixture(); var outside = doc.Objects.Rows[2]; string attrs = outside.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions());
        var result = Cleanup(doc);
        Check(Success(result, 2, 2) && doc.Objects.Rows.Take(2).All(o => o.IsDeleted) && doc.Layers[1].IsDeleted && doc.Layers[2].IsDeleted, "one request automatically cleans the complete top-level temp: " + result.ToString(Formatting.None));
        Check(!outside.IsDeleted && attrs == outside.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions()) && !doc.Layers[3].IsDeleted,
            "outside object material/color/UserText/geometry and similarly named temp2 survive");
        Check(doc.Events.IndexOf("observe_editor") < doc.Events.IndexOf("begin_undo") && doc.UndoCalls == 1 && doc.UndoRecords == 1 && !doc.UndoRecordingIsActive,
            "existing executor validates before one Undo and closes its own record");
        Check(doc.NamedViews.Single() == "existing-named-view" && doc.Layouts.Single() == "existing-layout", "NamedView/Layout tables are not deleted as layers");
        Check(result["result"].Children<JProperty>().Count() == 5 && Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) < 1024 &&
            result.ToString().IndexOf("fingerprint", StringComparison.Ordinal) < 0 && result.ToString().IndexOf("inventory", StringComparison.Ordinal) < 0 && result["result"]["undo_recorded"] == null,
            "success is a bounded five-field count result without preparation state or assumed undo_recorded");
        Check(doc.ManualUndo() && doc.Objects.Rows.All(o => !o.IsDeleted) && !doc.Layers[1].IsDeleted && !doc.Layers[2].IsDeleted,
            "manual Undo API fixture restores one successful cleanup");
        result = Cleanup(doc); Check(Success(result, 2, 2), "after caller changes Step to another status and completes again, restored temp can be cleaned again");
        result = Cleanup(doc); Check(Success(result, 0, 0) && doc.UndoCalls == 2, "missing canonical temp returns no-op without another Undo");

        doc = Fixture(); var outsideDefinition = doc.Objects.Rows[2]; outsideDefinition.IsInstanceDefinitionGeometry = true;
        Check(Success(Cleanup(doc), 2, 2) && !outsideDefinition.IsDeleted,
            "the separate definition pass preserves outside definition geometry while deleting ordinary temp objects");
        doc = Fixture();
        doc.Objects.AfterDelete = () => {
            if (doc.Objects.DeletedIds.Count == 2)
                doc.Objects.Rows.Add(new RhinoObject { IsInstanceDefinitionGeometry = true, Attributes = new ObjectAttributes { LayerIndex = 2 } });
        };
        result = Cleanup(doc);
        Check(Unknown(result) && (int)result["attempted_object_count"] == 2 && !doc.Events.Contains("delete_layer"),
            "a new definition in temp is observed by the layer-empty check before any layer Delete");

        foreach (string name in new[] { "action", "answer", "token", "fingerprint", "temp_layer", "object_ids" })
        { doc = Fixture(); var q = Request(doc); q[name] = "legacy input"; Check(NotStarted(StepCompletion.Handle(doc, q), doc), "old confirmation/selector input rejected: " + name); }
        doc = Fixture(); var wrong = Request(doc); wrong["expected_model_path"] = @"C:\other.3dm";
        Check(NotStarted(StepCompletion.Handle(doc, wrong), doc), "wrong bound document cannot be cleaned");
        foreach (string state in new[] { "editor", "ui", "readonly", "undo", "redo" })
        {
            doc = Fixture(); if (state == "editor") doc.StableEditor = false; if (state == "ui") doc.UiThread = false; if (state == "readonly") doc.IsReadOnly = true; if (state == "undo") doc.UndoActive = true; if (state == "redo") doc.RedoActive = true;
            Check(NotStarted(Cleanup(doc), doc), "unavailable editor/document transition blocks automatic cleanup: " + state);
        }
        doc = Fixture(); int registeredGroup = doc.Groups.Add("permanent meaning", new[] { Id(1) });
        RegisterBeforeCleanup(doc, registeredGroup); var registeredId = doc.Groups[registeredGroup].Id;
        Check(doc.Objects.Rows[0].Attributes.GetUserStrings().Count == 0 &&
            (string)ComponentSemanticRegistry.Records(doc)["holon_protected"]["rhino_group_id"] == registeredId.ToString("D") &&
            NotStarted(Cleanup(doc), doc), "registered Holon membership without object UserText prevents any Delete");
        doc = Fixture(); registeredGroup = doc.Groups.Add("reference meaning", new[] { Id(1) }); RegisterBeforeCleanup(doc, registeredGroup);
        doc.Groups[registeredGroup].IsReference = true;
        Check(NotStarted(Cleanup(doc), doc), "active semantic membership does not skip reference groups");
        foreach (string change in new[] { "new_registration", "new_membership" })
        {
            doc = Fixture(); var next = doc.Objects.Rows[1];
            int group = doc.Groups.Add("meaning callback", change == "new_registration" ? new[] { next.Id } : new[] { doc.Objects.Rows[2].Id });
            if (change == "new_membership") RegisterBeforeCleanup(doc, group);
            var oldRecords = ComponentSemanticRegistry.Records(doc);
            string initialAttributes = next.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions());
            doc.Objects.AfterDelete = () => { if (change == "new_registration") Register(doc, group); else next.Attributes.AddToGroup(group); };
            result = Cleanup(doc);
            Check(Unknown(result) && !next.IsDeleted && !doc.Objects.DeletedIds.Contains(next.Id) && (int)result["attempted_object_count"] == 1 &&
                doc.Events.Contains("undo_recovery"), "live registered-group change stops the next candidate before Delete: " + change);
            if (change == "new_registration")
                Check(initialAttributes == next.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions()) &&
                    !ReferenceEquals(oldRecords, ComponentSemanticRegistry.Records(doc)), "registration replaces the records JObject without stamping or changing candidate attributes");
        }
        foreach (string ordinary in new[] { "no_registration", "tombstone", "deleted_group", "reused_index", "other_guid" })
        {
            doc = Fixture(); int group = doc.Groups.Add("same display name", new[] { Id(1) });
            if (ordinary == "tombstone") RegisterBeforeCleanup(doc, group, "unregistered");
            if (ordinary == "deleted_group" || ordinary == "reused_index") { RegisterBeforeCleanup(doc, group); doc.Groups[group].IsDeleted = true; }
            if (ordinary == "reused_index") doc.Groups[group] = new Group { Index = group, Name = "same display name", Id = Guid.NewGuid() };
            if (ordinary == "other_guid") { int other = doc.Groups.Add("same display name", new[] { doc.Objects.Rows[2].Id }); RegisterBeforeCleanup(doc, other); }
            Check(Success(Cleanup(doc), 2, 2), "ordinary or non-active group does not imply semantic ownership: " + ordinary);
        }
        doc = Fixture(); doc.Objects.Rows[2].Attributes.Text["almond:component_record"] = "invalid legacy JSON";
        Check(Success(Cleanup(doc), 2, 2) && ComponentSemanticRegistry.MigrationProblems(doc).Count > 0,
            "an unrelated legacy migration problem does not block ordinary temp items");
        doc = Fixture(); int parentGroup = doc.Groups.Add("parent meaning", new[] { doc.Objects.Rows[2].Id, doc.Objects.Rows[3].Id });
        int childGroup = doc.Groups.Add("child meaning", new[] { doc.Objects.Rows[3].Id });
        uint registrationUndo = doc.BeginUndoRecord("semantic tree fixture"); Register(doc, childGroup, "holon_child"); Register(doc, parentGroup, "holon_parent");
        var tree = (JObject)ComponentSemanticRegistry.Records(doc).DeepClone(); tree["holon_parent"]["child_component_ids"] = new JArray("holon_child");
        ComponentSemanticRegistry.Change(doc, tree); doc.EndUndoRecord(registrationUndo); doc.UndoCalls = 0; doc.Events.Clear();
        Check(Success(Cleanup(doc), 2, 2), "child links without actual candidate group membership are not ownership");
        foreach (string reason in new[] { "locked", "reference", "page", "definition", "grip", "component", "placement", "geometry_tag", "current_layer", "locked_layer", "ref_layer", "update_layer" })
        {
            doc = Fixture();
            switch (reason) {
                case "locked": doc.Objects.Rows[0].IsLocked = true; break; case "reference": doc.Objects.Rows[0].IsReference = true; break;
                case "page": doc.Objects.Rows[0].Attributes.Space = ActiveSpace.PageSpace; break; case "definition": doc.Objects.Rows[0].IsInstanceDefinitionGeometry = true; break;
                case "grip": doc.Objects.Rows[0] = new GripObject { Id = Id(1), Attributes = new ObjectAttributes { LayerIndex = 1 } }; break;
                case "component": doc.Objects.Rows[0].Attributes.Text["almond:component_id"] = "registered"; break;
                case "placement": doc.Objects.Rows[0].Attributes.Text["ps:placement"] = "existing output"; break;
                case "geometry_tag": doc.Objects.Rows[0].Geometry.Text["ps:generator"] = "PlanSection/2"; break;
                case "current_layer": doc.Layers[1].IsCurrent = true; break; case "locked_layer": doc.Layers[1].IsLocked = true; break;
                case "ref_layer": doc.Layers[1].IsReference = true; break; case "update_layer": doc.Layers[1].Text["ps:clip:" + Guid.NewGuid()] = "[]"; break;
            }
            Check(NotStarted(Cleanup(doc), doc), "existing protection retained: " + reason);
        }
        foreach (string relation in new[] { "source_key", "legacy", "output_membership" })
        {
            doc = RegistryFixture(out var key);
            if (relation == "source_key") doc.Layers[4].Text["ps:clip:" + Id(1)] = "[]";
            if (relation == "legacy") { doc.Objects.Rows[2].Attributes.Text["ps:generator"] = "PlanSection/2"; doc.Objects.Rows[2].Attributes.Text["ps:clip"] = Id(1).ToString(); }
            if (relation == "output_membership") doc.Layers[4].Text[key] = JsonConvert.SerializeObject(new[] { Id(1).ToString() });
            Check(NotStarted(Cleanup(doc), doc), "external PlanSection relation protects temp before any Delete: " + relation);
        }
        foreach (string text in new[] { "[", "{}", "null", "[1]", "[\"invalid\"]" })
        { doc = RegistryFixture(out var key); doc.Layers[4].Text[key] = text; Check(NotStarted(Cleanup(doc), doc), "malformed exact Drawing registry blocks cleanup: " + text); }
        foreach (string text in new[] { "", "[]", "[\"" + Guid.Empty + "\"]", "[\"" + Guid.NewGuid() + "\"]" })
        { doc = RegistryFixture(out var key); doc.Layers[4].Text[key] = text; Check(Success(Cleanup(doc), 2, 2), "empty/unrelated valid registry permits complete cleanup: " + text); }
        doc = RegistryFixture(out var unrelatedKey); doc.Layers[0].Text[unrelatedKey] = "["; doc.Layers[4].Text["ps:clip:ordinary-note"] = "["; doc.Objects.Rows[0].Attributes.Text["ordinary-note"] = "temp study";
        Check(Success(Cleanup(doc), 2, 2), "unknown UserText and arbitrary other-layer values are not ownership selectors");

        doc = Fixture(); doc.BeforeUndo = () => doc.Objects.Rows[0].Geometry.Crc++;
        result = Cleanup(doc); Check(Unknown(result) && (int)result["attempted_object_count"] == 0 && doc.Objects.DeletedIds.Count == 0 && doc.Events.Contains("undo_recovery"),
            "Undo entry change is rejected before Delete using directly compared snapshots");
        foreach (string change in new[] { "move", "geometry", "attribute", "protected_attribute", "protected_geometry", "lock", "legacy", "source_key", "membership", "malformed" })
        {
            doc = RegistryFixture(out var key); doc.Layers[4].Text[key] = "[]"; var next = doc.Objects.Rows[1];
            doc.Objects.AfterDelete = () => {
                switch (change) {
                    case "move": next.Attributes.LayerIndex = 0; break; case "geometry": next.Geometry.Crc++; break; case "attribute": next.Attributes.RenderMaterial = "changed"; break;
                    case "protected_attribute": next.Attributes.Text["ps:placement"] = "protected"; break; case "protected_geometry": next.Geometry.Text["ps:generator"] = "PlanSection/2"; break; case "lock": next.IsLocked = true; break;
                    case "legacy": doc.Objects.Rows[2].Attributes.Text["ps:generator"] = "PlanSection/2"; doc.Objects.Rows[2].Attributes.Text["ps:clip"] = next.Id.ToString(); break;
                    case "source_key": doc.Layers[4].Text["ps:clip:" + next.Id] = "[]"; break;
                    case "membership": doc.Layers[4].Text[key] = JsonConvert.SerializeObject(new[] { next.Id.ToString() }); break;
                    case "malformed": doc.Layers[4].Text[key] = "["; break;
                }
            };
            result = Cleanup(doc);
            Check(Unknown(result) && !next.IsDeleted && !doc.Objects.DeletedIds.Contains(next.Id) && (int)result["attempted_object_count"] == 1 &&
                doc.Events.Contains("undo_recovery") && doc.Objects.Rows.All(o => !o.IsDeleted), "callback protects next item before its Delete, failed outcome stays unknown: " + change);
        }
        doc = Fixture(); doc.Objects.FailDelete = Id(2); result = Cleanup(doc);
        Check(Unknown(result) && (int)result["attempted_object_count"] == 1 && doc.ClearedRedo == 1 && doc.Objects.Rows.All(o => !o.IsDeleted), "actual existing executor body recovers a failed nonempty record and clears its Redo");
        doc = Fixture(); doc.Objects.FailDelete = Id(1); result = Cleanup(doc);
        Check(Unknown(result) && !doc.Events.Contains("undo_recovery") && doc.ClearedRedo == 0, "empty failed record is purged without undoing earlier work");
        doc = Fixture(); doc.FailBeginUndo = true; result = Cleanup(doc);
        Check((string)result["mutation_state"] == "not_started" && (int)result["deleted_object_count"] == 0 && doc.Objects.DeletedIds.Count == 0, "cannot start Undo means action never entered");
        doc = Fixture(); doc.Objects.FailDelete = Id(2); doc.FailUndo = true; result = Cleanup(doc);
        Check(Unknown(result) && doc.Objects.Rows[0].IsDeleted && doc.ClearedRedo == 0, "failed executor Undo retains unknown partial state and does not pretend rollback");
        doc = Fixture(); doc.FailEndUndo = true; result = Cleanup(doc);
        Check(Unknown(result) && doc.UndoRecordingIsActive, "Undo close failure prevents successful completion");
        doc = Fixture(); doc.Objects.AfterDelete = () => doc.CurrentUndoRecordSerialNumber = 999; result = Cleanup(doc);
        Check(Unknown(result) && doc.CurrentUndoRecordSerialNumber == 999 && doc.UndoRecordingIsActive && !doc.Events.Contains("undo_recovery"), "executor never closes or undoes another owner's record");
        doc = Fixture(); doc.Views.FailRedraw = true; Check(Success(Cleanup(doc), 2, 2), "display failure does not roll back completed cleanup");

        foreach (string change in new[] { "reparent", "new_object", "new_child", "outside_attribute" })
        {
            doc = Fixture(); var root = doc.Layers[1];
            if (change == "outside_attribute") doc.Objects.AfterDelete = () => doc.Objects.Rows[2].Attributes.ObjectColor = "changed";
            else doc.Layers.AfterDelete = () => {
                if (change == "reparent") { root.ParentLayerId = doc.Layers[0].Id; root.FullPath = "Final::temp"; }
                if (change == "new_object") { doc.Objects.Rows.Add(new RhinoObject { Attributes = new ObjectAttributes { LayerIndex = root.Index } }); doc.Changed = true; }
                if (change == "new_child") { doc.Layers.Add(new Layer { Index = 4, FullPath = "temp::new", ParentLayerId = root.Id }); doc.Changed = true; }
            };
            result = Cleanup(doc); Check(Unknown(result) && doc.Events.Contains("undo_recovery"), "layer/cascade/outside changes fail the whole cleanup: " + change);
        }
        doc = Fixture(5000); result = Cleanup(doc);
        Check(Success(result, 5000, 2) && Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) < 1024 && result["result_error"] == null,
            "5000 complete deletions use actual bounded ResultProjector count output without relaxing its 64KiB guard");
        doc = Fixture(129, 129); result = Cleanup(doc);
        Check(Success(result, 129, 129), "129 temp layers are fully cleaned without an inventory cap");
        doc = Fixture(1, 1, 100001); result = Cleanup(doc);
        Check(Success(result, 1, 1) && doc.Objects.Rows.Count(o => !o.IsDeleted) == 100001, "100001 outside objects are preserved without a full-scan quantity cap");
        doc = Fixture(100001, 1, 0); foreach (var o in doc.Objects.Rows) o.IsLocked = true; result = Cleanup(doc);
        Check(NotStarted(result, doc) && Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) < 1024,
            "large invalid candidate set fails safely with a bounded error rather than a huge blocker inventory");
        doc = Fixture(1, 2, 100001); doc.Layers[1].FullPath = "Final::temp"; doc.Layers[1].ParentLayerId = doc.Layers[0].Id; doc.Layers[2].FullPath = "Final::temp::child";
        result = Cleanup(doc); Check(Success(result, 0, 0) && doc.Objects.ScanCalls == 0 && doc.UndoCalls == 0 && !doc.Layers[1].IsDeleted,
            "no top-level temp skips scan/Undo and never selects another location's temp");
        Check(!AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == "RhinoCommon"), "no actual Rhino assembly or model is loaded");
        Console.WriteLine(JsonConvert.SerializeObject(new { status = "passed", tests, actualRhinoLoaded = false, automatic_cleanup_v2 = true,
            executor = "actual unchanged ExecuteAction/Undo methods extracted and actual Results.cs linked; Rhino Undo APIs are fixtures" }));
    }
}
