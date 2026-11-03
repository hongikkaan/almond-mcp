"""Group registration at the public tool/store-to-native boundary.

Disposable SQLite and scripted native replies exercise Python contracts; they do
not certify a loaded Bridge, real Rhino group behavior or native Undo/Redo.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest
from fastmcp import FastMCP

from almond_mcp.features.components.tools import register
from almond_mcp.retrieval_store import AlmondStore


MODEL = r"C:\fixture\housing.3dm"
GROUP = "00000000-0000-0000-0000-000000000101"
OBJECT = "00000000-0000-0000-0000-000000000201"
COMPONENT = "component_arrival"
CHILD_GROUP = "00000000-0000-0000-0000-000000000102"
CHILD_OBJECT = "00000000-0000-0000-0000-000000000202"
CHILD = "component_seating"


def snapshot(scene_id, *, component_id=COMPONENT, group_id=GROUP, name="Arrival",
             object_ids=(OBJECT,), children=(), parent=None, effective=None):
    objects = [{"rhino_guid": guid, "component_id": component_id,
                "object_type": "Brep", "name": "Bench", "bounds_mm": [0, 0, 0, 100, 200, 300]}
               for guid in object_ids]
    return {"complete": True, "live_verified": True, "component_id": component_id,
            "model_path": MODEL, "rhino_group_id": group_id, "name": name,
            "scene_ids": [scene_id], "child_component_ids": list(children),
            "parent_component_id": parent, "availability": "present",
            "objects": objects, "effective_objects": copy.deepcopy(objects) if effective is None else effective,
            "object_ids": list(object_ids), "requires_sync": False, "pending_objects": []}


class NativeBoundary:
    """Script only the external native transport, never store internals."""

    def __init__(self, reply, *, inference=True):
        self.reply = reply
        self.requests = []
        self.capabilities = {"design_components": 1, "component_registry": 2}
        if inference:
            self.capabilities["component_group_inference"] = 1

    def send(self, payload):
        request = json.loads(payload)
        self.requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": self.capabilities})
        return json.dumps(copy.deepcopy(self.reply))


@pytest.fixture
def registry(tmp_path):
    store = AlmondStore(tmp_path / "components.sqlite3")
    scene_id = store.create_scene("Arrival scene")["scene_id"]
    return store, scene_id


def public_tools(store, native):
    return register(FastMCP("component-inference-test"),
                    SimpleNamespace(retrieval_store=store, _send_and_receive=native.send))


@pytest.mark.parametrize("member_arguments", [{}, {"object_ids": None}])
def test_group_registration_accepts_omitted_or_null_members(registry, member_arguments):
    store, scene_id = registry
    native = NativeBoundary({"status": "success", "component": snapshot(scene_id)})
    tool = public_tools(store, native)["upsert_ontological_holon"]

    result = json.loads(tool(name="Arrival", holon_id=COMPONENT,
                             expected_model_path=MODEL, rhino_group_id=GROUP,
                             scene_ids=[scene_id], **member_arguments))

    assert result["status"] == "success", result
    assert result["holon"]["rhino_group_id"] == GROUP
    assert result["holon"]["object_count"] == 1
    assert store.get_component(COMPONENT)["object_count"] == 1
    # Atomic inference sends no separate member observation before upsert.
    operations = [r for r in native.requests if r["type"] != "get_rhino_context"]
    assert len(operations) == 1
    assert operations[0]["action"] == "upsert"
    assert operations[0]["object_ids"] is None


def test_group_inference_requires_its_capability_before_registration(registry):
    store, scene_id = registry
    native = NativeBoundary({"status": "success", "component": snapshot(scene_id)}, inference=False)
    tool = public_tools(store, native)["upsert_ontological_holon"]

    result = json.loads(tool(name="Arrival", holon_id=COMPONENT,
                             expected_model_path=MODEL, rhino_group_id=GROUP,
                             scene_ids=[scene_id]))

    assert result["status"] == "error", result
    assert result["mutation_applied"] is False
    assert "component_group_inference=1" in result["message"]
    assert not any(r["type"] == "design_component" for r in native.requests)
    assert store.get_component(COMPONENT) is None


def test_explicit_members_remain_supported_without_inference_capability(registry):
    store, scene_id = registry
    native = NativeBoundary({"status": "success", "component": snapshot(scene_id)}, inference=False)
    tool = public_tools(store, native)["upsert_ontological_holon"]

    result = json.loads(tool(name="Arrival", object_ids=[OBJECT], holon_id=COMPONENT,
                             expected_model_path=MODEL, rhino_group_id=GROUP,
                             scene_ids=[scene_id]))

    assert result["status"] == "success", result
    assert store.get_component(COMPONENT)["object_count"] == 1
    assert native.requests[-1]["object_ids"] == [OBJECT]


@pytest.mark.parametrize("availability", ["present", "missing_group", "unregistered"])
def test_inference_requires_a_nonempty_present_group_snapshot(registry, availability):
    store, scene_id = registry
    observed = snapshot(scene_id, object_ids=())
    observed["availability"] = availability
    native = NativeBoundary({"status": "success", "component": observed})
    tool = public_tools(store, native)["upsert_ontological_holon"]

    result = json.loads(tool(name="Arrival", holon_id=COMPONENT,
                             expected_model_path=MODEL, rhino_group_id=GROUP,
                             scene_ids=[scene_id]))

    assert result["status"] == "error", result
    assert result["requires_reconciliation"] is True
    assert store.get_component(COMPONENT) is None
    assert len([r for r in native.requests if r["type"] == "design_component"]) == 1


@pytest.mark.parametrize("arguments", [
    {"object_ids": []},
    {"rhino_group_id": ""},
    {"scene_ids": []},
])
def test_registration_does_not_infer_from_empty_members_or_missing_context(registry, arguments):
    store, scene_id = registry
    native = NativeBoundary({"status": "success", "component": snapshot(scene_id)})
    tool = public_tools(store, native)["upsert_ontological_holon"]
    inputs = dict(name="Arrival", holon_id=COMPONENT, expected_model_path=MODEL,
                  rhino_group_id=GROUP, scene_ids=[scene_id])
    inputs.update(arguments)

    result = json.loads(tool(**inputs))

    assert result["status"] == "error", result
    assert native.requests == []
    assert store.get_component(COMPONENT) is None


def test_existing_component_binding_infers_new_group_members_without_respecifying_context(registry):
    store, scene_id = registry
    native = NativeBoundary({"status": "success", "component": snapshot(scene_id)})
    tool = public_tools(store, native)["upsert_ontological_holon"]
    assert json.loads(tool(name="Arrival", object_ids=[OBJECT], holon_id=COMPONENT,
                           expected_model_path=MODEL, rhino_group_id=GROUP,
                           scene_ids=[scene_id]))["status"] == "success"
    native.reply = {"status": "success", "component": snapshot(scene_id, object_ids=(OBJECT, CHILD_OBJECT))}

    result = json.loads(tool(name="Arrival", holon_id=COMPONENT, expected_model_path=MODEL))

    assert result["status"] == "success", result
    assert store.get_component(COMPONENT)["object_count"] == 2
    assert store.get_component(COMPONENT)["scene_ids"] == [scene_id]
    assert native.requests[-1]["rhino_group_id"] == GROUP
    assert native.requests[-1]["object_ids"] is None


@pytest.mark.parametrize("member_ids", [None, []])
def test_parent_without_direct_members_preserves_child_ownership_through_store(registry, member_ids):
    store, scene_id = registry
    child = snapshot(scene_id, component_id=CHILD, group_id=CHILD_GROUP,
                     name="Seating", object_ids=(CHILD_OBJECT,))
    native = NativeBoundary({"status": "success", "component": child}, inference=member_ids is None)
    tool = public_tools(store, native)["upsert_ontological_holon"]
    assert json.loads(tool(name="Seating", object_ids=[CHILD_OBJECT], holon_id=CHILD,
                           expected_model_path=MODEL, rhino_group_id=CHILD_GROUP,
                           scene_ids=[scene_id]))["status"] == "success"
    parent = snapshot(scene_id, object_ids=(), children=(CHILD,), effective=child["objects"])
    child["parent_component_id"] = COMPONENT
    native.reply = {"status": "success", "component": parent, "affected_components": [child]}

    result = json.loads(tool(name="Arrival", object_ids=member_ids, holon_id=COMPONENT,
                             expected_model_path=MODEL, rhino_group_id=GROUP,
                             scene_ids=[scene_id], child_holon_ids=[CHILD]))

    assert result["status"] == "success", result
    assert store.get_component(COMPONENT)["object_count"] == 0
    assert store.get_component(COMPONENT)["effective_object_count"] == 1
    assert store.get_component(CHILD)["parent_component_id"] == COMPONENT
    assert native.requests[-1]["object_ids"] == member_ids


@pytest.mark.parametrize("broken", ["document", "group", "name", "owner", "effective_owner",
                                    "children", "incomplete", "truncated", "object_ids"])
def test_invalid_native_snapshot_never_changes_the_ledger_or_replays_registration(registry, broken):
    store, scene_id = registry
    observed = snapshot(scene_id)
    if broken == "document":
        observed["model_path"] = r"C:\fixture\other.3dm"
    elif broken == "group":
        observed["rhino_group_id"] = CHILD_GROUP
    elif broken == "name":
        observed["name"] = "Other"
    elif broken == "owner":
        observed["objects"][0]["component_id"] = CHILD
    elif broken == "effective_owner":
        observed["effective_objects"][0]["component_id"] = CHILD
    elif broken == "children":
        observed["child_component_ids"] = [CHILD]
    elif broken == "incomplete":
        observed["complete"] = False
    elif broken == "truncated":
        observed["truncated"] = True
    elif broken == "object_ids":
        observed["object_ids"] = [CHILD_OBJECT]
    native = NativeBoundary({"status": "success", "component": observed})
    tool = public_tools(store, native)["upsert_ontological_holon"]
    before = store.get_scene(scene_id)

    result = json.loads(tool(name="Arrival", holon_id=COMPONENT,
                             expected_model_path=MODEL, rhino_group_id=GROUP,
                             scene_ids=[scene_id]))

    assert result["status"] == "error", result
    assert result["requires_reconciliation"] is True
    assert store.get_component(COMPONENT) is None
    assert store.get_scene(scene_id) == before
    assert len([r for r in native.requests if r["type"] == "design_component"]) == 1


# This executable compiles the two production registry sources. Only Rhino API,
# editing-state observation and the native executor boundary are doubled. It
# exercises registration logic, not real Rhino UI, geometry kernels or Undo.
NATIVE_FIXTURE = r'''
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using RhinoAlmondBridge;

namespace Rhino.Geometry {
    public struct Point3d { public double X, Y, Z; }
    public struct BoundingBox {
        public Point3d Min, Max;
        public bool IsValid => true;
    }
    public class GeometryBase {
        public BoundingBox GetBoundingBox(bool accurate) => new BoundingBox {
            Min = new Point3d(), Max = new Point3d { X=100, Y=200, Z=300 } };
    }
}
namespace Rhino.DocObjects {
    public enum ActiveSpace { ModelSpace, PageSpace }
    public enum ObjectType { Brep, InstanceReference, Annotation }
    public class ObjectAttributes {
        public ActiveSpace Space;
        public string Name = "Bench";
        public HashSet<int> Groups = new HashSet<int>();
        public string TemporaryEditData;
        public bool IsInGroup(int index) => Groups.Contains(index);
        public string GetUserString(string key) => key == "$TempBlockEditUserData$" ? TemporaryEditData : null;
    }
    public class RhinoObject {
        public Guid Id;
        public bool IsDeleted, IsReference, IsInstanceDefinitionGeometry;
        public ObjectAttributes Attributes = new ObjectAttributes();
        public Rhino.Geometry.GeometryBase Geometry = new Rhino.Geometry.GeometryBase();
        public ObjectType ObjectType = ObjectType.Brep;
    }
    public class Group {
        public Guid Id; public string Name; public int Index;
        public bool IsDeleted, IsReference;
    }
    public class ObjectEnumeratorSettings {
        public bool NormalObjects, HiddenObjects, LockedObjects, ReferenceObjects, IdefObjects, DeletedObjects;
    }
}
namespace Rhino.Commands {
    public class CustomUndoEventArgs : EventArgs {
        public RhinoDoc Document; public object Tag; public string ActionDescription;
    }
}
namespace Rhino.FileIO {
    public class BinaryArchiveWriter {
        public void Write3dmChunkVersion(int major, int minor) => throw new NotSupportedException();
        public void WriteString(string value) => throw new NotSupportedException();
    }
    public class BinaryArchiveReader {
        public void Read3dmChunkVersion(out int major, out int minor) => throw new NotSupportedException();
        public string ReadString() => throw new NotSupportedException();
    }
    public class FileReadOptions {
        public bool OpenMode, ImportMode, InsertMode, NewMode, ImportReferenceMode;
    }
}
namespace Rhino {
    public enum UnitSystem { Millimeters }
    public static class RhinoMath {
        public static double UnitScale(UnitSystem from, UnitSystem to) => 1;
    }
    public class RuntimeValues {
        readonly Dictionary<string, object> data = new Dictionary<string, object>();
        public T GetValue<T>(string key, Func<string, T> create) {
            if (!data.ContainsKey(key)) data[key] = create(key);
            return (T)data[key];
        }
    }
    public class ObjectTable : List<RhinoObject> {
        public RhinoObject FindId(Guid id) => this.FirstOrDefault(o => o.Id == id);
        public IEnumerable<RhinoObject> GetObjectList(ObjectEnumeratorSettings settings) => this;
    }
    public class GroupTable : List<Group> {
        readonly RhinoDoc doc;
        public int Created;
        public GroupTable(RhinoDoc value) { doc=value; }
        public Group FindId(Guid id) => this.FirstOrDefault(g => g.Id == id);
        public bool IsDeleted(int index) => this[index].IsDeleted;
        public RhinoObject[] GroupMembers(int index) => doc.Objects.Where(o => !o.IsDeleted && o.Attributes.IsInGroup(index)).ToArray();
        public int Add(string name, IEnumerable<Guid> members) {
            int index=Count;
            base.Add(new Group { Id=Guid.NewGuid(), Name=name, Index=index });
            foreach (Guid id in members) doc.Objects.FindId(id).Attributes.Groups.Add(index);
            Created++;
            return index;
        }
    }
    public class RhinoDoc {
        public string Path;
        public bool Modified, Stable=true;
        public int Executions, UndoEvents;
        public UnitSystem ModelUnitSystem = UnitSystem.Millimeters;
        public RuntimeValues RuntimeData = new RuntimeValues();
        public ObjectTable Objects = new ObjectTable();
        public GroupTable Groups;
        public RhinoDoc() { Groups = new GroupTable(this); }
        public bool AddCustomUndoEvent(string name, EventHandler<Rhino.Commands.CustomUndoEventArgs> callback, object tag) {
            UndoEvents++; return true;
        }
    }
}
namespace RhinoAlmondBridge {
    public static class ModelingMetadata { public static string Key(string key) => "almond:" + key; }
    public static class EditingContext {
        public static JObject Observe(RhinoDoc doc) => new JObject { ["stable"]=doc.Stable };
    }
    public class ScriptResult { public string Status, Message; }
    public class ScriptExecutor {
        public ScriptResult ExecuteAction(RhinoDoc doc, Func<object> action) {
            doc.Executions++;
            try { action(); return new ScriptResult { Status="success" }; }
            catch (Exception e) { return new ScriptResult { Status="error", Message=e.Message }; }
        }
    }
}
public static class FixtureProgram {
    public static void Main() {
        var input=JObject.Parse(Console.In.ReadToEnd());
        var doc=new RhinoDoc { Path=(string)input["model"], Stable=(bool?)input["stable"] ?? true };
        foreach (var row in input["objects"].OfType<JObject>()) doc.Objects.Add(new RhinoObject {
            Id=Guid.Parse((string)row["id"]), IsDeleted=(bool?)row["deleted"] ?? false,
            IsReference=(bool?)row["reference"] ?? false, IsInstanceDefinitionGeometry=(bool?)row["definition"] ?? false,
            Attributes=new ObjectAttributes { Space=(bool?)row["page"] == true ? ActiveSpace.PageSpace : ActiveSpace.ModelSpace,
                TemporaryEditData=(string)row["temporary"] }
        });
        foreach (var row in input["groups"].OfType<JObject>()) {
            int index=doc.Groups.Count;
            doc.Groups.Add(new Group { Id=Guid.Parse((string)row["id"]), Name=(string)row["name"], Index=index,
                IsDeleted=(bool?)row["deleted"] ?? false, IsReference=(bool?)row["reference"] ?? false });
            foreach (string id in row["members"].Values<string>()) doc.Objects.FindId(Guid.Parse(id)).Attributes.Groups.Add(index);
        }
        ComponentSemanticRegistry.Import(doc, new JObject {
            ["version"]=1, ["records"]=input["records"] ?? new JObject(), ["legacy_initialized"]=true
        }.ToString(Formatting.None));
        var replies=new JArray();
        foreach (var request in input["requests"].OfType<JObject>()) replies.Add(ComponentRegistry.Handle(doc, request));
        Console.WriteLine(new JObject {
            ["replies"]=replies, ["executions"]=doc.Executions, ["undo_events"]=doc.UndoEvents,
            ["groups_created"]=doc.Groups.Created, ["modified"]=doc.Modified,
            ["records"]=JObject.Parse(ComponentSemanticRegistry.Export(doc))["records"],
            ["groups"]=new JArray(doc.Groups.Select(g => new JObject {
                ["id"]=g.Id.ToString("D"), ["name"]=g.Name,
                ["members"]=new JArray(doc.Groups.GroupMembers(g.Index).Select(o => o.Id.ToString("D"))) }))
        }.ToString(Formatting.None));
    }
}
'''


@pytest.fixture(scope="module")
def native_host(tmp_path_factory):
    """Compile only a disposable .NET executable; never build or load an RHP."""
    sdk_path = os.environ.get("ALMOND_TEST_DOTNET")
    if not sdk_path:
        pytest.fail("Run the official MCP runner with a .NET 8 SDK (-DotNet).")
    sdk = Path(sdk_path)
    version = subprocess.run([str(sdk), "--version"], check=True, capture_output=True,
                             text=True, timeout=30).stdout.strip()
    newtonsoft = sdk.parent / "sdk" / version / "Newtonsoft.Json.dll"
    assert newtonsoft.is_file(), "The selected SDK must provide its Newtonsoft.Json assembly."
    folder = tmp_path_factory.mktemp("registry_native")
    native_source = Path(__file__).resolve().parents[1] / "features/components/native"
    (folder / "RegistryFixture.cs").write_text(NATIVE_FIXTURE, encoding="utf-8")
    (folder / "NuGet.Config").write_text(
        '<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    (folder / "RegistryFixture.csproj").write_text(f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems><NuGetAudit>false</NuGetAudit>
  </PropertyGroup>
  <ItemGroup><Compile Include="RegistryFixture.cs" />
    <Compile Include="{escape(str(native_source / 'ComponentRegistry.cs'))}" Link="ComponentRegistry.cs" />
    <Compile Include="{escape(str(native_source / 'ComponentSemanticRegistry.cs'))}" Link="ComponentSemanticRegistry.cs" />
    <Reference Include="Newtonsoft.Json"><HintPath>{escape(str(newtonsoft))}</HintPath></Reference>
  </ItemGroup>
</Project>''', encoding="utf-8")
    environment = {**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
                   "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1", "DOTNET_CLI_HOME": str(folder / "dotnet-home")}
    built = subprocess.run([str(sdk), "build", "RegistryFixture.csproj", "--nologo", "-v:q",
                            "-o", "out", "/p:UseSharedCompilation=false"], cwd=folder, env=environment,
                           capture_output=True, text=True, timeout=60)
    assert built.returncode == 0, built.stdout + built.stderr

    def invoke(case):
        completed = subprocess.run([str(sdk), str(folder / "out/RegistryFixture.dll")],
                                   input=json.dumps(case), capture_output=True, text=True,
                                   cwd=folder, env=environment, timeout=30)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return json.loads(completed.stdout)

    return invoke


def native_case():
    return {"model": MODEL, "objects": [{"id": OBJECT}],
            "groups": [{"id": GROUP, "name": "Arrival", "members": [OBJECT]}],
            "requests": [{"action": "upsert", "expected_model_path": MODEL,
                          "component_id": COMPONENT, "rhino_group_id": GROUP,
                          "name": "Arrival", "scene_ids": ["scene_arrival"],
                          "child_component_ids": []}]}


@pytest.mark.parametrize("explicit_null", [False, True])
def test_native_group_inference_reads_current_members_without_creating_a_group(native_host, explicit_null):
    case = native_case()
    if explicit_null:
        case["requests"][0]["object_ids"] = None

    result = native_host(case)

    assert result["replies"][0]["status"] == "success", result
    assert result["replies"][0]["component"]["object_ids"] == [OBJECT]
    assert result["groups"] == case["groups"]
    assert result["groups_created"] == 0
    assert result["executions"] == 1
    assert result["undo_events"] == 1


def native_child_case():
    case = native_case()
    case["objects"].append({"id": CHILD_OBJECT})
    case["groups"][0]["members"].append(CHILD_OBJECT)
    case["groups"].append({"id": CHILD_GROUP, "name": "Seating", "members": [CHILD_OBJECT]})
    case["records"] = {CHILD: {"component_id": CHILD, "rhino_group_id": CHILD_GROUP,
                              "name": "Seating", "scene_ids": ["scene_arrival"],
                              "child_component_ids": [], "registration_status": "registered"}}
    case["requests"][0]["child_component_ids"] = [CHILD]
    return case


def test_native_group_inference_preserves_declared_child_ownership(native_host):
    case = native_child_case()

    result = native_host(case)

    reply = result["replies"][0]
    assert reply["status"] == "success", result
    assert reply["component"]["object_ids"] == [OBJECT]
    assert {row["rhino_guid"]: row["component_id"] for row in reply["component"]["effective_objects"]} == {
        OBJECT: COMPONENT, CHILD_OBJECT: CHILD}
    assert reply["affected_components"][0]["parent_component_id"] == COMPONENT
    assert result["groups"] == case["groups"]
    assert result["groups_created"] == 0


def test_native_group_inference_rejects_unavailable_child_group_before_mutation(native_host):
    case = native_child_case()
    case["groups"].pop()

    result = native_host(case)

    assert result["replies"][0]["status"] == "error", result
    assert result["replies"][0]["mutation_applied"] is False
    assert result["executions"] == 0
    assert result["records"] == case["records"]


def test_native_group_inference_rejects_conflicting_child_ownership_before_mutation(native_host):
    case = native_child_case()
    other_group = "00000000-0000-0000-0000-000000000103"
    case["groups"].append({"id": other_group, "name": "Unrelated", "members": [CHILD_OBJECT]})
    case["records"]["component_other"] = {
        "component_id": "component_other", "rhino_group_id": other_group, "name": "Unrelated",
        "scene_ids": ["scene_arrival"], "child_component_ids": [], "registration_status": "registered"}

    result = native_host(case)

    assert result["replies"][0]["status"] == "error", result
    assert result["replies"][0]["mutation_applied"] is False, result
    assert result["executions"] == 0
    assert result["undo_events"] == 0
    assert result["modified"] is False
    assert result["records"] == case["records"]
    assert result["groups"] == case["groups"]


@pytest.mark.parametrize("problem", ["no_binding", "missing_group", "deleted_group", "reference_group",
                                    "empty_group", "wrong_name", "wrong_document", "unstable",
                                    "reference_member", "definition_member", "page_member", "editing_member",
                                    "unknown_child", "undeclared_child", "child_outside_group", "too_many"])
def test_native_group_inference_rejects_invalid_scope_before_mutation(native_host, problem):
    case = native_case()
    request = case["requests"][0]
    if problem == "no_binding":
        del request["rhino_group_id"]
    elif problem == "missing_group":
        case["groups"] = []
    elif problem == "deleted_group":
        case["groups"][0]["deleted"] = True
    elif problem == "reference_group":
        case["groups"][0]["reference"] = True
    elif problem == "empty_group":
        case["groups"][0]["members"] = []
    elif problem == "wrong_name":
        request["name"] = "Different name"
    elif problem == "wrong_document":
        request["expected_model_path"] = r"C:\fixture\other.3dm"
    elif problem == "unstable":
        case["stable"] = False
    elif problem in {"reference_member", "definition_member", "page_member"}:
        case["objects"][0][problem.removesuffix("_member")] = True
    elif problem == "editing_member":
        case["objects"][0]["temporary"] = "block-edit-object"
    elif problem == "unknown_child":
        request["child_component_ids"] = [CHILD]
    elif problem == "undeclared_child":
        case = native_child_case()
        case["requests"][0]["child_component_ids"] = []
    elif problem == "child_outside_group":
        case = native_child_case()
        case["groups"][0]["members"] = [OBJECT]
    elif problem == "too_many":
        members = [f"00000000-0000-0000-0001-{index:012x}" for index in range(4097)]
        case["objects"] = [{"id": member} for member in members]
        case["groups"][0]["members"] = members

    result = native_host(case)

    assert result["replies"][0]["status"] == "error", result
    assert result["replies"][0]["mutation_applied"] is False
    assert result["executions"] == result["undo_events"] == result["groups_created"] == 0
    assert result["modified"] is False
    assert result["records"] == case.get("records", {})


@pytest.mark.parametrize("mode", ["explicit", "empty_parent", "inferred_parent", "repeat_binding"])
def test_native_explicit_members_empty_parents_and_existing_bindings_remain_compatible(native_host, mode):
    case = native_child_case() if mode in {"empty_parent", "inferred_parent"} else native_case()
    if mode == "explicit":
        case["requests"][0]["object_ids"] = [OBJECT]
    elif mode in {"empty_parent", "inferred_parent"}:
        case["groups"][0]["members"] = [CHILD_OBJECT]
        if mode == "empty_parent":
            case["requests"][0]["object_ids"] = []
    else:
        repeated = copy.deepcopy(case["requests"][0])
        del repeated["rhino_group_id"]
        case["requests"].append(repeated)

    result = native_host(case)

    assert all(reply["status"] == "success" for reply in result["replies"]), result
    expected = [] if mode in {"empty_parent", "inferred_parent"} else [OBJECT]
    assert result["replies"][-1]["component"]["object_ids"] == expected
    assert result["groups"] == case["groups"]
    assert result["groups_created"] == 0
    assert result["executions"] == result["undo_events"] == 1


def test_native_explicit_empty_is_not_group_inference(native_host):
    case = native_case()
    case["requests"][0]["object_ids"] = []

    result = native_host(case)

    assert result["replies"][0]["status"] == "error", result
    assert result["replies"][0]["mutation_applied"] is False
    assert result["executions"] == 0
