import asyncio
import hashlib
import json
import os
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP
from mcp.shared.exceptions import MCPError

from almond_mcp import paths
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
