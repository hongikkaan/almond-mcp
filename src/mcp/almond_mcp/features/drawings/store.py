"""Drawing Sheet ledger rules on the shared AlmondStore connection lifecycle."""
from __future__ import annotations

import math
import re
import uuid
from typing import Any, Callable

from almond_mcp.store_common import (
    DrawingSheetReconciliationError, _NativeRejected, _decode, _json, _utc_now,
)


class DrawingsStore:
    """Authored modelspace regions, Layout identity and native reconciliation."""

    def _initialize_drawing_sheets(self, connection) -> None:
        if not connection.in_transaction:
            connection.execute("BEGIN IMMEDIATE")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS drawing_sheets (
                sheet_id TEXT PRIMARY KEY,
                model_path TEXT NOT NULL,
                layout_id TEXT NOT NULL,
                title TEXT NOT NULL,
                drawing_type TEXT NOT NULL,
                scale_denominator REAL NOT NULL CHECK(scale_denominator > 0),
                paper_mm_json TEXT NOT NULL,
                model_bounds_mm_json TEXT NOT NULL,
                plan_id TEXT REFERENCES generation_plans(plan_id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(model_path, layout_id)
            )
        """)
        for table, field, target in (
            ("drawing_sheet_scenes", "scene_id", "scenes"),
            ("drawing_sheet_components", "component_id", "components"),
        ):
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    sheet_id TEXT NOT NULL REFERENCES drawing_sheets(sheet_id) ON DELETE CASCADE,
                    {field} TEXT NOT NULL REFERENCES {target}({field}) ON DELETE RESTRICT,
                    PRIMARY KEY(sheet_id, {field})
                )
            """)
            connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_ref ON {table}({field}, sheet_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_drawing_sheets_plan ON drawing_sheets(plan_id)")

    @staticmethod
    def _drawing_sheet_handle(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
            raise ValueError("sheet_id must be a nonempty stable handle.")
        return value

    def _drawing_sheet_metadata(self, values):
        fields = ("title", "drawing_type", "scale_denominator", "paper_mm", "model_bounds_mm",
                  "scene_ids", "component_ids", "plan_id")
        if any(field not in values for field in fields):
            raise ValueError("A drawing sheet snapshot must include all metadata fields.")
        title = self._generation_text(values["title"], "title")
        drawing_type = self._generation_text(values["drawing_type"], "drawing_type").lower()
        if drawing_type not in {"plan", "section", "elevation", "detail", "axonometric", "perspective", "schedule", "other"}:
            raise ValueError("Unsupported drawing_type.")
        scale = values["scale_denominator"]
        if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("scale_denominator must be a finite positive number.")
        paper, bounds = values["paper_mm"], values["model_bounds_mm"]
        for value, count, field in ((paper, 2, "paper_mm"), (bounds, 6, "model_bounds_mm")):
            if not isinstance(value, list) or len(value) != count or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in value
            ):
                raise ValueError(f"{field} must contain {count} finite numbers.")
        if any(value <= 0 for value in paper):
            raise ValueError("paper_mm must contain positive width and height.")
        if bounds[0] >= bounds[3] or bounds[1] >= bounds[4] or bounds[2] > bounds[5]:
            raise ValueError("model_bounds_mm must have positive world XY extents and ordered Z bounds.")
        plan_id = values["plan_id"]
        if plan_id is not None:
            plan_id = self._generation_text(plan_id, "plan_id", allow_empty=True) or None
        return dict(title=title, drawing_type=drawing_type, scale_denominator=float(scale),
                    paper_mm=[float(value) for value in paper], model_bounds_mm=[float(value) for value in bounds],
                    scene_ids=sorted(self._generation_refs(values["scene_ids"], "scene_ids")),
                    component_ids=sorted(self._generation_refs(values["component_ids"], "component_ids")), plan_id=plan_id)

    def _drawing_sheet_validate_refs(self, connection, data):
        self._validate_generation_refs(connection, data["scene_ids"], data["component_ids"])
        if data["plan_id"] and not connection.execute(
            "SELECT 1 FROM generation_plans WHERE plan_id = ?", (data["plan_id"],)
        ).fetchone():
            raise KeyError(f"Unknown plan_id: {data['plan_id']}")

    @staticmethod
    def _read_drawing_sheet(connection, sheet_id):
        row = connection.execute("SELECT * FROM drawing_sheets WHERE sheet_id = ?", (sheet_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["paper_mm"] = _decode(result.pop("paper_mm_json"), [])
        result["model_bounds_mm"] = _decode(result.pop("model_bounds_mm_json"), [])
        for table, field, key in (
            ("drawing_sheet_scenes", "scene_id", "scene_ids"),
            ("drawing_sheet_components", "component_id", "component_ids"),
        ):
            result[key] = [item[field] for item in connection.execute(
                f"SELECT {field} FROM {table} WHERE sheet_id = ? ORDER BY {field}", (sheet_id,),
            )]
        return dict(result, registration_status="registered", live_verified=False)

    def get_drawing_sheet(self, sheet_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN")
            return self._read_drawing_sheet(connection, sheet_id)

    def list_drawing_sheets(
        self, plan_id: str = "", scene_id: str = "", component_id: str = "",
        model_path: str = "", limit: int = 100,
    ) -> dict[str, Any]:
        limit = self._generation_limit(limit)
        clauses, arguments = [], []
        for field, value in (("plan_id", plan_id), ("model_path", model_path)):
            if value:
                clauses.append(f"s.{field} = ?")
                arguments.append(self._component_model_path(value) if field == "model_path" else value)
        for table, field, value in (
            ("drawing_sheet_scenes", "scene_id", scene_id),
            ("drawing_sheet_components", "component_id", component_id),
        ):
            if value:
                clauses.append(f"EXISTS (SELECT 1 FROM {table} r WHERE r.sheet_id = s.sheet_id AND r.{field} = ?)")
                arguments.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute("SELECT COUNT(*) FROM drawing_sheets s" + where, arguments).fetchone()[0]
            rows = connection.execute(
                "SELECT s.sheet_id FROM drawing_sheets s" + where + " ORDER BY s.title, s.sheet_id LIMIT ?",
                [*arguments, limit],
            ).fetchall()
            sheets = [self._read_drawing_sheet(connection, row["sheet_id"]) for row in rows]
        return dict(sheets=sheets, total=total, limit=limit, truncated=total > len(sheets), live_verified=False)

    @staticmethod
    def _drawing_sheet_request(action, data):
        return {"type": "drawing_sheet", "action": action, "expected_model_path": data["model_path"],
                **{key: ("" if key == "plan_id" and value is None else value) for key, value in data.items()
                   if key not in {"model_path", "created_at", "updated_at", "registration_status", "live_verified"}}}

    @staticmethod
    def _drawing_sheet_matches_expected(data, expected):
        """Compare Rhino-measured numbers with rounding tolerance; IDs and labels remain exact."""
        def same_number(left, right):
            return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-6)

        for key, value in expected.items():
            actual = data[key]
            if key == "scale_denominator":
                if not same_number(actual, value):
                    return False
            elif key in {"paper_mm", "model_bounds_mm"}:
                if len(actual) != len(value) or any(
                    not same_number(left, right) for left, right in zip(actual, value)
                ):
                    return False
            elif actual != value:
                return False
        return True

    def _drawing_sheet_check_unregistered_proof(self, observed, sheet_id, model_path, layout_id):
        if (not isinstance(observed, dict) or observed.get("complete") is not True
                or observed.get("truncated") or observed.get("registration_status") != "unregistered"
                or observed.get("sheet_id") != sheet_id
                or self._component_model_path(observed.get("model_path")) != model_path
                or self._component_guid(observed.get("layout_id")) != layout_id):
            raise ValueError("Native unregistered Layout proof does not match the drawing sheet.")

    def _drawing_sheet_store_snapshot(self, connection, observed, model_path, sheet_id, layout_id="", expected=None):
        if not isinstance(observed, dict) or observed.get("complete") is not True or observed.get("truncated"):
            raise ValueError("Native drawing sheet snapshot must be complete and untruncated.")
        if observed.get("registration_status", "registered") != "registered":
            raise ValueError("Native Layout is not registered as a drawing sheet.")
        actual_layout = self._component_guid(observed.get("layout_id"))
        if (observed.get("sheet_id") != sheet_id
                or self._component_model_path(observed.get("model_path")) != model_path
                or (layout_id and actual_layout != layout_id)):
            raise ValueError("Native drawing sheet identity does not match the request.")
        data = self._drawing_sheet_metadata(observed)
        self._drawing_sheet_validate_refs(connection, data)
        if expected is not None and not self._drawing_sheet_matches_expected(data, expected):
            raise ValueError("Native drawing sheet metadata differs from the requested values.")
        existing = self._read_drawing_sheet(connection, sheet_id)
        if existing and (existing["model_path"] != model_path or existing["layout_id"] != actual_layout):
            raise ValueError("A drawing sheet cannot be rebound to another model or Layout.")
        owner = connection.execute(
            "SELECT sheet_id FROM drawing_sheets WHERE model_path = ? AND layout_id = ?", (model_path, actual_layout),
        ).fetchone()
        if owner and owner["sheet_id"] != sheet_id:
            raise ValueError("The Layout is already registered as another drawing sheet.")
        now = _utc_now()
        connection.execute("""
            INSERT INTO drawing_sheets(sheet_id, model_path, layout_id, title, drawing_type,
                scale_denominator, paper_mm_json, model_bounds_mm_json, plan_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sheet_id) DO UPDATE SET title = excluded.title, drawing_type = excluded.drawing_type,
                scale_denominator = excluded.scale_denominator, paper_mm_json = excluded.paper_mm_json,
                model_bounds_mm_json = excluded.model_bounds_mm_json, plan_id = excluded.plan_id,
                updated_at = excluded.updated_at
        """, (sheet_id, model_path, actual_layout, data["title"], data["drawing_type"], data["scale_denominator"],
              _json(data["paper_mm"]), _json(data["model_bounds_mm"]), data["plan_id"], now, now))
        for table, field, key in (
            ("drawing_sheet_scenes", "scene_id", "scene_ids"),
            ("drawing_sheet_components", "component_id", "component_ids"),
        ):
            connection.execute(f"DELETE FROM {table} WHERE sheet_id = ?", (sheet_id,))
            connection.executemany(f"INSERT INTO {table}(sheet_id, {field}) VALUES (?, ?)",
                                   [(sheet_id, value) for value in data[key]])
        return dict(self._read_drawing_sheet(connection, sheet_id), live_verified=True)

    def upsert_drawing_sheet(
        self, model_path: str, title: str, drawing_type: str, scale_denominator: float,
        paper_mm: list[float], model_bounds_mm: list[float], scene_ids: list[str] | None = None,
        component_ids: list[str] | None = None, plan_id: str | None = None,
        sheet_id: str = "", layout_id: str = "", native_apply: Callable | None = None,
    ) -> dict[str, Any]:
        model_path = self._component_model_path(model_path)
        sheet_id = self._drawing_sheet_handle(sheet_id or f"sheet_{uuid.uuid4().hex[:12]}")
        layout_id = self._component_guid(layout_id) if layout_id else ""
        if not callable(native_apply):
            raise ValueError("Native Layout creation/update is required.")
        attempted = False
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = self._read_drawing_sheet(connection, sheet_id)
                if existing:
                    if existing["model_path"] != model_path or (layout_id and existing["layout_id"] != layout_id):
                        raise ValueError("A drawing sheet cannot be rebound to another model or Layout.")
                    layout_id = existing["layout_id"]
                if layout_id:
                    owner = connection.execute(
                        "SELECT sheet_id FROM drawing_sheets WHERE model_path = ? AND layout_id = ?", (model_path, layout_id),
                    ).fetchone()
                    if owner and owner["sheet_id"] != sheet_id:
                        raise ValueError("The Layout is already registered as another drawing sheet.")
                data = self._drawing_sheet_metadata(dict(
                    title=title, drawing_type=drawing_type, scale_denominator=scale_denominator,
                    paper_mm=paper_mm, model_bounds_mm=model_bounds_mm,
                    scene_ids=scene_ids if scene_ids is not None else (existing["scene_ids"] if existing else []),
                    component_ids=component_ids if component_ids is not None else (existing["component_ids"] if existing else []),
                    plan_id=plan_id if plan_id is not None else (existing["plan_id"] if existing else None),
                ))
                self._drawing_sheet_validate_refs(connection, data)
                request = self._drawing_sheet_request("upsert", dict(data, sheet_id=sheet_id, model_path=model_path, layout_id=layout_id))
                attempted = True
                reply = self._component_native(native_apply, request)
                result = self._drawing_sheet_store_snapshot(
                    connection, reply.get("sheet"), model_path, sheet_id, layout_id, expected=data,
                )
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise DrawingSheetReconciliationError(sheet_id, model_path, str(exc)) from exc
            raise
        return result

    def sync_drawing_sheet(
        self, model_path: str, sheet_id: str, layout_id: str = "", native_inspect: Callable | None = None,
    ) -> dict[str, Any]:
        model_path = self._component_model_path(model_path)
        sheet_id = self._drawing_sheet_handle(sheet_id)
        layout_id = self._component_guid(layout_id) if layout_id else ""
        if not callable(native_inspect):
            raise ValueError("Native read-only Layout inspection is required.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._read_drawing_sheet(connection, sheet_id)
            if existing:
                if existing["model_path"] != model_path or (layout_id and existing["layout_id"] != layout_id):
                    raise ValueError("A drawing sheet cannot be rebound to another model or Layout.")
                layout_id = existing["layout_id"]
            request = dict(type="drawing_sheet", action="inspect", expected_model_path=model_path,
                           sheet_id=sheet_id, layout_id=layout_id)
            if existing:
                request["expected_sheet"] = {key: ("" if key == "plan_id" and value is None else value)
                                             for key, value in existing.items()
                                             if key not in {"created_at", "updated_at", "registration_status", "live_verified"}}
            reply = self._component_native(native_inspect, request)
            observed = reply.get("sheet")
            if isinstance(observed, dict) and observed.get("registration_status") == "unregistered":
                if existing is None:
                    raise ValueError("Unregistered Layout proof does not match an existing drawing sheet.")
                self._drawing_sheet_check_unregistered_proof(observed, sheet_id, model_path, layout_id)
                connection.execute("DELETE FROM drawing_sheets WHERE sheet_id = ?", (sheet_id,))
                result = dict(sheet_id=sheet_id, model_path=model_path, layout_id=layout_id,
                              registration_status="unregistered", live_verified=True)
            else:
                result = self._drawing_sheet_store_snapshot(connection, observed, model_path, sheet_id, layout_id)
        return result

    def remove_drawing_sheet(self, sheet_id: str, native_apply: Callable | None = None) -> dict[str, Any]:
        if not callable(native_apply):
            raise ValueError("Native drawing sheet unregistration is required.")
        attempted, model_path = False, ""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = self._read_drawing_sheet(connection, sheet_id)
                if existing is None:
                    raise KeyError(f"Unknown sheet_id: {sheet_id}")
                model_path = existing["model_path"]
                attempted = True
                reply = self._component_native(native_apply, self._drawing_sheet_request("unregister", existing))
                # Native unregister deliberately returns a compact top-level identity
                # acknowledgement. Only the read-only inspect path carries a full
                # nested unregistered snapshot with complete/status proof.
                if (reply.get("sheet_id") != sheet_id
                        or self._component_model_path(reply.get("model_path")) != model_path
                        or self._component_guid(reply.get("layout_id")) != existing["layout_id"]):
                    raise ValueError("Native unregistration acknowledgement does not match the drawing sheet.")
                connection.execute("DELETE FROM drawing_sheets WHERE sheet_id = ?", (sheet_id,))
                result = dict(sheet_id=sheet_id, model_path=model_path, layout_id=existing["layout_id"],
                              registration_status="unregistered", live_verified=True)
        except _NativeRejected:
            raise
        except Exception as exc:
            if attempted:
                raise DrawingSheetReconciliationError(sheet_id, model_path, str(exc)) from exc
            raise
        return result
