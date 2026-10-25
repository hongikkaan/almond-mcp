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


class AlmondStore(ScenesStore, ComponentsStore, PlacementStore, GrasshopperStore, StructureStore):
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

    def _initialize_generation_plans(self, connection: sqlite3.Connection) -> None:
        # Keep migration and baseline snapshots atomic, including direct-store callers.
        if not connection.in_transaction:
            connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS generation_phases (
                phase_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        additions = {
            "generation_plans": {
                "phase_id": "TEXT REFERENCES generation_phases(phase_id) ON DELETE RESTRICT",
                "revision": "INTEGER NOT NULL DEFAULT 0",
            },
            "generation_plan_steps": {
                "component_refs_set": "INTEGER NOT NULL DEFAULT 0 CHECK(component_refs_set IN (0, 1))",
            },
        }
        for table, columns in additions.items():
            present = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            for column, declaration in columns.items():
                if column not in present:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        for table, field, target in (
            ("generation_plan_scenes", "scene_id", "scenes"),
            ("generation_plan_components", "component_id", "components"),
        ):
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
                    {field} TEXT NOT NULL REFERENCES {target}({field}) ON DELETE RESTRICT,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (plan_id, {field}),
                    UNIQUE (plan_id, position)
                )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS generation_step_components (
                plan_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                component_id TEXT NOT NULL REFERENCES components(component_id) ON DELETE RESTRICT,
                position INTEGER NOT NULL,
                PRIMARY KEY (plan_id, step_id, component_id),
                UNIQUE (plan_id, step_id, position),
                FOREIGN KEY (plan_id, step_id)
                    REFERENCES generation_plan_steps(plan_id, step_id) ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS generation_plan_revisions (
                plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
                revision INTEGER NOT NULL,
                operation TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (plan_id, revision)
            )
        """)
        connection.execute("""
            INSERT OR IGNORE INTO generation_plan_scenes(plan_id, scene_id, position)
            SELECT plan_id, scene_id, 0 FROM generation_plans WHERE scene_id IS NOT NULL
        """)
        legacy = connection.execute("""
            SELECT plan_id FROM generation_plans p
            WHERE NOT EXISTS (
                SELECT 1 FROM generation_plan_revisions r WHERE r.plan_id = p.plan_id
            )
        """).fetchall()
        for row in legacy:
            snapshot = self._read_generation_plan(connection, row["plan_id"])
            connection.execute("""
                INSERT INTO generation_plan_revisions
                    (plan_id, revision, operation, snapshot_json, created_at)
                VALUES (?, ?, 'migration_baseline', ?, ?)
            """, (row["plan_id"], snapshot["revision"], _json(snapshot), _utc_now()))

    @staticmethod
    def _generation_text(value: str, field: str, *, allow_empty: bool = False) -> str:
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise ValueError(f"{field} must be a {'string' if allow_empty else 'nonempty string'}.")
        return value.strip()

    @staticmethod
    def _generation_refs(values: list[str], field: str) -> list[str]:
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"{field} must be a list of nonempty strings.")
        return list(dict.fromkeys(value.strip() for value in values))

    @staticmethod
    def _generation_limit(limit: int) -> int:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer from 1 to 500.")
        return limit

    @staticmethod
    def _check_generation_revision(plan: dict, expected_revision: int | None) -> None:
        if expected_revision is None:
            return
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("expected_revision must be a nonnegative integer.")
        if expected_revision != plan["revision"]:
            raise ValueError(
                f"Plan revision conflict: expected {expected_revision}, current {plan['revision']}. "
                "Read the current plan before updating; no change was made."
            )

    @staticmethod
    def _validate_generation_refs(connection, scene_ids, component_ids, phase_id=None) -> None:
        for scene_id in scene_ids:
            if not connection.execute("SELECT 1 FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone():
                raise KeyError(f"Unknown scene_id: {scene_id}")
        for component_id in component_ids:
            row = connection.execute(
                "SELECT model_path FROM components WHERE component_id = ?", (component_id,)
            ).fetchone()
            if not row:
                raise KeyError(f"Unknown component_id: {component_id}")
            if not row["model_path"] or not row["model_path"].strip():
                raise ValueError(f"Component {component_id} has no registered model_path.")
        if phase_id and not connection.execute(
            "SELECT 1 FROM generation_phases WHERE phase_id = ?", (phase_id,)
        ).fetchone():
            raise KeyError(f"Unknown phase_id: {phase_id}")

    @staticmethod
    def _write_generation_refs(connection, plan_id, scene_ids, component_ids) -> None:
        for table, field, values in (
            ("generation_plan_scenes", "scene_id", scene_ids),
            ("generation_plan_components", "component_id", component_ids),
        ):
            connection.execute(f"DELETE FROM {table} WHERE plan_id = ?", (plan_id,))
            connection.executemany(
                f"INSERT INTO {table}(plan_id, {field}, position) VALUES (?, ?, ?)",
                [(plan_id, value, index) for index, value in enumerate(values)],
            )

    @staticmethod
    def _read_generation_phase(connection, phase_id) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT * FROM generation_phases WHERE phase_id = ?", (phase_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["plan_count"] = connection.execute(
            "SELECT COUNT(*) FROM generation_plans WHERE phase_id = ?", (phase_id,)
        ).fetchone()[0]
        return result

    def create_generation_phase(self, name: str, description: str = "") -> dict[str, Any]:
        name = self._generation_text(name, "name")
        description = self._generation_text(description, "description", allow_empty=True)
        phase_id = f"phase_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO generation_phases VALUES (?, ?, ?, ?, ?)",
                (phase_id, name, description, now, now),
            )
            result = self._read_generation_phase(connection, phase_id)
        return result

    def get_generation_phase(self, phase_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._read_generation_phase(connection, phase_id)

    def list_generation_phases(self, limit: int = 50) -> dict[str, Any]:
        limit = self._generation_limit(limit)
        with self._connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute("SELECT COUNT(*) FROM generation_phases").fetchone()[0]
            rows = connection.execute(
                "SELECT phase_id FROM generation_phases ORDER BY created_at, phase_id LIMIT ?", (limit,)
            ).fetchall()
            phases = [self._read_generation_phase(connection, row["phase_id"]) for row in rows]
        return {"phases": phases, "total": total, "limit": limit, "truncated": total > len(phases)}

    def update_generation_phase(
        self, phase_id: str, name: str | None = None, description: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._read_generation_phase(connection, phase_id)
            if not current:
                raise KeyError(f"Unknown phase_id: {phase_id}")
            name = current["name"] if name is None else self._generation_text(name, "name")
            description = current["description"] if description is None else self._generation_text(
                description, "description", allow_empty=True
            )
            if (name, description) != (current["name"], current["description"]):
                connection.execute(
                    "UPDATE generation_phases SET name = ?, description = ?, updated_at = ? WHERE phase_id = ?",
                    (name, description, _utc_now(), phase_id),
                )
            result = self._read_generation_phase(connection, phase_id)
        return result

    def _read_generation_plan(self, connection, plan_id) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT * FROM generation_plans WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        for table, field, key in (
            ("generation_plan_scenes", "scene_id", "scene_ids"),
            ("generation_plan_components", "component_id", "component_ids"),
        ):
            result[key] = [item[field] for item in connection.execute(
                f"SELECT {field} FROM {table} WHERE plan_id = ? ORDER BY position", (plan_id,)
            )]
        component_refs: dict[str, list[str]] = {}
        for item in connection.execute(
            "SELECT step_id, component_id FROM generation_step_components WHERE plan_id = ? ORDER BY position",
            (plan_id,),
        ):
            component_refs.setdefault(item["step_id"], []).append(item["component_id"])
        result["steps"] = [
            {
                "step_id": step["step_id"], "position": step["position"],
                "kind": step["kind"], "status": step["status"],
                "depends_on": _decode(step["depends_on_json"], []),
                "input_refs": _decode(step["input_refs_json"], []),
                "output_refs": _decode(step["output_refs_json"], []),
                "component_ids": component_refs.get(step["step_id"], []) if step["component_refs_set"] else None,
            }
            for step in connection.execute(
                "SELECT * FROM generation_plan_steps WHERE plan_id = ? ORDER BY position", (plan_id,)
            )
        ]
        return result

    def _record_generation_revision(self, connection, plan_id, operation) -> dict[str, Any]:
        now = _utc_now()
        connection.execute(
            "UPDATE generation_plans SET revision = revision + 1, updated_at = ? WHERE plan_id = ?",
            (now, plan_id),
        )
        snapshot = self._read_generation_plan(connection, plan_id)
        connection.execute("""
            INSERT INTO generation_plan_revisions
                (plan_id, revision, operation, snapshot_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (plan_id, snapshot["revision"], operation, _json(snapshot), now))
        return snapshot

    def create_generation_plan(
        self,
        goal: str,
        scope: str = "house",
        scene_id: str = "",
        phase_id: str = "",
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        goal = self._generation_text(goal, "goal")
        scope = self._generation_text(scope, "scope").lower()
        if scope not in {"house", "interior", "structure", "drawing", "component"}:
            raise ValueError("scope must be house, interior, structure, drawing, or component.")
        scene_id = self._generation_text(scene_id, "scene_id", allow_empty=True)
        phase_id = self._generation_text(phase_id, "phase_id", allow_empty=True)
        scene_ids = self._generation_refs(
            ([scene_id] if scene_id else []) if scene_ids is None else scene_ids, "scene_ids"
        )
        if scene_id and (not scene_ids or scene_ids[0] != scene_id):
            raise ValueError("scene_id must match the first entry of scene_ids when both are supplied.")
        component_ids = self._generation_refs([] if component_ids is None else component_ids, "component_ids")
        templates = {
            "house": [
                ("programme", "reason", []),
                ("retrieve_structural_logic", "retrieve", ["programme"]),
                ("generate_structure", "execute", ["retrieve_structural_logic"]),
                ("validate_structure", "validate", ["generate_structure"]),
                ("define_rooms", "execute", ["validate_structure"]),
                ("retrieve_assets", "retrieve", ["define_rooms"]),
                ("place_assets", "execute", ["retrieve_assets"]),
                ("validate_layout", "validate", ["place_assets"]),
                ("resolve_collisions", "resolve", ["validate_layout"]),
                ("final_validation", "validate", ["resolve_collisions"]),
            ],
            "interior": [
                ("inspect_rooms", "reason", []),
                ("retrieve_assets", "retrieve", ["inspect_rooms"]),
                ("place_assets", "execute", ["retrieve_assets"]),
                ("validate_layout", "validate", ["place_assets"]),
                ("resolve_collisions", "resolve", ["validate_layout"]),
                ("final_validation", "validate", ["resolve_collisions"]),
            ],
            "structure": [
                ("programme", "reason", []),
                ("retrieve_structural_logic", "retrieve", ["programme"]),
                ("generate_structure", "execute", ["retrieve_structural_logic"]),
                ("validate_structure", "validate", ["generate_structure"]),
            ],
            "drawing": [
                ("freeze_scene", "reason", []),
                ("retrieve_drawing_recipe", "retrieve", ["freeze_scene"]),
                ("retrieve_drawing_assets", "retrieve", ["retrieve_drawing_recipe"]),
                ("prepare_drawing_layers", "execute", ["retrieve_drawing_recipe"]),
                ("configure_projection", "execute", ["prepare_drawing_layers"]),
                ("generate_linework", "execute", ["configure_projection"]),
                ("apply_graphic_styles", "execute", ["generate_linework"]),
                ("create_layout", "execute", ["apply_graphic_styles"]),
                ("export_drawing", "execute", ["create_layout"]),
                ("validate_drawing", "validate", ["export_drawing"]),
            ],
            "component": [
                ("inspect_context", "reason", []),
                ("design", "reason", ["inspect_context"]),
                ("model", "execute", ["design"]),
                ("validate", "validate", ["model"]),
            ],
        }
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._validate_generation_refs(connection, scene_ids, component_ids, phase_id)
            connection.execute(
                """
                INSERT INTO generation_plans(
                    plan_id, scene_id, scope, goal, status, created_at, updated_at, phase_id
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (plan_id, scene_ids[0] if scene_ids else None, scope, goal, now, now, phase_id or None),
            )
            for position, (step_id, kind, dependencies) in enumerate(templates[scope]):
                connection.execute(
                    """
                    INSERT INTO generation_plan_steps(
                        plan_id, step_id, position, kind, status,
                        depends_on_json, input_refs_json, output_refs_json
                    ) VALUES (?, ?, ?, ?, 'pending', ?, '[]', '[]')
                    """,
                    (plan_id, step_id, position, kind, _json(dependencies)),
                )
            self._write_generation_refs(connection, plan_id, scene_ids, component_ids)
            result = self._record_generation_revision(connection, plan_id, "create_plan")
        return result

    def get_generation_plan(
        self, plan_id: str, revision: int | None = None,
    ) -> dict[str, Any] | None:
        """Read current state or a saved plan snapshot; snapshots contain no geometry."""
        if revision is not None and (type(revision) is not int or revision < 0):
            raise ValueError("revision must be a nonnegative integer.")
        with self._connect() as connection:
            connection.execute("BEGIN")
            if revision is None:
                return self._read_generation_plan(connection, plan_id)
            row = connection.execute(
                "SELECT snapshot_json FROM generation_plan_revisions WHERE plan_id = ? AND revision = ?",
                (plan_id, revision),
            ).fetchone()
            return _decode(row["snapshot_json"], None) if row else None

    def list_generation_plans(
        self, phase_id: str = "", scene_id: str = "", status: str = "", limit: int = 50,
    ) -> dict[str, Any]:
        limit = self._generation_limit(limit)
        clauses, arguments = [], []
        if phase_id:
            clauses.append("p.phase_id = ?")
            arguments.append(phase_id)
        if scene_id:
            clauses.append("EXISTS (SELECT 1 FROM generation_plan_scenes s WHERE s.plan_id = p.plan_id AND s.scene_id = ?)")
            arguments.append(scene_id)
        if status:
            status = self._generation_text(status, "status").lower()
            if status not in {"pending", "running", "completed", "failed", "blocked"}:
                raise ValueError("Unsupported plan status.")
            clauses.append("p.status = ?")
            arguments.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute(
                "SELECT COUNT(*) FROM generation_plans p" + where, arguments
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT p.plan_id FROM generation_plans p" + where + " ORDER BY p.updated_at DESC, p.plan_id LIMIT ?",
                [*arguments, limit],
            ).fetchall()
            plans = [self._read_generation_plan(connection, row["plan_id"]) for row in rows]
            for plan in plans:
                plan.pop("steps")
        return {"plans": plans, "total": total, "limit": limit, "truncated": total > len(plans)}

    def list_generation_plan_revisions(self, plan_id: str, limit: int = 50) -> dict[str, Any]:
        limit = self._generation_limit(limit)
        with self._connect() as connection:
            connection.execute("BEGIN")
            if not connection.execute("SELECT 1 FROM generation_plans WHERE plan_id = ?", (plan_id,)).fetchone():
                raise KeyError(f"Unknown plan_id: {plan_id}")
            total = connection.execute(
                "SELECT COUNT(*) FROM generation_plan_revisions WHERE plan_id = ?", (plan_id,)
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT revision, operation, created_at FROM generation_plan_revisions WHERE plan_id = ? ORDER BY revision DESC LIMIT ?",
                (plan_id, limit),
            ).fetchall()
        return {
            "plan_id": plan_id, "revisions": [dict(row) for row in rows],
            "total": total, "limit": limit, "truncated": total > len(rows),
        }

    def update_generation_plan(
        self, plan_id: str, goal: str | None = None, phase_id: str | None = None,
        scene_ids: list[str] | None = None, component_ids: list[str] | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            plan = self._read_generation_plan(connection, plan_id)
            if not plan:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            self._check_generation_revision(plan, expected_revision)
            goal = plan["goal"] if goal is None else self._generation_text(goal, "goal")
            phase_id = plan["phase_id"] if phase_id is None else (
                self._generation_text(phase_id, "phase_id", allow_empty=True) or None
            )
            scene_ids = plan["scene_ids"] if scene_ids is None else self._generation_refs(scene_ids, "scene_ids")
            component_ids = plan["component_ids"] if component_ids is None else self._generation_refs(component_ids, "component_ids")
            self._validate_generation_refs(connection, scene_ids, component_ids, phase_id)
            if (goal, phase_id, scene_ids, component_ids) == (
                plan["goal"], plan["phase_id"], plan["scene_ids"], plan["component_ids"]
            ):
                return plan
            connection.execute(
                "UPDATE generation_plans SET goal = ?, phase_id = ?, scene_id = ? WHERE plan_id = ?",
                (goal, phase_id, scene_ids[0] if scene_ids else None, plan_id),
            )
            self._write_generation_refs(connection, plan_id, scene_ids, component_ids)
            result = self._record_generation_revision(connection, plan_id, "update_plan")
        return result

    def update_plan_step(
        self,
        plan_id: str,
        step_id: str,
        status: str,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        component_ids: list[str] | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        status = self._generation_text(status, "status").lower()
        if status not in {"pending", "running", "completed", "failed", "blocked"}:
            raise ValueError("Unsupported step status.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            plan = self._read_generation_plan(connection, plan_id)
            if not plan:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            self._check_generation_revision(plan, expected_revision)
            step_map = {step["step_id"]: step for step in plan["steps"]}
            if step_id not in step_map:
                raise KeyError(f"Unknown step_id: {step_id}")
            step = step_map[step_id]
            if status in {"running", "completed"}:
                incomplete = [dependency for dependency in step["depends_on"]
                              if dependency not in step_map or step_map[dependency]["status"] != "completed"]
                if incomplete:
                    raise ValueError(f"Step dependencies are incomplete: {', '.join(incomplete)}")
            if status != "completed":
                descendants, pending = set(), [step_id]
                while pending:
                    parent = pending.pop()
                    for candidate in plan["steps"]:
                        identifier = candidate["step_id"]
                        if parent in candidate["depends_on"] and identifier not in descendants:
                            descendants.add(identifier)
                            pending.append(identifier)
                active = sorted(identifier for identifier in descendants
                                if step_map[identifier]["status"] in {"running", "completed"})
                if active:
                    raise ValueError(
                        "Cannot reset a prerequisite with running or completed descendants: " + ", ".join(active)
                    )
            inputs = step["input_refs"] if input_refs is None else self._generation_refs(input_refs, "input_refs")
            outputs = step["output_refs"] if output_refs is None else self._generation_refs(output_refs, "output_refs")
            components = step["component_ids"] if component_ids is None else self._generation_refs(component_ids, "component_ids")
            self._validate_generation_refs(connection, [], components or [])
            if (status, inputs, outputs, components) == (
                step["status"], step["input_refs"], step["output_refs"], step["component_ids"]
            ):
                return plan
            connection.execute(
                """
                UPDATE generation_plan_steps
                SET status = ?, input_refs_json = ?, output_refs_json = ?, component_refs_set = ?
                WHERE plan_id = ? AND step_id = ?
                """,
                (status, _json(inputs), _json(outputs), int(components is not None), plan_id, step_id),
            )
            connection.execute(
                "DELETE FROM generation_step_components WHERE plan_id = ? AND step_id = ?", (plan_id, step_id)
            )
            connection.executemany(
                "INSERT INTO generation_step_components(plan_id, step_id, component_id, position) VALUES (?, ?, ?, ?)",
                [(plan_id, step_id, component, index) for index, component in enumerate(components or [])],
            )
            statuses = [status if item["step_id"] == step_id else item["status"] for item in plan["steps"]]
            plan_status = (
                "failed" if "failed" in statuses
                else "blocked" if "blocked" in statuses
                else "completed" if all(item == "completed" for item in statuses)
                else "running" if any(item in {"running", "completed"} for item in statuses)
                else "pending"
            )
            connection.execute(
                "UPDATE generation_plans SET status = ? WHERE plan_id = ?", (plan_status, plan_id),
            )
            result = self._record_generation_revision(connection, plan_id, "update_step:" + step_id)
        return result

    def resolve_generation_targets(self, plan_id: str, step_id: str = "") -> dict[str, Any]:
        """Resolve registered component identities only; scene refs never expand targets."""
        with self._connect() as connection:
            connection.execute("BEGIN")
            plan = self._read_generation_plan(connection, plan_id)
            if not plan:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            component_ids, source = plan["component_ids"], "plan"
            if step_id:
                step = next((item for item in plan["steps"] if item["step_id"] == step_id), None)
                if step is None:
                    raise KeyError(f"Unknown step_id: {step_id}")
                if step["component_ids"] is not None:
                    component_ids, source = step["component_ids"], "step"
            self._validate_generation_refs(connection, [], component_ids)
            components = []
            for component_id in component_ids:
                registered = self._component_read(connection, component_id)
                components.append({key: registered[key] for key in (
                    "component_id", "model_path", "rhino_group_id", "name", "parent_component_id",
                    "child_component_ids", "direct_object_ids", "effective_object_ids",
                )})
        return {
            "plan_id": plan_id, "step_id": step_id or None, "revision": plan["revision"],
            "source": source, "scene_ids": plan["scene_ids"], "component_ids": component_ids,
            "components": components, "live_verified": False,
        }

    # Drawing sheets: authored modelspace regions and persistent Layouts --

    def _initialize_drawing_sheets(self, connection) -> None:
        if not connection.in_transaction:
            connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS drawing_sheets (
                sheet_id TEXT PRIMARY KEY,
                model_path TEXT NOT NULL,
                layout_id TEXT NOT NULL,
                title TEXT NOT NULL,
                drawing_type TEXT NOT NULL,
                scale_denominator REAL NOT NULL CHECK(scale_denominator > 0),
                paper_mm_json TEXT NOT NULL,
                model_bounds_mm_json TEXT NOT NULL,
                plan_id TEXT REFERENCES generation_plans(plan_id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(model_path, layout_id)
            )
        """)
        for table, field, target in (
            ("drawing_sheet_scenes", "scene_id", "scenes"),
            ("drawing_sheet_components", "component_id", "components"),
        ):
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    sheet_id TEXT NOT NULL REFERENCES drawing_sheets(sheet_id) ON DELETE CASCADE,
                    {field} TEXT NOT NULL REFERENCES {target}({field}) ON DELETE RESTRICT,
                    PRIMARY KEY(sheet_id, {field})
                )
            """)
            connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_ref ON {table}({field}, sheet_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_drawing_sheets_plan ON drawing_sheets(plan_id)")

    @staticmethod
    def _drawing_sheet_handle(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
            raise ValueError("sheet_id must be a nonempty stable handle.")
        return value

    def _drawing_sheet_metadata(self, values):
        fields = ("title", "drawing_type", "scale_denominator", "paper_mm", "model_bounds_mm",
                  "scene_ids", "component_ids", "plan_id")
        if any(field not in values for field in fields):
            raise ValueError("A drawing sheet snapshot must include all metadata fields.")
        title = self._generation_text(values["title"], "title")
        drawing_type = self._generation_text(values["drawing_type"], "drawing_type").lower()
        if drawing_type not in {"plan", "section", "elevation", "detail", "axonometric", "perspective", "schedule", "other"}:
            raise ValueError("Unsupported drawing_type.")
        scale = values["scale_denominator"]
        if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("scale_denominator must be a finite positive number.")
        paper, bounds = values["paper_mm"], values["model_bounds_mm"]
        for value, count, field in ((paper, 2, "paper_mm"), (bounds, 6, "model_bounds_mm")):
            if not isinstance(value, list) or len(value) != count or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in value
            ):
                raise ValueError(f"{field} must contain {count} finite numbers.")
        if any(value <= 0 for value in paper):
            raise ValueError("paper_mm must contain positive width and height.")
        if bounds[0] >= bounds[3] or bounds[1] >= bounds[4] or bounds[2] > bounds[5]:
            raise ValueError("model_bounds_mm must have positive world XY extents and ordered Z bounds.")
        plan_id = values["plan_id"]
        if plan_id is not None:
            plan_id = self._generation_text(plan_id, "plan_id", allow_empty=True) or None
        return dict(title=title, drawing_type=drawing_type, scale_denominator=float(scale),
                    paper_mm=[float(value) for value in paper], model_bounds_mm=[float(value) for value in bounds],
                    scene_ids=sorted(self._generation_refs(values["scene_ids"], "scene_ids")),
                    component_ids=sorted(self._generation_refs(values["component_ids"], "component_ids")), plan_id=plan_id)

    def _drawing_sheet_validate_refs(self, connection, data):
        self._validate_generation_refs(connection, data["scene_ids"], data["component_ids"])
        if data["plan_id"] and not connection.execute(
            "SELECT 1 FROM generation_plans WHERE plan_id = ?", (data["plan_id"],)
        ).fetchone():
            raise KeyError(f"Unknown plan_id: {data['plan_id']}")

    @staticmethod
    def _read_drawing_sheet(connection, sheet_id):
        row = connection.execute("SELECT * FROM drawing_sheets WHERE sheet_id = ?", (sheet_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["paper_mm"] = _decode(result.pop("paper_mm_json"), [])
        result["model_bounds_mm"] = _decode(result.pop("model_bounds_mm_json"), [])
        for table, field, key in (
            ("drawing_sheet_scenes", "scene_id", "scene_ids"),
            ("drawing_sheet_components", "component_id", "component_ids"),
        ):
            result[key] = [item[field] for item in connection.execute(
                f"SELECT {field} FROM {table} WHERE sheet_id = ? ORDER BY {field}", (sheet_id,),
            )]
        return dict(result, registration_status="registered", live_verified=False)

    def get_drawing_sheet(self, sheet_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._read_drawing_sheet(connection, sheet_id)

    def list_drawing_sheets(
        self, plan_id: str = "", scene_id: str = "", component_id: str = "",
        model_path: str = "", limit: int = 100,
    ) -> dict[str, Any]:
        limit = self._generation_limit(limit)
        clauses, arguments = [], []
        for field, value in (("plan_id", plan_id), ("model_path", model_path)):
            if value:
                clauses.append(f"s.{field} = ?")
                arguments.append(self._component_model_path(value) if field == "model_path" else value)
        for table, field, value in (
            ("drawing_sheet_scenes", "scene_id", scene_id),
            ("drawing_sheet_components", "component_id", component_id),
        ):
            if value:
                clauses.append(f"EXISTS (SELECT 1 FROM {table} r WHERE r.sheet_id = s.sheet_id AND r.{field} = ?)")
                arguments.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute("SELECT COUNT(*) FROM drawing_sheets s" + where, arguments).fetchone()[0]
            rows = connection.execute(
                "SELECT s.sheet_id FROM drawing_sheets s" + where + " ORDER BY s.title, s.sheet_id LIMIT ?",
                [*arguments, limit],
            ).fetchall()
            sheets = [self._read_drawing_sheet(connection, row["sheet_id"]) for row in rows]
        return dict(sheets=sheets, total=total, limit=limit, truncated=total > len(sheets), live_verified=False)

    @staticmethod
    def _drawing_sheet_request(action, data):
        return {"type": "drawing_sheet", "action": action, "expected_model_path": data["model_path"],
                **{key: ("" if key == "plan_id" and value is None else value) for key, value in data.items()
                   if key not in {"model_path", "created_at", "updated_at", "registration_status", "live_verified"}}}

    @staticmethod
    def _drawing_sheet_matches_expected(data, expected):
        """Compare Rhino-measured numbers with rounding tolerance; IDs and labels remain exact."""
        def same_number(left, right):
            return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-6)

        for key, value in expected.items():
            actual = data[key]
            if key == "scale_denominator":
                if not same_number(actual, value):
                    return False
            elif key in {"paper_mm", "model_bounds_mm"}:
                if len(actual) != len(value) or any(
                    not same_number(left, right) for left, right in zip(actual, value)
                ):
                    return False
            elif actual != value:
                return False
        return True

    def _drawing_sheet_check_unregistered_proof(self, observed, sheet_id, model_path, layout_id):
        if (not isinstance(observed, dict) or observed.get("complete") is not True
                or observed.get("truncated") or observed.get("registration_status") != "unregistered"
                or observed.get("sheet_id") != sheet_id
                or self._component_model_path(observed.get("model_path")) != model_path
                or self._component_guid(observed.get("layout_id")) != layout_id):
            raise ValueError("Native unregistered Layout proof does not match the drawing sheet.")

    def _drawing_sheet_store_snapshot(self, connection, observed, model_path, sheet_id, layout_id="", expected=None):
        if not isinstance(observed, dict) or observed.get("complete") is not True or observed.get("truncated"):
            raise ValueError("Native drawing sheet snapshot must be complete and untruncated.")
        if observed.get("registration_status", "registered") != "registered":
            raise ValueError("Native Layout is not registered as a drawing sheet.")
        actual_layout = self._component_guid(observed.get("layout_id"))
        if (observed.get("sheet_id") != sheet_id
                or self._component_model_path(observed.get("model_path")) != model_path
                or (layout_id and actual_layout != layout_id)):
            raise ValueError("Native drawing sheet identity does not match the request.")
        data = self._drawing_sheet_metadata(observed)
        self._drawing_sheet_validate_refs(connection, data)
        if expected is not None and not self._drawing_sheet_matches_expected(data, expected):
            raise ValueError("Native drawing sheet metadata differs from the requested values.")
        existing = self._read_drawing_sheet(connection, sheet_id)
        if existing and (existing["model_path"] != model_path or existing["layout_id"] != actual_layout):
            raise ValueError("A drawing sheet cannot be rebound to another model or Layout.")
        owner = connection.execute(
            "SELECT sheet_id FROM drawing_sheets WHERE model_path = ? AND layout_id = ?", (model_path, actual_layout),
        ).fetchone()
        if owner and owner["sheet_id"] != sheet_id:
            raise ValueError("The Layout is already registered as another drawing sheet.")
        now = _utc_now()
        connection.execute("""
            INSERT INTO drawing_sheets(sheet_id, model_path, layout_id, title, drawing_type,
                scale_denominator, paper_mm_json, model_bounds_mm_json, plan_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sheet_id) DO UPDATE SET title = excluded.title, drawing_type = excluded.drawing_type,
                scale_denominator = excluded.scale_denominator, paper_mm_json = excluded.paper_mm_json,
                model_bounds_mm_json = excluded.model_bounds_mm_json, plan_id = excluded.plan_id,
                updated_at = excluded.updated_at
        """, (sheet_id, model_path, actual_layout, data["title"], data["drawing_type"], data["scale_denominator"],
              _json(data["paper_mm"]), _json(data["model_bounds_mm"]), data["plan_id"], now, now))
        for table, field, key in (
            ("drawing_sheet_scenes", "scene_id", "scene_ids"),
            ("drawing_sheet_components", "component_id", "component_ids"),
        ):
            connection.execute(f"DELETE FROM {table} WHERE sheet_id = ?", (sheet_id,))
            connection.executemany(f"INSERT INTO {table}(sheet_id, {field}) VALUES (?, ?)",
                                   [(sheet_id, value) for value in data[key]])
        return dict(self._read_drawing_sheet(connection, sheet_id), live_verified=True)

    def upsert_drawing_sheet(
        self, model_path: str, title: str, drawing_type: str, scale_denominator: float,
        paper_mm: list[float], model_bounds_mm: list[float], scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None, plan_id: str | None = None,
        sheet_id: str = "", layout_id: str = "", native_apply: Callable | None = None,
    ) -> dict[str, Any]:
        model_path = self._component_model_path(model_path)
        sheet_id = self._drawing_sheet_handle(sheet_id or f"sheet_{uuid.uuid4().hex[:12]}")
        layout_id = self._component_guid(layout_id) if layout_id else ""
        if not callable(native_apply):
            raise ValueError("Native Layout creation/update is required.")
        attempted = False
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = self._read_drawing_sheet(connection, sheet_id)
                if existing:
                    if existing["model_path"] != model_path or (layout_id and existing["layout_id"] != layout_id):
                        raise ValueError("A drawing sheet cannot be rebound to another model or Layout.")
                    layout_id = existing["layout_id"]
                if layout_id:
                    owner = connection.execute(
                        "SELECT sheet_id FROM drawing_sheets WHERE model_path = ? AND layout_id = ?", (model_path, layout_id),
                    ).fetchone()
                    if owner and owner["sheet_id"] != sheet_id:
                        raise ValueError("The Layout is already registered as another drawing sheet.")
                data = self._drawing_sheet_metadata(dict(
                    title=title, drawing_type=drawing_type, scale_denominator=scale_denominator,
                    paper_mm=paper_mm, model_bounds_mm=model_bounds_mm,
                    scene_ids=scene_ids if scene_ids is not None else (existing["scene_ids"] if existing else []),
                    component_ids=component_ids if component_ids is not None else (existing["component_ids"] if existing else []),
                    plan_id=plan_id if plan_id is not None else (existing["plan_id"] if existing else None),
                ))
                self._drawing_sheet_validate_refs(connection, data)
                request = self._drawing_sheet_request("upsert", dict(data, sheet_id=sheet_id, model_path=model_path, layout_id=layout_id))
                attempted = True
                reply = self._component_native(native_apply, request)
                result = self._drawing_sheet_store_snapshot(
                    connection, reply.get("sheet"), model_path, sheet_id, layout_id, expected=data,
                )
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise DrawingSheetReconciliationError(sheet_id, model_path, str(exc)) from exc
            raise
        return result

    def sync_drawing_sheet(
        self, model_path: str, sheet_id: str, layout_id: str = "", native_inspect: Callable | None = None,
    ) -> dict[str, Any]:
        model_path = self._component_model_path(model_path)
        sheet_id = self._drawing_sheet_handle(sheet_id)
        layout_id = self._component_guid(layout_id) if layout_id else ""
        if not callable(native_inspect):
            raise ValueError("Native read-only Layout inspection is required.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._read_drawing_sheet(connection, sheet_id)
            if existing:
                if existing["model_path"] != model_path or (layout_id and existing["layout_id"] != layout_id):
                    raise ValueError("A drawing sheet cannot be rebound to another model or Layout.")
                layout_id = existing["layout_id"]
            request = dict(type="drawing_sheet", action="inspect", expected_model_path=model_path,
                           sheet_id=sheet_id, layout_id=layout_id)
            if existing:
                request["expected_sheet"] = {key: ("" if key == "plan_id" and value is None else value)
                                             for key, value in existing.items()
                                             if key not in {"created_at", "updated_at", "registration_status", "live_verified"}}
            reply = self._component_native(native_inspect, request)
            observed = reply.get("sheet")
            if isinstance(observed, dict) and observed.get("registration_status") == "unregistered":
                if existing is None:
                    raise ValueError("Unregistered Layout proof does not match an existing drawing sheet.")
                self._drawing_sheet_check_unregistered_proof(observed, sheet_id, model_path, layout_id)
                connection.execute("DELETE FROM drawing_sheets WHERE sheet_id = ?", (sheet_id,))
                result = dict(sheet_id=sheet_id, model_path=model_path, layout_id=layout_id,
                              registration_status="unregistered", live_verified=True)
            else:
                result = self._drawing_sheet_store_snapshot(connection, observed, model_path, sheet_id, layout_id)
        return result

    def remove_drawing_sheet(self, sheet_id: str, native_apply: Callable | None = None) -> dict[str, Any]:
        if not callable(native_apply):
            raise ValueError("Native drawing sheet unregistration is required.")
        attempted, model_path = False, ""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = self._read_drawing_sheet(connection, sheet_id)
                if existing is None:
                    raise KeyError(f"Unknown sheet_id: {sheet_id}")
                model_path = existing["model_path"]
                attempted = True
                reply = self._component_native(native_apply, self._drawing_sheet_request("unregister", existing))
                # Native unregister deliberately returns a compact top-level identity
                # acknowledgement. Only the read-only inspect path carries a full
                # nested unregistered snapshot with complete/status proof.
                if (reply.get("sheet_id") != sheet_id
                        or self._component_model_path(reply.get("model_path")) != model_path
                        or self._component_guid(reply.get("layout_id")) != existing["layout_id"]):
                    raise ValueError("Native unregistration acknowledgement does not match the drawing sheet.")
                connection.execute("DELETE FROM drawing_sheets WHERE sheet_id = ?", (sheet_id,))
                result = dict(sheet_id=sheet_id, model_path=model_path, layout_id=existing["layout_id"],
                              registration_status="unregistered", live_verified=True)
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise DrawingSheetReconciliationError(sheet_id, model_path, str(exc)) from exc
            raise
        return result

