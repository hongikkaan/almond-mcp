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


class AlmondStore(ScenesStore, ComponentsStore, PlacementStore, GrasshopperStore, StructureStore, PlanningStore, DrawingsStore):
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

    def sync_assets(
        self,
        assets: list[dict[str, Any]],
        library_id: str = "ikea",
    ) -> int:
        """Upsert one manifest and prune stale records only within its library."""
        library_id = library_id.strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,40}", library_id):
            raise ValueError("library_id must be a short lowercase identifier.")
        now = _utc_now()
        seen: list[str] = []
        with self._connect() as connection:
            for source in assets:
                asset = {
                    key: value
                    for key, value in source.items()
                    if not key.startswith("_")
                }
                asset["library_id"] = library_id
                asset_id = str(asset["asset_id"])
                dimensions = asset.get("dimensions_mm", {})
                width = float(dimensions.get("width", 0))
                depth = float(dimensions.get("depth", 0))
                height = float(dimensions.get("height", 0))
                if min(width, depth, height) <= 0:
                    raise ValueError(f"Asset {asset_id} has invalid dimensions.")

                search_text = " ".join(
                    filter(
                        None,
                        [
                            asset_id,
                            asset.get("category", ""),
                            asset.get("series", ""),
                            asset.get("product", ""),
                            asset.get("variant", ""),
                            asset.get("brand", ""),
                            asset.get("source_class", ""),
                            " ".join(asset.get("tags", [])),
                        ],
                    )
                )
                geometry_source = asset.get("geometry_source", {})
                connection.execute(
                    """
                    INSERT INTO assets (
                        asset_id, library_id, category, series, product, variant,
                        width_mm, depth_mm, height_mm, match_status,
                        geometry_source_type, file_available, search_text,
                        metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(asset_id) DO UPDATE SET
                        library_id = excluded.library_id,
                        category = excluded.category,
                        series = excluded.series,
                        product = excluded.product,
                        variant = excluded.variant,
                        width_mm = excluded.width_mm,
                        depth_mm = excluded.depth_mm,
                        height_mm = excluded.height_mm,
                        match_status = excluded.match_status,
                        geometry_source_type = excluded.geometry_source_type,
                        file_available = excluded.file_available,
                        search_text = excluded.search_text,
                        metadata_json = excluded.metadata_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        asset_id,
                        library_id,
                        asset.get("category", ""),
                        asset.get("series", ""),
                        asset.get("product", ""),
                        asset.get("variant", ""),
                        width,
                        depth,
                        height,
                        asset.get("match_status", ""),
                        geometry_source.get("type", "downloaded_asset"),
                        int(bool(asset.get("file_available"))),
                        search_text,
                        _json(asset),
                        now,
                    ),
                )
                asset_row = connection.execute(
                    "SELECT id FROM assets WHERE asset_id = ?",
                    (asset_id,),
                ).fetchone()
                row_id = int(asset_row["id"])

                connection.execute(
                    "DELETE FROM asset_fts WHERE asset_id = ?",
                    (asset_id,),
                )
                connection.execute(
                    "INSERT INTO asset_fts(asset_id, search_text) VALUES (?, ?)",
                    (asset_id, search_text),
                )
                connection.execute(
                    "DELETE FROM asset_rtree WHERE asset_rowid = ?",
                    (row_id,),
                )
                spatial = asset.get("spatial", {})
                bounds = spatial.get("local_aabb", {})
                minimum = bounds.get("min", [-width / 2, -depth / 2, 0])
                maximum = bounds.get("max", [width / 2, depth / 2, height])
                connection.execute(
                    """
                    INSERT INTO asset_rtree(
                        asset_rowid, min_x, max_x, min_y, max_y, min_z, max_z
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row_id,
                        float(minimum[0]),
                        float(maximum[0]),
                        float(minimum[1]),
                        float(maximum[1]),
                        float(minimum[2]),
                        float(maximum[2]),
                    ),
                )
                seen.append(asset_id)

            if seen:
                placeholders = ",".join("?" for _ in seen)
                stale_rows = connection.execute(
                    f"""
                    SELECT id, asset_id FROM assets
                    WHERE library_id = ? AND asset_id NOT IN ({placeholders})
                    """,
                    [library_id, *seen],
                ).fetchall()
            else:
                stale_rows = connection.execute(
                    "SELECT id, asset_id FROM assets WHERE library_id = ?",
                    (library_id,),
                ).fetchall()
            for stale in stale_rows:
                connection.execute(
                    "DELETE FROM asset_fts WHERE asset_id = ?",
                    (stale["asset_id"],),
                )
                connection.execute(
                    "DELETE FROM asset_rtree WHERE asset_rowid = ?",
                    (stale["id"],),
                )
                referenced = connection.execute(
                    "SELECT 1 FROM instances WHERE asset_id = ? LIMIT 1",
                    (stale["asset_id"],),
                ).fetchone()
                if referenced:
                    # Scene history still points at this asset: keep the row
                    # for lookups but take it out of its library and search.
                    connection.execute(
                        """
                        UPDATE assets SET library_id = ?, file_available = 0,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (RETIRED_LIBRARY_ID, now, stale["id"]),
                    )
                else:
                    connection.execute(
                        "DELETE FROM assets WHERE id = ?",
                        (stale["id"],),
                    )
        return len(seen)

    @staticmethod
    def compact_asset(asset: dict[str, Any]) -> dict[str, Any]:
        return {
            "asset_id": asset["asset_id"],
            "library_id": asset.get("library_id", "ikea"),
            "brand": asset.get("brand", "IKEA"),
            "source_class": asset.get("source_class", "ikea_catalogue"),
            "catalogue_status": asset.get("catalogue_status"),
            "category": asset.get("category"),
            "series": asset.get("series"),
            "product": asset.get("product"),
            "variant": asset.get("variant"),
            "size_mm": [
                asset.get("dimensions_mm", {}).get("width"),
                asset.get("dimensions_mm", {}).get("depth"),
                asset.get("dimensions_mm", {}).get("height"),
            ],
            "match": asset.get("match_status"),
            "source_type": asset.get("geometry_source", {}).get("type"),
            "available": bool(asset.get("file_available")),
        }

    def search_assets(
        self,
        query: str = "",
        library_id: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        exact_dimensions_only: bool = False,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))
        clauses: list[str] = []
        parameters: list[Any] = []
        joins = ""
        ordering = "a.series, a.product, a.asset_id"

        if library_id.strip():
            clauses.append("a.library_id = ?")
            parameters.append(library_id.strip().lower())
        else:
            clauses.append("a.library_id != ?")
            parameters.append(RETIRED_LIBRARY_ID)
        tokens = re.findall(r"[\w-]+", query.lower(), flags=re.UNICODE)
        if tokens:
            joins = "JOIN asset_fts ON asset_fts.asset_id = a.asset_id"
            fts_query = " OR ".join(f'"{token}"*' for token in tokens[:12])
            clauses.append("asset_fts MATCH ?")
            parameters.append(fts_query)
            ordering = "bm25(asset_fts), a.series, a.product"
        if category.strip():
            clauses.append("a.category = ?")
            parameters.append(category.strip().lower())
        if max_width_mm > 0:
            clauses.append("a.width_mm <= ?")
            parameters.append(float(max_width_mm))
        if max_depth_mm > 0:
            clauses.append("a.depth_mm <= ?")
            parameters.append(float(max_depth_mm))
        if max_height_mm > 0:
            clauses.append("a.height_mm <= ?")
            parameters.append(float(max_height_mm))
        if exact_dimensions_only:
            clauses.append("a.match_status = 'exact_dimensions'")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        count_sql = f"SELECT COUNT(*) AS count FROM assets a {joins} {where}"
        query_sql = f"""
            SELECT a.metadata_json
            FROM assets a
            {joins}
            {where}
            ORDER BY {ordering}
            LIMIT ? OFFSET ?
        """
        with self._connect() as connection:
            total = int(connection.execute(count_sql, parameters).fetchone()["count"])
            rows = connection.execute(
                query_sql,
                [*parameters, limit, offset],
            ).fetchall()
        assets = [
            self.compact_asset(_decode(row["metadata_json"], {}))
            for row in rows
        ]
        next_offset = offset + len(assets)
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "assets": assets,
        }

    def get_asset(
        self,
        asset_id: str,
        library_id: str = "",
    ) -> dict[str, Any] | None:
        clauses = ["asset_id = ?"]
        parameters: list[Any] = [asset_id]
        if library_id.strip():
            clauses.append("library_id = ?")
            parameters.append(library_id.strip().lower())
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT metadata_json FROM assets WHERE {' AND '.join(clauses)}",
                parameters,
            ).fetchone()
        return _decode(row["metadata_json"], {}) if row else None

    def asset_stats(self, library_id: str = "") -> dict[str, Any]:
        where = ""
        parameters: list[Any] = []
        if library_id.strip():
            where = "WHERE library_id = ?"
            parameters.append(library_id.strip().lower())
        with self._connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) AS count FROM assets {where}",
                parameters,
            ).fetchone()["count"])
            categories = [
                {"category": row["category"], "count": int(row["count"])}
                for row in connection.execute(
                    f"""
                    SELECT category, COUNT(*) AS count FROM assets
                    {where}
                    GROUP BY category ORDER BY category
                    """,
                    parameters,
                )
            ]
            libraries = [
                {"library_id": row["library_id"], "count": int(row["count"])}
                for row in connection.execute(
                    """
                    SELECT library_id, COUNT(*) AS count FROM assets
                    GROUP BY library_id ORDER BY library_id
                    """
                )
            ]
        return {"total": total, "libraries": libraries, "categories": categories}

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

    # Explicit Rhino components -----------------------------------------






























    # Dependency-aware generation plans --------------------------------






















    # Drawing sheets: authored modelspace regions and persistent Layouts --
