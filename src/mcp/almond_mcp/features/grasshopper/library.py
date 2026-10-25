"""Startup indexing and capsule synchronization for Grasshopper libraries."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from almond_mcp.features.grasshopper.ghx_parser import validate_capsule_manifest

if TYPE_CHECKING:
    from almond_mcp.retrieval_store import AlmondStore


class LibraryIndexer:
    """Walks the library directory once at startup, building an O(1) lookup index."""

    INDEXED_EXTENSIONS = {'gh', 'ghx', 'json'}

    def __init__(self, directory: str):
        self.directory = directory
        self.index: dict[str, dict[str, str]] = {}
        self._build_index()

    def _build_index(self):
        print(f"Indexing library from: {self.directory}", file=sys.stderr)
        for root, _, files in os.walk(self.directory):
            for file in files:
                ext = file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                if ext in self.INDEXED_EXTENSIONS:
                    logic_id = file.rsplit('.', 1)[0].lower()
                    if logic_id not in self.index:
                        self.index[logic_id] = {}
                    self.index[logic_id][ext] = os.path.join(root, file)
        print(f"Indexed {len(self.index)} unique logic entities.", file=sys.stderr)

    def list_ids(self) -> list[str]:
        """Return sorted list of all indexed logic IDs."""
        return sorted(self.index.keys())


def _sync_capsule_library(store: AlmondStore, capsules_dir: str) -> dict:
    """Scan <capsules_dir>/*.capsule.json sidecars, validate each manifest via
    ghx_parser.validate_capsule_manifest, and sync the valid ones into the
    AlmondStore capsule registry.

    Invalid manifests are skipped loudly (stderr) rather than aborting startup,
    so one bad sidecar cannot take down the whole capsule library. The absolute
    sidecar path is recorded on each manifest (_manifest_path) so run_gh_definition
    can hand it to the bridge.
    """
    manifests: list[dict] = []
    skipped: list[dict] = []
    directory = Path(capsules_dir)
    if not directory.is_dir():
        print(f"Capsule directory not found: {directory}", file=sys.stderr)
        store.sync_capsules([])
        return {"synced": 0, "skipped": skipped}

    for manifest_path in sorted(directory.glob("*.capsule.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            skipped.append({"file": manifest_path.name, "errors": [str(exc)]})
            continue
        errors = validate_capsule_manifest(manifest)
        if errors:
            skipped.append({"file": manifest_path.name, "errors": errors})
            continue
        manifest["_manifest_path"] = str(manifest_path.resolve())
        manifests.append(manifest)

    for entry in skipped:
        print(
            f"Skipping capsule manifest {entry['file']}: {entry['errors']}",
            file=sys.stderr,
        )
    synced = store.sync_capsules(manifests)
    print(f"Synced {synced} capsule manifests from {directory}.", file=sys.stderr)
    return {"synced": synced, "skipped": skipped}
