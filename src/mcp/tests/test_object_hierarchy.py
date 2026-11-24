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
    includes = [tests / "object_hierarchy_host/Fixture.cs", native / "ObservationEntities.cs", native / "ObjectHierarchy.cs",
                native / "ObjectScope.cs", native / "ObjectFilters.cs", native / "ObjectMetadataFilters.cs"]
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


def test_layer_full_paths_and_guids_filter_top_level_objects_before_grouping(hierarchy):
    case = {"scope": "document", "layers": [
        {"id": guid(201), "path": "1F::Wall"}, {"id": guid(202), "path": "2F::Wall"},
        {"id": guid(203), "path": "Roof"}],
        "objects": [{"id": guid(i), "layer": i - 1} for i in (1, 2, 3)],
        "filters": {"layer": {"include": [guid(201), "2f::wall"], "exclude": ["1F::Wall"]}}}
    result = hierarchy(case)
    assert [row["id"] for row in result["nodes"]] == [guid(2)]
    case["filters"]["layer"]["exclude"] = ["Basement"]
    failure = hierarchy(case)
    assert failure["status"] == "error" and "Basement" in failure["message"]
    case["layers"].append({"id": guid(204), "path": "2F::Wall"})
    case["filters"]["layer"] = {"include": ["2F::Wall"]}
    assert "ambiguous" in hierarchy(case)["message"].lower()


def test_group_membership_as_filter_does_not_change_the_query_scope(hierarchy):
    case = grouped_case()
    case["scope"] = "document"
    case["groups"][0]["name"] = "A"
    case["groups"][1]["name"] = "B"
    case["filters"] = {"group": {"include": ["a"], "exclude": [guid(102)]}}
    result = hierarchy(case)
    assert result["matched_count"] == 1 and result["source_count"] == 3
    assert guid(1) in [n["id"] for n in result["nodes"]]
    case["filters"]["group"] = {"exclude": ["missing group"]}
    assert "missing group" in hierarchy(case)["message"]
    case["groups"][1]["complete"] = False
    case["filters"]["group"] = {"exclude": ["B"]}
    assert "membership is uncertain" in hierarchy(case)["message"]


def test_effective_material_matches_legacy_and_render_ids_and_detects_name_collisions(hierarchy):
    case = {"scope": "document", "objects": [
        {"id": guid(1), "front": guid(40)}, {"id": guid(2), "render": guid(41)}, {"id": guid(3)}],
        "materials": [{"id": guid(40), "name": "Plaster", "render": guid(41)}],
        "render_materials": [{"id": guid(41), "name": "Plaster"}]}
    for value in ("plaster", guid(40), guid(41)):
        case["filters"] = {"material": {"include": [value]}}
        assert [n["id"] for n in hierarchy(case)["nodes"]] == [guid(1), guid(2)]
    case["materials"].append({"id": guid(49), "name": "Plaster"})
    case["filters"] = {"material": {"exclude": ["Plaster"]}}
    assert "Ambiguous filters.material" in hierarchy(case)["message"]
    case["filters"] = {"material": {"exclude": ["Missing"]}}
    assert "Missing" in hierarchy(case)["message"]


@pytest.mark.parametrize("group,expected", [
    ({"include":["A","B"],"include_mode":"any"}, [1,2,3]),
    ({"include":["A",guid(102)],"include_mode":"all"}, [2]),
    ({"exclude":["A","B"],"exclude_mode":"any"}, [4,5,6,7,8]),
    ({"exclude":["A","B"],"exclude_mode":"all"}, [1,3,4,5,6,7,8]),
    ({"include":["A","B"],"include_mode":"any","exclude":["A","B"],"exclude_mode":"all"}, [1,3]),
    ({"include":["A",guid(101)],"include_mode":"all","exclude":["B"]}, [1]),
])
def test_multi_group_query_matches_each_side_independently(hierarchy,group,expected):
    result = hierarchy({"objects":[{"id":guid(i)} for i in range(1,9)],"scope":"document",
                        "groups":[{"id":guid(101),"name":"A","members":[guid(1),guid(2)]},
                                  {"id":guid(102),"name":"B","members":[guid(2),guid(3)]}],
                        "filters":{"group":group},"matched_ids_only":True})
    assert result["ids"] == [guid(i) for i in expected]


