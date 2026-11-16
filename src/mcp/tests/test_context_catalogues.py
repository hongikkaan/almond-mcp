"""Discovery uses complete catalogues without live Rhino or project databases."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess

import pytest

from almond_mcp.features.context.context_query import context_catalogues, layer_tree, observe_context, query
from almond_mcp.retrieval_store import AlmondStore
from test_layout_viewport_state import method


def test_layer_tree_retains_same_names_under_distinct_parents_and_table_order():
    rows = [{"id": "a-wall", "parent_id": "a", "name": "Wall"},
            {"id": "a", "parent_id": None, "name": "Building A"},
            {"id": "b", "parent_id": "", "name": "Building B"},
            {"id": "b-wall", "parent_id": "b", "name": "Wall"},
            {"id": "detail", "parent_id": "b-wall", "name": "Detail"}]
    assert layer_tree(rows) == "- Building A\n  - Wall\n- Building B\n  - Wall\n    - Detail"
    assert layer_tree([]) == ""
    assert layer_tree(None) is None
    assert rows[0]["parent_id"] == "a"


def test_deep_and_large_layer_lists_are_not_truncated_or_recursion_limited():
    rows = [{"id": str(i), "parent_id": str(i - 1) if i else None, "name": f"L{i}"}
            for i in range(1100)]
    lines = layer_tree(rows).splitlines()
    assert len(lines) == 1100
    assert lines[-1] == "  " * 1099 + "- L1099"
    roots = [{"id": str(i), "parent_id": None, "name": f"R{i}"} for i in range(1500)]
    assert len(layer_tree(roots).splitlines()) == 1500


@pytest.mark.parametrize("rows", [
    [{"id": "x", "parent_id": "missing", "name": "A"}],
    [{"id": "x", "parent_id": "y", "name": "A"}, {"id": "y", "parent_id": "x", "name": "B"}],
    [{"id": "x", "name": "A"}, {"id": "x", "name": "B"}],
])
def test_invalid_hierarchy_is_reported_instead_of_silently_omitting_layers(rows):
    with pytest.raises(ValueError):
        layer_tree(rows)


def test_inspect_and_project_use_identical_catalogue_projection_without_mutating_native_rows():
    native = {"status": "success", "capabilities": {"context_sections": 3}, "warnings": [],
              "named_views": [{"id": "v", "name": "Entrance", "metadata": {"purpose": "arrival"}}],
              "layouts": [{"id": "p", "name": "A3"}],
              "layers": [{"id": "l", "name": "Building", "parent_id": None}]}
    sections = ["named_views", "layouts", "layers"]
    send = lambda _: json.dumps(native)
    project = context_catalogues(observe_context(send, sections), sections)
    inspected = json.loads(query(send, sections))
    assert {key: inspected[key] for key in sections} == project
    assert native["layers"][0]["id"] == "l"
    assert project["named_views"][0]["metadata"] == {"purpose": "arrival"}


def test_project_file_descriptions_migrate_old_rows_and_survive_reopening(tmp_path):
    path = tmp_path / "scene.sqlite3"
    store = AlmondStore(path)
    scene = store.create_scene("Entry", file_name="entry.3dm")
    with sqlite3.connect(path) as db:
        before = db.execute("SELECT file_id,file_name FROM project_files").fetchall()
        db.execute("ALTER TABLE project_files DROP COLUMN description")
    reopened = AlmondStore(path)
    assert reopened.list_project_files()["files"] == [{"project_file_id": before[0][0],
        "file_name": "entry.3dm", "filename": "entry.3dm", "description": ""}]
    with reopened._connect() as db:
        reopened._project_file_reference(db, project_file_id=before[0][0], description="Arrival plan")
        reopened._project_file_reference(db, "entry.3dm")
    reopened = AlmondStore(path)
    assert reopened.list_project_files()["files"][0]["description"] == "Arrival plan"
    assert reopened.get_scene(scene["scene_id"])["file_name"] == "entry.3dm"
    with reopened._connect() as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        reopened._project_file_reference(db, "entry.3dm", description="")
    assert reopened.list_project_files()["files"][0]["description"] == ""


def test_file_description_updates_by_model_path_do_not_merge_equal_filenames(tmp_path):
    store = AlmondStore(tmp_path / "scene.sqlite3")
    with store._connect() as db:
        first = store._project_file_reference(db, model_path=str(tmp_path / "a" / "same.3dm"), description="A")
        second = store._project_file_reference(db, model_path=str(tmp_path / "b" / "same.3dm"), description="B")
        assert first != second
        assert store._project_file_reference(db, model_path=str(tmp_path / "b" / "same.3dm"), description="B updated") == second
        with pytest.raises(ValueError, match="description"):
            store._project_file_reference(db, project_file_id=first, description=42)
    assert {r["description"] for r in store.list_project_files()["files"]} == {"A", "B updated"}


def test_native_layer_catalogue_retains_hidden_locked_and_reference_layers(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source = (Path(__file__).parents[1] / "features/context/native/DocumentObservation.cs").read_text(encoding="utf-8")
    (tmp_path / "Program.cs").write_text(LAYER_HARNESS.replace("// PRODUCTION_METHOD", method(source, "ListContextLayers")), encoding="utf-8")
    project = tmp_path / "ContextLayers.csproj"
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable></PropertyGroup>
  <ItemGroup><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildBinPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert built.returncode == 0, built.stdout + built.stderr
    run = subprocess.run([sdk, str(tmp_path / "bin/Release/net8.0/ContextLayers.dll")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert run.returncode == 0, run.stdout + run.stderr


LAYER_HARNESS = r'''
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
sealed class Layer {
    public string Name; public Guid Id = Guid.NewGuid(), ParentLayerId;
    public bool IsDeleted, IsVisible = true, IsLocked, IsReference;
}
sealed class RhinoDoc { public List<Layer> Layers = new List<Layer>(); }
static class Program {
    // PRODUCTION_METHOD
    static void Main() {
        var doc = new RhinoDoc();
        var root = new Layer { Name = "Root" };
        doc.Layers.Add(root);
        for (int i = 0; i < 1500; i++) doc.Layers.Add(new Layer {
            Name = "Repeated", ParentLayerId = root.Id, IsVisible = false, IsLocked = true, IsReference = true });
        doc.Layers.Add(new Layer { Name = "Deleted", IsDeleted = true });
        var result = ListContextLayers(doc);
        if (result.Count != 1501 || result.Skip(1).Any(row => (string)row["parent_id"] != root.Id.ToString()))
            throw new Exception("Lost layers or parent identities.");
        if (doc.Layers.Count != 1502 || doc.Layers[1].IsVisible || !doc.Layers[1].IsLocked)
            throw new Exception("Observation mutated the document.");
        if (ListContextLayers(new RhinoDoc()).Count != 0) throw new Exception("Empty layers changed.");
        Console.WriteLine("PASS: all live layers, hidden/locked/reference, duplicate names, no mutation");
    }
}
'''
