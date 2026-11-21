"""Read persisted Loop evidence using the Dashboard's existing read transaction."""
import json

from .database import CELL_LIMIT, MAX_COLUMNS, Database


def loop_numbers(view, plan, limit):
    sources = []
    for table in ("generation_plan_loops", "generation_loop_steps", "generation_plan_revisions"):
        if view.has(table, "plan_id", "loop_no"):
            minimum = 1 if table == "generation_plan_loops" else 0
            sources.append(f"SELECT loop_no FROM {table} WHERE plan_id=? AND typeof(loop_no)='integer' "
                           f"AND loop_no BETWEEN {minimum} AND 9007199254740991")
    current = plan.get("loop_no")
    numbers = set()
    if sources:
        query = " UNION ".join(sources) + " ORDER BY loop_no DESC LIMIT ?"
        rows = view.db.execute(query, [plan["plan_id"]] * len(sources) + [limit + 1]).fetchall()
        if len(rows) > limit:
            view.notes.append(f"회차 목록은 최근 {limit}개까지 표시합니다.")
        numbers.update(row[0] for row in rows[:limit])
    if type(current) is int and current > 0:
        numbers.add(current)
    return sorted(numbers)


def loop_row(view, plan_id, number):
    if view.has("generation_plan_loops", "plan_id", "loop_no"):
        rows = view.rows("generation_plan_loops", "plan_id=? AND loop_no=?", (plan_id, number), limit=1)
        if rows:
            return rows[0]
    return {}


def stored_loop_directory(view, plan_id, number):
    if not view.has("generation_plan_revisions", "plan_id", "loop_no", "revision", "snapshot_json"):
        return None
    row = view.db.execute("""SELECT CASE WHEN json_valid(snapshot_json) THEN
                          CASE WHEN json_extract(snapshot_json,'$.plan_id')=?
                               AND json_type(snapshot_json,'$.loop_artifact_dir')='text'
                               THEN substr(json_extract(snapshot_json,'$.loop_artifact_dir'),1,?) END END,
                          CASE WHEN json_valid(snapshot_json) THEN length(json_extract(snapshot_json,'$.loop_artifact_dir')) END
                          FROM generation_plan_revisions WHERE plan_id=? AND loop_no=?
                          ORDER BY revision DESC LIMIT 1""", (plan_id, CELL_LIMIT, plan_id, number)).fetchone()
    return Database._cells(row)[0] if row else None


# Project a field only after SQLite has found it in the complete document. A long
# rationale must not truncate the JSON before a subsequent output reference.
JSON_FIELD = """substr(f.key,1,200), f.type,
                CASE WHEN f.type IN ('text','array','object') THEN substr(f.value,1,?) ELSE f.value END,
                CASE WHEN f.type IN ('text','array','object') THEN length(f.value) END"""
REVISION = """SELECT snapshot_json FROM generation_plan_revisions
              WHERE plan_id=? AND loop_no=? AND revision=?"""


def snapshot_field(kind, raw, length):
    if kind in ("true", "false"):
        return kind == "true"
    value = Database._cells((raw, length))[0]
    if isinstance(value, str) and kind in ("array", "object"):
        return json.loads(value)
    return value


