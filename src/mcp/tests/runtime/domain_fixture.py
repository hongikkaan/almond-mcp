"""Disposable producer fixture shared by domain API and headless UI checks."""
from contextlib import closing
import json
import sqlite3


def create_domain_database(path):
    from almond_mcp.retrieval_store import AlmondStore
    AlmondStore(path)  # Producer only; the dashboard never imports or constructs it.
    now = "2026-11-04T12:00+09:00"
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO project_files(file_name,registered) VALUES ('example.3dm',1)")
        db.execute("INSERT INTO _project_file_locations VALUES ('example.3dm','C:/Projects/example.3dm')")
        db.executemany("INSERT INTO scenes(scene_id,name,units,created_at,updated_at,file_name) VALUES (?,?,'mm',?,?,'example.3dm')",
                       [(key, name, now, now) for key, name in (("scene_a", "진입 장면"), ("scene_b", "휴식 장면"))])
        db.executemany("""INSERT INTO ontological_holons(ontological_id,file_name,rhino_group_id,name,
            created_at,updated_at,object_count,effective_object_count,parent_ontological_id)
            VALUES (?,'example.3dm',?,?,?,?,2,2,?)""", [
                ("holon_a", "group_a", "출입부", now, now, None),
                ("holon_b", "group_b", "출입부", now, now, None),
                ("holon_child", "group_child", "문틀", now, now, "holon_a"),
                ("holon_c", "group_c", "쉼터", now, now, None)])
        db.executemany("INSERT INTO ontological_scene_context VALUES (?,?)", [
            ("holon_a", "scene_a"), ("holon_b", "scene_a"), ("holon_child", "scene_a"), ("holon_c", "scene_b")])
        db.execute("INSERT INTO scene_ontological VALUES ('scene_a','holon_a')")
        db.executemany("INSERT INTO generation_phases(phase_id,name,description,created_at,updated_at) VALUES (?,?,?,?,?)", [
            (key, name, "화면 검수용 가상 Phase", now, now) for key, name in (
                ("phase_a", "설계"), ("phase_b", "설계"), ("phase_empty", "자료 정리"))])
        db.executemany("""INSERT INTO generation_plans(plan_id,title,scene_id,scope,goal,status,revision,phase_id,created_at,updated_at)
                           VALUES (?,?,?,'house',?,?,?,?,?,?)""", [
            ("plan_a", "공간 설계", "scene_a", "진입 공간의 동선과 경계를 구성한다.", "running", 7, "phase_a", now, now),
            ("plan_b", "공간 설계", "scene_a", "다른 Task의 독립적인 목표", "pending", 2, "phase_a", now, now),
            ("plan_c", "구조 검토", "scene_b", "쉼터 구조를 검토한다.", "completed", 3, "phase_b", now, now),
            ("plan_unassigned", "독립 작업", None, "아직 Phase를 정하지 않은 작업", "pending", 0, None, now, now),
            ("plan_empty", "단계 없는 작업", None, "Step이 없는 Task", "paused", 0, "phase_a", now, now)])
        db.executemany("INSERT INTO generation_plan_scenes VALUES (?,?,?)", [
            ("plan_a", "scene_a", 0), ("plan_a", "scene_b", 1), ("plan_b", "scene_a", 0), ("plan_c", "scene_b", 0)])
        steps = [
            ("plan_a", "a_last", 2, "pending", '["검토할 조건"]', '[]'),
            ("plan_a", "z_first", 0, "completed", '["기존 도면"]', '["장면 해석 결과"]'),
            ("plan_a", "m_middle", 1, "running", '["장면 해석 결과"]', '["동선 검토 중"]'),
            ("plan_b", "b_first", 0, "blocked", '["다른 Task의 입력"]', '[]'),
            ("plan_c", "review_structure", 0, "completed", '[]', '["검토 완료"]')]
        db.executemany("INSERT INTO generation_plan_steps(plan_id,step_id,position,kind,depends_on_json) VALUES (?,?,?,'reason','[]')",
                       [(plan, step, position) for plan, step, position, *_ in steps])
        db.executemany("INSERT INTO generation_loop_steps(plan_id,loop_no,step_id,status,input_refs_json,output_refs_json) VALUES (?,0,?,?,?,?)",
                       [(plan, step, status, inputs, outputs) for plan, step, _, status, inputs, outputs in steps])
        db.commit()
        db.execute("PRAGMA journal_mode=DELETE")
    return path


