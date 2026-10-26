"""Plan metadata, dependency and archival contracts without a Rhino connection."""
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from almond_mcp.retrieval_store import AlmondStore


class GenerationPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "plans.sqlite3"
        self.store = AlmondStore(self.database)
        self.scene_a = self.store.create_scene("A")["scene_id"]
        self.scene_b = self.store.create_scene("B")["scene_id"]
        self.component_a, self.component_b = "component_fixture_a", "component_fixture_b"
        # Registered identities are the boundary of this suite; no native registration occurs.
        with self.store._connect() as connection:
            connection.executemany("""
                INSERT INTO components(component_id, model_path, rhino_group_id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (component, str(Path(self.temp.name) / "model.3dm"),
                 f"00000000-0000-0000-0000-{index:012d}", component,
                 "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")
                for index, component in enumerate((self.component_a, self.component_b), 1)
            ])
            connection.executemany(
                "INSERT INTO scene_components(scene_id, component_id) VALUES (?, ?)",
                [(self.scene_a, self.component_a), (self.scene_b, self.component_b)],
            )

    def plan(self, **kwargs):
        return self.store.create_plan("Revise facade", scope="component", **kwargs)

    def test_selection_references_include_parent_and_explicit_step_targets(self):
        model = self.store._component_model_path(str(Path(self.temp.name) / "model.3dm"))
        guid = "00000000-0000-0000-0000-000000000099"
        with self.store._connect() as connection:
            connection.execute("UPDATE components SET model_path = ?", (model,))
            connection.execute("UPDATE components SET parent_component_id = ? WHERE component_id = ?",
                               (self.component_a, self.component_b))
            connection.execute("""INSERT INTO document_objects(model_path,rhino_guid,component_id,object_type,
                               min_x,max_x,min_y,max_y,min_z,max_z,observed_at)
                               VALUES(?,?,?,'Point',0,0,0,0,0,0,'fixture')""",
                               (model, guid, self.component_b))
        plan = self.plan(component_ids=[self.component_a])
        self.store.update_plan_step(plan["plan_id"], "model", "paused", component_ids=[self.component_b])
        self.store.update_plan_step(plan["plan_id"], "validate", "pending", component_ids=[])
        result = self.store.selection_references(model, [guid])
        self.assertEqual(result["objects"][0]["component_id"], self.component_b)
        self.assertEqual(set(result["objects"][0]["related_component_ids"]), {self.component_a, self.component_b})
        steps = {step["step_id"]: step for step in result["plans"][0]["steps"]}
        self.assertEqual(steps["model"]["source"], "step_direct")
        self.assertEqual(steps["inspect_context"]["source"], "plan_inherited")
        self.assertNotIn("validate", steps)
        self.assertEqual(self.store.selection_references(model, [])["plans"], [])
        self.assertEqual(self.store.selection_references(model + ".other.3dm", [guid])["plans"], [])

    def test_phase_and_multiple_scene_references_remain_organizational(self):
        phase = self.store.create_phase("Scheme design", "Envelope work")
        plan = self.plan(
            phase_id=phase["phase_id"], scene_ids=[self.scene_a, self.scene_b],
            component_ids=[self.component_a],
        )
        self.assertEqual(plan["scene_id"], self.scene_a)
        self.assertEqual(plan["scene_ids"], [self.scene_a, self.scene_b])
        self.assertEqual(plan["component_ids"], [self.component_a])
        self.assertEqual(self.store.get_phase(phase["phase_id"])["plan_count"], 1)
        self.assertEqual(self.store.list_phases()["total"], 1)
        self.assertEqual(
            self.store.list_plans(phase_id=phase["phase_id"], scene_id=self.scene_b)["total"], 1,
        )
        self.assertNotIn("steps", self.store.list_plans()["plans"][0])
        renamed = self.store.update_phase(phase["phase_id"], name="Detail design")
        self.assertEqual(renamed["description"], "Envelope work")
        self.assertEqual(self.store.get_plan(plan["plan_id"])["revision"], plan["revision"])
        detached = self.store.update_plan(plan["plan_id"], phase_id="", scene_ids=[])
        self.assertIsNone(detached["phase_id"])
        self.assertIsNone(detached["scene_id"])
        self.assertEqual(detached["component_ids"], [self.component_a])

    def test_step_targets_override_inherit_and_explicit_empty_never_expands(self):
        plan = self.plan(scene_ids=[self.scene_a], component_ids=[self.component_a])
        plan_id = plan["plan_id"]
        self.assertIsNone(plan["steps"][0]["component_ids"])
        inherited = self.store.resolve_targets(plan_id, "inspect_context")
        self.assertEqual(inherited["source"], "plan")
        self.assertEqual(inherited["component_ids"], [self.component_a])
        self.assertFalse(inherited["live_verified"])
        self.assertEqual(inherited["components"][0]["component_id"], self.component_a)

        # B belongs to another contextual Scene; explicit targeting is intentionally flexible.
        self.store.update_plan_step(plan_id, "inspect_context", "pending", component_ids=[self.component_b])
        selected = self.store.resolve_targets(plan_id, "inspect_context")
        self.assertEqual(selected["source"], "step")
        self.assertEqual(selected["component_ids"], [self.component_b])
        self.store.update_plan_step(plan_id, "inspect_context", "running")
        self.assertEqual(self.store.resolve_targets(plan_id, "inspect_context")["component_ids"], [self.component_b])
        self.store.update_plan_step(plan_id, "inspect_context", "running", component_ids=[])
        empty = self.store.resolve_targets(plan_id, "inspect_context")
        self.assertEqual(empty["source"], "step")
        self.assertEqual(empty["component_ids"], [])
        self.assertEqual(empty["components"], [])
        scene_only = self.plan(scene_ids=[self.scene_b])
        self.assertEqual(self.store.resolve_targets(scene_only["plan_id"])["component_ids"], [])
        with self.assertRaises(KeyError):
            self.store.resolve_targets(plan_id, "unknown-step")

    def test_omitted_evidence_is_preserved_and_noops_do_not_make_revisions(self):
        plan_id = self.plan()["plan_id"]
        running = self.store.update_plan_step(
            plan_id, "inspect_context", "running", input_refs=["observation-1"], output_refs=["report-1"],
        )
        completed = self.store.update_plan_step(plan_id, "inspect_context", "completed")
        self.assertEqual(completed["steps"][0]["input_refs"], ["observation-1"])
        self.assertEqual(completed["steps"][0]["output_refs"], ["report-1"])
        self.assertEqual(completed["revision"], running["revision"] + 1)
        self.assertEqual(self.store.update_plan_step(plan_id, "inspect_context", "completed"), completed)
        self.assertEqual(self.store.update_plan(plan_id), completed)
        cleared = self.store.update_plan_step(plan_id, "inspect_context", "completed", output_refs=[])
        self.assertEqual(cleared["steps"][0]["output_refs"], [])
        self.assertEqual(cleared["steps"][0]["input_refs"], ["observation-1"])

    def test_plan_snapshots_remain_exact_after_later_metadata_and_step_changes(self):
        original = self.plan(scene_ids=[self.scene_a], component_ids=[self.component_a])
        plan_id = original["plan_id"]
        changed = self.store.update_plan(
            plan_id, goal="Refine roof", scene_ids=[self.scene_b], component_ids=[self.component_b],
            expected_revision=original["revision"],
        )
        completed = self.store.update_plan_step(
            plan_id, "inspect_context", "completed", output_refs=["verified-observation"],
            expected_revision=changed["revision"],
        )
        self.assertEqual(self.store.get_plan(plan_id, original["revision"]), original)
        self.assertEqual(self.store.get_plan(plan_id, changed["revision"]), changed)
        self.assertEqual(self.store.get_plan(plan_id), completed)
        history = self.store.list_plan_revisions(plan_id, limit=2)
        self.assertEqual(history["total"], 3)
        self.assertTrue(history["truncated"])
        self.assertEqual([item["revision"] for item in history["revisions"]], [3, 2])
        self.assertIsNone(self.store.get_plan(plan_id, 100))
        self.assertEqual(self.store.get_scene(self.scene_a)["revision"], 0)

    def test_work_can_pause_switch_and_resume_without_dependency_gates(self):
        plan_id = self.plan()["plan_id"]
        self.store.update_plan_step(plan_id, "model", "completed", output_refs=["tmp/model.3dm"])
        paused = self.store.update_plan_step(plan_id, "design", "paused")
        self.assertEqual(paused["status"], "paused")
        reset = self.store.update_plan_step(plan_id, "inspect_context", "pending")
        self.assertEqual(reset["steps"][2]["status"], "completed")
        self.assertEqual(reset["steps"][2]["output_refs"], ["tmp/model.3dm"])
        resumed = self.store.update_plan_step(plan_id, "design", "running")
        self.assertEqual(resumed["status"], "running")

    def test_related_plan_phase_ids_are_free_arrays_and_file_names_default_empty(self):
        phase = self.store.create_phase("Other work")
        self.assertEqual(phase["file_name"], "")
        self.assertEqual(self.store.get_scene(self.scene_a)["file_name"], "")
        self.assertEqual(self.store.update_phase(phase["phase_id"], file_name="A.3dm")["file_name"], "A.3dm")
        self.assertEqual(self.store.update_scene(self.scene_a, "B.3dm")["file_name"], "B.3dm")
        plan = self.plan(depends_on=["missing-plan", phase["phase_id"], "missing-plan"])
        refs = [plan["plan_id"], "not-yet-created", phase["phase_id"]]
        changed = self.store.update_plan(plan["plan_id"], depends_on=refs, status="paused")
        self.assertEqual(changed["depends_on"], refs)
        self.assertEqual(changed["status"], "paused")
        with self.assertRaisesRegex(ValueError, "array"):
            self.store.update_plan(plan["plan_id"], depends_on="a, b")
        self.assertEqual(self.store.get_plan(plan["plan_id"]), changed)

    def test_reference_errors_and_archive_failures_roll_back_every_write(self):
        with self.assertRaises(KeyError):
            self.plan(scene_ids=[self.scene_a], component_ids=["missing"])
        self.assertEqual(self.store.list_plans()["total"], 0)
        with self.assertRaises(ValueError):
            self.plan(scene_id=self.scene_a, scene_ids=[self.scene_b])
        original = self.plan(component_ids=[self.component_a])
        plan_id = original["plan_id"]
        with self.assertRaises(KeyError):
            self.store.update_plan(plan_id, goal="Should roll back", scene_ids=["missing"])
        with self.assertRaises(KeyError):
            self.store.update_plan_step(plan_id, "inspect_context", "completed", component_ids=["missing"])
        self.assertEqual(self.store.get_plan(plan_id), original)
        with self.store._connect() as connection:
            connection.execute("""
                CREATE TRIGGER reject_test_snapshot BEFORE INSERT ON generation_plan_revisions
                BEGIN SELECT RAISE(ABORT, 'fixture archive failure'); END
            """)
        for operation in (
            lambda: self.store.update_plan(plan_id, goal="Fail after metadata update"),
            lambda: self.store.update_plan_step(plan_id, "inspect_context", "completed", output_refs=["new"]),
        ):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "fixture archive failure"):
                operation()
            self.assertEqual(self.store.get_plan(plan_id), original)
            self.assertEqual(self.store.list_plan_revisions(plan_id)["total"], 1)

    def test_foreign_keys_protect_plan_and_step_component_references(self):
        plan = self.plan(scene_ids=[self.scene_a], component_ids=[self.component_a])
        self.store.update_plan_step(plan["plan_id"], "inspect_context", "pending", component_ids=[self.component_b])
        for table, column, value in (
            ("scenes", "scene_id", self.scene_a),
            ("components", "component_id", self.component_a),
            ("components", "component_id", self.component_b),
        ):
            with self.assertRaises(sqlite3.IntegrityError), self.store._connect() as connection:
                connection.execute(f"DELETE FROM {table} WHERE {column} = ?", (value,))
        with self.store._connect() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_two_direct_store_writers_cannot_both_commit_the_same_expected_revision(self):
        original = self.plan()
        stores = [AlmondStore(self.database), AlmondStore(self.database)]
        barrier = threading.Barrier(2)

        def write(index):
            barrier.wait(timeout=10)
            try:
                return stores[index].update_plan(
                    original["plan_id"], goal=f"Writer {index}", expected_revision=original["revision"],
                )
            except ValueError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, (0, 1)))
        self.assertEqual(sum(isinstance(item, dict) for item in results), 1)
        errors = [item for item in results if isinstance(item, ValueError)]
        self.assertEqual(len(errors), 1)
        self.assertIn("revision conflict", str(errors[0]))
        self.assertEqual(self.store.get_plan(original["plan_id"])["revision"], 2)
        self.assertEqual(self.store.list_plan_revisions(original["plan_id"])["total"], 2)

    def test_legacy_scope_ids_and_branch_dependencies_are_preserved(self):
        expected = {
            "house": ["programme", "retrieve_structural_logic", "generate_structure", "validate_structure",
                      "define_rooms", "retrieve_assets", "place_assets", "validate_layout",
                      "resolve_collisions", "final_validation"],
            "interior": ["inspect_rooms", "retrieve_assets", "place_assets", "validate_layout",
                         "resolve_collisions", "final_validation"],
            "structure": ["programme", "retrieve_structural_logic", "generate_structure", "validate_structure"],
            "drawing": ["freeze_scene", "retrieve_drawing_recipe", "retrieve_drawing_assets", "prepare_drawing_layers",
                        "configure_projection", "generate_linework", "apply_graphic_styles", "create_layout",
                        "export_drawing", "validate_drawing"],
        }
        for scope, identifiers in expected.items():
            with self.subTest(scope=scope):
                plan = self.store.create_plan("Legacy workflow", scope, self.scene_a)
                self.assertEqual([step["step_id"] for step in plan["steps"]], identifiers)
                self.assertEqual(plan["scene_ids"], [self.scene_a])
                if scope == "drawing":
                    self.assertEqual(plan["steps"][2]["depends_on"], ["retrieve_drawing_recipe"])
                    self.assertEqual(plan["steps"][3]["depends_on"], ["retrieve_drawing_recipe"])

    def test_missing_records_and_invalid_arguments_do_not_mutate_plans(self):
        original = self.plan()
        plan_id = original["plan_id"]
        for value in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                self.store.update_plan(plan_id, goal="bad", expected_revision=value)
            with self.assertRaises(ValueError):
                self.store.get_plan(plan_id, revision=value)
        for refs in ("component_fixture_a", [None], [""]):
            with self.assertRaises(ValueError):
                self.store.update_plan(plan_id, component_ids=refs)
        with self.assertRaises(KeyError):
            self.store.update_plan(plan_id, phase_id="missing")
        with self.assertRaises(KeyError):
            self.store.update_phase("missing", name="bad")
        self.assertIsNone(self.store.get_phase("missing"))
        self.assertIsNone(self.store.get_plan("missing"))
        self.assertEqual(self.store.get_plan(plan_id), original)


class GenerationPlanMigrationTests(unittest.TestCase):
    def test_prior_schema_gets_one_honest_baseline_without_changing_existing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy.sqlite3"
            # This is the published pre-Phase schema, not a model of the new implementation.
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript("""
                    CREATE TABLE scenes (
                        scene_id TEXT PRIMARY KEY, name TEXT NOT NULL, units TEXT NOT NULL,
                        revision INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE generation_plans (
                        plan_id TEXT PRIMARY KEY, scene_id TEXT REFERENCES scenes(scene_id) ON DELETE SET NULL,
                        scope TEXT NOT NULL, goal TEXT NOT NULL, status TEXT NOT NULL,
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE generation_plan_steps (
                        plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
                        step_id TEXT NOT NULL, position INTEGER NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
                        depends_on_json TEXT NOT NULL, input_refs_json TEXT NOT NULL, output_refs_json TEXT NOT NULL,
                        PRIMARY KEY(plan_id, step_id)
                    );
                    INSERT INTO scenes VALUES ('scene_old', 'Existing scene', 'mm', 7, 'old-created', 'old-updated');
                    INSERT INTO generation_plans VALUES
                        ('plan_old', 'scene_old', 'interior', 'Existing goal', 'running', 'plan-created', 'plan-updated');
                    INSERT INTO generation_plan_steps VALUES
                        ('plan_old', 'inspect_rooms', 0, 'reason', 'completed', '[]', '["scene_old"]', '["legacy-evidence"]'),
                        ('plan_old', 'retrieve_assets', 1, 'retrieve', 'pending', '["inspect_rooms"]', '[]', '[]');
                """)
            store = AlmondStore(database)
            baseline = store.get_plan("plan_old")
            self.assertEqual(baseline["revision"], 0)
            self.assertIsNone(baseline["phase_id"])
            self.assertEqual(baseline["scene_ids"], ["scene_old"])
            self.assertEqual(baseline["created_at"], "plan-created")
            self.assertEqual(baseline["updated_at"], "plan-updated")
            self.assertEqual(baseline["steps"][0]["output_refs"], ["legacy-evidence"])
            self.assertEqual(store.get_plan("plan_old", 0), baseline)
            history = store.list_plan_revisions("plan_old")
            self.assertEqual(history["total"], 1)
            self.assertEqual(history["revisions"][0]["operation"], "migration_baseline")
            reopened = AlmondStore(database)
            self.assertEqual(reopened.get_plan("plan_old"), baseline)
            self.assertEqual(reopened.list_plan_revisions("plan_old"), history)
            updated = reopened.update_plan_step("plan_old", "retrieve_assets", "completed", expected_revision=0)
            self.assertEqual(updated["revision"], 1)
            self.assertEqual(reopened.get_plan("plan_old", 0), baseline)
            self.assertEqual(reopened.get_scene("scene_old")["revision"], 7)
            with closing(sqlite3.connect(database)) as connection:
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
