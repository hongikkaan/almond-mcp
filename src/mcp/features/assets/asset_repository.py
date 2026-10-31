"""One read-only catalogue for generated models, drawing elements and projections.

The catalogue joins existing libraries by stable asset ID. Files stay in their
canonical libraries; HTTP serves only individual manifest-listed files.
"""
from __future__ import annotations

import json
import mimetypes
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from urllib.parse import quote, urlsplit

from almond_mcp import __version__, paths
from almond_mcp.features.assets import drafting
from almond_mcp.features.assets.model_index import is_model_source, verify_model

UI_ROOT = Path(__file__).resolve().parents[2] / "library_ui"
if not UI_ROOT.is_dir():
    UI_ROOT = Path(__file__).resolve().parents[3] / "rhp" / "Asset_Panel" / "web"


def read_json(path: Path, default=None):
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _public_metadata(value):
    """Keep portable provenance; local paths belong to explicit MCP file handles."""
    def private(item):
        return isinstance(item, str) and (PureWindowsPath(item).is_absolute() or item.startswith(("/", "file://")))
    if isinstance(value, dict):
        return {key: _public_metadata(item) for key, item in value.items() if not private(item)}
    if isinstance(value, list):
        return [_public_metadata(item) for item in value if not private(item)]
    return value


class AssetRepository:
    def __init__(self, roots: dict[str, Path] | None = None):
        self.roots = roots or {
            "generated": Path(paths.resolve_dir("RHINO_MCP_GENERATED_ASSET_DIR")),
            "drawing": Path(paths.resolve_dir("RHINO_MCP_DRAWING_ASSET_DIR")),
            "drafting": Path(paths.resolve_dir("RHINO_MCP_DRAFTING_DIR")),
        }
        self.roots = {k: Path(v).resolve() for k, v in self.roots.items()}
        self.files: dict[str, tuple[Path, Path]] = {}
        self.records: dict[str, dict] = {}
        self.refresh()

    def file(self, library: str, relative: str | None) -> str | None:
        if not relative:
            return None
        root = self.roots[library]
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            return None
        url = "/files/" + library + "/" + quote(candidate.relative_to(root).as_posix(), safe="/")
        self.files[url] = (root, candidate)
        return url

    def refresh(self):
        self.files = {}
        self.records = {}
        source_register = read_json(self.roots["generated"] / "source-register.json")
        sources = {a["asset_id"]: a for a in source_register.get("assets", [])}
        drawings = {a["asset_id"]: a for a in read_json(self.roots["drafting"] / "manifest.json").get("assets", [])}
        for library in ("generated", "drawing"):
            manifest = read_json(self.roots[library] / "manifest.json")
            for asset in manifest.get("assets", []):
                aid = asset["asset_id"]
                model = self.file(library, asset.get("file"))
                fmt = Path(asset.get("file", "")).suffix.lstrip(".").lower()
                model_source = is_model_source(asset, generated=library == "generated")
                record = {
                    "id": aid, "name": asset.get("product", aid),
                    "kind": "model" if model_source else "element",
                    "library": "model_assets", "source_library": library, "category": asset.get("category", "other"),
                    "variant": asset.get("variant", ""), "format": fmt,
                    "tags": asset.get("tags", []), "roles": asset.get("drawing_roles", []),
                    "dimensions_mm": asset.get("dimensions_mm", {}),
                    "dimension_basis": asset.get("spatial", {}).get("bounds_source", "unverified"),
                    "available": bool(model), "model": model,
                    "preview": self.file(library, f"previews/{aid}.png") if library == "generated" else model if fmt == "svg" else None,
                    "contract": self.file(library, asset.get("contract_file")),
                    "license": asset.get("license", "Source terms apply; not cleared for redistribution"),
                    "source_url": (asset.get("warehouse_url") or "https://www.meshy.ai/") if library == "generated" else asset.get("warehouse_url", ""),
                    "publisher": asset.get("warehouse_publisher") or ("Almond generated asset library" if library == "generated" else "Not recorded"),
                    "provenance": _public_metadata(sources.get(aid)), "metadata": _public_metadata(asset),
                    "drawing": None, "uri": f"almond://repository/{aid}",
                    "record_url": "/api/assets/" + quote(aid, safe="") + ".json",
                }
                conversion = model_source and fmt != "3dm"
                record.update(source_available=bool(model), source_only=conversion,
                              model_status="needs_conversion" if conversion else "unverified" if fmt == "3dm" and model else "ready" if model else "missing",
                              drawing_status="missing", drawing_ready=False)
                if conversion:
                    record.update(source_file=model, model=None, available=False,
                                  next_tool="prepare_drawing_asset", conversion_target="3dm")
                captured = ((asset.get("geometry_source") or {}).get("parameters") or {}).get("captured_generation")
                if captured and library == "generated":
                    record["generation_image"] = self.file(library, captured.get("input_image_file"))
                if asset.get("drawing_package") or aid in drawings:
                    package_library = library if asset.get("drawing_package") else "drafting"
                    package = asset.get("drawing_package") or drawings[aid]["package"]
                    drawing_url = self.file(package_library, package + "/drawing.json")
                    if drawing_url:
                        drawing = read_json(self.files[drawing_url][1])
                        views = []
                        for rep in drawing.get("representations", []):
                            view = {k: rep[k] for k in ("view", "scale", "method", "approximation_note") if k in rep}
                            for fmt_name in ("svg", "dxf"):
                                view[fmt_name] = self.file(package_library, package + "/" + rep[fmt_name])
                            views.append(view)
                        record["drawing"] = {
                            "record": drawing_url, "views": views,
                            "sheets": [{"scale": s, "svg": self.file(package_library, f"{package}/sheet-A3-1-{s}.svg")} for s in drawing.get("scales", [])],
                            "dimensions": self.file(package_library, package + "/dimensions.json"),
                            "source": _public_metadata(drawing.get("source", {})),
                        }
                        if fmt == "3dm":
                            record["preview"] = next((v["svg"] for v in views if v["view"] == "plan"), None)
                        record["drawing_status"] = "source_requires_conversion" if conversion else "unverified"
                self.records[aid] = record
        self.sources = _public_metadata(read_json(self.roots["drafting"] / "sources.json").get("sources", []))

    def verify_record(self, asset: dict) -> dict:
        record = dict(asset)
        if record["format"] == "3dm" and record.get("model"):
            source = self.files[record["model"]][1]
            package = self.files[record["drawing"]["record"]][1].parent if record.get("drawing") else None
            record.update(verify_model(source, record["metadata"].get("sha256"), package))
            if record["model_status"] == "needs_refresh":
                record["next_tool"] = "refresh_asset"
        return record

    def catalogue(self, *, verify=True) -> dict:
        assets = [self.verify_record(a) if verify else dict(a) for a in self.records.values()]
        return {"schema_version": 1, "version": __version__,
                "title": "Almond Object Archive", "indexed_at": datetime.now(timezone.utc).isoformat(),
                "counts": {"assets": len(assets), "models": sum(a["kind"] == "model" for a in assets),
                           "elements": sum(a["kind"] == "element" for a in assets),
                           "drawing_packages": sum(bool(a["drawing"]) for a in assets),
                           "views": sum(len(a["drawing"]["views"]) for a in assets if a["drawing"])},
                "assets": assets, "sources": self.sources}

    def search(self, query="", kind="all", drawing_ready=False, limit=20):
        if kind not in {"all", "model", "element"}:
            raise ValueError("kind must be all, model or element")
        terms = query.casefold().split()
        matches = []
        for asset in self.records.values():
            text = " ".join([asset["name"], asset["id"], asset["category"], asset["variant"], asset["metadata"].get("render_material_id", ""), *asset["tags"], *asset["roles"]]).casefold()
            if kind != "all" and asset["kind"] != kind:
                continue
            if all(term in text for term in terms):
                if drawing_ready:
                    asset = self.verify_record(asset)
                    if not asset["drawing_ready"]:
                        continue
                matches.append(asset)
        page = [self.verify_record(a) for a in matches[:max(1, min(limit, 100))]]
        results = [{k: asset[k] for k in ("id", "name", "kind", "category", "format", "available", "dimensions_mm", "license", "uri",
                    "drawing_ready", "drawing_status", "model_status", "source_only", "source_available")} |
                    {k: asset[k] for k in ("next_tool", "conversion_target", "verification_issue") if k in asset} for asset in page]
        return {"total": len(matches), "assets": results}