def add_plan_outline_fixture(path):
    """Add two-file Plan branches using the current producer schema."""
    now = "2026-11-20T12:00+09:00"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("INSERT INTO project_files(file_name,registered) VALUES ('other.3dm',1)")
        db.executemany("INSERT INTO generation_phase_files VALUES (?,?,0)", [
            ("phase_a", "example.3dm"), ("phase_b", "other.3dm"),
        ])
        db.executemany(
            """INSERT INTO generation_plans(plan_id,title,scope,goal,status,phase_id,loop_no,previous_id,
                   parent_plan_json,child_plan_json,created_at,updated_at)
               VALUES (?,?,'house','Outline fixture',?,?,?,?,?,?,?,?)""",
            [(key, title, status, phase, loop, previous, parents, children, now, now)
             for key, title, status, phase, loop, previous, parents, children in [
                ("outline_root", "부모 Plan", "completed", "phase_a", 2, None, "[]", '["outline_child_b"]'),
                ("outline_next", "후속 Plan", "running", "phase_a", 1, "outline_root", "[]", "[]"),
                ("outline_branch", "검토 분기", "paused", "phase_a", 1, "outline_root", "[]", "[]"),
                ("outline_child_a", "첫 자식", "running", "phase_b", 1, None, '["outline_root"]', "[]"),
                ("outline_child_b", "둘째 자식", "paused", "phase_b", 1, "outline_child_a", "[]", "[]"),
                ("outline_leaf", "공유 손자", "pending", "phase_b", 0, None, '["outline_child_a","outline_child_b"]', "[]"),
                ("outline_loose", "독립 검토", "blocked", "phase_b", 0, None, "[]", "[]"),
                ("outline_pending", "시작한 대기 작업", "pending", "phase_b", 1, None, "[]", "[]"),
                ("outline_legacy", "이관된 대기 작업", "pending", "phase_b", 0, None, "[]", "[]"),
                ("outline_cycle_a", "순환 참조 A", "failed", None, 0, "outline_cycle_b",
                 '["outline_cycle_b","outline_missing_parent"]', "[]"),
                ("outline_cycle_b", "순환 참조 B", "failed", None, 0, "outline_cycle_a",
                 '["outline_cycle_a"]', "[]"),
             ]],
        )
        db.executemany("INSERT INTO generation_plan_loops(plan_id,loop_no,created_at) VALUES (?,?,?)", [
            (key, loop, now) for key, loop in [
                ("outline_root", 1), ("outline_root", 2), ("outline_next", 1), ("outline_branch", 1),
                ("outline_child_a", 1), ("outline_child_b", 1), ("outline_pending", 1),
            ]],
        )
        db.executemany("INSERT INTO generation_plan_steps(plan_id,step_id,position,kind,depends_on_json) "
                       "VALUES (?, ?, 0, 'reason', '[]')",
                       [("outline_leaf", "step_new"), ("outline_legacy", "step_imported")])
        db.executemany("INSERT INTO generation_loop_steps(plan_id,loop_no,step_id,status,output_refs_json) VALUES (?,0,?,?,?)",
                       [("outline_leaf", "step_new", "pending", "[ ]"),
                        ("outline_legacy", "step_imported", "completed", '["legacy/drawing.png"]')])
    return path


def add_loop_history_fixture(path):
    """Recorded Loops 0, 1, 3 and 4, with a deleted Step and a surviving feedback-only record."""
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE generation_plans SET loop_no=4, revision=1 WHERE plan_id='plan_a'")
        db.executemany("INSERT INTO generation_plan_loops VALUES ('plan_a', ?, ?, '2026-11-21')",
                       [(1, 'first feedback'), (3, 'feedback only'), (4, 'current feedback')])
        db.execute("""INSERT INTO generation_loop_steps(plan_id,loop_no,step_id,status,takeaways,output_refs_json)
                      VALUES ('plan_a',4,'z_first','running','current decision','["current/new.png"]')""")
        for revision in (1, 2):
            snapshot = {"plan_id": "plan_a", "loop_no": 1, "title": "Old title", "goal": "Original goal",
                        "status": "paused", "feedback": "first feedback", "revision": revision,
                        "loop_artifact_dir": ".almond/produced/example/01",
                        "steps": [{"step_id": "archived_step", "name": "Old Step", "status": "completed",
                                   "output_refs": ["previous/deleted.png"], "takeaways": f"decision {revision}",
                                   "design_rationale": "saved basis", "input_refs": ["drawing.3dm"]},
                                  {"step_id": "z_first", "name": "같은 Step의 이전 기록", "status": "completed",
                                   "design_rationale": "한글 설계 근거 " * 1300, "output_refs": ["old/first.png"]}]}
            db.execute("""INSERT INTO generation_plan_revisions
                       (plan_id,loop_no,revision,operation,created_at,snapshot_json) VALUES ('plan_a',1,?,'update_step','2026-11-21',?)""",
                       (revision, json.dumps(snapshot, ensure_ascii=False)))
    return path
