"""Persistent structured retrieval and scene state for AlmondMCP."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

# Public compatibility exports retain one exception identity across features.
from almond_mcp.store_common import (
    RETIRED_LIBRARY_ID, _utc_now, _json, _decode, _NativeRejected,
    ComponentReconciliationError, DrawingSheetReconciliationError,
)


from almond_mcp.features.assets.store import AssetsStore
from almond_mcp.features.components.store import ComponentsStore
from almond_mcp.features.drawings.store import DrawingsStore
from almond_mcp.features.grasshopper.store import GrasshopperStore
from almond_mcp.features.planning.files import ProjectFilesStore
from almond_mcp.features.planning.store import PlanningStore
from almond_mcp.features.scenes.store import ScenesStore
from almond_mcp.features.structure.store import StructureStore
from almond_mcp.store_database import StoreDatabase


class AlmondStore(
    ScenesStore, ComponentsStore, GrasshopperStore,
    StructureStore, PlanningStore, ProjectFilesStore, DrawingsStore, AssetsStore,
):
    """SQLite-backed asset retrieval, spatial state, and generation plans."""

    def __init__(self, database_path: str | Path):
        self._database = StoreDatabase(database_path)
        self._database.initialize(self)

    @property
    def database_path(self) -> Path:
        return self._database.database_path

    def _connect(self):
        return self._database.connect()

    def _record_revision(
        self,
        connection: sqlite3.Connection,
        scene_id: str,
        operation: str,
        patch: dict[str, Any],
    ) -> int:
        row = connection.execute(
            "SELECT revision FROM scenes WHERE scene_id = ?",
            (scene_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"Unknown scene_id: {scene_id}")
        revision = int(row["revision"]) + 1
        now = _utc_now()
        connection.execute(
            "UPDATE scenes SET revision = ?, updated_at = ? WHERE scene_id = ?",
            (revision, now, scene_id),
        )
        connection.execute(
            """
            INSERT INTO scene_revisions(scene_id, revision, operation, patch_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scene_id, revision, operation, _json(patch), now),
        )
        return revision
