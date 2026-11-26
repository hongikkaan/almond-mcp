"""Check native archive consumption independently of Rhino."""
import asyncio
from hashlib import sha256
from http.client import HTTPConnection
from http import HTTPStatus
import json
import os
import subprocess
from urllib.parse import urlsplit

import pytest

from render_tool_declarations import ROOT


pytestmark = pytest.mark.archive_host


def run_archive(*arguments):
    return subprocess.run([os.environ["ALMOND_ARCHIVE_TEST_HOST"], *arguments],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)


def test_generated_model_decodes(tmp_path):
    library = ROOT / "asset/models/GeneratedAssetfiles"
    manifest = json.loads((library / "manifest.json").read_text(encoding="utf-8"))
    asset_id = "gen-office-chair-1"
    asset = next(asset for asset in manifest["assets"] if asset["asset_id"] == asset_id)
    original = library / asset["file"]
    result = run_archive("--mesh", original, asset_id)
    assert result.returncode == 0, result.stderr
    model = json.loads(result.stdout)
    assert model["Passport"]["asset_id"] == asset_id
    assert model["TriangleCount"] > 0

    damaged = tmp_path / "damaged.glb"
    damaged.write_bytes(original.read_bytes()[:-1])
    invalid = run_archive("--mesh", damaged, asset_id)
    assert invalid.returncode == 1 and not invalid.stdout


def test_overlay_detects_tamper(tmp_path):
    release = tmp_path / "release"
    release.mkdir()
    routes = {}
    for route, name, mime, content in (
        ("/", "index.html", "text/html", b"<h1>Archive</h1>"),
        ("/api/catalogue", "catalogue.json", "application/json", b'{"assets":[]}'),
    ):
        (release / name).write_bytes(content)
        routes[route] = {"path": name, "mime": mime, "sha256": sha256(content).hexdigest()}
    (release / "bundle.json").write_text(json.dumps({"schema_version": 1, "routes": routes}), encoding="utf-8")

    drawing = tmp_path / "drawing.svg"
    content = b"<svg>one</svg>"
    drawing.write_bytes(content)
    original = drawing.stat()
    file_route = "/files/drawing.svg"
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"schema_version": 1, "catalogue": {"assets": []}, "files": {
        file_route: {"path": str(drawing), "root": str(tmp_path), "mime": "image/svg+xml",
                     "size": original.st_size, "mtime_ns": original.st_mtime_ns, "sha256": sha256(content).hexdigest()},
    }}), encoding="utf-8")

    async def inspect():
        process = await asyncio.create_subprocess_exec(
            os.environ["ALMOND_ARCHIVE_TEST_HOST"], "--serve", str(release), str(snapshot),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        )
        try:
            address = urlsplit((await asyncio.wait_for(process.stdout.readline(), 15)).decode().strip())
            assert address.hostname == "127.0.0.1" and address.port
            client = HTTPConnection(address.hostname, address.port, timeout=5)
            try:
                client.request("GET", "/api/catalogue")
                assert json.loads(client.getresponse().read())["library_status"]["status"] == "ready"
                client.request("GET", file_route)
                response = client.getresponse()
                assert response.status == HTTPStatus.OK and response.read() == content

                drawing.write_bytes(b"<svg>two</svg>")
                os.utime(drawing, ns=(original.st_atime_ns, original.st_mtime_ns))
                changed = drawing.stat()
                assert (changed.st_size, changed.st_mtime_ns) == (original.st_size, original.st_mtime_ns)
                client.request("GET", file_route)
                assert client.getresponse().status == HTTPStatus.CONFLICT
            finally:
                client.close()
        finally:
            try:
                await asyncio.wait_for(process.communicate(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()
        assert process.returncode == 0

    asyncio.run(inspect())
