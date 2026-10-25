"""Feature-owned Phase/Plan/Step SQL for the composed AlmondStore facade."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from almond_mcp.store_common import _utc_now, _json, _decode


class PlanningStore:
    """Planning rules using the facade's shared connection and component reader."""

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
