"""Compile the production object query against read-only Rhino doubles, without Rhino."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from xml.sax.saxutils import escape

import pytest


ROOT = Path(__file__).resolve().parents[3]
FIRST = "10000000-0000-0000-0000-000000000001"
SECOND = "10000000-0000-0000-0000-000000000002"


@pytest.fixture(scope="module")
def observation_native(tmp_path_factory):
    sdk = os.environ.get("ALMOND_TEST_DOTNET") or shutil.which("dotnet")
    assert sdk, "The offline object-observation fixture requires the .NET 8 SDK."
    directory = tmp_path_factory.mktemp("object-observation-native")
    shutil.copyfile(ROOT / "global.json", directory / "global.json")
    assembly = ROOT / "src/rhp/RhinoAlmondBridge/plugin-runtime/Newtonsoft.Json.dll"
    source = ROOT / "src/mcp/features/context/native/ObjectObservation.cs"
    assert assembly.is_file()
    (directory / "Fixture.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <ItemGroup><Compile Include="''' + escape(str(source)) + '''" />
  <Reference Include="Newtonsoft.Json"><HintPath>''' + escape(str(assembly)) + '''</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    (directory / "NuGet.Config").write_text(
        '<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    shutil.copyfile(Path(__file__).with_name("fixtures") / "ObjectObservationStub.cs", directory / "Program.cs")
    built = subprocess.run([str(sdk), "build", "Fixture.csproj", "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           cwd=directory, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    return str(sdk), directory / "bin/Release/net8.0/Fixture.dll"


def native_case(fixture, scenario):
    sdk, binary = fixture
    ran = subprocess.run([sdk, str(binary), scenario], capture_output=True, text=True)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    payload = json.loads(ran.stdout)
    assert payload["user_dictionary_getter_calls"] == 0
    assert payload["source_unchanged"]
    return payload["result"]


@pytest.mark.parametrize("source", ["attributes", "geometry"])
@pytest.mark.parametrize("position", ["first", "last"])
def test_dictionary_filter_reads_full_257_item_value_before_display_budget(observation_native, source, position):
    result = native_case(observation_native, f"long_{source}_{position}")
    assert result["status"] == "success" and result["matched_count"] == 1
    row = result["objects"][0]
    assert row["id"] == FIRST and row["geometry_crc"] == 123
    # A presentation omission must not become a filter omission.
    omitted = row["user_dictionary"][source]["values"]["Floor"]
    assert omitted["value_omitted"] and omitted["unsupported_type"]


def test_dictionary_filter_preserves_scalar_vs_multivalue_meaning(observation_native):
    result = native_case(observation_native, "scalar_exact")
    assert result["status"] == "success"
    assert [row["id"] for row in result["objects"]] == [FIRST]
    assert result["objects"][0]["user_dictionary"]["attributes"]["values"]["Floor"] == ["GF", "B1"]


@pytest.mark.parametrize("scenario", ["missing_dictionary", "missing_geometry_dictionary"])
def test_missing_dictionary_is_empty_without_allocating_user_data(observation_native, scenario):
    result = native_case(observation_native, scenario)
    assert result["status"] == "success" and result["matched_count"] == 2
    for row in result["objects"]:
        for source in ("attributes", "geometry"):
            assert row["user_dictionary"][source] == {"values": {}, "total_keys": 0, "truncated": False}


def test_missing_dictionary_does_not_match_filter_or_allocate_user_data(observation_native):
    result = native_case(observation_native, "missing_filter")
    assert result["status"] == "success" and result["matched_count"] == 0
    assert result["objects"] == []


@pytest.mark.parametrize("scenario", ["selected", "ids"])
def test_query_does_not_expand_groups_and_reports_members_outside_match(observation_native, scenario):
    result = native_case(observation_native, scenario)
    assert result["status"] == "success" and result["source_count"] == 1
    assert [row["id"] for row in result["objects"]] == [FIRST]
    assert result["document_visible_count"] == 2 and result["visible_outside_match_count"] == 1
    group = result["objects"][0]["groups"][0]
    assert group["member_count"] == 2 and group["members_outside_match_count"] == 1
    assert group["member_ids"] == [FIRST, SECOND]


def test_document_visibility_is_distinct_from_object_hidden_flag(observation_native):
    result = native_case(observation_native, "layer_hidden")
    assert result["status"] == "success" and result["matched_count"] == 2
    assert result["document_visible_count"] == 1 and result["matched_visible_count"] == 1
    rows = {row["id"]: row for row in result["objects"]}
    assert rows[FIRST]["visible"] and rows[FIRST]["selected"]
    assert not rows[SECOND]["visible"] and not rows[SECOND]["hidden"]
    assert rows[SECOND]["geometry_crc"] == 456


def test_visible_scope_uses_actual_visibility_without_expanding_selected_group(observation_native):
    result = native_case(observation_native, "visible")
    assert result["status"] == "success" and result["source_count"] == 1
    assert [row["id"] for row in result["objects"]] == [FIRST]
    assert result["objects"][0]["groups"][0]["visible_member_count"] == 1


def test_unsupported_metadata_is_explicit_without_reading_arbitrary_properties(observation_native):
    result = native_case(observation_native, "unsupported")
    value = result["objects"][0]["user_dictionary"]["attributes"]["values"]["Floor"]
    assert result["status"] == "success"
    assert value == {"unsupported_type": "UnsafeMetadata", "value_omitted": True}


def test_filter_over_budget_fails_instead_of_silently_omitting_last_value(observation_native):
    result = native_case(observation_native, "filter_over_budget")
    assert result["status"] == "error" and result["error_code"] == "invalid_arguments"
    assert "4096" in result["message"]


def test_query_excludes_pages_deleted_and_definition_objects(observation_native):
    result = native_case(observation_native, "non_model_objects")
    assert result["status"] == "success" and result["source_count"] == 2
    assert [row["id"] for row in result["objects"]] == [FIRST, SECOND]
