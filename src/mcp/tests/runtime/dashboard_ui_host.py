"""Disposable browser fixture. Never opens a user's Rhino document or DB."""
from pathlib import Path
import json
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'runtime'))
from domain_fixture import add_loop_history_fixture, add_plan_outline_fixture, create_domain_database
from dashboard.server import DashboardServer


def seed_browsing(path):
    with sqlite3.connect(path) as db:
        db.execute("UPDATE generation_loop_steps SET takeaways='판단 기록',design_rationale='설계 근거' "
                   "WHERE plan_id='plan_a' AND step_id='z_first'")
        db.execute("UPDATE generation_plans SET previous_id='plan_b' WHERE plan_id='plan_a'")
        db.execute("UPDATE generation_plans SET title=? WHERE plan_id='plan_b'", ("Related Task " + "W" * 180,))
        db.execute("UPDATE generation_phases SET name=? WHERE phase_id='phase_a'", ("Phase_" + "W" * 220,))
        db.execute("UPDATE generation_phases SET name='다른 Phase' WHERE phase_id='phase_b'")
        for table in ("project_files", "_project_file_locations", "scenes", "ontological_holons"):
            db.execute(f'UPDATE "{table}" SET file_name=? WHERE file_name=?', ("F" * 180 + ".3dm", "example.3dm"))
        db.execute("INSERT INTO project_files(file_name,registered) VALUES ('other.3dm',1)")
        db.execute("UPDATE scenes SET file_name='other.3dm' WHERE scene_id='scene_b'")
        db.execute("UPDATE ontological_holons SET file_name='other.3dm' WHERE ontological_id='holon_c'")
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_a',?,0)", ("F" * 180 + ".3dm",))
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_b','other.3dm',0)")
        db.execute("UPDATE generation_loop_steps SET input_refs_json=? WHERE plan_id='plan_a' AND step_id='z_first'",
                   (json.dumps(["reference/" + "W" * 2000]),))
        db.execute("UPDATE generation_loop_steps SET output_refs_json=? WHERE plan_id='plan_a' AND step_id='z_first'",
                   (json.dumps([{"label": "검토 자료", "url": "https://example.com/record?id=3", "pages": [1, 2],
                                 "range_url": "https://example.com/report?range=[1,2]"}]),))
        db.executemany("INSERT INTO generation_plan_steps(plan_id,step_id,position,kind,depends_on_json) "
                       "VALUES ('plan_b',?,?,'reason','[]')",
                       [(f'bounded_{index}', index + 1) for index in range(201)])


with tempfile.TemporaryDirectory(prefix='dashboard-ui-') as directory:
    path = create_domain_database(Path(directory) / 'fixture.sqlite3')
    if '--plan-outline' in sys.argv[1:]:
        add_plan_outline_fixture(path)
    elif '--loop-history' in sys.argv[1:]:
        add_loop_history_fixture(path)
    else:
        seed_browsing(path)
    server = DashboardServer(path)
    print(server.url, flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
