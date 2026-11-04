"""Named domain projections use stored relationships, not inferred live geometry."""
import hashlib
import http.client
import json
import sqlite3
import threading
from urllib.parse import urlencode

import pytest

from dashboard.database import Database
from dashboard.domain_views import RELATED_LIMIT
from dashboard.server import DashboardServer
from domain_fixture import create_domain_database


@pytest.fixture
def project(tmp_path):
    return Database(create_domain_database(tmp_path / "project.sqlite3"))


def test_scene_names_links_and_multiple_scene_tasks_are_not_duplicated(project):
    caps = project.schema()["domain_views"]
    assert all(caps[key] for key in ("scenes", "holons", "phases", "tasks", "steps"))
    assert not caps["object_names"] and not caps["step_goals"]
    groups = {group["id"]: group for group in project.domain_page("scenes")["groups"]}
    assert groups["scene_a"]["name"] == "진입 장면"
    assert {ref["id"] for ref in groups["scene_a"]["holons"]} == {"holon_a", "holon_b", "holon_child"}
    assert len(groups["scene_a"]["holons"]) == 3  # Duplicate link tables do not duplicate a Holon.
    assert [ref["name"] for ref in groups["scene_a"]["holons"]].count("출입부") == 2  # Names are not identities.
    assert {ref["id"] for ref in groups["scene_a"]["tasks"]} == {"plan_a", "plan_b"}
    assert {ref["id"] for ref in groups["scene_b"]["tasks"]} == {"plan_a", "plan_c"}


def test_holon_focus_uses_id_and_preserves_scene_and_parent_links(project):
    page = project.domain_page("holons", focus="holon_child")
    assert len(page["groups"]) == 1
    record = page["groups"][0]
    assert record["name"] == "문틀" and record["parent"] == {"id": "holon_a", "name": "출입부"}
    assert record["scenes"] == [{"id": "scene_a", "name": "진입 장면"}]
    assert not record["objects"] and "이름이 저장되지" in page["notes"][0]
    assert project.domain_detail("holons", "holon_child")["fields"]["parent_ontological_id"] == "holon_a"


def test_phase_groups_do_not_merge_same_names_and_include_empty_and_unassigned(project):
    groups = {group["id"]: group for group in project.domain_page("phases")["groups"]}
    assert groups["phase_a"]["name"] == groups["phase_b"]["name"] == "설계"
    assert {task["plan_id"] for task in groups["phase_a"]["tasks"]} == {"plan_a", "plan_b", "plan_empty"}
    assert [task["plan_id"] for task in groups["phase_b"]["tasks"]] == ["plan_c"]
    assert not groups["phase_empty"]["tasks"]
    assert [task["plan_id"] for task in groups[None]["tasks"]] == ["plan_unassigned"]


def test_task_steps_are_ordered_and_do_not_inherit_an_unstored_goal(project):
    page = project.domain_page("tasks", focus="plan_a", limit=1)
    assert not page["has_more"] and len(page["groups"]) == 1
    task = page["groups"][0]
    assert task["name"] == "공간 설계" and task["revision"] == 7
    assert task["scope"] == "house" and task["goal"] == "진입 공간의 동선과 경계를 구성한다."
    assert [step["id"] for step in task["steps"]] == ["z_first", "m_middle", "a_last"]
    assert [step["status"] for step in task["steps"]] == ["completed", "running", "pending"]
    assert all(step["goal"] is None for step in task["steps"])
    assert any("Step별 목표가 저장되지" in note for note in page["notes"])


def test_step_detail_is_scoped_by_both_task_and_step_and_keeps_evidence(project):
    first = project.domain_detail("steps", "z_first", "plan_a")
    second = project.domain_detail("steps", "z_first", "plan_b")
    assert first["fields"]["Task revision"] == 7 and second["fields"]["Task revision"] == 2
    assert json.loads(first["fields"]["output_refs_json"]) == ["장면 해석 결과"]
    assert json.loads(second["fields"]["input_refs_json"]) == ["다른 Task의 입력"]
    with pytest.raises(ValueError):
        project.domain_detail("steps", "z_first")
    with pytest.raises(ValueError):
        project.domain_detail("steps", "z_first", "plan_c")


