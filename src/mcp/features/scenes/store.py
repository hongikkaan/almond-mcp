"""Scene metadata and live semantic-group geometry; no per-object persistence."""
from __future__ import annotations

from typing import Any, Callable
import uuid

from almond_mcp.store_common import _utc_now


class ScenesStore:
    """Scene metadata and transient recursive semantic-group observations."""

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
                "WITH matched AS (SELECT scene_id, name, file_name, project_file_id, units, revision, created_at, updated_at FROM _scene_records "
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

    def create_scene(self, name: str, units: str = "mm", file_name: str = "", project_file_id: str | None = None) -> dict[str, Any]:
        if not isinstance(file_name, str):
            raise ValueError("file_name must be a string.")
        units = units.lower().strip()
        if units not in {"mm", "cm", "m", "in", "ft"}:
            raise ValueError("units must be mm, cm, m, in, or ft.")
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            file_id = self._project_file_reference(connection, file_name, project_file_id)
            connection.execute(
                """
                INSERT INTO scenes(scene_id, name, units, revision, created_at, updated_at, project_file_id)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                """,
                (scene_id, name.strip() or "Untitled scene", units, now, now, file_id),
            )
        return self.get_scene(scene_id)

    def update_scene(self, scene_id: str, file_name: str | None = None, project_file_id: str | None = None) -> dict[str, Any]:
        if file_name is not None and not isinstance(file_name, str):
            raise ValueError("file_name must be a string.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT file_name,project_file_id FROM _scene_records WHERE scene_id = ?", (scene_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown scene_id: {scene_id}")
            file_id = row['project_file_id'] if file_name is None and project_file_id is None else self._project_file_reference(connection,file_name or '',project_file_id)
            if row['project_file_id'] != file_id:
                connection.execute('UPDATE scenes SET project_file_id=? WHERE scene_id=?',(file_id,scene_id))
                display = connection.execute('SELECT file_name FROM _scene_records WHERE scene_id=?',(scene_id,)).fetchone()[0]
                self._record_revision(connection,scene_id,'update_scene',{'project_file_id':file_id,'file_name':display})
        return self.get_scene(scene_id)


    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            scene = connection.execute(
                "SELECT * FROM _scene_records WHERE scene_id = ?",
                (scene_id,),
            ).fetchone()
            if not scene:
                return None
            component_count = connection.execute(
                "SELECT COUNT(*) FROM _scene_component_refs WHERE scene_id = ?", (scene_id,)
            ).fetchone()[0]
            object_count = connection.execute("""
                WITH RECURSIVE linked(component_id) AS (
                    SELECT component_id FROM _scene_component_refs WHERE scene_id = ? UNION
                    SELECT c.component_id FROM _component_records c JOIN linked p ON c.parent_component_id=p.component_id)
                SELECT COALESCE(SUM(c.object_count),0) FROM _component_records c JOIN linked l ON l.component_id=c.component_id
                WHERE c.availability='present'
            """, (scene_id,)).fetchone()[0]
        return dict(scene_id=scene['scene_id'], name=scene['name'], file_name=scene['file_name'],
                    project_file_id=scene['project_file_id'],units=scene['units'],revision=int(scene['revision']),components=component_count,
                    objects=object_count,live_verified=False,updated_at=scene['updated_at'])

    def scene_objects(self, scene_id, model_path='', native_inspect=None):
        """Read members of semantic groups from Rhino; never register individual objects."""
        if not callable(native_inspect):
            raise ValueError('Scene geometry requires a live read-only Rhino observation.')
        with self._connect() as connection:
            connection.execute('BEGIN')
            self._component_scene_ids(connection,[scene_id])
            rows = connection.execute("""WITH RECURSIVE linked(component_id) AS (
                SELECT component_id FROM _scene_component_refs WHERE scene_id=? UNION
                SELECT c.component_id FROM _component_records c JOIN linked p ON c.parent_component_id=p.component_id)
                SELECT c.component_id,c.model_path FROM _component_records c JOIN linked l ON l.component_id=c.component_id""",(scene_id,)).fetchall()
            if not rows:
                return []
            if not model_path:
                models={r['model_path'] for r in rows}
                if len(models)!=1:
                    raise ValueError('Scene spans several models; select the saved model to observe.')
                model_path=next(iter(models))
            model_path=self._component_model_path(model_path)
            ids=sorted(r['component_id'] for r in rows if r['model_path']==model_path)
            if not ids:
                return []
            if len(ids)>64:
                raise ValueError('Narrow Scene observation to at most 64 Component registrations.')
            seeds=[{k:v for k,v in self._component_read(connection,h).items()
                    if k in {'component_id','rhino_group_id','name','scene_ids','child_component_ids'}} for h in ids]
            reply=self._component_native(native_inspect,dict(type='design_component',action='inspect_many',
                expected_model_path=model_path,component_ids=ids,registrations=seeds))
            if (reply.get('complete') is not True or reply.get('truncated') or reply.get('problems')
                    or self._component_model_path(reply.get('model_path'))!=model_path
                    or not isinstance(reply.get('editing'),dict) or reply['editing'].get('stable') is not True):
                raise ValueError('Scene geometry needs complete stable native observation without unresolved bindings.')
            if not isinstance(reply.get('components'),list):
                raise ValueError('Scene observation must contain Component snapshots.')
            prepared={}
            for raw in reply['components']:
                item=self._component_snapshot(connection,raw,model_path)
                if item['component_id'] in prepared or item['component_id'] not in ids:
                    raise ValueError('Scene observation contains duplicate or out-of-scope Components; align first.')
                prepared[item['component_id']]=item
            if set(prepared)!=set(ids):
                raise ValueError('Scene observation omitted registered Components.')
            self._component_validate_tree(connection,prepared,model_path)
            objects={}
            for item in prepared.values():
                for obj in item['objects']:
                    objects[obj['rhino_guid']]=dict(obj,model_path=model_path,live_verified=True)
            return [objects[guid] for guid in sorted(objects)]
