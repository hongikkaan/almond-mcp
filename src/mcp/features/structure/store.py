"""Structural validation history on the shared AlmondStore connection/schema."""
from __future__ import annotations

import json
from typing import Any

from almond_mcp.store_common import _json, _utc_now


class StructureStore:
    def record_validation_run(
        self,
        request: dict[str, Any],
        result: dict[str, Any],
        guids: list[str],
    ) -> int:
        """Persists one validate_structure run for later report export."""
        results = result.get("results") or {}
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO validation_runs(
                    ran_at, structure_type, material, load_kn, member_count,
                    analysis_method, confidence, passed, span_m,
                    max_deflection_mm, deflection_limit_mm, utilization_ratio,
                    max_stress_mpa, yield_stress_mpa, reactions_kn,
                    verdict, warnings_json, guids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(),
                    str(request.get("structure_type", "beam")),
                    str(request.get("material", "Steel")),
                    float(request.get("load_kn", 10.0)),
                    len(guids),
                    str(results.get("analysis_method", "unknown")),
                    str(result.get("confidence", "unknown")),
                    1 if result.get("passed") else 0,
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
            run["passed"] = bool(run["passed"])
            run["warnings"] = json.loads(run.pop("warnings_json") or "[]")
            run["guids"] = json.loads(run.pop("guids_json") or "[]")
            runs.append(run)
        return runs
