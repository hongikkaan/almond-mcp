"""Step completion through the registered MCP tool and a disposable planning database."""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore


@pytest.fixture
def completion(tmp_path, monkeypatch):
    model_path = str(tmp_path / "fixture.3dm")
    monkeypatch.setenv("ALMOND_MODEL_PATH", model_path)
    bridge_requests = []
    observed = []

    def native(payload, **options):
        request = json.loads(payload)
        bridge_requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"step_temp_cleanup": 1}})
        assert request == {"type": "cleanup_step_temp", "expected_model_path": model_path}
        saved = store.get_step(plan["plan_id"], step["step_id"])
        observed.append((saved["step"]["status"], saved["revision"], saved["step"]["takeaways"]))
        return json.dumps({"status": "success", "cleanup": {"deleted_layers": 3, "deleted_objects": 2}})

    store = AlmondStore(tmp_path / "planning.sqlite3")
    plan = store.create_plan("Review entrance", scope="inspection")
    step = plan["steps"][0]
    context = SimpleNamespace(retrieval_store=store, _send_and_receive=native)
    server = FastMCP("step-completion-test")
    register(server, context)

    def call(tool, **arguments):
        async def run():
            async with Client(server) as client:
                result = await client.call_tool(tool, arguments)
                return json.loads(result.content[0].text)
        return asyncio.run(run())

    def update(**fields):
        return call("plan_12-update", request={"target": "step", "plan_id": plan["plan_id"],
                    "step_id": step["step_id"], **fields})

    def read():
        return call("plan_05-get", request={"target": "step", "plan_id": plan["plan_id"],
                    "step_id": step["step_id"], "include_details": True})

    return SimpleNamespace(update=update, read=read, bridge_requests=bridge_requests,
                           context=context, plan=plan, native=native, observed=observed)


def test_completion_commits_in_one_call_then_runs_rhino_without_a_notice(completion, tmp_path):
    artifact = tmp_path / "handoff.3dm"
    artifact.write_bytes(b"preserve this file")
    store = completion.context.retrieval_store
    for sibling in completion.plan["steps"][1:]:
        store.update_plan_step(completion.plan["plan_id"], sibling["step_id"], "completed")
    registered_files = store.list_project_files()
    before = completion.read()
    result = completion.update(
        status="completed", takeaways="Record the entrance decision",
        design_rationale="Keep the circulation axis", input_refs={"add": ["survey.md"]},
        output_refs={"add": [str(artifact)]}, expected_revision=before["revision"], loop_no=before["loop_no"],
    )
    assert result["status"] == "updated" and result["changed"] is True
    assert result["step"]["status"] == "completed"
    assert result["plan"]["status"] == "pending"
    assert result["plan"]["revision"] == before["revision"] + 1
    assert {"confirmation", "cleanup", "cleanup_state", "requires_reconciliation"}.isdisjoint(result)
    assert [request["type"] for request in completion.bridge_requests] == [
        "get_rhino_context", "cleanup_step_temp"]
    assert completion.observed == [("completed", before["revision"] + 1, "Record the entrance decision")]
    assert not any(word in json.dumps(result, ensure_ascii=False).lower()
                   for word in ("temp", "삭제", "정리", "confirmation", "cleanup"))
    after = completion.read()
    assert after["status"] == "completed" and after["revision"] == before["revision"] + 1
    assert after["step"]["takeaways"] == "Record the entrance decision"
    assert after["step"]["design_rationale"] == "Keep the circulation axis"
    assert after["step"]["input_refs"] == ["survey.md"]
    assert after["step"]["output_refs"] == [str(artifact)]
    assert store.list_project_files() == registered_files
    assert artifact.read_bytes() == b"preserve this file"


def test_cleanup_runs_only_on_transition_to_completed(completion):
    first = completion.update(status="completed")
    second = completion.update(status="completed")
    assert first["status"] == "updated" and second["status"] == "no_change"
    assert first["changed"] is True and second["changed"] is False
    assert first["plan"]["revision"] == second["plan"]["revision"]
    assert len(completion.bridge_requests) == 2
    assert completion.update(status="completed", takeaways="Revised notes")["status"] == "updated"
    assert completion.update(status="running")["status"] == "updated"
    assert len(completion.bridge_requests) == 2
    assert completion.update(status="completed")["status"] == "updated"
    assert len(completion.bridge_requests) == 4


@pytest.mark.parametrize("change", ["revision", "loop"])
def test_completion_rejects_stale_revision_or_loop(completion, change):
    old = completion.read()
    store = completion.context.retrieval_store
    if change == "revision":
        store.edit_plan(completion.plan["plan_id"], title="Updated")
    else:
        store.execute_looping(completion.plan["plan_id"])
    current = completion.read()
    result = completion.update(status="completed", takeaways="Stale request",
                               expected_revision=old["revision"], loop_no=old["loop_no"])
    assert result["status"] == "error"
    assert completion.read() == current
    assert completion.bridge_requests == []


