"""Installed-library overlay on the actual standalone host; no Rhino is opened."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

import pytest


pytestmark = pytest.mark.archive_host


@pytest.fixture
def installed_host(tmp_path):
    bundle = tmp_path / "archive"
    bundle.mkdir()
    base = {"schema_version": 1, "assets": [
        {"id": "shared-chair", "name": "Old source", "kind": "model", "format": "glb", "source_only": True,
         "source_file": "/files/generated/old.glb", "record_url": "/api/assets/shared-chair.json"},
        {"id": "source-only", "name": "Retained source", "kind": "model", "source_only": True,
         "source_file": "/files/generated/retained.glb", "record_url": "/api/assets/source-only.json"}],
        "counts": {"assets": 2}, "distribution": "rhino"}
    routes = {}
    for route, name, body, mime in [
        ("/", "index.html", b"<html></html>", "text/html"),
        ("/api/catalogue", "catalogue.json", json.dumps(base).encode(), "application/json"),
        ("/files/generated/retained.glb", "retained.glb", b"retained source", "application/octet-stream"),
    ]:
        (bundle / name).write_bytes(body)
        routes[route] = {"path": name, "sha256": hashlib.sha256(body).hexdigest(), "mime": mime}
    (bundle / "bundle.json").write_text(json.dumps({"schema_version": 1, "routes": routes}), encoding="utf-8")
    library = tmp_path / "installed"
    library.mkdir()
    model = library / "model.3dm"
    model.write_bytes(b"3dm content is validated by placement, not the HTTP host")
    model_url = "/files/drawing/registered/model.3dm"
    asset = {"id": "shared-chair", "name": "Current canonical", "kind": "model", "format": "3dm",
             "model": model_url, "available": True, "model_status": "unverified", "record_url": "/api/assets/shared-chair.json"}
    def file_entry(path=model, root=library):
        stat = path.stat()
        return {"path": str(path), "root": str(root), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
                "mime": "application/octet-stream"}
    snapshot = {"schema_version": 1, "catalogue": {"assets": [asset]}, "files": {model_url: file_entry()}}
    snapshot_path = tmp_path / "snapshot.json"
    def publish():
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    publish()
    process = subprocess.Popen([os.environ["ALMOND_ARCHIVE_TEST_HOST"], str(bundle), "--snapshot", str(snapshot_path)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        url = process.stdout.readline().strip()
        assert url.startswith("http://127.0.0.1:"), process.stderr.read() if process.poll() is not None else url
        origin = urlsplit(url)
        def request(route):
            connection = http.client.HTTPConnection(origin.hostname, origin.port, timeout=10)
            connection.request("GET", route)
            response = connection.getresponse()
            result = response.status, response.read()
            connection.close()
            return result
        yield request, snapshot, publish, model, model_url, file_entry
    finally:
        process.communicate("\n", timeout=10)
        assert process.returncode == 0


def test_overlay_keeps_release_sources_and_uses_current_canonical_record(installed_host):
    request, snapshot, _, model, url, _ = installed_host
    status, body = request("/api/catalogue")
    catalogue = json.loads(body)
    assert status == 200 and catalogue["library_status"]["status"] == "ready"
    assert len(catalogue["assets"]) == 2
    current = next(a for a in catalogue["assets"] if a["id"] == "shared-chair")
    assert current["format"] == "3dm" and current["model_status"] == "unverified"
    assert "source_file" not in current
    assert "files" not in catalogue and str(model) not in json.dumps(catalogue)
    assert json.loads(request("/api/assets/shared-chair.json")[1]) == current
    assert request(url) == (200, model.read_bytes())
    assert request("/files/generated/retained.glb") == (200, b"retained source")


def test_changed_installed_file_requires_reload_and_new_stat_snapshot(installed_host):
    request, snapshot, publish, model, url, file_entry = installed_host
    assert request("/api/catalogue")[0] == 200
    old = model.stat()
    model.write_bytes(b"changed source")
    os.utime(model, ns=(old.st_atime_ns, old.st_mtime_ns + 1_000_000_000))
    assert request(url)[0] == 409
    snapshot["files"][url] = file_entry()
    publish()
    assert json.loads(request("/api/catalogue")[1])["library_status"]["status"] == "ready"
    assert request(url) == (200, b"changed source")


def test_invalid_root_is_not_served_and_failure_keeps_release_catalogue(installed_host):
    request, snapshot, publish, model, url, file_entry = installed_host
    outside = model.parent.parent / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    snapshot["files"][url] = file_entry(outside, model.parent)
    publish()
    status, body = request("/api/catalogue")
    catalogue = json.loads(body)
    assert status == 200 and catalogue["library_status"]["status"] == "error"
    assert next(a for a in catalogue["assets"] if a["id"] == "shared-chair")["format"] == "glb"
    assert request(url)[0] == 404
    assert request("/files/generated/retained.glb")[0] == 200
    assert str(outside) not in json.dumps(catalogue)


def test_reader_failure_is_visible_and_does_not_hide_release_sources(installed_host):
    request, snapshot, publish, _, _, _ = installed_host
    snapshot.clear()
    snapshot.update(status="error", error_code="library_export_timeout", message="Lookup timed out. Reload.")
    publish()
    catalogue = json.loads(request("/api/catalogue")[1])
    assert catalogue["library_status"]["error_code"] == "library_export_timeout"
    assert len(catalogue["assets"]) == 2
