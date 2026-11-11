"""Structural validation history on the shared AlmondStore connection/schema."""
from __future__ import annotations

import json
from typing import Any

from almond_mcp.store_common import _json, _utc_now

_VALIDATION_COLUMNS = """
    id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT NOT NULL,
    structure_type TEXT NOT NULL, material TEXT NOT NULL, load_kn REAL NOT NULL,
    member_count INTEGER NOT NULL, analysis_method TEXT NOT NULL, confidence TEXT NOT NULL,
    passed INTEGER, status TEXT NOT NULL, span_m REAL NOT NULL,
    max_deflection_mm REAL NOT NULL, deflection_limit_mm REAL NOT NULL,
    utilization_ratio REAL NOT NULL, max_stress_mpa REAL NOT NULL, yield_stress_mpa REAL NOT NULL,
    reactions_kn REAL NOT NULL, verdict TEXT NOT NULL, warnings_json TEXT NOT NULL, guids_json TEXT NOT NULL
"""


class StructureStore:
    @staticmethod
    def _initialize_validation_runs(connection):
        connection.execute(f"CREATE TABLE IF NOT EXISTS validation_runs ({_VALIDATION_COLUMNS})")
        columns = {row["name"]: row for row in connection.execute("PRAGMA table_info(validation_runs)")}
        if "status" in columns and not columns["passed"]["notnull"]:
            return
        # Keep existing IDs, values and PASS/FAIL history. Only new indicative
        # runs use NULL: completion must not manufacture a safety verdict.
        connection.execute("SAVEPOINT validation_history_migration")
        try:
            sequence = connection.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'validation_runs'"
            ).fetchone()
            connection.execute(f"CREATE TABLE validation_runs_migrating ({_VALIDATION_COLUMNS})")
            names = ", ".join(columns)
            status = "" if "status" in columns else ", status"
            expression = "" if not status else ", CASE WHEN passed = 1 THEN 'pass' WHEN passed = 0 THEN 'fail' ELSE 'indicative' END"
            connection.execute(f"INSERT INTO validation_runs_migrating ({names}{status}) SELECT {names}{expression} FROM validation_runs")
            connection.execute("DROP TABLE validation_runs")
            connection.execute("ALTER TABLE validation_runs_migrating RENAME TO validation_runs")
            if sequence is not None:
                # AUTOINCREMENT must also remember IDs of previously deleted runs.
                updated = connection.execute(
                    "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = 'validation_runs'",
                    (sequence["seq"],),
                )
                if not updated.rowcount:
                    connection.execute(
                        "INSERT INTO sqlite_sequence(name, seq) VALUES ('validation_runs', ?)",
                        (sequence["seq"],),
                    )
            connection.execute("RELEASE validation_history_migration")
        except BaseException:
            connection.execute("ROLLBACK TO validation_history_migration")
            connection.execute("RELEASE validation_history_migration")
            raise

    def record_validation_run(
        self,
        request: dict[str, Any],
        result: dict[str, Any],
        guids: list[str],
    ) -> int:
        """Persists one validate_structure run for later report export."""
        status = result.get("status")
        if status not in {"pass", "fail", "indicative"}:
            raise ValueError("Only completed pass/fail/indicative analyses can enter validation history.")
        passed = None if status == "indicative" else int(status == "pass")
        results = result.get("results") or {}
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO validation_runs(
                    ran_at, structure_type, material, load_kn, member_count,
                    analysis_method, confidence, passed, status, span_m,
                    max_deflection_mm, deflection_limit_mm, utilization_ratio,
                    max_stress_mpa, yield_stress_mpa, reactions_kn,
                    verdict, warnings_json, guids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(),
                    str(request.get("structure_type", "beam")),
                    str(request.get("material", "Steel")),
                    float(request.get("load_kn", 10.0)),
                    len(guids),
                    str(results.get("analysis_method", "unknown")),
                    str(result.get("confidence", "unknown")),
                    passed,
                    status,
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
            run["passed"] = None if run["status"] == "indicative" else bool(run["passed"])
            run["warnings"] = json.loads(run.pop("warnings_json") or "[]")
            run["guids"] = json.loads(run.pop("guids_json") or "[]")
            runs.append(run)
        return runs
