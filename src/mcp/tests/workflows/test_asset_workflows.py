import asyncio
import hashlib
import json
import os
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP
from mcp.shared.exceptions import MCPError

from almond_mcp import paths
from almond_mcp.features.assets.preparation import SCHEMA, sha
from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from almond_mcp.features.assets.tools import register
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.startup import create_server


def manifest(root, library, *assets):
    root.mkdir(exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({"library_id": library, "assets": assets}), encoding="utf-8")


def drawing_package(library, package, filename, contents):
    dxf = b"drawing fixture"
    (package / "plan.dxf").write_bytes(dxf)
    description = {
        "source": {"asset_id": "chair"},
        "representations": [{"view": "plan", "scale": 50, "svg": filename, "dxf": "plan.dxf"}],
        "files": {filename: hashlib.sha256(contents).hexdigest(), "plan.dxf": hashlib.sha256(dxf).hexdigest()},
    }
    (package / "drawing.json").write_text(json.dumps(description), encoding="utf-8")
    manifest(library, "drawing_assets", {"asset_id": "chair", "package": package.name})
    server = FastMCP("Drawing package workflow")
    register(server, SimpleNamespace(
        DRAWING_LIBRARY_DIR=str(library), GENERATED_LIBRARY_DIR=str(library), DRAFTING_LIBRARY_DIR=str(library),
        drawing_asset_indexer=AssetLibraryIndexer(library, "drawing_assets", "drawing"),
        generated_asset_indexer=AssetLibraryIndexer(library, "generated_assets", "generated"),
    ))
    return server


def read_drawing(server):
    async def read():
        async with Client(server) as client:
            result = await client.read_resource("almond://assets/chair/drawing/plan/50")
            return result[0].text

    return asyncio.run(read())


def test_drawing_hash_rechecked(tmp_path, call_tool):
    package = tmp_path / "chair"
    package.mkdir()
    filename = "architect-plan.svg"
    source = package / filename
    original = b"<svg>plan A</svg>"
    source.write_bytes(original)
    server = drawing_package(tmp_path, package, filename, original)

    assert read_drawing(server).encode() == original
    _, drawing = call_tool(server, "asset_03-get_drawings", asset_id="chair")
    assert drawing["package_dir"] == str(package)
    assert drawing["manifest"]["source"]["asset_id"] == "chair"
    assert call_tool(server, "asset_01-audit_drawing", package_dir=str(package))[1]["status"] == "success"

    timestamps = source.stat()
    source.write_bytes(b"<svg>plan B</svg>")
    os.utime(source, ns=(timestamps.st_atime_ns, timestamps.st_mtime_ns))

    with pytest.raises(MCPError):
        read_drawing(server)
    assert call_tool(server, "asset_01-audit_drawing", package_dir=str(package))[1]["status"] == "error"


def test_linked_drawing_rejected(tmp_path, call_tool):
    library = tmp_path / "library"
    package = library / "chair"
    package.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "private.svg"
    contents = b"<svg>private drawing sentinel</svg>"
    sentinel.write_bytes(contents)
    link = package / "linked"
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)

    try:
        server = drawing_package(library, package, "linked/private.svg", contents)
        with pytest.raises(MCPError, match="[Ll]inked|[Oo]utside") as response:
            read_drawing(server)
        assert contents.decode() not in str(response.value)
        _, audit = call_tool(server, "asset_01-audit_drawing", package_dir=str(package))
        assert audit["status"] == "error" and contents.decode() not in json.dumps(audit)
        assert sentinel.read_bytes() == contents
    finally:
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()


