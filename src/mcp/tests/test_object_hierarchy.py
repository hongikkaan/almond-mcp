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
                native / "ObjectObservation.cs", native / "ObjectScope.cs", native / "ObjectFilters.cs",
                native / "ObjectMetadataFilters.cs"]
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


def group_observation_case():
    return {
        "objects": [{"id": guid(n), "hidden": n == 70, "definition": n == 69} for n in range(1, 71)],
        "groups": [
            {"id": guid(101), "name": "Main", "members": [guid(n) for n in range(70, 0, -1)]},
            {"id": guid(102), "name": "Exclude", "members": [guid(4)]},
        ],
        "request": {"scope": "current", "group_ids": [guid(101)], "fields": ["id", "groups"], "limit": 4,
                    "filters": {"group": {"include": ["Main"], "exclude": ["Exclude"]}}},
    }


def group_hierarchy_case():
    return {
        "objects": [{"id": guid(n), "min_x": n, "max_x": n + 1} for n in range(1, 5)],
        "groups": [
            {"id": guid(101), "name": "Parent", "members": [guid(1), guid(2), guid(3)]},
            {"id": guid(102), "name": "Child", "members": [guid(1), guid(2)]},
            {"id": guid(103), "name": "Overlap", "members": [guid(3), guid(4)]},
        ],
        "request": {"scope": "document", "group_ids": [guid(101)], "result_mode": "hierarchy",
                    "fields": ["id", "name", "bounds"], "expand_groups": True, "depth": 4},
    }


def geometry_observation_case():
    return {
        "objects": [{"id": guid(1), "crc": 42, "faces": [0, 1, 2]}, {"id": guid(2), "crc": 43}],
        "request": {"scope": "document", "object_ids": [guid(1), guid(2)], "fields": ["geometry_crc", "faces"],
                    "face_offset": 1, "face_limit": 1, "expected_geometry_crcs": {guid(1): 42, guid(2): 43}},
    }


def placed_hierarchy_case():
    shared_definition = {"definition_id": guid(201), "members": [guid(3), guid(5)]}
    return {
        "objects": [
            {"id": guid(1), **shared_definition, "xy_matrix": [0, -1, 1, 0], "x": 10, "y": 20},
            {"id": guid(2), **shared_definition, "xy_matrix": [-1, 0, 0, 2], "x": -10, "y": 4},
            {"id": guid(3), "definition": True, "members": [guid(4)], "xy_matrix": [-2, 0, 0, 3], "x": 5, "y": 2},
            {"id": guid(4), "definition": True, "min_x": 1, "max_x": 3, "min_y": 2, "max_y": 4},
            {"id": guid(5), "definition": True, "min_x": 2, "max_x": 1},
        ],
        "groups": [{"id": guid(101), "members": [guid(4)]}],
        "request": {"scope": "document", "result_mode": "hierarchy", "fields": ["id", "bounds"],
                    "expand_blocks": True, "expand_groups": True, "depth": 5},
    }


def test_block_hierarchy_places_each_reused_definition_occurrence_once(hierarchy):
    observed = hierarchy(placed_hierarchy_case())
    response = observed["response"]
    assert response["status"] == "success" and response["root_count"] == 2
    rows = {(row["root_object_id"], row["id"]): row for row in response["nodes"]}
    world_bounds = ({"min": [-4, 19, 0], "max": [2, 23, 0]}, {"min": [-13, 20, 0], "max": [-9, 32, 0]})
    for root, bounds in zip((guid(1), guid(2)), world_bounds):
        group, leaf, invalid = (rows[root, guid(n)] for n in (101, 4, 5))
        assert group["bounds"] == leaf["bounds"] == bounds
        assert group["block_path_ids"] == [guid(3)] and leaf["block_path_ids"] == [guid(3), guid(4)]
        assert not group["document_object"] and not leaf["document_object"]
        assert invalid["bounds"] is None and invalid["block_path_ids"] == [guid(5)]
    assert observed["bounds_reads"] == 10


@pytest.mark.parametrize("group_source, expected, member_reads", [
    ({"members": [guid(2)]}, [12, 14], 0),
    ({"members": [guid(2)], "bounds": [-9, -5]}, [12, 14], 0),
    ({"bounds": [-9, -5]}, [10, 14], 1),
])
def test_public_roots_calculates_bounds_from_group_members(hierarchy, group_source, expected, member_reads):
    observed = hierarchy({
        "objects": [{"id": guid(1), "min_x": 10, "max_x": 11}, {"id": guid(2), "min_x": 12, "max_x": 14}],
        "groups": [{"id": guid(101), "members": [guid(1), guid(2)]}],
        "public_group_source": group_source,
    })
    assert observed["bounds"] == {"min": [expected[0], 0, 0], "max": [expected[1], 0, 0]}
    assert observed["member_reads"] == member_reads


