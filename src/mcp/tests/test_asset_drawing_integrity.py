"""Drawing tools and resources serve only verified package representations."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from fastmcp import Client, FastMCP
from mcp.shared.exceptions import MCPError
import pytest

from almond_mcp.features.assets.tools import register
from almond_mcp.features.assets.asset_repository import AssetRepository, create_server, snapshot
from almond_mcp.features.assets import drafting
from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from test_stage2_asset_paths import small_glb


@pytest.mark.parametrize("change", ["none", "empty_files", "unregistered_view", "changed_file", "outside", "linked", "declared_name"])
def test_drawing_resource_uses_declared_verified_output(tmp_path, change):
    package = tmp_path / "package"
    package.mkdir()
    svg = b"<svg>fixture</svg>"
    filename = "custom.svg" if change == "declared_name" else "plan-1-50.svg"
    (package / filename).write_bytes(svg)
    dxf = b"fixture dxf"
    (package / "plan.dxf").write_bytes(dxf)
    manifest = {
        "source": {"asset_id": "fixture"},
        "representations": [{"view": "plan", "scale": 50, "svg": filename, "dxf": "plan.dxf"}],
        "files": {filename: hashlib.sha256(svg).hexdigest().upper(), "plan.dxf": hashlib.sha256(dxf).hexdigest().upper()},
    }
    if change == "empty_files":
        manifest["files"] = {}
    if change == "unregistered_view":
        manifest["representations"][0]["view"] = "front"
    if change == "changed_file":
        (package / filename).write_bytes(b"<svg>tampered</svg>")
    if change == "outside":
        (tmp_path / filename).write_bytes(svg)
        manifest["representations"][0]["svg"] = f"../{filename}"
        manifest["files"][f"../{filename}"] = manifest["files"].pop(filename)
    if change == "linked":
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / filename).write_bytes(svg)
        link = package / "linked"
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(outside), str(link))
        else:
            link.symlink_to(outside, target_is_directory=True)
        manifest["representations"][0]["svg"] = f"linked/{filename}"
        manifest["files"][f"linked/{filename}"] = manifest["files"].pop(filename)
    (package / "drawing.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"assets": [{"asset_id": "fixture", "package": "package"}]}),
                                          encoding="utf-8")
    mcp = FastMCP("drawing-package")
    register(mcp, SimpleNamespace(DRAWING_LIBRARY_DIR=str(tmp_path), GENERATED_LIBRARY_DIR=str(tmp_path),
        DRAFTING_LIBRARY_DIR=str(tmp_path), drawing_asset_indexer=AssetLibraryIndexer(tmp_path, "drawing_assets", "drawing"),
        generated_asset_indexer=AssetLibraryIndexer(tmp_path, "generated_assets", "generated")))

    async def run():
        async with Client(mcp) as client:
            uri = "almond://assets/fixture/drawing/plan/50"
            if change in {"none", "declared_name"}:
                response = await client.read_resource(uri)
                assert response[0].text == "<svg>fixture</svg>"
            else:
                with pytest.raises(MCPError):
                    await client.read_resource(uri)
            audit = await client.call_tool("asset_01-audit_drawing", {"package_dir": str(package)}, raise_on_error=False)
            expected = "error" if change in {"empty_files", "changed_file", "outside", "linked"} else "success"
            assert json.loads(audit.content[0].text)["status"] == expected

    asyncio.run(run())


def test_archive_cannot_serve_a_drawing_modified_after_indexing(tmp_path):
    roots = {key: tmp_path / key for key in ("generated", "drawing", "drafting")}
    package = roots["drawing"] / "package"
    package.mkdir(parents=True)
    model = roots["drawing"] / "fixture.3dm"
    model.write_bytes(b"fixture source")
    svg = b"<svg>fixture</svg>"
    drawing = package / "plan.svg"
    drawing.write_bytes(svg)
    dxf = b"fixture dxf"
    (package / "plan.dxf").write_bytes(dxf)
    (package / "drawing.json").write_text(json.dumps({
        "source": {"asset_id": "fixture", "source_format": "3dm"},
        "representations": [{"view": "plan", "scale": 50, "svg": "plan.svg", "dxf": "plan.dxf"}],
        "files": {"plan.svg": hashlib.sha256(svg).hexdigest(), "plan.dxf": hashlib.sha256(dxf).hexdigest()},
    }), encoding="utf-8")
    (roots["drawing"] / "manifest.json").write_text(json.dumps({
        "library_id": "drawing_assets",
        "assets": [{"asset_id": "fixture", "file": "fixture.3dm", "drawing_package": "package"}],
    }), encoding="utf-8")
    repo = AssetRepository(roots)
    route = repo.catalogue(verify=False)["assets"][0]["drawing"]["views"][0]["svg"]
    assert snapshot(repo)["files"][route]["sha256"] == hashlib.sha256(svg).hexdigest()
    with create_server(0, repository=repo) as server:
        running = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        running.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}{route}"
            with urlopen(url, timeout=2) as response:
                assert response.read() == svg
            drawing.write_bytes(b"<svg>tampered</svg>")
            with pytest.raises(HTTPError, match="404"):
                urlopen(url, timeout=2)
            assert route not in snapshot(repo)["files"]
        finally:
            server.shutdown()
            running.join(timeout=2)


@pytest.mark.parametrize("canonical", ["available", "missing", "no_package", "no_legacy"])
def test_drawing_lookup_uses_the_selected_package_and_its_own_source(tmp_path, canonical):
    roots = {key: tmp_path / key for key in ("generated", "drawing", "drafting")}
    for root in roots.values():
        root.mkdir()
    legacy = roots["generated"] / "legacy.glb"
    small_glb(legacy)
    pilot = roots["drafting"] / "pilot"
    drafting.create_package(legacy, pilot, asset_id="fixture", name="Legacy", units="mm", scales=[50])
    (roots["drafting"] / "manifest.json").write_text(json.dumps({
        "assets": [{"asset_id": "fixture", "package": "pilot"}],
    }), encoding="utf-8")
    (roots["generated"] / "manifest.json").write_text(json.dumps({
        "library_id": "generated_assets",
        "assets": [] if canonical == "no_legacy" else [{"asset_id": "fixture", "file": "legacy.glb"}],
    }), encoding="utf-8")

    model = roots["drawing"] / "canonical.3dm"
    if canonical not in {"missing", "no_legacy"}:
        model.write_bytes(b"canonical model source")
    canonical_package = roots["drawing"] / "registered"
    svg = b"<svg>Canonical view</svg>"
    dxf = b"0\nEOF\n"
    entry = {"asset_id": "fixture", "file": model.name}
    if canonical != "no_package":
        entry["drawing_package"] = canonical_package.name
        canonical_package.mkdir()
        (canonical_package / "plan.svg").write_bytes(svg)
        (canonical_package / "plan.dxf").write_bytes(dxf)
        (canonical_package / "drawing.json").write_text(json.dumps({
            "source": {"asset_id": "fixture", "source_format": "3dm",
                       "model_sha256": hashlib.sha256(b"canonical model source").hexdigest().upper()},
            "representations": [{"view": "plan", "scale": 50, "svg": "plan.svg", "dxf": "plan.dxf"}],
            "files": {"plan.svg": hashlib.sha256(svg).hexdigest(), "plan.dxf": hashlib.sha256(dxf).hexdigest()},
        }), encoding="utf-8")
    (roots["drawing"] / "manifest.json").write_text(json.dumps({
        "library_id": "drawing_assets", "assets": [entry],
    }), encoding="utf-8")
    mcp = FastMCP("drawing-selection")
    register(mcp, SimpleNamespace(
        DRAWING_LIBRARY_DIR=str(roots["drawing"]), GENERATED_LIBRARY_DIR=str(roots["generated"]),
        DRAFTING_LIBRARY_DIR=str(roots["drafting"]),
        drawing_asset_indexer=AssetLibraryIndexer(roots["drawing"], "drawing_assets", "drawing"),
        generated_asset_indexer=AssetLibraryIndexer(roots["generated"], "generated_assets", "generated"),
    ))
    expected_package = canonical_package if canonical in {"available", "no_legacy"} else pilot
    expected_svg = svg.decode() if canonical == "available" else (pilot / "plan-1-50.svg").read_text(encoding="utf-8")

    async def run():
        async with Client(mcp) as client:
            reply = await client.call_tool("asset_03-get_drawings", {"asset_id": "fixture", "field_groups": ["all"]})
            drawing = json.loads(reply.content[0].text)
            assert Path(drawing["package_dir"]) == expected_package
            if canonical == "no_legacy":
                with pytest.raises(MCPError):
                    await client.read_resource(drawing["plan_svg_uri"])
                audit = await client.call_tool("asset_01-audit_drawing", {"package_dir": drawing["package_dir"]}, raise_on_error=False)
                assert json.loads(audit.content[0].text)["status"] == "error"
                return
            response = await client.read_resource(drawing["plan_svg_uri"])
            assert response[0].text == expected_svg
            audit = await client.call_tool("asset_01-audit_drawing", {"package_dir": drawing["package_dir"]})
            assert json.loads(audit.content[0].text)["source_geometry"] == (
                "source_file_current" if canonical == "available" else "current")

    asyncio.run(run())
