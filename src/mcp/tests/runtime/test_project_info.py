"""Project discovery against an isolated store and a controlled live observer."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

import mcp_server
from almond_mcp.retrieval_store import AlmondStore
from project import connection_paths
from workspace import Workspace


@pytest.fixture
def context(tmp_path, monkeypatch):
    model = tmp_path / "model.3dm"
    model.touch()
    locations = connection_paths(model, "A", "a" * 32, create=True)
    binding = {"label": "A", "port": 5501}
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(mcp_server, "read_binding", lambda *_: (binding, locations))
    monkeypatch.setattr(mcp_server, "verify_process", lambda _: None)
    store = AlmondStore(locations["state_db"])
    workspace = Workspace(locations, store)
    runtime = SimpleNamespace(workspace=workspace, rhinocode_availability=lambda: {
        "available": True, "pipe_id": "rhino-pipe", "languages": ["python"]})
    live = {"status": "success", "document": {
        "name": model.name, "path": str(model), "runtime_serial_number": 41,
        "units": "Millimeters", "absolute_tolerance": 0.01,
        "angle_tolerance_radians": 0.017, "modified": False,
        "object_count": 5, "layer_count": 3}}
    calls = []

    def send(raw):
        calls.append(json.loads(raw))
        return json.dumps(live)

    server = FastMCP("project-info-test")
    args = SimpleNamespace(session="unused", token="a" * 32)
    asyncio.run(mcp_server.configure_project_context(server, args, binding, locations,
                                                     sender=send, runtime=runtime))

    def call(**arguments):
        async def invoke():
            async with Client(server) as client:
                return await client.call_tool("project_info", arguments, raise_on_error=False)
        return asyncio.run(invoke())

    return SimpleNamespace(call=call, live=live, calls=calls, store=store,
                           workspace=workspace, root=tmp_path, binding=binding)


def value(result):
    assert not result.is_error
    return json.loads(result.content[0].text)


def test_first_query_checks_live_once_and_separates_identity_properties_and_locations(context):
    result = value(context.call())
    assert set(result) == {"status", "project", "document", "locations", "next_step_guide"}
    assert result["next_step_guide"].splitlines() == [
        "- list_plans으로 프로젝트 진행상황 파악합니다.",
        "- 산출물 작업 공간은 set_working_plan으로 선택합니다.",
        "- 객체 상태가 필요하면 get_objects로 확인합니다.",
    ]
    project = result["project"]
    assert project["project_root"] == str(context.root)
    assert project["file_name"] == "model.3dm"
    assert project["file_path"] == "model.3dm"
    assert project["is_bound_document"] is True
    assert "connection_status" not in project and "live_document_checked" not in project
    assert "database" not in project and "root_variable" not in project and "root_variable_set" not in project
    assert result["document"] == {"units": "Millimeters", "absolute_tolerance": 0.01,
        "angle_tolerance_radians": 0.017, "modified": False, "object_count": 5, "layer_count": 3}
    assert result["locations"]["database"] == ".almond/scene.sqlite3"
    assert result["locations"]["artifact_dir"] is None
    assert context.calls == [{"type": "get_rhino_context", "sections": ["document"], "selection_limit": 0}]
    assert context.live["document"]["name"] == "model.3dm"


def test_files_pagination_preserves_duplicates_and_opt_in_references(context):
    with context.store._connect() as db:
        for folder in ("first", "second", "third"):
            context.store._project_file_reference(db, model_path=str(context.root / folder / "same.3dm"))
    first = value(context.call(sections=["project"], files_limit=2))["project"]
    assert first["files"] == [{"file_name": "same.3dm"}] * 2
    assert first["files_page"] == {"total": 3, "limit": 2, "offset": 0, "truncated": True}
    selected = value(context.call(sections=["project"], files_limit=2, include_ids=True))["project"]
    last = value(context.call(sections=["project"], files_limit=2, files_offset=2, include_ids=True))["project"]
    assert len({row["project_file_id"] for row in selected["files"] + last["files"]}) == 3
    assert last["files_page"] == {"total": 3, "limit": 2, "offset": 2, "truncated": False}
    empty = value(context.call(sections=["project"], files_offset=3))["project"]
    assert empty["files"] == [] and not empty["files_page"]["truncated"]


@pytest.mark.parametrize("path", ["other.3dm", ""])
def test_successful_observation_of_different_or_unsaved_document_is_not_bound(context, path):
    context.live["document"].update(path=str(context.root / path) if path else "", name="Other")
    project = value(context.call(sections=["project"]))["project"]
    assert project["is_bound_document"] is False
    assert project["file_name"] == "Other"
    assert project["file_path"] == path


@pytest.mark.parametrize("document", [None, {}, {"path": None}, {"path": 42}])
def test_incomplete_identity_is_error_without_a_bound_document_flag(context, document):
    context.live["document"] = document
    context.live["warnings"] = ["document.path: unavailable"]
    result = value(context.call(sections=["project"]))
    assert result["status"] == "error"
    assert result["warnings"] == context.live["warnings"]
    assert "project" not in result and "is_bound_document" not in result
    assert "live_document_checked" not in result


def test_native_failure_keeps_error_evidence_without_normal_project_output(context):
    error = {"status": "error", "error_code": "document_mismatch", "message": "Document changed.",
             "request_id": "native-request", "details": {"observed": "other.3dm"}}
    context.live.clear()
    context.live.update(error)
    assert value(context.call(sections=["project"])) == error


def test_ids_are_opt_in_for_document_runtime_and_selected_plan(context):
    plan = context.store.create_plan(goal="Review")
    selection = context.workspace.select(plan["plan_id"], artifact_name="review")
    for include_ids in (False, True):
        result = value(context.call(sections=["document", "runtime", "locations"], include_ids=include_ids))
        assert ("runtime_serial_number" in result["document"]) is include_ids
        assert ("pipe_id" in result["runtime"]["rhinocode"]) is include_ids
        assert ("plan_id" in result["locations"]) is include_ids
        assert result["locations"]["artifact_dir"] == selection["artifact_dir"]
        assert "path" not in result["document"] and "name" not in result["document"]


def test_workspace_selection_returns_revision_after_first_folder_setup(context):
    plan = context.store.create_plan(goal="Review entrance", scope="component")
    selected = context.workspace.select(plan["plan_id"], plan["steps"][1]["step_id"], artifact_name="review")
    assert selected["revision"] == plan["revision"] + 1
    assert context.store.get_step(plan["plan_id"], plan["steps"][1]["step_id"])["step"]["status"] == "pending"
    assert not (context.root / selected["artifact_dir"]).exists()
    assert context.workspace.select(plan["plan_id"], plan["steps"][1]["step_id"]) == selected
    with pytest.raises(ValueError):
        context.store.update_plan_step(plan["plan_id"], plan["steps"][1]["step_id"], output_refs=["review"],
                                       expected_revision=plan["revision"])
    updated = context.store.update_plan_step(plan["plan_id"], plan["steps"][1]["step_id"], output_refs=["review"],
                                            expected_revision=selected["revision"])
    assert updated["revision"] == selected["revision"] + 1


def test_locations_and_runtime_only_do_not_observe_rhino(context):
    result = value(context.call(sections=["locations", "runtime"]))
    assert context.calls == []
    assert "project" not in result and "document" not in result


@pytest.mark.parametrize("arguments", [
    {"sections": ["instructions"]}, {"sections": ["artifacts"]},
    {"files_limit": 0}, {"files_limit": 501}, {"files_offset": -1},
    {"files_limit": True}, {"files_offset": "1"}, {"include_ids": "false"},
])
def test_invalid_arguments_fail_before_observation(context, arguments):
    assert context.call(**arguments).is_error
    assert context.calls == []


def test_changed_binding_fails_before_observation(context, monkeypatch):
    monkeypatch.setattr(mcp_server, "read_binding", lambda *_: ({"label": "B"}, {}))
    assert context.call(sections=["project"]).is_error
    assert context.calls == []
