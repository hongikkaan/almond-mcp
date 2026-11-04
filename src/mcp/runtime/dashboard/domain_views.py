"""Read-only named projections of the stored Scene/Holon/Phase/Plan model.

Never instantiate AlmondStore here: its constructor migrates the selected DB.
Task is the dashboard label for the existing generation_plans records.
"""
from __future__ import annotations

import json
import sqlite3

from .database import Database, identifier

PAGE_SIZE = 20
RELATED_LIMIT = 200
LINK_LIMIT = 2000
KINDS = ("scenes", "holons", "phases", "tasks")


def text(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("value", ""))
    return str(value)


def label(record, *fields):
    return next((text(record.get(field)).strip() for field in fields if text(record.get(field)).strip()), "이름 미기록")


def json_list(value):
    try:
        result = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError):
        return []
    return result if isinstance(result, list) else []


class DomainViews:
    def __init__(self, connection):
        self.db = connection
        self.columns = {}
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_schema WHERE type IN ('table','view')")}
        for name in ("scenes", "ontological_holons", "_component_records", "components", "generation_phases",
                     "generation_plans", "generation_plan_steps", "generation_plan_scenes", "ontological_scene_context",
                     "scene_ontological", "_scene_component_refs", "scene_components", "document_objects"):
            if name in names:
                self.columns[name] = [row[1] for row in connection.execute("SELECT * FROM pragma_table_xinfo(?)", (name,))]
        self.holon_table, self.holon_key = None, None
        for name, key in (("ontological_holons", "ontological_id"), ("_component_records", "component_id"), ("components", "component_id")):
            if self.has(name, key, "name") and (name != "components" or self.has(name, "rhino_group_id") or self.has(name, "model_path")):
                self.holon_table, self.holon_key = name, key
                break
        self.object_key = next((key for key in ("ontological_id", "component_id") if self.has("document_objects", key, "name")), None)
        self.step_goal = next((key for key in ("goal", "objective") if self.has("generation_plan_steps", key)), None)
        self.notes = []

    def has(self, table, *columns):
        return table in self.columns and set(columns).issubset(self.columns[table])

    def capabilities(self):
        return {
            "scenes": self.has("scenes", "scene_id", "name"),
            "holons": bool(self.holon_table),
            "phases": self.has("generation_phases", "phase_id", "name") and self.has("generation_plans", "plan_id", "phase_id"),
            "tasks": self.has("generation_plans", "plan_id"),
            "steps": self.has("generation_plan_steps", "plan_id", "step_id"),
            "object_names": bool(self.object_key or (self.holon_table and self.has(self.holon_table, "object_names_json"))),
            "step_goals": bool(self.step_goal),
        }

    def rows(self, table, where="1", params=(), order="", limit=LINK_LIMIT + 1, offset=0):
        columns = [{"name": name} for name in self.columns[table][:128]]
        query = f"SELECT {Database._selection(columns)} FROM {identifier(table)} WHERE {where}"
        if order:
            query += " ORDER BY " + order
        records = self.db.execute(query + " LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall()
        return [dict(zip((column["name"] for column in columns), Database._cells(record))) for record in records]

    def order(self, table, *fields):
        return ",".join(identifier(field) + " COLLATE NOCASE" for field in fields if self.has(table, field))

    def search_clause(self, table, fields, search):
        fields = [field for field in fields if self.has(table, field)]
        if not search or not fields:
            return "1", ()
        return "(" + " OR ".join(f"instr(lower(CAST({identifier(field)} AS TEXT)),lower(?))>0" for field in fields) + ")", (search,) * len(fields)

    def page(self, kind, *, search="", focus="", offset=0, limit=PAGE_SIZE):
        if kind not in KINDS or not self.capabilities()[kind]:
            raise ValueError("이 DB에는 해당 조회에 필요한 테이블이 없습니다. 전체 테이블에서 원본 구조를 확인하세요.")
        if len(search) > 200 or len(focus) > 200 or not 0 <= offset <= 10_000_000 or not 1 <= limit <= PAGE_SIZE:
            raise ValueError("조회 범위 또는 검색어가 올바르지 않습니다.")
        table, key, names = {"scenes": ("scenes", "scene_id", ("name",)),
                             "holons": (self.holon_table, self.holon_key, ("name",)),
                             "phases": ("generation_phases", "phase_id", ("name", "description")),
                             "tasks": ("generation_plans", "plan_id", ("title", "goal", "scope"))}[kind]
        where, params = self.search_clause(table, names, search)
        if focus:
            where += f" AND {identifier(key)}=?"
            params += (focus,)
        records = self.rows(table, where, params, self.order(table, *names[:1], key), limit + 1, offset)
        more, records = len(records) > limit, records[:limit]
        if any(not isinstance(row.get(key), str) or not row[key] or len(row[key]) > 200 for row in records):
            raise ValueError("이 DB의 항목 ID 형식은 도메인 조회에서 지원하지 않습니다. 전체 테이블에서 확인하세요.")
        groups = getattr(self, kind)(records)
        if kind == "phases" and not more and not focus:
            where = '(phase_id IS NULL OR phase_id=\'\')'
            search_where, args = self.search_clause("generation_plans", ("title", "goal", "scope"), search)
            unassigned = self.rows("generation_plans", where + " AND " + search_where, args,
                                   self.order("generation_plans", "title", "plan_id"), RELATED_LIMIT + 1)
            if unassigned:
                groups.append({"id": None, "name": "Phase 미지정", "tasks": self.limited(unassigned, "Phase 미지정 Task")})
        caps = self.capabilities()
        if kind in ("scenes", "holons") and not caps["object_names"]:
            self.notes.append("현재 DB에는 개별 객체 이름이 저장되지 않습니다. 객체 이름은 ‘미기록’으로 표시합니다.")
        if kind == "tasks" and not caps["step_goals"]:
            self.notes.append("현재 DB에는 Step별 목표가 저장되지 않습니다. Task 목표와 scope는 별도로 표시합니다.")
        if kind == "tasks" and not caps["steps"]:
            self.notes.append("현재 DB에는 Step 저장 구조가 없습니다.")
        return {"view": kind, "groups": groups, "offset": offset, "limit": limit, "has_more": more,
                "focus": focus, "notes": list(dict.fromkeys(self.notes)), "capabilities": caps}

    def limited(self, records, description):
        if len(records) > RELATED_LIMIT:
            self.notes.append(f"{description}: 처음 {RELATED_LIMIT}개만 표시합니다. 나머지는 전체 테이블에서 확인하세요.")
        return records[:RELATED_LIMIT]

    def links(self, table, left, right, ids):
        if not ids or not self.has(table, left, right):
            return []
        placeholders = ",".join("?" for _ in ids)
        result = self.db.execute(f"SELECT substr(CAST({identifier(left)} AS TEXT),1,8192),"
                                 f"substr(CAST({identifier(right)} AS TEXT),1,8192) FROM {identifier(table)} "
                                 f"WHERE {identifier(left)} IN ({placeholders}) ORDER BY 1,2 LIMIT ?",
                                 (*ids, LINK_LIMIT + 1)).fetchall()
        if len(result) > LINK_LIMIT:
            self.notes.append(f"연결 목록은 처음 {LINK_LIMIT}개만 표시합니다.")
        return result[:LINK_LIMIT]

    def holon_links(self, scene_ids):
        links = set()
        for table, key in (("ontological_scene_context", "ontological_id"), ("scene_ontological", "ontological_id"),
                           ("_scene_component_refs", "component_id"), ("scene_components", "component_id")):
            links.update(self.links(table, "scene_id", key, scene_ids))
        return links

    def task_links(self, scene_ids):
        links = set(self.links("generation_plan_scenes", "scene_id", "plan_id", scene_ids))
        links.update(self.links("generation_plans", "scene_id", "plan_id", scene_ids))
        return links

    def indexed(self, table, key, ids):
        ids = sorted(set(ids))
        if not ids:
            return {}
        result = self.rows(table, identifier(key) + " IN (" + ",".join("?" for _ in ids) + ")", ids)
        return {text(row.get(key)): row for row in result[:LINK_LIMIT]}

    def object_names(self, holon):
        names = [name for name in json_list(holon.get("object_names_json")) if isinstance(name, str) and name.strip()]
        if self.object_key:
            records = self.rows("document_objects", identifier(self.object_key) + "=?", (holon[self.holon_key],),
                                self.order("document_objects", "name"), RELATED_LIMIT + 1)
            names += [text(row.get("name")) for row in self.limited(records, "객체 이름") if text(row.get("name")).strip()]
        return list(dict.fromkeys(names))[:RELATED_LIMIT]

    @staticmethod
    def ref(record, key, *names):
        return {"id": text(record[key]), "name": label(record, *names)}

    def scenes(self, records):
        scene_ids = [row["scene_id"] for row in records]
        links = self.holon_links(scene_ids) if self.holon_table else set()
        holons = self.indexed(self.holon_table, self.holon_key, [right for _, right in links]) if self.holon_table else {}
        tasks_links = self.task_links(scene_ids) if self.has("generation_plans", "plan_id") else set()
        tasks = self.indexed("generation_plans", "plan_id", [right for _, right in tasks_links]) if tasks_links else {}
        result = []
        for row in records:
            linked = [holons[right] for left, right in sorted(links) if left == row["scene_id"] and right in holons]
            result.append({"id": row["scene_id"], "name": label(row, "name"),
                           "holons": sorted([self.ref(item, self.holon_key, "name") for item in linked], key=lambda item: (item["name"], item["id"])),
                           "objects": list(dict.fromkeys(name for item in linked for name in self.object_names(item)))[:RELATED_LIMIT],
                           "tasks": sorted([self.ref(tasks[right], "plan_id", "title", "name") for left, right in tasks_links
                                            if left == row["scene_id"] and right in tasks], key=lambda item: (item["name"], item["id"]))})
        return result

    def holons(self, records):
        return self._holon_groups(records)

    def _holon_groups(self, records):
        result = []
        for row in records:
            key = row[self.holon_key]
            scene_ids = set()
            for table, column in (("ontological_scene_context", "ontological_id"), ("scene_ontological", "ontological_id"),
                                  ("_scene_component_refs", "component_id"), ("scene_components", "component_id")):
                scene_ids.update(right for _, right in self.links(table, column, "scene_id", [key]))
            scene_ids.update(item for item in json_list(row.get("scene_ids_json")) if isinstance(item, str))
            scenes = self.indexed("scenes", "scene_id", scene_ids) if self.has("scenes", "scene_id", "name") else {}
            parent_key = row.get("parent_ontological_id", row.get("parent_component_id"))
            parent = self.indexed(self.holon_table, self.holon_key, [parent_key]) if parent_key else {}
            result.append({"id": key, "name": label(row, "name"),
                           "scenes": [self.ref(item, "scene_id", "name") for item in sorted(scenes.values(), key=lambda item: label(item, "name"))],
                           "parent": self.ref(parent[parent_key], self.holon_key, "name") if parent_key in parent else None,
                           "objects": self.object_names(row), "object_count": row.get("object_count"),
                           "availability": row.get("availability", "미기록")})
        return result

    def phases(self, records):
        result = []
        for row in records:
            tasks = self.rows("generation_plans", "phase_id=?", (row["phase_id"],),
                              self.order("generation_plans", "title", "plan_id"), RELATED_LIMIT + 1)
            result.append({"id": row["phase_id"], "name": label(row, "name"),
                           "tasks": self.limited(tasks, "Phase 소속 Task")})
        return result

    def tasks(self, records):
        result = []
        for row in records:
            steps = []
            if self.has("generation_plan_steps", "plan_id", "step_id"):
                # position is stored as an INTEGER; retain it rather than sorting step names.
                order = ("position," if self.has("generation_plan_steps", "position") else "") + "step_id"
                steps = self.rows("generation_plan_steps", "plan_id=?", (row["plan_id"],), order, RELATED_LIMIT + 1)
            result.append({"id": row["plan_id"], "name": label(row, "title", "name"), "revision": row.get("revision"),
                           "goal": row.get("goal"), "scope": row.get("scope"), "status": row.get("status"),
                           "steps": [{"id": step["step_id"], "name": label(step, "name", "step_id"),
                                      "status": step.get("status"), "goal": step.get(self.step_goal), "position": step.get("position")}
                                     for step in self.limited(steps, "Task 소속 Step")]})
        return result

    def detail(self, kind, key, parent=""):
        if not key or len(key) > 200 or len(parent) > 200:
            raise ValueError("조회할 항목을 선택하세요.")
        if kind == "steps":
            if not self.has("generation_plan_steps", "step_id", "plan_id") or not self.has("generation_plans", "plan_id") or not parent:
                raise ValueError("Step을 조회하려면 소속 Task가 필요합니다.")
            records = self.rows("generation_plan_steps", "step_id=? AND plan_id=?", (key, parent), limit=1)
            plan = self.rows("generation_plans", "plan_id=?", (parent,), limit=1)
            if not records or not plan:
                raise ValueError("선택한 Step 또는 Task가 없습니다. 새로고침해 주세요.")
            return {"title": label(records[0], "name", "step_id"),
                    "fields": {"Task 이름": label(plan[0], "title", "name"), "Task revision": plan[0].get("revision"), **records[0]}}
        mapping = {"scenes": ("scenes", "scene_id", "name"), "holons": (self.holon_table, self.holon_key, "name"),
                   "phases": ("generation_phases", "phase_id", "name"), "tasks": ("generation_plans", "plan_id", "title")}
        if kind not in mapping or not self.capabilities()[kind]:
            raise ValueError("지원하지 않는 조회입니다.")
        table, column, name = mapping[kind]
        records = self.rows(table, identifier(column) + "=?", (key,), limit=1)
        if not records:
            raise ValueError("선택한 항목이 없습니다. 새로고침해 주세요.")
        return {"title": label(records[0], name), "fields": records[0]}