@pytest.fixture(scope="module")
def native_cleanup(tmp_path_factory):
    sdk = os.environ["ALMOND_TEST_DOTNET"]
    version = subprocess.run([sdk, "--version"], check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    newtonsoft = Path(sdk).parent / "sdk" / version / "Newtonsoft.Json.dll"
    tests = Path(__file__).resolve().parent
    files = [tests / "step_temp_cleanup_host/Fixture.cs", tests.parent / "features/planning/native/StepTempCleanup.cs"]
    folder = tmp_path_factory.mktemp("step-temp-cleanup")
    items = "".join(f'<Compile Include="{escape(str(path))}" />' for path in files)
    (folder / "NuGet.Config").write_text('<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    (folder / "Cleanup.csproj").write_text(f'''<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>
<EnableDefaultCompileItems>false</EnableDefaultCompileItems><NuGetAudit>false</NuGetAudit></PropertyGroup>
<ItemGroup>{items}<Reference Include="Newtonsoft.Json"><HintPath>{escape(str(newtonsoft))}</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    env = {**os.environ, "DOTNET_CLI_HOME": str(folder / "home"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
           "DOTNET_GENERATE_ASPNET_CERTIFICATE": "false", "DOTNET_NOLOGO": "1"}
    build = subprocess.run([sdk, "build", "Cleanup.csproj", "--nologo", "-v:q", "-o", "out", "/p:UseSharedCompilation=false"],
                           cwd=folder, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    assert build.returncode == 0, build.stdout + build.stderr

    def run(scenario):
        result = subprocess.run([sdk, str(folder / "out/Cleanup.dll"), scenario], cwd=folder, env=env,
                                capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)
    return run


@pytest.mark.parametrize("scenario,deleted,current_layer", [("clear", 2, 1), ("light", 3, 1), ("new-current", 2, 6)])
def test_native_cleanup_removes_current_temp_tree_and_preserves_other_data(native_cleanup, scenario, deleted, current_layer):
    result = native_cleanup(scenario)
    assert result["result"] == {"status": "success", "cleanup": {"deleted_layers": 2, "deleted_objects": deleted}}
    expected_layers = ["Drawing", "Temp", "temp", "temp"]
    if scenario == "new-current":
        expected_layers.append("Layer 01")
    assert result["layers"] == expected_layers
    assert result["objects"] == 2
    assert result["current_layer"] == current_layer
    assert result["drawing_preserved"] and result["attachment_preserved"]


def test_native_cleanup_with_only_an_attachment_temp_reports_zero(native_cleanup):
    result = native_cleanup("no-local-temp")
    assert result["result"] == {"status": "success", "cleanup": {"deleted_layers": 0, "deleted_objects": 0}}
    assert result["layers"] == ["Drawing", "Study", "tests", "empty", "temp", "temp"]
    assert result["objects"] == 4
    assert result["current_layer"] == 2
    assert result["attachment_preserved"]


def test_native_cleanup_keeps_a_current_temp_root_with_no_children(native_cleanup):
    outcome = native_cleanup("root-only")
    assert outcome["result"] == {"status": "success", "cleanup": {"deleted_layers": 0, "deleted_objects": 1}}
    assert outcome["current_layer"] == 1 and "Temp" in outcome["layers"]


@pytest.mark.parametrize("stage", ["write", "commit"])
def test_failed_completion_db_update_preserves_state_without_rhino(completion, stage):
    with sqlite3.connect(completion.context.retrieval_store.database_path) as db:
        if stage == "write":
            db.executescript("""
                CREATE TRIGGER reject_step_write BEFORE UPDATE OF status ON generation_loop_steps
                WHEN new.status = 'completed' BEGIN SELECT RAISE(ABORT, 'write rejected'); END;
            """)
        else:
            db.executescript("""
                CREATE TABLE fixture_parent(id INTEGER PRIMARY KEY);
                CREATE TABLE fixture_child(parent_id INTEGER REFERENCES fixture_parent(id) DEFERRABLE INITIALLY DEFERRED);
                CREATE TRIGGER reject_step_commit AFTER UPDATE OF status ON generation_loop_steps
                WHEN new.status = 'completed' BEGIN INSERT INTO fixture_child VALUES (999); END;
            """)
    before = completion.read()
    result = completion.update(status="completed", takeaways="No partial update")
    assert result["status"] == "error"
    assert result["error_code"] == "step_completion_db_failed"
    assert result["cleanup_state"] == "not_started"
    assert result["changed"] is False and result["requires_reconciliation"] is False
    assert completion.bridge_requests == []
    assert completion.read() == before


@pytest.mark.parametrize("reply,state", [
    ({"status": "error", "cleanup_state": "rolled_back", "message": "Could not delete layer."}, "rolled_back"),
    (None, "unknown"),
    ({"status": "success", "cleanup": {"deleted_layers": 1, "deleted_objects": True}}, "unknown"),
])
def test_failed_rhino_follow_up_reports_committed_step_without_retry(completion, reply, state):
    attempts = []

    def native(payload, **options):
        if json.loads(payload)["type"] == "get_rhino_context":
            return completion.native(payload, **options)
        attempts.append(json.loads(payload))
        if reply is None:
            raise TimeoutError("Native acknowledgement never arrived.")
        return json.dumps(reply)

    completion.context._send_and_receive = native
    before = completion.read()
    result = completion.update(status="completed", takeaways="Saved before the follow-up")
    assert result["status"] == "error" and result["cleanup_state"] == state
    assert result["changed"] is True and result["requires_reconciliation"] is True
    after = completion.read()
    assert result["step"]["status"] == after["status"] == "completed"
    assert result["plan"]["revision"] == after["revision"] == before["revision"] + 1
    assert after["step"]["takeaways"] == "Saved before the follow-up"
    assert "delete" not in result["message"].lower() and "next_step_guide" not in result
    assert completion.update(status="completed")["status"] == "no_change"
    assert len(attempts) == 1


def test_native_cleanup_removes_temp_block_instances_and_definition_members(native_cleanup):
    result = native_cleanup("block-member")
    assert result["result"] == {"status": "success", "cleanup": {"deleted_layers": 2, "deleted_objects": 4}}
    assert result["definition_members"] == [202]
    assert result["definition_preserved"] and result["outside_instance_preserved"]
    assert result["temp_instance_deleted"] and result["drawing_preserved"] and result["attachment_preserved"]


def test_native_cleanup_filters_both_owning_definitions_and_keeps_nested_placement(native_cleanup):
    outcome = native_cleanup("block-nested-filter")
    assert outcome["result"] == {"status": "success", "cleanup": {"deleted_layers": 2, "deleted_objects": 5}}
    assert outcome["definition_members"] == [202]
    assert outcome["parent_members"] == [405, 505]
    assert outcome["nested_instance_preserved"]
    assert outcome["outside_instance_preserved"] and outcome["temp_instance_deleted"]


@pytest.mark.parametrize("scenario,state", [
    ("block-attributes", "unknown"),
    ("block-user-dictionary", "unknown"),
    ("block-user-strings", "unknown"),
    ("block-order", "rolled_back"),
    ("block-nested", "unknown"),
])
def test_native_block_cleanup_checks_retained_order_attributes_and_nested_instances(native_cleanup, scenario, state):
    outcome = native_cleanup(scenario)
    result = outcome["result"]
    assert result["status"] == "error" and result["cleanup_state"] == state
    assert result["message"] in outcome["error_log"]
    assert "before rollback" in outcome["error_log"]


def test_native_cleanup_keeps_definition_and_outside_instance_when_all_members_are_temp(native_cleanup):
    outcome = native_cleanup("block-empty")
    assert outcome["result"] == {"status": "success", "cleanup": {"deleted_layers": 2, "deleted_objects": 4}}
    assert outcome["definition_members"] == []
    assert outcome["definition_preserved"] and outcome["outside_instance_preserved"]
    assert outcome["temp_instance_deleted"]


@pytest.mark.parametrize("scenario,state,expected_members", [
    ("block-linked", "not_started", [101, 202]),
    ("block-empty-declined", "rolled_back", [101]),
    ("block-rollback", "rolled_back", [101, 202]),
])
def test_native_block_cleanup_failure_keeps_definition_and_instances(native_cleanup, scenario, state, expected_members):
    result = native_cleanup(scenario)
    assert result["result"]["status"] == "error" and result["result"]["cleanup_state"] == state
    assert result["definition_members"] == expected_members
    assert result["definition_preserved"] and result["outside_instance_preserved"]
    assert result["temp_instance_deleted"] is False
    assert result["layers"] == ["Drawing", "Temp", "tests", "empty", "temp", "temp"]


@pytest.mark.parametrize("scenario,state,objects", [
    ("locked-layer-rollback", "rolled_back", 4),
    ("log-unavailable", "rolled_back", 4),
    ("ref-object", "not_started", 5),
    ("other-document", "not_started", 4),
])
def test_native_cleanup_failure_keeps_the_temp_tree_and_other_data(native_cleanup, scenario, state, objects):
    result = native_cleanup(scenario)
    assert result["result"]["status"] == "error" and result["result"]["cleanup_state"] == state
    assert result["layers"] == ["Drawing", "Temp", "tests", "empty", "temp", "temp"]
    assert result["objects"] == objects
    assert result["current_layer"] == 2
    assert result["drawing_preserved"] and result["attachment_preserved"]