def test_recorded_object_names_and_step_goals_are_used_when_present(project):
    with sqlite3.connect(project.path) as db:
        db.execute("CREATE TABLE document_objects(rhino_guid TEXT,component_id TEXT,name TEXT)")
        db.executemany("INSERT INTO document_objects VALUES (?,?,?)", [("obj_a", "holon_a", "유리문"), ("obj_b", "holon_b", "손잡이")])
        db.execute("ALTER TABLE generation_plan_steps ADD COLUMN goal TEXT")
        db.execute("UPDATE generation_plan_steps SET goal='입력 조건 확인' WHERE plan_id='plan_a' AND step_id='z_first'")
    scene = project.domain_page("scenes", focus="scene_a")
    assert scene["capabilities"]["object_names"]
    assert set(scene["groups"][0]["objects"]) == {"유리문", "손잡이"}
    task = project.domain_page("tasks", focus="plan_a")
    assert task["capabilities"]["step_goals"] and task["groups"][0]["steps"][0]["goal"] == "입력 조건 확인"


def test_pagination_preserves_whole_parent_groups_and_bounds_expansions(project):
    first = project.domain_page("tasks", limit=1)
    second = project.domain_page("tasks", limit=1, offset=1)
    assert first["has_more"] and first["groups"][0]["id"] != second["groups"][0]["id"]
    with sqlite3.connect(project.path) as db:
        db.executemany("""INSERT INTO generation_plan_steps(plan_id,step_id,position,kind,status,
            depends_on_json,input_refs_json,output_refs_json) VALUES ('plan_empty',?,?,'reason','pending','[]','[]','[]')""",
                       [(f"extra_{i}", i) for i in range(RELATED_LIMIT + 1)])
    page = project.domain_page("tasks", focus="plan_empty", limit=1)
    assert len(page["groups"][0]["steps"]) == RELATED_LIMIT
    assert any(str(RELATED_LIMIT) in note for note in page["notes"])


def test_search_is_literal_and_invalid_ranges_and_identifiers_are_refused(project):
    assert project.domain_page("tasks", search="동선")["groups"][0]["id"] == "plan_a"
    assert not project.domain_page("tasks", search="%' OR 1=1 --")["groups"]
    assert not project.domain_page("holons", focus="holon_a' OR 1=1 --")["groups"]
    for options in ({"limit": 0}, {"limit": 21}, {"offset": -1}, {"search": "x" * 201}):
        with pytest.raises(ValueError):
            project.domain_page("scenes", **options)
    with pytest.raises(ValueError):
        project.domain_page("sqlite_schema")


def test_queries_preserve_database_bytes_and_do_not_initialize_missing_fields(project):
    before = hashlib.sha256(project.path.read_bytes()).digest()
    for kind in ("scenes", "holons", "phases", "tasks"):
        project.domain_page(kind)
    project.domain_detail("steps", "z_first", "plan_a")
    assert hashlib.sha256(project.path.read_bytes()).digest() == before
    with sqlite3.connect(project.path) as db:
        assert "goal" not in {row[1] for row in db.execute("PRAGMA table_info(generation_plan_steps)")}
        assert not db.execute("SELECT 1 FROM sqlite_schema WHERE name='document_objects'").fetchone()


def test_non_almond_database_stays_available_in_raw_explorer(tmp_path):
    path = tmp_path / "DB"  # An extension is not required for SQLite.
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE ordinary(name TEXT)")
        db.execute("INSERT INTO ordinary VALUES ('sample')")
    database = Database(path)
    assert not any(database.schema()["domain_views"].values())
    assert database.rows("ordinary")["rows"] == [["sample"]]
    with pytest.raises(ValueError):
        database.domain_page("scenes")


def test_partial_step_schema_reports_unsupported_instead_of_reading_missing_plan(tmp_path):
    path = tmp_path / "partial.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE generation_plan_steps(plan_id TEXT,step_id TEXT)")
        db.execute("INSERT INTO generation_plan_steps VALUES ('plan_a','step_a')")
    with pytest.raises(ValueError):
        Database(path).domain_detail("steps", "step_a", "plan_a")


def test_domain_http_endpoints_keep_authentication_file_identity_and_assets(project):
    server = DashboardServer(project.path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def get(route, params=None, authenticated=True):
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        path = route + ("?" + urlencode(params) if params else "")
        client.request("GET", path, headers={"X-Dashboard-Token": server.token} if authenticated else {})
        response = client.getresponse()
        result = response.status, response.read()
        client.close()
        return result
    try:
        params = {"database": str(project.path), "view": "tasks", "focus": "plan_a"}
        assert get("/api/domain", params, False)[0] == 403
        assert get("/api/domain", {**params, "database": "other.sqlite3"})[0] == 409
        status, body = get("/api/domain", params)
        assert status == 200 and json.loads(body)["groups"][0]["revision"] == 7
        assert get("/api/domain-detail", {**params, "view": "steps", "id": "z_first", "parent": "plan_a"})[0] == 200
        status, body = get("/domain.js", authenticated=False)
        assert status == 200 and b"DomainExplorer" in body
    finally:
        server.shutdown(); server.server_close(); thread.join(2)
