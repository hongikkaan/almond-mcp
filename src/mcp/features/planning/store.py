"""Feature-owned Phase/Plan/Step SQL for the composed AlmondStore facade."""

from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

import sqlite3
import uuid
from typing import Any

from almond_mcp.store_common import _utc_now, _json, _decode
from almond_mcp.features.planning.updates import StringListPatch, PlanningUpdate, apply_list_patch
from almond_mcp.features.planning.schema import previous_reference


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
        from almond_mcp.features.planning.schema import initialize_workflow
        initialize_workflow(connection)
        additions = {
            "generation_plans": {
                "title": "TEXT NOT NULL DEFAULT ''",
                "phase_id": "TEXT REFERENCES generation_phases(phase_id) ON DELETE RESTRICT",
                "revision": "INTEGER NOT NULL DEFAULT 0",
                "depends_on_json": "TEXT NOT NULL DEFAULT '[]'",
                "previous_id": "TEXT",
                "artifact_dir": "TEXT NOT NULL DEFAULT ''",
                "artifact_refs_json": "TEXT NOT NULL DEFAULT '[]'",
            },
            "generation_plan_steps": {
                "component_refs_set": "INTEGER NOT NULL DEFAULT 0 CHECK(component_refs_set IN (0, 1))",
            },
            "generation_phases": {
                "depends_on_json": "TEXT NOT NULL DEFAULT '[]'",
                "previous_id": "TEXT",
            },
        }
        for table, columns in additions.items():
            present = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            for column, declaration in columns.items():
                if column not in present:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
                    if column == 'component_refs_set':
                        connection.execute('''UPDATE generation_plan_steps SET component_refs_set=1
                            WHERE EXISTS(SELECT 1 FROM generation_step_ontological r
                            WHERE r.plan_id=generation_plan_steps.plan_id AND r.step_id=generation_plan_steps.step_id)''')
        from almond_mcp.features.components.semantic_schema import initialize_file_relations
        initialize_file_relations(self, connection)
        from almond_mcp.features.planning.schema import initialize_minute_timestamps
        initialize_minute_timestamps(connection)
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS plan_artifact_folder ON generation_plans(artifact_dir COLLATE NOCASE) WHERE artifact_dir <> ''")
        for table, field, target in (
            ("generation_plan_scenes", "scene_id", "scenes"),
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
        from almond_mcp.features.planning.schema import initialize_planning_details
        initialize_planning_details(self, connection)

    @staticmethod
    def _generation_text(value: str, field: str, *, allow_empty: bool = False) -> str:
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise ValueError(f"{field} must be a {'string' if allow_empty else 'nonempty string'}.")
        return value.strip()

    @staticmethod
    def _generation_status(value):
        from almond_mcp.features.planning.schema import STATUSES
        if not isinstance(value, str) or value.strip().lower() not in STATUSES:
            raise ValueError('Unsupported workflow status.')
        return value.strip().lower()

    @staticmethod
    def _generation_refs(values: list[str], field: str) -> list[str]:
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"{field} must be a list of nonempty strings.")
        return list(dict.fromkeys(value.strip() for value in values))

    @staticmethod
    def _related_ids(values: list[str], kind: str = "plan") -> list[str]:
        from almond_mcp.features.planning.schema import same_kind_ids
        return same_kind_ids(values, kind)

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
                read_instruction(__file__, 'response-803').format(expected_revision, plan['revision'])
            )

    @staticmethod
    def _validate_generation_refs(connection, scene_ids, component_ids, phase_id=None) -> None:
        for scene_id in scene_ids:
            if not connection.execute("SELECT 1 FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone():
                raise KeyError(f"Unknown scene_id: {scene_id}")
        for component_id in component_ids:
            row = connection.execute(
                "SELECT model_path FROM _component_records WHERE component_id = ?", (component_id,)
            ).fetchone()
            if not row:
                raise KeyError(f"Unknown component_id: {component_id}")
            if not row["model_path"] or not row["model_path"].strip():
                raise ValueError(f"Component {component_id} has no registered model_path.")
        if phase_id and not connection.execute(
            "SELECT 1 FROM generation_phases WHERE phase_id = ?", (phase_id,)
        ).fetchone():
            raise KeyError(f"Unknown phase_id: {phase_id}")

    def _write_generation_refs(self, connection, plan_id, scene_ids, component_ids) -> None:
        component_ids = self._canonical_component_refs(connection, component_ids)
        for table, field, values in (
            ("generation_plan_scenes", "scene_id", scene_ids),
            ("generation_plan_ontological", "ontological_id", component_ids),
        ):
            connection.execute(f"DELETE FROM {table} WHERE plan_id = ?", (plan_id,))
            connection.executemany(
                f"INSERT INTO {table}(plan_id, {field}, position) VALUES (?, ?, ?)",
                [(plan_id, value, index) for index, value in enumerate(values)],
            )

    @staticmethod
    def _read_generation_phase(connection, phase_id) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT * FROM _phase_records WHERE phase_id = ?", (phase_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["depends_on"] = _decode(result.pop("depends_on_json"), [])
        result["plan_count"] = connection.execute(
            "SELECT COUNT(*) FROM generation_plans WHERE phase_id = ?", (phase_id,)
        ).fetchone()[0]
        from almond_mcp.features.planning.schema import default_plan_title
        result["plan_titles"] = [row["title"] or default_plan_title(row["goal"]) for row in connection.execute(
            "SELECT title,goal FROM generation_plans WHERE phase_id=? ORDER BY created_at,plan_id", (phase_id,))]
        return result

    def create_phase(self, name: str, description: str = "", file_name: str = "", project_file_id: str | None = None,
                     status: str = "pending", depends_on: list[str] | None = None,
                     previous_id: str | None = None) -> dict[str, Any]:
        name = self._generation_text(name, "name")
        description = self._generation_text(description, "description", allow_empty=True)
        file_name = self._generation_text(file_name, "file_name", allow_empty=True)
        status = self._generation_status(status)
        depends_on = self._related_ids([] if depends_on is None else depends_on, "phase")
        previous_id = previous_reference(previous_id, "phase")
        phase_id = f"phase_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            file_id = self._project_file_reference(connection,file_name,project_file_id)
            connection.execute(
                "INSERT INTO generation_phases(phase_id, name, description, created_at, updated_at, project_file_id, status, depends_on_json, previous_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (phase_id, name, description, now, now, file_id, status, _json(depends_on), previous_id),
            )
            result = self._read_generation_phase(connection, phase_id)
        return result

    def get_phase(self, phase_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._read_generation_phase(connection, phase_id)

    def list_phases(self, limit: int = 50) -> dict[str, Any]:
        limit = self._generation_limit(limit)
        with self._connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute("SELECT COUNT(*) FROM generation_phases").fetchone()[0]
            rows = connection.execute(
                "SELECT phase_id FROM generation_phases ORDER BY created_at, phase_id LIMIT ?", (limit,)
            ).fetchall()
            phases = [self._read_generation_phase(connection, row["phase_id"]) for row in rows]
        return {"phases": phases, "total": total, "limit": limit, "truncated": total > len(phases)}

    def update_phase(
        self, phase_id: str, name: str | None = None, description: str | None = None,
        file_name: str | None = None, project_file_id: str | None = None, status: str | None = None,
        depends_on: list[str] | None = None,
        previous_id: str | None = None,
    ) -> dict[str, Any]:
        return self.edit_phase(phase_id, name, description, file_name, project_file_id, status, depends_on, previous_id).record

    def edit_phase(
        self, phase_id: str, name: str | None = None, description: str | None = None,
        file_name: str | None = None, project_file_id: str | None = None, status: str | None = None,
        depends_on: list[str] | StringListPatch | None = None,
        previous_id: str | None = None,
    ) -> PlanningUpdate:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._read_generation_phase(connection, phase_id)
            if not current:
                raise KeyError(f"Unknown phase_id: {phase_id}")
            name = current["name"] if name is None else self._generation_text(name, "name")
            description = current["description"] if description is None else self._generation_text(
                description, "description", allow_empty=True
            )
            file_id = current['project_file_id'] if file_name is None and project_file_id is None else self._project_file_reference(connection,file_name or '',project_file_id)
            status = current['status'] if status is None else self._generation_status(status)
            previous_id = current['previous_id'] if previous_id is None else previous_reference(previous_id, "phase")
            issues = []
            if isinstance(depends_on, StringListPatch):
                depends_on, issues = apply_list_patch(current['depends_on'], depends_on, "depends_on", kind="phase")
            else:
                depends_on = current['depends_on'] if depends_on is None else self._related_ids(depends_on, "phase")
            changed = (name,description,file_id,status,depends_on,previous_id) != (current['name'],current['description'],current['project_file_id'],current['status'],current['depends_on'],current['previous_id'])
            if changed:
                connection.execute(
                    "UPDATE generation_phases SET name = ?, description = ?, project_file_id = ?, status = ?, depends_on_json = ?, previous_id = ?, updated_at = ? WHERE phase_id = ?",
                    (name, description, file_id, status, _json(depends_on), previous_id, _utc_now(), phase_id),
                )
            result = self._read_generation_phase(connection, phase_id)
        return PlanningUpdate(result, changed, issues)

    def _read_generation_plan(self, connection, plan_id) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT * FROM generation_plans WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        from almond_mcp.features.planning.schema import default_plan_title
        result["title"] = result["title"] or default_plan_title(result["goal"])
        phase = connection.execute("SELECT phase_id,name FROM generation_phases WHERE phase_id=?", (result["phase_id"],)).fetchone()
        result["phase"] = dict(phase) if phase else None
        result["depends_on"] = _decode(result.pop("depends_on_json"), [])
        result["artifact_refs"] = _decode(result.pop("artifact_refs_json"), [])
        for table, field, key in (
            ("generation_plan_scenes", "scene_id", "scene_ids"),
            ("_plan_component_refs", "component_id", "component_ids"),
        ):
            result[key] = [item[field] for item in connection.execute(
                f"SELECT {field} FROM {table} WHERE plan_id = ? ORDER BY position", (plan_id,)
            )]
        result["steps"] = [
            {
                "step_id": step["step_id"], "name": step["step_id"], "position": step["position"],
                "kind": step["kind"], "status": step["status"],
                "depends_on": _decode(step["depends_on_json"], []),
                "input_refs": _decode(step["input_refs_json"], []),
                "output_refs": _decode(step["output_refs_json"], []),
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

    def create_plan(
        self,
        goal: str,
        scope: str = "house",
        scene_id: str = "",
        phase_id: str = "",
        scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None,
        depends_on: list[str] | None = None,
        title: str | None = None,
        previous_id: str | None = None,
    ) -> dict[str, Any]:
        goal = self._generation_text(goal, "goal")
        from almond_mcp.features.planning.schema import default_plan_title
        title = default_plan_title(goal) if title is None else self._generation_text(title, "title")
        scope = self._generation_text(scope, "scope").lower()
        scene_id = self._generation_text(scene_id, "scene_id", allow_empty=True)
        phase_id = self._generation_text(phase_id, "phase_id", allow_empty=True)
        scene_ids = self._generation_refs(
            ([scene_id] if scene_id else []) if scene_ids is None else scene_ids, "scene_ids"
        )
        if scene_id and (not scene_ids or scene_ids[0] != scene_id):
            raise ValueError("scene_id must match the first entry of scene_ids when both are supplied.")
        component_ids = self._generation_refs([] if component_ids is None else component_ids, "component_ids")
        depends_on = self._related_ids([] if depends_on is None else depends_on)
        previous_id = previous_reference(previous_id, "plan")
        templates = {


            "spatial_development": [
                ("inspect_context", "reason", []),
                ("inspect_surroundings", "reason", ["inspect_context"]),
                ("Explore_opportunities", "reason", ["inspect_surroundings"]),
                ("develop_options", "reason", ["Explore_opportunities"]),
                ("develop_model_and_drawings", "execute", ["develop_options"]),
                ("resolve_collisions", "resolve", ["develop_model_and_drawings"]),
                ("check_tectonic_consistency", "resolve", ["resolve_collisions"]),
                ("validate_relationships", "validate", ["check_tectonic_consistency"]),
                ("cleanup_intermediate_artifacts", "validate", ["validate_relationships"]),
            ],
            "semantic_exploration": [
                ("inspect_context", "reason", []),
                ("inspect_surroundings", "reason", ["inspect_context"]),
                ("interpret_spatial_context", "reason", ["inspect_surroundings"]),
                ("report_findings", "reason", ["interpret_spatial_context"]),
            ],
            "plan_editing": [
                ("inspect_plan", "reason", []),
                ("define_changes", "reason", ["inspect_plan"]),
                ("edit_plan", "execute", ["define_changes"]),
                ("validate_plan", "validate", ["edit_plan"]),
            ],
            "model_revision": [
                ("inspect_context", "reason", []),
                ("identify_tectonic_system", "reason", ["inspect_context"]),
                ("diagnose_issue", "reason", ["identify_tectonic_system"]),
                ("define_changes", "reason", ["diagnose_issue"]),
                ("apply_changes", "execute", ["define_changes"]),
                ("resolve_collisions", "resolve", ["apply_changes"]),
                ("validate_impacts", "validate", ["resolve_collisions"]),
                ("final_validation", "validate", ["validate_impacts"]),
            ],
            "construction_detail": [
                ("inspect_context", "reason", []),
                ("review_system", "retrieve", ["inspect_context"]),
                ("resolve_detail", "reason", ["review_system"]),
                ("model_detail", "execute", ["resolve_detail"]),
                ("validate_detail", "validate", ["model_detail"]),
            ],
            "inspection": [
                ("define_criteria", "reason", []),
                ("observe", "retrieve", ["define_criteria"]),
                ("evaluate", "validate", ["observe"]),
                ("report_findings", "reason", ["evaluate"]),
            ],
            "structure": [
                ("inspect_existing_structure", "reason", []),
                ("programme", "reason", ["inspect_existing_structure"]),
                ("retrieve_structural_logic", "retrieve", ["programme"]),
                ("analyze_structure", "validate", ["retrieve_structural_logic"]),
                ("develop_structure_or_improvements", "reason", ["analyze_structure"]),
                ("apply_structure_changes", "execute", ["develop_structure_or_improvements"]),
                ("validate_structure", "validate", ["apply_structure_changes"]),
            ],
            "drawing": [
                ("define_drawing_scope", "reason", []),
                ("inspect_existing_drawings", "retrieve", ["define_drawing_scope"]),
                ("generate_or_update_drawings", "execute", ["inspect_existing_drawings"]),
                ("validate_drawing", "validate", ["generate_or_update_drawings"]),
                ("prepare_layout_or_export", "execute", ["validate_drawing"]),
            ],
            "component": [
                ("inspect_context", "reason", []),
                ("design", "reason", ["inspect_context"]),
                ("model", "execute", ["design"]),
                ("validate", "validate", ["model"]),
            ],
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
        }
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._validate_generation_refs(connection, scene_ids, component_ids, phase_id)
            template = connection.execute('SELECT template_scope FROM planning_scopes WHERE scope=?', (scope,)).fetchone()
            if template is None:
                raise ValueError('Unknown scope; choose a value from planning_scopes.')
            connection.execute(
                """
                INSERT INTO generation_plans(
                    plan_id, scene_id, scope, goal, status, created_at, updated_at, phase_id, depends_on_json, title, previous_id
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
                """,
                (plan_id, scene_ids[0] if scene_ids else None, scope, goal, now, now, phase_id or None, _json(depends_on), title, previous_id),
            )
            for position, (step_id, kind, dependencies) in enumerate(templates[template[0]]):
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

    def get_plan(
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
            snapshot = _decode(row["snapshot_json"], None) if row else None
            if snapshot is not None:
                from almond_mcp.features.planning.schema import default_plan_title
                snapshot.setdefault("title", default_plan_title(snapshot["goal"]))
                # Older snapshots had no Phase name. Do not invent its historical name.
                snapshot.setdefault("phase", {"phase_id": snapshot["phase_id"], "name": None} if snapshot.get("phase_id") else None)
                for key, default in (("depends_on", []), ("previous_id", None), ("artifact_dir", ""), ("artifact_refs", [])):
                    snapshot.setdefault(key, default)
                for step in snapshot.get("steps", []):
                    step.setdefault("name", step["step_id"])
            return snapshot

    def get_step(self, plan_id: str, step_id: str, revision: int | None = None) -> dict[str, Any] | None:
        """Read one Step; the public unified tool owns the output envelope."""
        if revision is not None:
            plan = self.get_plan(plan_id, revision)
            if plan is None:
                return None
            step = next((item for item in plan["steps"] if item["step_id"] == step_id), None)
            return {"plan_id": plan_id, "revision": plan["revision"], "step": step} if step else None
        with self._connect() as connection:
            connection.execute("BEGIN")
            row = connection.execute('''SELECT p.revision,s.step_id,s.status,s.input_refs_json,s.output_refs_json
                FROM generation_plan_steps s JOIN generation_plans p ON p.plan_id=s.plan_id
                WHERE s.plan_id=? AND s.step_id=?''', (plan_id, step_id)).fetchone()
            if row is None:
                return None
            return {"plan_id": plan_id, "revision": row["revision"], "step": {
                "step_id": row["step_id"], "name": row["step_id"], "status": row["status"],
                "input_refs": _decode(row["input_refs_json"], []),
                "output_refs": _decode(row["output_refs_json"], [])}}

    def list_plans(
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
            if status not in {"pending", "running", "completed", "failed", "blocked", "paused"}:
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
                "SELECT p.plan_id,p.title,p.goal,p.scope,p.status,p.revision FROM generation_plans p" + where + " ORDER BY p.updated_at DESC, p.plan_id LIMIT ?",
                [*arguments, limit],
            ).fetchall()
            plans = [dict(row) for row in rows]
            from almond_mcp.features.planning.schema import default_plan_title
            for plan in plans:
                goal = plan.pop("goal")
                plan["title"] = plan["title"] or default_plan_title(goal)
        return {"plans": plans, "total": total, "limit": limit, "truncated": total > len(plans)}

    def list_plan_revisions(self, plan_id: str, limit: int = 50) -> dict[str, Any]:
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

    def update_plan(
        self, plan_id: str, goal: str | None = None, phase_id: str | None = None,
        scene_ids: list[str] | None = None, component_ids: list[str] | None = None,
        expected_revision: int | None = None,
        depends_on: list[str] | None = None,
        status: str | None = None,
        artifact_refs: list[str] | None = None,
        title: str | None = None,
        previous_id: str | None = None,
    ) -> dict[str, Any]:
        return self.edit_plan(plan_id, goal, phase_id, scene_ids, component_ids, expected_revision,
                              depends_on, status, artifact_refs, title, previous_id).record

    def edit_plan(
        self, plan_id: str, goal: str | None = None, phase_id: str | None = None,
        scene_ids: list[str] | None = None, component_ids: list[str] | None = None,
        expected_revision: int | None = None, depends_on: list[str] | StringListPatch | None = None,
        status: str | None = None, artifact_refs: list[str] | None = None, title: str | None = None,
        previous_id: str | None = None,
    ) -> PlanningUpdate:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            plan = self._read_generation_plan(connection, plan_id)
            if not plan:
                raise KeyError(f"Unknown plan_id: {plan_id}")
            self._check_generation_revision(plan, expected_revision)
            goal = plan["goal"] if goal is None else self._generation_text(goal, "goal")
            title = plan["title"] if title is None else self._generation_text(title, "title")
            previous_id = plan["previous_id"] if previous_id is None else previous_reference(previous_id, "plan")
            phase_id = plan["phase_id"] if phase_id is None else (
                self._generation_text(phase_id, "phase_id", allow_empty=True) or None
            )
            scene_ids = plan["scene_ids"] if scene_ids is None else self._generation_refs(scene_ids, "scene_ids")
            component_ids = plan["component_ids"] if component_ids is None else self._generation_refs(component_ids, "component_ids")
            issues = []
            if isinstance(depends_on, StringListPatch):
                depends_on, issues = apply_list_patch(plan["depends_on"], depends_on, "depends_on", kind="plan")
            else:
                depends_on = plan["depends_on"] if depends_on is None else self._related_ids(depends_on)
            status = plan["status"] if status is None else self._generation_text(status, "status").lower()
            if status not in {"pending", "running", "completed", "failed", "blocked", "paused"}:
                raise ValueError("Unsupported plan status.")
            artifact_refs = plan["artifact_refs"] if artifact_refs is None else self._generation_refs(artifact_refs, "artifact_refs")
            self._validate_generation_refs(connection, scene_ids, component_ids, phase_id)
            if (goal, phase_id, scene_ids, component_ids, depends_on, status, artifact_refs, title, previous_id) == (
                plan["goal"], plan["phase_id"], plan["scene_ids"], plan["component_ids"], plan["depends_on"], plan["status"], plan["artifact_refs"], plan["title"], plan["previous_id"]
            ):
                return PlanningUpdate(plan, False, issues)
            connection.execute(
                "UPDATE generation_plans SET goal = ?, phase_id = ?, scene_id = ?, depends_on_json = ?, status = ?, artifact_refs_json = ?, title = ?, previous_id = ? WHERE plan_id = ?",
                (goal, phase_id, scene_ids[0] if scene_ids else None, _json(depends_on), status, _json(artifact_refs), title, previous_id, plan_id),
            )
            self._write_generation_refs(connection, plan_id, scene_ids, component_ids)
            result = self._record_generation_revision(connection, plan_id, "update_plan")
        return PlanningUpdate(result, True, issues)

    def update_plan_step(
        self,
        plan_id: str,
        step_id: str,
        status: str | None = None,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        expected_revision: int | None = None,
    ) -> dict[str, Any]:
        return self.edit_step(plan_id, step_id, status, input_refs, output_refs, expected_revision).record

    def edit_step(
        self, plan_id: str, step_id: str, status: str | None = None,
        input_refs: list[str] | StringListPatch | None = None,
        output_refs: list[str] | StringListPatch | None = None,
        expected_revision: int | None = None,
    ) -> PlanningUpdate:
        if status is not None:
            status = self._generation_text(status, "status").lower()
            if status not in {"pending", "running", "completed", "failed", "blocked", "paused"}:
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
            status = step["status"] if status is None else status
            issues = []
            def refs(value, field):
                if isinstance(value, StringListPatch):
                    result, skipped = apply_list_patch(step[field], value, field)
                    issues.extend(skipped)
                    return result
                return step[field] if value is None else self._generation_refs(value, field)
            inputs, outputs = refs(input_refs, "input_refs"), refs(output_refs, "output_refs")
            if (status, inputs, outputs) == (
                step["status"], step["input_refs"], step["output_refs"]
            ):
                return PlanningUpdate(plan, False, issues)
            connection.execute(
                """
                UPDATE generation_plan_steps
                SET status = ?, input_refs_json = ?, output_refs_json = ?
                WHERE plan_id = ? AND step_id = ?
                """,
                (status, _json(inputs), _json(outputs), plan_id, step_id),
            )
            # Reference-only changes do not resume an explicitly stopped Plan.
            if status != step["status"]:
                statuses = [status if item["step_id"] == step_id else item["status"] for item in plan["steps"]]
                plan_status = (
                    "failed" if "failed" in statuses
                    else "blocked" if "blocked" in statuses
                    else "completed" if all(item == "completed" for item in statuses)
                    else "running" if "running" in statuses
                    else "paused" if "paused" in statuses
                    else "running" if "completed" in statuses
                    else "pending"
                )
                connection.execute(
                    "UPDATE generation_plans SET status = ? WHERE plan_id = ?", (plan_status, plan_id),
                )
            result = self._record_generation_revision(connection, plan_id, "update_step:" + step_id)
        return PlanningUpdate(result, True, issues)

    def resolve_targets(self, plan_id: str, step_id: str = "") -> dict[str, Any]:
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
            self._validate_generation_refs(connection, [], component_ids)
            components = []
            for component_id in component_ids:
                registered = self._component_read(connection, component_id)
                components.append({key: registered[key] for key in (
                    "component_id", "model_path", "rhino_group_id", "name", "parent_component_id",
                    "child_component_ids",
                )})
        return {
            "plan_id": plan_id, "step_id": step_id or None, "revision": plan["revision"],
            "source": source, "scene_ids": plan["scene_ids"], "component_ids": component_ids,
            "components": components, "live_verified": False,
        }

    def selection_references(self, model_path: str, object_ids: list[str], limit: int = 50, native_observe=None) -> dict[str, Any]:
        """Read actual registered ownership and Plan/Step references, including ancestors."""
        model_path = self._component_model_path(model_path)
        object_ids = self._component_object_ids(object_ids)
        limit = self._generation_limit(limit)
        objects, components, plans = [], {}, {}
        if object_ids and not callable(native_observe):
            raise ValueError('Selection ownership requires live read-only Rhino observation.')
        observed = {}
        if object_ids:
            reply = self._component_native(native_observe, dict(type='design_component',action='objects',
                expected_model_path=model_path,object_ids=object_ids))
            if self._component_model_path(reply.get('model_path')) != model_path:
                raise ValueError('Selected objects belong to a different model.')
            observed = {o['rhino_guid']:o for o in self._component_observed_objects(reply,object_ids)}
        with self._connect() as connection:
            connection.execute("BEGIN")
            for guid in object_ids:
                owner = observed[guid].get('component_id')
                if owner:
                    registered = self._component_read(connection,owner)
                    if registered is None or registered['model_path'] != model_path or registered['availability'] != 'present':
                        raise ValueError('Align the selected semantic Component before resolving Plan references.')
                ancestors = connection.execute("""
                    WITH RECURSIVE parents(component_id, parent_component_id, name) AS (
                        SELECT component_id, parent_component_id, name FROM _component_records WHERE component_id = ?
                        UNION
                        SELECT c.component_id, c.parent_component_id, c.name FROM _component_records c
                        JOIN parents p ON p.parent_component_id = c.component_id
                    ) SELECT * FROM parents
                """, (owner,)).fetchall()
                related = []
                for component in ancestors:
                    component_id = component["component_id"]
                    components[component_id] = dict(component)
                    related.append(component_id)
                    for match in connection.execute("""
                        SELECT plan_id FROM _plan_component_refs WHERE component_id = ?
                    """, (component_id,)):
                        plans.setdefault(match["plan_id"], set()).add(component_id)
                objects.append({"object_id": guid, "registered": owner is not None,
                                "component_id": owner, "related_component_ids": related})
            total = len(plans)
            matches = []
            for plan_id in sorted(plans)[:limit]:
                plan = self._read_generation_plan(connection, plan_id)
                related = plans[plan_id]
                steps = []
                for step in plan["steps"]:
                    matched = sorted(related.intersection(plan["component_ids"]))
                    if matched:
                        steps.append({"step_id": step["step_id"], "name": step["name"],
                                      "status": step["status"], "source": "plan"})
                matches.append({"plan_id": plan_id, "title": plan["title"], "goal": plan["goal"], "phase_id": plan["phase_id"],
                                "component_ids": sorted(related.intersection(plan["component_ids"])), "steps": steps})
        return {"objects": objects, "components": list(components.values()), "plans": matches,
                "total_plans": total, "truncated": total > len(matches),
                "ownership_live_verified": bool(object_ids), "references_live_verified": False}