@pytest.mark.parametrize("group,bad", [
    ({"include":["A","B"]},"include_mode"), ({"exclude_mode":"any"},"exclude"),
    ({"include":["A"],"include_mode":"all"},"multiple"), ({"exclude":["A","B"],"exclude_mode":"none"},"exclude_mode"),
    ({"include":["A","missing"],"include_mode":"any"},"missing"),
])
def test_multi_group_native_rejects_bad_modes_and_unknown_groups_even_on_empty_scope(hierarchy,group,bad):
    result = hierarchy({"objects":[],"groups":[{"id":guid(101),"name":"A","members":[]}],"filters":{"group":group}})
    assert result["status"] == "error" and bad in result["message"]


def test_metadata_source_type_exclusion_and_legacy_conjunction(hierarchy):
    case = {"scope":"document","objects":[
        {"id":guid(1),"text":{"key":"2"},"attribute_data":{"key":2}},
        {"id":guid(2),"text":{"key":"2"},"geometry_data":{"key":[2,3]}},
        {"id":guid(3),"attribute_data":{"key":"2"}}]}
    text = {"key":"key","any_of":["2"]}
    condition = {"source":"attributes","key":"key","any_of":[2]}
    def ids(filters):
        return [n["id"] for n in hierarchy({**case,"filters":filters})["nodes"]]
    assert ids({"user_text":{"include":[text]},"user_dictionary":{"exclude":[condition]}}) == [guid(2)]
    assert ids({"user_text":[text],"user_dictionary":[condition]}) == [guid(1)]
    assert ids({"user_dictionary":{"include":[{**condition,"source":"geometry"}]}}) == [guid(2)]
    assert ids({"user_dictionary":{"include":[{**condition,"any_of":["2"]}]}}) == [guid(3)]
    assert ids({"user_text":{"exclude":[text]}}) == [guid(3)]


def test_block_definition_object_name_and_type_filter_the_same_occurrence(hierarchy):
    case = {"scope": "document", "objects": [
        {"id": guid(1), "name": "Desk", "definition_id": guid(40), "definition_name": "Furniture", "members": []},
        {"id": guid(2), "name": "Desk lamp", "definition_id": guid(41), "definition_name": "Light", "members": []},
        {"id": guid(3), "name": "Desk"}],
        "filters": {"block": {"include": ["Furniture", guid(41)]}, "name": {"include": ["desk"]},
                    "object_type": {"exclude": ["BREP"]}}}
    assert [row["id"] for row in hierarchy(case)["nodes"]] == [guid(1)]
    case["filters"] = {"object_type": {"include": ["Typo"]}}
    assert "Typo" in hierarchy(case)["message"]
    case["filters"] = {"block": {"exclude": [guid(999)]}}
    assert guid(999) in hierarchy(case)["message"]


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


def test_current_excludes_hidden_object_and_ancestor_layer_locks_but_keeps_offscreen(hierarchy):
    case = {"scope": "current", "objects": [
        {"id": guid(1), "min_x": 20, "max_x": 21},
        {"id": guid(2), "hidden": True}, {"id": guid(3), "locked": True},
        {"id": guid(4), "layer": 2}], "layers": [
        {"id": guid(51)}, {"id": guid(52), "locked": True}, {"id": guid(53), "parent": guid(52)}]}
    result = hierarchy(case)
    assert [n["id"] for n in result["nodes"]] == [guid(1)]
    case["objects"][0]["selected"] = True
    case["current_selected"] = True
    assert hierarchy(case)["matched_count"] == 1  # Selection is not a screen intersection.


