"""Scene persistence using the composed store connection and Component contracts."""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

from typing import Any, Callable
import uuid

from almond_mcp.store_common import _utc_now


class ScenesStore:
    """Scene metadata, recursive object reads, and direct membership transactions."""

    def list_scenes(self, name: str = "", file_name: str = "", limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """List project metadata in one query, without recursive geometry reads."""
        if not isinstance(name, str) or not isinstance(file_name, str):
            raise ValueError("name and file_name must be strings.")
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("limit must be an integer from 1 to 200.")
        if type(offset) is not int or offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        with self._connect() as connection:
            rows = connection.execute(
                "WITH matched AS (SELECT scene_id, name, file_name, units, revision, created_at, updated_at FROM scenes "
                "WHERE (? = '' OR instr(lower(name), lower(?)) > 0) "
                "AND (? = '' OR file_name = ?)), "
                "page AS (SELECT * FROM matched ORDER BY name COLLATE NOCASE, scene_id LIMIT ? OFFSET ?) "
                "SELECT page.*, stats.total FROM (SELECT COUNT(*) AS total FROM matched) stats "
                "LEFT JOIN page ON 1 = 1 ORDER BY page.name COLLATE NOCASE, page.scene_id",
                (name, name, file_name, file_name, limit, offset),
            ).fetchall()
        total = int(rows[0]["total"]) if rows else 0
        scenes = [{key: row[key] for key in row.keys() if key != "total"}
                  for row in rows if row["scene_id"] is not None]
        return {"scenes": scenes, "total": total, "limit": limit, "offset": offset,
                "truncated": offset + len(scenes) < total}

    def create_scene(self, name: str, units: str = "mm", file_name: str = "") -> dict[str, Any]:
        if not isinstance(file_name, str):
            raise ValueError("file_name must be a string.")
        units = units.lower().strip()
        if units not in {"mm", "cm", "m", "in", "ft"}:
            raise ValueError("units must be mm, cm, m, in, or ft.")
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scenes(scene_id, name, units, revision, created_at, updated_at, file_name)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                """,
                (scene_id, name.strip() or "Untitled scene", units, now, now, file_name),
            )
        return self.get_scene(scene_id)

    def update_scene(self, scene_id: str, file_name: str) -> dict[str, Any]:
        if not isinstance(file_name, str):
            raise ValueError("file_name must be a string.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT file_name FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown scene_id: {scene_id}")
            if row["file_name"] != file_name:
                connection.execute("UPDATE scenes SET file_name = ? WHERE scene_id = ?", (file_name, scene_id))
                self._record_revision(connection, scene_id, "update_scene", {"file_name": file_name})
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
                    SELECT sc.component_id FROM scene_components sc JOIN components c ON c.component_id = sc.component_id
                        WHERE sc.scene_id = ? AND c.availability = 'present'
                    UNION
                    SELECT c.component_id FROM components c
                        JOIN linked_components parent ON c.parent_component_id = parent.component_id
                )
                SELECT COUNT(*) FROM document_objects o
                WHERE EXISTS(SELECT 1 FROM scene_objects so WHERE so.scene_id = ? AND so.object_rowid = o.id)
                   OR EXISTS(SELECT 1 FROM linked_components lc JOIN components c ON c.component_id = lc.component_id
                             WHERE lc.component_id = o.component_id AND c.availability = 'present')
                """, (scene_id, scene_id),
            ).fetchone()[0]
        return {
            "scene_id": scene["scene_id"],
            "name": scene["name"],
            "file_name": scene["file_name"],
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
                        raise ValueError(read_instruction(__file__, 'response-862'))
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
                    SELECT sc.component_id FROM scene_components sc JOIN components c ON c.component_id = sc.component_id
                        WHERE sc.scene_id = ? AND c.availability = 'present'
                    UNION
                    SELECT child.component_id FROM components child
                        JOIN linked_components parent ON child.parent_component_id = parent.component_id
                )
                SELECT o.*, EXISTS(
                    SELECT 1 FROM scene_objects so WHERE so.object_rowid = o.id AND so.scene_id = ?
                ) AS direct FROM document_objects o
                WHERE EXISTS(SELECT 1 FROM scene_objects so WHERE so.object_rowid = o.id AND so.scene_id = ?)
                   OR EXISTS(SELECT 1 FROM linked_components lc JOIN components c ON c.component_id = lc.component_id
                             WHERE lc.component_id = o.component_id AND c.availability = 'present')
                ORDER BY o.model_path, o.rhino_guid
                """, (scene_id, scene_id, scene_id),
            ).fetchall()
        return [
            {"model_path": row["model_path"], "rhino_guid": row["rhino_guid"],
             "component_id": row["component_id"], "object_type": row["object_type"],
              "name": row["name"],
             "bounds_mm": [row["min_x"], row["min_y"], row["min_z"],
                           row["max_x"], row["max_y"], row["max_z"]],
             "direct": bool(row["direct"]), "observed_at": row["observed_at"], "live_verified": False}
            for row in rows
        ]