def snapshot_fields(view, plan_id, number, revision, limit, step_id):
    args = (plan_id, number, revision)
    # Legacy snapshots can omit the inner loop/revision. The row key still identifies them.
    valid = view.db.execute(f"""WITH src(doc) AS ({REVISION})
        SELECT CASE WHEN json_valid(doc) THEN json_extract(doc,'$.plan_id')=?
               AND coalesce(json_extract(doc,'$.loop_no'),?)=?
               AND coalesce(json_extract(doc,'$.revision'),?)=? END FROM src""",
        (*args, plan_id, number, number, revision, revision)).fetchone()
    if not valid or not valid[0]:
        return {}, [], False
    fields = view.db.execute(f"""WITH src(doc) AS ({REVISION})
        SELECT {JSON_FIELD} FROM src, json_each(doc) f
        WHERE f.key NOT IN ('steps','read_only') LIMIT ?""", (*args, CELL_LIMIT, MAX_COLUMNS))
    plan = {key: snapshot_field(kind, value, length) for key, kind, value, length in fields}

    # Filter by the source Step ID before the display limit so its popup can be read independently.
    selected = f"""WITH src(doc) AS ({REVISION}), chosen AS (
        SELECT s.key AS pos, s.value AS step FROM src, json_each(doc,'$.steps') s
        WHERE s.type='object' AND CASE WHEN s.type='object' THEN json_type(s.value,'$.step_id')='text'
              AND (? IS NULL OR json_extract(s.value,'$.step_id')=?) END
        ORDER BY s.key LIMIT ?)"""
    values = view.db.execute(selected + f"""
        SELECT chosen.pos, {JSON_FIELD} FROM chosen, json_each(chosen.step) f ORDER BY chosen.pos, f.id""",
        (*args, step_id, step_id, limit + 1, CELL_LIMIT))
    steps = {}
    for pos, key, kind, value, length in values:
        if pos not in steps and len(steps) == limit:
            view.notes.append(f"회차 Step은 처음 {limit}개만 표시합니다.")
            break
        record = steps.setdefault(pos, {})
        if len(record) < MAX_COLUMNS:
            record[key] = snapshot_field(kind, value, length)
    shape = view.db.execute(f"""WITH src(doc) AS ({REVISION})
        SELECT json_type(doc,'$.steps')='array' AND NOT EXISTS (
          SELECT 1 FROM json_each(doc,'$.steps') s WHERE CASE WHEN s.type='object'
          THEN json_type(s.value,'$.step_id') IS NOT 'text' ELSE 1 END) FROM src""",
        args).fetchone()
    recorded = [s for s in steps.values() if isinstance(s.get("step_id"), str)]
    complete = "goal" in plan and "status" in plan and bool(shape[0]) and len(recorded) == len(steps)
    return plan, recorded, complete


def read_history(view, plan_id, number, step_limit, step_id=None):
    """Read the last revision of this Loop or the surviving Loop-local rows."""
    plan = {}
    steps = []
    revision = None
    complete = False
    if view.has("generation_plan_revisions", "plan_id", "loop_no", "revision", "snapshot_json"):
        row = view.db.execute("""SELECT revision FROM generation_plan_revisions
                                 WHERE plan_id=? AND loop_no=? ORDER BY revision DESC LIMIT 1""",
                              (plan_id, number)).fetchone()
        if row:
            revision = row[0]
            plan, steps, complete = snapshot_fields(view, plan_id, number, revision, step_limit, step_id)
            if not complete:
                view.notes.append("해당 revision의 전체 기록을 읽을 수 없어 남아 있는 회차별 자료를 표시합니다.")

    if not complete and view.has("generation_loop_steps", "plan_id", "loop_no", "step_id"):
        where, params = "plan_id=? AND loop_no=?", (plan_id, number)
        if step_id is not None:
            where += " AND step_id=?"
            params += (step_id,)
        rows = view.rows("generation_loop_steps", where, params, "step_id", step_limit + 1)
        recorded = {s["step_id"]: s for s in steps}
        for s in rows[:step_limit]:
            recorded[s["step_id"]] = {**s, **recorded.get(s["step_id"], {})}
        if len(recorded) > step_limit or len(rows) > step_limit:
            view.notes.append(f"회차 Step은 처음 {step_limit}개만 표시합니다.")
        steps = list(recorded.values())[:step_limit]
    loop = loop_row(view, plan_id, number)
    if "feedback" in loop:
        plan.setdefault("feedback", loop["feedback"])
    if "created_at" in loop:
        plan["loop_created_at"] = loop["created_at"]
    plan.update(plan_id=plan_id, loop_no=number, revision=revision)
    return plan, steps, complete
