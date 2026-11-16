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

    def native(payload, timeout=60):
        request = json.loads(payload)
        bridge_requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"step_temp_cleanup": 1}})
        assert request == {"type": "cleanup_step_temp", "expected_model_path": model_path}
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
                           context=context, plan=plan, native=native)


def test_completion_request_returns_agent_choice_before_any_change(completion):
    before = completion.read()
    result = completion.update(status="completed", takeaways="Record the entrance decision")
    assert result["status"] == "confirmation_required"
    assert result["changed"] is False
    assert result["confirmation"]["choices"] == ["yes", "no"]
    warning = result["confirmation"]["warning"]
    assert "temp가 아닌 다른 레이어" in warning
    assert "모든 하위 레이어" in warning
    assert "객체 전체가 삭제" in warning
    assert result["confirmation"]["token"]
    assert completion.bridge_requests == []
    assert completion.read() == before



def test_no_consumes_attempt_without_edit_then_new_attempt_can_complete(completion):
    before = completion.read()
    fields = {"status": "completed", "takeaways": "Record the entrance decision"}
    first = completion.update(**fields)["confirmation"]["token"]
    refused = completion.update(**fields, completion_token=first, completion_decision="no")
    assert refused["status"] == "cancelled" and refused["changed"] is False
    replay = completion.update(**fields, completion_token=first, completion_decision="yes")
    assert replay["status"] == "error"
    assert completion.bridge_requests == []
    assert completion.read() == before

    second = completion.update(**fields)["confirmation"]["token"]
    assert second != first
    accepted = completion.update(**fields, completion_token=second, completion_decision="yes")
    assert accepted["status"] == "success" and accepted["changed"] is True
    assert accepted["cleanup"] == {"deleted_layers": 3, "deleted_objects": 2}
    assert [request["type"] for request in completion.bridge_requests] == [
        "get_rhino_context", "cleanup_step_temp"]
    after = completion.read()
    assert after["status"] == "completed"
    assert after["revision"] == before["revision"] + 1
    assert after["step"]["takeaways"] == fields["takeaways"]



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


def confirm(completion, **fields):
    request = {"status": "completed", **fields}
    token = completion.update(**request)["confirmation"]["token"]
    return completion.update(**request, completion_token=token, completion_decision="yes")


def test_cleanup_accepts_objects_removed_from_the_temp_root_only(completion):
    def native(payload, timeout=60):
        if json.loads(payload)["type"] == "get_rhino_context":
            return completion.native(payload)
        return json.dumps({"status": "success", "cleanup": {"deleted_layers": 0, "deleted_objects": 1}})

    completion.context._send_and_receive = native
    result = confirm(completion)
    assert result["status"] == "success"
    assert result["cleanup"] == {"deleted_layers": 0, "deleted_objects": 1}


def test_only_actual_transition_cleans_again_and_keeps_file_registration_separate(completion, tmp_path):
    artifact = tmp_path / "handoff.3dm"
    artifact.write_bytes(b"preserve this file")
    before_files = completion.context.retrieval_store.list_project_files()
    assert completion.update(status="running")["status"] == "success"
    assert completion.bridge_requests == []
    assert confirm(completion, output_refs={"add": [str(artifact)]})["status"] == "success"
    already_completed = completion.update(status="completed", takeaways="Revised notes")
    assert already_completed["status"] == "success" and "cleanup" not in already_completed
    assert len(completion.bridge_requests) == 2
    assert completion.update(status="running")["status"] == "success"
    assert confirm(completion)["status"] == "success"
    assert len(completion.bridge_requests) == 4
    assert completion.context.retrieval_store.list_project_files() == before_files
    assert artifact.read_bytes() == b"preserve this file"


