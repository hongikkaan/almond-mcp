"""Schema-driven SQLite reads with bounded queries and no application migrations."""

from __future__ import annotations

import json
import math
import sqlite3
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

MAX_COLUMNS = 128
CELL_LIMIT = 8192
SAMPLE_LIMIT = 300


def identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve(strict=True)
        if not self.path.is_file():
            raise ValueError("SQLite DB 파일을 선택해 주세요.")
        with self.connect() as db:
            db.execute("SELECT name FROM sqlite_schema LIMIT 1").fetchall()

    @contextmanager
    def connect(self):
        # Do not use AlmondStore: constructing it runs migrations and enables WAL.
        # mode=ro also includes committed WAL data; immutable=1 would miss it.
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=0.3)
        try:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            deadline = time.monotonic() + 2.0
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            db.execute("BEGIN")
            yield db
        finally:
            db.close()

    @staticmethod
    def _columns(db, name):
        return [dict(zip(("index", "name", "type", "not_null", "default", "pk", "hidden"), row))
                for row in db.execute("SELECT * FROM pragma_table_xinfo(?)", (name,))]

    @staticmethod
    def _relations(db, name):
        return [dict(zip(("id", "sequence", "target", "from", "to", "on_update", "on_delete", "match"), row))
                for row in db.execute("SELECT * FROM pragma_foreign_key_list(?)", (name,))]

    def _table(self, db, name):
        result = db.execute("SELECT type, sql FROM sqlite_schema WHERE name=? AND type IN ('table','view')", (name,)).fetchone()
        if not result:
            raise ValueError("테이블이 없거나 구조가 바뀌었습니다. 구조 새로고침을 눌러 주세요.")
        return {"name": name, "type": result[0], "sql": result[1],
                "columns": self._columns(db, name), "relations": self._relations(db, name)}

    def schema(self):
        with self.connect() as db:
            kinds = {row[1]: row[2] for row in db.execute("PRAGMA table_list") if row[0] == "main"}
            tables = []
            for name, in db.execute("SELECT name FROM sqlite_schema WHERE type IN ('table','view') ORDER BY name COLLATE NOCASE"):
                table = self._table(db, name)
                table["kind"] = kinds.get(name, table["type"])
                table["internal"] = name.startswith("sqlite_") or table["kind"] == "shadow"
                tables.append(table)
            return {"path": str(self.path), "name": self.path.name, "bytes": self.path.stat().st_size,
                    "schema_version": db.execute("PRAGMA schema_version").fetchone()[0],
                    "tables": tables, "read_only": True}

    @staticmethod
    def _selection(columns, cell_limit=CELL_LIMIT):
        expressions = []
        for col in columns:
            quoted = identifier(col["name"])
            # Bound TEXT/BLOB before crossing the SQLite/Python boundary.
            expressions.extend([
                f"CASE WHEN typeof({quoted}) IN ('text','blob') THEN substr({quoted},1,{cell_limit}) ELSE {quoted} END",
                f"CASE WHEN typeof({quoted}) IN ('text','blob') THEN length({quoted}) ELSE NULL END",
            ])
        return ", ".join(expressions)

    @staticmethod
    def _cells(record, cell_limit=CELL_LIMIT):
        cells = []
        for index in range(0, len(record), 2):
            value, length = record[index:index + 2]
            if isinstance(value, bytes):
                cells.append({"kind": "blob", "bytes": length, "hex": value[:32].hex()})
            elif isinstance(value, str) and length > cell_limit:
                cells.append({"kind": "text", "value": value, "characters": length, "truncated": True})
            elif isinstance(value, int) and abs(value) > 2**53 - 1:
                cells.append({"kind": "integer", "value": str(value)})
            elif isinstance(value, float) and not math.isfinite(value):
                cells.append({"kind": "number", "value": str(value)})
            else:
                cells.append(value)
        return cells

    def rows(self, name, *, offset=0, limit=50, search="", sort="", descending=False):
        if not 0 <= offset <= 1_000_000 or not 1 <= limit <= 100 or len(search) > 200:
            raise ValueError("조회 범위를 초과했습니다.")
        with self.connect() as db:
            table = self._table(db, name)
            columns = [c for c in table["columns"] if c["hidden"] != 1][:MAX_COLUMNS]
            if not columns:
                raise ValueError("표시할 열이 없습니다.")
            names = [c["name"] for c in columns]
            if sort and sort not in names:
                raise ValueError("정렬할 열이 없습니다. 구조 새로고침을 눌러 주세요.")
            params = []
            where = ""
            if search:
                escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                where = " WHERE " + " OR ".join(
                    f"(typeof({identifier(c)}) != 'blob' AND CAST({identifier(c)} AS TEXT) LIKE ? ESCAPE '\\')" for c in names)
                params = ["%" + escaped + "%"] * len(names)
            order = ""
            if sort:
                order = f" ORDER BY {identifier(sort)} {'DESC' if descending else 'ASC'}"
            else:
                primary = sorted((c for c in columns if c["pk"]), key=lambda c: c["pk"])
                if primary:
                    order = " ORDER BY " + ", ".join(identifier(c["name"]) for c in primary)
            records = db.execute(f"SELECT {self._selection(columns)} FROM {identifier(name)}{where}{order} LIMIT ? OFFSET ?",
                                 (*params, limit + 1, offset)).fetchall()
            return {"table": name, "columns": columns, "rows": [self._cells(row) for row in records[:limit]],
                    "offset": offset, "limit": limit, "has_more": len(records) > limit,
                    "omitted_columns": len([c for c in table["columns"] if c["hidden"] != 1]) - len(columns)}

    def profile(self, name):
        """Describe a bounded, unfiltered sample, never claim a whole-table count."""
        with self.connect() as db:
            table = self._table(db, name)
            columns = [c for c in table["columns"] if c["hidden"] != 1][:MAX_COLUMNS]
            if not columns:
                return {"sample_size": 0, "has_more": False, "columns": []}
            # Category labels need only a short prefix. Discard truncated values from distributions.
            records = db.execute(f"SELECT {self._selection(columns, 256)} FROM {identifier(name)} LIMIT ?", (SAMPLE_LIMIT + 1,)).fetchall()
            sampled = records[:SAMPLE_LIMIT]
            profiles = []
            for index, col in enumerate(columns):
                values = [row[index * 2] for row in sampled]
                non_null = [v for v in values if v is not None]
                item = {"name": col["name"], "nulls": len(values) - len(non_null), "kind": "empty"}
                numeric = [v for v in non_null if isinstance(v, (int, float)) and math.isfinite(v)]
                if numeric and len(numeric) == len(non_null) and all(abs(v) <= 2**53 - 1 for v in numeric):
                    low, high = min(numeric), max(numeric)
                    bins = [0] * (1 if low == high else 8)
                    for value in numeric:
                        bucket = 0 if low == high else min(7, int((value - low) / (high - low) * 8))
                        bins[bucket] += 1
                    item.update(kind="number", minimum=low, maximum=high, mean=sum(v / len(numeric) for v in numeric), bins=bins)
                elif non_null and all(isinstance(v, str) for v in non_null):
                    short = [row[index * 2] for row in sampled if row[index * 2] is not None and row[index * 2 + 1] <= 256]
                    counts = Counter(short)
                    item.update(kind="category", distinct=len(counts), excluded_long=len(non_null) - len(short),
                                top=[{"label": k, "count": v} for k, v in counts.most_common(8)])
                    try:
                        if short and all(isinstance(json.loads(v), (dict, list)) for v in short):
                            item["kind"] = "json"
                    except (ValueError, RecursionError):
                        pass
                elif non_null:
                    item["kind"] = "binary_or_mixed"
                profiles.append(item)
            return {"sample_size": len(sampled), "has_more": len(records) > SAMPLE_LIMIT, "columns": profiles,
                    "omitted_columns": len([c for c in table["columns"] if c["hidden"] != 1]) - len(columns)}
