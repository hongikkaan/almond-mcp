"""Public asset call regressions with disposable data and native wire replies.

The ``owned`` cases exercise FastMCP + the operation boundary without requesting
Windows leases. The ``windows`` cases use the complete production middleware;
run those with run_tests.ps1. Neither mode opens Rhino or a user's library.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import struct
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from fastmcp.server.middleware import Middleware
from mcp.shared.exceptions import MCPError
import pytest

from almond_mcp import paths
from almond_mcp.features.assets import preparation
from almond_mcp.features.assets.tools import register as asset_tools
from almond_mcp.features.planning.tools import register as planning_tools
from almond_mcp.retrieval_store import AlmondStore
import mcp_server
from project import connection_paths, write_json
from shared_store import ProjectRuntime, writes_artifacts
from workspace import Workspace


class OwnedCallBoundary(Middleware):
    """Cloud probe boundary: actual ownership, no Windows lease acquisition."""
    def __init__(self, runtime):
        self.runtime = runtime

    async def on_call_tool(self, context, call_next):
        self.runtime.validate()
        return await self.runtime._owned_call(context, call_next, context.message.name,
            writes_artifacts(context.message.name, context.message.arguments or {}), "")


def small_glb(path):
    """A tetrahedron, encoded independently of Almond's GLB reader."""
    vertices = [(0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100)]
    faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
    floats = [coordinate for face in faces for index in face for coordinate in vertices[index]]
    binary = struct.pack("<36f", *floats)
    document = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [{"buffer": 0, "byteLength": len(binary)}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 12, "type": "VEC3"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    encoded = json.dumps(document).encode()
    encoded += b" " * (-len(encoded) % 4)
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 28 + len(encoded) + len(binary))
        + struct.pack("<II", len(encoded), 0x4E4F534A) + encoded
        + struct.pack("<II", len(binary), 0x004E4942) + binary)


@pytest.fixture(params=["owned", "windows"])
def managed_assets(tmp_path, monkeypatch, request):
    project = tmp_path / "project"
    project.mkdir()
    model = project / "source.3dm"
    model.write_bytes(b"Disposable source: native work is simulated at the wire boundary")
    small_glb(project / "source.glb")
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(project))
    monkeypatch.setenv("ALMOND_MODEL_PATH", str(model))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "appdata"))
    token = "d" * 32
    locations = connection_paths(model, "A", token, create=True)
    binding = {"schema": "almond-project", "storage_protocol": 2, "valid": True,
        "token": token, "label": "A", "port": 5501, **locations}
    write_json(locations["ready_path"], binding)
    write_json(Path(locations["session_dir"]) / "worker.json", {"pid": 1, "process_start_ticks": "1"})
    runtime = ProjectRuntime(SimpleNamespace(token=token, session=locations["ready_path"]),
        binding, locations, check_owner=False)
    store = AlmondStore(locations["state_db"])
    runtime.workspace = Workspace(locations, store)
    wire = SimpleNamespace(calls=[], uncertain=False)

    def native_sender(raw, **kwargs):
        envelope = json.loads(raw)
        command = json.loads(envelope["payload"])
        wire.calls.append(command)
        if wire.uncertain:
            raise TimeoutError("Controlled native reply loss")
        assert command["type"] == "execute"
        jobs = list((project / ".almond/produced").rglob("job.json"))
        job_file = next(path for path in jobs if str(path).replace('"', '""') in command["script"])
        record = json.loads(job_file.read_text())
        job = job_file.parent
        output = job / "inspected.3dm"
        output.write_bytes(b"Isolated inspected model receipt")
        (job / "inspect.json").write_text(json.dumps({"schema": preparation.SCHEMA,
            "status": "success", "stage": "inspect", "operation_id": record["operation_id"],
            "source_sha256": record["source_sha256"], "summary": {
                "file": str(output), "sha256": preparation.sha(output), "units": "mm",
                "object_count": 1, "dimensions_mm": {"width": 100, "depth": 100, "height": 100}},
            "previews": []}))
        write_json(Path(locations["session_dir"]) / "native.json", {
            "schema": "almond-native", "token": token, "operation_id": envelope["operation_id"],
            "sequence": len(wire.calls), "pending": 0, "completion_status": "completed", "phase": "ready"})
        return json.dumps({"schema": "almond-native-response", "storage_protocol": 2,
            "token": token, "operation_id": envelope["operation_id"], "request_id": envelope["request_id"],
            "native_sequence": len(wire.calls), "completion_status": "completed",
            "payload": json.dumps({"status": "success"})})

    context = SimpleNamespace(retrieval_store=store, drawing_asset_indexer={}, generated_asset_indexer={},
        DRAWING_LIBRARY_DIR=str(tmp_path / "drawings"), GENERATED_LIBRARY_DIR=str(tmp_path / "generated"),
        DRAFTING_LIBRARY_DIR=str(tmp_path / "drafting"),
        _send_and_receive=lambda *args, **kwargs: runtime.send(native_sender, *args, **kwargs))
    server = FastMCP("asset-path-regressions")
    asset_tools(server, context)
    planning_tools(server, context)
    asyncio.run(mcp_server.configure_project_context(server, runtime.args, binding, locations, runtime=runtime))
    server.add_middleware(runtime if request.param == "windows" else OwnedCallBoundary(runtime))
    return SimpleNamespace(server=server, runtime=runtime, context=context, wire=wire, root=tmp_path, project=project)