def test_inside_window_includes_crossing_bounds_and_marks_partial_group_scope(hierarchy):
    case = {"scope": "current", "inside_window": True, "objects": [
        {"id": guid(1), "min_x": -1, "max_x": 1},
        {"id": guid(2), "min_x": 9, "max_x": 12},
        {"id": guid(3), "min_x": 11, "max_x": 12}],
        "groups": [{"id": guid(101), "members": [guid(1), guid(2), guid(3)]}],
        "expand_groups": True, "depth": 2}
    result = hierarchy(case)
    assert [n["id"] for n in result["nodes"]] == [guid(101), guid(1), guid(2)]
    group = result["nodes"][0]
    assert group["member_count"] == 3 and group["matched_member_count"] == 2
    assert group["membership_complete"] and not group["all_members_in_scope"]


def test_unknown_editor_group_membership_is_not_a_complete_empty_group(hierarchy):
    result = hierarchy({"objects": [], "groups": [{"id": guid(101), "members": [], "complete": False}],
                        "group_ids": [guid(101)]})
    assert result["complete"] is False and result["membership_complete"] is False
    assert result["nodes"][0]["member_count"] is None
    assert result["nodes"][0]["children_state"] == "unavailable"


def test_group_inside_block_uses_the_occurrence_transform_and_never_document_ids(hierarchy):
    case = block_case()
    case["groups"] = [{"id": guid(101), "members": [guid(4)]}]
    case.update(expand_groups=True, depth=5)
    rows = hierarchy(case)["nodes"]
    leaves = [n for n in rows if n["id"] == guid(4)]
    assert len(leaves) == 2 and all(not n["document_object"] for n in leaves)
    assert [n["bounds"]["min_x"] for n in leaves] == [15, 25]
    groups = [n for n in rows if n["id"] == guid(101)]
    assert len(groups) == 2 and all(not n["document_object"] for n in groups)
    assert [n["root_object_id"] for n in groups] == [n["root_object_id"] for n in leaves]
    assert [n["block_path_ids"] for n in groups] == [n["block_path_ids"][:-1] for n in leaves]


def test_partial_nested_group_keeps_its_parent_and_excludes_overlapping_sibling(hierarchy):
    case = {"scope": "current", "objects": [{"id": guid(i)} for i in range(1, 6)],
            "groups": [{"id": guid(101), "name": "parent", "members": [guid(i) for i in range(1, 5)]},
                       {"id": guid(102), "name": "child", "members": [guid(1), guid(2)]},
                       {"id": guid(103), "name": "overlap", "members": [guid(1), guid(5)]}],
            "matched": [guid(1)], "expand_groups": True, "depth": 3}
    rows = hierarchy(case)["nodes"]
    parent = next(row for row in rows if row["id"] == guid(101))
    child = next(row for row in rows if row["id"] == guid(102))
    overlap = next(row for row in rows if row["id"] == guid(103))
    assert child["parent_number"] == parent["number"]
    assert child["matched_member_count"] == 1 and child["member_count"] == 2
    assert not child["all_members_in_scope"] and overlap["parent_number"] is None


def test_object_group_metadata_keeps_unknown_editor_counts_separate(hierarchy):
    row = hierarchy({"objects": [{"id": guid(1)}],
                     "groups": [{"id": guid(101), "members": [guid(1)], "complete": False}],
                     "group_metadata": True})
    assert row["member_count"] is None and row["visible_member_count"] is None
    assert row["members_outside_match_count"] is None and row["membership_complete"] is False
    assert row["observed_member_count"] == 1 and row["member_ids"] == [guid(1)]


def test_object_group_metadata_preserves_definition_members(hierarchy):
    row = hierarchy({"objects": [{"id": guid(1), "definition": True}],
                     "groups": [{"id": guid(101), "members": [guid(1)]}], "group_metadata": True})
    assert row["membership_complete"] is True and row["member_count"] == 1
    assert row["member_ids"] == [guid(1)]