def create_server(port=8767, repository: AssetRepository | None = None):
    repo = repository or AssetRepository()
    static = {"/" + p.relative_to(UI_ROOT).as_posix(): p for p in UI_ROOT.rglob("*") if p.is_file()}
    static["/"] = UI_ROOT / "index.html"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond(False)

        def do_HEAD(self):
            self.respond(True)

        def respond(self, head):
            # Loopback binding plus Host validation prevents DNS rebinding reads.
            if self.headers.get("Host", "") not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
                self.send_error(403)
                return
            route = urlsplit(self.path).path
            content = None
            mime = "application/json"
            filename = None
            if route == "/api/catalogue":
                content = json.dumps(repo.catalogue(), ensure_ascii=False).encode()
                filename = "almond-object-archive.json"
            elif route.startswith("/api/assets/"):
                record = next((a for a in repo.records.values() if a["record_url"] == route), None)
                if record:
                    content = json.dumps(record, ensure_ascii=False, indent=2).encode()
                    filename = record["id"] + ".json"
            else:
                path = static.get(route)
                root = UI_ROOT.resolve()
                if route in repo.files:
                    root, path = repo.files[route]
                if path and path.resolve().is_relative_to(root) and path.is_file():
                    content = path.read_bytes()
                    mime = {".js": "text/javascript", ".mjs": "text/javascript", ".glb": "model/gltf-binary", ".svg": "image/svg+xml", ".dxf": "application/dxf"}.get(path.suffix, mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                    filename = path.name
            if content is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            if filename and urlsplit(self.path).query == "download=1":
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(filename))
            self.end_headers()
            if not head:
                self.wfile.write(content)

        def log_message(self, fmt, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve_library(port=8767, open_browser=False):
    import webbrowser

    with create_server(port) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Almond Object Archive: {url}\nPress Ctrl+C to stop.", flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            if os.environ.get("ALMOND_DESKTOP_STOP_EVENT"):
                from almond_mcp.runtime.desktop_runtime import serve_until_desktop_exit
                serve_until_desktop_exit(server)
            else:
                server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def snapshot(repository=None) -> dict:
    """Private native-host snapshot; the files table is never an HTTP response."""
    repository = repository or AssetRepository()
    files = {}
    for url, (root, path) in repository.files.items():
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(root) or any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                    for p in (path, *path.parents) if p != root and root in p.parents):
                continue
            stat = path.stat()
            files[url] = {"path": str(resolved), "root": str(root), "size": stat.st_size,
                          "mtime_ns": stat.st_mtime_ns, "mime": mimetypes.guess_type(path.name)[0] or "application/octet-stream"}
        except OSError:
            continue
    return {"schema_version": 1, "catalogue": repository.catalogue(verify=False), "files": files}


if __name__ == "__main__":
    import argparse
    import sys
    from almond_mcp.runtime.library_paths import configure_library_paths
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", action="store_true", required=True)
    parser.parse_args()
    try:
        from almond_mcp.runtime.desktop_runtime import ensure_desktop_runtime
        ensure_desktop_runtime()
        configure_library_paths()
        print(json.dumps(snapshot(), ensure_ascii=False, allow_nan=False))
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
