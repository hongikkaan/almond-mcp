"""Component ledger rules mixed into the shared AlmondStore connection lifecycle."""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

import math
import hashlib
import json
import ntpath
import os
import re
import uuid
from contextlib import contextmanager
from typing import Any, Callable

from almond_mcp.store_common import ComponentReconciliationError, _NativeRejected, _utc_now


class ComponentsStore:
    """Own Component hierarchy, direct ownership and native reconciliation SQL."""

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
            failure = (_NativeRejected(message) if reply.get("mutation_applied") is False or reply.get("rolled_back") is True
                       else ValueError(message))
            failure.native_result = {key: reply[key] for key in (
                "error_code", "editing", "mutation_applied", "requires_reconciliation", "rolled_back",
            ) if key in reply}
            raise failure
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
    def _component_descendant_ids(connection, component_id):
        return [row["component_id"] for row in connection.execute("""
            WITH RECURSIVE subtree(component_id) AS (
                SELECT component_id FROM _component_records WHERE component_id = ?
                UNION
                SELECT child.component_id FROM _component_records child
                    JOIN subtree parent ON child.parent_component_id = parent.component_id
            )
            SELECT component_id FROM subtree ORDER BY component_id
        """, (component_id,))]

    @staticmethod
    def _component_ancestor_ids(connection, component_id):
        return [row["component_id"] for row in connection.execute("""
            WITH RECURSIVE ancestors(component_id, parent_component_id) AS (
                SELECT component_id, parent_component_id FROM _component_records WHERE component_id = ?
                UNION
                SELECT parent.component_id, parent.parent_component_id FROM _component_records parent
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
                "SELECT model_path, parent_component_id, scene_ids_json FROM _component_records WHERE component_id = ?", (child_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown child component_id: {child_id}")
            if row["model_path"] != model_path:
                raise ValueError("Child Component must belong to the same model_path.")
            if not json.loads(row["scene_ids_json"]):
                raise ValueError("Child Component has no Scene registration.")
            if row["parent_component_id"] not in (None, component_id):
                raise ValueError(read_instruction(__file__, 'response-514'))
            if component_id in cls._component_descendant_ids(connection, child_id):
                raise ValueError("Component hierarchy cannot contain cycles.")
        return sorted(children)

    @staticmethod
    def _canonical_component_refs(connection, values):
        """Retain a requested child only when none of its requested ancestors is present."""
        selected = set(values)
        rows = connection.execute("SELECT component_id, parent_component_id, availability FROM _component_records").fetchall()
        parents = {row[0]: row[1] for row in rows}
        selected.intersection_update(row[0] for row in rows if row[2] == "present")
        result = []
        for value in values:
            ancestor, seen = parents.get(value), set()
            while ancestor is not None and ancestor not in seen and ancestor not in selected:
                seen.add(ancestor)
                ancestor = parents.get(ancestor)
            if ancestor not in selected:
                result.append(value)
        return result

    @staticmethod
    def _component_canonical_scene_links(connection, model_path):
        rows = connection.execute("SELECT component_id, parent_component_id, scene_ids_json, availability FROM _component_records WHERE model_path = ?",
                                  (model_path,)).fetchall()
        parents = {row[0]: row[1] for row in rows}
        availability = {row[0]: row[3] for row in rows}
        contexts = {row[0]: json.loads(row[2]) if row[3] != "unregistered" else [] for row in rows}
        for handle, scenes in contexts.items():
            connection.execute("DELETE FROM scene_ontological WHERE ontological_id = ?", (handle,))
            for scene in scenes:
                ancestor, seen, redundant = parents[handle], set(), False
                while ancestor is not None and ancestor not in seen:
                    seen.add(ancestor)
                    if availability.get(ancestor) == "present" and scene in contexts.get(ancestor, []):
                        redundant = True
                        break
                    ancestor = parents.get(ancestor)
                if not redundant:
                    connection.execute("INSERT INTO scene_ontological(scene_id, ontological_id) VALUES (?, ?)", (scene, handle))


    @staticmethod
    def _component_summary(objects, effective):
        """Persist only aggregate facts and an opaque digest, never member rows/IDs."""
        def evidence(rows):
            return [(o['rhino_guid'], o.get('component_id'), o['object_type'],
                     o.get('name', ''), o['bounds_mm']) for o in sorted(rows, key=lambda o: o['rhino_guid'])]
        digest = hashlib.sha256(json.dumps([evidence(objects), evidence(effective)],
            ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
        bounds = ([min(o['bounds_mm'][i] for o in effective) for i in range(3)] +
                  [max(o['bounds_mm'][i] for o in effective) for i in range(3, 6)]) if effective else None
        return dict(geometry_digest=digest, object_count=len(objects), effective_object_count=len(effective),
                    object_types={kind: sum(o['object_type'] == kind for o in objects)
                                  for kind in sorted({o['object_type'] for o in objects})}, bounds_mm=bounds)

    @staticmethod
    def _component_read(connection, component_id):
        row = connection.execute('SELECT * FROM _component_records WHERE component_id = ?', (component_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result['scene_ids'] = json.loads(result.pop('scene_ids_json'))
        result['object_types'] = json.loads(result.pop('object_types_json'))
        result['bounds_mm'] = json.loads(result.pop('bounds_json'))
        result['child_component_ids'] = [r[0] for r in connection.execute(
            'SELECT component_id FROM _component_records WHERE parent_component_id = ? ORDER BY component_id', (component_id,))]
        result.update(status='unregistered' if row['availability'] == 'unregistered' else 'registered',
                      live_verified=False, geometry_available=False)
        if result.pop('effective_summary_stale'):
            result.update(effective_object_count=None, bounds_mm=None, requires_sync=True)
        return result

    def _component_snapshot(self, connection, item, model_path):
        if not isinstance(item, dict) or item.get('complete') is not True or item.get('truncated'):
            raise ValueError('Native Component snapshot must be complete and untruncated.')
        handle = self._component_handle(item.get('component_id'))
        if self._component_model_path(item.get('model_path')) != model_path:
            raise ValueError('Native snapshot belongs to a different document.')
        group = self._component_guid(item.get('rhino_group_id'))
        prior = self._component_read(connection, handle)
        if prior and (prior['model_path'] != model_path or prior['rhino_group_id'] != group):
            raise ValueError('A Component cannot be rebound to another document or Rhino group.')
        name = item.get('name')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('A Component needs its current group name.')
        scenes = self._component_scene_ids(connection, item.get('scene_ids'))
        if not scenes:
            raise ValueError('A Component must belong to at least one scene.')
        availability = item.get('availability', 'present')
        if availability not in {'present', 'missing_group', 'unregistered'}:
            raise ValueError('Unknown Component availability.')
        children = item.get('child_component_ids', [])
        if not isinstance(children, list):
            raise ValueError('Native children must be distinct Component handles.')
        children = [self._component_handle(value) for value in children]
        if len(children) != len(set(children)) or handle in children:
            raise ValueError('Invalid or cyclic Component children.')
        parent = item.get('parent_component_id', prior['parent_component_id'] if prior else None)
        if parent is not None:
            self._component_handle(parent)
            if parent == handle:
                raise ValueError('A Component cannot parent itself.')
        objects = self._component_observed_objects(item, owner=handle)
        if children and 'effective_objects' not in item:
            raise ValueError('Native hierarchy snapshot omitted effective Component members.')
        effective = self._component_observed_objects(dict(complete=True, objects=item.get('effective_objects', objects)))
        direct_ids = [o['rhino_guid'] for o in objects]
        effective_ids = [o['rhino_guid'] for o in effective]
        for field, actual in [('object_ids', direct_ids), ('effective_object_ids', effective_ids)]:
            if field in item and self._component_object_ids(item[field]) != actual:
                raise ValueError('Native object identities and geometry disagree.')
        if availability != 'present' and (objects or effective):
            raise ValueError('An unavailable group cannot supply geometry.')
        effective_map = {o['rhino_guid']: o for o in effective}
        if any(effective_map.get(o['rhino_guid']) != o for o in objects):
            raise ValueError('Native direct and effective geometry disagree.')
        if item.get('requires_sync') or item.get('pending_objects'):
            raise ValueError('Native Component snapshot still requires membership reconciliation.')
        return dict(item, component_id=handle, model_path=model_path, rhino_group_id=group, name=name.strip(),
                    scene_ids=scenes, parent_component_id=parent, child_component_ids=sorted(children),
                    availability=availability, objects=objects, effective_objects=effective,
                    object_ids=direct_ids, direct_object_ids=direct_ids, effective_object_ids=effective_ids,
                    **self._component_summary(objects, effective))

    def _component_validate_tree(self, connection, prepared, model_path):
        """Validate observed relations and transient ownership before any ledger writes."""
        cached = {r[0]: self._component_read(connection, r[0]) for r in connection.execute(
            'SELECT component_id FROM _component_records WHERE model_path = ?', (model_path,))}
        combined = {**cached, **prepared}
        for handle, item in prepared.items():
            for related in item['child_component_ids'] + ([item['parent_component_id']] if item['parent_component_id'] else []):
                if related not in combined:
                    failure = ValueError('Include the unobserved parent/child Component in alignment scope.')
                    failure.native_result = dict(error_code='component_scope_incomplete', mutation_applied=False,
                        missing_component_ids=[related], next_action='Align the missing Component IDs explicitly first.')
                    if related == item['parent_component_id']:
                        failure.native_result['missing_parent_component_ids'] = [related]
                    raise failure
            for child in item['child_component_ids']:
                if child in prepared and prepared[child]['parent_component_id'] != handle:
                    raise ValueError('Alignment parent and child relationship proofs disagree.')
                if child not in prepared and cached[child]['parent_component_id'] not in (None, handle):
                    raise ValueError('Include the former parent and child before reparenting.')
            parent = item['parent_component_id']
            if parent in prepared and handle not in prepared[parent]['child_component_ids']:
                raise ValueError('Alignment parent and child relationship proofs disagree.')
        # Use observed parent edges, including an explicit detach from an observed parent.
        parents = {h: r['parent_component_id'] for h, r in combined.items()}
        for h, item in prepared.items():
            for child, old_parent in list(parents.items()):
                if old_parent == h and child not in item['child_component_ids'] and child not in prepared:
                    parents[child] = None
            for child in item['child_component_ids']:
                parents[child] = h
        for h in combined:
            seen, cursor = set(), h
            while cursor is not None:
                if cursor in seen:
                    raise ValueError('Component hierarchy contains a cycle.')
                seen.add(cursor)
                cursor = parents.get(cursor)
        direct = {}
        for h, item in prepared.items():
            for obj in item['objects']:
                guid = obj['rhino_guid']
                if guid in direct:
                    raise ValueError('Alignment gives one object to unrelated Components.')
                direct[guid] = (h, obj)
        for h, item in prepared.items():
            descendants = {h}
            for candidate in combined:
                cursor = candidate
                while cursor is not None and cursor != h:
                    cursor = parents.get(cursor)
                if cursor == h:
                    descendants.add(candidate)
            observed = {o['rhino_guid']: o for o in item['effective_objects']}
            for obj in observed.values():
                if obj.get('component_id') not in descendants:
                    raise ValueError('Native effective object owner is outside the registered subtree.')
                owner = obj['component_id']
                if owner in prepared and direct.get(obj['rhino_guid']) != (owner, obj):
                    raise ValueError('Native ancestor geometry disagrees with descendant ownership.')
            # A missing parent group may have a living child, which retains its own Scene route.
            if item['availability'] == 'present':
                for owner in descendants.intersection(prepared):
                    for obj in prepared[owner]['objects']:
                        if observed.get(obj['rhino_guid']) != obj:
                            raise ValueError('Native effective membership omitted a descendant object.')
        return cached

    def _component_apply_snapshots(self, connection, snapshots, model_path, operation):
        prepared = {}
        for raw in snapshots:
            item = self._component_snapshot(connection, raw, model_path)
            if item['component_id'] in prepared:
                raise ValueError('Duplicate Component snapshot.')
            prepared[item['component_id']] = item
        cached = self._component_validate_tree(connection, prepared, model_path)
        def signature(item):
            return tuple(item[k] for k in ('name', 'rhino_group_id', 'scene_ids', 'child_component_ids',
                'parent_component_id', 'availability', 'geometry_digest'))
        changed = [h for h, item in prepared.items() if h not in cached or signature(item) != signature(cached[h])
                   or cached[h].get('requires_sync')]
        affected = set()
        unobserved_ancestors = set()
        for h in changed:
            affected.update(prepared[h]['scene_ids'])
            if h in cached:
                affected.update(cached[h]['scene_ids'])
            for ancestor in self._component_ancestor_ids(connection, h):
                affected.update(cached[ancestor]['scene_ids'])
                unobserved_ancestors.add(ancestor)
        now = _utc_now()
        for h in changed:
            item = prepared[h]
            connection.execute("""INSERT INTO ontological_components(ontological_id,project_file_id,rhino_group_id,name,created_at,updated_at,
                availability,geometry_digest,object_count,effective_object_count,object_types_json,bounds_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(ontological_id) DO UPDATE SET
                name=excluded.name,updated_at=excluded.updated_at,availability=excluded.availability,
                geometry_digest=excluded.geometry_digest,
                object_count=excluded.object_count,effective_object_count=excluded.effective_object_count,
                object_types_json=excluded.object_types_json,bounds_json=excluded.bounds_json,effective_summary_stale=0""",
                (h, self._project_file_reference(connection, model_path=model_path), item['rhino_group_id'], item['name'], now, now, item['availability'],
                 item['geometry_digest'], item['object_count'],
                 item['effective_object_count'], json.dumps(item['object_types']), json.dumps(item['bounds_mm'])))
            connection.execute('DELETE FROM ontological_scene_context WHERE ontological_id=?',(h,))
            connection.executemany('INSERT INTO ontological_scene_context VALUES(?,?)',[(h,scene) for scene in item['scene_ids']])
        if changed:
            # Clear observed edges first so valid simultaneous reparenting is order independent.
            for h in prepared:
                connection.execute('UPDATE ontological_components SET parent_ontological_id = NULL WHERE ontological_id = ? OR parent_ontological_id = ?', (h, h))
            for h, item in prepared.items():
                for child in item['child_component_ids']:
                    connection.execute('UPDATE ontological_components SET parent_ontological_id = ? WHERE ontological_id = ?', (h, child))
            for h, item in prepared.items():
                connection.execute('UPDATE ontological_components SET parent_ontological_id = ? WHERE ontological_id = ?', (item['parent_component_id'], h))
            self._component_canonical_scene_links(connection, model_path)
            for h in changed:
                for ancestor in self._component_ancestor_ids(connection, h):
                    affected.update(self._component_read(connection, ancestor)['scene_ids'])
                    unobserved_ancestors.add(ancestor)
            # A child-only observation cannot certify an ancestor's aggregate
            # geometry. Retain direct summaries but hide obsolete effective data.
            connection.executemany('UPDATE ontological_components SET effective_summary_stale=1 WHERE ontological_id=?',
                [(h,) for h in unobserved_ancestors - prepared.keys()])
        revisions = {scene: self._record_revision(connection, scene, operation, {'component_ids': changed})
                     for scene in sorted(affected)}
        return prepared, changed, revisions

    def get_component(self, component_id, live=False, native_inspect=None):
        with self._connect() as connection:
            connection.execute('BEGIN')
            cached = self._component_read(connection, component_id)
            if cached is None:
                return None
            if not live:
                return {k: v for k, v in cached.items() if k != 'geometry_digest'}
            if not callable(native_inspect):
                raise ValueError('A native read-only inspection is required for live=True.')
            reply = self._component_native(native_inspect, dict(type='design_component', action='inspect',
                expected_model_path=cached['model_path'], component_id=component_id, rhino_group_id=cached['rhino_group_id']))
            item = self._component_snapshot(connection, reply.get('component'), cached['model_path'])
            if item['component_id'] != component_id:
                raise ValueError('Native Component identity differs from the requested identity.')
            # Read-only observations do not update even group summaries in SQLite.
            needs_sync = bool(cached.get('requires_sync')) or any(item[k] != cached[k] for k in ('name','scene_ids','child_component_ids',
                'parent_component_id','availability','geometry_digest'))
            return {k: v for k, v in {**cached, **item, 'live_verified':True, 'geometry_available':True,
                'requires_sync':needs_sync, 'object_names':list(dict.fromkeys(o['name'] for o in item['objects'] if o.get('name')))}.items()
                if k != 'geometry_digest'}

    def list_components(self, model_path='', scene_id='', recursive=False):
        model_path = self._component_model_path(model_path) if model_path else ''
        if type(recursive) is not bool:
            raise ValueError('recursive must be a boolean.')
        with self._connect() as connection:
            if scene_id:
                self._component_scene_ids(connection, [scene_id])
            rows = connection.execute("""WITH RECURSIVE scoped(component_id) AS (
                SELECT component_id FROM _scene_component_refs WHERE scene_id = ? UNION
                SELECT c.component_id FROM _component_records c JOIN scoped p ON c.parent_component_id = p.component_id WHERE ?)
                SELECT component_id FROM _component_records WHERE (? = '' OR model_path = ?)
                AND (? = '' OR component_id IN (SELECT component_id FROM scoped))
                AND (? OR ? != '' OR parent_component_id IS NULL) ORDER BY model_path,name,component_id""",
                (scene_id,recursive,model_path,model_path,scene_id,recursive,scene_id)).fetchall()
            return [{k:v for k,v in self._component_read(connection,r[0]).items() if k != 'geometry_digest'} for r in rows]

    def upsert_component(self, model_path, name, object_ids, scene_ids=None, component_id='', rhino_group_id='',
                         native_apply=None, child_component_ids=None):
        model_path = self._component_model_path(model_path)
        handle = self._component_handle(component_id or f'component_{uuid.uuid4().hex[:12]}')
        ids = self._component_object_ids(object_ids)
        if not isinstance(name, str) or not name.strip():
            raise ValueError('A Component needs a name.')
        name = name.strip()
        group = self._component_guid(rhino_group_id) if rhino_group_id else ''
        if not callable(native_apply):
            raise ValueError('Native Component registration is required.')
        attempted = False
        try:
            with self._connect() as connection:
                connection.execute('BEGIN IMMEDIATE')
                prior = self._component_read(connection, handle)
                if prior:
                    if prior['model_path'] != model_path or (group and group != prior['rhino_group_id']):
                        raise ValueError('The Component belongs to a different model_path or Rhino group.')
                    group = prior['rhino_group_id']
                if group:
                    owner = connection.execute('SELECT component_id FROM _component_records WHERE model_path=? AND rhino_group_id=?', (model_path,group)).fetchone()
                    if owner and owner[0] != handle:
                        raise ValueError('The Rhino group is already registered as another component.')
                scenes = self._component_scene_ids(connection, scene_ids if scene_ids is not None else (prior['scene_ids'] if prior else []))
                children = self._component_child_ids(connection,handle,model_path,
                    child_component_ids if child_component_ids is not None else (prior['child_component_ids'] if prior else []))
                if not scenes:
                    raise ValueError('A component must belong to at least one scene.')
                if not ids and not children:
                    raise ValueError('A Component needs a direct object or existing child Component.')
                attempted = True
                reply = self._component_native(native_apply,dict(type='design_component',action='upsert',
                    expected_model_path=model_path,component_id=handle,rhino_group_id=group,name=name,
                    object_ids=ids,scene_ids=scenes,child_component_ids=children))
                item = self._component_snapshot(connection,reply.get('component'),model_path)
                if (item['component_id'] != handle or item['name'] != name or item['object_ids'] != ids
                        or item['scene_ids'] != scenes or item['child_component_ids'] != children
                        or (group and item['rhino_group_id'] != group)
                        or item['parent_component_id'] != (prior['parent_component_id'] if prior else None)):
                    raise ValueError('Native Component registration differs from the requested identity or membership.')
                related = reply.get('affected_components') or []
                if not isinstance(related,list):
                    raise ValueError('affected_components must be a list.')
                allowed = set(children) | set(prior['child_component_ids'] if prior else []) | set(self._component_ancestor_ids(connection,handle))
                if any(not isinstance(r,dict) or r.get('component_id') not in allowed for r in related):
                    raise ValueError('Native response contains unrelated affected Components.')
                changed_children = set(children) ^ set(prior['child_component_ids'] if prior else [])
                if not changed_children.issubset(r.get('component_id') for r in related):
                    raise ValueError('Native response omitted changed child Component proof.')
                prepared, _, revisions = self._component_apply_snapshots(connection,[item]+related,model_path,'upsert_component')
                result = dict(self._component_read(connection,handle), **{k:v for k,v in prepared[handle].items() if k not in {'status'}})
                result.update(live_verified=True,geometry_available=True,scene_revisions=revisions)
                result.pop('geometry_digest',None)
                return result
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise ComponentReconciliationError(handle,model_path,str(exc)) from exc
            raise

    def align_components(self, model_path, component_ids=None, scene_id='', native_inspect=None, expected_groups=None):
        model_path = self._component_model_path(model_path)
        if not callable(native_inspect):
            raise ValueError('A native read-only Component observation is required.')
        if scene_id and component_ids is not None:
            raise ValueError('Use a Component target or a Scene scope, not both.')
        if component_ids is not None:
            if not isinstance(component_ids,list) or not 1 <= len(component_ids) <= 64:
                raise ValueError('component_ids must contain 1 to 64 distinct Component handles.')
            component_ids = [self._component_handle(h) for h in component_ids]
            if len(set(component_ids)) != len(component_ids):
                raise ValueError('component_ids must not contain duplicates.')
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            cached = {r[0]:self._component_read(connection,r[0]) for r in connection.execute('SELECT component_id FROM _component_records WHERE model_path=?',(model_path,))}
            ids = component_ids
            if scene_id:
                self._component_scene_ids(connection,[scene_id])
                ids = [r[0] for r in connection.execute('SELECT component_id FROM _scene_component_refs WHERE scene_id=?',(scene_id,)) if r[0] in cached]
            if ids is not None:
                ids = sorted(set(child for h in ids for child in (self._component_descendant_ids(connection,h) if h in cached else [h])))
                if len(ids)>64:
                    raise ValueError('Narrow alignment to at most 64 Components including descendants.')
            seeds = [{k:r[k] for k in ('component_id','rhino_group_id','name','scene_ids','child_component_ids')}
                     for h,r in cached.items() if ids is None or h in ids]
            reply = self._component_native(native_inspect,dict(type='design_component',action='inspect_many',
                expected_model_path=model_path,component_ids=ids,scene_id=scene_id,discover_scene=bool(scene_id),registrations=seeds))
            if (reply.get('complete') is not True or reply.get('truncated') or self._component_model_path(reply.get('model_path')) != model_path):
                raise ValueError('Alignment needs a complete snapshot of the requested document scope.')
            if not isinstance(reply.get('editing'),dict) or reply['editing'].get('stable') is not True:
                raise ValueError('Finish group/block editing before alignment; editing scope is not stable.')
            snapshots, problems = reply.get('components'), reply.get('problems',[])
            if not isinstance(snapshots,list) or not isinstance(problems,list) or len(snapshots)>64:
                raise ValueError('Alignment must report at most 64 snapshots and item-specific problems.')
            prepared = {}
            for raw in snapshots:
                item = self._component_snapshot(connection,raw,model_path)
                h = item['component_id']
                if h in prepared:
                    raise ValueError('Duplicate Component snapshot.')
                if expected_groups and h in expected_groups and item['rhino_group_id'] != self._component_guid(expected_groups[h]):
                    raise ValueError('Native observation does not match the supplied group GUID.')
                prepared[h]=item
            scoped=set(ids or [])
            if scene_id:
                scoped.update(h for h,r in prepared.items() if scene_id in r['scene_ids'])
            pending=list(scoped)
            while pending:
                for child in prepared.get(pending.pop(),{}).get('child_component_ids',[]):
                    if child not in scoped:
                        scoped.add(child)
                        pending.append(child)
            if ids is not None and not set(prepared).issubset(scoped):
                raise ValueError('Native observation contains an out-of-scope Component.')
            reported=set(prepared)|{p.get('component_id') for p in problems if isinstance(p,dict)}
            if not set(ids if ids is not None else cached).issubset(reported):
                raise ValueError('Alignment omitted requested Component identities.')
            # Tombstones unknown to this ledger do not create new inactive registrations.
            prepared={h:r for h,r in prepared.items() if h in cached or r['availability']!='unregistered'}
            applied,changed,revisions=self._component_apply_snapshots(connection,list(prepared.values()),model_path,'align_components')
            return dict(status='success',checked=len(applied),changed=len(changed),
                unavailable=sum(r['availability']!='present' for r in applied.values()),problems=problems,
                scene_revisions=revisions,live_verified=not problems)

    def sync_component(self, model_path, component_id, rhino_group_id='', native_inspect=None):
        self.align_components(model_path,[component_id],native_inspect=native_inspect,
            expected_groups={component_id:rhino_group_id} if rhino_group_id else None)
        return self.get_component(component_id)

    def unregister_component(self, component_id, native_apply=None):
        if not callable(native_apply):
            raise ValueError('Native Component unregistration is required.')
        attempted=False
        model_path=''
        try:
            with self._connect() as connection:
                connection.execute('BEGIN IMMEDIATE')
                prior=self._component_read(connection,component_id)
                if prior is None:
                    raise KeyError(f'Unknown component_id: {component_id}')
                self._component_require_unreferenced(connection,component_id)
                model_path=prior['model_path']
                attempted=True
                reply=self._component_native(native_apply,dict(type='design_component',action='unregister',
                    expected_model_path=model_path,component_id=component_id,rhino_group_id=prior['rhino_group_id']))
                if (reply.get('component_id')!=component_id or self._component_model_path(reply.get('model_path'))!=model_path
                        or self._component_guid(reply.get('rhino_group_id'))!=prior['rhino_group_id']):
                    raise ValueError('Native unregistration acknowledgement does not match the Component.')
                detached=reply.get('detached_child_component_ids',[])
                if not isinstance(detached,list) or sorted(detached)!=prior['child_component_ids']:
                    raise ValueError('Native detached child IDs differ from the registered tree.')
                related=reply.get('affected_components',[])
                if (not isinstance(related,list) or any(not isinstance(r,dict) for r in related)
                        or sorted(r.get('component_id','') for r in related)!=sorted(detached)):
                    raise ValueError('Native response omitted detached child Component proof.')
                if any(r.get('parent_component_id') is not None for r in related):
                    raise ValueError('Native detached child still has a parent.')
                _,_,revisions=self._component_apply_snapshots(connection,related,model_path,'detach_components')
                connection.execute('DELETE FROM ontological_components WHERE ontological_id=?',(component_id,))
                self._component_canonical_scene_links(connection,model_path)
                for scene in prior['scene_ids']:
                    revisions[scene]=self._record_revision(connection,scene,'unregister_component',{'component_id':component_id})
                return dict(component_id=component_id,model_path=model_path,rhino_group_id=prior['rhino_group_id'],
                    status='unregistered',live_verified=True,scene_revisions=revisions)
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise ComponentReconciliationError(component_id,model_path,str(exc)) from exc
            raise
    @staticmethod
    def _component_require_unreferenced(connection, component_id):
        node = connection.execute(
            "SELECT parent_component_id FROM _component_records WHERE component_id = ?", (component_id,)
        ).fetchone()
        if node and node["parent_component_id"] is not None:
            raise ValueError(read_instruction(__file__, 'response-491'))
        if connection.execute(
            "SELECT 1 FROM _plan_component_refs WHERE component_id = ? "
            "UNION ALL SELECT 1 FROM _step_component_refs WHERE component_id = ? LIMIT 1",
            (component_id, component_id),
        ).fetchone():
            raise ValueError(
                read_instruction(__file__, 'response-492')
            )