@pytest.mark.parametrize("change", ["revision", "loop"])
def test_confirmation_is_bound_to_issued_loop_and_revision(completion, change):
    token = completion.update(status="completed")["confirmation"]["token"]
    store = completion.context.retrieval_store
    if change == "revision":
        store.edit_plan(completion.plan["plan_id"], title="Updated")
    else:
        store.execute_looping(completion.plan["plan_id"])
    before = completion.read()
    result = completion.update(status="completed", completion_token=token, completion_decision="yes")
    assert result["status"] == "error" and result["cleanup_state"] == "not_started"
    assert completion.bridge_requests == []
    assert completion.read() == before
    assert result["plan"]["loop_no"] == before["loop_no"]
    assert result["step"]["status"] == before["status"]


def test_confirmation_cannot_cross_to_another_bound_document(completion, monkeypatch, tmp_path):
    token = completion.update(status="completed")["confirmation"]["token"]
    before = completion.read()
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(tmp_path / "other.3dm"))
    result = completion.update(status="completed", completion_token=token, completion_decision="yes")
    assert result["status"] == "error" and result["cleanup_state"] == "not_started"
    assert completion.bridge_requests == []
    assert completion.read() == before


def test_wrong_request_is_rejected_without_consuming_the_matching_attempt(completion):
    token = completion.update(status="completed", takeaways="original")["confirmation"]["token"]
    mismatch = completion.update(status="completed", takeaways="changed", completion_token=token, completion_decision="yes")
    assert mismatch["error_code"] == "invalid_step_completion_confirmation"
    assert completion.bridge_requests == []
    assert completion.update(status="completed", takeaways="original", completion_token=token, completion_decision="yes")["status"] == "success"


@pytest.mark.parametrize("reply, expected", [
    ({"status": "error", "cleanup_state": "rolled_back", "message": "Layer could not be deleted."}, "rolled_back"),
    (None, "unknown"),
    ({"status": "success", "cleanup": {"deleted_layers": 1, "deleted_objects": True}}, "unknown"),
])
def test_failed_native_cleanup_reports_the_committed_step_and_does_not_retry(completion, reply, expected):
    attempts = []

    def fail_native(payload, timeout=60):
        if json.loads(payload)["type"] == "get_rhino_context":
            return completion.native(payload, timeout)
        attempts.append(payload)
        if reply is None:
            raise TimeoutError("The cleanup acknowledgement was not received.")
        return json.dumps(reply)

    completion.context._send_and_receive = fail_native
    before = completion.read()
    result = confirm(completion, takeaways="The Step is completed")
    assert result["status"] == "error" and result["cleanup_state"] == expected
    assert result["changed"] is True and result["requires_reconciliation"] is True
    observed = completion.read()
    assert result["step"]["status"] == observed["status"] == "completed"
    assert result["plan"]["revision"] == observed["revision"] == before["revision"] + 1
    assert observed["step"]["takeaways"] == "The Step is completed"
    assert completion.update(status="completed")["status"] == "success"
    assert len(attempts) == 1


def test_yes_persists_the_step_before_dispatching_native_cleanup(completion):
    store = completion.context.retrieval_store
    before = completion.read()
    observed = []

    def observe_when_cleaning(payload, timeout=60):
        if json.loads(payload)["type"] == "cleanup_step_temp":
            saved = store.get_step(before["plan_id"], before["id"])
            observed.append((saved["step"]["status"], saved["revision"], saved["step"]["takeaways"]))
        return completion.native(payload, timeout)

    completion.context._send_and_receive = observe_when_cleaning
    assert confirm(completion, takeaways="Committed before cleanup")["status"] == "success"
    assert observed == [("completed", before["revision"] + 1, "Committed before cleanup")]


@pytest.mark.parametrize("stage", ["write", "commit"])
def test_failed_db_update_never_dispatches_cleanup(completion, stage):
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
    result = confirm(completion, takeaways="No partial update")
    assert result["status"] == "error" and result["error_code"] == "step_completion_db_failed"
    assert result["requires_reconciliation"] is False
    assert result["cleanup_state"] == "not_started"
    assert completion.bridge_requests == []
    assert result["step"]["status"] == before["status"]
    assert completion.read() == before


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
