"""Disposable producer fixture shared by domain API and headless UI checks."""
import sqlite3


def create_domain_database(path):
    from almond_mcp.retrieval_store import AlmondStore
    AlmondStore(path)  # Producer only; the dashboard never imports or constructs it.
    now = "2026-11-04T12:00+09:00"
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO project_files(file_id,file_name) VALUES ('file_a','example.3dm')")
        db.execute("INSERT INTO _project_file_locations VALUES ('file_a','C:/Projects/example.3dm')")
        db.executemany("INSERT INTO scenes(scene_id,name,units,created_at,updated_at,project_file_id) VALUES (?,?,'mm',?,?,'file_a')",
                       [(key, name, now, now) for key, name in (("scene_a", "진입 장면"), ("scene_b", "휴식 장면"))])
        db.executemany("""INSERT INTO ontological_holons(ontological_id,project_file_id,rhino_group_id,name,
            created_at,updated_at,object_count,effective_object_count,parent_ontological_id)
            VALUES (?,'file_a',?,?,?,?,2,2,?)""", [
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
