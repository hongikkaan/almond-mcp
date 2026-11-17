"""SQLite connections and schema initialization for the Almond store."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from almond_mcp.retrieval_store import AlmondStore


class StoreDatabase:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
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

    def initialize(self, store: "AlmondStore") -> None:
        from almond_mcp.features.planning.file_schema import check_file_name_collisions, migrate_project_file_keys
        if self.database_path.exists():
            with closing(sqlite3.connect(self.database_path.as_uri() + "?mode=ro", uri=True)) as preflight:
                preflight.row_factory = sqlite3.Row
                check_file_name_collisions(preflight)
        with self.connect() as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            # executescript commits a pending transaction in legacy transaction mode.
            # Begin inside the script so the final FK check gates every schema change.
            connection.executescript(
                """
                BEGIN IMMEDIATE;

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

                CREATE INDEX IF NOT EXISTS idx_assets_category
                    ON assets(category, width_mm, depth_mm, height_mm);
                CREATE INDEX IF NOT EXISTS idx_instances_scene
                    ON instances(scene_id, room_id);
                CREATE INDEX IF NOT EXISTS idx_rooms_scene
                    ON rooms(scene_id);

                CREATE TRIGGER IF NOT EXISTS instances_delete_rtree
                AFTER DELETE ON instances BEGIN
                    DELETE FROM instance_rtree WHERE instance_rowid = OLD.id;
                END;
                """
            )
            store._initialize_validation_runs(connection)
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
            from almond_mcp.features.components.semantic_schema import initialize_semantics
            initialize_semantics(store, connection)
            store._initialize_generation_plans(connection)
            migrate_project_file_keys(connection)
            store._retire_drawing_sheet_constraints(connection)
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("DB migration found invalid relationships; all migration changes were rolled back.")
