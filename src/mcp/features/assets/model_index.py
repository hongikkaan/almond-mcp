"""One model/2D view with bounded, target-local verification of editable sources."""
from collections import OrderedDict
from pathlib import Path
from threading import RLock
import time
from types import SimpleNamespace

from almond_mcp.features.assets.library_index import AssetLibraryIndexer
from almond_mcp.features.assets import drafting

_VERIFIED = OrderedDict()
_LOCK = RLock()
_CACHE_SECONDS = 5.0
_MODEL_FORMATS = {".3dm", ".skp", ".glb", ".gltf", ".obj", ".stl", ".ply", ".off",
                  ".fbx", ".3ds", ".3mf", ".dae", ".step", ".stp", ".iges", ".igs"}


def is_model_source(asset, *, generated=False):
    suffix = Path(asset.get("file", asset.get("_resolved_file", ""))).suffix.lower()
    return generated or suffix in _MODEL_FORMATS or str(asset.get("geometry_mode", "")).lower().startswith("3d")


def _stamp(path):
    stat = path.stat()
    return (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def verify_model(source, expected_hash, package=None):
    """Verify requested records only; unchanged files reuse a short-lived result."""
    source = Path(source)
    package = Path(package) if package else None
    result = {"model_status": "unverified", "drawing_status": "missing", "drawing_ready": False}
    try:
        if not source.is_file():
            return {**result, "model_status": "missing", "drawing_status": "source_missing"}
        if source.stat().st_size > 100_000_000:
            return {**result, "verification_issue": "source_exceeds_100_MB"}
        watched = [source]
        if package:
            try:
                manifest = drafting.read_package_manifest(package)
                files, _ = drafting.package_inventory(manifest)
            except (OSError, ValueError, KeyError, TypeError):
                return {**result, "drawing_status": "invalid"}
            watched.append(drafting.package_file(package, "drawing.json"))
            for name in files:
                watched.append(drafting.package_file(package, name))
        signature = tuple(_stamp(p) for p in watched)
        key = (str(source.resolve()), expected_hash, str(package.resolve()) if package else "")
        now = time.monotonic()
        with _LOCK:
            cached = _VERIFIED.get(key)
            if cached and now - cached[0] < _CACHE_SECONDS and signature == cached[1]:
                _VERIFIED.move_to_end(key)
                return {**cached[2], "verification_basis": "recent_hashes_unchanged_file_stats"}
        current = drafting.file_sha(source)
        result["model_status"] = "ready" if expected_hash and current == expected_hash.upper() else "needs_refresh" if expected_hash else "unverified"
        if package:
            checked = drafting.audit_package(package, source, source_sha256=current)
            result["drawing_status"] = ("current" if checked["status"] == "success" and checked["source_geometry"] == "source_file_current"
                                       else "stale" if checked["source_geometry"] == "stale" else "invalid")
            result["drawing_ready"] = result["model_status"] == "ready" and result["drawing_status"] == "current"
        if signature != tuple(_stamp(p) for p in watched):
            return {"model_status": "unverified", "drawing_status": "unverified", "drawing_ready": False,
                    "verification_issue": "files_changed_during_check"}
        result["verification_basis"] = "file_hashes"
        with _LOCK:
            _VERIFIED[key] = (now, signature, dict(result))
            _VERIFIED.move_to_end(key)
            while len(_VERIFIED) > 256:
                _VERIFIED.popitem(last=False)
        return result
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"model_status": "unverified", "drawing_status": "unverified", "drawing_ready": False,
                "verification_issue": type(exc).__name__}


class ModelAssetIndex(AssetLibraryIndexer):
    """Join metadata cheaply; verify a requested item or returned page, never every asset."""

    def __init__(self, drawing, generated):
        self.assets = {}
        for index, legacy in ((generated, True), (drawing, False)):
            for asset_id, original in index.assets.items():
                if not legacy and asset_id in self.assets and not original.get("file_available"):
                    continue
                record = dict(original)
                suffix = Path(record.get("file", record.get("_resolved_file", ""))).suffix.lower()
                model = is_model_source(record, generated=legacy)
                conversion = model and suffix != ".3dm"
                record.update(library_id="model_assets", asset_kind="model" if model else "drawing",
                              source_library=original.get("library_id", "generated_assets" if legacy else "drawing_assets"),
                              source_available=bool(original.get("file_available")),
                              model_status="needs_conversion" if conversion else "unverified" if suffix == ".3dm" else "ready" if original.get("file_available") else "missing",
                              drawing_status="missing", drawing_ready=False)
                if hasattr(index, "directory"):
                    record["_library_root"] = str(index.directory)
                if conversion:
                    record.update(file_available=False, source_only=True,
                                  next_tool="prepare_drawing_asset", conversion_target="3dm")
                self.assets[asset_id] = record

    def get(self, asset_id):
        original = self.assets.get(asset_id)
        if original is None:
            return None
        record = dict(original)
        source = record.get("_resolved_file")
        if source and Path(source).suffix.lower() == ".3dm" and not record.get("source_only"):
            package = None
            if record.get("drawing_package") and record.get("_library_root"):
                root = Path(record["_library_root"]).resolve()
                package = (root / record["drawing_package"]).resolve()
                if not package.is_relative_to(root):
                    return {**record, "model_status": "unverified", "drawing_status": "invalid", "drawing_ready": False}
            record.update(verify_model(source, record.get("sha256"), package))
            if record["model_status"] == "needs_refresh":
                record["next_tool"] = "refresh_asset"
            record["file_available"] = Path(source).is_file()
        return record

    def public_record(self, asset):
        record = super().public_record(asset)
        source = asset.get("_resolved_file")
        if source and Path(source).is_absolute():
            record["source_path"] = source
            if not asset.get("source_only"):
                record["model_path"] = source
        return record

    def search_page(self, **filters):
        page = super().search_page(**filters)
        page["assets"] = [self.public_record(self.get(item["asset_id"])) for item in page["assets"]]
        return page


def for_context(context):
    drawing = context.drawing_asset_indexer
    generated = getattr(context, "generated_asset_indexer", SimpleNamespace(assets={}))
    return ModelAssetIndex(drawing, generated)
