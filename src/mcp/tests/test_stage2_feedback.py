"""Live-review regressions using disposable storage and controlled native replies."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP
from jsonschema import validate

from almond_mcp.features.assets import preparation
from almond_mcp.features.grasshopper.tools import register as grasshopper_tools
from almond_mcp.features.structure import tools as structure_tools
from almond_mcp.managed_paths import drawing_package_path
from almond_mcp.output_contracts import public_output_schema
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.tool_guidance import next_step
from shared_store import ProjectRuntime
from workspace import Workspace


def test_capsule_ports_and_nullable_type_match_the_call_contract(tmp_path):
    store = AlmondStore(tmp_path / "scene.sqlite3")
    ports = [{"name": "ALMOND_IN_length", "type": "number", "units": "mm", "required": True}]
    store.sync_capsules([{"capsule_id": "example", "capability": "generate", "definition_file": "example.ghx",
                          "audited": True, "inputs": ports, "outputs": []}])
    ctx = SimpleNamespace(retrieval_store=store, CAPSULE_LIBRARY_DIR=str(tmp_path))
    tools = grasshopper_tools(FastMCP("capsule-contract"), ctx)
    value = json.loads(tools["list_capsules"](include_ids=True, field_groups=["ports"]))
    assert value["capsules"][0]["structure_type"] is None
    assert value["capsules"][0]["input_ports"] == ports
    validate(value, public_output_schema("list_capsules", wrapped=False))
    rejected = json.loads(tools["run_gh_definition"]("example", {"wrong": 1}))
    assert rejected["valid_inputs"] == ["ALMOND_IN_length"]
    validate(rejected, public_output_schema("run_gh_definition", wrapped=False))
    assert "input_ports" in public_output_schema("run_gh_definition", False)["properties"]["valid_inputs"]["description"]
    assert next_step("list_library", {"logic_names": []}, {}) is None
    assert next_step("visualize_structure", {"status": "cleared"}, {}) is None
    assert "get_logic_by_id" not in value["next_step_guide"]


def test_package_audit_accepts_returned_library_path_but_not_arbitrary_files(tmp_path, monkeypatch):
    project, library, unrelated = (tmp_path / name for name in ("project", "drawing-runs", "unrelated"))
    for folder in (project, library / "package", unrelated):
        folder.mkdir(parents=True)
        (folder / "drawing.json").write_text("{}")
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(project))
    package = library / "package"
    assert drawing_package_path(os.path.relpath(package, project), library_roots=[library]) == package
    assert drawing_package_path(str(package), library_roots=[library]) == package
    with pytest.raises(ValueError):
        drawing_package_path(str(unrelated), library_roots=[library])
    # Source files and outputs still use the strict project-only resolver.
    from almond_mcp.managed_paths import project_path
    with pytest.raises(ValueError):
        project_path(os.path.relpath(package, project), base=project)


def runtime_with_workspace(tmp_path):
    runtime = object.__new__(ProjectRuntime)
    runtime.locations = {"project_dir": str(tmp_path), "session_dir": str(tmp_path / "session"), "call_root": str(tmp_path / "calls")}
    (tmp_path / "session").mkdir()
    runtime.workspace = Workspace(runtime.locations, AlmondStore(tmp_path / "scene.sqlite3"))
    plan = runtime.workspace.store.create_plan(goal="Preparation review")
    runtime.workspace.select(plan["plan_id"], artifact_name="261111_review")
    return runtime, plan


def test_prepare_resolves_current_plan_without_changing_other_path_contracts(tmp_path):
    runtime, plan = runtime_with_workspace(tmp_path)
    args, work, _ = runtime._prepare_arguments("prepare_drawing_asset", {"stage": "inspect", "source_file": "model.3dm"}, tmp_path / "call", "")
    assert Path(work["artifact_dir"]) == runtime.workspace.artifact_path()
    assert not Path(work["artifact_dir"]).exists()
    assert Path(args["source_file"]) == tmp_path / "model.3dm"
    assert not Path(runtime.workspace.current()["artifact_dir"]).is_absolute()
    runtime.workspace.execute_looping(plan["plan_id"])
    _, current, _ = runtime._prepare_arguments("prepare_drawing_asset", {"stage": "inspect"}, tmp_path / "call", "")
    assert current["artifact_dir"].endswith("/01") or current["artifact_dir"].endswith("\\01")


def test_bad_managed_input_is_tool_error_before_operation_or_files(tmp_path):
    runtime, _ = runtime_with_workspace(tmp_path)
    context = SimpleNamespace(message=SimpleNamespace(arguments={"source_glb": "../outside.glb"}))
    async def forbidden(*args):
        raise AssertionError("Rejected input must never dispatch")
    value = asyncio.run(runtime._owned_call(context, forbidden, "audit_asset_drawing", False, ""))
    assert value.is_error and value.structured_content["error_code"] == "invalid_arguments"
    assert not (tmp_path / "session/operation.json").exists()
    assert not (tmp_path / "calls").exists()


def test_inspect_creates_new_owned_folder_status_and_bad_input_do_not(tmp_path, monkeypatch):
    root = tmp_path / "plan/01"
    source = tmp_path / "source.3dm"
    source.write_bytes(b"isolated source; native is controlled")
    calls = []
    monkeypatch.setattr(preparation, "_dispatch", lambda *args: calls.append(args[2]))
    with pytest.raises(ValueError):
        preparation.prepare(stage="status", job_dir=str(root / "absent"), artifact_dir=root)
    assert not root.exists()
    with pytest.raises(ValueError):
        preparation.prepare(stage="inspect", source_file=str(tmp_path / "missing.3dm"), artifact_dir=root)
    assert not root.exists()
    result = preparation.prepare(stage="inspect", source_file=str(source), artifact_dir=root)
    assert calls == ["inspect"] and Path(result["job_dir"]).parent == root
    assert (Path(result["job_dir"]) / "source.3dm").read_bytes() == source.read_bytes()


MODEL = {"status": "ok", "shells": 0, "tolerance_m": 0.001, "max_member_span_m": 2., "max_span_m": 2.,
         "anchor_points": [[0, 0, 0]], "members": [{"source_guids": ["beam"], "points": [[0, 0, 0], [2, 0, 0]],
         "section": {"shape": "solid_rectangle", "width": .3, "height": .5}}]}


class StructureContext:
    def __init__(self, root):
        self.events = []
        self.overlay_number = 0
        self._VIEW_ENGINE = None
        self.retrieval_store = AlmondStore(root / "scene.sqlite3")
        self.construction_library = SimpleNamespace(assess_span=lambda *args: {"warnings": []})
        self.__dict__.update(structure_tools.register(FastMCP("indicative"), self))

    def set_state(self, name, value):
        setattr(self, name, value)

    def _send_and_receive(self, payload, timeout=0):
        request = json.loads(payload)
        self.events.append(request["type"])
        if request["type"] == "structure_model":
            return json.dumps(copy.deepcopy(MODEL))
        if request["type"] == "structure_draw":
            if "result" in request:
                self.overlay_number += 1
            return json.dumps({"status": "indicative", "analysis_method": "native", "nodes": 2,
                               "overlay_id": str(self.overlay_number), "warnings": []})
        raise AssertionError("Successful native analysis must not fall back: " + request["type"])


@pytest.mark.parametrize("engine", ["native", "auto"])
def test_indicative_history_report_and_redraw_preserve_meaning(tmp_path, engine):
    ctx = StructureContext(tmp_path)
    args = dict(engine=engine, material="Concrete", load_kn=1, self_weight=False, stability="off")
    value = json.loads(ctx.validate_structure(["beam"], **args))
    assert value["status"] == "indicative" and value["passed"] is None
    runs = ctx.retrieval_store.list_validation_runs()
    assert len(runs) == 1 and runs[0]["passed"] is None and runs[0]["status"] == "indicative"
    text = ctx._render_validation_report(runs)
    assert "native (INDICATIVE)" in text and "native (FAIL)" not in text
    ctx.events.clear()
    displayed = json.loads(ctx.visualize_structure(["beam"], **args))
    assert displayed["status"] == "indicative" and displayed["passed"] is None and displayed["nodes"] == 2
    assert ctx.events == ["structure_model", "structure_draw"]
    ctx.events.clear()
    redraw = json.loads(ctx.visualize_structure(["beam"], reanalyze=False, **args))
    assert redraw["nodes"] == 2 and redraw["passed"] is None
    assert "overlay_id" not in displayed and "overlay_id" not in redraw
    assert ctx.events == ["structure_draw"]


def test_legacy_validation_rows_survive_nullable_history_migration(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    # Exact old table layout, with NOT NULL passed and no status field.
    ddl = """id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT NOT NULL, structure_type TEXT NOT NULL,
    material TEXT NOT NULL, load_kn REAL NOT NULL, member_count INTEGER NOT NULL, analysis_method TEXT NOT NULL,
    confidence TEXT NOT NULL, passed INTEGER NOT NULL, span_m REAL NOT NULL, max_deflection_mm REAL NOT NULL,
    deflection_limit_mm REAL NOT NULL, utilization_ratio REAL NOT NULL, max_stress_mpa REAL NOT NULL,
    yield_stress_mpa REAL NOT NULL, reactions_kn REAL NOT NULL, verdict TEXT NOT NULL,
    warnings_json TEXT NOT NULL, guids_json TEXT NOT NULL"""
    with sqlite3.connect(database) as db:
        db.execute(f"CREATE TABLE validation_runs ({ddl})")
        for number, passed in ((13, 1), (21, 0)):
            db.execute("INSERT INTO validation_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (number, "2026-11-10", "beam", "Steel", 10, 1, "native", "high", passed,
                        2, .5, 8, .2, 20, 235, 10, "old verdict", '["preserved"]', '["original-guid"]'))
        old = db.execute("SELECT * FROM validation_runs ORDER BY id").fetchall()
    store = AlmondStore(database)
    with store._connect() as db:
        columns = [c["name"] for c in db.execute("PRAGMA table_info(validation_runs)") if c["name"] != "status"]
        assert [tuple(r) for r in db.execute("SELECT " + ",".join(columns) + " FROM validation_runs ORDER BY id")] == old
    new_id = store.record_validation_run({}, {"status": "indicative", "passed": None}, ["new-guid"])
    assert new_id > 21
    rows = AlmondStore(database).list_validation_runs()
    assert [(r["status"], r["passed"]) for r in rows] == [("indicative", None), ("fail", False), ("pass", True)]