async def call(client, name, **arguments):
    response = await client.call_tool(name, arguments, raise_on_error=False)
    return response, json.loads(response.content[0].text)


def test_generate_audit_roundtrip_uses_returned_package_path(managed_assets):
    fixture = managed_assets
    async def run():
        async with Client(fixture.server) as client:
            _, generated = await call(client, "generate_asset_drawing_views", source_glb="source.glb", input_units="mm")
            assert generated["status"] == "success", generated
            _, audited = await call(client, "audit_asset_drawing", package_dir=generated["package_dir"], source_glb="source.glb")
            assert audited["status"] == "success" and audited["source_geometry"] == "current", audited
            assert audited["checked_files"] > 0
            assert fixture.wire.calls == []
            assert not fixture.runtime.completion()["pending"] and not fixture.runtime.completion()["uncertain"]
    asyncio.run(run())


def test_preflight_error_keeps_same_connection_usable_without_creating_operation(managed_assets):
    fixture = managed_assets
    async def run():
        async with Client(fixture.server) as client:
            rejected, error = await call(client, "generate_asset_drawing_views", source_glb="../outside.glb", input_units="mm")
            assert rejected.is_error and error["error_code"] == "invalid_arguments"
            assert fixture.runtime.completion()["uncertain"] is False
            assert not (Path(fixture.runtime.locations["session_dir"]) / "operation.json").exists()
            assert not Path(fixture.runtime.locations["call_root"]).exists()
            _, generated = await call(client, "generate_asset_drawing_views", source_glb="source.glb", input_units="mm")
            assert generated["status"] == "success", generated
            assert fixture.wire.calls == []
    asyncio.run(run())


def test_selected_plan_prepare_and_loop_preserve_public_work_state(managed_assets):
    fixture = managed_assets
    async def run():
        async with Client(fixture.server) as client:
            _, created = await call(client, "create_plan", title="Prepare", goal="Inspect asset", scope="inspection")
            pid = created["plan"]["plan_id"]
            _, selected = await call(client, "set_working_plan", plan_id=pid, artifact_name="261111_assets")
            artifact = fixture.project / selected["artifact_dir"]
            assert not artifact.exists()
            _, before = await call(client, "get_phase_plan_step", plan_id=pid, include_details=True)
            _, missing = await call(client, "prepare_drawing_asset", stage="status", job_dir=selected["artifact_dir"] + "/missing")
            assert missing["status"] == "error" and not artifact.exists()
            _, inspected = await call(client, "prepare_drawing_asset", stage="inspect", source_file="source.3dm")
            assert inspected.get("state") == "inspected", inspected
            assert not Path(inspected["job_dir"]).is_absolute()
            assert (fixture.project / inspected["job_dir"]).parent == artifact
            _, reread = await call(client, "prepare_drawing_asset", stage="status", job_dir=inspected["job_dir"])
            assert reread["state"] == "inspected" and len(fixture.wire.calls) == 1
            _, after = await call(client, "get_phase_plan_step", plan_id=pid, include_details=True)
            assert before == after
            _, reselected = await call(client, "set_working_plan", plan_id=pid)
            assert reselected == selected
            assert fixture.wire.calls[0]["artifact_dir"] == selected["artifact_dir"]
            _, loop = await call(client, "execute_looping", plan_id=pid)
            assert loop["loop_no"] == 1 and loop["artifact_dir"].endswith("/01")
            _, second = await call(client, "prepare_drawing_asset", stage="inspect", source_file="source.3dm")
            assert second["state"] == "inspected", second
            assert (fixture.project / second["job_dir"]).parent == fixture.project / loop["artifact_dir"]
            assert len(fixture.wire.calls) == 2
            assert fixture.wire.calls[1]["artifact_dir"] == loop["artifact_dir"]
            assert not fixture.runtime.completion()["uncertain"]
    asyncio.run(run())


def test_returned_package_path_survives_cross_volume_relpath_failure(managed_assets, monkeypatch):
    fixture = managed_assets
    relative = os.path.relpath
    generated_root = paths.user_data_dir() / "drawing-runs"
    def cross_volume(path, start=None):
        if Path(path).is_relative_to(generated_root):
            raise ValueError("path is on another Windows drive")
        return relative(path, start)
    # Simulate the OS's cross-volume relpath result, not the resolver or tools.
    monkeypatch.setattr(os.path, "relpath", cross_volume)
    async def run():
        async with Client(fixture.server) as client:
            _, generated = await call(client, "generate_asset_drawing_views", source_glb="source.glb", input_units="mm")
            assert Path(generated["package_dir"]).is_absolute(), generated
            _, audited = await call(client, "audit_asset_drawing", package_dir=generated["package_dir"])
            assert audited["status"] == "success", audited
    asyncio.run(run())


