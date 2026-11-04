"""Run the production bounded impact traversal without Rhino or user documents."""
import json
import os
from pathlib import Path
import subprocess
from uuid import UUID
from xml.sax.saxutils import escape

import pytest


def guid(n):
    return str(UUID(int=n))


@pytest.fixture(scope="module")
def impact(tmp_path_factory):
    sdk = os.environ["ALMOND_TEST_DOTNET"]
    version = subprocess.run([sdk, "--version"], check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    newtonsoft = Path(sdk).parent / "sdk" / version / "Newtonsoft.Json.dll"
    tests = Path(__file__).resolve().parent
    files = [tests / "block_definition_impact_host/Fixture.cs", tests.parent / "features/context/native/BlockDefinitionImpact.cs"]
    folder = tmp_path_factory.mktemp("block-impact")
    items = "".join(f'<Compile Include="{escape(str(path))}" />' for path in files)
    (folder / "NuGet.Config").write_text('<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    (folder / "Impact.csproj").write_text(f'''<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>
<EnableDefaultCompileItems>false</EnableDefaultCompileItems><NuGetAudit>false</NuGetAudit></PropertyGroup>
<ItemGroup>{items}<Reference Include="Newtonsoft.Json"><HintPath>{escape(str(newtonsoft))}</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    env = {**os.environ, "DOTNET_CLI_HOME": str(folder / "home"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}
    build = subprocess.run([sdk, "build", "Impact.csproj", "--nologo", "-v:q", "-o", "out", "/p:UseSharedCompilation=false"],
                           cwd=folder, env=env, capture_output=True, text=True, timeout=60)
    assert build.returncode == 0, build.stdout + build.stderr

    def run(value):
        result = subprocess.run([sdk, str(folder / "out/Impact.dll")], input=json.dumps(value), cwd=folder, env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)
    return run


def shared_case():
    return {"target": guid(10), "definitions": [
        {"id": guid(10), "containers": [guid(20)]},
        {"id": guid(20), "members": [{"id": guid(30), "definition": guid(10)}, {"id": guid(31), "definition": guid(10)}]}],
        "roots": [{"id": guid(1), "definition": guid(20)}, {"id": guid(2), "definition": guid(20)}]}


def test_shared_nested_members_are_four_occurrences_not_two_definition_ids(impact):
    result = impact(shared_case())
    assert result["complete"] and result["occurrence_count"] == 4 and result["affected_root_count"] == 2
    assert [(row["root_object_id"], row["block_path_ids"]) for row in result["occurrences"]] == [
        (guid(root), [guid(member)]) for root in (1, 2) for member in (30, 31)]
    assert result["container_definitions"][0]["definition_id"] == guid(20)


def test_editor_observations_never_certify_original_impact_or_zero(impact):
    case = shared_case()
    case.update(stable=False, roots=[])
    result = impact(case)
    assert not result["complete"] and result["document_scan_complete"]
    assert result["occurrence_count"] is None and result["affected_root_count"] is None
    assert result["observed_occurrence_count"] == 0


def test_cycle_retains_observations_but_never_reports_complete_impact(impact):
    case = shared_case()
    case["definitions"][0]["members"] = [{"id": guid(40), "definition": guid(20)}]
    result = impact(case)
    assert not result["complete"] and result["occurrence_count"] is None
    assert "cycle" in result["limits"] and result["observed_occurrence_count"] > 0


def test_bounded_path_list_does_not_turn_exact_counts_into_a_partial_total(impact):
    case = shared_case()
    case["roots"] = [{"id": guid(1000 + i), "definition": guid(10)} for i in range(513)]
    case["definitions"][0].update(reference=True, linked=True, source="external.3dm")
    result = impact(case)
    assert result["complete"] and result["occurrence_count"] == 513
    assert len(result["occurrences"]) == 512 and result["occurrences_truncated"]
    assert result["definition_is_reference"] and result["source_archive_present"] and result["update_type"] == "Linked"
    assert result["editing_permission"] == "not_granted_by_read_only_analysis"


def test_unused_definition_has_verified_zero_only_in_stable_document(impact):
    case = shared_case()
    case["roots"] = []
    result = impact(case)
    assert result["complete"] and result["occurrence_count"] == 0
    assert result["container_definitions"]  # Unplaced definitions still retain a reference.


def test_layout_instances_count_toward_shared_definition_impact(impact):
    case = shared_case()
    case["roots"][1]["page"] = True
    result = impact(case)
    assert result["complete"] and result["affected_root_count"] == 2 and result["occurrence_count"] == 4
    assert {row["root_space"] for row in result["occurrences"]} == {"ModelSpace", "PageSpace"}


def test_repeated_definition_reads_ordinary_members_once(impact):
    case = shared_case()
    case["definitions"][0]["extra_members"] = 50000
    case["roots"] = [{"id": guid(1000 + i), "definition": guid(20)} for i in range(200)]
    result = impact(case)
    assert result["complete"] and result["fixture_definition_reads"] == {guid(10): 1, guid(20): 1}


def test_member_budget_stops_before_allocating_an_oversized_definition(impact):
    case = shared_case()
    case["definitions"][0]["extra_members"] = 100001
    result = impact(case)
    assert not result["complete"] and result["occurrence_count"] is None
    assert "definition_member_limit" in result["limits"]
    assert result["fixture_definition_reads"][guid(10)] == 0
