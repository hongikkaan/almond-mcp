"""Persistent structured retrieval and scene state for AlmondMCP."""

from __future__ import annotations

import json
import math
import ntpath
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Public compatibility exports retain one exception identity across features.
from almond_mcp.store_common import (
    RETIRED_LIBRARY_ID, _utc_now, _json, _decode, _NativeRejected,
    ComponentReconciliationError, DrawingSheetReconciliationError,
)


from almond_mcp.features.scenes.store import ScenesStore


from almond_mcp.features.components.store import ComponentsStore


from almond_mcp.features.placement.store import PlacementStore


from almond_mcp.features.grasshopper.store import GrasshopperStore


from almond_mcp.features.structure.store import StructureStore


from almond_mcp.features.planning.store import PlanningStore


from almond_mcp.features.drawings.store import DrawingsStore


from almond_mcp.features.assets.store import AssetsStore


class AlmondStore(
    ScenesStore, ComponentsStore, PlacementStore, GrasshopperStore,
    StructureStore, PlanningStore, DrawingsStore, AssetsStore,
):
    """SQLite-backed asset retrieval, spatial state, and generation plans."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id TEXT NOT NULL UNIQUE,
                    library_id TEXT NOT NULL DEFAULT 'ikea',
                    category TEXT NOT NULL,
                    series TEXT NOT NULL,
                    product TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    width_mm REAL NOT NULL,
                    depth_mm REAL NOT NULL,
                    height_mm REAL NOT NULL,
                    match_status TEXT NOT NULL,
                    geometry_source_type TEXT NOT NULL,
                    file_available INTEGER NOT NULL DEFAULT 0,
                    search_text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS asset_fts USING fts5(
                    asset_id UNINDEXED,
                    search_text,
                    tokenize = 'unicode61 remove_diacritics 2'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS asset_rtree USING rtree(
                    asset_rowid,
                    min_x, max_x,
                    min_y, max_y,
                    min_z, max_z
                );

                CREATE TABLE IF NOT EXISTS scenes (
                    scene_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    units TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    min_x REAL NOT NULL,
                    max_x REAL NOT NULL,
                    min_y REAL NOT NULL,
                    max_y REAL NOT NULL,
                    min_z REAL NOT NULL,
                    max_z REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL UNIQUE,
                    scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
                    room_id TEXT REFERENCES rooms(room_id) ON DELETE SET NULL,
                    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
                    rhino_guid TEXT,
                    x_mm REAL NOT NULL,
                    y_mm REAL NOT NULL,
                    z_mm REAL NOT NULL,
                    rotation_degrees REAL NOT NULL,
                    scale REAL NOT NULL,
                    locked INTEGER NOT NULL DEFAULT 0,
                    min_x REAL NOT NULL,
                    max_x REAL NOT NULL,
                    min_y REAL NOT NULL,
                    max_y REAL NOT NULL,
                    min_z REAL NOT NULL,
                    max_z REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS instance_rtree USING rtree(
                    instance_rowid,
                    min_x, max_x,
                    min_y, max_y,
                    min_z, max_z
                );

                CREATE TABLE IF NOT EXISTS scene_revisions (
                    scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    patch_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (scene_id, revision)
                );

                CREATE TABLE IF NOT EXISTS generation_plans (
                    plan_id TEXT PRIMARY KEY,
                    scene_id TEXT REFERENCES scenes(scene_id) ON DELETE SET NULL,
                    scope TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS generation_plan_steps (
                    plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
                    step_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    depends_on_json TEXT NOT NULL,
                    input_refs_json TEXT NOT NULL,
                    output_refs_json TEXT NOT NULL,
                    PRIMARY KEY (plan_id, step_id)
                );

                CREATE TABLE IF NOT EXISTS capsules (
                    capsule_id TEXT PRIMARY KEY,
                    capability TEXT NOT NULL,
                    definition_file TEXT NOT NULL,
                    audited INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL DEFAULT '',
                    manifest_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_capsules_capability
                    ON capsules(capability, audited);

                CREATE TABLE IF NOT EXISTS validation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ran_at TEXT NOT NULL,
                    structure_type TEXT NOT NULL,
                    material TEXT NOT NULL,
                    load_kn REAL NOT NULL,
                    member_count INTEGER NOT NULL,
                    analysis_method TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    span_m REAL NOT NULL,
                    max_deflection_mm REAL NOT NULL,
                    deflection_limit_mm REAL NOT NULL,
                    utilization_ratio REAL NOT NULL,
                    max_stress_mpa REAL NOT NULL,
                    yield_stress_mpa REAL NOT NULL,
                    reactions_kn REAL NOT NULL,
                    verdict TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    guids_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_assets_category
                    ON assets(category, width_mm, depth_mm, height_mm);
                CREATE INDEX IF NOT EXISTS idx_instances_scene
                    ON instances(scene_id, room_id);
                CREATE INDEX IF NOT EXISTS idx_rooms_scene
                    ON rooms(scene_id);

                CREATE TABLE IF NOT EXISTS components (
                    component_id TEXT PRIMARY KEY,
                    model_path TEXT NOT NULL,
                    rhino_group_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    parent_component_id TEXT REFERENCES components(component_id) ON DELETE RESTRICT,
                    UNIQUE(component_id, model_path),
                    UNIQUE(model_path, rhino_group_id)
                );

                CREATE TABLE IF NOT EXISTS document_objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_path TEXT NOT NULL,
                    rhino_guid TEXT NOT NULL,
                    component_id TEXT,
                    object_type TEXT NOT NULL,
                    min_x REAL NOT NULL, max_x REAL NOT NULL,
                    min_y REAL NOT NULL, max_y REAL NOT NULL,
                    min_z REAL NOT NULL, max_z REAL NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(model_path, rhino_guid),
                    FOREIGN KEY(component_id, model_path)
                        REFERENCES components(component_id, model_path)
                );

                CREATE TABLE IF NOT EXISTS scene_components (
                    scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
                    component_id TEXT NOT NULL REFERENCES components(component_id) ON DELETE CASCADE,
                    PRIMARY KEY(scene_id, component_id)
                );

                CREATE TABLE IF NOT EXISTS scene_objects (
                    scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
                    object_rowid INTEGER NOT NULL REFERENCES document_objects(id) ON DELETE CASCADE,
                    PRIMARY KEY(scene_id, object_rowid)
                );

                CREATE INDEX IF NOT EXISTS idx_document_objects_component
                    ON document_objects(component_id);
                CREATE INDEX IF NOT EXISTS idx_scene_components_component
                    ON scene_components(component_id, scene_id);
                CREATE INDEX IF NOT EXISTS idx_scene_objects_object
                    ON scene_objects(object_rowid, scene_id);

                CREATE TRIGGER IF NOT EXISTS instances_delete_rtree
                AFTER DELETE ON instances BEGIN
                    DELETE FROM instance_rtree WHERE instance_rowid = OLD.id;
                END;
                """
            )
            asset_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(assets)")
            }
            if "library_id" not in asset_columns:
                connection.execute(
                    "ALTER TABLE assets ADD COLUMN library_id TEXT NOT NULL DEFAULT 'ikea'"
                )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_assets_library_category
                ON assets(library_id, category, width_mm, depth_mm, height_mm)
                """
            )
            connection.execute(
                "DELETE FROM instance_rtree WHERE instance_rowid NOT IN (SELECT id FROM instances)"
            )
            component_columns = {row["name"] for row in connection.execute("PRAGMA table_info(components)")}
            if "parent_component_id" not in component_columns:
                connection.execute(
                    "ALTER TABLE components ADD COLUMN parent_component_id TEXT "
                    "REFERENCES components(component_id) ON DELETE RESTRICT"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_components_parent ON components(parent_component_id)"
            )
            for action in ("INSERT", "UPDATE OF parent_component_id, model_path"):
                trigger_name = "components_parent_check_" + ("insert" if action == "INSERT" else "update")
                connection.execute(f"""
                    CREATE TRIGGER IF NOT EXISTS {trigger_name} BEFORE {action} ON components
                    WHEN NEW.parent_component_id IS NOT NULL
                    BEGIN
                        SELECT CASE WHEN NEW.parent_component_id = NEW.component_id OR
                            NOT EXISTS (SELECT 1 FROM components p
                                WHERE p.component_id = NEW.parent_component_id
                                  AND p.model_path = NEW.model_path)
                            THEN RAISE(ABORT, 'Component parent must exist in the same model and differ from child') END;
                        SELECT CASE WHEN EXISTS (
                            WITH RECURSIVE ancestors(component_id, parent_component_id) AS (
                                SELECT component_id, parent_component_id FROM components
                                    WHERE component_id = NEW.parent_component_id
                                UNION
                                SELECT c.component_id, c.parent_component_id FROM components c
                                    JOIN ancestors a ON c.component_id = a.parent_component_id
                            )
                            SELECT 1 FROM ancestors WHERE component_id = NEW.component_id
                        ) THEN RAISE(ABORT, 'Component hierarchy contains a cycle') END;
                    END
                """)
            self._initialize_generation_plans(connection)
            self._initialize_drawing_sheets(connection)

    # Asset registry -----------------------------------------------------


    # Capsule registry ---------------------------------------------------


    # Scene ledger -------------------------------------------------------


    # Structural validation history ---------------------------------------


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