@pytest.mark.parametrize("kind", ["outside", "directory_link", "manifest_link"])
def test_audit_rejects_paths_outside_configured_libraries(managed_assets, kind):
    fixture = managed_assets
    outside = fixture.root / "private"
    outside.mkdir()
    (outside / "drawing.json").write_text(json.dumps({"source": {"asset_id": "private-asset"}, "files": {}}))
    library = Path(fixture.context.DRAWING_LIBRARY_DIR)
    library.mkdir()
    candidate = outside
    if kind == "directory_link":
        candidate = library / "linked"
        candidate.symlink_to(outside, target_is_directory=True)
    elif kind == "manifest_link":
        candidate = library / "linked-manifest"
        candidate.mkdir()
        (candidate / "drawing.json").symlink_to(outside / "drawing.json")
    async def run():
        async with Client(fixture.server) as client:
            _, result = await call(client, "audit_asset_drawing", package_dir=str(candidate))
            assert result["status"] == "error" and "private-asset" not in json.dumps(result), result
            _, valid = await call(client, "generate_asset_drawing_views", source_glb="source.glb", input_units="mm")
            assert valid["status"] == "success", valid
    asyncio.run(run())


def test_project_manifest_link_is_rejected_before_read(managed_assets):
    fixture = managed_assets
    package = fixture.project / "linked-package"
    package.mkdir()
    foreign = fixture.root / "private-drawing.json"
    foreign.write_text(json.dumps({"source": {"asset_id": "must-not-be-returned"}, "files": {}}))
    (package / "drawing.json").symlink_to(foreign)
    async def run():
        async with Client(fixture.server) as client:
            _, result = await call(client, "audit_asset_drawing", package_dir="linked-package")
            assert result["status"] == "error" and "must-not-be-returned" not in json.dumps(result), result
    asyncio.run(run())


@pytest.mark.parametrize("cross_volume", [False, True])
def test_get_drawing_result_is_auditable_in_separate_drafting_library(managed_assets, monkeypatch, cross_volume):
    fixture = managed_assets
    root = Path(fixture.context.DRAFTING_LIBRARY_DIR)
    package = root / "fixture"
    package.mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps({"assets": [{"asset_id": "fixture", "package": "fixture"}]}))
    drawing_bytes = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L1 1"/></svg>'
    (package / "plan.svg").write_bytes(drawing_bytes)
    metadata = {"path": str(package / "plan.svg"), "package_dir": str(package)}
    (package / "drawing.json").write_text(json.dumps({"source": {"asset_id": "fixture"},
        "files": {"plan.svg": hashlib.sha256(drawing_bytes).hexdigest().upper()}, "metadata": metadata}))
    if cross_volume:
        relative = os.path.relpath
        def different_drive(path, start=None):
            if Path(path).is_relative_to(root):
                raise ValueError("path is on another Windows drive")
            return relative(path, start)
        monkeypatch.setattr(os.path, "relpath", different_drive)
    async def run():
        async with Client(fixture.server) as client:
            _, drawing = await call(client, "get_asset_drawing", asset_id="fixture", field_groups=["all"])
            _, result = await call(client, "audit_asset_drawing", package_dir=drawing["package_dir"])
            assert result["status"] == "success" and result["checked_files"] == 1, result
            if cross_volume:
                assert drawing["package_dir"] == str(package)
                unavailable = "[unavailable: a relative path between different drives does not exist]"
                assert drawing["manifest"]["metadata"] == {"path": unavailable, "package_dir": unavailable}
    asyncio.run(run())


def test_unconfirmed_native_work_still_fences_followup(managed_assets):
    fixture = managed_assets
    fixture.wire.uncertain = True
    async def run():
        async with Client(fixture.server) as client:
            _, created = await call(client, "create_plan", title="Prepare", goal="Inspect asset", scope="inspection")
            await call(client, "set_working_plan", plan_id=created["plan"]["plan_id"], artifact_name="261111_uncertain")
            _, result = await call(client, "prepare_drawing_asset", stage="inspect", source_file="source.3dm")
            assert result["state"] == "unconfirmed" and result["requires_reconciliation"] is True
            assert fixture.runtime.completion()["uncertain"] is True
            assert (Path(fixture.runtime.locations["session_dir"]) / "artifact-write.json").exists()
            with pytest.raises(MCPError, match="Internal server error"):
                await call(client, "generate_asset_drawing_views", source_glb="source.glb", input_units="mm")
            assert not (paths.user_data_dir() / "drawing-runs").exists()
            assert len(fixture.wire.calls) == 1
    asyncio.run(run())
