from contextlib import contextmanager
import json
from pathlib import Path
import sys
import threading

from almond_mcp.retrieval_store import AlmondStore
from dashboard.server import DashboardServer


def create_sample(path):
    """Record two design Loops through the producer used by Almond."""
    store = AlmondStore(path)
    for name in ("Lobby.3dm", "Courtyard.3dm"):
        store.upsert_project_file(name)
    lobby = store.create_scene("로비 입구", file_name="Lobby.3dm")
    garden = store.create_scene("안뜰", file_name="Courtyard.3dm")
    survey = store.create_phase("기본 설계", file_name=["Lobby.3dm", "Courtyard.3dm"])
    review = store.create_phase("설계 검토", file_name="Courtyard.3dm")
    plan = store.create_plan(
        goal="입구의 동선과 개구부를 검토한다.", title="입구 설계", scope="component",
        phase_id=survey["phase_id"], scene_ids=[lobby["scene_id"], garden["scene_id"]],
    )
    store.create_plan(goal="안뜰을 검토한다.", title="안뜰 검토", scope="component",
                      phase_id=review["phase_id"], scene_ids=[garden["scene_id"]])

    plan_id, step_id = plan["plan_id"], plan["steps"][0]["step_id"]
    store.execute_looping(plan_id, feedback="기존 입구 검토")
    store.update_plan_step(plan_id, step_id, takeaways="기존 입구 유지", output_refs=["drawings/old.pdf"])
    store.execute_looping(plan_id, feedback="새 입구 검토")
    store.update_plan_step(plan_id, step_id, takeaways="새 입구 확장", output_refs=["drawings/new.pdf"])
    return plan_id, step_id, survey["phase_id"], garden["scene_id"]


@contextmanager
def serve_database(path):
    with DashboardServer(path) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    database = Path(sys.argv[1])
    plan, step, phase, _ = create_sample(database)
    with serve_database(database) as server:
        print(json.dumps({"url": server.url, "plan": plan, "step": step, "phase": phase}), flush=True)
        sys.stdin.read()
