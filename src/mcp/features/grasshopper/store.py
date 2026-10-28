"""Grasshopper capsule registry methods for the shared AlmondStore database."""
from __future__ import annotations

import re
from typing import Any

from almond_mcp.store_common import _utc_now, _json, _decode


class GrasshopperStore:
    """Own capsule registry SQL while sharing the facade's connection lifecycle."""

    def sync_capsules(self, manifests: list[dict[str, Any]]) -> int:
        """Upsert capsule manifests and prune capsules absent from the batch."""
        now = _utc_now()
        seen: list[str] = []
        with self._connect() as connection:
            for manifest in manifests:
                if not isinstance(manifest, dict):
                    raise ValueError("Each capsule manifest must be a dict.")
                missing = [
                    key
                    for key in ("capsule_id", "capability", "definition_file",
                                "inputs", "outputs", "audited")
                    if key not in manifest
                ]
                if missing:
                    raise ValueError(
                        f"Capsule manifest is missing keys: {', '.join(missing)}"
                    )
                capsule_id = str(manifest["capsule_id"]).strip()
                if not capsule_id:
                    raise ValueError("capsule_id must be a non-empty string.")
                connection.execute(
                    """
                    INSERT INTO capsules (
                        capsule_id, capability, definition_file, audited,
                        title, manifest_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(capsule_id) DO UPDATE SET
                        capability = excluded.capability,
                        definition_file = excluded.definition_file,
                        audited = excluded.audited,
                        title = excluded.title,
                        manifest_json = excluded.manifest_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        capsule_id,
                        str(manifest["capability"]).strip().lower(),
                        str(manifest["definition_file"]).strip(),
                        int(bool(manifest["audited"])),
                        str(manifest.get("title", "")).strip(),
                        _json(manifest),
                        now,
                    ),
                )
                seen.append(capsule_id)

            if seen:
                placeholders = ",".join("?" for _ in seen)
                connection.execute(
                    f"DELETE FROM capsules WHERE capsule_id NOT IN ({placeholders})",
                    seen,
                )
            else:
                connection.execute("DELETE FROM capsules")
        return len(seen)

    @staticmethod
    def compact_capsule(manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            "capsule_id": manifest.get("capsule_id"),
            "capability": manifest.get("capability"),
            "structure_type": manifest.get("structure_type"),
            "definition_file": manifest.get("definition_file"),
            "title": manifest.get("title", ""),
            "audited": bool(manifest.get("audited")),
            "inputs": [port.get("name") for port in manifest.get("inputs", [])],
            "outputs": [port.get("name") for port in manifest.get("outputs", [])],
        }

    def search_capsules(
        self,
        query: str = "",
        capability: str = "",
        audited_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))
        clauses: list[str] = []
        parameters: list[Any] = []

        if capability.strip():
            clauses.append("capability = ?")
            parameters.append(capability.strip().lower())
        if audited_only:
            clauses.append("audited = 1")
        tokens = re.findall(r"[\w-]+", query.lower(), flags=re.UNICODE)
        for token in tokens[:12]:
            clauses.append(
                "(LOWER(capsule_id) LIKE ? OR LOWER(title) LIKE ? "
                "OR LOWER(definition_file) LIKE ? OR LOWER(manifest_json) LIKE ?)"
            )
            pattern = f"%{token}%"
            parameters.extend([pattern, pattern, pattern, pattern])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) AS count FROM capsules {where}",
                parameters,
            ).fetchone()["count"])
            rows = connection.execute(
                f"""
                SELECT manifest_json FROM capsules
                {where}
                ORDER BY audited DESC, capsule_id
                LIMIT ? OFFSET ?
                """,
                [*parameters, limit, offset],
            ).fetchall()
        capsules = [
            self.compact_capsule(_decode(row["manifest_json"], {}))
            for row in rows
        ]
        next_offset = offset + len(capsules)
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "capsules": capsules,
        }

    def get_capsule(self, capsule_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM capsules WHERE capsule_id = ?",
                (capsule_id.strip(),),
            ).fetchone()
        return _decode(row["manifest_json"], {}) if row else None
