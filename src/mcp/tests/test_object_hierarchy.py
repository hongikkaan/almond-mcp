"""Production C# hierarchy logic with in-memory Rhino API doubles, no live Rhino."""
import json
import os
from pathlib import Path
import subprocess
from uuid import UUID
from xml.sax.saxutils import escape

import pytest


def guid(number):
    return str(UUID(int=number))


@pytest.fixture(scope="module")
def hierarchy(tmp_path_factory):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Use the official MCP test runner with a .NET 8 SDK."
    version = subprocess.run([sdk, "--version"], check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    newtonsoft = Path(sdk).parent / "sdk" / version / "Newtonsoft.Json.dll"
    folder = tmp_path_factory.mktemp("hierarchy")
    tests = Path(__file__).resolve().parent
    native = tests.parent / "features/context/native"
    includes = [tests / "object_hierarchy_host/Fixture.cs", native / "ObservationEntities.cs", native / "ObjectHierarchy.cs"]
    compile_items = "".join(f'<Compile Include="{escape(str(p))}" Link="{p.name}" />' for p in includes)
    (folder / "NuGet.Config").write_text('<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    (folder / "Hierarchy.csproj").write_text(f'''<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>
<EnableDefaultCompileItems>false</EnableDefaultCompileItems><NuGetAudit>false</NuGetAudit></PropertyGroup>
<ItemGroup>{compile_items}<Reference Include="Newtonsoft.Json"><HintPath>{escape(str(newtonsoft))}</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    environment = {**os.environ, "DOTNET_CLI_HOME": str(folder / "home"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                   "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1", "DOTNET_NOLOGO": "1"}
    built = subprocess.run([sdk, "build", "Hierarchy.csproj", "--nologo", "-v:q", "-o", "out", "/p:UseSharedCompilation=false"],
                           cwd=folder, env=environment, capture_output=True, text=True, timeout=60)
    assert built.returncode == 0, built.stdout + built.stderr

    def invoke(case):
        run = subprocess.run([sdk, str(folder / "out/Hierarchy.dll")], input=json.dumps(case),
                             cwd=folder, env=environment, capture_output=True, text=True, timeout=30)
        assert run.returncode == 0, run.stdout + run.stderr
        return json.loads(run.stdout)

    return invoke


def grouped_case():
    return {"objects": [{"id": guid(n)} for n in (1, 2, 3)],
            "groups": [{"id": guid(101), "members": [guid(1), guid(2)]},
                       {"id": guid(102), "members": [guid(2), guid(3)]}],
            "expand_groups": True, "depth": 4}


def test_overlapping_groups_are_separate_branches_not_a_fabricated_parent(hierarchy):
    result = hierarchy(grouped_case())
    assert result["status"] == "success"
    assert result["source_count"] == 3 and result["root_count"] == 2
    nodes = result["nodes"]
    assert [(n["id"], n["parent_number"]) for n in nodes] == [
        (guid(101), None), (guid(1), 1), (guid(2), 1),
        (guid(102), None), (guid(2), 4), (guid(3), 4)]


def test_explicit_group_does_not_pull_in_overlapping_group_outside_members(hierarchy):
    case = grouped_case()
    case["group_ids"] = [guid(101)]
    result = hierarchy(case)
    assert result["source_count"] == 2
    assert [n["id"] for n in result["nodes"]] == [guid(101), guid(1), guid(2)]


def test_partial_selection_and_filtering_keep_distinct_group_semantics(hierarchy):
    case = grouped_case()
    case["selected"] = [guid(1)]
    result = hierarchy(case)
    assert result["root_count"] == 1 and result["nodes"][0]["entity_kind"] == "object"
    case["group_ids"] = [guid(101)]
    case["matched"] = [guid(1)]
    result = hierarchy(case)
    assert result["nodes"][0]["entity_kind"] == "group"
    assert result["nodes"][0]["member_count"] == 2
    assert result["nodes"][0]["matched_member_count"] == 1
    assert [n["id"] for n in result["nodes"]] == [guid(101), guid(1)]


def test_equal_members_are_siblings_and_strict_subgroups_have_explicit_parents(hierarchy):
    case = grouped_case()
    case["groups"] = [{"id": guid(101), "members": [guid(1), guid(2)]},
                      {"id": guid(102), "members": [guid(1), guid(2)]},
                      {"id": guid(103), "members": [guid(1)]}]
    nodes = hierarchy(case)["nodes"]
    roots = [n for n in nodes if n["parent_number"] is None]
    assert {n["id"] for n in roots} == {guid(101), guid(102), guid(3)}
    group_numbers = {n["number"] for n in roots if n["entity_kind"] == "group"}
    subgroups = [n for n in nodes if n["id"] == guid(103)]
    assert len(subgroups) == 2 and all(n["parent_number"] in group_numbers for n in subgroups)


def block_case():
    return {"objects": [
        {"id": guid(1), "members": [guid(3)], "x": 10},
        {"id": guid(2), "members": [guid(3)], "x": 20},
        {"id": guid(3), "members": [guid(4)], "x": 5, "definition": True},
        {"id": guid(4), "definition": True}], "expand_blocks": True, "depth": 3}


def test_reused_nested_block_members_have_distinct_root_paths_and_world_bounds(hierarchy):
    result = hierarchy(block_case())
    leaves = [n for n in result["nodes"] if n["id"] == guid(4)]
    assert len(leaves) == 2
    assert [n["root_object_id"] for n in leaves] == [guid(1), guid(2)]
    assert all(n["block_path_ids"] == [guid(3), guid(4)] and not n["document_object"] for n in leaves)
    assert [n["bounds"]["min_x"] for n in leaves] == [15, 25]
    assert all(n["visible"] is None and n["selected"] is None for n in leaves)


def test_depth_collapsed_and_paginated_parent_relationships_are_not_lost(hierarchy):
    case = block_case()
    case["depth"] = 2
    result = hierarchy(case)
    assert result["depth_limited"] and result["complete"]
    assert any(n["children_state"] == "depth_limit" for n in result["nodes"])
    case.update(offset=1, limit=1)
    page = hierarchy(case)
    assert page["nodes"][0]["number"] == 2 and page["nodes"][0]["parent_number"] == 1
    assert not page["complete"] and page["next_offset"] == 2
    case.update(expand_blocks=False, offset=0, limit=200)
    collapsed = hierarchy(case)
    assert not collapsed["depth_limited"] and collapsed["hierarchy_count"] == 2
    assert all(n["children_state"] == "collapsed" for n in collapsed["nodes"])


def test_recursive_block_reference_stops_with_cycle_evidence(hierarchy):
    case = block_case()
    case["objects"][2]["members"] = [guid(3)]
    case["depth"] = 8
    result = hierarchy(case)
    assert result["cycle_limited"]
    assert any(n["children_state"] == "cycle" for n in result["nodes"])


def test_stale_group_is_error_not_empty_success(hierarchy):
    case = grouped_case()
    case["group_ids"] = [guid(999)]
    result = hierarchy(case)
    assert result["status"] == "error" and "Unknown group" in result["message"]