@pytest.mark.parametrize("failure", ["prior-owner", "malformed-manifest"])
def test_catalogue_sync_is_atomic(tmp_path, failure):
    roots = {variable: tmp_path / name for variable, name in paths.LIBRARY_DIRS.items()}
    database = tmp_path / "project.sqlite3"
    store = AlmondStore(database)
    dimensions = {"width": 100, "depth": 100, "height": 100}
    diagram = {"asset_id": "survey-symbol", "product": "Survey symbol", "file": "marker.svg",
               "dimensions_mm": dimensions}
    other = {"asset_id": "shared", "product": "Earlier project index", "file": "shared.3dm",
             "dimensions_mm": dimensions}
    store.sync_assets([diagram], library_id="diagram_assets")
    store.sync_assets([other], library_id="project_fixture")
    manifest(roots["RHINO_MCP_DIAGRAM_ASSET_DIR"], "diagram_assets", {**diagram, "product": "Replacement"})

    generated = roots["RHINO_MCP_GENERATED_ASSET_DIR"]
    if failure == "prior-owner":
        manifest(generated, "generated_assets", other)
        expected = "shared.*project_fixture.*generated_assets"
    else:
        generated.mkdir()
        (generated / "manifest.json").write_text('{"library_id":"generated_assets","assets":{}}', encoding="utf-8")
        expected = "Invalid assets list"

    def unexpected_bridge(*_args, **_kwargs):
        pytest.fail("Indexing must not contact Rhino")

    with pytest.raises(ValueError, match=expected):
        create_server(state_db=database, library_dirs={key: str(path) for key, path in roots.items()}, send=unexpected_bridge)

    reopened = AlmondStore(database)
    assert reopened.get_asset("survey-symbol", library_id="diagram_assets")["product"] == "Survey symbol"
    assert reopened.get_asset("shared", library_id="project_fixture")["product"] == "Earlier project index"
    assert reopened.get_asset("shared", library_id="generated_assets") is None


def test_library_results_are_reusable(tmp_path, monkeypatch, call_tool):
    roots = {variable: tmp_path / name for variable, name in paths.LIBRARY_DIRS.items()}
    assets = [{"asset_id": asset_id, "product": asset_id, "file": f"{asset_id}.svg",
               "dimensions_mm": {"width": 100, "depth": 10, "height": 100}}
              for asset_id in ("chair-a", "chair-b")]
    manifest(roots["RHINO_MCP_DRAWING_ASSET_DIR"], "drawing_assets", *assets)
    manifest(roots["RHINO_MCP_DIAGRAM_ASSET_DIR"], "diagram_assets",
             {**assets[0], "asset_id": "diagram-a"})
    logic_dir = roots["RHINO_MCP_LIBRARY_DIR"]
    logic_dir.mkdir()
    metadata = {"logic_id": "design", "created_at": "authored date", "file": r"Z:\library\design.gh"}
    (logic_dir / "design.json").write_text(json.dumps(metadata), encoding="utf-8")

    def unexpected_bridge(*_args, **_kwargs):
        pytest.fail("Library queries must not contact Rhino")

    server = create_server(state_db=tmp_path / "project.sqlite3", library_dirs=roots, send=unexpected_bridge).mcp
    with monkeypatch.context() as bound:
        bound.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
        _, logic = call_tool(server, "grasshopper_01-get_logic", logic_id="design")
    assert logic["metadata"] == metadata

    _, page = call_tool(server, "asset_05-list", limit=1)
    assert page["assets"][0]["asset_id"] == "chair-a"
    _, next_page = call_tool(server, "asset_05-list", limit=1, offset=page["next_offset"])
    assert next_page["assets"][0]["asset_id"] == "chair-b"
    assert next_page["next_offset"] is None

    _, repository = call_tool(server, "asset_10-search_repository", query="chair-a")
    assert repository["assets"][0]["asset_id"] == "chair-a"
    _, result = call_tool(server, "diagram_04-search", field_groups=["dimensions"])
    diagram, = result["assets"]
    assert diagram["asset_id"] == "diagram-a"
    assert diagram["dimensions_mm"] == {"width": 100, "depth": 10, "height": 100}
    assert diagram["file_available"] is False
    _, details = call_tool(server, "diagram_01-get", asset_id=diagram["asset_id"], field_groups=["paths"])
    assert details["asset"]["file"] == "chair-a.svg"