def test_observation_reuses_crc_for_face_pages(hierarchy):
    observed = hierarchy(geometry_observation_case())
    response = observed["response"]
    assert response["status"] == "success"
    first, second = response["objects"]
    assert first["id"] == guid(1) and first["geometry_crc"] == 42
    assert first["face_page"] == {"offset": 1, "limit": 1, "returned": 1, "next_offset": 2, "complete": False}
    assert [face["face_index"] for face in first["faces"]] == [1]
    assert second == {"geometry_crc": 43, "face_edit_supported": False}
    assert observed["crc_reads"] == 2


def test_observation_rejects_stale_face_crc_before_snapshot(hierarchy):
    case = geometry_observation_case()
    case["request"]["expected_geometry_crcs"][guid(1)] = 1
    observed = hierarchy(case)
    assert observed["response"]["error_code"] == "stale_geometry"
    assert observed["crc_reads"] == 1


def test_observation_reuses_group_reads_and_keeps_row_metadata_independent(hierarchy):
    observed = hierarchy(group_observation_case())
    response = observed["response"]
    assert response["status"] == "success"
    assert response["source_count"] == 68 and response["matched_count"] == 67
    rows = response["objects"]
    assert [row["id"] for row in rows] == [guid(n) for n in (1, 2, 3, 5)]
    assert all(row["groups"] == rows[0]["groups"] for row in rows)
    assert rows[0]["groups"] == [{
        "id": guid(101), "name": "Main", "member_count": 70, "members_outside_match_count": 3,
        "visible_member_count": 68, "membership_complete": True, "membership_basis": "document_group_table",
        "observed_member_count": 70, "observed_members_outside_match_count": 3, "observed_visible_member_count": 68,
        "member_ids": [guid(n) for n in range(70, 6, -1)], "members_truncated": True,
    }]
    assert observed["independent_rows"]
    assert observed["member_reads"] == 2


def test_observation_reuses_group_roots_and_preserves_hierarchy_scope(hierarchy):
    observed = hierarchy(group_hierarchy_case())
    response = observed["response"]
    assert response["status"] == "success"
    assert response["root_count"] == 1 and response["hierarchy_count"] == 5
    rows = response["nodes"]
    assert {row["id"] for row in rows} == {guid(n) for n in (101, 102, 1, 2, 3)}
    parent = next(row for row in rows if row["id"] == guid(101))
    child = next(row for row in rows if row["id"] == guid(102))
    assert parent["parent_number"] is None and child["parent_number"] == parent["number"]
    assert parent["matched_member_count"] == 3 and child["matched_member_count"] == 2
    assert parent["bounds"] == {"min": [1, 0, 0], "max": [4, 0, 0]}
    assert child["bounds"] == {"min": [1, 0, 0], "max": [3, 0, 0]}
    assert observed["member_reads"] == 3
    assert observed["bounds_reads"] == 10


def test_observation_reuses_incomplete_editor_members_without_certifying_them(hierarchy):
    case = group_observation_case()
    case["editor_stable"] = False
    case["groups"][0]["complete"] = False
    filters = case["request"].pop("filters")
    observed = hierarchy(case)
    response = observed["response"]
    assert response["status"] == "success" and not response["membership_complete"]
    groups = [row["groups"][0] for row in response["objects"]]
    assert all(group["member_count"] is None and group["members_outside_match_count"] is None
               and group["visible_member_count"] is None and group["observed_member_count"] == 70
               and group["observed_members_outside_match_count"] == 2 and group["observed_visible_member_count"] == 68
               and group["membership_basis"] == "editor_incomplete" for group in groups)
    assert observed["member_reads"] == 2
    case["request"]["filters"] = filters
    filtered = hierarchy(case)
    assert filtered["response"]["error_code"] == "invalid_arguments"
    assert "filters.group.include membership is uncertain during editing" in filtered["response"]["message"]
    assert filtered["member_reads"] == 1


def test_observation_checks_group_scope_and_snapshot_before_filters(hierarchy):
    case = group_observation_case()
    case["request"]["group_ids"] = [guid(999)]
    case["request"]["expected_snapshot"] = "stale"
    case["request"]["filters"]["group"]["include"] = ["Unknown filter"]
    response = hierarchy(case)["response"]
    assert response["error_code"] == "invalid_arguments" and "Unknown group GUID" in response["message"]
    case["request"]["group_ids"] = [guid(101)]
    assert hierarchy(case)["response"]["error_code"] == "observation_changed"
    del case["request"]["expected_snapshot"]
    response = hierarchy(case)["response"]
    assert response["error_code"] == "invalid_arguments" and "Unknown filters.group reference" in response["message"]


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
    assert [n["bounds"]["min"][0] for n in leaves] == [15, 25]
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
    assert [n["bounds"]["min"][0] for n in leaves] == [15, 25]
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
