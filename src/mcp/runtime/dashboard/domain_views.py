"""Read-only named projections of the stored Scene/Holon/Phase/Plan model.

Never instantiate AlmondStore here: its constructor migrates the selected DB.
Task is the dashboard label for the existing generation_plans records.
"""
from __future__ import annotations

import json
import sqlite3

from .database import Database, identifier
from .loop_history import loop_numbers, loop_row, read_history, stored_loop_directory

PAGE_SIZE = 20
RELATED_LIMIT = 200
LINK_LIMIT = 2000
KINDS = ("files", "scenes", "holons", "phases", "tasks", "steps")
PLAN_OUTLINE_FIELDS = ("plan_id", "title", "name", "status", "previous_id", "parent_plan_json", "child_plan_json",
                       "phase_id", "scene_id")


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
        self.notes = []
        self.outline_catalogue = None
        entries = {row[1]: (row[2], row[3]) for row in connection.execute("PRAGMA table_list") if row[0] == "main"}
        for name in ("project_files", "generation_phase_files", "generation_plan_ontological",
                     "scenes", "ontological_holons", "components", "generation_phases",
                     "generation_plans", "generation_plan_steps", "generation_loop_steps", "generation_plan_scenes", "ontological_scene_context",
                     "scene_ontological", "_scene_component_refs", "scene_components", "document_objects",
                     "workflow_statuses", "generation_plan_loops", "generation_plan_revisions"):
            if name not in entries:
                continue
            kind, column_count = entries[name]
            if kind == "view" and column_count == 0:
                self.notes.append(f"참조를 해석할 수 없는 뷰({name})는 조회에 사용하지 않습니다.")
                continue
            self.columns[name] = [row[1] for row in connection.execute("SELECT * FROM pragma_table_xinfo(?)", (name,))]
        self.holon_table, self.holon_key = None, None
        for name, key in (("ontological_holons", "ontological_id"), ("components", "component_id")):
            if self.has(name, key, "name") and (name != "components" or self.has(name, "rhino_group_id") or self.has(name, "model_path")):
                self.holon_table, self.holon_key = name, key
                break
        self.object_key = next((key for key in ("ontological_id", "component_id") if self.has("document_objects", key, "name")), None)
        self.step_goal = next((key for key in ("goal", "objective") if self.has("generation_plan_steps", key)), None)

    def has(self, table, *columns):
        return table in self.columns and set(columns).issubset(self.columns[table])

    def capabilities(self):
        return {
            "files": self.has("project_files", "file_name"),
            "scenes": self.has("scenes", "scene_id", "name"),
            "holons": bool(self.holon_table),
            "phases": self.has("generation_phases", "phase_id", "name") and self.has("generation_plans", "plan_id", "phase_id"),
            "tasks": self.has("generation_plans", "plan_id"),
            "steps": self.has("generation_plan_steps", "plan_id", "step_id") and self.has("generation_plans", "plan_id"),
            "object_names": bool(self.object_key or (self.holon_table and self.has(self.holon_table, "object_names_json"))),
            "step_goals": bool(self.step_goal),
        }

    def rows(self, table, where="1", params=(), order="", limit=LINK_LIMIT + 1, offset=0, *, fields=None):
        names = self.columns[table]
        if fields is not None:
            names = [field for field in fields if field in names]
        columns = [{"name": name} for name in names[:128]]
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

    def page(self, kind, *, search="", focus="", parent="", file="", phase="", scene="", status="", execution="",
             offset=0, limit=PAGE_SIZE, loop_no=None):
        if loop_no is not None and (kind != "tasks" or not focus or type(loop_no) is not int or not 0 <= loop_no < 2**53):
            raise ValueError("회차 조회에는 Task 하나와 0 이상의 회차 번호가 필요합니다.")
        if kind not in KINDS or not self.capabilities()[kind]:
            raise ValueError("이 DB에는 해당 조회에 필요한 저장 구조가 없습니다.")
        if any(not isinstance(value, str) or len(value) > 200 for value in (search, focus, parent, file, phase, scene, status)) or not 0 <= offset <= 10_000_000 or not 1 <= limit <= PAGE_SIZE:
            raise ValueError("조회 범위 또는 검색어가 올바르지 않습니다.")
        table, key, names = {"scenes": ("scenes", "scene_id", ("name",)),
                             "files": ("project_files", "file_name", ("file_name", "description")),
                             "holons": (self.holon_table, self.holon_key, ("name",)),
                             "phases": ("generation_phases", "phase_id", ("name", "description")),
                             "tasks": ("generation_plans", "plan_id", ("title", "goal", "scope")),
                             "steps": ("generation_plan_steps", "step_id", ("name", "step_type", "step_id"))}[kind]
        where, params = self.search_clause(table, names, search)
        if focus:
            where += f" AND {identifier(key)}=?"
            params += (focus,)
        if kind == "steps":
            where += ' AND plan_id IN (SELECT plan_id FROM generation_plans)'
            if parent:
                where += ' AND plan_id=?'
                params += (parent,)
        if kind in ("tasks", "steps"):
            task_where, task_params = self.task_filter(file=file, phase=phase, scene=scene, status=status, execution=execution)
            if kind == "steps":
                where += ' AND plan_id IN (SELECT plan_id FROM generation_plans WHERE ' + task_where + ')'
            else:
                where += ' AND (' + task_where + ')'
            params += task_params
        elif file and kind in ("scenes", "holons"):
            where += ' AND file_name=?' if self.has(table, "file_name") else ' AND 0'
            if self.has(table, "file_name"):
                params += (file,)
        elif file and kind == "phases":
            if "generation_phase_files" in self.columns:
                valid = self.has("generation_phase_files", "phase_id", "file_name")
                where += ' AND phase_id IN (SELECT phase_id FROM generation_phase_files WHERE file_name=?)' if valid else ' AND 0'
                if valid:
                    params += (file,)
            elif self.has(table, "file_name"):
                where += ' AND file_name=?'
                params += (file,)
            else:
                where += ' AND 0'
        if kind == "holons" and scene:
            scene_where, scene_params = self.holon_scene_filter(scene)
            where += " AND (" + scene_where + ")"
            params += scene_params
        order = self.order(table, "plan_id", "position", "step_id") if kind == "steps" else self.order(table, *names[:1], key)
        records = self.rows(table, where, params, order, limit + 1, offset)
        more, records = len(records) > limit, records[:limit]
        if any(not isinstance(row.get(key), str) or not row[key] or len(row[key]) > 200 for row in records):
            raise ValueError("이 DB의 항목 ID 형식은 도메인 조회에서 지원하지 않습니다.")
        if kind == "tasks":
            groups = self.tasks(records, loop_no)
        else:
            groups = self.step_groups(records) if kind == "steps" else getattr(self, kind)(records)
        if kind == "phases" and not more and not focus:
            where = '(phase_id IS NULL OR phase_id=\'\')'
            search_where, args = self.search_clause("generation_plans", ("title", "goal", "scope"), search)
            filter_where, filter_args = self.task_filter(file=file)
            unassigned = self.rows("generation_plans", where + " AND " + search_where + " AND " + filter_where, args + filter_args,
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
        filters = {"file": file, "phase": phase, "scene": scene}
        if kind in ("tasks", "steps"):
            filters.update(status=status, execution=execution)
        return {"view": kind, "groups": groups, "offset": offset, "limit": limit, "has_more": more,
                "focus": focus, "parent": parent, "filters": filters,
                "notes": list(dict.fromkeys(self.notes)), "capabilities": caps}

    def options(self, *, file="", phase="", scene="", status="", execution="", search=""):
        if any(not isinstance(value, str) or len(value) > 200 for value in (file, phase, scene, status, search)):
            raise ValueError("선택 목록 필터가 올바르지 않습니다.")
        result = {}
        for kind, table, key, names in (("files", "project_files", "file_name", ("file_name",)),
                                        ("phases", "generation_phases", "phase_id", ("name",)),
                                        ("scenes", "scenes", "scene_id", ("name",))):
            records = self.rows(table, order=self.order(table, *names, key)) if self.has(table, key) else []
            if len(records) > LINK_LIMIT:
                self.notes.append(f"{kind}: 선택 목록은 처음 {LINK_LIMIT}개만 표시합니다.")
            result[kind] = [self.ref(row, key, *names) for row in records[:LINK_LIMIT]]
        tasks = []
        if self.has("generation_plans", "plan_id"):
            where, params = self.task_filter(file=file, phase=phase, scene=scene, status=status, execution=execution)
            search_where, search_params = self.search_clause("generation_plans", ("title", "goal", "scope"), search)
            tasks = self.rows("generation_plans", "(" + where + ") AND " + search_where, params + search_params,
                              self.order("generation_plans", "title", "plan_id"), fields=PLAN_OUTLINE_FIELDS)
        if len(tasks) > LINK_LIMIT:
            self.notes.append(f"tasks: 선택 목록은 처음 {LINK_LIMIT}개만 표시합니다. 필터나 검색으로 범위를 좁혀 주세요.")
        result["tasks"] = [self.ref(row, "plan_id", "title", "name") for row in tasks[:LINK_LIMIT]]
        result["statuses"] = self.plan_statuses()
        result["has_execution_history"] = self.has_execution_history()
        result["plan_outline"] = self.plan_outline(tasks[:LINK_LIMIT], include_context_files=bool(file))
        return {**result, "notes": list(dict.fromkeys(self.notes))}

    def plan_statuses(self):
        if not self.has("generation_plans", "status"):
            return []
        stored = self.db.execute(
            "SELECT DISTINCT status FROM generation_plans "
            "WHERE typeof(status)='text' AND length(status) BETWEEN 1 AND 200 ORDER BY status LIMIT ?",
            (RELATED_LIMIT,),
        )
        statuses = {status for status, in stored}
        if self.has("workflow_statuses", "status"):
            statuses.update(row["status"] for row in self.rows("workflow_statuses", limit=RELATED_LIMIT)
                            if isinstance(row["status"], str) and 0 < len(row["status"]) <= 200)
        return sorted(statuses)

    def has_execution_history(self):
        return (self.has("generation_plans", "plan_id", "loop_no")
                and self.has("generation_plan_loops", "plan_id", "loop_no")
                and self.has("generation_loop_steps", "plan_id", "loop_no", "status",
                             "input_refs_json", "output_refs_json", "takeaways", "design_rationale"))

    def unstarted_filter(self):
        if not self.has_execution_history():
            return "0"
        # Legacy Step work can be imported into Loop 0. Empty JSON arrays provide no evidence.
        references = ("CASE WHEN json_valid({field}) THEN json_type({field})!='array' "
                      "OR json_array_length({field})>0 ELSE trim(coalesce({field},''))<>'' END")
        evidence = (
            "generation_plans.loop_no=0 "
            "AND NOT EXISTS (SELECT 1 FROM generation_plan_loops l "
            "WHERE l.plan_id=generation_plans.plan_id AND l.loop_no>0) "
            "AND NOT EXISTS (SELECT 1 FROM generation_loop_steps s "
            "WHERE s.plan_id=generation_plans.plan_id AND (s.loop_no>0 OR s.status IS NOT 'pending' "
            f"OR {references.format(field='s.input_refs_json')} OR {references.format(field='s.output_refs_json')} "
            "OR trim(coalesce(s.takeaways,''))<>'' OR trim(coalesce(s.design_rationale,''))<>''))"
        )
        if self.has("generation_plans", "artifact_refs_json"):
            evidence += f" AND NOT ({references.format(field='generation_plans.artifact_refs_json')})"
        return evidence

    def plan_outline(self, matches, *, include_context_files=False):
        if not matches:
            return {"items": [], "truncated": False}
        if self.outline_catalogue is None:
            self.outline_catalogue = self.rows(
                "generation_plans", order=self.order("generation_plans", "title", "plan_id"),
                fields=PLAN_OUTLINE_FIELDS,
            )
        matched_ids = {row["plan_id"] for row in matches}
        catalogue = {row["plan_id"]: row for row in (*self.outline_catalogue[:LINK_LIMIT], *matches)}
        parents = {key: set() for key in catalogue}
        for key, row in catalogue.items():
            parents[key].update(value for value in json_list(row.get("parent_plan_json"))
                                if isinstance(value, str) and 0 < len(value) <= 200)
            for child in json_list(row.get("child_plan_json")):
                if isinstance(child, str) and child in parents:
                    parents[child].add(key)

        included = set(matched_ids)
        pending = sorted(matched_ids, reverse=True)
        truncated = len(self.outline_catalogue) > LINK_LIMIT
        while pending:
            for parent in sorted(parents[pending.pop()]):
                if parent in catalogue and parent not in included:
                    if len(included) >= LINK_LIMIT:
                        truncated = True
                        continue
                    included.add(parent)
                    pending.append(parent)
        items = []
        for key in sorted(included, key=lambda key: (label(catalogue[key], "title", "name"), key)):
            row = catalogue[key]
            previous = row.get("previous_id")
            previous_ref = None
            if isinstance(previous, str) and 0 < len(previous) <= 200:
                previous_ref = {"id": previous, "name": label(catalogue[previous], "title", "name") if previous in catalogue else None}
            item = {**self.ref(row, "plan_id", "title", "name"), "status": row.get("status"),
                    "matches": key in matched_ids, "parents": sorted(parents[key]), "previous": previous_ref}
            if not item["matches"] and include_context_files:
                item["file_names"] = self.task_context(row)["file_names"]
            items.append(item)
        return {"items": items, "truncated": truncated}

    def task_filter(self, *, file="", phase="", scene="", status="", execution=""):
        clauses, params = [], []
        plan_id = '"generation_plans"."plan_id"'
        if status:
            has_status = self.has("generation_plans", "status")
            clauses.append("status COLLATE BINARY=?" if has_status else "0")
            if has_status:
                params.append(status)
        if execution:
            if execution != "unstarted":
                raise ValueError("실행 이력 필터가 올바르지 않습니다.")
            clauses.append(self.unstarted_filter())
        if phase:
            clauses.append('phase_id=?' if self.has("generation_plans", "phase_id") else "0")
            if self.has("generation_plans", "phase_id"):
                params.append(phase)
        if scene:
            if "generation_plan_scenes" in self.columns:
                valid = self.has("generation_plan_scenes", "plan_id", "scene_id")
                clauses.append(f'EXISTS (SELECT 1 FROM generation_plan_scenes r WHERE r.plan_id={plan_id} AND r.scene_id=?)' if valid else "0")
                if valid:
                    params.append(scene)
            elif self.has("generation_plans", "scene_id"):
                clauses.append('scene_id=?')
                params.append(scene)
            else:
                clauses.append("0")
        if file:
            matches, values = [], []
            if self.has("generation_plans", "phase_id"):
                if "generation_phase_files" in self.columns:
                    if self.has("generation_phase_files", "phase_id", "file_name"):
                        matches.append('EXISTS (SELECT 1 FROM generation_phase_files pf WHERE pf.phase_id=generation_plans.phase_id AND pf.file_name=?)')
                        values.append(file)
                elif self.has("generation_phases", "phase_id", "file_name"):
                    matches.append('EXISTS (SELECT 1 FROM generation_phases p WHERE p.phase_id=generation_plans.phase_id AND p.file_name=?)')
                    values.append(file)
            if self.has("scenes", "scene_id", "file_name"):
                if "generation_plan_scenes" in self.columns:
                    if self.has("generation_plan_scenes", "plan_id", "scene_id"):
                        matches.append(f'EXISTS (SELECT 1 FROM generation_plan_scenes r JOIN scenes s ON s.scene_id=r.scene_id WHERE r.plan_id={plan_id} AND s.file_name=?)')
                        values.append(file)
                elif self.has("generation_plans", "scene_id"):
                    matches.append('EXISTS (SELECT 1 FROM scenes s WHERE s.scene_id=generation_plans.scene_id AND s.file_name=?)')
                    values.append(file)
            if self.holon_table and self.has(self.holon_table, "file_name") and self.has("generation_plan_ontological", "plan_id", "ontological_id"):
                matches.append(f'EXISTS (SELECT 1 FROM generation_plan_ontological r JOIN {identifier(self.holon_table)} h ON h.{identifier(self.holon_key)}=r.ontological_id WHERE r.plan_id={plan_id} AND h.file_name=?)')
                values.append(file)
            clauses.append("(" + " OR ".join(matches) + ")" if matches else "0")
            params.extend(values)
        return " AND ".join(clauses) or "1", tuple(params)

    def files(self, records):
        result = []
        for row in records:
            name = row['file_name']
            scenes = self.rows('scenes', 'file_name=?', (name,), self.order('scenes', 'name', 'scene_id'), RELATED_LIMIT + 1) if self.has('scenes', 'scene_id', 'name', 'file_name') else []
            holons = self.rows(self.holon_table, 'file_name=?', (name,), self.order(self.holon_table, 'name', self.holon_key), RELATED_LIMIT + 1) if self.holon_table and self.has(self.holon_table, 'file_name') else []
            phases = []
            if self.has('generation_phases', 'phase_id', 'name'):
                if 'generation_phase_files' in self.columns:
                    if self.has('generation_phase_files', 'phase_id', 'file_name'):
                        phases = self.rows('generation_phases', 'phase_id IN (SELECT phase_id FROM generation_phase_files WHERE file_name=?)', (name,), self.order('generation_phases', 'name', 'phase_id'), RELATED_LIMIT + 1)
                elif self.has('generation_phases', 'file_name'):
                    phases = self.rows('generation_phases', 'file_name=?', (name,), limit=RELATED_LIMIT + 1)
            tasks = []
            if self.has('generation_plans', 'plan_id'):
                where, params = self.task_filter(file=name)
                tasks = self.rows('generation_plans', where, params, self.order('generation_plans', 'title', 'plan_id'),
                                  RELATED_LIMIT + 1, fields=PLAN_OUTLINE_FIELDS)
            tasks = self.limited(tasks, '파일 Task')
            result.append({'id': name, 'name': name, 'file_name': name, 'description': row.get('description'), 'registered': row.get('registered'),
                           'scenes': [self.ref(item, 'scene_id', 'name') for item in self.limited(scenes, '파일 Scene')],
                           'holons': [self.ref(item, self.holon_key, 'name') for item in self.limited(holons, '파일 Holon')],
                           'phases': [self.ref(item, 'phase_id', 'name') for item in self.limited(phases, '파일 Phase')],
                           'tasks': [self.ref(item, 'plan_id', 'title', 'name') for item in tasks],
                           'plan_outline': self.plan_outline(tasks, include_context_files=True)})
        return result

    def limited(self, records, description):
        if len(records) > RELATED_LIMIT:
            self.notes.append(f"{description}: 처음 {RELATED_LIMIT}개만 표시합니다. 검색 또는 관련 조회로 범위를 좁혀 주세요.")
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

    def holon_link_sources(self):
        canonical = [(table, "ontological_id") for table in ("ontological_scene_context", "scene_ontological")
                     if table in self.columns]
        if canonical:
            if any(not self.has(table, "scene_id", key) for table, key in canonical):
                self.notes.append("현재 Holon 관계 저장 구조가 불완전합니다. 과거 관계로 대체하지 않습니다.")
            return canonical
        return [(table, "component_id") for table in ("_scene_component_refs", "scene_components")
                if self.has(table, "scene_id", "component_id")]

    def holon_scene_filter(self, scene):
        clauses, params = [], []
        sources = self.holon_link_sources()
        for table, key in sources:
            if self.has(table, "scene_id", key):
                clauses.append(f'EXISTS (SELECT 1 FROM {identifier(table)} r WHERE r.{identifier(key)}='
                               f'{identifier(self.holon_table)}.{identifier(self.holon_key)} AND r.scene_id=?)')
                params.append(scene)
        if not sources and self.has(self.holon_table, "scene_ids_json"):
            # Only a stored array of string IDs is a supported legacy relation.
            source = f'{identifier(self.holon_table)}.scene_ids_json'
            safe_json = f"CASE WHEN json_valid({source}) THEN {source} ELSE '[]' END"
            clauses.append(f"(json_type({safe_json})='array' AND EXISTS (SELECT 1 FROM json_each({safe_json}) r "
                           "WHERE r.type='text' AND r.value=?))")
            params.append(scene)
        if not clauses:
            self.notes.append("이 DB에는 Scene 필터에 필요한 Holon 관계 정보가 없습니다.")
        return " OR ".join(clauses) or "0", tuple(params)

    def holon_links(self, scene_ids):
        links = set()
        for table, key in self.holon_link_sources():
            links.update(self.links(table, "scene_id", key, scene_ids))
        return links

    def task_links(self, scene_ids):
        table = "generation_plan_scenes" if "generation_plan_scenes" in self.columns else "generation_plans"
        if table == "generation_plan_scenes" and not self.has(table, "scene_id", "plan_id"):
            self.notes.append("현재 Task 관계 저장 구조가 불완전합니다. 과거 관계로 대체하지 않습니다.")
        return set(self.links(table, "scene_id", "plan_id", scene_ids))

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
            result.append({"id": row["scene_id"], "name": label(row, "name"), "file_name": row.get("file_name"),
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
            sources = self.holon_link_sources()
            for table, column in sources:
                scene_ids.update(right for _, right in self.links(table, column, "scene_id", [key]))
            if not sources:
                scene_ids.update(item for item in json_list(row.get("scene_ids_json")) if isinstance(item, str))
            scenes = self.indexed("scenes", "scene_id", scene_ids) if self.has("scenes", "scene_id", "name") else {}
            parent_key = row.get("parent_ontological_id", row.get("parent_component_id"))
            parent = self.indexed(self.holon_table, self.holon_key, [parent_key]) if parent_key else {}
            result.append({"id": key, "name": label(row, "name"), "file_name": row.get("file_name"),
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
            result.append({"id": row["phase_id"], "name": label(row, "name"), "file_names": self.phase_files(row),
                           "tasks": self.limited(tasks, "Phase 소속 Task")})
        return result

    def step_records(self, plan, key=None):
        if not self.has("generation_plan_steps", "plan_id", "step_id"):
            return []
        where, params = "plan_id=?", (plan["plan_id"],)
        if key is not None:
            where += " AND step_id=?"
            params += (key,)
        order = ("position," if self.has("generation_plan_steps", "position") else "") + "step_id"
        steps = self.rows("generation_plan_steps", where, params, order, 1 if key is not None else RELATED_LIMIT + 1)
        if steps and self.has("generation_plans", "loop_no"):
            ids = [step["step_id"] for step in steps]
            states = []
            if self.has("generation_loop_steps", "plan_id", "loop_no", "step_id"):
                states = self.rows("generation_loop_steps",
                                   "plan_id=? AND loop_no=? AND step_id IN (" + ",".join("?" for _ in ids) + ")",
                                   (plan["plan_id"], plan["loop_no"], *ids), limit=len(ids))
            by_id = {state["step_id"]: state for state in states}
            for step in steps:
                state = by_id.get(step["step_id"], {})
                step.update(loop_no=plan["loop_no"])
                for field in ("status", "input_refs_json", "output_refs_json", "takeaways", "design_rationale"):
                    step[field] = state.get(field)
        return steps

    def step_groups(self, records):
        plans = self.indexed("generation_plans", "plan_id", [row["plan_id"] for row in records])
        result = []
        for record in records:
            plan = plans.get(record["plan_id"])
            if not plan:
                continue
            # This selected definition can be beyond the first Task expansion page.
            step = self.step_records(plan, record["step_id"])[0]
            result.append({"id": step["step_id"], "parent": plan["plan_id"],
                           "task": self.ref(plan, "plan_id", "title", "name"),
                           **self.task_context(plan),
                           "name": label(step, "name", "step_id"),
                           "step_type": step.get("step_type"), "kind": step.get("kind"), "position": step.get("position"),
                           "loop_no": plan.get("loop_no"),
                           **{field: step.get(field) for field in ("status", "takeaways", "design_rationale", "input_refs_json", "output_refs_json")}})
        return result

    def phase_files(self, phase):
        if not phase:
            return []
        if "generation_phase_files" in self.columns:
            if not self.has("generation_phase_files", "phase_id", "file_name"):
                return []
            rows = self.rows("generation_phase_files", "phase_id=?", (phase["phase_id"],),
                             self.order("generation_phase_files", "position", "file_name"), RELATED_LIMIT + 1)
            return [row["file_name"] for row in self.limited(rows, "Phase 파일") if isinstance(row.get("file_name"), str) and row["file_name"]]
        return [phase["file_name"]] if phase.get("file_name") else []

    def task_context(self, record):
        phase_id = record.get("phase_id")
        phases = self.indexed("generation_phases", "phase_id", [phase_id]) if phase_id and self.has("generation_phases", "phase_id") else {}
        phase = phases.get(phase_id)
        if "generation_plan_scenes" in self.columns:
            ids = [right for _, right in self.links("generation_plan_scenes", "plan_id", "scene_id", [record["plan_id"]])]
        else:
            ids = [record["scene_id"]] if record.get("scene_id") else []
        scenes = self.indexed("scenes", "scene_id", ids) if self.has("scenes", "scene_id") else {}
        files = set(self.phase_files(phase))
        files.update(row["file_name"] for row in scenes.values() if isinstance(row.get("file_name"), str) and row["file_name"])
        if self.holon_table and self.has(self.holon_table, "file_name"):
            ids = [right for _, right in self.links("generation_plan_ontological", "plan_id", "ontological_id", [record["plan_id"]])]
            holons = self.indexed(self.holon_table, self.holon_key, ids)
            files.update(row["file_name"] for row in holons.values() if isinstance(row.get("file_name"), str) and row["file_name"])
        return {"phase": self.ref(phase, "phase_id", "name") if phase else None,
                "scenes": [self.ref(row, "scene_id", "name") for row in scenes.values()],
                "file_names": sorted(files)}

    def task_relations(self, record, catalogue):
        wanted = []
        if isinstance(record.get("previous_id"), str) and record["previous_id"]:
            wanted.append(("previous", record["previous_id"]))
        for kind, field in (("related", "depends_on_json"), ("parent", "parent_plan_json"), ("child", "child_plan_json")):
            wanted.extend((kind, value) for value in json_list(record.get(field))
                          if isinstance(value, str) and value and len(value) <= 200)
        for other in catalogue:
            if other.get("previous_id") == record["plan_id"]:
                wanted.append(("next", other["plan_id"]))
            for kind, field in (("related", "depends_on_json"), ("child", "parent_plan_json"), ("parent", "child_plan_json")):
                if record["plan_id"] in json_list(other.get(field)):
                    wanted.append((kind, other["plan_id"]))
        wanted = sorted(set(wanted))
        if len(wanted) > RELATED_LIMIT:
            self.notes.append(f"인접 Task 관계는 처음 {RELATED_LIMIT}개만 표시합니다.")
        wanted = wanted[:RELATED_LIMIT]
        records = self.indexed("generation_plans", "plan_id", [key for _, key in wanted])
        return [{"type": kind, "id": key, "name": label(records[key], "title", "name") if key in records else "미등록 Task",
                 "missing": key not in records} for kind, key in wanted]

    def tasks(self, records, loop_no=None):
        result = []
        catalogue = self.rows("generation_plans", order=self.order("generation_plans", "plan_id")) if records else []
        if len(catalogue) > LINK_LIMIT:
            self.notes.append(f"다른 Plan에 기록된 순서·관련·상하위 관계는 처음 {LINK_LIMIT}개 기록에서 찾습니다.")
        for row in records:
            numbers = loop_numbers(self, row, LINK_LIMIT)
            selected = loop_no if loop_no is not None else row.get("loop_no")
            if loop_no is None and numbers and selected not in numbers:
                selected = numbers[-1]
            if loop_no is not None and loop_no not in numbers:
                raise ValueError("이 Task에 선택한 회차 기록이 없습니다.")
            navigation = {"loop_numbers": numbers, "current_loop": row.get("loop_no"),
                          **self.task_context(row), "relations": self.task_relations(row, catalogue[:LINK_LIMIT])}
            if selected != row.get("loop_no"):
                plan, historical_steps, complete = read_history(self, row["plan_id"], selected, RELATED_LIMIT)
                result.append({**navigation, **{k: plan.get(k) for k in ("goal", "scope", "status", "revision", "feedback",
                               "artifact_dir", "loop_artifact_dir", "artifact_refs", "loop_created_at")},
                               "id": row["plan_id"], "name": label(plan, "title", "name"), "loop_no": selected,
                               "history": "snapshot" if complete else "partial",
                               "steps": [{**s, "id": s["step_id"], "name": label(s, "name", "step_id"),
                                          "input_refs_json": s.get("input_refs", s.get("input_refs_json")),
                                          "output_refs_json": s.get("output_refs", s.get("output_refs_json"))}
                                         for s in historical_steps]})
                continue
            steps = self.step_records(row)
            loop = loop_row(self, row["plan_id"], selected)
            result.append({"id": row["plan_id"], "name": label(row, "title", "name"), "revision": row.get("revision"),
                           "goal": row.get("goal"), "scope": row.get("scope"), "status": row.get("status"), "loop_no": row.get("loop_no"),
                           **navigation, "feedback": loop.get("feedback"), "loop_created_at": loop.get("created_at"),
                           "artifact_dir": row.get("artifact_dir"), "artifact_refs": row.get("artifact_refs_json"),
                           "loop_artifact_dir": stored_loop_directory(self, row["plan_id"], selected),
                           "steps": [{"id": step["step_id"], "name": label(step, "name", "step_id"),
                                      "status": step.get("status"), "goal": step.get(self.step_goal), "position": step.get("position"),
                                      "step_type": step.get("step_type"), "kind": step.get("kind"), "loop_no": row.get("loop_no"),
                                      **{field: step.get(field) for field in ("takeaways", "design_rationale", "input_refs_json", "output_refs_json")}}
                                     for step in self.limited(steps, "Task 소속 Step")]})
        return result

    def detail(self, kind, key, parent="", loop_no=None):
        if not key or len(key) > 200 or len(parent) > 200:
            raise ValueError("조회할 항목을 선택하세요.")
        if loop_no is not None:
            if kind not in ("tasks", "steps") or type(loop_no) is not int or not 0 <= loop_no < 2**53:
                raise ValueError("올바른 Task 또는 Step 회차를 선택하세요.")
            pid = key if kind == "tasks" else parent
            plans = self.rows("generation_plans", "plan_id=?", (pid,), limit=1) if self.has("generation_plans", "plan_id") else []
            if not plans or loop_no not in loop_numbers(self, plans[0], LINK_LIMIT):
                raise ValueError("이 Task에 선택한 회차 기록이 없습니다.")
            if loop_no != plans[0].get("loop_no"):
                fields, steps, complete = read_history(self, pid, loop_no, RELATED_LIMIT, key if kind == "steps" else None)
                title = label(fields, "title", "name")
                if kind == "steps":
                    if not steps:
                        raise ValueError("선택한 회차에 이 Step의 기록이 없습니다.")
                    fields = {**steps[0], "plan_id": pid, "loop_no": loop_no, "revision": fields["revision"]}
                    title = label(fields, "name", "step_id")
                return {"title": title, "fields": fields, "loop_no": loop_no,
                        "history": "snapshot" if complete else "partial", "notes": self.notes}
        if kind == "steps":
            if not self.has("generation_plan_steps", "step_id", "plan_id") or not self.has("generation_plans", "plan_id") or not parent:
                raise ValueError("Step을 조회하려면 소속 Task가 필요합니다.")
            plan = self.rows("generation_plans", "plan_id=?", (parent,), limit=1)
            records = self.step_records(plan[0], key) if plan else []
            if not records or not plan:
                raise ValueError("선택한 Step 또는 Task가 없습니다. 새로고침해 주세요.")
            return {"title": label(records[0], "name", "step_id"),
                    "task": {**self.ref(plan[0], "plan_id", "title", "name"), "revision": plan[0].get("revision")},
                    "context": self.task_context(plan[0]), "fields": records[0]}
        mapping = {"files": ("project_files", "file_name", "file_name"), "scenes": ("scenes", "scene_id", "name"), "holons": (self.holon_table, self.holon_key, "name"),
                   "phases": ("generation_phases", "phase_id", "name"), "tasks": ("generation_plans", "plan_id", "title")}
        if kind not in mapping or not self.capabilities()[kind]:
            raise ValueError("지원하지 않는 조회입니다.")
        table, column, name = mapping[kind]
        records = self.rows(table, identifier(column) + "=?", (key,), limit=1)
        if not records:
            raise ValueError("선택한 항목이 없습니다. 새로고침해 주세요.")
        if kind == "tasks" and loop_no is not None:
            loop = loop_row(self, key, loop_no)
            records[0].update(feedback=loop.get("feedback"), loop_created_at=loop.get("created_at"),
                              loop_artifact_dir=stored_loop_directory(self, key, loop_no))
        return {"title": label(records[0], name), "fields": records[0]}