def test_source_only_asset_returns_conversion_tool(tmp_path, call_tool):
    roots = {variable: tmp_path / name for variable, name in paths.LIBRARY_DIRS.items()}
    drawing = roots["RHINO_MCP_DRAWING_ASSET_DIR"]
    manifest(drawing, "drawing_assets", {"asset_id": "legacy-chair", "product": "Legacy chair", "file": "chair.obj"})
    (drawing / "chair.obj").write_bytes(b"source fixture")

    def unexpected_bridge(*_args, **_kwargs):
        pytest.fail("A source-only asset cannot be placed")

    server = create_server(state_db=tmp_path / "project.sqlite3", library_dirs=roots, send=unexpected_bridge).mcp
    _, found = call_tool(server, "asset_04-get", asset_id="legacy-chair")
    _, rejected = call_tool(server, "asset_06-place", asset_id="legacy-chair")
    assert found["asset"]["next_tool"] == rejected["next_tool"] == "asset_07-prepare"
    assert rejected["mutation_state"] == "not_started"


def test_preparation_status_returns_next_stage(tmp_path, call_tool, monkeypatch):
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", str(tmp_path))
    job = tmp_path / "preparation"
    job.mkdir()
    output = job / "inspected.3dm"
    script = job / "inspect.cs"
    report = job / "inspect.json"
    output.write_bytes(b"inspected fixture")
    script.write_bytes(b"script fixture")
    report.write_text(json.dumps({"schema": SCHEMA, "status": "passed", "stage": "inspect", "operation_id": "fixture",
                                  "source_sha256": "source-hash", "summary": {"file": str(output), "sha256": sha(output)}}), encoding="utf-8")
    record = {"schema": SCHEMA, "job_dir": str(job), "source_sha256": "source-hash", "state": "inspected",
              "stages": {"inspect": {"operation_id": "fixture", "output_sha256": sha(output),
                                     "report_sha256": sha(report), "script_sha256": sha(script)}}}
    record_path = job / "job.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    server = FastMCP("Preparation status workflow")
    register(server, SimpleNamespace(_send_and_receive=lambda *_args, **_kwargs: pytest.fail("Status cannot rerun Rhino")))

    _, inspected = call_tool(server, "asset_07-prepare", stage="status", job_dir=str(job))
    assert inspected["state"] == "inspected" and inspected["next_stage"] == "verify"
    assert inspected["review_targets"]["inspected_sha256"] == sha(output)

    record["state"] = "running"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    _, pending = call_tool(server, "asset_07-prepare", stage="status", job_dir=str(job))
    assert pending["next_stage"] is None and pending["requires_reconciliation"] is True


@pytest.mark.parametrize(("receipt", "state", "cause", "unconfirmed"), [
    ({"status": "error", "message": "Rhino importer rejected the source file " + "detail " * 500,
      "error_trace": "internal stack trace sentinel"}, "failed", "Rhino importer rejected the source file", False),
    ({"status": "error", "message": "Native result capture failed", "result_error": "Native receipt could not be captured",
      "mutation_state": "unknown"}, "unconfirmed", "Native receipt could not be captured", True),
])
def test_preparation_status_reports_saved_failure(tmp_path, call_tool, monkeypatch, receipt, state, cause, unconfirmed):
    monkeypatch.setenv("ALMOND_ARTIFACT_DIR", str(tmp_path))
    source = tmp_path / "source.3dm"
    source.write_bytes(b"source fixture")
    calls = []

    def bridge(raw, **_options):
        assert json.loads(raw)["type"] == "execute"
        calls.append(raw)
        return json.dumps(receipt)

    server = FastMCP("Preparation failure workflow")
    register(server, SimpleNamespace(_send_and_receive=bridge))
    _, failed = call_tool(server, "asset_07-prepare", stage="inspect", source_file=str(source))
    _, replay = call_tool(server, "asset_07-prepare", stage="status", job_dir=failed["job_dir"])
    assert failed == replay
    assert replay["status"] == "error" and replay["state"] == state
    assert replay["requires_reconciliation"] is unconfirmed and replay["next_stage"] is None
    assert cause in replay["message"] and "job.json" in replay["message"] and "job_dir" in replay["message"]
    assert "internal stack trace sentinel" not in replay["message"] and len(replay["message"]) < 1000
    assert "execution" not in replay

    _, retry = call_tool(server, "asset_07-prepare", stage="verify", job_dir=failed["job_dir"])
    assert retry["status"] == "error" and len(calls) == 1
