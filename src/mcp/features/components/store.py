"""Component ledger rules mixed into the shared AlmondStore connection lifecycle."""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

import math
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
                    model_path, rhino_guid, object_type, name,
                    min_x, max_x, min_y, max_y, min_z, max_z, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_path, rhino_guid) DO UPDATE SET
                    object_type = excluded.object_type, name = excluded.name,
                    min_x = excluded.min_x, max_x = excluded.max_x,
                    min_y = excluded.min_y, max_y = excluded.max_y,
                    min_z = excluded.min_z, max_z = excluded.max_z,
                    observed_at = excluded.observed_at
                """,
                (model_path, obj["rhino_guid"], obj["object_type"], obj.get("name", ""),
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
                "SELECT model_path, parent_component_id, scene_ids_json FROM components WHERE component_id = ?", (child_id,)
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
    def _component_object_row(item):
        return {"rhino_guid": item["rhino_guid"], "object_type": item["object_type"],
                "name": item["name"] if "name" in item.keys() else "",
                "component_id": item["component_id"],
                "bounds_mm": [item["min_x"], item["min_y"], item["min_z"],
                              item["max_x"], item["max_y"], item["max_z"]],
                "observed_at": item["observed_at"]}

    @staticmethod
    def _canonical_component_refs(connection, values):
        """Retain a requested child only when none of its requested ancestors is present."""
        selected = set(values)
        rows = connection.execute("SELECT component_id, parent_component_id, availability FROM components").fetchall()
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
        rows = connection.execute("SELECT component_id, parent_component_id, scene_ids_json, availability FROM components WHERE model_path = ?",
                                  (model_path,)).fetchall()
        parents = {row[0]: row[1] for row in rows}
        availability = {row[0]: row[3] for row in rows}
        contexts = {row[0]: json.loads(row[2]) if row[3] != "unregistered" else [] for row in rows}
        for handle, scenes in contexts.items():
            connection.execute("DELETE FROM scene_components WHERE component_id = ?", (handle,))
            for scene in scenes:
                ancestor, seen, redundant = parents[handle], set(), False
                while ancestor is not None and ancestor not in seen:
                    seen.add(ancestor)
                    if availability.get(ancestor) == "present" and scene in contexts.get(ancestor, []):
                        redundant = True
                        break
                    ancestor = parents.get(ancestor)
                if not redundant:
                    connection.execute("INSERT INTO scene_components(scene_id, component_id) VALUES (?, ?)", (scene, handle))

    @staticmethod
    def _component_read(connection, component_id):
        row = connection.execute(
            "SELECT * FROM components WHERE component_id = ?", (component_id,)
        ).fetchone()
        if row is None:
            return None
        objects = [
            ComponentsStore._component_object_row(item)
            for item in connection.execute(
                "SELECT * FROM document_objects WHERE component_id = ? ORDER BY rhino_guid",
                (component_id,),
            )
        ]
        effective_objects = [ComponentsStore._component_object_row(item) for item in connection.execute("""
            WITH RECURSIVE subtree(component_id) AS (
                SELECT component_id FROM components WHERE component_id = ? AND availability = 'present'
                UNION SELECT c.component_id FROM components c
                    JOIN subtree parent ON c.parent_component_id = parent.component_id
            )
            SELECT o.* FROM document_objects o JOIN subtree s ON o.component_id = s.component_id
                JOIN components c ON c.component_id = o.component_id AND c.availability = 'present'
            ORDER BY o.model_path, o.rhino_guid
        """, (component_id,))]
        children = [item["component_id"] for item in connection.execute(
            "SELECT component_id FROM components WHERE parent_component_id = ? ORDER BY component_id",
            (component_id,),
        )]
        return {
            **{key: value for key, value in dict(row).items() if key != "scene_ids_json"},
            "status": "unregistered" if row["availability"] == "unregistered" else "registered", "live_verified": False,
            "scene_ids": json.loads(row["scene_ids_json"]),
            "object_ids": [item["rhino_guid"] for item in objects],
            "object_count": len(objects), "objects": objects,
            "direct_object_ids": [item["rhino_guid"] for item in objects],
            "child_component_ids": children,
            "effective_objects": effective_objects,
            "effective_object_ids": [item["rhino_guid"] for item in effective_objects],
            "effective_object_count": len(effective_objects),
            "pending_objects": [], "requires_sync": False,
            "object_names": list(dict.fromkeys(obj["name"] for obj in objects if obj.get("name"))),
            "object_types": {kind: sum(obj["object_type"] == kind for obj in objects)
                             for kind in sorted({obj["object_type"] for obj in objects})},
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
            effective_ids = cached["effective_object_ids"]
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
                    (obj["rhino_guid"], obj["object_type"], obj.get("component_id"), obj.get("name", ""), obj["bounds_mm"])
                    for obj in effective
                ] != [
                    (obj["rhino_guid"], obj["object_type"], obj["component_id"], obj.get("name", ""), obj["bounds_mm"])
                    for obj in cached["effective_objects"]
                ]
            elif "effective_object_ids" in observed:
                effective_ids = self._component_object_ids(observed["effective_object_ids"])
                effective_changed = effective_ids != cached["effective_object_ids"]
            changed = (direct_ids != cached["object_ids"] or children != cached["child_component_ids"]
                       or native_scenes != cached["scene_ids"] or observed.get("name") != cached["name"]
                       or effective_changed
                       or ("parent_component_id" in observed and
                           observed["parent_component_id"] != cached["parent_component_id"])
                       or any((prior["object_type"], prior.get("name", ""), prior["bounds_mm"]) !=
                              (obj["object_type"], obj.get("name", ""), obj["bounds_mm"])
                              for prior, obj in zip(cached["objects"], objects)))
            result = dict(cached)
            result.update(observed)
            result.update(object_ids=direct_ids, direct_object_ids=direct_ids, objects=objects,
                          object_count=len(objects), effective_object_count=len(effective_ids),
                          object_names=list(dict.fromkeys(obj["name"] for obj in objects if obj.get("name"))),
                          object_types={kind: sum(obj["object_type"] == kind for obj in objects)
                                        for kind in sorted({obj["object_type"] for obj in objects})},
                          scene_ids=native_scenes, child_component_ids=children,
                          pending_objects=pending, live_verified=True,
                          requires_sync=bool(changed or pending or observed.get("requires_sync")))
            return result

    def list_components(self, model_path: str = "", scene_id: str = "", recursive: bool = False) -> list[dict[str, Any]]:
        model_path = self._component_model_path(model_path) if model_path else ""
        if type(recursive) is not bool:
            raise ValueError("recursive must be a boolean.")
        with self._connect() as connection:
            if scene_id:
                self._component_scene_ids(connection, [scene_id])
            rows = connection.execute(
                "WITH RECURSIVE scoped(component_id) AS ("
                "SELECT component_id FROM scene_components WHERE scene_id = ? UNION "
                "SELECT child.component_id FROM components child JOIN scoped parent "
                "ON child.parent_component_id = parent.component_id WHERE ?) "
                "SELECT component_id FROM components "
                "WHERE (? = '' OR model_path = ?) "
                "AND (? = '' OR component_id IN (SELECT component_id FROM scoped)) "
                "AND (? OR ? != '' OR parent_component_id IS NULL) "
                "ORDER BY model_path, name, component_id",
                (scene_id, recursive, model_path, model_path, scene_id, recursive, scene_id),
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
            raise ValueError(read_instruction(__file__, 'response-476'))
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
            INSERT INTO components(component_id, model_path, rhino_group_id, name, created_at, updated_at, scene_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(component_id) DO UPDATE SET name = excluded.name, updated_at = excluded.updated_at,
                scene_ids_json = excluded.scene_ids_json, availability = 'present'
            """, (component_id, model_path, group_id, name, now, now, json.dumps(scenes)),
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
        self._component_canonical_scene_links(connection, model_path)
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

    def align_components(self, model_path: str, component_ids: list[str] | None = None,
                         scene_id: str = "", native_inspect: Callable | None = None,
                         expected_groups: dict[str, str] | None = None) -> dict[str, Any]:
        """Import a complete, stable group observation; never request a native edit."""
        model_path = self._component_model_path(model_path)
        if not callable(native_inspect):
            raise ValueError("A native read-only Component observation is required.")
        if scene_id and component_ids is not None:
            raise ValueError("Use a Component target or a Scene scope, not both.")
        discover_scene = bool(scene_id)
        if component_ids is not None:
            if not isinstance(component_ids, list) or not component_ids or len(component_ids) > 64:
                raise ValueError("component_ids must contain 1 to 64 distinct Component handles.")
            ids = [self._component_handle(value) for value in component_ids]
            if len(set(ids)) != len(ids):
                raise ValueError("component_ids must not contain duplicates.")
        else:
            ids = None
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cached = {row["component_id"]: self._component_read(connection, row["component_id"])
                      for row in connection.execute("SELECT component_id FROM components WHERE model_path = ?", (model_path,))}
            if scene_id:
                self._component_scene_ids(connection, [scene_id])
                scoped = {row[0] for row in connection.execute(
                    "SELECT component_id FROM scene_components WHERE scene_id = ?", (scene_id,))}
                ids = [value for value in (ids if ids is not None else cached) if value in scoped]
            if ids is not None:
                ids = list(dict.fromkeys(child for handle in ids for child in (
                    self._component_descendant_ids(connection, handle) if handle in cached else [handle])))
                if len(ids) > 64:
                    raise ValueError("Narrow alignment to at most 64 Component registrations including descendants.")
            seeds = [{key: value[key] for key in ("component_id", "rhino_group_id", "name", "scene_ids", "child_component_ids")}
                     for handle, value in cached.items() if ids is None or handle in ids]
            prior_rows = connection.execute("SELECT * FROM document_objects WHERE model_path = ?", (model_path,)).fetchall()
            if ids is not None:
                direct_scene_ids = {row[0] for row in connection.execute(
                    "SELECT object_rowid FROM scene_objects WHERE scene_id = ?", (scene_id,))} if scene_id else set()
                prior_rows = [row for row in prior_rows if row["component_id"] in ids or row["id"] in direct_scene_ids]
            prior_objects = {row["rhino_guid"]: self._component_object_row(row) for row in prior_rows}
            reply = self._component_native(native_inspect, dict(
                type="design_component", action="inspect_many", expected_model_path=model_path,
                component_ids=ids, scene_id=scene_id, discover_scene=discover_scene, registrations=seeds,
                prior_object_ids=sorted(prior_objects)))
            if (reply.get("complete") is not True or reply.get("truncated")
                    or self._component_model_path(reply.get("model_path")) != model_path):
                raise ValueError("Alignment needs a complete snapshot of the requested document scope.")
            if not isinstance(reply.get("editing"), dict) or reply["editing"].get("stable") is not True:
                raise ValueError("Finish group/block editing before aligning Component records; editing scope is not stable.")
            snapshots, problems = reply.get("components"), reply.get("problems", [])
            if not isinstance(snapshots, list) or not isinstance(problems, list):
                raise ValueError("Alignment must report Component snapshots and item-specific problems.")
            prepared, inactive = {}, set()
            for item in snapshots:
                if not isinstance(item, dict) or item.get("complete") is not True or item.get("truncated"):
                    raise ValueError("Alignment contains an incomplete Component snapshot.")
                handle = self._component_handle(item.get("component_id"))
                if handle in prepared:
                    raise ValueError("Alignment contains a duplicate or out-of-scope Component.")
                if self._component_model_path(item.get("model_path")) != model_path:
                    raise ValueError("Alignment contains a different document.")
                group = self._component_guid(item.get("rhino_group_id"))
                if expected_groups and handle in expected_groups and group != self._component_guid(expected_groups[handle]):
                    raise ValueError("Native observation does not match the supplied persistent group GUID.")
                prior = cached.get(handle)
                if prior is None:
                    other = connection.execute("SELECT model_path FROM components WHERE component_id = ?", (handle,)).fetchone()
                    if other is not None and other["model_path"] != model_path:
                        raise ValueError("Alignment contains a Component registered to another model.")
                if prior and prior["rhino_group_id"] != group:
                    raise ValueError("Alignment cannot rebind a Component to another Rhino group.")
                scenes = self._component_scene_ids(connection, item.get("scene_ids"))
                if not scenes or not isinstance(item.get("name"), str):
                    raise ValueError("A Component needs its current group name and existing Scene context.")
                availability = item.get("availability", "present")
                if availability not in {"present", "missing_group", "unregistered"}:
                    raise ValueError("Unknown Component availability.")
                if availability == "unregistered" and prior is None:
                    inactive.add(handle)
                    continue
                objects = self._component_observed_objects(item, owner=handle)
                effective = self._component_observed_objects(dict(
                    complete=True, objects=item.get("effective_objects", item["objects"])))
                if "effective_object_ids" in item and self._component_object_ids(item["effective_object_ids"]) != [obj["rhino_guid"] for obj in effective]:
                    raise ValueError("Alignment effective geometry and object identities disagree.")
                if availability != "present" and objects:
                    raise ValueError("An unavailable group cannot supply geometry.")
                children = item.get("child_component_ids", [])
                if not isinstance(children, list) or len(set(children)) != len(children):
                    raise ValueError("Invalid Component children.")
                for child in children:
                    self._component_handle(child)
                parent = item.get("parent_component_id", prior["parent_component_id"] if prior else None)
                if parent is not None:
                    self._component_handle(parent)
                    if parent == handle:
                        raise ValueError("A Component cannot parent itself.")
                prepared[handle] = dict(item, rhino_group_id=group, scene_ids=scenes,
                                        objects=objects, effective_objects=effective,
                                        availability=availability, child_component_ids=children, parent_component_id=parent)
            if len(prepared) > 64:
                raise ValueError("Narrow alignment to at most 64 Component registrations including descendants.")
            if ids is not None:
                scoped_members = set(ids)
                if discover_scene:
                    scoped_members.update(handle for handle, item in prepared.items() if scene_id in item["scene_ids"])
                pending = list(scoped_members)
                while pending:
                    handle = pending.pop()
                    if handle not in prepared:
                        continue
                    for child in prepared[handle]["child_component_ids"]:
                        if child in prepared and child not in scoped_members:
                            scoped_members.add(child)
                            pending.append(child)
                if not set(prepared).issubset(scoped_members):
                    raise ValueError("Native observation contains an out-of-scope Component.")
            missing_parents = {item["parent_component_id"] for item in prepared.values()
                               if item["parent_component_id"] is not None
                               and item["parent_component_id"] not in prepared
                               and item["parent_component_id"] not in cached}
            if missing_parents:
                failure = ValueError("The observed hierarchy needs an uncached parent; align its explicit ID scope or its Scene first.")
                failure.native_result = dict(error_code="component_scope_incomplete", mutation_applied=False,
                    missing_parent_component_ids=sorted(missing_parents),
                    next_action="Align the listed parent Component IDs explicitly, or align their Scene, then retry this Scene.")
                raise failure
            missing_presence = {handle for handle in prepared if handle in cached
                                and any(guid not in prior_objects for guid in cached[handle]["object_ids"])}
            if missing_presence:
                failure = ValueError("Expand the Component presence scope to include the listed IDs.")
                failure.native_result = dict(error_code="component_scope_incomplete", mutation_applied=False,
                    required_component_ids=sorted(set(ids or []) | set(prepared)),
                    next_action="Align the listed Component IDs together to observe prior object presence before updating DB records.")
                raise failure
            # Missing/incomplete results never silently erase omitted ledger rows.
            reported = set(prepared) | inactive | {item.get("component_id") for item in problems if isinstance(item, dict)}
            required = set(ids if ids is not None else cached)
            if not required.issubset(reported):
                raise ValueError("Alignment omitted requested Component identities.")
            absent = self._component_object_ids(reply.get("absent_object_ids", []))
            detached = self._component_observed_objects(dict(complete=True, objects=reply.get("detached_objects", [])))
            if (absent or detached) and reply.get("presence_complete") is not True:
                raise ValueError("Cached-object presence needs complete stable native proof.")
            observed_ids = {obj["rhino_guid"] for item in prepared.values() for obj in item["effective_objects"]}
            detached_ids = {obj["rhino_guid"] for obj in detached}
            if (not (set(absent) | detached_ids).issubset(prior_objects)
                    or set(absent) & (observed_ids | detached_ids) or detached_ids & observed_ids):
                raise ValueError("Cached-object presence proof is contradictory or outside the requested scope.")
            # Invalid registrations keep their previous snapshot. Never use an
            # unrelated missing-object report to erase another owner's rows.
            absent = [guid for guid in absent if prior_objects[guid]["component_id"] is None
                      or prior_objects[guid]["component_id"] in prepared]
            def object_signature(obj):
                return (obj["object_type"], obj["bounds_mm"], obj.get("name", ""))
            detached_changes = [obj for obj in detached
                                if object_signature(obj) != object_signature(prior_objects[obj["rhino_guid"]])]
            direct = {}
            for handle, item in prepared.items():
                for obj in item["objects"]:
                    guid = obj["rhino_guid"]
                    if guid in direct:
                        raise ValueError("Alignment gives one object to unrelated Components.")
                    direct[guid] = handle
            # An unaffected/invalid Component's objects must not be stolen by this batch.
            for guid, owner in direct.items():
                row = connection.execute("SELECT component_id FROM document_objects WHERE model_path = ? AND rhino_guid = ?",
                                         (model_path, guid)).fetchone()
                if row and row[0] and row[0] != owner and row[0] not in prepared:
                    raise ValueError("Alignment conflicts with an unobserved Component owner.")
            changed = []
            for handle, item in prepared.items():
                prior = cached.get(handle)
                def signature(value):
                    return (value["name"], value["rhino_group_id"], value["scene_ids"],
                            value["child_component_ids"], value.get("parent_component_id"), value.get("availability", "present"),
                            [(o["rhino_guid"], o["object_type"], o["bounds_mm"], o.get("name", "")) for o in value["objects"]],
                            [(o["rhino_guid"], o.get("component_id"), o["object_type"], o["bounds_mm"], o.get("name", ""))
                             for o in value["effective_objects"]])
                if prior is None or signature(prior) != signature(item):
                    changed.append(handle)
            if not changed and not absent and not detached_changes:
                return dict(status="success", checked=len(prepared), changed=0,
                            unavailable=sum(item["availability"] != "present" for item in prepared.values()),
                            removed_objects=0, refreshed_objects=0, problems=problems,
                            scene_revisions={}, live_verified=not problems)
            now = _utc_now()
            affected_scenes = self._component_affected_scenes(connection, model_path,
                absent + [obj["rhino_guid"] for obj in detached_changes])
            changed_objects = set()
            for handle in changed:
                item = prepared[handle]
                prior = cached.get(handle)
                affected_scenes.update(item["scene_ids"])
                affected_scenes.update(prior["scene_ids"] if prior else [])
                changed_objects.update(obj["rhino_guid"] for obj in item["effective_objects"])
                changed_objects.update(prior["effective_object_ids"] if prior else [])
            affected_scenes.update(self._component_affected_scenes(connection, model_path, changed_objects))
            for handle in changed:
                item = prepared[handle]
                connection.execute("""INSERT INTO components(component_id, model_path, rhino_group_id, name, created_at, updated_at, availability, scene_ids_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(component_id) DO UPDATE SET
                    name=excluded.name, updated_at=excluded.updated_at, availability=excluded.availability,
                    scene_ids_json=excluded.scene_ids_json""",
                    (handle, model_path, item["rhino_group_id"], item["name"], now, now, item["availability"], json.dumps(item["scene_ids"])))
            for handle in prepared:
                connection.execute("UPDATE document_objects SET component_id = NULL WHERE model_path = ? AND component_id = ?",
                                   (model_path, handle))
            for handle, item in prepared.items():
                if handle in changed:
                    self._component_cache_objects(connection, model_path, item["objects"])
                    connection.execute("DELETE FROM scene_components WHERE component_id = ?", (handle,))
                    connection.executemany("INSERT INTO scene_components(scene_id, component_id) VALUES (?, ?)",
                                           [(scene, handle) for scene in item["scene_ids"]])
                connection.executemany("UPDATE document_objects SET component_id = ? WHERE model_path = ? AND rhino_guid = ?",
                                       [(handle, model_path, obj["rhino_guid"]) for obj in item["objects"]])
            # Only relations explicitly observed in this scope can change.
            for handle in prepared:
                connection.execute("UPDATE components SET parent_component_id = NULL WHERE parent_component_id = ?", (handle,))
            for handle, item in prepared.items():
                for child in item["child_component_ids"]:
                    row = connection.execute("SELECT model_path FROM components WHERE component_id = ?", (child,)).fetchone()
                    if row is None or row[0] != model_path:
                        raise ValueError("Alignment references an unobserved child Component.")
                    connection.execute("UPDATE components SET parent_component_id = ? WHERE component_id = ?", (handle, child))
            for handle, item in prepared.items():
                parent = item["parent_component_id"]
                if parent is not None:
                    row = connection.execute("SELECT model_path FROM components WHERE component_id = ?", (parent,)).fetchone()
                    if row is None or row[0] != model_path:
                        raise ValueError("Include the new semantic parent in the alignment scope.")
                connection.execute("UPDATE components SET parent_component_id = ? WHERE component_id = ?", (parent, handle))
            for handle, item in prepared.items():
                current = self._component_read(connection, handle)
                if current["child_component_ids"] != sorted(item["child_component_ids"]):
                    raise ValueError("Alignment parent and child relationship proofs disagree.")
            self._component_canonical_scene_links(connection, model_path)
            affected_scenes.update(self._component_affected_scenes(connection, model_path, changed_objects))
            for handle, item in prepared.items():
                self._component_check_native_effective(item, self._component_read(connection, handle), require=True)
            self._component_cache_objects(connection, model_path, detached_changes)
            connection.executemany("DELETE FROM document_objects WHERE model_path = ? AND rhino_guid = ?",
                                   [(model_path, guid) for guid in absent])
            revisions = {scene: self._record_revision(connection, scene, "align_components", {"component_ids": changed})
                         for scene in sorted(affected_scenes)}
        return dict(status="success", checked=len(prepared), changed=len(changed),
                    unavailable=sum(item["availability"] != "present" for item in prepared.values()),
                    removed_objects=len(absent), refreshed_objects=len(detached_changes),
                    problems=problems, scene_revisions=revisions, live_verified=not problems)

    @staticmethod
    def _component_require_unreferenced(connection, component_id):
        node = connection.execute(
            "SELECT parent_component_id FROM components WHERE component_id = ?", (component_id,)
        ).fetchone()
        if node and node["parent_component_id"] is not None:
            raise ValueError(read_instruction(__file__, 'response-491'))
        if connection.execute(
            "SELECT 1 FROM generation_plan_components WHERE component_id = ? "
            "UNION ALL SELECT 1 FROM generation_step_components WHERE component_id = ? LIMIT 1",
            (component_id, component_id),
        ).fetchone():
            raise ValueError(
                read_instruction(__file__, 'response-492')
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
        self._component_canonical_scene_links(connection, model_path)
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
                self._component_canonical_scene_links(connection, model_path)
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
