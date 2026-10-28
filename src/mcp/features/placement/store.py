"""Feature-owned Room and asset-instance SQL on the shared AlmondStore database."""
from __future__ import annotations

import math
import uuid
from typing import Any

from almond_mcp.store_common import _json, _utc_now


class PlacementStore:
    """Legacy placement ledger; connection, schema and revisions are shared."""

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
