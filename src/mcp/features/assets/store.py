"""Feature-owned asset index queries using AlmondStore's shared connection."""
from __future__ import annotations

import re
from typing import Any

from almond_mcp.store_common import RETIRED_LIBRARY_ID, _utc_now, _json, _decode


class AssetsStore:
    """Asset indexing, search, lookup and statistics within the shared database."""

    def sync_assets(
        self,
        assets: list[dict[str, Any]],
        library_id: str = "ikea",
    ) -> int:
        """Upsert one manifest and prune stale records only within its library."""
        library_id = library_id.strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,40}", library_id):
            raise ValueError("library_id must be a short lowercase identifier.")
        now = _utc_now()
        seen: list[str] = []
        with self._connect() as connection:
            for source in assets:
                asset = {
                    key: value
                    for key, value in source.items()
                    if not key.startswith("_")
                }
                asset["library_id"] = library_id
                asset_id = str(asset["asset_id"])
                dimensions = asset.get("dimensions_mm", {})
                width = float(dimensions.get("width", 0))
                depth = float(dimensions.get("depth", 0))
                height = float(dimensions.get("height", 0))
                if min(width, depth, height) <= 0:
                    raise ValueError(f"Asset {asset_id} has invalid dimensions.")

                search_text = " ".join(
                    filter(
                        None,
                        [
                            asset_id,
                            asset.get("category", ""),
                            asset.get("series", ""),
                            asset.get("product", ""),
                            asset.get("variant", ""),
                            asset.get("brand", ""),
                            asset.get("source_class", ""),
                            " ".join(asset.get("tags", [])),
                        ],
                    )
                )
                geometry_source = asset.get("geometry_source", {})
                connection.execute(
                    """
                    INSERT INTO assets (
                        asset_id, library_id, category, series, product, variant,
                        width_mm, depth_mm, height_mm, match_status,
                        geometry_source_type, file_available, search_text,
                        metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(asset_id) DO UPDATE SET
                        library_id = excluded.library_id,
                        category = excluded.category,
                        series = excluded.series,
                        product = excluded.product,
                        variant = excluded.variant,
                        width_mm = excluded.width_mm,
                        depth_mm = excluded.depth_mm,
                        height_mm = excluded.height_mm,
                        match_status = excluded.match_status,
                        geometry_source_type = excluded.geometry_source_type,
                        file_available = excluded.file_available,
                        search_text = excluded.search_text,
                        metadata_json = excluded.metadata_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        asset_id,
                        library_id,
                        asset.get("category", ""),
                        asset.get("series", ""),
                        asset.get("product", ""),
                        asset.get("variant", ""),
                        width,
                        depth,
                        height,
                        asset.get("match_status", ""),
                        geometry_source.get("type", "downloaded_asset"),
                        int(bool(asset.get("file_available"))),
                        search_text,
                        _json(asset),
                        now,
                    ),
                )
                asset_row = connection.execute(
                    "SELECT id FROM assets WHERE asset_id = ?",
                    (asset_id,),
                ).fetchone()
                row_id = int(asset_row["id"])

                connection.execute(
                    "DELETE FROM asset_fts WHERE asset_id = ?",
                    (asset_id,),
                )
                connection.execute(
                    "INSERT INTO asset_fts(asset_id, search_text) VALUES (?, ?)",
                    (asset_id, search_text),
                )
                connection.execute(
                    "DELETE FROM asset_rtree WHERE asset_rowid = ?",
                    (row_id,),
                )
                spatial = asset.get("spatial", {})
                bounds = spatial.get("local_aabb", {})
                minimum = bounds.get("min", [-width / 2, -depth / 2, 0])
                maximum = bounds.get("max", [width / 2, depth / 2, height])
                connection.execute(
                    """
                    INSERT INTO asset_rtree(
                        asset_rowid, min_x, max_x, min_y, max_y, min_z, max_z
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row_id,
                        float(minimum[0]),
                        float(maximum[0]),
                        float(minimum[1]),
                        float(maximum[1]),
                        float(minimum[2]),
                        float(maximum[2]),
                    ),
                )
                seen.append(asset_id)

            if seen:
                placeholders = ",".join("?" for _ in seen)
                stale_rows = connection.execute(
                    f"""
                    SELECT id, asset_id FROM assets
                    WHERE library_id = ? AND asset_id NOT IN ({placeholders})
                    """,
                    [library_id, *seen],
                ).fetchall()
            else:
                stale_rows = connection.execute(
                    "SELECT id, asset_id FROM assets WHERE library_id = ?",
                    (library_id,),
                ).fetchall()
            for stale in stale_rows:
                connection.execute(
                    "DELETE FROM asset_fts WHERE asset_id = ?",
                    (stale["asset_id"],),
                )
                connection.execute(
                    "DELETE FROM asset_rtree WHERE asset_rowid = ?",
                    (stale["id"],),
                )
                referenced = connection.execute(
                    "SELECT 1 FROM instances WHERE asset_id = ? LIMIT 1",
                    (stale["asset_id"],),
                ).fetchone()
                if referenced:
                    # Scene history still points at this asset: keep the row
                    # for lookups but take it out of its library and search.
                    connection.execute(
                        """
                        UPDATE assets SET library_id = ?, file_available = 0,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (RETIRED_LIBRARY_ID, now, stale["id"]),
                    )
                else:
                    connection.execute(
                        "DELETE FROM assets WHERE id = ?",
                        (stale["id"],),
                    )
        return len(seen)


    @staticmethod
    def compact_asset(asset: dict[str, Any]) -> dict[str, Any]:
        return {
            "asset_id": asset["asset_id"],
            "library_id": asset.get("library_id", "ikea"),
            "brand": asset.get("brand", "IKEA"),
            "source_class": asset.get("source_class", "ikea_catalogue"),
            "catalogue_status": asset.get("catalogue_status"),
            "category": asset.get("category"),
            "series": asset.get("series"),
            "product": asset.get("product"),
            "variant": asset.get("variant"),
            "size_mm": [
                asset.get("dimensions_mm", {}).get("width"),
                asset.get("dimensions_mm", {}).get("depth"),
                asset.get("dimensions_mm", {}).get("height"),
            ],
            "match": asset.get("match_status"),
            "source_type": asset.get("geometry_source", {}).get("type"),
            "available": bool(asset.get("file_available")),
        }


    def search_assets(
        self,
        query: str = "",
        library_id: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        exact_dimensions_only: bool = False,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))
        clauses: list[str] = []
        parameters: list[Any] = []
        joins = ""
        ordering = "a.series, a.product, a.asset_id"

        if library_id.strip():
            clauses.append("a.library_id = ?")
            parameters.append(library_id.strip().lower())
        else:
            clauses.append("a.library_id != ?")
            parameters.append(RETIRED_LIBRARY_ID)
        tokens = re.findall(r"[\w-]+", query.lower(), flags=re.UNICODE)
        if tokens:
            joins = "JOIN asset_fts ON asset_fts.asset_id = a.asset_id"
            fts_query = " OR ".join(f'"{token}"*' for token in tokens[:12])
            clauses.append("asset_fts MATCH ?")
            parameters.append(fts_query)
            ordering = "bm25(asset_fts), a.series, a.product"
        if category.strip():
            clauses.append("a.category = ?")
            parameters.append(category.strip().lower())
        if max_width_mm > 0:
            clauses.append("a.width_mm <= ?")
            parameters.append(float(max_width_mm))
        if max_depth_mm > 0:
            clauses.append("a.depth_mm <= ?")
            parameters.append(float(max_depth_mm))
        if max_height_mm > 0:
            clauses.append("a.height_mm <= ?")
            parameters.append(float(max_height_mm))
        if exact_dimensions_only:
            clauses.append("a.match_status = 'exact_dimensions'")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        count_sql = f"SELECT COUNT(*) AS count FROM assets a {joins} {where}"
        query_sql = f"""
            SELECT a.metadata_json
            FROM assets a
            {joins}
            {where}
            ORDER BY {ordering}
            LIMIT ? OFFSET ?
        """
        with self._connect() as connection:
            total = int(connection.execute(count_sql, parameters).fetchone()["count"])
            rows = connection.execute(
                query_sql,
                [*parameters, limit, offset],
            ).fetchall()
        assets = [
            self.compact_asset(_decode(row["metadata_json"], {}))
            for row in rows
        ]
        next_offset = offset + len(assets)
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "next_offset": next_offset if next_offset < total else None,
            "assets": assets,
        }


    def get_asset(
        self,
        asset_id: str,
        library_id: str = "",
    ) -> dict[str, Any] | None:
        clauses = ["asset_id = ?"]
        parameters: list[Any] = [asset_id]
        if library_id.strip():
            clauses.append("library_id = ?")
            parameters.append(library_id.strip().lower())
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT metadata_json FROM assets WHERE {' AND '.join(clauses)}",
                parameters,
            ).fetchone()
        return _decode(row["metadata_json"], {}) if row else None


    def asset_stats(self, library_id: str = "") -> dict[str, Any]:
        where = ""
        parameters: list[Any] = []
        if library_id.strip():
            where = "WHERE library_id = ?"
            parameters.append(library_id.strip().lower())
        with self._connect() as connection:
            total = int(connection.execute(
                f"SELECT COUNT(*) AS count FROM assets {where}",
                parameters,
            ).fetchone()["count"])
            categories = [
                {"category": row["category"], "count": int(row["count"])}
                for row in connection.execute(
                    f"""
                    SELECT category, COUNT(*) AS count FROM assets
                    {where}
                    GROUP BY category ORDER BY category
                    """,
                    parameters,
                )
            ]
            libraries = [
                {"library_id": row["library_id"], "count": int(row["count"])}
                for row in connection.execute(
                    f"""
                    SELECT library_id, COUNT(*) AS count FROM assets
                    {where}
                    GROUP BY library_id ORDER BY library_id
                    """,
                    parameters,
                )
            ]
        return {"total": total, "libraries": libraries, "categories": categories}
