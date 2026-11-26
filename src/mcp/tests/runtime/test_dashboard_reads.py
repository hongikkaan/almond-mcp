from contextlib import closing
from http import HTTPStatus
from http.client import HTTPConnection
import json
import sqlite3
from urllib.parse import urlencode

import pytest

from dashboard.database import Database
from dashboard_sample import create_sample, serve_database


def _request(server, path, *, headers=None, body=None):
    method = "GET" if body is None else "POST"
    with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as connection:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, json.loads(response.read())


def test_dashboard_serves_only_the_current_file_to_an_authorized_client(tmp_path):
    first, second = tmp_path / "Current.sqlite3", tmp_path / "Reviewed.sqlite3"
    for path in (first, second):
        with closing(sqlite3.connect(path)) as writer, writer:
            writer.execute("CREATE TABLE notes(label TEXT)")
            writer.execute("INSERT INTO notes VALUES (?)", (path.stem,))
    missing = tmp_path / "Missing.sqlite3"
    original = first.read_bytes(), second.read_bytes()

    with serve_database(first) as server:
        authenticated = {"X-Dashboard-Token": server.token}
        route = "/api/rows?" + urlencode({"database": str(first), "table": "notes"})
        assert _request(server, route)[0] == HTTPStatus.FORBIDDEN
        for header, value in (("Host", "other.example"), ("Origin", "https://other.example")):
            assert _request(server, route, headers={**authenticated, header: value})[0] == HTTPStatus.FORBIDDEN
        assert _request(server, route, headers=authenticated)[1]["rows"] == [["Current"]]

        def open_db(path):
            return _request(server, "/api/open", headers=authenticated, body=json.dumps({"path": str(path)}))

        assert open_db(missing)[0] == HTTPStatus.BAD_REQUEST
        assert not missing.exists()
        assert _request(server, route, headers=authenticated)[1]["rows"] == [["Current"]]
        assert open_db(second)[0] == HTTPStatus.OK
        assert _request(server, route, headers=authenticated)[0] == HTTPStatus.CONFLICT
        updated = "/api/rows?" + urlencode({"database": str(second), "table": "notes"})
        assert _request(server, updated, headers=authenticated)[1]["rows"] == [["Reviewed"]]
        assert _request(server, "/api/rows", headers=authenticated, body="{}")[0] == HTTPStatus.NOT_FOUND

    assert (first.read_bytes(), second.read_bytes()) == original


def test_dashboard_filters_stored_context_and_keeps_previous_loop_evidence(tmp_path):
    path = tmp_path / "Design.sqlite3"
    plan, step, phase, scene = create_sample(path)
    original = path.read_bytes()

    with serve_database(path) as server:
        def request_domain(route, **options):
            query = urlencode({"database": str(path), **options})
            return _request(server, f"/api/{route}?{query}", headers={"X-Dashboard-Token": server.token})

        status, body = request_domain("domain", view="tasks", file="Courtyard.3dm", phase=phase, scene=scene)
        assert status == HTTPStatus.OK
        assert [group["id"] for group in body["groups"]] == [plan]
        task = body["groups"][0]
        assert task["loop_no"] == 2
        assert task["file_names"] == ["Courtyard.3dm", "Lobby.3dm"]
        assert task["steps"][0]["takeaways"] == "새 입구 확장"

        status, body = request_domain("domain-detail", view="steps", id=step, parent=plan, loop_no=1)
        assert status == HTTPStatus.OK
        assert body["loop_no"] == 1
        assert body["fields"]["takeaways"] == "기존 입구 유지"
        assert body["fields"]["output_refs"] == ["drawings/old.pdf"]

    assert path.read_bytes() == original


def test_dashboard_reads_committed_wal_without_writing_or_disturbing_the_writer(tmp_path):
    path = tmp_path / "Project.sqlite3"
    with closing(sqlite3.connect(path)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE notes(label TEXT)")
        writer.execute("INSERT INTO notes VALUES ('committed')")
        writer.commit()
        writer.execute("INSERT INTO notes VALUES ('pending')")
        dashboard = Database(path)

        assert dashboard.rows("notes")["rows"] == [["committed"]]
        with dashboard.connect() as reader:
            for sql in ("INSERT INTO notes VALUES ('dashboard change')", "DROP TABLE notes"):
                with pytest.raises(sqlite3.OperationalError) as rejected:
                    reader.execute(sql)
                assert rejected.value.sqlite_errorcode == sqlite3.SQLITE_READONLY
        assert writer.in_transaction
        writer.commit()
        assert dashboard.rows("notes", sort="label")["rows"] == [["committed"], ["pending"]]
