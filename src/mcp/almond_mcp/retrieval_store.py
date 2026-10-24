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

# Assets dropped from their manifest but still placed in a recorded scene.
RETIRED_LIBRARY_ID = "retired"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


class ComponentReconciliationError(RuntimeError):
    """Rhino may have changed although the ledger transaction did not finish."""

    def __init__(self, component_id: str, model_path: str, message: str):
        super().__init__(
            f"{message} Inspect and reconcile component {component_id}; do not automatically retry."
        )
        self.component_id = component_id
        self.model_path = model_path
        self.requires_reconciliation = True


class DrawingSheetReconciliationError(RuntimeError):
    """A Layout operation may have succeeded while its ledger transaction failed."""

    def __init__(self, sheet_id: str, model_path: str, message: str):
        super().__init__(f"{message} Inspect and sync drawing sheet {sheet_id}; do not automatically retry.")
        self.sheet_id = sheet_id
        self.model_path = model_path


class _NativeRejected(ValueError):
    """A native response explicitly certifies no change or a verified rollback."""


class AlmondStore:
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

    def sync_capsules(self, manifests: list[dict[str, Any]]) -> int:
        """Upsert capsule manifests and prune capsules absent from the batch."""
        now = _utc_now()
        seen: list[str] = []
        with self._connect() as connection:
            for manifest in manifests:
                if not isinstance(manifest, dict):
                    raise ValueError("Each capsule manifest must be a dict.")
                missing = [
                    key
                    for key in ("capsule_id", "capability", "definition_file",
                                "inputs", "outputs", "audited")
                    if key not in manifest
                ]
                if missing:
                    raise ValueError(
                        f"Capsule manifest is missing keys: {', '.join(missing)}"
                    )
                capsule_id = str(manifest["capsule_id"]).strip()
                if not capsule_id:
                    raise ValueError("capsule_id must be a non-empty string.")
                connection.execute(
                    """
                    INSERT INTO capsules (
                        capsule_id, capability, definition_file, audited,
                        title, manifest_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(capsule_id) DO UPDATE SET
                        capability = excluded.capability,
                        definition_file = excluded.definition_file,
                        audited = excluded.audited,
                        title = excluded.title,
                        manifest_json = excluded.manifest_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        capsule_id,
                        str(manifest["capability"]).strip().lower(),
                        str(manifest["definition_file"]).strip(),
                        int(bool(manifest["audited"])),
                        str(manifest.get("title", "")).strip(),
                        _json(manifest),
                        now,
                    ),
                )
                seen.append(capsule_id)

            if seen:
                placeholders = ",".join("?" for _ in seen)
                connection.execute(
                    f"DELETE FROM capsules WHERE capsule_id NOT IN ({placeholders})",
                    seen,
                )
            else:
                connection.execute("DELETE FROM capsules")
        return len(seen)

    @staticmethod
    def compact_capsule(manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            "capsule_id": manifest.get("capsule_id"),
            "capability": manifest.get("capability"),
            "structure_type": manifest.get("structure_type"),
            "definition_file": manifest.get("definition_file"),
            "title": manifest.get("title", ""),
            "audited": bool(manifest.get("audited")),
            "inputs": [port.get("name") for port in manifest.get("inputs", [])],
            "outputs": [port.get("name") for port in manifest.get("outputs", [])],
        }

    def search_capsules(
        self,
        query: str = "",
        capability: str = "",
        audited_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))
        clauses: list[str] = []
        parameters: list[Any] = []

        if capability.strip():
            clauses.append("capability = ?")
            parameters.append(capability.strip().lower())
        if audited_only:
            clauses.append("audited = 1")
        tokens = re.findall(r"[\w-]+", query.lower(), flags=re.UNICODE)
        for token in tokens[:12]:
            clauses.append(
                "(LOWER(capsule_id) LIKE ? OR LOWER(title) LIKE ? "
                "OR LOWER(definition_file) LIKE ? OR LOWER(manifest_json) LIKE ?)"
            )
            pattern = f"%{token}%"
            parameters.extend([pattern, pattern, pattern, pattern])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) AS count FROM capsules {where}",
                parameters,
            ).fetchone()["count"])
            rows = connection.execute(
                f"""
                SELECT manifest_json FROM capsules
                {where}
                ORDER BY audited DESC, capsule_id
                LIMIT ? OFFSET ?
                """,
                [*parameters, limit, offset],
            ).fetchall()
        capsules = [
            self.compact_capsule(_decode(row["manifest_json"], {}))
            for row in rows
        ]
        next_offset = offset + len(capsules)
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "capsules": capsules,
        }

    def get_capsule(self, capsule_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM capsules WHERE capsule_id = ?",
                (capsule_id.strip(),),
            ).fetchone()
        return _decode(row["manifest_json"], {}) if row else None

    # Scene ledger -------------------------------------------------------

    def create_scene(self, name: str, units: str = "mm") -> dict[str, Any]:
        units = units.lower().strip()
        if units not in {"mm", "cm", "m", "in", "ft"}:
            raise ValueError("units must be mm, cm, m, in, or ft.")
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scenes(scene_id, name, units, revision, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (scene_id, name.strip() or "Untitled scene", units, now, now),
            )
        return self.get_scene(scene_id)

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            scene = connection.execute(
                "SELECT * FROM scenes WHERE scene_id = ?",
                (scene_id,),
            ).fetchone()
            if not scene:
                return None
            room_count = int(connection.execute(
                "SELECT COUNT(*) AS count FROM rooms WHERE scene_id = ?",
                (scene_id,),
            ).fetchone()["count"])
            instance_count = int(connection.execute(
                "SELECT COUNT(*) AS count FROM instances WHERE scene_id = ?",
                (scene_id,),
            ).fetchone()["count"])
            component_count = connection.execute(
                "SELECT COUNT(*) FROM scene_components WHERE scene_id = ?", (scene_id,)
            ).fetchone()[0]
            direct_object_count = connection.execute(
                "SELECT COUNT(*) FROM scene_objects WHERE scene_id = ?", (scene_id,)
            ).fetchone()[0]
            object_count = connection.execute(
                """
                WITH RECURSIVE linked_components(component_id) AS (
                    SELECT component_id FROM scene_components WHERE scene_id = ?
                    UNION
                    SELECT c.component_id FROM components c
                        JOIN linked_components parent ON c.parent_component_id = parent.component_id
                )
                SELECT COUNT(*) FROM document_objects o
                WHERE EXISTS(SELECT 1 FROM scene_objects so WHERE so.scene_id = ? AND so.object_rowid = o.id)
                   OR EXISTS(SELECT 1 FROM linked_components lc WHERE lc.component_id = o.component_id)
                """, (scene_id, scene_id),
            ).fetchone()[0]
        return {
            "scene_id": scene["scene_id"],
            "name": scene["name"],
            "units": scene["units"],
            "revision": int(scene["revision"]),
            "rooms": room_count,
            "instances": instance_count,
            "components": component_count,
            "direct_objects": direct_object_count,
            "objects": object_count,
            "live_verified": False,
            "updated_at": scene["updated_at"],
        }

    def upsert_room(
        self,
        scene_id: str,
        name: str,
        bounds_mm: list[float],
        room_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if len(bounds_mm) != 6:
            raise ValueError("bounds_mm must be [min_x, min_y, min_z, max_x, max_y, max_z].")
        values = [float(value) for value in bounds_mm]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Room bounds must be finite.")
        min_x, min_y, min_z, max_x, max_y, max_z = values
        if min_x >= max_x or min_y >= max_y or min_z >= max_z:
            raise ValueError("Room bounds must have positive volume.")
        if not self.get_scene(scene_id):
            raise KeyError(f"Unknown scene_id: {scene_id}")
        room_id = room_id.strip()
        if not room_id:
            # True upsert semantics: an omitted room_id matches an existing
            # room of the same name instead of minting a duplicate.
            with self._connect() as connection:
                existing = connection.execute(
                    "SELECT room_id FROM rooms WHERE scene_id = ? AND name = ?",
                    (scene_id, name.strip() or ""),
                ).fetchone()
            room_id = existing["room_id"] if existing else f"room_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        patch = {
            "room_id": room_id,
            "name": name,
            "bounds_mm": values,
        }
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            owner = connection.execute(
                "SELECT scene_id FROM rooms WHERE room_id = ?", (room_id,)
            ).fetchone()
            if owner and owner["scene_id"] != scene_id:
                raise ValueError("room_id already belongs to another scene.")
            connection.execute(
                """
                INSERT INTO rooms(
                    room_id, scene_id, name,
                    min_x, max_x, min_y, max_y, min_z, max_z,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(room_id) DO UPDATE SET
                    name = excluded.name,
                    min_x = excluded.min_x,
                    max_x = excluded.max_x,
                    min_y = excluded.min_y,
                    max_y = excluded.max_y,
                    min_z = excluded.min_z,
                    max_z = excluded.max_z,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    room_id, scene_id, name.strip() or room_id,
                    min_x, max_x, min_y, max_y, min_z, max_z,
                    _json(metadata or {}), now, now,
                ),
            )
            revision = self._record_revision(
                connection, scene_id, "upsert_room", patch
            )
        return {"room_id": room_id, "scene_id": scene_id, "revision": revision}

    def upsert_instance(
        self,
        scene_id: str,
        asset_id: str,
        x_mm: float,
        y_mm: float,
        z_mm: float | None = None,
        rotation_degrees: float = 0,
        scale: float = 1,
        room_id: str = "",
        instance_id: str = "",
        locked: bool = False,
        rhino_guid: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.get_scene(scene_id):
            raise KeyError(f"Unknown scene_id: {scene_id}")
        asset = self.get_asset(asset_id)
        if not asset:
            raise KeyError(f"Unknown asset_id: {asset_id}")
        room_floor_z = 0.0
        if room_id:
            with self._connect() as connection:
                room = connection.execute(
                    "SELECT scene_id, min_z FROM rooms WHERE room_id = ?",
                    (room_id,),
                ).fetchone()
            if not room or room["scene_id"] != scene_id:
                raise KeyError("room_id does not belong to the scene.")
            room_floor_z = float(room["min_z"])
        # An omitted z means "standing on the floor of its room" - rooms may
        # sit at storey elevation (e.g. an office floor at z=18000).
        if z_mm is None:
            z_mm = room_floor_z
        numeric = [x_mm, y_mm, z_mm, rotation_degrees, scale]
        if not all(math.isfinite(float(value)) for value in numeric):
            raise ValueError("Instance transform values must be finite.")
        if scale <= 0:
            raise ValueError("scale must be greater than zero.")

        instance_id = instance_id.strip() or f"instance_{uuid.uuid4().hex[:12]}"
        bounds = self._world_aabb(
            asset,
            float(x_mm),
            float(y_mm),
            float(z_mm),
            float(rotation_degrees),
            float(scale),
        )
        now = _utc_now()
        patch = {
            "instance_id": instance_id,
            "asset_id": asset_id,
            "room_id": room_id or None,
            "transform": [x_mm, y_mm, z_mm, rotation_degrees, scale],
            "locked": bool(locked),
        }
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            owner = connection.execute(
                "SELECT scene_id FROM instances WHERE instance_id = ?", (instance_id,)
            ).fetchone()
            if owner and owner["scene_id"] != scene_id:
                raise ValueError("instance_id already belongs to another scene.")
            connection.execute(
                """
                INSERT INTO instances(
                    instance_id, scene_id, room_id, asset_id, rhino_guid,
                    x_mm, y_mm, z_mm, rotation_degrees, scale, locked,
                    min_x, max_x, min_y, max_y, min_z, max_z,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    room_id = excluded.room_id,
                    asset_id = excluded.asset_id,
                    rhino_guid = excluded.rhino_guid,
                    x_mm = excluded.x_mm,
                    y_mm = excluded.y_mm,
                    z_mm = excluded.z_mm,
                    rotation_degrees = excluded.rotation_degrees,
                    scale = excluded.scale,
                    locked = excluded.locked,
                    min_x = excluded.min_x,
                    max_x = excluded.max_x,
                    min_y = excluded.min_y,
                    max_y = excluded.max_y,
                    min_z = excluded.min_z,
                    max_z = excluded.max_z,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    instance_id, scene_id, room_id or None, asset_id,
                    rhino_guid or None,
                    float(x_mm), float(y_mm), float(z_mm),
                    float(rotation_degrees), float(scale), int(bool(locked)),
                    *bounds, _json(metadata or {}), now, now,
                ),
            )
            row = connection.execute(
                "SELECT id FROM instances WHERE instance_id = ?",
                (instance_id,),
            ).fetchone()
            connection.execute(
                "DELETE FROM instance_rtree WHERE instance_rowid = ?",
                (row["id"],),
            )
            connection.execute(
                """
                INSERT INTO instance_rtree(
                    instance_rowid, min_x, max_x, min_y, max_y, min_z, max_z
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (row["id"], *bounds),
            )
            revision = self._record_revision(
                connection, scene_id, "upsert_instance", patch
            )
        return {
            "instance_id": instance_id,
            "scene_id": scene_id,
            "asset_id": asset_id,
            "world_aabb_mm": {
                "min": [bounds[0], bounds[2], bounds[4]],
                "max": [bounds[1], bounds[3], bounds[5]],
            },
            "revision": revision,
        }

    @staticmethod
    def _world_aabb(
        asset: dict[str, Any],
        x: float,
        y: float,
        z: float,
        rotation_degrees: float,
        scale: float,
    ) -> tuple[float, float, float, float, float, float]:
        dimensions = asset.get("dimensions_mm", {})
        width = float(dimensions.get("width", 0))
        depth = float(dimensions.get("depth", 0))
        height = float(dimensions.get("height", 0))
        bounds = asset.get("spatial", {}).get("local_aabb", {})
        minimum = bounds.get("min", [-width / 2, -depth / 2, 0])
        maximum = bounds.get("max", [width / 2, depth / 2, height])
        angle = math.radians(rotation_degrees)
        cosine = math.cos(angle)
        sine = math.sin(angle)
        world_xy = []
        for local_x in (float(minimum[0]), float(maximum[0])):
            for local_y in (float(minimum[1]), float(maximum[1])):
                scaled_x = local_x * scale
                scaled_y = local_y * scale
                world_xy.append((
                    x + scaled_x * cosine - scaled_y * sine,
                    y + scaled_x * sine + scaled_y * cosine,
                ))
        return (
            min(point[0] for point in world_xy),
            max(point[0] for point in world_xy),
            min(point[1] for point in world_xy),
            max(point[1] for point in world_xy),
            z + float(minimum[2]) * scale,
            z + float(maximum[2]) * scale,
        )

    # Structural validation history ---------------------------------------

    def record_validation_run(
        self,
        request: dict[str, Any],
        result: dict[str, Any],
        guids: list[str],
    ) -> int:
        """Persists one validate_structure run for later report export."""
        results = result.get("results") or {}
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO validation_runs(
                    ran_at, structure_type, material, load_kn, member_count,
                    analysis_method, confidence, passed, span_m,
                    max_deflection_mm, deflection_limit_mm, utilization_ratio,
                    max_stress_mpa, yield_stress_mpa, reactions_kn,
                    verdict, warnings_json, guids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(),
                    str(request.get("structure_type", "beam")),
                    str(request.get("material", "Steel")),
                    float(request.get("load_kn", 10.0)),
                    len(guids),
                    str(results.get("analysis_method", "unknown")),
                    str(result.get("confidence", "unknown")),
                    1 if result.get("passed") else 0,
                    float(results.get("span_m", 0.0) or 0.0),
                    float(results.get("max_deflection_mm", 0.0) or 0.0),
                    float(results.get("deflection_limit_mm", 0.0) or 0.0),
                    float(results.get("utilization_ratio", 0.0) or 0.0),
                    float(results.get("max_stress_mpa", 0.0) or 0.0),
                    float(results.get("yield_stress_mpa", 0.0) or 0.0),
                    float(results.get("reactions_kn", 0.0) or 0.0),
                    str(result.get("verdict", "")),
                    _json(result.get("warnings") or []),
                    _json(list(guids)),
                ),
            )
            return int(cursor.lastrowid)

    def list_validation_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM validation_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        runs = []
        for row in rows:
            run = {key: row[key] for key in row.keys()}
            run["passed"] = bool(run["passed"])
            run["warnings"] = json.loads(run.pop("warnings_json") or "[]")
            run["guids"] = json.loads(run.pop("guids_json") or "[]")
            runs.append(run)
        return runs

    def remove_instance(self, scene_id: str, instance_id: str) -> dict[str, Any]:
        if not self.get_scene(scene_id):
            raise KeyError(f"Unknown scene_id: {scene_id}")
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM instances WHERE scene_id = ? AND instance_id = ?",
                (scene_id, instance_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Unknown instance_id: {instance_id}")
            revision = self._record_revision(
                connection, scene_id, "remove_instance", {"instance_id": instance_id}
            )
        return {"instance_id": instance_id, "scene_id": scene_id, "revision": revision}

    def remove_room(self, scene_id: str, room_id: str) -> dict[str, Any]:
        """Deletes a room; its instances stay in the scene, orphaned."""
        if not self.get_scene(scene_id):
            raise KeyError(f"Unknown scene_id: {scene_id}")
        with self._connect() as connection:
            orphaned = connection.execute(
                "UPDATE instances SET room_id = NULL WHERE scene_id = ? AND room_id = ?",
                (scene_id, room_id),
            ).rowcount
            cursor = connection.execute(
                "DELETE FROM rooms WHERE scene_id = ? AND room_id = ?",
                (scene_id, room_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Unknown room_id: {room_id}")
            revision = self._record_revision(
                connection, scene_id, "remove_room",
                {"room_id": room_id, "orphaned_instances": orphaned},
            )
        return {
            "room_id": room_id,
            "scene_id": scene_id,
            "orphaned_instances": orphaned,
            "revision": revision,
        }

    def scene_instances(self, scene_id: str) -> list[dict[str, Any]]:
        """Every instance of a scene with its world bounding box (mm), for structural loads."""
        with self._connect() as conn:
            if not conn.execute("SELECT 1 FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone():
                raise KeyError(f"Unknown scene_id: {scene_id}")
            rows = conn.execute(
                """
                SELECT instance_id, asset_id, rhino_guid, scale, min_x, max_x, min_y, max_y, min_z, max_z
                FROM instances WHERE scene_id = ? ORDER BY instance_id
                """,
                (scene_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def validate_scene(self, scene_id: str, limit: int = 100) -> dict[str, Any]:
        scene = self.get_scene(scene_id)
        if not scene:
            raise KeyError(f"Unknown scene_id: {scene_id}")
        limit = max(1, min(int(limit), 500))
        with self._connect() as connection:
            collision_rows = connection.execute(
                """
                SELECT
                    ia.instance_id AS a,
                    ib.instance_id AS b,
                    ia.asset_id AS asset_a,
                    ib.asset_id AS asset_b
                FROM instance_rtree ra
                JOIN instance_rtree rb ON ra.instance_rowid < rb.instance_rowid
                    AND ra.min_x < rb.max_x AND ra.max_x > rb.min_x
                    AND ra.min_y < rb.max_y AND ra.max_y > rb.min_y
                    AND ra.min_z < rb.max_z AND ra.max_z > rb.min_z
                JOIN instances ia ON ia.id = ra.instance_rowid
                JOIN instances ib ON ib.id = rb.instance_rowid
                WHERE ia.scene_id = ? AND ib.scene_id = ?
                ORDER BY ia.instance_id, ib.instance_id
                LIMIT ?
                """,
                (scene_id, scene_id, limit),
            ).fetchall()
            outside_rows = connection.execute(
                """
                SELECT i.instance_id, i.room_id,
                    i.min_x < r.min_x OR i.max_x > r.max_x AS out_x,
                    i.min_y < r.min_y OR i.max_y > r.max_y AS out_y,
                    i.min_z < r.min_z OR i.max_z > r.max_z AS out_z
                FROM instances i
                JOIN rooms r ON r.room_id = i.room_id
                WHERE i.scene_id = ?
                  AND (
                    i.min_x < r.min_x OR i.max_x > r.max_x OR
                    i.min_y < r.min_y OR i.max_y > r.max_y OR
                    i.min_z < r.min_z OR i.max_z > r.max_z
                  )
                ORDER BY i.instance_id
                LIMIT ?
                """,
                (scene_id, limit),
            ).fetchall()
        collisions = [
            {
                "instances": [row["a"], row["b"]],
                "assets": [row["asset_a"], row["asset_b"]],
                "kind": "physical_aabb",
            }
            for row in collision_rows
        ]
        outside = [
            {
                "instance_id": row["instance_id"],
                "room_id": row["room_id"],
                "failing_axes": [
                    axis for axis, flag in
                    (("x", row["out_x"]), ("y", row["out_y"]), ("z", row["out_z"]))
                    if flag
                ],
            }
            for row in outside_rows
        ]
        return {
            "scene_id": scene_id,
            "passed": not collisions and not outside,
            "collision_count": len(collisions),
            "outside_room_count": len(outside),
            "collisions": collisions,
            "outside_room": outside,
            "method": "rtree_world_aabb_broad_phase",
            "passed_scope": "legacy_asset_instances",
            "live_verified": False,
            "coverage": {
                "asset_instances": scene["instances"],
                "registered_objects": scene["objects"],
                "registered_object_collisions_checked": False,
                "room_containment": "instances_with_assigned_room",
            },
        }

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

    @staticmethod
    def _component_model_path(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("An absolute saved model_path is required.")
        value = value.strip()
        if ntpath.splitdrive(value)[0]:
            if not ntpath.isabs(value):
                raise ValueError("model_path must be absolute.")
            value = ntpath.normcase(ntpath.normpath(value))
        elif os.path.isabs(value):
            value = os.path.normcase(os.path.normpath(value))
        else:
            raise ValueError("model_path must be absolute.")
        if not value.lower().endswith(".3dm"):
            raise ValueError("model_path must identify a saved .3dm document.")
        return value

    @staticmethod
    def _component_handle(value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
            raise ValueError("component_id must be a nonempty stable handle.")
        return value

    @staticmethod
    def _component_guid(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Rhino object/group IDs must be GUID strings.")
        try:
            result = uuid.UUID(value)
        except (ValueError, AttributeError) as exc:
            raise ValueError("Rhino object/group IDs must be GUID strings.") from exc
        if result.int == 0:
            raise ValueError("An empty Rhino GUID is not an object or group.")
        return str(result)

    @classmethod
    def _component_object_ids(cls, values: list[str]) -> list[str]:
        if not isinstance(values, (list, tuple)):
            raise ValueError("object_ids must be a list of GUID strings.")
        result = [cls._component_guid(value) for value in values]
        if len(set(result)) != len(result):
            raise ValueError("object_ids must not contain duplicate GUIDs.")
        return sorted(result)

    @staticmethod
    def _component_scene_ids(connection, values: list[str]) -> list[str]:
        if not isinstance(values, (list, tuple)) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError("scene_ids must be a list of existing scene handles.")
        result = [value.strip() for value in values]
        if len(set(result)) != len(result):
            raise ValueError("scene_ids must not contain duplicates.")
        for scene_id in result:
            if not connection.execute(
                "SELECT 1 FROM scenes WHERE scene_id = ?", (scene_id,)
            ).fetchone():
                raise KeyError(f"Unknown scene_id: {scene_id}")
        return sorted(result)

    @staticmethod
    def _component_native(callback: Callable, request: dict[str, Any]) -> dict[str, Any]:
        reply = callback(request)
        if not isinstance(reply, dict):
            raise ValueError("Native component response must be a JSON object.")
        if reply.get("status") != "success":
            message = str(reply.get("message") or "Native component operation failed.")
            if reply.get("mutation_applied") is False or reply.get("rolled_back") is True:
                raise _NativeRejected(message)
            raise ValueError(message)
        return reply

    @classmethod
    def _component_observed_objects(
        cls, snapshot: dict[str, Any], expected_ids: list[str] | None = None,
        owner: str | None = None,
    ) -> list[dict[str, Any]]:
        if snapshot.get("truncated") or snapshot.get("complete") is not True:
            raise ValueError("Native object observation must be complete and untruncated.")
        values = snapshot.get("objects")
        if not isinstance(values, list):
            raise ValueError("Native snapshot must contain an objects list.")
        rows = []
        for value in values:
            if not isinstance(value, dict):
                raise ValueError("Native object rows must be JSON objects.")
            guid = cls._component_guid(value.get("rhino_guid"))
            object_type = value.get("object_type")
            bounds = value.get("bounds_mm")
            if not isinstance(object_type, str) or not object_type.strip():
                raise ValueError("Native objects must report object_type.")
            if not isinstance(bounds, list) or len(bounds) != 6 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in bounds
            ):
                raise ValueError("Native bounds_mm must contain six finite numbers.")
            if any(bounds[i] > bounds[i + 3] for i in range(3)):
                raise ValueError("Native bounds_mm minima must not exceed maxima.")
            if owner is not None and value.get("component_id") != owner:
                raise ValueError(f"Native component ownership was not verified for {guid}.")
            rows.append(dict(value, rhino_guid=guid, object_type=object_type.strip(),
                             bounds_mm=[float(v) for v in bounds]))
        ids = [row["rhino_guid"] for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("Native snapshot contains duplicate Rhino objects.")
        if expected_ids is not None and set(ids) != set(expected_ids):
            raise ValueError("Native snapshot does not match the requested object set.")
        return sorted(rows, key=lambda row: row["rhino_guid"])

    @staticmethod
    def _component_check_owners(connection, model_path, object_ids, component_id):
        wanted = set(object_ids)
        for row in connection.execute(
            "SELECT rhino_guid, component_id FROM document_objects "
            "WHERE model_path = ? AND component_id IS NOT NULL", (model_path,)
        ):
            if row["rhino_guid"] in wanted and row["component_id"] != component_id:
                raise ValueError(
                    f"Object {row['rhino_guid']} already belongs to component "
                    f"{row['component_id']}; no registration was changed."
                )

    @staticmethod
    def _component_cache_objects(connection, model_path, objects):
        now = _utc_now()
        for obj in objects:
            low_x, low_y, low_z, high_x, high_y, high_z = obj["bounds_mm"]
            connection.execute(
                """
                INSERT INTO document_objects(
                    model_path, rhino_guid, object_type,
                    min_x, max_x, min_y, max_y, min_z, max_z, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_path, rhino_guid) DO UPDATE SET
                    object_type = excluded.object_type,
                    min_x = excluded.min_x, max_x = excluded.max_x,
                    min_y = excluded.min_y, max_y = excluded.max_y,
                    min_z = excluded.min_z, max_z = excluded.max_z,
                    observed_at = excluded.observed_at
                """,
                (model_path, obj["rhino_guid"], obj["object_type"],
                 low_x, high_x, low_y, high_y, low_z, high_z, now),
            )

    @staticmethod
    def _component_affected_scenes(connection, model_path, object_ids):
        wanted = set(object_ids)
        result = set()
        for row in connection.execute(
            """
            WITH RECURSIVE owners(rhino_guid, component_id) AS (
                SELECT rhino_guid, component_id FROM document_objects
                    WHERE model_path = ? AND component_id IS NOT NULL
                UNION
                SELECT owner.rhino_guid, parent.parent_component_id
                    FROM owners owner JOIN components parent ON parent.component_id = owner.component_id
                    WHERE parent.parent_component_id IS NOT NULL
            )
            SELECT o.rhino_guid, so.scene_id FROM document_objects o
            JOIN scene_objects so ON so.object_rowid = o.id WHERE o.model_path = ?
            UNION
            SELECT owner.rhino_guid, sc.scene_id FROM owners owner
            JOIN scene_components sc ON sc.component_id = owner.component_id
            """, (model_path, model_path)
        ):
            if row["rhino_guid"] in wanted:
                result.add(row["scene_id"])
        return result

    @staticmethod
    def _component_descendant_ids(connection, component_id):
        return [row["component_id"] for row in connection.execute("""
            WITH RECURSIVE subtree(component_id) AS (
                SELECT component_id FROM components WHERE component_id = ?
                UNION
                SELECT child.component_id FROM components child
                    JOIN subtree parent ON child.parent_component_id = parent.component_id
            )
            SELECT component_id FROM subtree ORDER BY component_id
        """, (component_id,))]

    @staticmethod
    def _component_ancestor_ids(connection, component_id):
        return [row["component_id"] for row in connection.execute("""
            WITH RECURSIVE ancestors(component_id, parent_component_id) AS (
                SELECT component_id, parent_component_id FROM components WHERE component_id = ?
                UNION
                SELECT parent.component_id, parent.parent_component_id FROM components parent
                    JOIN ancestors child ON parent.component_id = child.parent_component_id
            )
            SELECT component_id FROM ancestors WHERE component_id != ?
        """, (component_id, component_id))]

    @classmethod
    def _component_child_ids(cls, connection, component_id, model_path, values):
        if not isinstance(values, list):
            raise ValueError("child_component_ids must be a list of distinct Component handles.")
        children = [cls._component_handle(value) for value in values]
        if len(set(children)) != len(children):
            raise ValueError("child_component_ids contains duplicates.")
        for child_id in children:
            if child_id == component_id:
                raise ValueError("A Component cannot be its own child.")
            row = connection.execute(
                "SELECT model_path, parent_component_id FROM components WHERE component_id = ?", (child_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown child component_id: {child_id}")
            if row["model_path"] != model_path:
                raise ValueError("Child Component must belong to the same model_path.")
            if not connection.execute(
                "SELECT 1 FROM scene_components WHERE component_id = ? LIMIT 1", (child_id,)
            ).fetchone():
                raise ValueError("Child Component has no Scene registration.")
            if row["parent_component_id"] not in (None, component_id):
                raise ValueError("Child already belongs to another parent; detach it before reparenting.")
            if component_id in cls._component_descendant_ids(connection, child_id):
                raise ValueError("Component hierarchy cannot contain cycles.")
        return sorted(children)

    @staticmethod
    def _component_object_row(item):
        return {"rhino_guid": item["rhino_guid"], "object_type": item["object_type"],
                "component_id": item["component_id"],
                "bounds_mm": [item["min_x"], item["min_y"], item["min_z"],
                              item["max_x"], item["max_y"], item["max_z"]],
                "observed_at": item["observed_at"]}

    @staticmethod
    def _component_read(connection, component_id):
        row = connection.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)
        ).fetchone()
        if row is None:
            return None
        objects = [
            AlmondStore._component_object_row(item)
            for item in connection.execute(
                "SELECT * FROM document_objects WHERE component_id = ? ORDER BY rhino_guid",
                (component_id,),
            )
        ]
        effective_objects = [AlmondStore._component_object_row(item) for item in connection.execute("""
            WITH RECURSIVE subtree(component_id) AS (
                SELECT component_id FROM components WHERE component_id = ?
                UNION SELECT c.component_id FROM components c
                    JOIN subtree parent ON c.parent_component_id = parent.component_id
            )
            SELECT o.* FROM document_objects o JOIN subtree s ON o.component_id = s.component_id
            ORDER BY o.model_path, o.rhino_guid
        """, (component_id,))]
        children = [item["component_id"] for item in connection.execute(
            "SELECT component_id FROM components WHERE parent_component_id = ? ORDER BY component_id",
            (component_id,),
        )]
        return {
            **dict(row), "status": "registered", "live_verified": False,
            "scene_ids": [item["scene_id"] for item in connection.execute(
                "SELECT scene_id FROM scene_components WHERE component_id = ? ORDER BY scene_id",
                (component_id,),
            )],
            "object_ids": [item["rhino_guid"] for item in objects],
            "object_count": len(objects), "objects": objects,
            "direct_object_ids": [item["rhino_guid"] for item in objects],
            "child_component_ids": children,
            "effective_objects": effective_objects,
            "effective_object_ids": [item["rhino_guid"] for item in effective_objects],
            "effective_object_count": len(effective_objects),
            "pending_objects": [], "requires_sync": False,
        }

    def get_component(
        self, component_id: str, live: bool = False, native_inspect: Callable | None = None,
    ) -> dict[str, Any] | None:
        """Cached registration or one native read-only inspection with pending-group additions."""
        with self._connect() as connection:
            connection.execute("BEGIN")
            cached = self._component_read(connection, component_id)
            if cached is None or not live:
                return cached
            if not callable(native_inspect):
                raise ValueError("A native read-only inspection is required for live=True.")
            request = dict(type="design_component", action="inspect",
                           expected_model_path=cached["model_path"], component_id=component_id,
                           rhino_group_id=cached["rhino_group_id"],
                           expected_object_ids=cached["object_ids"],
                           expected_effective_object_ids=cached["effective_object_ids"],
                           expected_child_component_ids=cached["child_component_ids"],
                           expected_parent_component_id=cached["parent_component_id"])
            reply = self._component_native(native_inspect, request)
            observed = reply.get("component")
            if (not isinstance(observed, dict) or observed.get("complete") is not True
                    or observed.get("truncated") or observed.get("component_id") != component_id
                    or self._component_model_path(observed.get("model_path")) != cached["model_path"]
                    or self._component_guid(observed.get("rhino_group_id")) != cached["rhino_group_id"]):
                raise ValueError("Native Component inspection identity is incomplete or inconsistent.")
            if observed.get("registration_status") == "unregistered":
                return dict(cached, registration_status="unregistered", live_verified=True,
                            requires_sync=True, pending_objects=[])
            objects = self._component_observed_objects(observed, owner=component_id)
            direct_ids = [item["rhino_guid"] for item in objects]
            children = observed.get("child_component_ids", cached["child_component_ids"])
            pending = observed.get("pending_objects", [])
            if not isinstance(children, list) or not isinstance(pending, list):
                raise ValueError("Native Component children and pending objects must be lists.")
            native_scenes = self._component_scene_ids(connection, observed.get("scene_ids"))
            effective_changed = False
            if "effective_objects" in observed:
                effective = self._component_observed_objects(
                    {"complete": observed.get("complete"), "truncated": observed.get("truncated"),
                     "objects": observed["effective_objects"]},
                )
                effective_ids = [item["rhino_guid"] for item in effective]
                if ("effective_object_ids" in observed and
                        self._component_object_ids(observed["effective_object_ids"]) != effective_ids):
                    raise ValueError("Native effective object identities and details disagree.")
                effective_changed = [
                    (obj["rhino_guid"], obj["object_type"], obj.get("component_id"), obj["bounds_mm"])
                    for obj in effective
                ] != [
                    (obj["rhino_guid"], obj["object_type"], obj["component_id"], obj["bounds_mm"])
                    for obj in cached["effective_objects"]
                ]
            elif "effective_object_ids" in observed:
                effective_changed = (self._component_object_ids(observed["effective_object_ids"])
                                     != cached["effective_object_ids"])
            changed = (direct_ids != cached["object_ids"] or children != cached["child_component_ids"]
                       or native_scenes != cached["scene_ids"] or observed.get("name") != cached["name"]
                       or effective_changed
                       or ("parent_component_id" in observed and
                           observed["parent_component_id"] != cached["parent_component_id"])
                       or any(cached["objects"][i]["bounds_mm"] != obj["bounds_mm"]
                              for i, obj in enumerate(objects) if i < len(cached["objects"])))
            result = dict(cached)
            result.update(observed)
            result.update(object_ids=direct_ids, direct_object_ids=direct_ids, objects=objects,
                          scene_ids=native_scenes, child_component_ids=children,
                          pending_objects=pending, live_verified=True,
                          requires_sync=bool(changed or pending or observed.get("requires_sync")))
            return result

    def list_components(self, model_path: str = "") -> list[dict[str, Any]]:
        model_path = self._component_model_path(model_path) if model_path else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT component_id FROM components "
                "WHERE (? = '' OR model_path = ?) ORDER BY model_path, name, component_id",
                (model_path, model_path),
            ).fetchall()
            results = [self._component_read(connection, row["component_id"]) for row in rows]
        return [{key: value for key, value in item.items()
                 if key not in {"objects", "object_ids", "direct_object_ids", "effective_objects", "effective_object_ids"}}
                for item in results]

    def _component_store_snapshot(
        self, connection, snapshot, model_path, component_id, operation, *,
        expected_ids=None, expected_scene_ids=None, expected_name=None, expected_group_id="",
        expected_children=None, affected_components=None, sync_pending_ids=None,
        cache_effective=False,
    ):
        if not isinstance(snapshot, dict):
            raise ValueError("Native response must contain a component snapshot.")
        if snapshot.get("component_id") != component_id:
            raise ValueError("Native component_id does not match the requested registration.")
        if self._component_model_path(snapshot.get("model_path")) != model_path:
            raise ValueError("Native snapshot belongs to a different document.")
        group_id = self._component_guid(snapshot.get("rhino_group_id"))
        if expected_group_id and group_id != expected_group_id:
            raise ValueError("Native snapshot belongs to a different Rhino group.")
        name = snapshot.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Native component snapshot must report its name.")
        name = name.strip()
        if expected_name is not None and name != expected_name:
            raise ValueError("Native component name differs from the requested name.")
        scenes = self._component_scene_ids(connection, snapshot.get("scene_ids"))
        if not scenes:
            raise ValueError("A component must belong to at least one scene.")
        if expected_scene_ids is not None and scenes != expected_scene_ids:
            raise ValueError("Native scene membership differs from the requested scenes.")
        previous = self._component_read(connection, component_id)
        if "child_component_ids" not in snapshot and expected_children:
            raise ValueError("Native Component snapshot omitted its child Component identities.")
        children = self._component_child_ids(
            connection, component_id, model_path,
            snapshot.get("child_component_ids", previous["child_component_ids"] if previous else []),
        )
        if expected_children is not None and children != expected_children:
            raise ValueError("Native child Component selection differs from the requested values.")
        native_parent = snapshot.get("parent_component_id", previous["parent_component_id"] if previous else None)
        if native_parent == "":
            native_parent = None
        if native_parent is not None:
            self._component_handle(native_parent)
        if previous and native_parent != previous["parent_component_id"]:
            raise ValueError("Native Component parent differs from the registered tree; edit the parent explicitly.")
        if not previous and native_parent is not None:
            raise ValueError("A new Component must be attached by editing its registered parent.")
        objects = self._component_observed_objects(snapshot, expected_ids, component_id)
        if not objects and not children:
            raise ValueError("A Component requires a direct object or a child Component.")
        if snapshot.get("requires_sync") or snapshot.get("pending_objects"):
            raise ValueError("Native Component snapshot still requires membership reconciliation.")
        ids = [obj["rhino_guid"] for obj in objects]
        self._component_check_owners(connection, model_path, ids, component_id)
        if sync_pending_ids is not None and previous and (
            not set(previous["object_ids"]).issubset(ids)
            or not set(ids).difference(previous["object_ids"]).issubset(sync_pending_ids)
        ):
            raise ValueError("Native sync introduced an unobserved direct ownership change.")
        if previous and (previous["model_path"] != model_path
                         or previous["rhino_group_id"] != group_id):
            raise ValueError("A component cannot be rebound to another document or Rhino group.")
        group_owner = connection.execute(
            "SELECT component_id FROM components WHERE model_path = ? AND rhino_group_id = ?",
            (model_path, group_id),
        ).fetchone()
        if group_owner and group_owner["component_id"] != component_id:
            raise ValueError("The Rhino group is already registered as another component.")
        # The native endpoint reports only ancestors whose *effective member set*
        # changed. A child name-only edit leaves its ancestors untouched.
        prior_ancestor_effective = {
            ancestor_id: self._component_read(connection, ancestor_id)["effective_object_ids"]
            for ancestor_id in self._component_ancestor_ids(connection, component_id)
        }
        prior_descendants = set(self._component_descendant_ids(connection, component_id)) - {component_id}
        if sync_pending_ids is not None:
            self._component_sync_descendants(
                connection, model_path, component_id, affected_components, sync_pending_ids)
        previous_ids = previous["object_ids"] if previous else []
        affected = set(scenes) | set(previous["scene_ids"] if previous else [])
        affected |= self._component_affected_scenes(connection, model_path, ids + previous_ids)
        now = _utc_now()
        connection.execute(
            """
            INSERT INTO components(component_id, model_path, rhino_group_id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(component_id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at
            """, (component_id, model_path, group_id, name, now, now),
        )
        self._component_cache_objects(connection, model_path, objects)
        connection.execute("UPDATE document_objects SET component_id = NULL WHERE component_id = ?",
                           (component_id,))
        connection.executemany(
            "UPDATE document_objects SET component_id = ? WHERE model_path = ? AND rhino_guid = ?",
            [(component_id, model_path, guid) for guid in ids],
        )
        connection.execute("DELETE FROM scene_components WHERE component_id = ?", (component_id,))
        connection.executemany(
            "INSERT INTO scene_components(scene_id, component_id) VALUES (?, ?)",
            [(scene_id, component_id) for scene_id in scenes],
        )
        connection.execute(
            "UPDATE components SET parent_component_id = NULL WHERE parent_component_id = ?",
            (component_id,),
        )
        connection.executemany(
            "UPDATE components SET parent_component_id = ? WHERE component_id = ?",
            [(component_id, child_id) for child_id in children],
        )
        current = self._component_read(connection, component_id)
        self._component_check_native_effective(snapshot, current, require=bool(children))
        if cache_effective and "effective_objects" in snapshot:
            # A parent can have no direct objects while its descendants moved.
            # Read-only sync must refresh their cached bounds as well.
            effective = self._component_observed_objects(
                {"complete": snapshot.get("complete"), "truncated": snapshot.get("truncated"),
                 "objects": snapshot["effective_objects"]},
                expected_ids=current["effective_object_ids"],
            )
            self._component_cache_objects(connection, model_path, effective)
            current = self._component_read(connection, component_id)
        ancestors = set(self._component_ancestor_ids(connection, component_id))
        related = affected_components if affected_components is not None else []
        if not isinstance(related, list):
            raise ValueError("affected_components must be a list of complete Component snapshots.")
        related_ids = set()
        descendants = set(self._component_descendant_ids(connection, component_id)) - {component_id}
        allowed_related = (ancestors | descendants | prior_descendants |
                           set(previous["child_component_ids"] if previous else []))
        for item in related:
            if not isinstance(item, dict):
                raise ValueError("affected_components must contain Component snapshots.")
            related_id = item.get("component_id")
            if related_id in related_ids or related_id not in allowed_related:
                raise ValueError("Native response contains duplicate or unrelated affected Components.")
            related_ids.add(related_id)
            registered = self._component_read(connection, related_id)
            if (item.get("complete") is not True or item.get("truncated")
                    or registered is None or self._component_model_path(item.get("model_path")) != model_path
                    or self._component_guid(item.get("rhino_group_id")) != registered["rhino_group_id"]
                    or item.get("name") != registered["name"]
                    or self._component_scene_ids(connection, item.get("scene_ids")) != registered["scene_ids"]
                    or item.get("parent_component_id") != registered["parent_component_id"]
                    or self._component_object_ids([obj["rhino_guid"] for obj in item.get("objects", [])])
                       != registered["object_ids"]
                    or self._component_child_ids(connection, related_id, model_path,
                       item.get("child_component_ids", registered["child_component_ids"]))
                       != registered["child_component_ids"]):
                raise ValueError("Related native Component snapshot differs from the registered tree.")
            self._component_check_native_effective(item, registered, require=related_id in ancestors)
            if sync_pending_ids is not None and related_id in descendants:
                observed_direct = self._component_observed_objects(item, owner=related_id)
                if [(obj["rhino_guid"], obj["object_type"], obj["bounds_mm"]) for obj in observed_direct] != [
                    (obj["rhino_guid"], obj["object_type"], obj["bounds_mm"])
                    for obj in registered["objects"]
                ]:
                    raise ValueError("Native descendant Component bounds disagree with the effective snapshot.")
        changed_ancestors = {
            ancestor_id for ancestor_id in ancestors
            if prior_ancestor_effective.get(ancestor_id) !=
                self._component_read(connection, ancestor_id)["effective_object_ids"]
        }
        changed_children = set(children) ^ set(previous["child_component_ids"] if previous else [])
        if (changed_ancestors | changed_children) - related_ids:
            raise ValueError("Native response omitted changed ancestor or child Component proof.")
        affected |= self._component_affected_scenes(connection, model_path, ids + previous_ids)
        for child_id in set(children) | set(previous["child_component_ids"] if previous else []):
            child = self._component_read(connection, child_id)
            if child:
                affected |= self._component_affected_scenes(connection, model_path, child["effective_object_ids"])
        revisions = {scene_id: self._record_revision(
            connection, scene_id, operation,
            {"component_id": component_id, "model_path": model_path,
             "rhino_group_id": group_id, "object_ids": ids, "child_component_ids": children,
             "scene_ids": scenes},
        ) for scene_id in sorted(affected)}
        return dict(current,
                    live_verified=True, scene_revisions=revisions)

    @classmethod
    def _component_check_native_effective(cls, snapshot, registered, *, require=False):
        values = snapshot.get("effective_object_ids")
        objects = snapshot.get("effective_objects")
        if "effective_objects" in snapshot:
            objects = snapshot["effective_objects"]
            if not isinstance(objects, list) or any(not isinstance(obj, dict) for obj in objects):
                raise ValueError("Native effective_objects must be a list of objects.")
            observed_ids = [obj.get("rhino_guid") for obj in objects]
            if values is not None and cls._component_object_ids(values) != cls._component_object_ids(observed_ids):
                raise ValueError("Native effective objects and ID list disagree.")
            if values is None:
                values = observed_ids
        if values is None:
            if require:
                raise ValueError("Native hierarchy snapshot omitted effective Component members.")
            return
        if cls._component_object_ids(values) != sorted(registered["effective_object_ids"]):
            raise ValueError("Native effective Component membership does not match the registered subtree.")
        if objects is not None:
            owners = {obj["rhino_guid"]: obj["component_id"] for obj in registered["effective_objects"]}
            if any(obj.get("component_id") != owners.get(obj.get("rhino_guid")) for obj in objects):
                raise ValueError("Native ancestor group changed a descendant's direct owner.")

    def _component_sync_descendants(self, connection, model_path, component_id, related, pending_ids):
        """Cache verified descendant owners adopted by one native subtree sync."""
        descendants = set(self._component_descendant_ids(connection, component_id)) - {component_id}
        if not isinstance(related, list):
            raise ValueError("Native sync must return affected Component snapshots.")
        for item in related:
            if not isinstance(item, dict):
                raise ValueError("Native sync returned an invalid affected Component snapshot.")
            child_id = item.get("component_id")
            if child_id not in descendants:
                continue
            cached = self._component_read(connection, child_id)
            if (item.get("complete") is not True or item.get("truncated")
                    or self._component_model_path(item.get("model_path")) != model_path
                    or self._component_guid(item.get("rhino_group_id")) != cached["rhino_group_id"]
                    or item.get("name") != cached["name"]
                    or self._component_scene_ids(connection, item.get("scene_ids")) != cached["scene_ids"]
                    or item.get("parent_component_id") != cached["parent_component_id"]
                    or self._component_child_ids(connection, child_id, model_path,
                                                 item.get("child_component_ids")) != cached["child_component_ids"]
                    or item.get("pending_objects") or item.get("requires_sync")):
                raise ValueError("Native sync changed a descendant Component's registered identity.")
            direct = self._component_observed_objects(item, owner=child_id)
            ids = [obj["rhino_guid"] for obj in direct]
            if (not set(cached["object_ids"]).issubset(ids)
                    or not set(ids).difference(cached["object_ids"]).issubset(pending_ids)):
                raise ValueError("Native sync introduced an unobserved descendant ownership change.")
            self._component_check_owners(connection, model_path, ids, child_id)
            self._component_cache_objects(connection, model_path, direct)
            connection.execute("UPDATE document_objects SET component_id = NULL WHERE component_id = ?",
                               (child_id,))
            connection.executemany(
                "UPDATE document_objects SET component_id = ? WHERE model_path = ? AND rhino_guid = ?",
                [(child_id, model_path, guid) for guid in ids],
            )

    def upsert_component(
        self, model_path: str, name: str, object_ids: list[str],
        scene_ids: list[str] | None = None, component_id: str = "", rhino_group_id: str = "",
        native_apply: Callable | None = None,
        child_component_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register direct members and explicit children without retagging descendant owners."""
        model_path = self._component_model_path(model_path)
        component_id = self._component_handle(component_id or f"component_{uuid.uuid4().hex[:12]}")
        ids = self._component_object_ids(object_ids)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A component needs a name.")
        name = name.strip()
        group_id = self._component_guid(rhino_group_id) if rhino_group_id else ""
        if not callable(native_apply):
            raise ValueError("Native component registration is required.")
        attempted = False
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = self._component_read(connection, component_id)
                if existing:
                    if existing["model_path"] != model_path:
                        raise ValueError("The component belongs to a different model_path.")
                    if group_id and group_id != existing["rhino_group_id"]:
                        raise ValueError("The component belongs to a different Rhino group.")
                    group_id = existing["rhino_group_id"]
                if group_id:
                    owner = connection.execute(
                        "SELECT component_id FROM components WHERE model_path = ? AND rhino_group_id = ?",
                        (model_path, group_id),
                    ).fetchone()
                    if owner and owner["component_id"] != component_id:
                        raise ValueError("The Rhino group is already registered as another component.")
                scenes = self._component_scene_ids(
                    connection, scene_ids if scene_ids is not None else
                    (existing["scene_ids"] if existing else []),
                )
                if not scenes:
                    raise ValueError("A component must belong to at least one scene.")
                children = self._component_child_ids(
                    connection, component_id, model_path,
                    child_component_ids if child_component_ids is not None else
                    (existing["child_component_ids"] if existing else []),
                )
                if not ids and not children:
                    raise ValueError("A Component needs a direct object or an existing child Component.")
                self._component_check_owners(connection, model_path, ids, component_id)
                request = dict(type="design_component", action="upsert",
                               expected_model_path=model_path, component_id=component_id,
                               rhino_group_id=group_id, name=name, object_ids=ids,
                               child_component_ids=children, scene_ids=scenes)
                if existing:
                    request["expected_object_ids"] = existing["object_ids"]
                    request["expected_child_component_ids"] = existing["child_component_ids"]
                    request["expected_parent_component_id"] = existing["parent_component_id"]
                attempted = True
                reply = self._component_native(native_apply, request)
                result = self._component_store_snapshot(
                    connection, reply.get("component"), model_path, component_id, "upsert_component",
                    expected_ids=ids, expected_scene_ids=scenes, expected_name=name,
                    expected_group_id=group_id, expected_children=children,
                    affected_components=reply.get("affected_components"),
                )
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise ComponentReconciliationError(component_id, model_path, str(exc)) from exc
            raise
        return result

    @contextmanager
    def _component_sync_transaction(self, component_id, model_path, mutated):
        # A native mutation can succeed even if SQLite fails on context exit.
        try:
            with self._connect() as connection:
                yield connection
        except (_NativeRejected, ComponentReconciliationError):
            raise
        except Exception as exc:
            if mutated[0]:
                raise ComponentReconciliationError(component_id, model_path, str(exc)) from exc
            raise

    def sync_component(
        self, model_path: str, component_id: str, rhino_group_id: str = "",
        native_inspect: Callable | None = None,
    ) -> dict[str, Any]:
        """Inspect once; explicitly adopt unowned group additions through one native sync."""
        model_path = self._component_model_path(model_path)
        component_id = self._component_handle(component_id)
        group_id = self._component_guid(rhino_group_id) if rhino_group_id else ""
        if not callable(native_inspect):
            raise ValueError("A native read-only component inspection is required.")
        mutated = [False]
        with self._component_sync_transaction(component_id, model_path, mutated) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._component_read(connection, component_id)
            if existing:
                if existing["model_path"] != model_path:
                    raise ValueError("The component belongs to a different model_path.")
                if group_id and group_id != existing["rhino_group_id"]:
                    raise ValueError("The component belongs to a different Rhino group.")
                group_id = existing["rhino_group_id"]
            request = dict(
                type="design_component", action="inspect", expected_model_path=model_path,
                component_id=component_id, rhino_group_id=group_id,
                name=existing["name"] if existing else "", object_ids=[], scene_ids=[],
                child_component_ids=existing["child_component_ids"] if existing else [],
            )
            if existing:
                request["expected_object_ids"] = existing["object_ids"]
                request["expected_effective_object_ids"] = existing["effective_object_ids"]
                request["expected_child_component_ids"] = existing["child_component_ids"]
                request["expected_parent_component_id"] = existing["parent_component_id"]
            reply = self._component_native(native_inspect, request)
            observed = reply.get("component")
            if isinstance(observed, dict) and observed.get("registration_status") == "unregistered":
                result = self._component_sync_unregistered(
                    connection, observed, existing, affected_components=reply.get("affected_components"),
                )
            else:
                if not isinstance(observed, dict):
                    raise ValueError("Native Component inspection did not return a snapshot.")
                inspected_ancestors = []
                for ancestor_id in self._component_ancestor_ids(connection, component_id):
                    ancestor = self._component_read(connection, ancestor_id)
                    related_reply = self._component_native(native_inspect, dict(
                        type="design_component", action="inspect",
                        expected_model_path=model_path, component_id=ancestor_id,
                        rhino_group_id=ancestor["rhino_group_id"],
                        expected_object_ids=ancestor["object_ids"],
                        expected_child_component_ids=ancestor["child_component_ids"],
                        expected_parent_component_id=ancestor["parent_component_id"],
                    ))
                    related_snapshot = related_reply.get("component")
                    if not isinstance(related_snapshot, dict):
                        raise ValueError("Native ancestor Component inspection did not return a snapshot.")
                    inspected_ancestors.append(related_snapshot)
                provided_related = reply.get("affected_components") or []
                if not isinstance(provided_related, list) or any(
                    not isinstance(item, dict) for item in provided_related
                ):
                    raise ValueError("Native inspection returned invalid related Component snapshots.")
                newest_ancestors = {item["component_id"] for item in inspected_ancestors}
                related_proof = [item for item in provided_related
                                 if item.get("component_id") not in newest_ancestors] + inspected_ancestors
                pending = observed.get("pending_objects", [])
                if not isinstance(pending, list):
                    raise ValueError("Native pending_objects must be a list.")
                if any(not isinstance(obj, dict) or obj.get("component_id") not in (None, "")
                       for obj in pending):
                    raise ValueError("Pending objects have another owner; reconcile the conflict explicitly.")
                attempted_sync = bool(pending or observed.get("requires_sync") or
                                      any(item.get("requires_sync") for item in inspected_ancestors))
                if attempted_sync:
                    sync_request = dict(request, action="sync",
                                        pending_object_ids=self._component_object_ids(
                                            [item.get("rhino_guid") for item in pending]),
                                        expected_object_ids=existing["object_ids"] if existing else [],
                                        expected_child_component_ids=existing["child_component_ids"] if existing else [],
                                        expected_parent_component_id=existing["parent_component_id"] if existing else None)
                    try:
                        mutated[0] = True
                        applied = self._component_native(native_inspect, sync_request)
                        observed = applied.get("component")
                        result = self._component_store_snapshot(
                            connection, observed, model_path, component_id, "sync_component",
                            expected_group_id=group_id,
                            affected_components=applied.get("affected_components"),
                            sync_pending_ids=set(sync_request["pending_object_ids"]),
                            cache_effective=True,
                        )
                    except _NativeRejected:
                        raise
                    except Exception as exc:
                        raise ComponentReconciliationError(component_id, model_path, str(exc)) from exc
                else:
                    if existing is not None:
                        inspected = self._component_observed_objects(observed, owner=component_id)
                        same_direct_tree = (
                            [obj["rhino_guid"] for obj in inspected] == existing["object_ids"]
                            and observed.get("child_component_ids", existing["child_component_ids"])
                            == existing["child_component_ids"])
                        if same_direct_tree:
                            self._component_check_native_effective(
                                observed, existing, require=bool(existing["child_component_ids"]))
                        if "effective_objects" in observed:
                            effective = self._component_observed_objects(
                                {"complete": observed.get("complete"),
                                 "truncated": observed.get("truncated"),
                                 "objects": observed["effective_objects"]},
                                expected_ids=existing["effective_object_ids"] if same_direct_tree else None,
                            )
                        else:
                            effective = inspected
                        unchanged = (
                            self._component_object_ids([obj["rhino_guid"] for obj in inspected])
                            == existing["object_ids"]
                            and self._component_scene_ids(connection, observed.get("scene_ids"))
                            == existing["scene_ids"]
                            and observed.get("name") == existing["name"]
                            and observed.get("child_component_ids", existing["child_component_ids"])
                            == existing["child_component_ids"]
                            and observed.get("parent_component_id", existing["parent_component_id"])
                            == existing["parent_component_id"]
                            and [obj["bounds_mm"] for obj in inspected]
                            == [obj["bounds_mm"] for obj in existing["objects"]]
                            and [(obj["rhino_guid"], obj["object_type"], obj["component_id"], obj["bounds_mm"])
                                 for obj in effective] == [
                                (obj["rhino_guid"], obj["object_type"], obj["component_id"], obj["bounds_mm"])
                                for obj in existing["effective_objects"]]
                        )
                        if unchanged:
                            return dict(existing, live_verified=True)
                result = self._component_store_snapshot(
                    connection, observed, model_path, component_id, "sync_component",
                    expected_group_id=group_id,
                    affected_components=related_proof,
                    cache_effective=True,
                ) if not attempted_sync else result
        return result

    @staticmethod
    def _component_require_unreferenced(connection, component_id):
        node = connection.execute(
            "SELECT parent_component_id FROM components WHERE component_id = ?", (component_id,)
        ).fetchone()
        if node and node["parent_component_id"] is not None:
            raise ValueError("Detach this Component from its parent before unregistering.")
        if connection.execute(
            "SELECT 1 FROM generation_plan_components WHERE component_id = ? "
            "UNION ALL SELECT 1 FROM generation_step_components WHERE component_id = ? "
            "UNION ALL SELECT 1 FROM drawing_sheet_components WHERE component_id = ? LIMIT 1",
            (component_id, component_id, component_id),
        ).fetchone():
            raise ValueError(
                "Component is referenced by a generation plan, step, or drawing sheet; "
                "remove those references explicitly before unregistering."
            )

    def _component_check_detached_children(self, connection, existing, detached, snapshots):
        expected = existing["child_component_ids"]
        if (not isinstance(detached, list) or
                sorted(self._component_handle(value) for value in detached) != expected):
            raise ValueError("Native detached child Component IDs do not match the parent registration.")
        if not isinstance(snapshots, list):
            raise ValueError("Native detached Component snapshots must be a list.")
        descendants = set(expected)
        for child_id in expected:
            descendants.update(self._component_descendant_ids(connection, child_id))
        seen = set()
        for item in snapshots:
            if not isinstance(item, dict) or item.get("complete") is not True or item.get("truncated"):
                raise ValueError("Native detached child snapshot is incomplete.")
            child_id = item.get("component_id")
            if child_id not in descendants or child_id in seen:
                raise ValueError("Native detached Component response contains unrelated or duplicate children.")
            seen.add(child_id)
            registered = self._component_read(connection, child_id)
            if (registered is None or self._component_model_path(item.get("model_path")) != registered["model_path"]
                    or self._component_guid(item.get("rhino_group_id")) != registered["rhino_group_id"]
                    or item.get("name") != registered["name"]
                    or item.get("parent_component_id") != registered["parent_component_id"]
                    or self._component_scene_ids(connection, item.get("scene_ids")) != registered["scene_ids"]
                    or sorted(item.get("child_component_ids", [])) != registered["child_component_ids"]
                    or self._component_object_ids([obj.get("rhino_guid") for obj in item.get("objects", [])])
                       != registered["object_ids"]):
                raise ValueError("Native detached Component snapshot differs from retained child ownership.")
            self._component_check_native_effective(item, registered, require=True)
        if not set(expected).issubset(seen):
            raise ValueError("Native response omitted detached child Component proof.")

    def _component_sync_unregistered(self, connection, observed, existing, affected_components=None):
        if existing is None:
            raise ValueError("An unregistered proof requires an existing Component registration.")
        component_id, model_path = existing["component_id"], existing["model_path"]
        if (observed.get("component_id") != component_id
                or self._component_model_path(observed.get("model_path")) != model_path
                or self._component_guid(observed.get("rhino_group_id")) != existing["rhino_group_id"]
                or observed.get("scene_ids") != []):
            raise ValueError("Unregistered proof does not match the existing Component identity.")
        objects = self._component_observed_objects(observed, existing["object_ids"])
        if any("component_id" not in obj or obj["component_id"] is not None for obj in objects):
            raise ValueError("Unregistered proof must verify every former member is unowned.")
        if existing["child_component_ids"] and "effective_object_ids" not in observed:
            raise ValueError("Native unregistered parent proof omitted former effective group membership.")
        if "effective_object_ids" in observed and self._component_object_ids(observed["effective_object_ids"]) != sorted(existing["effective_object_ids"]):
            raise ValueError("Native unregistered parent group no longer contains the registered subtree.")
        self._component_require_unreferenced(connection, component_id)
        affected = set(existing["scene_ids"]) | self._component_affected_scenes(
            connection, model_path, existing["effective_object_ids"],
        )
        connection.execute("UPDATE components SET parent_component_id = NULL WHERE parent_component_id = ?",
                           (component_id,))
        self._component_check_detached_children(
            connection, existing, observed.get("detached_child_component_ids", []),
            affected_components if affected_components is not None else [],
        )
        self._component_cache_objects(connection, model_path, objects)
        connection.execute("UPDATE document_objects SET component_id = NULL WHERE component_id = ?", (component_id,))
        connection.execute("DELETE FROM components WHERE component_id = ?", (component_id,))
        revisions = {scene_id: self._record_revision(
            connection, scene_id, "sync_component_unregistered", {"component_id": component_id},
        ) for scene_id in sorted(affected)}
        return dict(component_id=component_id, model_path=model_path, rhino_group_id=existing["rhino_group_id"],
                    status="unregistered", live_verified=True, scene_revisions=revisions)

    def unregister_component(
        self, component_id: str, native_apply: Callable | None = None,
    ) -> dict[str, Any]:
        """Remove semantic ownership; the native handler must preserve objects and ordinary groups."""
        if not callable(native_apply):
            raise ValueError("Native component unregistration is required.")
        attempted = False
        model_path = ""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = self._component_read(connection, component_id)
                if existing is None:
                    raise KeyError(f"Unknown component_id: {component_id}")
                self._component_require_unreferenced(connection, component_id)
                model_path = existing["model_path"]
                affected = set(existing["scene_ids"])
                affected |= self._component_affected_scenes(
                connection, model_path, existing["effective_object_ids"],
                )
                attempted = True
                reply = self._component_native(native_apply, dict(
                    type="design_component", action="unregister", expected_model_path=model_path,
                    component_id=component_id, rhino_group_id=existing["rhino_group_id"],
                    name=existing["name"], object_ids=existing["object_ids"], scene_ids=existing["scene_ids"],
                    expected_object_ids=existing["object_ids"],
                    child_component_ids=existing["child_component_ids"],
                    expected_child_component_ids=existing["child_component_ids"],
                    expected_effective_object_ids=existing["effective_object_ids"],
                    expected_parent_component_id=None,
                ))
                if (reply.get("component_id") != component_id
                        or self._component_model_path(reply.get("model_path")) != model_path
                        or self._component_guid(reply.get("rhino_group_id")) != existing["rhino_group_id"]):
                    raise ValueError("Native unregistration acknowledgement does not match the component.")
                connection.execute("UPDATE components SET parent_component_id = NULL WHERE parent_component_id = ?",
                                   (component_id,))
                self._component_check_detached_children(
                    connection, existing, reply.get("detached_child_component_ids", []),
                    reply.get("affected_components", []),
                )
                connection.execute(
                    "UPDATE document_objects SET component_id = NULL WHERE component_id = ?",
                    (component_id,),
                )
                connection.execute("DELETE FROM components WHERE component_id = ?", (component_id,))
                revisions = {scene_id: self._record_revision(
                    connection, scene_id, "unregister_component", {"component_id": component_id},
                ) for scene_id in sorted(affected)}
                result = dict(component_id=component_id, model_path=model_path,
                              status="unregistered", live_verified=True, scene_revisions=revisions)
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise ComponentReconciliationError(component_id, model_path, str(exc)) from exc
            raise
        return result

    def register_scene_objects(
        self, scene_id: str, model_path: str, object_ids: list[str], mode: str = "add",
        native_observe: Callable | None = None,
    ) -> dict[str, Any]:
        """Link raw objects directly to one scene; the native callback only observes geometry."""
        model_path = self._component_model_path(model_path)
        ids = set(self._component_object_ids(object_ids))
        if mode not in {"add", "remove", "replace"}:
            raise ValueError("mode must be add, remove, or replace.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            scene_id = self._component_scene_ids(connection, [scene_id])[0]
            existing = {row["rhino_guid"] for row in connection.execute(
                "SELECT o.rhino_guid FROM scene_objects so JOIN document_objects o ON o.id = so.object_rowid "
                "WHERE so.scene_id = ? AND o.model_path = ?", (scene_id, model_path),
            )}
            desired = (existing | ids if mode == "add" else
                       existing - ids if mode == "remove" else ids)
            # A removed object may no longer exist in Rhino; only the retained
            # membership needs live geometry/ownership observation.
            observed_ids = sorted(desired)
            affected = {scene_id} | self._component_affected_scenes(connection, model_path, existing | desired)
            if observed_ids:
                if not callable(native_observe):
                    raise ValueError("Native read-only object observation is required.")
                reply = self._component_native(native_observe, dict(
                    type="design_component", action="objects", expected_model_path=model_path,
                    object_ids=observed_ids,
                ))
                if self._component_model_path(reply.get("model_path")) != model_path:
                    raise ValueError("Native objects belong to a different document.")
                objects = self._component_observed_objects(reply, observed_ids)
                for obj in objects:
                    if "component_id" not in obj:
                        continue
                    row = connection.execute(
                        "SELECT component_id FROM document_objects WHERE model_path = ? AND rhino_guid = ?",
                        (model_path, obj["rhino_guid"]),
                    ).fetchone()
                    registered_owner = row["component_id"] if row else None
                    if (obj["component_id"] or None) != registered_owner:
                        raise ValueError("Native object ownership differs from the ledger; reconcile its component first.")
                self._component_cache_objects(connection, model_path, objects)
            connection.execute(
                "DELETE FROM scene_objects WHERE scene_id = ? AND object_rowid IN "
                "(SELECT id FROM document_objects WHERE model_path = ?)", (scene_id, model_path),
            )
            connection.executemany(
                "INSERT INTO scene_objects(scene_id, object_rowid) "
                "SELECT ?, id FROM document_objects WHERE model_path = ? AND rhino_guid = ?",
                [(scene_id, model_path, guid) for guid in sorted(desired)],
            )
            revisions = {affected_id: self._record_revision(
                connection, affected_id, "register_scene_objects",
                {"model_path": model_path, "scene_id": scene_id, "object_ids": sorted(desired), "mode": mode},
            ) for affected_id in sorted(affected)}
        return dict(scene_id=scene_id, model_path=model_path, object_ids=sorted(desired),
                    direct_objects=len(desired), scene_revisions=revisions, live_verified=True)

    def scene_objects(self, scene_id: str) -> list[dict[str, Any]]:
        """Cached set of directly linked objects and recursively linked Component members."""
        with self._connect() as connection:
            scene_id = self._component_scene_ids(connection, [scene_id])[0]
            rows = connection.execute(
                """
                WITH RECURSIVE linked_components(component_id) AS (
                    SELECT component_id FROM scene_components WHERE scene_id = ?
                    UNION
                    SELECT child.component_id FROM components child
                        JOIN linked_components parent ON child.parent_component_id = parent.component_id
                )
                SELECT o.*, EXISTS(
                    SELECT 1 FROM scene_objects so WHERE so.object_rowid = o.id AND so.scene_id = ?
                ) AS direct FROM document_objects o
                WHERE EXISTS(SELECT 1 FROM scene_objects so WHERE so.object_rowid = o.id AND so.scene_id = ?)
                   OR EXISTS(SELECT 1 FROM linked_components lc WHERE lc.component_id = o.component_id)
                ORDER BY o.model_path, o.rhino_guid
                """, (scene_id, scene_id, scene_id),
            ).fetchall()
        return [
            {"model_path": row["model_path"], "rhino_guid": row["rhino_guid"],
             "component_id": row["component_id"], "object_type": row["object_type"],
             "bounds_mm": [row["min_x"], row["min_y"], row["min_z"],
                           row["max_x"], row["max_y"], row["max_z"]],
             "direct": bool(row["direct"]), "observed_at": row["observed_at"], "live_verified": False}
            for row in rows
        ]

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

